#!/usr/bin/env python
"""Query the structured process-parameter store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import DATABASE_DIR, setup_logging

PARAM_JSONL = DATABASE_DIR / "parameters.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Query structured parameters")
    parser.add_argument("--material", help="e.g. PEDOT, MXene, PDMS")
    parser.add_argument("--process", help="e.g. spin, blade, transfer")
    parser.add_argument("--parameter", help="e.g. thickness, annealing")
    parser.add_argument("--doi")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    setup_logging("params-query", verbose=False)
    if not PARAM_JSONL.exists():
        print("参数库为空；先运行 export_parameters.py。")
        return 0
    rows = []
    with PARAM_JSONL.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            hay = " ".join(str(r.get(k, "")) for k in ("material", "parameter", "value", "title", "title_cn")).lower()
            if args.material and args.material.lower() not in hay:
                continue
            if args.process and args.process.lower() not in " ".join(str(r.get(k, "")) for k in ("process", "parameter", "value")).lower():
                continue
            if args.parameter and args.parameter.lower() not in " ".join(str(r.get(k, "")) for k in ("parameter", "value")).lower():
                continue
            if args.doi and args.doi.lower() not in str(r.get("doi", "")).lower():
                continue
            rows.append(r)
    rows = rows[: args.limit]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("没有匹配的参数记录。")
        return 0
    print(f"匹配 {len(rows)} 条\n")
    print(f"{'材料':<18} {'参数':<24} {'值':<28} {'来源':<6} 论文")
    print("-" * 120)
    for r in rows:
        print(f"{str(r.get('material',''))[:16]:<18} {str(r.get('parameter',''))[:22]:<24} {str(r.get('value',''))[:26]:<28} {str(r.get('source',''))[:5]:<6} {r.get('title','')[:50]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
