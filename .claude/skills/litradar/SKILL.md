---
name: litradar
description: "Literature radar for graduate students in any field: scan a whitelisted journal list, filter and score papers by your own direction keywords, verify metadata, and produce a verifiable Chinese weekly report with deduplicated history. Use for 文献雷达、每周文献周报、领域前沿追踪、期刊监控、论文筛选、科研情报整理."
---

# litradar

本技能的完整说明在仓库根目录的 `SKILL.md`（相对本文件为 `../../../SKILL.md`），
执行前先读它；仓库结构与常用命令见 `../../../AGENTS.md`。

关键约束：

- 不绕过付费墙；不虚构论文、DOI、实验参数、影响因子与分区。
- 只有摘要时 `evidence_level = "abstract_only"`，不得写摘要之外的参数。
- 参数缺失区分标注：`原文未披露` / `摘要未披露；需查全文`。
- 领域配置在 `config/`（`journals.yaml`、`keywords.yaml`、`profile.yaml`），无需改代码。
