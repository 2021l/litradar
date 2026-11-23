> **这是一份示例报告。** 由 `presets/flexible-electronics/` 在真实检索结果上生成，
> 为了方便阅读，删掉了 4.2–4.5 的深读和全部附录，其余内容原样保留。
> 报告里只有公开论文的元数据与分析，不含任何个人数据。

# 柔性电子前沿文献周报

> 第 2 期 · 2026-11-23 · 检索窗口 2026-11-14 至 2026-11-23
>
> Flexible Electronics Literature Radar · 覆盖柔性电子全领域：柔性机器人/软体执行器、柔性传感器、可拉伸导体、柔性光电子/能源/生物电子、PEDOT 薄膜与航天可靠性

| 🔎 检索论文 | 🎯 相关论文 | ⭐ 深度解读 |
|:---:|:---:|:---:|
| **1424** | **104** | **5** |

> 本周从 34 本白名单期刊中检索，TOP 表收录 10 篇，其中 5 篇做深度精读。数量不代表质量，不足 10 篇时不凑数。

## 1. 本周检索概况

| 项目 | 内容 |
|---|---|
| 检索日期 | 2026-11-23（Asia/Shanghai） |
| 检索时间范围 | 2026-11-14 至 2026-11-23（10 天） |
| 运行类型 | 增量检索（含 2 天重叠窗口） |
| 监测期刊数量 | 34 本（A/B/C/综述四层） |
| Crossref 去重后论文 | 1424 篇 |
| 有公开摘要 | 1188 篇 |
| 初筛通过 | 104 篇 |
| 可进入主榜 | 90 篇 |
| 最终推荐（TOP 表） | 10 篇 |
| 综述观察 | 7 篇 |
| 无摘要转待核验 | 7 篇 |
| 历史已推荐（候选池标记） | 0 篇 |
| 数据源 | Crossref REST API；OpenAlex 摘要/开放获取信息 |
| 失败或部分失败的数据源 | 无 |

> 说明：期刊影响因子和中科院分区本次未接入可核实数据源，统一标注“未核实”；期刊分仅占 15 分，且 A/B/C 三档分差有限，不能替代对论文创新性和实验证据的判断。

## 2. 本周重要发现

### 2.1 软体机器人从“结构演示”走向“医疗介入 + 全软多模态”

本周 LCE 光波导执行器把径向收缩转成 14.2% 轴向伸长，并在 28 s 内清除模拟血栓；全软异质层机器人把介电弹性体人工肌肉与 LCE 可重构骨架做成 monolithic 结构，实现 2.3 cm/s 双向爬行、跳过 2.5 个体长、20° 爬坡；DEA 主动铰链则把驱动/铰链/封装做成低轮廓模块。共同信号是：软体机器人开始同时回答“能不能动”和“能不能进窄腔/可重构”。

