#!/usr/bin/env python
"""DOI-first deduplication and historical literature database."""

from __future__ import annotations

import argparse
import difflib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from common import (
    DATABASE_DIR,
    atomic_write_json,
    load_json,
    normalize_doi,
    normalize_title,
    now_iso,
    setup_logging,
)

DB_PATH = DATABASE_DIR / "papers.json"


def empty_db() -> dict[str, Any]:
    return {"schema_version": 1, "updated_at": None, "papers": {}}


def load_db() -> dict[str, Any]:
    db = load_json(DB_PATH, default=None)
    if not db or not isinstance(db, dict):
        return empty_db()
    db.setdefault("schema_version", 1)
    db.setdefault("papers", {})
    return db


def save_db(db: dict[str, Any]) -> None:
    db["updated_at"] = now_iso()
    atomic_write_json(DB_PATH, db)


def find_title_match(title: str, db: dict[str, Any], threshold: float = 0.92) -> str | None:
    norm = normalize_title(title)
    if not norm:
        return None
    for doi, rec in db.get("papers", {}).items():
        other = rec.get("title_norm") or normalize_title(rec.get("title", ""))
        if not other:
            continue
        ratio = difflib.SequenceMatcher(None, norm, other).ratio()
        if ratio >= threshold:
            return doi
    return None


def annotate(paper: dict[str, Any], db: dict[str, Any]) -> dict[str, Any]:
    doi = normalize_doi(paper.get("doi"))
    rec = db.get("papers", {}).get(doi) if doi else None
    if not rec and not doi:
        alt = find_title_match(paper.get("title", ""), db, 0.96)
        rec = db.get("papers", {}).get(alt) if alt else None
    if not rec:
        return {"status": "new", "record": None}
    oa = paper.get("openalex") or {}
    if rec.get("status") == "reported" or rec.get("reported"):
        if oa.get("is_retracted") or rec.get("status") == "retracted":
            return {"status": "retraction_alert", "record": rec}
        return {"status": "already_reported", "record": rec}
    return {"status": "seen_before", "record": rec}


def mark_reported(
    papers: list[dict[str, Any]],
    report_path: str,
    report_date: str,
    db: dict[str, Any],
    analysis_meta: dict[str, Any] | None = None,
) -> None:
    now = now_iso()
    for p in papers:
        doi = normalize_doi(p.get("doi"))
        if not doi:
            continue
        rec = db["papers"].get(doi)
        if not rec:
            rec = {
                "doi": doi,
                "title": p.get("title", ""),
                "title_norm": normalize_title(p.get("title", "")),
                "journal": p.get("journal", ""),
                "journal_id": p.get("journal_id", ""),
                "published_online": p.get("published_online") or p.get("effective_date"),
                "first_seen": now,
                "times_seen": 0,
            }
            db["papers"][doi] = rec
        rec["last_seen"] = now
        rec["times_seen"] = int(rec.get("times_seen", 0)) + 1
        rec["status"] = "reported"
        rec["reported"] = True
        rec["report_file"] = report_path
        rec["report_date"] = report_date
        rec["direction"] = p.get("direction") or p.get("primary_direction")
        rec["score"] = p.get("score", {}).get("total") if isinstance(p.get("score"), dict) else p.get("score")
        rec["recommendation"] = p.get("recommendation") or p.get("score", {}).get("band")
        if analysis_meta and doi in (analysis_meta.get("papers_by_doi") or {}):
            meta = analysis_meta["papers_by_doi"][doi] or {}
            if meta.get("score") is not None:
                rec["score"] = meta["score"]
            if meta.get("grade"):
                rec["recommendation"] = meta["grade"]
            rec["analysis"] = meta
    save_db(db)


def scan_updates(papers: list[dict[str, Any]], db: dict[str, Any]) -> list[dict[str, Any]]:
    """Return alerts for retractions/corrections affecting previously reported papers."""
    alerts = []
    for p in papers:
        doi = normalize_doi(p.get("doi"))
        oa = p.get("openalex") or {}
        if oa.get("is_retracted") and doi in db.get("papers", {}):
            alerts.append({"doi": doi, "type": "retraction", "title": p.get("title")})
        for upd in p.get("update_to", []) or []:
            target = normalize_doi(upd.get("doi"))
            if target and target in db.get("papers", {}):
                alerts.append(
                    {
                        "doi": doi,
                        "target_doi": target,
                        "type": upd.get("type") or "update",
                        "title": p.get("title"),
                    }
                )
    return alerts


def cmd_check(args: argparse.Namespace) -> int:
    db = load_db()
    doi = normalize_doi(args.doi)
    rec = db.get("papers", {}).get(doi)
    if rec:
        print(json.dumps({"found": True, "record": rec}, ensure_ascii=False, indent=2))
    else:
        alt = find_title_match(args.title or "", db)
        print(json.dumps({"found": bool(alt), "matched_doi": alt}, ensure_ascii=False, indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    db = load_db()
    papers = db.get("papers", {})
    by_status: dict[str, int] = {}
    by_journal: dict[str, int] = {}
    for rec in papers.values():
        by_status[rec.get("status", "unknown")] = by_status.get(rec.get("status", "unknown"), 0) + 1
        by_journal[rec.get("journal", "?")] = by_journal.get(rec.get("journal", "?"), 0) + 1
    print(json.dumps({
        "total": len(papers),
        "by_status": by_status,
        "by_journal": dict(sorted(by_journal.items(), key=lambda x: -x[1])),
        "updated_at": db.get("updated_at"),
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Historical paper database utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check", help="Check whether a DOI/title was reported")
    p_check.add_argument("--doi", default="")
    p_check.add_argument("--title", default="")
    p_check.set_defaults(func=cmd_check)
    p_stats = sub.add_parser("stats", help="Show database statistics")
    p_stats.set_defaults(func=cmd_stats)
    args = parser.parse_args()
    setup_logging("dedup", verbose=False)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
