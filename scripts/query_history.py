#!/usr/bin/env python
"""Query the historical paper database by week, journal, direction or material."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import DATABASE_DIR, load_json, setup_logging

DB = DATABASE_DIR / "papers.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Query reported papers")
    parser.add_argument("--week", help="Report date, e.g. 2026-11-16")
    parser.add_argument("--journal", help="Journal name substring")
    parser.add_argument("--direction", help="Direction id/label substring")
    parser.add_argument("--material", help="Material/title substring, e.g. PEDOT, MXene")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    setup_logging("history", verbose=False)
    db = load_json(DB, default={}) or {}
    papers = list((db.get("papers") or {}).values())

    def keep(r: dict) -> bool:
        if args.week and str(r.get("report_date", ""))[:10] != args.week:
            return False
        if args.journal and args.journal.lower() not in str(r.get("journal", "")).lower():
            return False
        if args.direction and args.direction.lower() not in str(r.get("direction", "")).lower():
            return False
        if args.material:
            hay = f"{r.get('title','')} {r.get('direction','')}".lower()
            if args.material.lower() not in hay:
                return False
        return True

    rows = [r for r in papers if keep(r)]
    rows.sort(key=lambda r: (str(r.get("report_date", "")), r.get("score") or 0), reverse=True)
    rows = rows[: args.limit]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("没有匹配的历史论文。")
        return 0
    print(f"匹配 {len(rows)} 篇（最多显示 {args.limit} 篇）\n")
    print(f"{'报告日期':<12} {'期刊':<32} {'评分':>5}  标题")
    print("-" * 110)
    for r in rows:
        print(f"{str(r.get('report_date',''))[:10]:<12} {str(r.get('journal',''))[:30]:<32} {str(r.get('score','')):>5}  {r.get('title','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
