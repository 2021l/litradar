#!/usr/bin/env python
"""Prepare an analysis worksheet for the Agent (no invented content)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (
    ANALYSIS_DIR,
    CANDIDATE_DIR,
    atomic_write_json,
    ensure_dirs,
    load_json,
    now_iso,
    setup_logging,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create analysis worksheet")
    parser.add_argument("--candidates", help="Candidates JSON (default: latest)")
    parser.add_argument("--output", help="Output path")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    setup_logging("analysis", verbose=False)
    ensure_dirs()

    if args.candidates:
        cand_path = Path(args.candidates)
    else:
        files = sorted(CANDIDATE_DIR.glob("*.json"))
        if not files:
            raise SystemExit("No candidates JSON found; run fetch and filter first")
        cand_path = files[-1]
    cand = load_json(cand_path)
    ranked = cand.get("ranked", [])[: args.top]
    top_table = [p["doi"] for p in ranked]
    top_picks = top_table[:5]

    papers = {}
    for p in ranked:
        papers[p["doi"]] = {
            "title_en": p.get("title", ""),
            "title_cn": "",
            "authors": p.get("authors", []),
            "journal": p.get("journal", ""),
            "published_online": p.get("published_online"),
            "doi_url": p.get("doi_url"),
            "publisher_url": p.get("publisher_url"),
            "abstract": p.get("abstract", ""),
            "machine_score": p.get("score", {}).get("total"),
            "machine_subscores": {
                k: p.get("score", {}).get(k)
                for k in ("relevance", "innovation", "materials_and_process", "results", "journal")
            },
            "direction": p.get("direction", ""),
            "flags": {k: v.get("hits", []) for k, v in (p.get("flags") or {}).items()},
            "final_score": None,
            "grade": "",
            "one_line": "",
            "background": "",
            "question": "",
            "innovations": [],
            "paper_type": "Research Article",
            "parameters": [],
            "results": [],
            "mechanism": "",
            "limitations": [],
            "inspiration": [],
            "evidence_level": "",
            "fulltext_url": "",
            "source_quote": "",
            "original_vs_inference": [],
        }

    worksheet = {
        "schema_version": 1,
        "status": "TEMPLATE_NOT_ANALYSIS",
        "generated_at": now_iso(),
        "source_candidates": str(cand_path),
        "report_date": cand.get("window", {}).get("until"),
        "window": cand.get("window", {}),
        "counts": cand.get("stats", {}),
        "_instructions": [
            "把本文件复制为 database/analysis/<until>.json 后填写；不要直接改模板。",
            "top_table 最多 10 篇，top_picks 最多 5 篇；不足时按实际数量，不凑数。",
            "中文标题、创新点、机理、局限性和启发必须由你阅读摘要/全文后写；不得编造。",
            "evidence_level 只能是 abstract_only 或 full_text；abstract_only 时不得写摘要中没有的数字。",
            "参数缺失用“原文未披露”或“摘要未披露；需查全文”，不要猜测旋涂速度、浓度、退火温度。",
            "原文事实与推理必须分开：original_vs_inference 列出原文结论和你自己的推论。",
            "trends 写 3–5 条，并用 evidence_dois 指向本次候选池中的真实 DOI。",
            "完成后运行 validate_analysis.py，再用 generate_report.py --finalize 生成正式周报。",
        ],
        "trends": [],
        "top_table": top_table,
        "top_picks": top_picks,
        "papers": papers,
        "sections": {"pedot": "", "sensor": "", "extreme": ""},
        "methods_table": [],
        "comparisons": [],
        "opportunities": [],
        "next_keywords": [],
        "limitations": [],
    }

    until = cand.get("window", {}).get("until") or "unknown"
    output = Path(args.output) if args.output else ANALYSIS_DIR / f"{until}.template.json"
    atomic_write_json(output, worksheet)
    print(json.dumps({
        "ok": True,
        "output": str(output),
        "top_table": len(top_table),
        "top_picks": len(top_picks),
        "candidates": str(cand_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
