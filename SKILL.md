# Literature Radar（文献雷达）

给研究生用的**通用**文献雷达：每周扫描你白名单里的期刊，按你自己定义的方向打分排序，
产出一份可核验、可追溯的中文周报，让你知道本领域这周真正发生了什么。

它不绑定任何学科——柔性电子、AI、临床、材料、社科都能用，换个配置就是另一个领域的雷达。

## 0. 边界与原则

- 只用合法公开数据源：Crossref、OpenAlex、Europe PMC、出版社开放获取页面、出版社公开 RSS。
- **不绕过付费墙**，不使用 Sci-Hub 类来源。
- 不虚构论文、DOI、实验参数、影响因子、分区、引用次数。
- 没有全文时只做 `abstract_only` 分析，并明确写“仅依据公开摘要与元数据”。
- 原文没给的参数写 **“原文未披露”**；摘要没给的写 **“摘要未披露；需查全文”**。两者不能混用。
- 原文结论与 Agent 推理必须分开写；评分不能替代阅读。
- 影响因子/分区无法核实时写 **“未核实”**，不得用记忆中的数值填充。
- 不足 10 篇高质量论文时，TOP 表按实际数量，不凑数。

## 1. 目录与关键文件

| 路径 | 用途 |
|---|---|
| `config/profile.yaml` | 领域档案：报告标题、文件名前缀、参数表列名、免责声明 |
| `config/journals.yaml` | 期刊白名单（`issn` 可选，留空则按刊名检索） |
| `config/keywords.yaml` | 门槛词、方向与分值、专项 `flags`、综述识别、下周种子词 |
| `config/scoring.yaml` | 100 分制权重、分档、置信度、去重阈值 |
| `presets/<name>/` | 现成领域预设（柔性电子 / AI-ML / 生物医学） |
| `scripts/fetch_literature.py` | Crossref 检索 + OpenAlex 摘要/开放获取补全 |
| `scripts/filter_papers.py` | 门槛、批内去重、机器预评分 |
| `scripts/deduplicate.py` | DOI 优先历史库；`check` / `stats` 子命令 |
| `scripts/prepare_analysis.py` | 生成 Agent 分析模板（含摘要） |
| `scripts/peek_candidates.py` | 打印候选阅读清单与摘要片段 |
| `scripts/validate_analysis.py` | 校验 DOI、字段、摘要数字一致性 |
| `scripts/validate_dois.py` | 用 DOI Handle API 验证链接可解析到出版社 |
| `scripts/generate_report.py` | 渲染中文周报；`--finalize` 才写历史 |
| `scripts/fetch_fulltext.py` | Europe PMC / OpenAlex 开放全文定位与正文提取 |
| `scripts/run_weekly.py` | 一键执行 检索 → 筛选 → 分析模板 |
| `scripts/health_check.py` | 配置、API、状态、数据库体检 |
| `scripts/query_history.py` | 按周、期刊、方向、材料查询历史 |
| `scripts/query_parameters.py` | 查参数库（材料/工艺/指标） |
| `scripts/use_preset.py` | 切换领域预设 |
| `database/papers.json` | 历史论文库（已推荐/已见/更新提醒） |
| `database/candidates/YYYY-MM-DD.json` | 当周候选池与机器评分 |
| `database/analysis/YYYY-MM-DD.json` | Agent 复核后的结构化分析 |
| `reports/<prefix>_YYYY-MM-DD.md` | 正式周报，禁止覆盖 |
| `state/last_run.json` | 运行状态、最后成功时间、失败次数 |
| `logs/` | 每次运行的日志 |

## 2. 首次使用：把雷达对准你的领域

先确认三份配置说的是你的方向：

1. `config/profile.yaml` 的 `report.field`、`title`、`parameter_rows`；
2. `config/journals.yaml` 的期刊名单（**最关键**，15~40 本为宜）；
3. `config/keywords.yaml` 的 `directions`（cap 之和 = `scoring.yaml` 的 `relevance`，默认 30）
   与 `flags`（每个 flag 会变成周报第 5 节的一个小节）。

想跳过手工配置，直接用现成模板：

```bash
python scripts/use_preset.py --list
python scripts/use_preset.py --use ai-ml      # 或 biomedicine / flexible-electronics
```

切换会覆盖 `config/` 下三份文件，旧文件自动备份为 `*.bak-<时间戳>`。

改完务必体检：

```bash
python scripts/health_check.py
```

## 3. 每周标准流程（必须按顺序）

### Step 1 — 检索与初筛

```bash
python scripts/run_weekly.py
```

它会：

1. 读取 `state/last_run.json` 确定窗口；失败的上次运行不会推进起点。
2. 逐本期刊查询 Crossref，按 DOI 去重。
3. 用 OpenAlex 补摘要、开放获取链接、引用数、撤稿标记。
4. 门槛过滤：`gates.core` 与 `gates.scope` **留空即不过滤**；`gates.exclude` 始终生效。
5. 批内标题近似去重；查历史库，排除已推荐论文（撤稿/勘误除外）。
6. 机器预评分，生成 `database/candidates/<until>.json` 与分析模板。

