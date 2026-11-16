# litradar

本仓库是一个**文献雷达技能包**：扫描你白名单里的期刊，按领域关键词打分校准，
产出可核验的中文周报，并维护去重历史。

完整操作流程在 [`SKILL.md`](SKILL.md)，**执行前先读它**。本文件只说明从仓库里怎么开工。

## 这个技能做什么

- 输入：`config/journals.yaml`（扫哪些刊）+ `config/keywords.yaml`（什么算你的方向）
- 过程：Crossref 检索 → OpenAlex 补摘要/开放获取 → 门槛过滤 → 批内与历史去重 → 机器预评分
- 输出：`database/candidates/<date>.json`（候选池）、`database/analysis/<date>.json`（分析模板）、
  `reports/<prefix>_<date>.md`（中文周报）

## 先跑这几条

```bash
python scripts/health_check.py          # 体检，先确认配置没写错
python scripts/use_preset.py --list     # 看现成领域预设
python scripts/use_preset.py --use ai-ml
python scripts/run_weekly.py            # 检索 → 筛选 → 生成分析模板
```

只依赖 Python 3.9+；PyYAML 已内置在 `vendor/`，离线可用。

## 必须遵守的纪律

读 [`SKILL.md`](SKILL.md) 的「0. 边界与原则」，核心几条：

- 不绕过付费墙，不使用 Sci-Hub 类来源。
- 不虚构论文、DOI、参数、影响因子、分区。
- 没拿到全文时 `evidence_level = "abstract_only"`，不得写摘要之外的实验参数。
- 参数缺失分别标注：`原文未披露`（全文没写）或 `摘要未披露；需查全文`（只有摘要）。
- 原文结论与你的推理分开写；机器预评分不是最终分。
- 报告一旦生成不得覆盖。

## 改造成别的领域

只改 `config/` 下三份文件，不用动代码：

- `journals.yaml` —— 换成本领域 15~40 本刊（`issn` 可留空，会按刊名检索）
- `keywords.yaml` —— `directions` 的分值之和等于 `scoring.yaml` 的 `relevance`；
  每个 `flags` 会自动变成周报第 5 节的一个小节
- `profile.yaml` —— 报告标题、副标题、参数表列名、免责声明

改完跑 `python scripts/health_check.py` 复检。
