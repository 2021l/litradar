#!/usr/bin/env python
"""Flatten verified process parameters from analysis JSON into a queryable store."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from common import (
    DATABASE_DIR,
    atomic_write_json,
    load_json,
    normalize_doi,
    setup_logging,
)

PARAM_JSONL = DATABASE_DIR / "parameters.jsonl"
PARAM_CSV = DATABASE_DIR / "parameters.csv"

FIELDS = [
    "doi", "title", "title_cn", "journal", "published_online", "report_date",
    "material", "process", "parameter", "value", "source", "evidence_level",
]


def load_existing() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not PARAM_JSONL.exists():
        return rows
    with PARAM_JSONL.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            key = "|".join(str(row.get(k, "")) for k in ("doi", "parameter", "value"))
            rows[key] = row
    return rows


def export(analysis_path: Path, candidates_path: Path, report_date: str | None = None) -> int:
    analysis = load_json(analysis_path) or {}
    candidates = load_json(candidates_path) or {}
    known = {p["doi"]: p for p in candidates.get("papers", [])}
    rows = load_existing()
    added = 0
    for doi, item in (analysis.get("papers") or {}).items():
        nd = normalize_doi(doi)
        p = known.get(nd, {})
        if not p:
            continue
        evidence = item.get("evidence_level", "")
        for param in item.get("parameters") or []:
            if not isinstance(param, dict):
                continue
            name = str(param.get("item") or param.get("name") or "").strip()
            value = str(param.get("value") or "").strip()
            if not name or not value:
                continue
            if any(x in value for x in ("未披露", "未核实", "未提取", "待查")):
                continue
            row = {
                "doi": nd,
                "title": p.get("title", ""),
                "title_cn": item.get("title_cn", ""),
                "journal": p.get("journal", ""),
                "published_online": p.get("published_online") or p.get("effective_date"),
                "report_date": report_date or analysis.get("report_date"),
                "material": (
                    param.get("material")
                    or item.get("material")
                    or (value if ("材料" in name or "基底" in name) else "")
                ),
                "process": param.get("process") or item.get("process") or "",
                "parameter": name,
                "value": value,
                "source": param.get("source") or ("摘要" if evidence == "abstract_only" else "原文"),
                "evidence_level": evidence,
            }
            key = "|".join(str(row.get(k, "")) for k in ("doi", "parameter", "value"))
            if key not in rows:
                rows[key] = row
                added += 1
    ordered = sorted(rows.values(), key=lambda r: (r.get("report_date", ""), r.get("doi", ""), r.get("parameter", "")))
    with PARAM_JSONL.open("w", encoding="utf-8", newline="\n") as fh:
        for row in ordered:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with PARAM_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(ordered)
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description="Export structured parameters")
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--report-date")
    args = parser.parse_args()
    setup_logging("params", verbose=False)
    added = export(Path(args.analysis), Path(args.candidates), args.report_date)
    print(json.dumps({"ok": True, "added": added, "jsonl": str(PARAM_JSONL), "csv": str(PARAM_CSV)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