检查输出的 `stats` 与 `failed_sources`。某期刊查询失败要在报告里披露，不要假装全部成功。

首次运行回溯 30 天，之后以上次成功日期为基准向前重叠 2 天。手动补跑：

```bash
python scripts/fetch_literature.py --since 2026-11-01 --until 2026-11-16
python scripts/filter_papers.py
python scripts/prepare_analysis.py
```

### Step 2 — 选择要精读的论文

```bash
python scripts/peek_candidates.py --top 12
```

机器分只是初筛，**不要按分数机械取前 5**。选择标准：

- 与你在 `keywords.yaml` 里写的方向是否真的相关；
- 是否有新方法、新数据、新机理或新的实验设计；
- 是否有可比较的定量结果与可靠性/稳健性证据；
- 是否真的解决了一个瓶颈，而不是摘要里写 “novel”。

综述不进入原创主榜；放入附录 A 做趋势观察。

### Step 3 — 尽量核验全文

```bash
python scripts/fetch_fulltext.py --doi "10.xxxx/xxxxx"
```

也可用 `web_fetch` 打开 `publisher_url` 或 OpenAlex 的 `oa_url`。

- 拿到全文：`evidence_level = "full_text"`，填写 `fulltext_url`，关键数字附 `source_quote`。
- 只有摘要：`evidence_level = "abstract_only"`，不得写摘要之外的参数。
- 连摘要都没有：不进入主榜，放附录 B。

> ACM / Wiley / Elsevier 常见 403 或付费墙，直接标 `abstract_only`，不要尝试绕过。

### Step 4 — 填写 analysis JSON

把 `database/analysis/<until>.template.json` 复制为 `database/analysis/<until>.json` 再填，
**不要直接在模板上改**。

最低要求：

| 字段 | 要求 |
|---|---|
| `top_table` | 最多 10 个真实 DOI，按综合评分排序；不足按实际 |
| `top_picks` | 最多 5 个 DOI，必须是 `top_table` 子集 |
| `title_cn` | 准确中文标题，不机翻堆词 |
| `final_score` / `grade` | 0–100；按分档给等级 |
| `one_line` | 一句话结论：做了什么、关键结果、为什么值得读 |
| `background` / `question` | 研究背景与核心问题，不能复述摘要 |
| `innovations` | 具体到方法/数据/机理；不能照抄 “novel” 宣传语 |
| `parameters` | 按 `profile.yaml` 的 `parameter_rows` 填；缺失按规则标注 |
| `results` | 只写原文报告的结果与指标 |
| `mechanism` | 用中文解释机理；区分证据与推测 |
| `limitations` | 规模、稳定性、外部效度、重复性、指标权衡 |
| `inspiration` | 对本领域后续研究的启发 |
| `evidence_level` | `abstract_only` 或 `full_text` |
| `original_vs_inference` | 至少 2 条“原文事实 → 自己的推理” |
| `trends` | 3–5 条，每条用 `evidence_dois` 指向候选池真实论文 |
| `methods_table` | 可借鉴的方法/参数/结果；没有就留空并说明 |
| `sections.<flag_id>` | 对应 `keywords.yaml` 里每个 `flags` 的专项判断；没有就写“本周无” |

写作要求：

- 中文周报，论文英文标题、DOI、期刊名保留原文。
- 每个数字都要能回到摘要/全文；无法核实的写“未核实”。
- 不要把“作者说首次”当成事实；写“作者声称首次”，再判断证据是否充分。
- 不要用影响因子替代创新性判断。

### Step 5 — 校验并生成正式周报

```bash
python scripts/validate_analysis.py \
  --analysis database/analysis/2026-11-16.json \
  --candidates database/candidates/2026-11-16.json

python scripts/generate_report.py \
  --candidates database/candidates/2026-11-16.json \
  --analysis database/analysis/2026-11-16.json \
  --finalize
```

`--finalize` 会：再次严格校验；写 `reports/<prefix>_<until>.md`；把 TOP 表与深读论文标记为 `reported`；
更新 `state/last_run.json` 为 `success` 并推进增量起点。

**没有 `--finalize` 的生成只是预览**，不写历史、不推进起点。报告已存在时默认拒绝覆盖；
需要修订时新建带 `_rev2` 的报告并说明。

### Step 6 — 回复用户

回复必须包含：

- 本周检索窗口、期刊数、检索/初筛/推荐数量；
- 3–5 条最重要发现；
- TOP 5 的一句话推荐理由；
- 周报绝对路径；
- 数据源失败、全文缺失、未核实项；
- 定时任务状态（若本次由定时任务触发）。

不要只回复“已完成”，也不要把整篇报告粘进聊天。

## 4. 评分模型

`config/scoring.yaml` 的 100 分制：

