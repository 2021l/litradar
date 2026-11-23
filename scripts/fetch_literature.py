#!/usr/bin/env python
"""Fetch recent journal articles from Crossref and enrich with OpenAlex.

Usage:
  python scripts/fetch_literature.py
  python scripts/fetch_literature.py --since 2026-10-17 --until 2026-11-16
  python scripts/fetch_literature.py --days 7 --journals nature_electronics,advanced_materials
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from common import (
    RAW_DIR,
    atomic_write_json,
    clean_markup,
    crossref_dates,
    date_in_window,
    effective_date,
    ensure_dirs,
    journal_index,
    load_json,
    load_keywords,
    load_scoring,
    normalize_doi,
    now_iso,
    paper_any_date_in_window,
    request_json,
    setup_logging,
    today,
)

CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"
MAILTO = "radar@example.org"
CROSSREF_SELECT = (
    "DOI,title,abstract,author,published-online,published-print,issued,created,"
    "container-title,type,URL,link,subject,ISSN,update-to,relation,publisher,"
    "is-referenced-by-count"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch recent papers from whitelisted journals")
    p.add_argument("--since", help="YYYY-MM-DD (inclusive)")
    p.add_argument("--until", help="YYYY-MM-DD (inclusive)")
    p.add_argument("--days", type=int, help="Override window length in days")
    p.add_argument("--first-run-days", type=int, default=30, help="Window for first run")
    p.add_argument("--journals", help="Comma-separated journal ids")
    p.add_argument("--max-per-journal", type=int, default=1500)
    p.add_argument("--output", help="Output JSON path")
    p.add_argument("--skip-openalex", action="store_true")
    p.add_argument("--merge", action="store_true", help="Merge into an existing raw file")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args()


def determine_window(args: argparse.Namespace, logger) -> tuple[date, date, bool]:
    until = date.fromisoformat(args.until) if args.until else today()
    if args.since:
        state = load_json(ROOT_STATE, default={}) or {}
        return date.fromisoformat(args.since), until, not bool(state.get("last_success"))
    state = load_json(ROOT_STATE, default={}) or {}
    last_success = state.get("last_success")
    if last_success:
        try:
            last_date = date.fromisoformat(str(last_success)[:10])
            return last_date - timedelta(days=2), until, False
        except Exception:
            logger.warning("Invalid last_success %r; falling back to first run", last_success)
    if args.days:
        return until - timedelta(days=args.days - 1), until, False
    return until - timedelta(days=args.first_run_days - 1), until, True


ROOT_STATE = Path(__file__).resolve().parent.parent / "state" / "last_run.json"


def _norm_name(text: str) -> str:
    """刊名归一化：小写，非字母数字折叠为空格。"""
    chars = [ch if ch.isalnum() else " " for ch in str(text or "").lower()]
    return " ".join("".join(chars).split())


def container_matches(item: dict[str, Any], name: str) -> bool:
    """没有 ISSN 时，用 container-title 校验结果确实来自目标期刊。"""
    targets = item.get("container-title") or []
    if isinstance(targets, str):
        targets = [targets]
    wanted = _norm_name(name)
    if not wanted:
        return True
    for target in targets:
        got = _norm_name(target)
        if not got:
            continue
        if got == wanted or wanted in got or got in wanted:
            return True
    return False


def topic_terms(query: str) -> list[str]:
    """把检索式拆成有效词，去掉虚词和过短的词。"""
    stop = {"and", "or", "the", "of", "for", "with", "in", "on", "a", "an", "to", "by", "using"}
    return [w for w in _norm_name(query).split() if len(w) > 2 and w not in stop]


def topic_matches(item: dict[str, Any], query: str) -> bool:
    """主题检索的精度闸门。

    Crossref 的 bibliographic 查询很宽松，不加约束会把无关论文一起带回来，
    所以这里要求标题/摘要/主题词命中检索式的多数关键词才收。
    """
    terms = topic_terms(query)
    if not terms:
        return True
    text = _norm_name(
        " ".join(
            [
                " ".join(item.get("title") or []),
                str(item.get("abstract") or ""),
                " ".join(item.get("subject") or []),
            ]
        )
    )
    hits = sum(1 for term in terms if term in text)
    need = max(1, len(terms) // 2 + 1)
    return hits >= need


def crossref_query(
    journal: dict[str, Any], since: date, until: date, max_items: int, logger,
    use_created: bool = False,
) -> tuple[list[dict], int]:
    issn = (journal.get("issn") or [""])[0]
    date_field = "created" if use_created else "pub"
    date_filter = (
        f"from-{date_field}-date:{since.isoformat()},"
        f"until-{date_field}-date:{until.isoformat()},type:journal-article"
    )
    # 三类条目：
    #   issn  —— 按刊号精确检索
    #   query —— 按主题检索（不知道盯哪几本刊时用）
    #   其余  —— 按刊名检索 + container-title 过滤
    topic = str(journal.get("query") or "").strip()
    name_query = "" if (issn or topic) else str(journal.get("name") or "").strip()
    if not issn and not topic and not name_query:
        raise ValueError(f"期刊 {journal.get('id')} 既没有 issn、name，也没有 query")
    filt = f"issn:{issn},{date_filter}" if issn else date_filter
    cursor = "*"
    items: list[dict] = []
    total = 0
    page = 0
    while True:
        page += 1
        params = {
            "filter": filt,
            "rows": "500",
            "cursor": cursor,
            "select": CROSSREF_SELECT,
            "mailto": MAILTO,
        }
        if name_query:
            params["query.container-title"] = name_query
        elif topic:
            params["query.bibliographic"] = topic
            params["sort"] = "relevance"
            params["order"] = "desc"
        url = CROSSREF + "?" + urllib.parse.urlencode(params)
        try:
            data = request_json(url, logger=logger, timeout=90)
        except Exception as exc:
            # Older API deployments may reject one of the select fields.
            logger.warning("Crossref select query failed, retrying without select: %s", exc)
            params.pop("select", None)
            url = CROSSREF + "?" + urllib.parse.urlencode(params)
            data = request_json(url, logger=logger, timeout=120)
        msg = data.get("message", {})
        total = int(msg.get("total-results", 0) or 0)
        batch = msg.get("items", []) or []
        if name_query:
            batch = [it for it in batch if container_matches(it, name_query)]
        elif topic:
            batch = [it for it in batch if topic_matches(it, topic)]
        items.extend(batch)
        cursor = msg.get("next-cursor")
        logger.info(
            "Crossref %-28s %4d/%-4d fetched (page %d%s)",
            journal["name"], len(items), total, page,
            ", created-date fallback" if use_created else "",
        )
        if not batch or not cursor or len(items) >= max_items or len(items) >= total:
            break
        if page >= 5:
            logger.warning("Page cap reached for %s; possible truncation", journal["name"])
            break
        time.sleep(0.7)
    if len(items) > max_items:
        items = items[:max_items]
    time.sleep(0.35)
    return items, total


def trim_crossref_item(
    item: dict[str, Any], journal: dict[str, Any], since: date, until: date,
    use_created: bool = False,
) -> dict[str, Any] | None:
    doi = normalize_doi(item.get("DOI"))
    title = clean_markup((item.get("title") or [""])[0])
    if not doi or not title:
        return None
    dates = crossref_dates(item)
    probe = dict(dates)
    if not paper_any_date_in_window(probe, since, until):
        return None

    def parts(key: str) -> list:
        obj = item.get(key) or {}
        p = (obj.get("date-parts") or [[]])[0]
        return p or []

    online_parts = parts("published-online")
    if use_created and len(online_parts) < 3:
        # RSC / IEEE often deposit only a year-level publication date.
        # Use the Crossref deposit date as a transparent, labelled fallback.
        dates["published_online"] = dates["created"]
        date_precision = "deposit"
        date_note = "Crossref 未提供精确在线日期；以入库日期作为检索日期，正式发表日期需查出版社页面"
    else:
        date_precision = "day" if len(online_parts) >= 3 else ("month" if len(online_parts) == 2 else "year")
        date_note = "" if date_precision == "day" else "Crossref 在线日期精度不足，需查出版社页面核实"

    authors: list[str] = []
    for a in item.get("author", []) or []:
        name = " ".join(x for x in [a.get("given"), a.get("family")] if x).strip()
        if not name:
            name = a.get("name", "") or ""
        if name:
            authors.append(name)

    abstract = clean_markup(item.get("abstract"))
    subjects = item.get("subject", []) or []
    resource = item.get("resource", {}) or {}
    primary = resource.get("primary", {}) if isinstance(resource, dict) else {}
    publisher_url = primary.get("URL") if isinstance(primary, dict) else None
    publisher_url = publisher_url or ("https://doi.org/" + doi)
    links = []
    for link in item.get("link", []) or []:
        u = link.get("URL")
        if u:
            links.append(u)

    subtype = item.get("subtype") or ""
    update_to = []
    for rel in item.get("update-to", []) or []:
        update_to.append(
            {
                "type": rel.get("type"),
                "doi": normalize_doi(rel.get("DOI")),
                "label": rel.get("label"),
            }
        )

    return {
        "doi": doi,
        "doi_url": "https://doi.org/" + doi,
        "title": title,
        "abstract": abstract,
        "abstract_source": "crossref" if abstract else "none",
        "authors": authors,
        "journal_id": journal["id"],
        "journal": journal["name"],
        "journal_tier": journal["tier"],
        "publisher": journal.get("publisher", item.get("publisher", "")),
        "issn": item.get("ISSN", []) or journal.get("issn", []),
        "type": item.get("type", ""),
        "subtype": subtype,
        "subject": subjects,
        "published_online": dates["published_online"],
        "published_print": dates["published_print"],
        "issued": dates["issued"],
        "created": dates["created"],
        "date_precision": date_precision,
        "date_note": date_note,
        "effective_date": effective_date({**dates, "doi": doi}),
        "crossref_url": item.get("URL", ""),
        "publisher_url": publisher_url,
        "landing_page_url": publisher_url,
        "links": links[:5],
        "update_to": update_to,
        "relation": item.get("relation", {}) or {},
        "citation_count_crossref": item.get("is-referenced-by-count"),
        "openalex": None,
    }


def openalex_enrich(papers: list[dict[str, Any]], logger) -> int:
    by_doi = {p["doi"]: p for p in papers}
    dois = list(by_doi)
    matched = 0
    fields = (
        "id,doi,title,publication_date,abstract_inverted_index,cited_by_count,type,"
        "primary_location,open_access,topics,keywords,is_retracted,updated_date"
    )
    for start in range(0, len(dois), 40):
        chunk = dois[start:start + 40]
        filter_val = "doi:" + "|".join("https://doi.org/" + d for d in chunk)
        params = {"filter": filter_val, "per-page": "50", "select": fields, "mailto": MAILTO}
        url = OPENALEX + "?" + urllib.parse.urlencode(params)
        try:
            data = request_json(url, logger=logger, timeout=90)
        except Exception as exc:
            logger.warning("OpenAlex batch %d failed: %s", start // 40 + 1, exc)
            continue
        for r in data.get("results", []) or []:
            doi = normalize_doi(r.get("doi"))
            p = by_doi.get(doi)
            if not p:
                continue
            inv = r.get("abstract_inverted_index")
            abstract = clean_markup(p.get("abstract"))
            oa_abstract = ""
            if inv:
                from common import reconstruct_abstract
                oa_abstract = clean_markup(reconstruct_abstract(inv))
            if len(oa_abstract) > len(abstract):
                p["abstract"] = oa_abstract
                p["abstract_source"] = "openalex"
            loc = r.get("primary_location") or {}
            source = loc.get("source") or {}
            open_access = r.get("open_access") or {}
            topics = []
            for t in (r.get("topics") or [])[:5]:
                name = t.get("display_name")
                if name:
                    topics.append(name)
            keywords = []
            for k in (r.get("keywords") or [])[:8]:
                name = k.get("display_name")
                if name:
                    keywords.append(name)
            p["openalex"] = {
                "id": r.get("id"),
                "publication_date": r.get("publication_date"),
                "cited_by_count": r.get("cited_by_count"),
                "type": r.get("type"),
                "is_retracted": bool(r.get("is_retracted")),
                "is_oa": bool(open_access.get("is_oa")),
                "oa_status": open_access.get("oa_status"),
                "oa_url": open_access.get("oa_url"),
                "source": source.get("display_name"),
                "source_issn_l": source.get("issn_l"),
                "landing_page_url": loc.get("landing_page_url"),
                "topics": topics,
                "keywords": keywords,
            }
            landing = loc.get("landing_page_url")
            if landing and (not p.get("publisher_url") or p["publisher_url"].startswith("https://doi.org/")):
                p["publisher_url"] = landing
                p["landing_page_url"] = landing
            matched += 1
        logger.info("OpenAlex enriched %d/%d", matched, len(dois))
        time.sleep(0.15)
    return matched


def mark_flags(paper: dict[str, Any], kw: dict[str, Any]) -> None:
    text = f"{paper.get('title','')} {paper.get('abstract','')}"
    flags = {}
    for key, spec in (kw.get("flags") or {}).items():
        hits = []
        for term in spec.get("terms", []):
            if term_present_safe(text, term):
                hits.append(term)
        flags[key] = {"label": spec.get("label", key), "hits": sorted(set(hits))}
    paper["flags"] = flags

    tie = 0
    for group in kw.get("priority_tiebreak") or []:
        if any(term_present_safe(text, t) for t in group.get("terms", [])):
            tie += int(group.get("points", 0))
    paper["strategic_tiebreak"] = tie

    review_reasons = []
    import re
    # Review detection must not fire on a research abstract that merely says
    # "recent advances in..."; use the title plus Crossref subtype only.
    review_text = paper.get("title", "")
    for pat in kw.get("review_patterns", []):
        try:
            if re.search(pat, review_text, re.I):
                review_reasons.append(pat)
        except re.error:
            continue
    abstract_text = paper.get("abstract", "")
    for pat in (
        r"\bthis (?:review|perspective|overview|roadmap)\b",
        r"\bin this (?:review|perspective|overview)\b",
        r"\bwe (?:review|summarize|provide an overview)\b",
        r"\bhere,? we (?:review|summarize)\b",
    ):
        if re.search(pat, abstract_text, re.I):
            review_reasons.append("abstract-review-cue")
            break
    if str(paper.get("subtype", "")).lower() in ("review-article", "review"):
        review_reasons.append("crossref-subtype-review")
    paper["is_review_suspect"] = bool(review_reasons)
    paper["review_reasons"] = review_reasons


def term_present_safe(text: str, term: str) -> bool:
    from common import term_present
    return term_present(text, term)


def gate_check(paper: dict[str, Any], kw: dict[str, Any]) -> None:
    text = f"{paper.get('title','')} {paper.get('abstract','')}"
    gates = kw.get("gates", {})
    core_hits = [t for t in gates.get("core", []) if term_present_safe(text, t)]
    scope_hits = [t for t in gates.get("scope", []) if term_present_safe(text, t)]
    exclude_hits = [t for t in gates.get("exclude", []) if term_present_safe(text, t)]
    # gates 可以留空：留空即不做门槛过滤，只靠方向关键词打分排序。
    core_cfg = gates.get("core") or []
    scope_cfg = gates.get("scope") or []
    core_ok = (not core_cfg) or bool(core_hits)
    scope_ok = (not scope_cfg) or bool(scope_hits)
    paper["gate"] = {
        "core_hits": sorted(set(core_hits)),
        "scope_hits": sorted(set(scope_hits)),
        "exclude_hits": sorted(set(exclude_hits)),
        "core_gate_enabled": bool(core_cfg),
        "scope_gate_enabled": bool(scope_cfg),
        "pass": bool(core_ok and scope_ok and not exclude_hits),
    }


def main() -> int:
    args = parse_args()
    logger = setup_logging("fetch", verbose=not args.quiet)
    ensure_dirs()
    since, until, first_run = determine_window(args, logger)
    logger.info("Window: %s .. %s (first_run=%s)", since, until, first_run)

    jmap, journals = journal_index()
    if args.journals:
        wanted = {s.strip() for s in args.journals.split(",") if s.strip()}
        journals = [j for j in journals if j["id"] in wanted]
        if not journals:
            logger.error("No journal matched --journals")
            return 2
    logger.info("Journals enabled: %d", len(journals))

    kw = load_keywords()
    scoring = load_scoring()
    out_path = Path(args.output) if args.output else RAW_DIR / f"{until.isoformat()}.json"
    existing = load_json(out_path, default=None) if args.merge else None
    papers: dict[str, dict[str, Any]] = {}
    journal_stats: list[dict[str, Any]] = []
    failed = []
    if existing:
        papers = {p["doi"]: p for p in existing.get("papers", []) if p.get("doi")}
        journal_stats = list(existing.get("journals", []))
        failed = list(existing.get("failed_sources", []))
        logger.info("Merge mode: loaded %d existing papers from %s", len(papers), out_path)

    for i, journal in enumerate(journals, 1):
        logger.info("[%d/%d] Querying %s", i, len(journals), journal["name"])
        journal_stats = [s for s in journal_stats if s.get("journal_id") != journal["id"]]
        stat = {
            "journal_id": journal["id"],
            "name": journal["name"],
            "tier": journal["tier"],
            "issn": (journal.get("issn") or [""])[0],
            "total_results": 0,
            "fetched": 0,
            "kept": 0,
            "error": None,
            "date_fallback": None,
        }
        try:
            items, total = crossref_query(journal, since, until, args.max_per_journal, logger)
            if total == 0:
                logger.info("No published-date results for %s; trying Crossref created-date fallback", journal["name"])
                items, total = crossref_query(
                    journal, since, until, args.max_per_journal, logger, use_created=True
                )
                stat["date_fallback"] = "created"
            stat["total_results"] = total
            stat["fetched"] = len(items)
            for item in items:
                slim = trim_crossref_item(item, journal, since, until, use_created=stat["date_fallback"] == "created")
                if not slim:
                    continue
                doi = slim["doi"]
                if doi in papers:
                    # Keep the record from the journal that owns the DOI; merge abstract if missing.
                    if not papers[doi].get("abstract") and slim.get("abstract"):
                        papers[doi]["abstract"] = slim["abstract"]
                        papers[doi]["abstract_source"] = slim["abstract_source"]
                    continue
                mark_flags(slim, kw)
                gate_check(slim, kw)
                papers[doi] = slim
                stat["kept"] += 1
        except Exception as exc:
            logger.error("Journal query failed for %s: %s", journal["name"], exc)
            stat["error"] = str(exc)
            failed.append({"journal_id": journal["id"], "name": journal["name"], "error": str(exc)})
        journal_stats.append(stat)

    paper_list = list(papers.values())
    logger.info("Crossref unique papers: %d", len(paper_list))
    oa_matched = 0
    to_enrich = [p for p in paper_list if not p.get("openalex")]
    if to_enrich and not args.skip_openalex:
        try:
            oa_matched = openalex_enrich(to_enrich, logger)
        except Exception as exc:
            logger.error("OpenAlex enrichment aborted: %s", exc)
            failed.append({"journal_id": "openalex", "name": "OpenAlex enrichment", "error": str(exc)})

    # Final abstract/date consistency pass
    no_abstract = 0
    for p in paper_list:
        p["abstract"] = clean_markup(p.get("abstract"))
        p["has_abstract"] = len(p["abstract"]) >= int(scoring.get("confidence", {}).get("medium_min_abstract_chars", 200))
        if not p["has_abstract"]:
            no_abstract += 1
        p["in_window"] = paper_any_date_in_window(p, since, until)
        p["review_suspect"] = p.get("is_review_suspect", False)

    output = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "window": {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "days": (until - since).days + 1,
            "first_run": first_run,
            "overlap_days": 2,
        },
        "sources": ["Crossref REST API", "OpenAlex API"],
        "journals_queried": len({s.get("journal_id") for s in journal_stats}),
        "journals": journal_stats,
        "failed_sources": failed,
        "stats": {
            "crossref_unique": len(paper_list),
            "openalex_matched": oa_matched,
            "with_abstract": len(paper_list) - no_abstract,
            "without_abstract": no_abstract,
            "gate_pass": sum(1 for p in paper_list if p.get("gate", {}).get("pass")),
            "review_suspect": sum(1 for p in paper_list if p.get("review_suspect")),
        },
        "papers": sorted(paper_list, key=lambda p: (p.get("journal_id", ""), p.get("effective_date") or "")),
    }

    atomic_write_json(out_path, output)
    logger.info("Wrote %s (%d papers)", out_path, len(paper_list))
    print(json.dumps({"ok": True, "output": str(out_path), "stats": output["stats"], "failed_sources": failed}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
