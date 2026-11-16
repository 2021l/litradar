#!/usr/bin/env python
"""Validate an Agent-written analysis file against the candidate pool.

Hard failures protect against invented DOIs and inconsistent rankings.
Soft warnings flag claims that cannot be found in the public abstract.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import load_json, normalize_doi, setup_logging


class ValidationError(Exception):
    pass


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text or ""))


def _value_numbers(value: Any) -> set[str]:
    return _numbers(str(value))


def validate(
    analysis: dict[str, Any],
    candidates: dict[str, Any],
    *,
    strict: bool = True,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    known = {normalize_doi(p.get("doi")): p for p in candidates.get("papers", [])}
    ranked = {normalize_doi(p.get("doi")) for p in candidates.get("ranked", [])}

    if not isinstance(analysis, dict):
        raise ValidationError("analysis must be a JSON object")

    top_table = [normalize_doi(d) for d in analysis.get("top_table", [])]
    top_picks = [normalize_doi(d) for d in analysis.get("top_picks", [])]
    papers = analysis.get("papers") or {}

    if not top_table:
        errors.append("top_table 为空：至少给出 1 篇论文（不足 10 篇时按实际数量）")
    if len(top_table) > 10:
        errors.append("top_table 超过 10 篇；高质量论文不足时不得凑数，也不得超编")
    if len(set(top_table)) != len(top_table):
        errors.append("top_table 存在重复 DOI")
    if len(top_picks) > 5:
        errors.append("top_picks 最多 5 篇")
    if len(set(top_picks)) != len(top_picks):
        errors.append("top_picks 存在重复 DOI")
    if not set(top_picks).issubset(set(top_table)):
        errors.append("top_picks 必须是 top_table 的子集")

    for doi in top_table:
        if doi not in known:
            errors.append(f"top_table DOI 不在本次候选池中: {doi}")
        elif doi not in ranked:
            errors.append(f"top_table DOI 未通过筛选（综述/无摘要/重复/已推荐）: {doi}")
    for doi in top_picks:
        if doi not in known:
            errors.append(f"top_picks DOI 不在候选池中: {doi}")

    for doi, item in papers.items():
        nd = normalize_doi(doi)
        if nd not in known:
            errors.append(f"papers 中存在候选池之外的 DOI: {doi}")
            continue
        p = known[nd]
        if not isinstance(item, dict):
            errors.append(f"{doi}: 分析项必须是对象")
            continue
        if nd in top_picks:
            for field in ("title_cn", "one_line", "background", "question", "mechanism"):
                if not str(item.get(field, "")).strip():
                    errors.append(f"{doi}: 缺少必填字段 {field}")
            if not item.get("innovations"):
                errors.append(f"{doi}: 缺少核心创新点 innovations")
            if not item.get("limitations"):
                errors.append(f"{doi}: 缺少局限性 limitations")
            if not item.get("inspiration"):
                errors.append(f"{doi}: 缺少科研启发 inspiration")
            if item.get("evidence_level") not in ("abstract_only", "full_text"):
                errors.append(f"{doi}: evidence_level 必须是 abstract_only 或 full_text")
            score = item.get("final_score")
            if not isinstance(score, (int, float)) or not 0 <= score <= 100:
                errors.append(f"{doi}: final_score 必须是 0-100 的数字")
            if not str(item.get("grade", "")).strip():
                errors.append(f"{doi}: 缺少 grade")

            if item.get("evidence_level") == "abstract_only":
                abstract_nums = _numbers(p.get("abstract", ""))
                for group in ("results", "parameters"):
                    for row in item.get(group, []) or []:
                        value = row.get("value") if isinstance(row, dict) else row
                        if not value:
                            continue
                        sval = str(value)
                        if any(marker in sval for marker in ("未披露", "未核实", "未提取", "待查", "N/A")):
                            continue
                        missing = _value_numbers(value) - abstract_nums
                        if missing:
                            warnings.append(
                                f"{doi}: {group} 中数值 {sorted(missing)} 未在公开摘要中出现，"
                                "请确认来源或标注为未核实"
                            )
                if item.get("results") and not item.get("source_quote"):
                    warnings.append(f"{doi}: abstract_only 分析缺少 source_quote（建议附摘要原句）")
            elif item.get("evidence_level") == "full_text":
                if not item.get("fulltext_url"):
                    warnings.append(f"{doi}: full_text 分析缺少 fulltext_url")
                for row in item.get("results", []) or []:
                    if isinstance(row, dict) and not row.get("source_quote"):
                        warnings.append(f"{doi}: 全文结果缺少 source_quote，难以核验")

    trends = analysis.get("trends") or []
    if not 3 <= len(trends) <= 5:
        warnings.append(f"trends 应为 3-5 条，当前 {len(trends)} 条")
    for t in trends:
        for doi in t.get("evidence_dois", []) or []:
            if normalize_doi(doi) not in known:
                errors.append(f"trends 引用了候选池之外的 DOI: {doi}")

    for comp in analysis.get("comparisons", []) or []:
        for doi in comp.get("papers", []) or []:
            if normalize_doi(doi) not in known:
                errors.append(f"comparisons 引用了候选池之外的 DOI: {doi}")
    for opp in analysis.get("opportunities", []) or []:
        for doi in opp.get("evidence_dois", []) or []:
            if normalize_doi(doi) not in known:
                errors.append(f"opportunities 引用了候选池之外的 DOI: {doi}")

    if strict and errors:
        raise ValidationError("; ".join(errors))
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate analysis JSON")
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    setup_logging("validate", verbose=False)
    analysis = load_json(Path(args.analysis))
    candidates = load_json(Path(args.candidates))
    try:
        errors, warnings = validate(analysis, candidates, strict=False)
    except ValidationError as exc:
        errors, warnings = [str(exc)], []
    result = {"ok": not errors, "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("OK" if not errors else "FAILED")
        for e in errors:
            print("ERROR:", e)
        for w in warnings:
            print("WARN:", w)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
