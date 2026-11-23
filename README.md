# litradar · 文献雷达

> 每周扫一遍你关心的期刊，告诉你这周真正发生了什么。

[![CI](https://github.com/2021l/litradar/actions/workflows/ci.yml/badge.svg)](https://github.com/2021l/litradar/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

做这个是因为踩过坑。曾经连续几个月只盯一个材料方向，周报做得挺漂亮，后来才发现
同一时期软体机器人那边冒出好几篇能直接借用的工作，全被自己的关键词挡在外面了。

所以它的重心不是"搜得更全"，就三件事：名单由你定，去重是自动的，没读到全文的地方老实标出来。
剩下交给你判断。

你写一份配置声明「我读哪些刊、关心哪些方向」，它每周把新论文捞回来、去重、打分、排序，
写成一份中文周报。柔性电子、AI、生物医学、材料都能用，换配置就是换领域。

*English: a config-driven literature radar. You declare which journals to watch and which
directions matter; it pulls new papers weekly, dedupes by DOI, scores and ranks them, and writes
a weekly report that keeps what the paper actually says separate from what the agent inferred.
No API keys — Crossref and OpenAlex only. Swap the config and it becomes a radar for another field.*

### 先看一份产出

不想装任何东西？这里有一份真实跑出来的报告（23 KB，删了部分深读和附录）：

👉 [examples/sample-weekly-report.md](examples/sample-weekly-report.md)

看完觉得有用再往下装。

## 它解决什么问题

多数文献工具想的是「搜得更全」。真正难的是另一件事：每周知道该读哪几篇，并且读完不后悔。

所以它只扫你自己列的期刊名单，按 DOI 记住看过什么，下周不再重复推；每篇都标清楚是读了全文
还是只看了摘要，没全文就不填实验参数；报告里的每个数字都能点回原文。

它不做什么也明说：不碰付费墙，不编影响因子和分区，不替你做实验判断。

## 快速开始

```bash
git clone https://github.com/2021l/litradar.git
cd litradar
python scripts/health_check.py            # 体检（无需联网可加 --no-network）
python scripts/use_preset.py --list       # 看看有哪些现成领域
python scripts/use_preset.py --use ai-ml  # 选一个，或改 config/ 自己写
python scripts/run_weekly.py              # 检索 → 筛选 → 生成分析模板
```

只依赖 Python 3.9+ 与 PyYAML（仓库内已内置 `vendor/PyYAML`，离线可用）。

## 三步把它变成你自己的雷达

全部领域知识都在这三个文件里，**不需要改代码**：

| 文件 | 你决定什么 |
| --- | --- |
| `config/journals.yaml` | 扫哪些刊（15~40 本，`issn` 可留空）。也可以不锁定期刊，改填一条 `query` 检索式做主题扫描 |
| `config/keywords.yaml` | 什么算你的方向（`directions` 打分）、盯哪几个专项（`flags` 生成周报章节） |
| `config/profile.yaml` | 报告长什么样（标题、参数表列名、免责声明） |

改完跑一次 `python scripts/health_check.py`，它会告诉你哪儿配错了。

### 现成预设

| 预设 | 适用 |
| --- | --- |
| `flexible-electronics` | 柔性电子 / PEDOT:PSS / 柔性传感器（含 34 本已核对 ISSN 的期刊） |
| `ai-ml` | 机器学习 / 大模型 / 可信 AI |
| `biomedicine` | 临床研究 / 疾病机制 / 转化医学 |

```bash
python scripts/use_preset.py --use flexible-electronics
```

预设只覆盖 `config/` 下三份文件，旧文件自动备份。

## 怎么跟它说话

装好之后不用记命令，正常说人话就行。下面这些说法都能直接用。

**第一次：把领域告诉它**

> 帮我用 litradar 建一个文献雷达。我研究固态电池，关心界面化学、锂枝晶和硫化物电解质，
> 常看的刊是 Advanced Materials、Joule、Nature Energy、ACS Energy Letters。

它会去改 `config/` 里的期刊名单和关键词，跑一次体检，再把结果贴给你。如果它没列出期刊，
补一句「剩下几本你帮我挑」即可。

**每周例行**

> 跑一下这周的文献雷达，挑出值得读的 5 篇，每篇一句话说清为什么值得读。

想在忙的时候少打扰：

> 这周只有真正的机理突破才报，其他不用发。

**只想查一个具体问题**

> 用 litradar 查 2025 年以来锂枝晶原位观测的论文，按能不能直接搬到我现在这个体系排序。

它走的还是检索、筛选、打分，只是方向临时收窄到这个问题。

**读完一篇想深挖**

> 这篇（DOI: 10.xxxx/xxxxx）的方法部分帮我拆开讲，和上周那篇对比，关键参数差在哪。

**换课题**

> 我换方向了，改成钙钛矿光伏的稳定性。期刊名单帮我换掉，每周一的定时任务保留。

**想确认它有没有瞎编**

> 这份报告里哪些是原文写的，哪些是你的推理？只看了摘要的单独列出来。

最后这句建议养成习惯。它会强制把 `abstract_only` 和原文引文分开摆——这也是这个工具存在的意义。

## 周报长什么样

一份报告包含：

1. **本周检索概况** —— 扫了多少刊、命中多少、失败的数据源
2. **本周重要发现** —— 3~5 条趋势，每条都挂着支撑论文的 DOI
3. **TOP 10 论文表** —— 综合评分 + 一句话结论 + 链接
4. **TOP 5 深度解读** —— 背景、问题、创新点、关键参数、结果、机理、局限、启发
5. **专项追踪** —— 由 `flags` 自动展开，你有几个方向就有几节
6. **值得借鉴的实验方法**
7. **下周重点关注方向**
8. **方法与数据限制** —— 明确写出这份雷达的盲区

## 目录结构

```
config/        领域配置（profile / journals / keywords / scoring）
presets/       现成领域预设
scripts/       检索、筛选、去重、校验、报告生成
templates/     周报模板
vendor/        内置 PyYAML（离线可用）
SKILL.md       给 AI Agent 的操作手册（含每周标准流程与纪律）
database/      运行时数据：历史库、候选池、参数库（不入库）
reports/       生成的周报（不入库）
```

## 设计原则

1. **宁可少写，也不猜。** 原文没给的数据写“原文未披露”，摘要没给的写“摘要未披露；需查全文”。
2. **证据分级。** `abstract_only` 的论文不允许出现摘要之外的实验参数。
3. **机器只做初筛。** 脚本给的是预评分，创新性必须由人或 Agent 读完摘要/全文后复核。
4. **历史不可覆盖。** 周报一旦生成就是记录，修订另起文件。
5. **数据可追溯。** 每个 DOI 都能点到出版社，每条趋势都能指向候选池里的真实论文。

`SKILL.md` 里写着完整的每周流程、评分模型、异常处理与验收清单，可以直接交给 AI Agent 执行。

## 在 DeepSeek Harness 里直接用

litradar 是一份**标准的 DSH skill**：`SKILL.md` 带 `name` / `description` frontmatter，
落在 `~/.dsh/skills/` 下就会被 Harness 自动发现，不需要额外插件或打包。

```powershell
# Windows
git clone https://github.com/2021l/litradar.git "$env:USERPROFILE\.dsh\skills\litradar"
```

```bash
# macOS / Linux
git clone https://github.com/2021l/litradar.git ~/.dsh/skills/litradar
```

仓库放在别处也行，用目录链接进来（这样 `git pull` 就能升级技能，不必重新安装）：

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.dsh\skills\litradar" -Target "D:\path\to\litradar"
```

```bash
ln -s ~/code/litradar ~/.dsh/skills/litradar
```

装好后 Harness 会实时刷新技能列表（无需重启）。之后对 Agent 说一句就行：

> 用 litradar 给我建一个「固态电池界面化学」方向的文献雷达

Agent 会按 `SKILL.md` 里的流程执行：确认/修改三份配置 → 体检 → 检索 → 选文 → 核验全文 → 生成周报 → 更新增量起点。

注意事项：

- 目录名建议与 frontmatter 的 `name` 保持一致（都用 `litradar`）。
- `SKILL.md` 必须位于技能包根目录，Harness 只在那里找。
- 技能本身不依赖 Harness：同样的文件在终端里 `python scripts/run_weekly.py` 也能跑，
  装进 Harness 只是让 Agent 替你执行这套流程。

## 其他 AI Agent 怎么装

技能按开放 Agent Skills 约定组织（`SKILL.md` + YAML frontmatter），主流 Agent 都能直接用：

| Agent | 怎么装 |
| --- | --- |
| DeepSeek Harness | `git clone … ~/.dsh/skills/litradar`（或建目录联接），技能列表实时出现 |
| Claude Code | 项目级：仓库已内置 `.claude/skills/litradar/`，在此仓库开工即可；个人级：把该目录拷到 `~/.claude/skills/` |
| Codex | 仓库根目录已内置 `AGENTS.md` 与 `.agents/skills/litradar/`，在此仓库开工即可 |
| 豆包 | 豆包 →「技能」→「导入技能」→ 选择仓库根目录（根目录含 `SKILL.md`） |
| Cursor / Windsurf / Copilot 等 | 多数会读 `AGENTS.md`；不读的话把 `SKILL.md` 正文当提示词粘进系统设定 |

入口文件分工（正文只有一份，避免多处漂移）：

- `SKILL.md` —— **唯一的流程真相**，所有 Agent 最终都读它
- `AGENTS.md` —— Codex 等工具的仓库级指引
- `CLAUDE.md` —— Claude Code 的仓库记忆
- `.agents/skills/litradar/`、`.claude/skills/litradar/` —— 两个 Agent 的技能发现目录，
  里面是只指向根 `SKILL.md` 的薄封装

> 豆包客户端各版本对「导入技能」的支持不一致。如果你的版本只接受提示词，
> 把根 `SKILL.md` 的正文整段粘进智能体设定即可；脚本部分在本地手动跑。

## 常见问题

**会议论文怎么办？**
Crossref 对 NeurIPS / ICML / CVPR 这类会议收录不稳定，领域若以会议为主，建议把会议官网或 arXiv 作为补充渠道，
`journals.yaml` 只管能被稳定检索的期刊。

**没填 ISSN 会不会不准？**
会。没填时会按刊名检索并用 `container-title` 做模糊校验，能跑，但可能误收同名刊物、也更慢。长期使用请补 ISSN。

**能不能不设门槛词？**
可以。`gates.core` 和 `gates.scope` 留空即“不做门槛过滤”，适合“我就要这几本刊的全部新文章”的用法。

**需要 API key 吗？**
不需要。Crossref 与 OpenAlex 都是公开 API，带上 `mailto` 即可（`config/profile.yaml` 的 `user_agent`）。

## 许可证

[MIT](LICENSE)