| 维度 | 默认分值 | 说明 |
|---|---:|---|
| 与本领域方向相关性 | 30 | 由 `keywords.yaml` 的 `directions` 决定，标题命中权重高于摘要 |
| 科学问题与创新程度 | 25 | 脚本只给“新颖性线索”预评分，必须由 Agent 复核 |
| 方法与材料价值 | 15 | 方法/材料/数据集类关键词，不代表质量 |
| 结果与证据强度 | 15 | 摘要中的定量指标与对比词；无全文时置信度低 |
| 期刊学术地位 | 15 | A/B/C/R 分档，分差有限；禁止用影响因子替代 |

分档：90–100 优先精读；80–89 推荐阅读；70–79 技术参考；60–69 相关性一般；<60 不进入核心周报。

**机器预评分不是最终分。** 复核时重点改创新性：只是把已有方法换个数据集且没有新结论，创新分下调；
有真正的机理证据或方法突破，即使期刊分不高也上调。

## 5. 历史库与去重

`database/papers.json` 每条记录包含：DOI、标题、期刊、发表时间、首次发现、最后出现、出现次数、
方向、评分、是否已推荐、周报文件、证据级别。

- 去重优先 DOI；无 DOI 时用标准化标题 + 年份 + 作者近似匹配。
- 已 `reported` 的论文默认不再推荐。
- 撤稿、勘误、重要更新生成 `update_alerts`，允许重新提醒。
- 历史报告不覆盖。

```bash
python scripts/query_history.py --week 2026-11-16
python scripts/query_history.py --journal "Nature"
python scripts/query_history.py --direction foundation_models
python scripts/query_parameters.py --material PEDOT
```

### 5.1 参数库

每次 `--finalize` 会把通过核验的 `parameters` 追加到 `database/parameters.jsonl` 与 `.csv`。
只收录**明确有值**的参数；`原文未披露` / `摘要未披露` 不入库。

### 5.2 跨论文对比与创新机会

analysis JSON 可选填写 `comparisons` 与 `opportunities`（见 `templates` 与原有示例），
报告会在附录 D/E 渲染。没有就写“本周证据不足，不强行生成对比”。
不要把不同实验条件下的数字直接横向比较，必须注明条件。

## 6. 异常处理

| 情况 | 处理 |
|---|---|
| Crossref 某期刊 429/5xx | 重试 3 次；仍失败记录 `failed_sources`，继续其他期刊，报告披露 |
| 刊名检索误收同名刊物 | 补 ISSN；脚本已用 `container-title` 模糊校验，但不保证 100% |
| OpenAlex 摘要缺失 | 保留 Crossref 摘要；仍无则转附录 B |
| 无开放全文 | `abstract_only`；参数写“摘要未披露；需查全文” |
| 报告已存在 | 默认拒绝覆盖；检查是否重复运行 |
| 上次运行失败 | `last_success` 不推进；下次仍从旧起点 + 2 天重叠开始 |
| 并发运行 | `state/run.lock` 阻止；超过 6 小时视为陈旧锁 |
| analysis 里 DOI 不存在 | `validate_analysis.py` 硬失败，不得生成报告 |
| 摘要里没有的数字 | 校验器警告；删掉、标“未核实”，或补全文出处 |

## 7. 定时任务

定时任务只负责唤醒 Agent；质量控制在 Step 2–5。提示词必须要求：

1. 加载本 Skill；
2. 运行 `run_weekly.py`；
3. 完成全文核验与 analysis JSON；
4. 校验后用 `--finalize` 生成周报；
5. 回复摘要与路径；
6. 失败时报告具体失败步骤，不得把 `candidates_ready` 当成成功。

若调度器未启用，`state/last_run.json` 会显示 `never` 或旧日期；此时不能宣称“已自动运行”。

## 8. 验收清单

- [ ] `health_check.py` 无 error；
- [ ] 白名单期刊均能查询，刊名/ISSN 匹配；
- [ ] TOP 表 DOI 全部能解析到真实出版社页面（`validate_dois.py`）；
- [ ] 报告里每篇论文都来自候选 JSON，无虚构 DOI；
- [ ] TOP 5 的 `evidence_level` 明确；
- [ ] 参数缺失标注为“原文未披露”或“摘要未披露；需查全文”；
- [ ] 已推荐论文不再出现在下周主榜；
- [ ] 报告文件未被覆盖；
- [ ] `state/last_run.json` 的 `status` 为 `success`；
- [ ] 失败日志在 `logs/` 可查。

## 9. 维护

- **换领域**：`use_preset.py`，或手改三份配置。
- **加期刊**：编辑 `journals.yaml`，`id/name/tier` 必填，`issn` 建议填，然后跑 `health_check.py`。
- **加方向**：`keywords.yaml` 的 `directions`，保持 cap 之和 = `scoring.yaml` 的 `relevance`。
- **加专项章节**：`keywords.yaml` 的 `flags`，每个 flag 自动变成周报 5.x 小节。
- **改评分**：`scoring.yaml`；改完先用历史候选做回归，不要直接用于正式报告。
