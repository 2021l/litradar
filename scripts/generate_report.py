#!/usr/bin/env python
"""Render the Chinese weekly report from candidates + Agent analysis.

Without --finalize the report is a preview/draft and does not update history.
With --finalize the report is validated, written, and the reported papers are
recorded in database/papers.json.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from common import (
    ANALYSIS_DIR,
    CANDIDATE_DIR,
    REPORTS_DIR,
    ROOT,
    STATE_DIR,
    atomic_write_json,
    atomic_write_text,
    ensure_dirs,
    issue_number,
    journal_index,
    load_json,
    load_keywords,
    load_profile,
    load_scoring,
    normalize_doi,
    now_iso,
    setup_logging,
    short_authors,
    term_present,
    today,
)
from deduplicate import load_db, mark_reported
from validate_analysis import ValidationError, validate
from export_parameters import export as export_parameters

TEMPLATE = ROOT / "templates" / "weekly_report.md"
STATE_PATH = STATE_DIR / "last_run.json"

PROFILE = load_profile()


def subtitle_md() -> str:
    meta = PROFILE.get("meta") or {}
    report = PROFILE.get("report") or {}
    field = report.get("field") or "自定义研究领域"
    return f"{meta.get('display_name_en', 'Literature Radar')} · 面向 {field}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Chinese weekly literature report")
    p.add_argument("--candidates", help="Candidates JSON (default: latest)")
    p.add_argument("--analysis", help="Agent analysis JSON")
    p.add_argument("--output", help="Output Markdown path")
    p.add_argument("--draft", action="store_true", help="Allow generation without analysis")
    p.add_argument("--finalize", action="store_true", help="Validate, mark papers reported, update state")
    p.add_argument("--force", action="store_true", help="Overwrite an existing report (history preservation override)")
    p.add_argument("--issue", type=int, help="Issue number override")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args()


def pick_candidates(args: argparse.Namespace) -> Path:
    if args.candidates:
        return Path(args.candidates)
    files = sorted(CANDIDATE_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No candidate files in {CANDIDATE_DIR}")
    return files[-1]


def pick_analysis(args: argparse.Namespace, cand: dict[str, Any]) -> Path | None:
    if args.analysis:
        return Path(args.analysis)
    if args.finalize:
        until = cand.get("window", {}).get("until")
        candidate = ANALYSIS_DIR / f"{until}.json"
        if candidate.exists():
            return candidate
        return None
    return None


def item_for(analysis: dict[str, Any] | None, doi: str) -> dict[str, Any]:
    if not analysis:
        return {}
    return (analysis.get("papers") or {}).get(doi, {}) or {}


def band_for(score: float, scoring: dict[str, Any]) -> str:
    for b in scoring.get("bands", []):
        if score >= b["min"]:
            return b["label"]
    return "暂不推荐"


def fmt_date(p: dict[str, Any]) -> str:
    return p.get("published_online") or p.get("effective_date") or p.get("issued") or "未核实"


def link_cell(p: dict[str, Any]) -> str:
    doi = p.get("doi", "")
    url = p.get("doi_url") or ("https://doi.org/" + doi if doi else "")
    pub = p.get("publisher_url") or url
    cell = f"[DOI]({url})"
    if pub and pub != url:
        cell += f" · [原文]({pub})"
    return cell


def journal_metric_text(p: dict[str, Any], jmap: dict[str, dict[str, Any]]) -> str:
    j = jmap.get(p.get("journal_id", ""), {})
    metrics = j.get("metrics") or {}
    if metrics.get("impact_factor"):
        return f"{metrics['impact_factor']}（{metrics.get('impact_factor_year', '年份未注明')}，{metrics.get('source', '来源未注明')}）"
    return "未核实（本次未接入 JCR / 中科院分区数据）"


def authors_text(p: dict[str, Any], limit: int = 6) -> str:
    authors = p.get("authors") or []
    return short_authors(authors, limit=limit) if authors else "作者未从 Crossref 元数据中获取"


def oa_note(p: dict[str, Any]) -> str:
    oa = (p.get("openalex") or {}).get("oa_url")
    return f" · [开放获取全文]({oa})" if oa else ""


def top_table_md(
    cand: dict[str, Any],
    analysis: dict[str, Any] | None,
    scoring: dict[str, Any],
    jmap: dict[str, dict[str, Any]],
    final: bool,
) -> tuple[str, list[str]]:
    known = {p["doi"]: p for p in cand.get("papers", [])}
    dois: list[str] = []
    if analysis and analysis.get("top_table"):
        dois = [normalize_doi(d) for d in analysis["top_table"]]
    else:
        dois = [p["doi"] for p in cand.get("ranked", [])[:10]]
    if not dois:
        return "_本周没有通过筛选的原创研究论文。_", []
    lines = [
        "| 排名 | 论文（中文 / 英文） | 期刊 | 在线发表 | 研究方向 | 综合评分 | 推荐等级 | 链接 |",
        "|:---:|---|---|---|---|:---:|---|---|",
    ]
    used = []
    for i, doi in enumerate(dois, 1):
        p = known.get(doi)
        if not p:
            continue
        item = item_for(analysis, doi)
        title_cn = str(item.get("title_cn") or "").strip()
        title_en = p.get("title", "")
        title = f"{title_cn}<br>*{title_en}*" if title_cn else f"*{title_en}*"
        if item.get("final_score") is not None:
            score = item["final_score"]
            grade = item.get("grade") or band_for(float(score), scoring)
        else:
            score = p.get("score", {}).get("total", 0)
            grade = p.get("score", {}).get("band", "待复核")
        if not final and item.get("final_score") is None:
            grade = f"{grade}（机器预评分）"
        lines.append(
            f"| {i} | {title} | {p.get('journal','')} | {fmt_date(p)} | "
            f"{item.get('direction') or p.get('direction','')} | **{score}** | {grade} | {link_cell(p)} |"
        )
        used.append(doi)
    return "\n".join(lines), used


def dashboard_md(cand: dict[str, Any], top_count: int, deep_count: int) -> str:
    st = cand.get("stats", {})
    return (
        "| 🔎 检索论文 | 🎯 相关论文 | ⭐ 重点精读 |\n"
        "|:---:|:---:|:---:|\n"
        f"| **{st.get('fetched', 0)}** | **{st.get('gate_pass', 0)}** | **{deep_count}** |\n\n"
        f"> 本周从 {cand.get('journals_queried', 0)} 本白名单期刊中检索，"
        f"TOP 表收录 {top_count} 篇，其中 {deep_count} 篇做深度精读。"
        "数量不代表质量，不足 10 篇时不凑数。"
    )


def overview_md(cand: dict[str, Any], top_count: int) -> str:
    st = cand.get("stats", {})
    w = cand.get("window", {})
    failed = cand.get("failed_sources") or []
    failed_txt = "；".join(f"{x.get('name')}: {x.get('error')}" for x in failed) if failed else "无"
    return "\n".join([
        "| 项目 | 内容 |",
        "|---|---|",
        f"| 检索日期 | {today().isoformat()}（Asia/Shanghai） |",
        f"| 检索时间范围 | {w.get('since','?')} 至 {w.get('until','?')}（{w.get('days','?')} 天） |",
        f"| 运行类型 | {'首次回溯' if w.get('first_run') else '增量检索（含 2 天重叠窗口）'} |",
        f"| 监测期刊数量 | {cand.get('journals_queried', 0)} 本（A/B/C/综述四层） |",
        f"| Crossref 去重后论文 | {st.get('fetched', 0)} 篇 |",
        f"| 有公开摘要 | {st.get('with_abstract', 0)} 篇 |",
        f"| 初筛通过 | {st.get('gate_pass', 0)} 篇 |",
        f"| 可进入主榜 | {st.get('rankable', 0)} 篇 |",
        f"| 最终推荐（TOP 表） | {top_count} 篇 |",
        f"| 综述观察 | {st.get('reviews', 0)} 篇 |",
        f"| 无摘要转待核验 | {st.get('metadata_only_appendix', 0)} 篇 |",
        f"| 历史已推荐（已排除） | {st.get('already_reported', 0)} 篇 |",
        f"| 数据源 | Crossref REST API；OpenAlex 摘要/开放获取信息 |",
        f"| 失败或部分失败的数据源 | {failed_txt} |",
        "",
        "> 说明：期刊影响因子和中科院分区本次未接入可核实数据源，统一标注“未核实”；"
        "期刊分仅占 15 分，且 A/B/C 三档分差有限，不能替代对论文创新性和实验证据的判断。",
    ])


def trends_md(analysis: dict[str, Any] | None, known: dict[str, dict[str, Any]]) -> str:
    trends = (analysis or {}).get("trends") or []
    if not trends:
        return "_待 Agent 阅读本周候选论文后补充 3–5 条趋势判断；本预览版不自动生成趋势结论。_"
    out = []
    for i, t in enumerate(trends, 1):
        title = t.get("title", f"趋势 {i}")
        summary = t.get("summary", "")
        evidence = []
        for doi in t.get("evidence_dois", []) or []:
            p = known.get(normalize_doi(doi))
            if p:
                evidence.append(f"[{p.get('journal','')}]({p.get('doi_url')})")
        ev = f"\n\n证据：{'；'.join(evidence)}" if evidence else ""
        out.append(f"### 2.{i} {title}\n\n{summary}{ev}")
    return "\n\n".join(out)


def bullet_list(value: Any, empty: str = "原文未披露") -> str:
    if not value:
        return f"- {empty}"
    if isinstance(value, str):
        return f"- {value}"
    out = []
    for x in value:
        if isinstance(x, dict):
            label = x.get("type") or x.get("label") or ""
            text = x.get("text") or x.get("summary") or ""
            out.append(f"- **{label}**：{text}" if label else f"- {text}")
        else:
            out.append(f"- {x}")
    return "\n".join(out)


def parameter_rows(item: dict[str, Any], evidence_level: str) -> list[dict[str, str]]:
    provided = item.get("parameters") or []
    rows: list[dict[str, str]] = []
    seen = set()
    for row in provided:
        if isinstance(row, dict):
            name = str(row.get("item") or row.get("name") or "").strip()
            value = str(row.get("value") or "").strip()
            source = str(row.get("source") or "").strip()
            note = str(row.get("note") or "").strip()
        else:
            name, value, source, note = str(row), "", "", ""
        if not name:
            continue
        rows.append({"item": name, "value": value or "原文未披露", "source": source or "原文", "note": note})
        seen.add(name)
    standard = (PROFILE.get("report") or {}).get("parameter_rows") or [
        "研究对象 / 体系", "关键材料 / 试剂", "关键参数 / 条件",
        "样本 / 数据规模", "方法 / 设备", "评价指标", "对照 / 基线",
    ]
    for name in standard:
        if name in seen:
            continue
        if evidence_level == "full_text":
            value = "原文未披露"
            source = "原文"
        else:
            value = "摘要未披露；需查全文"
            source = "未核验"
        rows.append({"item": name, "value": value, "source": source, "note": ""})
    return rows


def params_table_md(item: dict[str, Any], evidence_level: str) -> str:
    rows = parameter_rows(item, evidence_level)
    lines = ["| 参数 | 数值 / 条件 | 来源 | 备注 |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['item']} | {r['value']} | {r['source']} | {r['note']} |")
    return "\n".join(lines)


def results_table_md(item: dict[str, Any], evidence_level: str) -> str:
    results = item.get("results") or []
    if not results:
        return "_本次未提取到可核验的性能数据；不以推测填充。_"
    lines = ["| 性能指标 | 数值 | 测试条件 / 说明 | 来源 |", "|---|---|---|---|"]
    for r in results:
        if isinstance(r, dict):
            metric = r.get("metric") or r.get("name") or ""
            value = r.get("value") or ""
            note = r.get("note") or r.get("condition") or ""
            source = r.get("source") or ("摘要" if evidence_level == "abstract_only" else "原文")
        else:
            metric, value, note, source = str(r), "", "", ""
        lines.append(f"| {metric} | {value} | {note} | {source} |")
    return "\n".join(lines)


def origin_table_md(item: dict[str, Any]) -> str:
    pairs = item.get("original_vs_inference") or []
    if not pairs:
        return "_本次未逐条拆分原文事实与推理；阅读时请以原文为准。_"
    lines = ["| 原文事实 | Agent 推理（非原文结论） |", "|---|---|"]
    for pair in pairs:
        if isinstance(pair, dict):
            lines.append(f"| {pair.get('original','')} | {pair.get('inference','')} |")
        else:
            lines.append(f"| {pair} |  |")
    return "\n".join(lines)


def deep_dive_md(
    p: dict[str, Any],
    item: dict[str, Any],
    n: int,
    jmap: dict[str, dict[str, Any]],
    scoring: dict[str, Any],
) -> str:
    title_cn = item.get("title_cn") or p.get("title", "")
    evidence = item.get("evidence_level", "abstract_only")
    evidence_label = (
        "仅依据公开摘要与元数据，未核验全文；缺失参数不等于论文未披露"
        if evidence == "abstract_only"
        else "已获取全文并核验（引用位置见 source_quote）"
    )
    score = item.get("final_score", p.get("score", {}).get("total"))
    grade = item.get("grade") or band_for(float(score), scoring)
    oa = oa_note(p)
    basic = "\n".join([
        "| 项目 | 内容 |",
        "|---|---|",
        f"| 英文标题 | {p.get('title','')} |",
        f"| 中文标题 | {title_cn} |",
        f"| 作者 | {authors_text(p)} |",
        f"| 期刊 | {p.get('journal','')} |",
        f"| 在线发表 | {fmt_date(p)} |",
        f"| DOI | [{p.get('doi','')}]({p.get('doi_url','')}) |",
        f"| 论文类型 | {item.get('paper_type') or ('Research Article（Crossref: journal-article）')} |",
        f"| 影响因子 / 分区 | {journal_metric_text(p, jmap)} |",
        f"| OpenAlex 引用数（抓取时） | {(p.get('openalex') or {}).get('cited_by_count', '未获取')} |",
        f"| 开放获取 | {'有' + oa if oa else '未检测到开放获取全文'} |",
    ])
    innovations = bullet_list(item.get("innovations"), "本次未提取到明确创新点")
    limitations = bullet_list(item.get("limitations"), "本次未完成局限性分析")
    inspiration = bullet_list(item.get("inspiration"), "本次未完成启发分析")
    mechanism = item.get("mechanism") or "_本次未完成机理分析。_"
    background = item.get("background") or "_本次未完成背景分析。_"
    question = item.get("question") or "_本次未提炼核心科学问题。_"
    one_line = item.get("one_line") or ""
    return "\n".join([
        f"### 4.{n} {title_cn}",
        "",
        f"> **综合评分：{score} / 100（{grade}）** · **证据级别：** {evidence_label}",
        f"> {one_line}",
        "",
        "**1. 基本信息**",
        "",
        basic,
        "",
        "**2. 研究背景**",
        "",
        background,
        "",
        "**3. 科学问题**",
        "",
        question,
        "",
        "**4. 核心创新点**",
        "",
        innovations,
        "",
        "**5. 材料与实验方案**",
        "",
        params_table_md(item, evidence),
        "",
        "**6. 核心实验结果**",
        "",
        results_table_md(item, evidence),
        "",
        "**7. 工作机理**",
        "",
        mechanism,
        "",
        "**8. 局限性**",
        "",
        limitations,
        "",
        "**9. 对相关科研工作的启发**",
        "",
        (PROFILE.get("report") or {}).get("inspiration_note")
        or "> 以下为 Agent 的推理，不是原文结论。",
        "",
        inspiration,
        "",
        "**原文事实与推理拆分**",
        "",
        origin_table_md(item),
        "",
    ])


def pid_section(
    cand: dict[str, Any],
    analysis: dict[str, Any] | None,
    section_key: str,
    terms: list[str],
    title: str,
    empty_text: str,
) -> str:
    narrative = ""
    if analysis and isinstance(analysis.get("sections"), dict):
        val = (analysis["sections"] or {}).get(section_key)
        if isinstance(val, str):
            narrative = val
        elif isinstance(val, dict):
            narrative = val.get("summary", "")
    rows = []
    for p in cand.get("papers", []):
        if p.get("is_review_suspect") or not p.get("gate", {}).get("pass"):
            continue
        text = f"{p.get('title','')} {p.get('abstract','')}"
        if any(term_present(text, t) for t in terms):
            rows.append(p)
    rows.sort(key=lambda p: (-int(p.get("score", {}).get("total", 0)), p.get("effective_date") or ""))
    out = []
    if narrative:
        out.append(narrative)
    if not rows:
        out.append(f"_{empty_text}_")
        return "\n\n".join(out)
    table_lines = [
        "| 论文 | 期刊 / 日期 | 方向 | 预评分 | 关键命中 | 链接 |",
        "|---|---|---|:---:|---|---|",
    ]
    for p in rows[:10]:
        hits = (p.get("flags", {}).get(section_key, {}) or {}).get("hits") or []
        hits_txt = "、".join(hits[:4]) if hits else "—"
        table_lines.append(
            f"| {p.get('title','')} | {p.get('journal','')} / {fmt_date(p)} | "
            f"{p.get('direction','')} | {p.get('score',{}).get('total',0)} | {hits_txt} | {link_cell(p)} |"
        )
    out.append("\n".join(table_lines))
    return "\n\n".join(out)


def flag_sections_md(cand: dict[str, Any], analysis: dict[str, Any] | None) -> str:
    """按 keywords.yaml 的 flags 顺序生成专项追踪章节。

    领域完全由配置决定：换一份 flags，报告的专项章节随之改变，
    不需要改代码。
    """
    kw = load_keywords()
    flags = kw.get("flags") or {}
    if not flags:
        return (
            "_尚未在 `config/keywords.yaml` 中定义 `flags`。"
            "加上后，这里会自动按方向生成专项追踪表。_"
        )
    sections = (analysis or {}).get("sections") or {}
    out: list[str] = []
    for idx, (key, spec) in enumerate(flags.items(), start=1):
        label = spec.get("label", key)
        rows = []
        for p in cand.get("papers", []):
            if p.get("is_review_suspect") or not p.get("gate", {}).get("pass"):
                continue
            hits = (p.get("flags", {}).get(key, {}) or {}).get("hits") or []
            if hits:
                rows.append((p, hits))
        rows.sort(key=lambda pr: (-int(pr[0].get("score", {}).get("total", 0)),
                                  pr[0].get("effective_date") or ""))
        val = sections.get(key)
        narrative = val if isinstance(val, str) else (val or {}).get("summary", "") if isinstance(val, dict) else ""

        out.append(f"### 5.{idx} {label}")
        if narrative:
            out.append(narrative)
        if rows:
            lines = [
                "| 论文 | 期刊 / 日期 | 预评分 | 关键命中 | 链接 |",
                "|---|---|:---:|---|---|",
            ]
            for p, hits in rows[:10]:
                lines.append(
                    f"| {p.get('title','')} | {p.get('journal','')} / {fmt_date(p)} | "
                    f"{p.get('score',{}).get('total',0)} | {'、'.join(hits[:5]) or '—'} | {link_cell(p)} |"
                )
            out.append("\n".join(lines))
        else:
            out.append(f"_本周未检索到明确的「{label}」相关原创论文。_")
    note = (PROFILE.get("report") or {}).get("flag_note") or ""
    out.append(
        "> 注意：关键词命中只表示摘要/标题出现相关术语，不等于论文核心贡献。" + note
    )
    return "\n\n".join(out)


def methods_md(analysis: dict[str, Any] | None) -> str:
    rows = (analysis or {}).get("methods_table") or []
    if not rows:
        return "_本周未完成结构化工艺参数提取；不根据摘要猜测旋涂速度、浓度或退火温度。_"
    lines = [
        "| 论文 | 材料 / 配方 | 制备工艺 | 关键参数 | 性能 / 用途 | 可借鉴点 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        if not isinstance(r, dict):
            continue
        lines.append(
            f"| {r.get('paper','')} | {r.get('material','')} | {r.get('process','')} | "
            f"{r.get('key_params','')} | {r.get('metric','')} | {r.get('takeaway','')} |"
        )
    return "\n".join(lines)


def next_keywords_md(analysis: dict[str, Any] | None, cand: dict[str, Any]) -> str:
    kws = (analysis or {}).get("next_keywords") or []
    if not kws:
        kws = load_keywords().get("next_week_seed_keywords") or []
    if not kws:
        kws = ["（在 config/keywords.yaml 的 next_week_seed_keywords 里填下周种子词）"]
    src = "Agent 根据本周论文趋势提出" if (analysis or {}).get("next_keywords") else "配置文件默认种子词"
    return f"> {src}；下周将在同一白名单期刊上重点检索：\n\n" + "\n".join(f"- {k}" for k in kws)


def appendix_md(cand: dict[str, Any], analysis: dict[str, Any] | None, known: dict[str, dict[str, Any]]) -> str:
    out = ["### 附录 A：综述与趋势观察（不与原创研究混合排名）", ""]
    reviews = cand.get("reviews", [])[:10]
    if reviews:
        out.append("| 论文 | 期刊 / 日期 | DOI |\n|---|---|---|")
        for p in reviews:
            out.append(f"| {p.get('title','')} | {p.get('journal','')} / {fmt_date(p)} | {link_cell(p)} |")
    else:
        out.append("_本周没有识别到综述类论文。_")
    out.extend(["", "### 附录 B：无公开摘要的待核验论文", ""])
    appendix = cand.get("appendix", [])[:20]
    if appendix:
        out.append("| 论文 | 期刊 / 日期 | DOI | 说明 |\n|---|---|---|---|")
        for p in appendix:
            out.append(
                f"| {p.get('title','')} | {p.get('journal','')} / {fmt_date(p)} | "
                f"{link_cell(p)} | 无摘要，未进入主榜 |"
            )
    else:
        out.append("_无。_")
    alerts = cand.get("update_alerts", [])
    out.extend(["", "### 附录 C：勘误、撤稿与历史更新提醒", ""])
    if alerts:
        for a in alerts:
            out.append(f"- `{a.get('type')}`：{a.get('doi')}（关联 {a.get('target_doi','—')}）")
    else:
        out.append("_本周未检测到已推荐论文的撤稿/勘误更新。_")

    comparisons = (analysis or {}).get("comparisons") or []
    if comparisons:
        out.extend(["", "### 附录 D：跨论文创新点对比", ""])
        for comp in comparisons:
            out.append(f"#### {comp.get('topic','对比')}")
            dois = [normalize_doi(d) for d in comp.get("papers", [])]
            dims = comp.get("dimensions") or []
            if dims and dois:
                labels = []
                for d in dois:
                    item = item_for(analysis, d)
                    label = str(item.get("title_cn") or known.get(d, {}).get("title", d))
                    labels.append(label[:22] + ("…" if len(label) > 22 else ""))
                header = "| 维度 | " + " | ".join(labels) + " |"
                sep = "|---|" + "---|" * len(dois)
                out.extend([header, sep])
                for dim in dims:
                    vals = dim.get("values", {}) or {}
                    cells = [str(vals.get(d, vals.get(normalize_doi(d), "—"))) for d in dois]
                    out.append(f"| {dim.get('name','')} | " + " | ".join(cells) + " |")
            if comp.get("conclusion"):
                out.extend(["", comp["conclusion"]])
            out.append("")

    opportunities = (analysis or {}).get("opportunities") or []
    if opportunities:
        out.extend(["", "### 附录 E：科研选题与创新机会", ""])
        for i, opp in enumerate(opportunities, 1):
            out.append(f"**机会 {i}：{opp.get('gap','')}**")
            out.append("")
            if opp.get("why"):
                out.append(f"- 为什么是空白：{opp['why']}")
            if opp.get("next_step"):
                out.append(f"- 可执行验证：{opp['next_step']}")
            ev = []
            for doi in opp.get("evidence_dois", []) or []:
                p = known.get(normalize_doi(doi))
                if p:
                    ev.append(f"[{p.get('journal','')}]({p.get('doi_url')})")
            if ev:
                out.append(f"- 证据：{'；'.join(ev)}")
            out.append("")
    return "\n".join(out)


def limitations_md(cand: dict[str, Any], analysis: dict[str, Any] | None, final: bool) -> str:
    st = cand.get("stats", {})
    full_text = sum(
        1 for doi, item in ((analysis or {}).get("papers") or {}).items()
        if (item or {}).get("evidence_level") == "full_text"
    )
    items = [
        "数据来源为 Crossref 与 OpenAlex；未接入 Web of Science / Scopus / JCR。影响因子与中科院分区本次均标注为“未核实”，未用估算值填充。",
        "期刊分只占 15 分，且 A/B/C 分档差距有限；评分不能替代对科学问题、实验证据和机理的判断。",
        f"本周 {full_text} 篇重点论文核验了全文；其余论文仅依据公开摘要与元数据，参数缺失统一标注“摘要未披露；需查全文”。",
        (PROFILE.get("report") or {}).get("method_caveat")
        or "关键词和摘要级筛选可能漏检，也可能误收；需结合全文复核。",
        "检索窗口向前重叠 2 天，但出版社/数据库收录延迟仍可能导致论文顺延到下一周。",
        "不绕过任何付费墙；无开放获取全文时，不推测实验参数、机理细节或性能数字。",
        "本报告是选择性文献雷达，不是系统综述，不能用于宣称某一方向的完整证据覆盖。",
    ]
    if not final:
        items.append("本文件为预览/草稿，未写入历史数据库，也未推进增量检索起点。")
    custom = (analysis or {}).get("limitations") or []
    if isinstance(custom, str):
        custom = [custom]
    for c in custom:
        if c and c not in items:
            items.append(c)
    return "\n".join(f"- {x}" for x in items)


def render(template: str, values: dict[str, str]) -> str:
    out = template
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def main() -> int:
    args = parse_args()
    logger = setup_logging("report", verbose=not args.quiet)
    ensure_dirs()
    cand_path = pick_candidates(args)
    cand = load_json(cand_path)
    if not cand:
        raise SystemExit(f"Invalid candidates file: {cand_path}")
    analysis_path = pick_analysis(args, cand)
    analysis = load_json(analysis_path) if analysis_path else None
    if not analysis and not args.draft:
        raise SystemExit("Analysis JSON is required unless --draft is used")
    if args.finalize and not analysis:
        raise SystemExit("--finalize requires an analysis JSON")
    if args.finalize and not args.analysis:
        args.analysis = str(analysis_path) if analysis_path else ""

    scoring = load_scoring()
    jmap, _ = journal_index()
    known = {p["doi"]: p for p in cand.get("papers", [])}
    warnings: list[str] = []

    if analysis:
        try:
            errors, warnings = validate(analysis, cand, strict=args.finalize)
            for w in warnings:
                logger.warning("Analysis: %s", w)
            if errors and not args.finalize:
                logger.warning("Analysis validation errors: %s", errors)
        except ValidationError as exc:
            logger.error("Analysis validation failed: %s", exc)
            return 2

    # Top table and dashboard
    top_md, used_dois = top_table_md(cand, analysis, scoring, jmap, args.finalize)
    top_count = len(used_dois)
    top_picks = [normalize_doi(d) for d in ((analysis or {}).get("top_picks") or [])][:5]
    if not top_picks and used_dois:
        top_picks = used_dois[:5]
    deep_parts = []
    for i, doi in enumerate(top_picks, 1):
        p = known.get(doi)
        if not p:
            continue
        item = item_for(analysis, doi)
        if not item:
            deep_parts.append(
                f"### 4.{i} {p.get('title','')}\n\n_未提供该论文的结构化分析；"
                "请阅读摘要/全文后补充，报告不自动编造创新点、参数或机理。_"
            )
        else:
            deep_parts.append(deep_dive_md(p, item, i, jmap, scoring))
    deep_md = "\n\n".join(deep_parts) if deep_parts else "_本周没有可进行深度解读的论文。_"

    window = cand.get("window", {})
    issue = args.issue or issue_number()
    values = {
        "issue": str(issue),
        "report_date": today().isoformat(),
        "window_since": window.get("since", "?"),
        "window_until": window.get("until", "?"),
        "dashboard": dashboard_md(cand, top_count, len(top_picks)),
        "overview": overview_md(cand, top_count),
        "trends": trends_md(analysis, known),
        "top_table": top_md,
        "top_notes": (
            f"> 共 {top_count} 篇进入本周 TOP 表；"
            "综合评分为 Agent 复核后的 100 分制评分，机器预评分仅作为初筛参考。"
            "综述另见附录 A，不与原创研究混合排名。"
            if args.finalize else
            "> 预览/草稿：评分仍为机器预评分，创新性尚未经 Agent 复核。"
        ),
        "deep_dives": deep_md,
        "report_title": (PROFILE.get("report") or {}).get("title", "科研前沿文献周报"),
        "report_subtitle": subtitle_md(),
        "footer": (PROFILE.get("report") or {}).get("footer", ""),
        "sections": flag_sections_md(cand, analysis),
        "methods_table": methods_md(analysis),
        "next_keywords": next_keywords_md(analysis, cand),
        "limitations": limitations_md(cand, analysis, args.finalize),
        "appendix": appendix_md(cand, analysis, known),
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    report = render(template, values)

    until = window.get("until") or today().isoformat()
    if args.output:
        output = Path(args.output)
    else:
        suffix = "" if args.finalize else "_DRAFT"
        prefix = (PROFILE.get("report") or {}).get("prefix", "Literature_Radar_Weekly_Report")
        output = REPORTS_DIR / f"{prefix}_{until}{suffix}.md"
    if output.exists() and not args.force:
        logger.error("Report already exists (history must not be overwritten): %s", output)
        return 3
    atomic_write_text(output, report)
    logger.info("Wrote report: %s", output)

    if args.finalize:
        # Mark only the papers actually presented in the top table and deep dives.
        mark_dois = list(dict.fromkeys(used_dois + top_picks))
        papers_to_mark = [known[d] for d in mark_dois if d in known]
        db = load_db()
        analysis_meta = {
            "papers_by_doi": {
                normalize_doi(d): {
                    "title_cn": (item or {}).get("title_cn"),
                    "score": (item or {}).get("final_score"),
                    "grade": (item or {}).get("grade"),
                    "evidence_level": (item or {}).get("evidence_level"),
                }
                for d, item in ((analysis or {}).get("papers") or {}).items()
            }
        }
        mark_reported(papers_to_mark, str(output), until, db, analysis_meta)
        param_added = export_parameters(Path(analysis_path), Path(cand_path), until) if analysis_path else 0
        state = load_json(STATE_PATH, default={}) or {}
        state.update({
            "schema_version": 1,
            "status": "success",
            "last_attempt": now_iso(),
            "last_success": today().isoformat(),
            "last_window": window,
            "last_report": str(output),
            "last_candidate_file": str(cand_path),
            "last_error": None,
            "consecutive_failures": 0,
            "reported_count": len(papers_to_mark),
        })
        atomic_write_json(STATE_PATH, state)
        logger.info("Finalized; marked %d papers as reported", len(papers_to_mark))

    print(json.dumps({
        "ok": True,
        "output": str(output),
        "finalized": bool(args.finalize),
        "top_count": top_count,
        "deep_count": len(top_picks),
        "warnings": warnings[:20],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