证据：[Advanced Functional Materials](https://doi.org/10.1002/adfm.79659)；[Nature Communications](https://doi.org/10.1038/s41467-026-79466-w)；[Advanced Materials Technologies](https://doi.org/10.1002/admt.71469)

### 2.2 可拉伸电子制造从“做图案”走向“做多层互连/可编程转移”

单片分级微光刻用 PEDOT/PDMS 10 s 光固化、一步形成数千个软 VIA，绕过逐孔加工；UV 固化转移印刷用剥离应力让液态金属原位烧结，并用 AgNW 互锁；可编程 peel-transfer 烧结把同一 LMP 膜分成导电/绝缘区（27 μm 分辨率）。这些工作说明柔性电子的瓶颈正在从“材料能不能弯”转向“多层高密度互连能不能量产”。

证据：[Science Advances](https://doi.org/10.1126/sciadv.aei9286)；[Small](https://doi.org/10.1002/smll.76753)；[Advanced Functional Materials](https://doi.org/10.1002/adfm.79714)

### 2.3 自供电从“微瓦级”走向“毫安级/宽温域”

湿气发电机用构象自适应离子水凝胶做到 1.1 mA cm⁻² 峰值电流、400% 拉伸、1000 次 200% 循环；液态金属水凝胶 TENG 用 LMP 同时做催化剂/交联剂/导电填料，压力响应 12.53 V/kPa；珠串纤维 TENG 把工作温域拉到 −196–300°C。自供电开始从“能点亮 LED”走向“能给传感/通信供能”的指标竞争。

证据：[Nature Communications](https://doi.org/10.1038/s41467-026-79679-z)；[Advanced Materials Technologies](https://doi.org/10.1002/admt.71482)；[ACS Nano](https://doi.org/10.1021/acsnano.6c07976)

### 2.4 生物电子/智能织物强调“可持续、透气、多感官”

纤维素/CNT 分子焊接纱线在 11.2 wt% 低负载下做到 334.6 S m⁻¹，并同时监测形变/生理/湿度；向日葵花粉微凝胶实现无超声 CNT 分散，做可打印生物基导电墨水；原位纳米网表皮传感器直接在皮肤上生长 <1 μm 导电纳米纤维，适配任意曲面。可持续材料 + 共形制造正在成为可穿戴电子的新主线。

证据：[Nano-Micro Letters](https://doi.org/10.1007/s40820-026-02357-8)；[Nature Communications](https://doi.org/10.1038/s41467-026-79607-1)；[Nature Communications](https://doi.org/10.1038/s41467-026-79805-x)

### 2.5 航天/极端环境从“材料级”走向“器件级演示”，但仍缺在轨验证

CsPbBr3 顺序真空沉积用界面模板保住 (110)/(220) 取向，无封装 120°C/900 h 保持 94% 效率，并做 21.9 cm² 柔性组件（4.43%）；珠串纤维 TENG 覆盖 −196–300°C。两者都明确指向航空航天，但仍是地面材料/器件级数据，没有原子氧、辐射总剂量、热真空循环或在轨飞行件。

证据：[Advanced Materials Technologies](https://doi.org/10.1002/admt.71477)；[ACS Nano](https://doi.org/10.1021/acsnano.6c07976)

## 3. 本周 TOP 10 论文

| 排名 | 论文（中文 / 英文） | 期刊 | 在线发表 | 研究方向 | 综合评分 | 推荐等级 | 链接 |
|:---:|---|---|---|---|:---:|---|---|
| 1 | 超拉伸液态金属增强聚电解质水凝胶传感器用于多通道手势识别与机械手控制<br>*Ultrastretchable Liquid-Metal Reinforced Polyelectrolyte Hydrogel Sensors for Multichannel Gesture Recognition and Robotic-Hand Control* | ACS Applied Materials & Interfaces | 2026-11-18 | 柔性传感器 / 机器人触觉 | **88** | 推荐阅读 | [DOI](https://doi.org/10.1021/acsami.6c19768) |
| 2 | 完全可拉伸湿气发电机：构象自适应离子水凝胶实现毫安级峰值输出<br>*Fully stretchable moisture-electric generators with peak milliamp-scale output via conformationally adaptive ionic hydrogels for wearables* | Nature Communications | 2026-11-20 | 柔性能源 / 自供电 | **86** | 推荐阅读 | [DOI](https://doi.org/10.1038/s41467-026-79679-z) |
| 3 | 可伸长液晶弹性体光波导执行器<br>*Elongatable Liquid Crystal Elastomer Optical Waveguide Actuator* | Advanced Functional Materials | 2026-11-15 | 柔性机器人 / 医疗执行器 | **85** | 推荐阅读 | [DOI](https://doi.org/10.1002/adfm.79659) |
| 4 | 单片分级微光刻：高密度、柔软、超薄 VIA 的可拉伸多层电子<br>*Monolithic tiered microlithography for stretchable multilayer electronics with high-density, soft, and ultrathin VIAs* | Science Advances | 2026-11-20 | PEDOT / 可拉伸互连 | **84** | 推荐阅读 | [DOI](https://doi.org/10.1126/sciadv.aei9286) |
| 5 | 连续分子尺度焊接碳纳米管到纤维素纱线：用于稳健多感官全纺织电子<br>*Continuous Molecular-Scale Welding of Carbon Nanotubes into Cellulose Yarns for Robust, Multisensory All-Textile Electronics* | Nano-Micro Letters | 2026-11-16 | 智能纺织 / 多感官 | **83** | 推荐阅读 | [DOI](https://doi.org/10.1007/s40820-026-02357-8) |
| 6 | 一石三鸟：液态金属水凝胶 TENG 电极用于自供电传感<br>*One‐Stone‐Three‐Birds: Engineering Liquid‐Metal‐Based Hydrogel TENG Electrodes for Self‐Powered Sensing* | Advanced Materials Technologies | 2026-11-18 | 自供电 / 液态金属 | **82** | 推荐阅读 | [DOI](https://doi.org/10.1002/admt.71482) |
| 7 | 高效紫外固化转移印刷液态金属/银纳米线双导电层用于软–硬集成可拉伸电子<br>*Efficient UV‐Curing Transfer Printing of Liquid‐Metal/Ag‐Nanowire Dual‐Conductive Layers for Soft–Rigid Integrated Stretchable Electronics* | Small | 2026-11-17 | 转移印刷 / 软硬集成 | **81** | 推荐阅读 | [DOI](https://doi.org/10.1002/smll.76753) |
| 8 | 酸辅助自氧化实现新型聚吡咯聚合：基体介导的两栖弹性体传感器<br>*Unlocking a Novel Polypyrrole Polymerization via Acid‐Assisted Autoxidation for Matrix‐Mediated Amphibious Elastomer Sensors* | Small | 2026-11-20 | 导电聚合物 / 极端环境传感 | **80** | 推荐阅读 | [DOI](https://doi.org/10.1002/smll.76814) |
| 9 | CsPbBr3 真空生长模式：克服动力学俘获实现热超稳定光伏<br>*Unveiling Vacuum Growth Modes of CsPbBr 3 : Overcoming Kinetic Trapping for Thermally Ultra‐Stable Photovoltaics* | Advanced Materials Technologies | 2026-11-17 | 柔性光伏 / 航天 | **80** | 推荐阅读 | [DOI](https://doi.org/10.1002/admt.71477) |
| 10 | 珠串纤维纳米异质结构：超宽温域自供电能量收集与传感<br>*Bead-on-Fiber Nano-Heterostructure Engineering for Ultra-Wide-Temperature Self-Powered Energy Harvesting and Sensing* | ACS Nano | 2026-11-19 | 极端环境 / 自供电 | **79** | 技术参考 | [DOI](https://doi.org/10.1021/acsnano.6c07976) |

> 共 10 篇进入本周 TOP 表；综合评分为 Agent 复核后的 100 分制评分，机器预评分仅作为初筛参考。综述另见附录 A，不与原创研究混合排名。
>
> TOP 5 按方向均衡选择：柔性传感器、自供电能源、医疗软体执行器、PEDOT 可拉伸互连、极端环境 TENG；排名 3/5–9 的纺织、转移印刷、PPy、航天光伏等保留在 TOP 表与专项中。

## 4. TOP 5 重点论文深度解读

### 4.1 超拉伸液态金属增强聚电解质水凝胶传感器用于多通道手势识别与机械手控制

> **综合评分：88 / 100（推荐阅读）** · **证据级别：** 仅依据公开摘要与元数据，未核验全文；缺失参数不等于论文未披露
> EGaIn 微滴本体分散在 AETC 聚电解质水凝胶中，3000% 拉伸、0–900% 应变传感（GF 1.4/11.3）、8.07 kPa⁻¹ 压力灵敏，五通道手套识别十种手势并映射机械手。

**1. 基本信息**

| 项目 | 内容 |
|---|---|
| 英文标题 | Ultrastretchable Liquid-Metal Reinforced Polyelectrolyte Hydrogel Sensors for Multichannel Gesture Recognition and Robotic-Hand Control |
| 中文标题 | 超拉伸液态金属增强聚电解质水凝胶传感器用于多通道手势识别与机械手控制 |
| 作者 | Hui Chen, Xuqing Song, Yaming Hu, Xiangning Lu, Tianchi Chen |
| 期刊 | ACS Applied Materials & Interfaces |
| 在线发表 | 2026-11-18 |
| DOI | [10.1021/acsami.6c19768](https://doi.org/10.1021/acsami.6c19768) |
| 论文类型 | Research Article |
| 影响因子 / 分区 | 未核实（本次未接入 JCR / 中科院分区数据） |
| OpenAlex 引用数（抓取时） | 0 |
| 开放获取 | 未检测到开放获取全文 |

**2. 研究背景**

可穿戴传感需要在大变形下保持导电通路稳定，但层状液态金属/水凝胶界面容易失效，且高拉伸与高灵敏往往互相牵制。作者把 EGaIn 微滴直接分散到聚电解质网络中，试图从本体结构上绕开层间界面问题。

**3. 科学问题**

本体分散的 EGaIn 微液滴能否在聚(AETC)水凝胶中形成稳定导电网络，同时实现应变/压力双模传感与机械手控制？

**4. 核心创新点**

- **结构/材料创新**：EGaIn 微滴经超声分散后引入 AETC 前驱液，UV 引发自由基聚合，形成本体分散的 AETC@LM 水凝胶，避免层状 LM/水凝胶的界面失效。
- **配方优化**：系统比较液态金属含量，LM200（200 μL LM 分散液）综合性能最佳；拉伸 3000%、应变传感 0–900%，低压/高压分段灵敏度 8.07/0.68 kPa⁻¹。
- **系统集成**：五个传感器组成五通道智能手套，ResNet50 残差学习识别十种手势，并映射到机械手姿态。

**5. 材料与实验方案**

| 参数 | 数值 / 条件 | 来源 | 备注 |
|---|---|---|---|
| 材料体系 / 型号 | 聚(AETC) 聚电解质水凝胶 + EGaIn 微滴（AETC@LM） | 摘要 |  |
| 材料配比 / 浓度 | LM200 = 200 μL 液态金属分散液；AETC 浓度未披露 | 摘要 |  |
| 柔性基底 | 无（自支撑水凝胶） | 摘要 |  |
| 薄膜厚度 | 摘要未披露；需查全文 | 未核验 |  |
| 旋涂 / 涂布参数 | 不适用（浇注/UV 固化，具体未披露） | 摘要 |  |
| 干燥 / 退火条件 | UV 引发自由基聚合；具体波长/时间未披露 | 摘要 |  |
| 制备流程 | EGaIn 超声分散于水 → 加入 AETC 前驱液 → UV 自由基聚合 → AETC@LM 水凝胶 | 摘要 |  |
| 表征方法 | 形貌、化学结构、力学、保水、粘附、机电传感（具体仪器未披露） | 摘要 |  |

**6. 核心实验结果**

| 性能指标 | 数值 | 测试条件 / 说明 | 来源 |
|---|---|---|---|
| 最大拉伸应变 | ≈3000% | LM200 | 摘要 |
| 应变传感范围 | 0–900% | 分段线性 | 摘要 |
| 应变 GF | 1.4（低应变）/ 11.3（高应变） | 分段拟合 | 摘要 |
| 压力灵敏度 | 8.07 kPa⁻¹（0–7 kPa）；0.68 kPa⁻¹（8–25 kPa） | 分段拟合 | 摘要 |
| 响应 / 恢复时间 | 0.24 s / 0.18 s | — | 摘要 |
| 循环稳定性 | 600 次 @50% 应变 | 可重复电阻响应 | 摘要 |
| 保水 | 四周后约 95% 初始质量 | 环境储存 | 摘要 |
| 系统 | 五通道手套 + ResNet50，十种手势 | 摘要未给识别准确率 | 摘要 |

**7. 工作机理**

EGaIn 微滴在本体水凝胶中形成可重构的液态金属导电网络；拉伸时微滴间距/接触面积变化，叠加聚电解质离子传导，产生分段电阻响应。压力则通过压缩导电网络提高接触。把 LM 分散在本体而不是做层状电极，避免了层间剥离导致的导电通路突然断开。摘要没有给出网络渗流阈值或原位显微证据。

**8. 局限性**

- 仅基于公开摘要；AETC 浓度、LM 微滴尺寸、膜厚、UV 波长/时间均未披露。
- 摘要没有给出手势识别准确率、跨受试者泛化或机械手控制的延迟。
- 水凝胶的长期保水、汗液/低温/真空稳定性和生物相容性未验证。
- 3000% 拉伸是材料级测试，实际手套在反复穿脱/弯曲下的寿命未知。

**9. 对相关科研工作的启发**

> 以下为 Agent 结合 PEDOT:PSS 导电薄膜、柔性传感器与航天结构健康监测方向的推理，不是原文结论。

- 本体分散 LM/聚电解质水凝胶比层状 LM 电极更适合大变形；可尝试把 PEDOT:PSS 作为第二导电相，调节低应变区的 GF。
- 五通道手套 + 残差网络 + 机械手映射，是“柔性传感—边缘算法—执行器”闭环的完整演示；可迁移到机器人抓取/康复。
- 对航天应用，水凝胶在真空/低湿下会失水，LM 也可能泄漏；需要封装或改用非水凝胶弹性体。
- 建议补“LM 含量–渗流–GF–迟滞”相图，而不是只报最优配方。

**原文事实与推理拆分**

| 原文事实 | Agent 推理（非原文结论） |
|---|---|
| LM200 拉伸 3000%、应变 0–900%、GF 1.4/11.3、压力 8.07/0.68 kPa⁻¹。 | 该材料可做大面积可穿戴传感；但真空/低湿下失水会使离子电导下降，需封装验证。 |
| 五通道手套识别十种手势并映射机械手。 | 该闭环可用于危险环境遥操作；但摘要未给延迟，实时控制是否足够尚不清楚。 |



---

_（此处省略 4.2–4.5 四篇深读。完整报告每期约 50 KB，深读 5 篇。）_

## 5. 柔性机器人 / 软体执行器专项追踪

本周机器人方向的关键词是“医疗”和“全软”：LCE 光波导执行器用 14.2% 轴向伸长做血管内模拟血栓清除；monolithic 异质层软体机器人把介电弹性体（快响应人工肌肉）与 LCE（可重构骨架）集成，做到 2.3 cm/s 爬行、2.5 体长跳跃、20° 爬坡；DEA 主动铰链则解决预拉伸/电极暴露/多层对齐的制造问题。缺口仍是输出力、循环寿命和在体/真空环境验证。

| 论文 | 期刊 / 日期 | 方向 | 预评分 | 关键命中 | 链接 |
|---|---|---|:---:|---|---|
| Ultrastretchable Liquid-Metal Reinforced Polyelectrolyte Hydrogel Sensors for Multichannel Gesture Recognition and Robotic-Hand Control | ACS Applied Materials & Interfaces / 2026-11-18 | 导电材料与界面 | 74 | robotic hand | [DOI](https://doi.org/10.1021/acsami.6c19768) |
| Elongatable Liquid Crystal Elastomer Optical Waveguide Actuator | Advanced Functional Materials / 2026-11-15 | 柔性机器人 / 软体执行器 | 69 | liquid crystal elastomer | [DOI](https://doi.org/10.1002/adfm.79659) |
| Low‐Profile Active Hinges Driven by Dielectric Elastomer Actuators | Advanced Materials Technologies / 2026-11-17 | 柔性基底与复合材料 | 56 | dielectric elastomer | [DOI](https://doi.org/10.1002/admt.71469) |
| An electrically driven multimodal soft robot enabled by a monolithic heterolayer elastomer | Nature Communications / 2026-11-14 | 柔性机器人 / 软体执行器 | 53 | artificial muscle、dielectric elastomer、liquid crystal elastomer、soft robot | [DOI](https://doi.org/10.1038/s41467-026-79466-w) |
| Multimodal Haptic Display Integrating Texture, Softness, and Thermal Rendering for Active Touch | Advanced Materials Technologies / 2026-11-14 | 极端环境与航天应用 | 43 | haptic | [DOI](https://doi.org/10.1002/admt.71463) |
| VAH-CMG: A Conditional Diffusion Model for Audio-Visual Driven Haptic Signal Generation | IEEE Transactions on Instrumentation and Measurement / 2026-11-16 | 柔性电子基础 | 28 | haptic | [DOI](https://doi.org/10.1109/tim.2026.3754167) |

> 上表为关键词命中候选，不等于论文核心贡献；进入 TOP 5 前需读摘要/全文确认。

## 6. 柔性传感器专项追踪

本周传感器主线是“大变形 + 多模态 + 系统闭环”：LM/聚电解质水凝胶做到 3000% 拉伸、0–900% 应变、8.07 kPa⁻¹ 压力，并用五通道手套 + ResNet50 控制机械手；PI/Ag@AFs/GA 压力传感器 7.63 kPa⁻¹、153 kPa 压缩强度；应变传感纤维 GF 4640.1；MXene/纸、指套式多向触觉也在补足场景。缺口是冲击/振动/SHM 专门论文仍少。

| 论文 | 期刊 / 日期 | 方向 | 预评分 | 关键命中 | 链接 |
|---|---|---|:---:|---|---|
| Polyimide-Encapsulated Ag/Aramid-Reinforced Graphene Aerogel for Ultrasensitive and Fatigue-Resistant Wearable Motion Sensing | ACS Applied Materials & Interfaces / 2026-11-23 | 柔性电子基础 | 62 | electronic skin、pressure sensor | [DOI](https://doi.org/10.1021/acsami.6c18219) |
| In-situ fabrication of ultra-conformal nanomesh epidermal sensors on arbitrary skin surface | Nature Communications / 2026-11-16 | 柔性电子基础 | 59 | pressure sensor、sensor array | [DOI](https://doi.org/10.1038/s41467-026-79805-x) |
| A Microcapacitance Measurement System Based on Capacitance-to-Frequency Conversion and Its Application in Evaluating Flexible Sensor Performance | IEEE Transactions on Instrumentation and Measurement / 2026-11-16 | 柔性传感器 | 35 | electronic skin、flexible sensor、pressure sensor、tactile sensing | [DOI](https://doi.org/10.1109/tim.2026.3754158) |
| Molecularly imprinted wearable sensor based on in situ growth of gold nanowires on PET nanoporous film for rapid cortisol detection | Sensors and Actuators B: Chemical / 2026-11-17 | 柔性电子基础 | 33 | wearable sensor | [DOI](https://doi.org/10.1016/j.snb.2026.141271) |
| Flexible Sensors for Wearable Body Temperature Monitoring | Nano Energy / 2026-11-17 | 柔性电子基础 | 25 | flexible sensors | [DOI](https://doi.org/10.1016/j.nanoen.2026.112621) |
| Biomimetic Nanofibrous Electronic Skin with Response-Polarity-Enabled Thermal-State Perception for Intelligent Robotic Recognition | Nano Energy / 2026-11-22 | 柔性电子基础 | 25 | electronic skin | [DOI](https://doi.org/10.1016/j.nanoen.2026.112644) |

> 上表为关键词命中候选，不等于论文核心贡献；进入 TOP 5 前需读摘要/全文确认。


---

_（7–9 号专项章节与附录 A–E 已省略：PEDOT / 极端环境 / 光电子专项、综述趋势、待核验论文、勘误提醒、跨论文对比、选题机会。）_

_本报告由 litradar 生成，经 Agent 复核。_

## 10. 值得借鉴的实验方法

| 论文 | 材料 / 配方 | 制备工艺 | 关键参数 | 性能 / 用途 | 可借鉴点 |
|---|---|---|---|---|---|
| D1 Chen et al., ACS AMI | AETC 聚电解质 + EGaIn 微滴（LM200） | 超声分散 → UV 自由基聚合 | 200 μL LM 分散液；AETC 浓度未披露 | 3000%；0–900%；GF 1.4/11.3；8.07 kPa⁻¹ | 本体分散 LM 避免层间界面失效 |
| D2 Li et al., Nat. Commun. | 吸湿离子水凝胶 + 不对称孔隙 SEBS 电极 | 原位成胶 + 粘附集成 | 摘要未披露 | 8.1 S/m；1.1 mA/cm²；400%；1000 次 | 螺旋–卷曲转变保持拉伸下离子传输 |
| D3 Li et al., Adv. Funct. Mater. | LCE + Ecoflex@PDMS 光波导 | 旋转打印周向取向 + 环形阵列 | 2 cm 长；808 nm NIR | 14.2%；28 s 模拟血栓 | 径向收缩→轴向伸长，光波导解决窄腔驱动 |
| D4 Xie et al., Sci. Adv. | PEDOT 基导体 + PDMS 绝缘体 | 逐层光刻 + 全曝光 | 10 s 光固化；数千 VIA | 无线 ECG；高密度软 VIA | PEDOT 可光固化，适合高密度柔性互连 |
| D10 Tan et al., ACS Nano | 细菌纤维素 + 电荷锁定纳米珠 | 可控生长珠串异质结构 | 摘要未披露 | −196–300°C；21 mW/mK；115 μC/m² | 宽温域 TENG 兼顾隔热与电荷俘获 |

## 11. 下周重点关注方向

> Agent 根据本周论文趋势提出；下周将在同一白名单期刊上重点检索：

- soft robot medical intervention liquid crystal elastomer waveguide
- monolithic heterolayer dielectric elastomer soft robot
- liquid metal hydrogel strain pressure sensor robotic hand
- moisture-electric generator stretchable ionic hydrogel
- PEDOT photocurable stretchable via multilayer
- wide temperature triboelectric nanogenerator aerospace
- CsPbBr3 flexible perovskite space photovoltaic
- cellulose CNT yarn smart textile

## 12. 方法与数据限制

- 数据来源为 Crossref 与 OpenAlex；未接入 Web of Science / Scopus / JCR。影响因子与中科院分区本次均标注为“未核实”，未用估算值填充。
- 期刊分只占 15 分，且 A/B/C 分档差距有限；评分不能替代对科学问题、实验证据和机理的判断。
- 本周 0 篇重点论文核验了全文；其余论文仅依据公开摘要与元数据，参数缺失统一标注“摘要未披露；需查全文”。
- 关键词和摘要级筛选可能漏掉未在摘要中写明“flexible/stretchable”的论文，也可能误收仅顺带提及柔性的论文；需结合全文复核。
- 检索窗口向前重叠 2 天，但出版社/数据库收录延迟仍可能导致论文顺延到下一周。
- 不绕过任何付费墙；无开放获取全文时，不推测实验参数、机理细节或性能数字。
- 本报告是选择性文献雷达，不是系统综述，不能用于宣称某一方向的完整证据覆盖。
- 本周 5 篇深读均为 abstract_only；ACS/Wiley/Nature 全文被 403/重定向拦截，参数缺失不代表论文未披露。
- TOP 5 按方向均衡选择，不是前 5 名；排名 5–9 的纺织、TENG、转移印刷、PPy、航天光伏保留在 TOP 表与专项中。
- 本周有器件级航天/极端环境候选（CsPbBr3 柔性组件、宽温域 TENG），但没有任何原子氧/辐射总剂量/热真空循环/在轨验证；不能外推为航天适用。
- PEDOT:PSS 纯薄膜的二次掺杂/膜厚–方阻/转移仍缺少白名单原创论文；本周 PEDOT 工作主要是可光固化软导体和 PEDOT/PPy 涂层。
- RSC/IEEE 等期刊的 Crossref 日期仍可能只有年份级；本次窗口用 created/print 日期回退，正式发表日期需查出版社页面。

