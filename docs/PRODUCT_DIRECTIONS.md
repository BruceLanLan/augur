# Augur 产品方向与功能机会地图

- **状态**：Discovery / 方向约束，不等同于已承诺 backlog
- **研究日期**：2026-08-11
- **适用基线**：v11 Release Candidate 之后
- **执行计划**：[`docs/ROADMAP.md`](ROADMAP.md)
- **生态融合调研**：[`docs/research/FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK_2026-08-11.md`](research/FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK_2026-08-11.md)

## 一句话定位

> Augur 是面向美国公开市场研究者的 local-first、evidence-first 财报研究工作台：把 watchlist 变成可复验的财报前研究包，并在事件后准确展示“什么变了、依据是什么、哪些观点仍有分歧”。

Augur 不应把“18 位大师”或“多 Agent”本身当作产品。Persona 是分析镜头；真正的产品是一个持续积累的事件研究记忆系统。

## 为什么选择这个方向

通用赛道已经被更强的产品占据：

- [FinChat](https://finchat.io/) 已覆盖全球基本面、KPI、预期、所有权、IR 内容、财报日历、Dashboard 和 AI Copilot；Augur 不适合追求数据终端的横向完整度。
- [AlphaSense](https://www.alpha-sense.com/platform/generative-search/) 依靠付费内容、带引用检索、Deep Research 和 workflow agents 服务专业机构；Augur 无法用公共数据复制其内容壁垒。
- [OpenBB](https://docs.openbb.co/) 已把多数据源接入、可定制研究 Workspace 和自定义 Agent 作为核心平台能力；Augur 不应再造一个泛金融 Workspace。
- [TradingAgents](https://github.com/TauricResearch/TradingAgents)、[ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) 和 [Dexter](https://github.com/virattt/dexter) 说明“金融多 Agent”很容易获得关注，也意味着泛 Agent 叙事高度拥挤、难以形成长期差异。

Augur 的现有 watchlist、cron/bots、EDGAR fundamentals、management guidance、内部人/机构持仓、persona 分歧、历史记录、Dashboard、CLI 和 MCP 已经能组成财报事件闭环。最值得建设的是这些能力之间缺少的证据、变化和复盘层。

## 产品飞轮

```mermaid
flowchart LR
    A["Watchlist 与财报事件"] --> B["Point-in-time 证据账本"]
    B --> C["财报前研究包"]
    C --> D["财报后变化账本"]
    D --> E["用户 Thesis 与决策日志"]
    E --> F["Outcome / Replay / OOS 评估"]
    F --> G["保留有效镜头，降级无效镜头"]
    G --> C
```

这个飞轮产生三个会随时间复利的资产：

1. **Point-in-time evidence graph**：事件、filing、事实、claim、来源时点、转换版本和 snapshot hash。
2. **Longitudinal event memory**：连续季度的 guidance、基本面、风险、管理层措辞、所有权、分歧和未解决问题变化。
3. **Replay/evaluation corpus**：明确缺失值和 look-ahead 约束的历史事件包，用来决定 persona、prompt、因子和权重是否值得保留。

## 优先功能组合

### P0：信任底座

#### 1. Claim-level Evidence Ledger

每个重要结论、图表和提醒都携带：

- 原始来源类型、URL 或 SEC accession number；
- publication/retrieval/as-of 时间；
- 原文 locator 或可打开的 source card；
- 数据转换、schema、model/prompt 和代码版本；
- coverage、missing、degraded 与 validation status。

缺失来源必须显示 unknown/abstain，不能显示为 neutral 或 0。导出的报告同时生成 machine-readable evidence manifest。

#### 2. Reproducible Research Run Bundle

每次分析保存不可变的输入 snapshot、数据获取时间、配置、persona/prompt/model 版本、代码 revision、结构化输出和缺失统计。相同 bundle 可在离线 cache 上复验；空数据或验证失败只能得到 `unvalidated`，不能产生性能徽章。

### P1：财报事件核心闭环

#### 3. Watchlist Earnings Queue

把 watchlist 变成未来财报事件队列，显示：

- 事件时间及其可信度；
- filing、fundamentals、guidance、ownership 等来源新鲜度；
- dossier readiness 和缺失项；
- 已生成、需要刷新、因证据不足而暂停的状态。

#### 4. Pre-event Earnings Dossier

生成结构化财报前研究包：上一期 guidance、关键 KPI 变化、近期 filing/内部人/机构行为、主要风险、分析镜头分歧、待回答问题和 bull/base/bear 场景变量。每项事实直接链接 Evidence Ledger。

#### 5. Since-last-event Change Ledger

相较上一个有效事件 snapshot，只展示重要变化：

- guidance 与管理层措辞；
- 基本面和估值输入；
- risk factors 与新增 filing；
- ownership/insider 变化；
- persona 分歧、abstention 和结论变化。

变化账本比重新生成一份“公司简介”更接近高频研究需求。

#### 6. Evidence-backed Disagreement Map

从 18 份并列输出收敛为少量决策相关冲突：谁在什么事实和假设上不同、各自证据是什么、哪一项新信息会改变判断。未验证 persona 不参与排名；缺失输入的 persona 明确 abstain。

### P2：让用户回来，而不是只生成一次报告

#### 7. Thesis Journal 与 Thesis Delta

用户可记录投资 thesis、催化剂、主要风险、证伪条件和未解决问题。两次 run bundle 之间自动生成 thesis delta，用户标记 `intact / weakened / refuted` 并写原因。所有变化必须指向事实差异，而不是只比较生成文本。

#### 8. Material Catalyst Alerts

提醒从“分数超过阈值”升级为明确状态变化：新 filing/guidance、财报 dossier ready、内部人集群交易、机构覆盖变化、分歧显著扩大或 thesis 证伪条件触发。提醒需要 event dedupe、cooldown、触发解释和 evidence/diff 链接。

#### 9. Post-event Scorecard

财报后将 pre-event 问题、场景和事实与实际披露逐项对照，记录哪些判断被证实、证伪或仍未知。Scorecard 不给交易归因，而是评估研究过程和信息覆盖。

### P3：把可信度变成工程壁垒

#### 10. Chronological Evaluation Lab

使用不可变事件 bundles，在锁定的 walk-forward/OOS 窗口中比较 persona、prompt、因子或权重改动：

- 观察数量、日期和 ticker 覆盖；
- missingness 与有效覆盖率；
- baseline 对照、IC/Brier/log loss 和不确定性；
- cohort regression 与 promotion decision。

实验不能自动改变默认产品行为；只有过 gate 并经 maintainer 明确批准后才能晋级。

#### 11. Public Research Evidence Pack

发布一个版本化、可引用的研究证据包格式，包含 retrieval manifest/hash、point-in-time inputs、outcome definition、人工复核的 claim/citation cases 和预注册 evaluation config。公共 filing 不是壁垒，持续维护的复验与事实质量记录才是。

### P4：验证核心留存后再做的邻接方向

以下功能有价值，但必须由财报闭环的真实使用触发：

- peer/relative valuation workbench；
- filing corpus 的带引用问答和跨季度措辞搜索；
- 可编辑的 bull/base/bear scenario lab；
- 研究笔记、Markdown/PDF/Notion-style export；
- OpenBB custom backend/app 或标准化 MCP package；
- source、persona、report template、event workflow 的稳定 extension contract；
- 小团队的私有数据适配、共享模板和 self-hosted Research Ops。

## 功能总登记册：方向已记录，尚未排期

当前唯一有日期的开发计划是 [`docs/ROADMAP.md`](ROADMAP.md) 中的 7 天 v11 RC。下面是未来产品池，不代表月度承诺；只有满足依赖、指标和 owner 取舍后，才会进入新的 7 天计划。

### A. 证据、可信度与研究记忆

| ID | 功能 | 用户价值 | 进入条件 |
|---|---|---|---|
| A01 | Claim-level Source Cards | 从结论直接打开原始 filing/数据片段 | EvidenceItem locator/hash 稳定 |
| A02 | Evidence Graph | 查看事实、claim、反例和缺口关系 | Claim edge schema 通过 fixture |
| A03 | Research Run Explorer | 浏览每步输入、输出、耗时、失败和版本 | RunBundle/checkpoint 可离线读取 |
| A04 | Citation Correction Queue | 用户报告错误引用并形成回归用例 | 可定位 claim/evidence ID |
| A05 | Coverage & Data Health Center | 明确哪些 ticker/指标/时期不支持 | provider coverage/freshness 可统计 |
| A06 | Reproducible Research Pack | 导出 manifest、缓存证据和验证结果 | 数据许可允许对应导出 |

### B. 财报事件与持续跟踪

| ID | 功能 | 用户价值 | 进入条件 |
|---|---|---|---|
| B01 | Watchlist Earnings Queue | 将 watchlist 变成待研究事件队列 | 财报时间来源和置信规则稳定 |
| B02 | Pre-earnings Dossier | 财报前集中查看 guidance/KPI/风险/问题 | `earnings-prep` 通过证据 gate |
| B03 | Post-earnings Scorecard | 对照事前问题与实际结果 | pre-event snapshot 不可变 |
| B04 | Cross-quarter Change Ledger | 只看较上季真正变化的事实与措辞 | 连续两期 RunBundle 有效 |
| B05 | Guidance Tracker | 结构化跟踪 guidance 区间和修订 | guidance locator/单位规范稳定 |
| B06 | Management Language Diff | 捕获风险、需求和资本配置措辞变化 | filing section 对齐准确率达标 |
| B07 | Material Catalyst Alerts | 只提醒明确状态变化 | dedupe/cooldown/误报反馈可用 |
| B08 | Event Readiness Score | 告知 dossier 是否可生成及缺什么 | coverage 不被压成不透明总分 |

### C. Filing 与专题研究 Skill

| ID | 功能 | 用户价值 | 进入条件 |
|---|---|---|---|
| C01 | Filing Delta | 10-K/10-Q/8-K 的数字和章节变化 | `filing-delta` fixture 通过 |
| C02 | Risk-factor Review | 区分新增、删除和措辞升级风险 | section/locator 稳定 |
| C03 | Debt Covenant Review | 提取债务约束、流动性与触发条件 | fact/inference/source-gap gate |
| C04 | Capital Allocation Review | 回购、分红、并购、capex 连续变化 | cash-flow/filing 数据覆盖达标 |
| C05 | Insider Cluster Review | 识别连续或集群内部人行为 | Form 4 coverage/身份归一化稳定 |
| C06 | Institutional Ownership Delta | 展示持仓变化并明确披露滞后 | 13F available-at 语义正确 |
| C07 | Accounting Quality Review | 应计、现金转换和一次性项目检查 | 确定性公式与单位测试完备 |
| C08 | Peer Comparison Pack | 统一口径对比经营和估值指标 | peer universe 与口径可解释 |

### D. 估值、情景和确定性计算

| ID | 功能 | 用户价值 | 进入条件 |
|---|---|---|---|
| D01 | Deterministic DCF | LLM 只解释、Python 负责计算 | 输入 provenance 与公式 golden tests |
| D02 | WACC Builder | 显示每个资本成本输入与来源 | risk-free/beta/premium 时点明确 |
| D03 | Relative Valuation | 可复算的 comps 和分位数 | peer selection policy 冻结 |
| D04 | Bull/Base/Bear Scenario Lab | 用户修改少量驱动变量观察结果 | 不输出默认目标价/仓位建议 |
| D05 | Sensitivity & Reverse DCF | 看到市场价格隐含假设 | 单位、货币、稀释口径可靠 |
| D06 | Unit Economics/KPI Model | 支持行业特定 KPI 桥接 | 行业 schema 不污染核心合约 |

### E. Thesis、决策与协作

| ID | 功能 | 用户价值 | 进入条件 |
|---|---|---|---|
| E01 | Thesis Journal | 保存 thesis、催化剂、风险与证伪条件 | 用户身份/本地存储迁移稳定 |
| E02 | Thesis Delta | 新证据如何改变 thesis | 两个有效 RunBundle 可比较 |
| E03 | Decision Log | 记录当时知道什么和为什么行动/不行动 | evidence snapshot 可冻结 |
| E04 | Open Questions Queue | 跨事件保留未解决问题 | question 状态模型稳定 |
| E05 | Research Template Library | 按行业/事件复用研究 SOP | 内置 Skill compatibility 稳定 |
| E06 | Review & Comment | 小团队对 claim/evidence 留审阅意见 | 单用户复访和团队需求被验证 |
| E07 | Shared Watchlist Workspace | 共享研究队列、状态和责任人 | 权限/审计设计完成后再做 |

### F. Agent、Persona 与评估实验室

| ID | 功能 | 用户价值 | 进入条件 |
|---|---|---|---|
| F01 | Evidence-seeking Debate | 只对争议 claim 查找反证并修订 | 固定集证明准确率收益大于成本 |
| F02 | Persona Ablation | 判断 18 个镜头谁有增量价值 | baseline 与 outcome 定义冻结 |
| F03 | Prompt/Model Evaluation | 改 prompt/model 前检测事实退化 | replay corpus 有代表性样本 |
| F04 | Chronological Factor Lab | point-in-time OOS 比较因子/权重 | available-at 覆盖完整 |
| F05 | Disagreement Map | 展示事实、假设和未决问题上的分歧 | claim/evidence 结构化率达标 |
| F06 | Cost/Latency Budgeting | 每个 Skill 展示耗时、token 和失败率 | StepResult telemetry 稳定 |
| F07 | Promotion Gate | 人工批准实验能力成为默认 | 指标、阈值和回滚均预注册 |

### G. 数据、互操作与生态

| ID | 功能 | 用户价值 | 进入条件 |
|---|---|---|---|
| G01 | OpenBB Optional Provider | 使用更多 provider 而不改变核心 | canonical Evidence schema 稳定 |
| G02 | Private Data Adapter SDK | 团队接入自有数据 | credential/permission 边界稳定 |
| G03 | MCP Resources & Prompts Pack | 外部 Agent 读取同一 Evidence/Run | typed output 与授权测试通过 |
| G04 | Qlib/MLflow Run Export | 将研究实验接入现有评估工具 | RunBundle versioning 稳定 |
| G05 | Markdown/PDF/JSON Export | 便于分享且保留证据 manifest | export 后引用仍可定位 |
| G06 | Official Skill Catalog | 安装经过验证的研究 SOP | 至少一个外部贡献者通过兼容门 |
| G07 | Compatibility Badge | 标记 provider/Skill 支持的版本与能力 | 自动 compatibility suite 可公开运行 |
| G08 | Provider Health Dashboard | 观察延迟、覆盖、fallback 和失败 | provider metrics 结构化 |

### H. 产品体验与 Research Ops

| ID | 功能 | 用户价值 | 进入条件 |
|---|---|---|---|
| H01 | Research Inbox | 聚合需要处理的事件、缺口和提醒 | 状态变化事件模型稳定 |
| H02 | Universal Command Palette | 从任意页面启动 Skill/打开证据 | 核心动作边界清晰 |
| H03 | Saved Research Views | 保存筛选、字段和报告布局 | Dashboard 信息架构稳定 |
| H04 | Self-hosted Deployment Pack | 可靠部署、升级、备份和诊断 | fresh-install/upgrade gate 长期稳定 |
| H05 | Team Audit & Admin | 私有数据、权限和审计 | 出现真实团队付费需求 |
| H06 | Research Ops Support | 私有 adapter、模板和评估支持 | 三个团队验证同类运维问题 |

## 北极星指标与 kill criteria

### 产品指标

- fresh install 到第一份有效 dossier <10 分钟；
- 财报事件识别正确率 ≥90%；
- 支持 universe 中 ≥80% 的事件在 24 小时前生成 ready dossier；
- 抽样 claim/source 对应准确率 ≥98%；
- 用户研究准备时间中位数下降 ≥50%；
- ≥10 位独立用户使用 watchlist，且 ≥5 位连续使用两个财报周期后，再扩大协作与生态投入；
- 维护数据源故障的时间不超过维护者容量的 25%-30%。

### 停止或收缩条件

- 公共数据无法稳定覆盖 80%：缩小支持 universe，而不是无边界增加 provider。
- 引用准确率达不到 98%：停止新增功能，先修证据链。
- 用户认为它只是“LLM summary + links”：重新验证产品定位。
- persona OOS 不优于简单 baseline：取消排名、预测性语言和默认权重，仅保留可引用的定性镜头。
- 完成设计伙伴验证后仍不足 5 位用户进入第二个财报周期：停止扩张并重新做问题发现。

## 项目与商业化方向

建议采用 **trusted OSS product → evaluation/extension substrate → optional Research Ops** 的顺序：

1. 核心 runtime 保持宽松开源，以本地运行、隐私和可复验降低采用门槛。
2. 用 official/compatible policy、兼容测试和 trademark/发行规范建立“官方可信版本”，而不是急着建 marketplace。
3. 社区贡献对象优先是 replay fixture、citation correction、source adapter、report template 和 challenge case，而不是继续增加 persona 数量。
4. 初期商业化卖部署可靠性、私有 source adapter、共享模板、升级支持和 evaluation setup，不卖“秘密 alpha”或准确率承诺。
5. 至少三个团队独立验证相同协作/运维问题后，才评估 hosted control plane、团队权限和订阅产品。

数据与分发需要遵守来源条款。[SEC Developer Resources](https://www.sec.gov/about/developer-resources) 明确要求负责任地访问 EDGAR；商业数据、新闻、社交和 LLM 输出默认采用 BYO-key/provider，未核实再分发权利前不打包转售。

## 当前明确拒绝

- 泛化的“AI 股票推荐/多 Agent 炒股”定位；
- 自动交易、broker sync、目标价、仓位建议和投资回报承诺；
- 全量全球数据、实时新闻/社交情绪 firehose、付费预期数据平替；
- generic data terminal、generic workspace 或 connector 数量竞赛；
- portfolio accounting、税务、移动原生客户端；
- 未经 OOS gate 的动态权重、综合 confidence 和“已校准概率”；
- 无审核的 persona/plugin marketplace；
- multi-tenant SaaS、计费和复杂团队权限。

## 每个新功能必须回答的五个问题

1. 它是否缩短 watchlist 到有效 dossier 的时间？
2. 它是否让来源、时点、缺失项或变化更清楚？
3. 它是否增加下一次财报周期的回访理由？
4. 它是否复用统一事件、证据和 run bundle，而不是复制业务逻辑？
5. 如果失败，能否用可观测指标明确关闭，而不是继续投入？

不能至少满足前三项中的两项，或无法回答第五项的功能，不进入 roadmap。
