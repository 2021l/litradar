#!/usr/bin/env python
"""Locate open-access full text and cache Europe PMC JATS sections.

This only retrieves legally open content. It never attempts to bypass paywalls.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from common import (
    DATABASE_DIR,
    atomic_write_json,
    clean_markup,
    ensure_dirs,
    load_json,
    normalize_doi,
    now_iso,
    request_json,
    safe_slug,
    setup_logging,
)

FULLTEXT_DIR = DATABASE_DIR / "fulltext"
EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EPMC_XML = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
OPENALEX = "https://api.openalex.org/works/https://doi.org/{doi}"


def fetch_bytes(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Litradar/1.0 (mailto:radar@example.org)",
            "Accept": "application/xml,text/xml,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def text_of(el: ET.Element) -> str:
    return clean_markup(" ".join(el.itertext()))


def parse_jats(xml_bytes: bytes, max_section_chars: int = 12000) -> dict[str, Any]:
    root = ET.fromstring(xml_bytes)
    title = ""
    abstract = ""
    sections: list[dict[str, str]] = []
    for el in root.iter():
        tag = local_name(el.tag)
        if tag == "article-title" and not title:
            title = text_of(el)
        elif tag == "abstract" and not abstract:
            abstract = text_of(el)
    body = None
    for el in root.iter():
        if local_name(el.tag) == "body":
            body = el
            break
    if body is not None:
        for sec in body:
            if local_name(sec.tag) != "sec":
                continue
            sec_title = ""
            paras = []
            for child in sec:
                tag = local_name(child.tag)
                if tag == "title" and not sec_title:
                    sec_title = text_of(child)
                elif tag == "p":
                    t = text_of(child)
                    if t:
                        paras.append(t)
                elif tag == "sec":
                    # nested subsection: flatten its paragraphs
                    sub_title = ""
                    for sub in child:
                        if local_name(sub.tag) == "title" and not sub_title:
                            sub_title = text_of(sub)
                        elif local_name(sub.tag) == "p":
                            t = text_of(sub)
                            if t:
                                paras.append((sub_title + ": " if sub_title else "") + t)
            text = "\n\n".join(paras).strip()
            if text:
                sections.append({"title": sec_title or "正文", "text": text[:max_section_chars]})
    return {"title": title, "abstract": abstract, "sections": sections}


def find_epmc(doi: str) -> dict[str, Any] | None:
    query = f'DOI:"{doi}"'
    params = {"query": query, "format": "json", "resultType": "core", "pageSize": "5"}
    try:
        data = request_json(EPMC_SEARCH + "?" + urllib.parse.urlencode(params), timeout=60, retries=2)
    except Exception:
        return None
    results = (data.get("resultList") or {}).get("result") or []
    for r in results:
        if normalize_doi(r.get("doi")) == doi:
            return r
    return results[0] if results else None


def openalex_oa(doi: str) -> dict[str, Any]:
    try:
        data = request_json(OPENALEX.format(doi=urllib.parse.quote(doi, safe="")), timeout=60, retries=2)
    except Exception:
        return {}
    oa = data.get("open_access") or {}
    loc = data.get("primary_location") or {}
    return {
        "is_oa": bool(oa.get("is_oa")),
        "oa_status": oa.get("oa_status"),
        "oa_url": oa.get("oa_url"),
        "landing_page_url": loc.get("landing_page_url"),
        "pdf_url": loc.get("pdf_url"),
        "source": (loc.get("source") or {}).get("display_name"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch open-access full text")
    parser.add_argument("--doi", required=True)
    parser.add_argument("--max-section-chars", type=int, default=12000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    logger = setup_logging("fulltext", verbose=not args.json)
    ensure_dirs()
    FULLTEXT_DIR.mkdir(parents=True, exist_ok=True)
    doi = normalize_doi(args.doi)
    cache_path = FULLTEXT_DIR / f"{safe_slug(doi)}.json"
    if cache_path.exists():
        cached = load_json(cache_path)
        print(json.dumps(cached, ensure_ascii=False, indent=2))
        return 0

    oa = openalex_oa(doi)
    record: dict[str, Any] = {
        "doi": doi,
        "fetched_at": now_iso(),
        "available": False,
        "source": None,
        "fulltext_url": None,
        "reason": None,
        "openalex": oa,
        "title": "",
        "abstract": "",
        "sections": [],
    }
    epmc = find_epmc(doi)
    if epmc and epmc.get("pmcid"):
        pmcid = epmc["pmcid"]
        try:
            xml_bytes = fetch_bytes(EPMC_XML.format(pmcid=pmcid))
            parsed = parse_jats(xml_bytes, args.max_section_chars)
            record.update({
                "available": True,
                "source": "Europe PMC",
                "fulltext_url": f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
                "pmcid": pmcid,
                "title": parsed["title"] or epmc.get("title", ""),
                "abstract": parsed["abstract"] or clean_markup(epmc.get("abstractText", "")),
                "sections": parsed["sections"],
            })
        except Exception as exc:
            record["reason"] = f"Europe PMC full text fetch failed: {exc}"
    else:
        record["reason"] = "Europe PMC 未收录开放全文"

    if not record["available"] and oa.get("oa_url"):
        record["reason"] = (record["reason"] or "") + "；OpenAlex 提供开放获取链接，可用 web_fetch 读取"
        record["fulltext_url"] = oa["oa_url"]

    atomic_write_json(cache_path, record)
    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        logger.info("DOI: %s", doi)
        logger.info("Available: %s", record["available"])
        logger.info("Source: %s", record["source"])
        logger.info("URL: %s", record["fulltext_url"] or "none")
        logger.info("Reason: %s", record["reason"] or "ok")
        logger.info("Sections: %s", ", ".join(s["title"] for s in record["sections"][:12]))
        logger.info("Cache: %s", cache_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
