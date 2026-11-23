#!/usr/bin/env python
"""Health check for configs, APIs, state and the historical database."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from pathlib import Path

from common import (
    DATABASE_DIR,
    REPORTS_DIR,
    ROOT,
    STATE_DIR,
    journal_index,
    load_json,
    load_keywords,
    load_profile,
    load_scoring,
    load_yaml,
    request_json,
    setup_logging,
)

STATE = STATE_DIR / "last_run.json"
DB = DATABASE_DIR / "papers.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Radar health check")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    setup_logging("health", verbose=False)
    errors: list[str] = []
    warnings: list[str] = []
    info: dict = {}

    try:
        jcfg = load_yaml("journals.yaml")
        kw = load_yaml("keywords.yaml")
        sc = load_yaml("scoring.yaml")
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [f"YAML parse failed: {exc}"]}, ensure_ascii=False, indent=2))
        return 1

    journals = jcfg.get("journals", [])
    enabled = [j for j in journals if j.get("enabled", True)]
    ids = [j["id"] for j in enabled]
    if len(ids) != len(set(ids)):
        errors.append("journals.yaml 存在重复 id")
    for j in enabled:
        if not j.get("issn") and not j.get("query"):
            warnings.append(f"{j.get('id')}: 未填 ISSN，将按刊名检索（较慢，可能误收同名刊物）")
        if j.get("tier") not in ("A", "B", "C", "R"):
            errors.append(f"{j.get('id')}: tier 非法")
    info["journals"] = len(enabled)

    caps = [int(d.get("cap", 0)) for d in kw.get("directions", [])]
    relevance_max = int((sc.get("weights", {}) or {}).get("relevance", 30))
    if sum(caps) != relevance_max:
        warnings.append(
            f"keywords.yaml 各方向 cap 之和为 {sum(caps)}，"
            f"与 scoring.yaml 相关性满分 {relevance_max} 不一致"
        )
    info["direction_caps"] = caps

    weights = sc.get("weights", {})
    if sum(int(v) for v in weights.values()) != 100:
        errors.append(f"scoring.yaml 权重之和为 {sum(int(v) for v in weights.values())}，应为 100")
    info["weights"] = weights

    db = load_json(DB, default={}) or {}
    papers = db.get("papers", {})
    if not isinstance(papers, dict):
        errors.append("database/papers.json 结构异常")
    for doi, rec in (papers or {}).items():
        if not doi.startswith("10."):
            errors.append(f"历史库 DOI 格式异常: {doi}")
            break
    reported = [r for r in papers.values() if r.get("reported")]
    info["db_total"] = len(papers)
    info["db_reported"] = len(reported)

    state = load_json(STATE, default={}) or {}
    info["last_run"] = {
        "status": state.get("status"),
        "last_success": state.get("last_success"),
        "last_report": state.get("last_report"),
        "consecutive_failures": state.get("consecutive_failures", 0),
    }
    if state.get("status") == "failed":
        warnings.append(f"最近一次运行失败: {state.get('last_error')}")
    if state.get("consecutive_failures", 0) >= 2:
        warnings.append(f"连续失败 {state['consecutive_failures']} 次，请检查日志")

    prefix = (load_profile().get("report") or {}).get("prefix", "Literature_Radar_Weekly_Report")
    reports = sorted(REPORTS_DIR.glob(f"{prefix}_*.md"))
    info["reports"] = len(reports)
    info["latest_report"] = str(reports[-1]) if reports else None

    if not args.no_network:
        checks = {}
        probe_journal = next((j for j in enabled if j.get("issn")), None)
        if probe_journal is None:
            checks["crossref"] = {"ok": None, "note": "白名单中没有 ISSN，跳过 Crossref 探测"}
        else:
            try:
                data = request_json(
                    "https://api.crossref.org/works?" + urllib.parse.urlencode({
                        "filter": f"issn:{probe_journal['issn'][0]},from-pub-date:2020-01-01",
                        "rows": "1",
                        "select": "DOI",
                        "mailto": "radar@example.org",
                    }),
                    timeout=30, retries=3,
                )
                checks["crossref"] = {"ok": True, "total": data.get("message", {}).get("total-results")}
            except Exception as exc:
                checks["crossref"] = {"ok": False, "error": str(exc)}
                warnings.append(f"Crossref 探测失败（可能是瞬时网络问题）: {exc}")
        try:
            data = request_json(
                "https://api.openalex.org/works?" + urllib.parse.urlencode({
                    "per-page": "1",
                    "mailto": "radar@example.org",
                }),
                timeout=30, retries=3,
            )
            checks["openalex"] = {"ok": True, "count": data.get("meta", {}).get("count")}
        except Exception as exc:
            checks["openalex"] = {"ok": False, "error": str(exc)}
            warnings.append(f"OpenAlex 探测失败（可能是瞬时网络问题）: {exc}")
        info["network"] = checks

    result = {"ok": not errors, "errors": errors, "warnings": warnings, "info": info, "root": str(ROOT)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
