#!/usr/bin/env python
"""Filter, deduplicate and machine pre-score fetched papers."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from common import (
    CANDIDATE_DIR,
    RAW_DIR,
    atomic_write_json,
    ensure_dirs,
    load_json,
    load_keywords,
    load_scoring,
    matched_terms,
    normalize_doi,
    normalize_title,
    now_iso,
    setup_logging,
    term_present,
    today,
)
from deduplicate import annotate, load_db, scan_updates
from fetch_literature import gate_check, mark_flags


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Filter and score recent papers")
    p.add_argument("--input", help="Raw JSON from fetch_literature.py")
    p.add_argument("--output", help="Candidates JSON path")
    p.add_argument("--top", type=int, default=30, help="Max papers kept in ranked list")
    p.add_argument("--include-reported", action="store_true", help="Keep already reported papers rankable")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args()


def pick_input(args: argparse.Namespace) -> Path:
    if args.input:
        return Path(args.input)
    candidates = sorted(RAW_DIR.glob("*.json"))
    if not candidates:
        raise SystemExit(f"No raw files in {RAW_DIR}; run fetch_literature.py first")
    return candidates[-1]


def direction_terms(kw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {d["id"]: d for d in kw.get("directions", [])}


def score_relevance(paper: dict[str, Any], kw: dict[str, Any], scoring: dict[str, Any]) -> tuple[int, dict[str, Any], str, str]:
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    spec = scoring.get("relevance", {})
    title_points = int(spec.get("title_hit_points", 2))
    abstract_points = int(spec.get("abstract_hit_points", 1))
    total_terms = 0
    detail: dict[str, Any] = {}
    best_id = ""
    best_points = -1
    covered = 0
    for d in kw.get("directions", []):
        hits = []
        points = 0
        for term in d.get("terms", []):
            in_title = term_present(title, term)
            in_abs = term_present(abstract, term)
            if in_title or in_abs:
                hits.append(term)
                points += title_points if in_title else abstract_points
        points = min(points, int(d.get("cap", 0)))
        detail[d["id"]] = {
            "label": d.get("label", d["id"]),
            "hits": sorted(set(hits)),
            "points": points,
            "cap": d.get("cap"),
        }
        total_terms += points
        if points > 0:
            covered += 1
        if points > best_points:
            best_points = points
            best_id = d["id"]
    total_terms = min(total_terms, int(spec.get("term_points_cap", 30)))
    base = int(spec.get("base", 0))
    coverage_bonus = covered * int(spec.get("direction_coverage_points", 0))
    total = min(30, base + total_terms + coverage_bonus)
    best_label = next((d.get("label", best_id) for d in kw["directions"] if d["id"] == best_id), best_id)
    return total, detail, best_id, best_label


def score_innovation(paper: dict[str, Any], scoring: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    spec = scoring.get("innovation", {})
    text = f"{paper.get('title','')} {paper.get('abstract','')}"
    cues = [c for c in spec.get("cues", []) if term_present(text, c)]
    sups = [s for s in spec.get("superlatives", []) if term_present(text, s)]
    cue_points = min(len(cues) * float(spec.get("cue_points", 2.5)), float(spec.get("cue_cap", 12)))
    sup_points = min(len(sups) * int(spec.get("superlative_points", 2)), int(spec.get("superlative_cap", 5)))
    base = int(spec.get("base_if_any_cue", 6)) if cues or sups else 0
    total = min(int(round(base + cue_points + sup_points)), 25)
    return total, {"cues": sorted(set(cues)), "superlatives": sorted(set(sups)), "provisional": True}


def score_materials(paper: dict[str, Any], kw: dict[str, Any], scoring: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    spec = scoring.get("materials_and_process", {})
    text = f"{paper.get('title','')} {paper.get('abstract','')}"
    dirs = direction_terms(kw)
    material_terms: list[str] = []
    for did in ("conductive_materials", "substrates_composites"):
        material_terms.extend(dirs.get(did, {}).get("terms", []))
    process_terms = dirs.get("fabrication", {}).get("terms", [])
    mats = sorted(set(matched_terms(text, material_terms)))
    procs = sorted(set(matched_terms(text, process_terms)))
    mat_points = min(len(mats) * float(spec.get("material_points", 2)), float(spec.get("material_cap", 9)))
    proc_points = min(len(procs) * float(spec.get("process_points", 2)), float(spec.get("process_cap", 6)))
    base = int(spec.get("base_if_any", 3)) if mats or procs else 0
    total = int(round(min(base + mat_points + proc_points, 15)))
    return total, {"materials": mats, "processes": procs, "material_points": mat_points, "process_points": proc_points}


def score_results(paper: dict[str, Any], scoring: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    spec = scoring.get("results", {})
    text = f"{paper.get('title','')} {paper.get('abstract','')}"
    units = spec.get("unit_pattern", "")
    quant: list[str] = []
    if units:
        pattern = re.compile(r"\d+(?:\.\d+)?\s*(?:" + units + ")", re.I)
        quant = sorted({re.sub(r"\s+", "", m.lower()) for m in pattern.findall(text)})
    comparisons = sorted({c for c in spec.get("comparison_terms", []) if term_present(text, c)})
    q_points = min(len(quant) * int(spec.get("quantitative_points", 2)), int(spec.get("quantitative_cap", 10)))
    c_points = min(len(comparisons) * int(spec.get("comparison_points", 1)), int(spec.get("comparison_cap", 5)))
    total = min(q_points + c_points, 15)
    return total, {"quantities": quant, "comparisons": comparisons}


def score_journal(paper: dict[str, Any], scoring: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    spec = scoring.get("journal", {})
    tier = paper.get("journal_tier", "B")
    pts = int(spec.get("tier_points", {}).get(tier, 9))
    name = paper.get("journal", "")
    bonus = 0
    if tier == "A":
        if name in (spec.get("flagship_bonus") or {}):
            bonus = int(spec["flagship_bonus"][name])
        elif name.startswith("Nature "):
            bonus = int(spec.get("nature_subjournal_bonus", 2))
    total = min(pts + bonus, int(spec.get("cap", 15)))
    return total, {"tier": tier, "base": pts, "bonus": bonus}


def band_for(score: int, scoring: dict[str, Any]) -> dict[str, Any]:
    for item in scoring.get("bands", []):
        if score >= int(item["min"]):
            return item
    return {"label": "暂不推荐", "action": "不进入核心周报", "min": 0}


def dedup_batch(papers: list[dict[str, Any]], threshold: float) -> None:
    """Compare only same-journal papers with a similar prefix; keeps O(n) practical."""
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for p in papers:
        p["duplicate_of"] = None
        norm = normalize_title(p.get("title", ""))
        if not norm:
            continue
        key = (p.get("journal_id", ""), norm[:24])
        bucket = buckets.setdefault(key, [])
        for prev in bucket:
            if prev.get("duplicate_of"):
                continue
            norm_j = normalize_title(prev.get("title", ""))
            if not norm_j:
                continue
            if abs(len(norm) - len(norm_j)) > max(20, int(0.35 * max(len(norm), len(norm_j)))):
                continue
            if difflib.SequenceMatcher(None, norm, norm_j).ratio() >= threshold:
                p["duplicate_of"] = prev.get("doi")
                break
        bucket.append(p)


def main() -> int:
    args = parse_args()
    logger = setup_logging("filter", verbose=not args.quiet)
    ensure_dirs()
    inp = pick_input(args)
    raw = load_json(inp)
    if not raw or "papers" not in raw:
        raise SystemExit(f"Invalid raw file: {inp}")
    kw = load_keywords()
    scoring = load_scoring()
    db = load_db()

    papers = raw.get("papers", [])
    # Recompute gates/flags after OpenAlex abstract enrichment; fetch-time flags
    # were computed before enrichment and would miss OpenAlex-only abstracts.
    for p in papers:
        mark_flags(p, kw)
        gate_check(p, kw)
    gate_pass = [p for p in papers if p.get("gate", {}).get("pass")]
    dedup_batch(gate_pass, float(scoring.get("dedup", {}).get("title_similarity_threshold", 0.92)))

    empty_score = {
        "total": 0,
        "relevance": 0,
        "innovation": 0,
        "materials_and_process": 0,
        "results": 0,
        "journal": 0,
        "band": "暂不推荐",
        "band_min": 0,
        "machine_only": True,
        "caveat": "未通过相关性门槛，未进入评分",
        "details": {},
        "reasons": ["未通过相关性门槛"],
    }
    for p in papers:
        p["doi"] = normalize_doi(p.get("doi"))
        history = annotate(p, db)
        p["history"] = history
        if not p.get("gate", {}).get("pass"):
            p["direction"] = ""
            p["direction_id"] = ""
            p["primary_direction"] = ""
            p["score"] = dict(empty_score)
            continue
        relevance, rel_detail, direction_id, direction_label = score_relevance(p, kw, scoring)
        innovation, inn_detail = score_innovation(p, scoring)
        materials, mat_detail = score_materials(p, kw, scoring)
        results, res_detail = score_results(p, scoring)
        journal, j_detail = score_journal(p, scoring)
        total = relevance + innovation + materials + results + journal
        reasons: list[str] = []
        if not p.get("has_abstract"):
            total = min(total, int(scoring.get("confidence", {}).get("metadata_only_score_cap", 70)))
            reasons.append("无公开摘要：仅能做元数据初筛，分数封顶")
        band = band_for(total, scoring)
        p["direction"] = direction_label
        p["direction_id"] = direction_id
        p["score"] = {
            "total": total,
            "relevance": relevance,
            "innovation": innovation,
            "materials_and_process": materials,
            "results": results,
            "journal": journal,
            "band": band["label"],
            "band_min": band.get("min"),
            "machine_only": True,
            "caveat": "机器预评分；创新性需 Agent 阅读摘要/全文后复核",
            "details": {
                "relevance": rel_detail,
                "innovation": inn_detail,
                "materials_and_process": mat_detail,
                "results": res_detail,
                "journal": j_detail,
            },
            "reasons": reasons,
        }
        p["primary_direction"] = direction_id

    # Duplicate/history/gate exclusions
    for p in papers:
        exclusions = []
        if not p.get("gate", {}).get("pass"):
            exclusions.append("未通过相关性门槛")
        if p.get("duplicate_of"):
            exclusions.append("批内重复")
        if p.get("history", {}).get("status") == "already_reported" and not args.include_reported:
            exclusions.append("历史已推荐")
        if p.get("is_review_suspect"):
            exclusions.append("综述/非原创研究")
        if not p.get("has_abstract"):
            exclusions.append("无摘要，转待核验附录")
        p["exclusions"] = exclusions
        p["rankable"] = len(exclusions) == 0

    def rank_key(p: dict[str, Any]) -> tuple:
        try:
            day = date.fromisoformat((p.get("effective_date") or "1970-01-01")[:10]).toordinal()
        except Exception:
            day = 0
        return (-int(p["score"]["total"]), -int(p.get("strategic_tiebreak", 0)), -day)

    ranked = sorted(
        [p for p in papers if p["rankable"]],
        key=rank_key,
    )
    for i, p in enumerate(ranked, 1):
        p["rank"] = i
    for p in papers:
        p.setdefault("rank", None)

    reviews = sorted(
        [p for p in papers if p.get("is_review_suspect") and p.get("gate", {}).get("pass")],
        key=lambda p: (-int(p["score"]["total"]), p.get("effective_date") or ""),
    )
    appendix = sorted(
        [p for p in papers if not p.get("has_abstract") and p.get("gate", {}).get("pass") and not p.get("is_review_suspect")],
        key=lambda p: p.get("effective_date") or "",
        reverse=True,
    )
    top = ranked[: max(1, args.top)]

    bands: dict[str, int] = {}
    for p in ranked:
        bands[p["score"]["band"]] = bands.get(p["score"]["band"], 0) + 1

    out = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "source_raw": str(inp),
        "window": raw.get("window", {}),
        "journals_queried": raw.get("journals_queried"),
        "stats": {
            "fetched": len(papers),
            "gate_pass": sum(1 for p in papers if p.get("gate", {}).get("pass")),
            "rankable": len(ranked),
            "top_kept": len(top),
            "reviews": len(reviews),
            "metadata_only_appendix": len(appendix),
            "already_reported": sum(1 for p in papers if p.get("history", {}).get("status") == "already_reported"),
            "duplicates": sum(1 for p in papers if p.get("duplicate_of")),
            "score_bands": bands,
            "with_abstract": sum(1 for p in papers if p.get("has_abstract")),
        },
        "update_alerts": scan_updates(papers, db),
        "papers": papers,
        "ranked": top,
        "reviews": reviews,
        "appendix": appendix[:40],
    }
    if args.output:
        output = Path(args.output)
    else:
        until = raw.get("window", {}).get("until") or today().isoformat()
        output = CANDIDATE_DIR / f"{until}.json"
    atomic_write_json(output, out)
    logger.info("Candidates written: %s", output)
    print(json.dumps({
        "ok": True,
        "output": str(output),
        "stats": out["stats"],
        "top5": [
            {
                "rank": p["rank"],
                "doi": p["doi"],
                "title": p["title"],
                "journal": p["journal"],
                "date": p.get("published_online") or p.get("effective_date"),
                "score": p["score"]["total"],
                "direction": p["direction"],
            }
            for p in top[:5]
        ],
        "update_alerts": out["update_alerts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
