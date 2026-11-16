#!/usr/bin/env python
"""Print a compact reading list for the Agent (ranked papers + abstracts)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import CANDIDATE_DIR, load_json, setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Peek at ranked candidates")
    parser.add_argument("--candidates", help="Candidates JSON (default: latest)")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--start", type=int, default=1, help="1-based first rank to show")
    parser.add_argument("--abstract-chars", type=int, default=900)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    setup_logging("peek", verbose=False)
    if args.candidates:
        path = Path(args.candidates)
    else:
        files = sorted(CANDIDATE_DIR.glob("*.json"))
        if not files:
            raise SystemExit("No candidates found; run filter_papers.py first")
        path = files[-1]
    cand = load_json(path)
    rows = []
    start = max(0, args.start - 1)
    for p in cand.get("ranked", [])[start:start + args.top]:
        oa = (p.get("openalex") or {}).get("oa_url") or ""
        rows.append({
            "rank": p.get("rank"),
            "score": p.get("score", {}).get("total"),
            "subscores": {
                k: p.get("score", {}).get(k)
                for k in ("relevance", "innovation", "materials_and_process", "results", "journal")
            },
            "title": p.get("title"),
            "journal": p.get("journal"),
            "date": p.get("published_online") or p.get("effective_date"),
            "direction": p.get("direction"),
            "doi": p.get("doi"),
            "doi_url": p.get("doi_url"),
            "publisher_url": p.get("publisher_url"),
            "oa_url": oa,
            "flags": {k: v.get("hits", []) for k, v in (p.get("flags") or {}).items()},
            "abstract": (p.get("abstract") or "")[: args.abstract_chars],
        })
    if args.json:
        print(json.dumps({"candidates": str(path), "window": cand.get("window"), "stats": cand.get("stats"), "papers": rows}, ensure_ascii=False, indent=2))
        return 0
    print(f"Candidates: {path}")
    print(f"Window: {cand.get('window',{}).get('since')} .. {cand.get('window',{}).get('until')} / stats: {json.dumps(cand.get('stats',{}), ensure_ascii=False)}")
    for r in rows:
        print("\n" + "=" * 100)
        print(f"#{r['rank']}  {r['score']}  {r['journal']}  {r['date']}  [{r['direction']}]")
        print(r["title"])
        print(f"DOI: {r['doi']}  OA: {r['oa_url'] or 'none'}")
        print(f"Subscores: {r['subscores']}")
        print(f"Flags: {json.dumps(r['flags'], ensure_ascii=False)}")
        print(f"Abstract: {r['abstract']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
