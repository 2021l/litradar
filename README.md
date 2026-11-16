# litradar · 文献雷达

> 每周扫一遍你关心的期刊，告诉你本领域这周真正发生了什么。

`litradar` 是一个**面向研究生**的通用文献雷达：你用一份配置声明「我读哪些刊、关心哪些方向」，
它就每周把新论文捞回来、去重、打分、排序，并产出一份**可核验、可追溯**的中文周报。

它不绑定学科。柔性电子、AI、生物医学、材料、社科都能用——换一份配置就是另一个领域的雷达。

## 为什么不是「多搜几篇论文」

大部分文献工具解决的是「搜得更全」，`litradar` 解决的是另一件事：**每周稳定告诉你该读哪几篇，并且你信得过**。

- **白名单驱动**：只扫你信得过的期刊，不给你一堆来路不明的预印本。
- **增量与去重**：按 DOI 记住看过什么，已推荐的下周不再出现。
- **证据分级**：每篇都标 `full_text` 或 `abstract_only`；没拿到全文就不许编参数。
- **可核验**：DOI 全部回指出版社页面，报告里的每个数字都要能落到原文。
- **不越过红线**：不碰付费墙，不虚构影响因子/分区/实验参数。

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
| `config/journals.yaml` | 扫哪些刊（15~40 本；`issn` 可留空，会自动按刊名检索） |
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
