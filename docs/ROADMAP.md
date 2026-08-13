# Augur 开发路线图

**状态**：Active
**生效日期**：2026-08-11
**维护仓库**：`BruceLanLan/augur-next`
**当前基线**：`5d3d9bf` / v11.0.0-rc1
**详细审计**：[`docs/reviews/PROJECT_REVIEW_2026-08-11.md`](reviews/PROJECT_REVIEW_2026-08-11.md)
**后续方向**：[`docs/PRODUCT_DIRECTIONS.md`](PRODUCT_DIRECTIONS.md)
**生态融合调研**：[`docs/research/FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK_2026-08-11.md`](research/FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK_2026-08-11.md)

## 这份文档的权威性

本文件是接下来开发工作的唯一 canonical roadmap。

- `docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md`、`docs/V9_ROADMAP.md` 和 Loop reports 是历史执行记录。
- `docs/FUTURE_DIRECTIONS_BRAINSTORM_2026-07.md` 是候选池，不是承诺。
- 新工作只有进入本文件或对应 GitHub milestone/issue 后才算排期。
- 每次 release 后更新完成状态、证据和下一阶段，不再把 session 恢复日志追加到旧 roadmap。

## 北极星与原则

北极星不是“功能数量”，而是用户能否在 10 分钟内，从一个 ticker list 获得可追溯、可理解、不会把缺失数据冒充事实的研究报告。

执行原则：

1. 正确性和可复现性先于新增功能。
2. 任何动态权重、概率或校准声明必须经过预注册 OOS gate。
3. 缺失数据必须显式传播，不能静默补零。
4. 私有 `augur-next/main` 是开发上游；公开 `augur/main` 只同步验证过的精确 commit。
5. 短分支、短 PR、一个 owner；不恢复长期 `feature/v9-dev`。
6. 负结论可以关闭功能；不得因为已经投入开发就降低验收门槛。

## 目标架构

```text
augur-next/main
  ├── short-lived feature/fix branches
  ├── canonical roadmap + private release candidate
  └── verified release commit
          │ exact commit promotion
          ▼
augur/main
  └── tag → build once → artifact tests → owner approval → PyPI/GitHub Release
```

公开仓不得出现私有仓没有的独立 commit。同步前必须记录：

- source commit；
- version 与 tag；
- test/build/smoke 证据；
- wheel/sdist digest；
- migration 与 known limitations。

## 一周冲刺：交付 v11 Release Candidate

**周期**：2026-08-12 至 2026-08-18（7 个自然日）
**唯一目标**：第 7 天交付一个可安装、可复验、可由 owner 决定是否发布的 v11 RC，同时完成财报事件研究、证据运行包和受限 Skill/MCP 的最小闭环。

一周压缩依赖并行执行，不是降低正确性门槛：

- **轨道 A｜平台与发布**：F0.1、F0.2、F0.4、最小安全收口。
- **轨道 B｜数据与可信度**：F0.3、C1.1、C1.2、C1.3、C1.4。
- **轨道 C｜产品闭环**：P2.1、文档、fresh-install 与 release candidate。
- **轨道 D｜研究能力合约**：E1.1、E1.2、E1.3、E1.4；只包裹现有 workflow，不引入通用 Agent/DAG 框架。

每项工作使用短分支/短 PR；当日未过验收门的改动不得阻塞已通过的轨道合并。

### 一周范围分层

- **RC 必须项**：隔离安装、双形态构建、missingness、provenance、Evidence/RunBundle、财报前 dossier、发布门。
- **应完成项**：`earnings-prep`、`filing-delta` 两个内置 SkillSpec；Evidence/Run MCP resources；结构化 tool output。
- **可降级项**：通用 capability registry 只实现满足两个内置 Skill 的最小子集；Dashboard source card 可先用现有详情页承载。
- **明确不在本周实现**：任意第三方 Skill 执行、OpenBB adapter、Qlib export、通用 DAG、开放 marketplace。

任何应完成项若威胁 RC 必须项，在 Day 4 范围冻结时降为“schema + fixture + feature flag”，不得降低测试或证据门槛。

### Day 1｜冻结范围与隔离状态

**交付**：

- 建立 v11 milestone、任务 owner、依赖关系和每日合并窗口。
- 新增统一 `AUGUR_DATA_DIR` 解析模块；默认仍为 `~/.augur`。
- 测试夹具改用独立临时数据根，不再修改真实 `HOME`。
- CI 断言 `augur.__file__`、`__version__` 和被测 commit/artifact 一致。
- 冻结 `EvidenceItem`、`Claim`、`StepResult`、`RunBundle` v1 schema、ID 规则与 `effective_at/available_at/retrieved_at` 三类时间语义。
- 冻结 Skill、Persona、Provider、Capability、Plugin 的边界；SkillSpec v1 禁止任意代码、shell、module path 和未注册网络访问。

**当日退出门**：隔离 smoke test 连续运行三次，无真实用户目录写入和跨 run 污染；四个 schema 有 round-trip 与向后兼容测试。

### Day 2｜Hermetic test 与双形态构建

**交付**：

- 将 state/cache/profile/history/backtest/users/feedback 全部接入统一数据根。
- CI 分别测试当前 source/editable 与构建后的 wheel/sdist。
- wheel fresh install 通过 CLI help、最小离线报告、Dashboard import/startup、MCP startup。
- 质量门明确运行 ruff、基础类型检查、依赖审计和 package-content 检查；工具缺失视为失败。
- 在不改变现有分析结果的前提下，为 `run_workflow` 的现有阶段加 StepResult wrapper，并生成第一份 immutable RunBundle。
- checkpoint 必须能从本地 bundle 恢复已消费输入和完成状态，不重新请求已完成的网络步骤。

**当日退出门**：两种安装形态都能被证明来自当前 commit，完整离线套件通过；同一 fixture 可生成稳定 manifest/hash 并离线读取。

### Day 3｜Replay schema v2 与缺失值 contract

**交付**：

- replay feature 统一携带 value、availability、source、as_of。
- 11 个 ownership-dependent personas 在缺失时 abstain/renormalize，并返回原因。
- live/replay availability parity test 与旧 schema migration/拒绝信息落地。
- schema 更新使旧 `rolling_ic.json`、`agent_correlation.json` 自动 stale，禁止静默加载。
- provider 输出规范化为最小 EvidenceItem；不具备 `available_at` 的历史数据显式标记 unknown，不参与时间点回测。
- Claim 必须携带 `supports/contradicts/insufficient` evidence references；无证据结论不能进入 validated report。

**当日退出门**：缺失字段不会再被解释为 0，CLI/API/UI 均可机器读取缺失与降级原因。

### Day 4｜智能层验证与状态标注

**交付**：

- 固化 rolling-IC 的 purged walk-forward OOS A/B harness 与预注册 gate。
- 对照静态/简单基线与 50/50 rolling-IC blend；不达标则默认关闭或删除动态权重。
- 输出 Brier、log loss、reliability、slope/intercept、ECE 和 resolved outcome 覆盖度。
- 产品统一使用 raw / experimental / validated-calibrated 状态；样本不足时禁止显示“已校准”。
- 实现最小 Capability registry 与 SkillSpec validator，仅覆盖已注册、typed、预算/超时受控的能力。
- 提交 `earnings-prep` 和 `filing-delta` 两个内置 Skill manifest、fixture 与权限测试；它们复用现有 workflow phase，不新建通用编排框架。

**当日退出门**：实验可复跑，未通过验证的模型不默认改变用户结果。长期样本不足是诚实的未完成证据，不是阻塞 RC 的理由。

### Day 5｜Provenance、可观测性与发布安全

**交付**：

- Dashboard、CLI、MCP 报告统一显示 analysis/as-of、来源与新鲜度、live/replay/demo、persona 启用/跳过原因、缺失/降级字段、schema/version 和概率验证状态。
- 核心 report/consensus/replay 持久化错误结构化展示；provider fallback 和 WebSocket 最终失败可追踪。
- 合并 CORS 策略、弃用 WebSocket query token、日志脱敏；SQLite corruption 不再直接删除用户 DB。
- tag/version 一致性、build/publish 权限隔离、TestPyPI/fresh-install 和 owner approval gate 落地。
- MCP 增加 `augur://evidence/{id}`、`augur://runs/{id}` 只读 resources；workflow tool 返回 typed artifact/citation/resource links，而不是只有拼接字符串。
- Skill 执行默认只读；未注册 capability、network domain 或路径访问在执行前被拒绝并留下审计记录。

**当日退出门**：100% 核心报告带 provenance/degradation metadata；任意 `v*` tag 不能绕过已测试 artifact 直接发布。

### Day 6｜财报事件研究 MVP 与 RC 演练

**交付**：

1. 输入 watchlist/ticker list 并识别临近财报事件。
2. 通过内置 `earnings-prep` 批量生成带 RunBundle/evidence manifest 的 pre-event dossier。
3. 通过内置 `filing-delta` 与上次有效运行比较新增 filing、guidance、风险和 persona 分歧变化。
4. CLI + Dashboard 复用同一领域服务；MCP 仅作为 adapter。
5. 构建 v11 RC wheel/sdist，在全新环境完成 TestPyPI 或本地 artifact 安装演练。
6. 对争议结论记录结构化 claim/evidence gap；本周不承诺完整多轮 re-query debate。

**明确不包含**：broker sync、持仓成本、税务、订单、完整 portfolio accounting。

**当日退出门**：从 fresh install 到第一份有效报告 <10 分钟；迁移、known limitations、artifact digest 齐全。

### Day 7｜总验收与交付

**交付**：

- 完整测试、静态检查、依赖审计、source/wheel smoke、Dashboard 浏览器 smoke 全部复跑。
- 发布 v11 RC commit、候选 tag、release notes、迁移说明和可复验命令。
- 用 3-5 位目标用户的脚本化测试任务启动设计伙伴验证并记录首轮反馈。
- 对两个内置 Skill 运行 citation、no-lookahead、missingness、permission 和离线 replay fixtures。
- owner 在同一 RC commit 上决定：正式 PyPI/GitHub Release，或带具体 blocker 延后。

**一周退出门**：

- 测试和工具不写真实用户目录。
- source 与 wheel 都来自同一 RC commit，artifact digest 可追溯。
- replay 缺失项和所有核心降级在三种产品表面可见。
- 未验证权重/概率不以默认或“已校准”状态呈现。
- 财报事件 MVP 可在 fresh environment 端到端运行。
- 至少一个真实 ticker 的 dossier 可从 MCP/CLI 打开同一 Evidence 与 RunBundle；两个内置 Skill 不能越权或执行任意代码。
- 公开 `augur` 不包含独立开发提交；仅在 owner 批准后同步精确 RC/release commit。

**一周内无法诚实完成的证据**：长期 resolved-outcome 样本、重复使用/留存、生产环境稳定性周期。第 7 天交付收集与判定机制，后续按真实时间累积，不能虚报为已验证。

## Backlog

| ID | 项目 | 优先级 | 目标日 | 前置 | 当前状态 |
|---|---:|---:|---|---|
| F0.1 | 统一 `AUGUR_DATA_DIR` 与测试隔离 | P0 | D1-D2 | 无 | Done |
| F0.2 | source + wheel/sdist CI | P0 | D2 | F0.1 | Done |
| F0.3 | replay schema v2 / missingness | P0 | D3 | F0.1 | Done |
| F0.4 | v11 发布门 | P0 | D5-D7 | F0.2 | Done（本地验证） |
| F0.5 | 部署安全基线 | P1/P0 | D5 | F0.1 | Done |
| C1.1 | rolling IC OOS A/B harness | P0 | D4 | F0.3 | Done |
| C1.2 | calibration readiness 与状态标注 | P1 | D4 | F0.3 | Done |
| C1.3 | provenance contract | P0 | D5 | F0.3 | Done |
| C1.4 | degradation observability | P1 | D5 | C1.3 | Done |
| P2.1 | 财报事件研究 MVP | P0 | D6 | C1.3 | Done |
| P2.2 | v11 RC / PyPI 发布候选 | P0 | D6-D7 | F0.2/F0.4 | Done（本地 build/smoke；TestPyPI 待 owner） |
| P2.3 | 设计伙伴验证机制与首轮任务 | P1 | D7 | P2.1/P2.2 | 待 owner（需真实用户） |
| E1.1 | Evidence/Claim/StepResult/RunBundle v1 | P0 | D1-D3 | F0.1 | Done |
| E1.2 | workflow phase wrapper + local checkpoint | P0 | D2-D3 | E1.1 | Done |
| E1.3 | 最小 Capability registry + SkillSpec validator | P1 | D4-D6 | E1.1 | Done |
| E1.4 | `earnings-prep` + `filing-delta` 内置 Skill | P1 | D4-D7 | E1.2/E1.3/P2.1 | Done |
| E1.5 | Evidence/Run MCP resources + typed results | P1 | D5-D7 | E1.1/E1.2 | Done |
| E1.6 | Skill 权限、citation、replay fixtures | P0 | D4-D7 | E1.3/E1.4 | Done |

> **2026-08-13 状态**：代码层面 backlog 全部完成（3422 tests + 1 skipped 全绿，ruff 全绿）。
> v11.0.0-rc1 的 wheel/sdist 已在本地 fresh-venv 双格式 smoke 通过。剩余两项依赖外部条件：
> TestPyPI/fresh-install 演练需 PyPI 凭据，设计伙伴验证需真实用户 —— 均属 owner 决策，不在代码范围内。

## 功能登记册：已记录、未排期

以下项目已进入产品候选池，但**没有日期、周数或开发承诺**。只有完成当前 7 天 RC、满足进入条件并被移动到上方一周表后，才算开始开发。详细产品定义见 [`docs/PRODUCT_DIRECTIONS.md`](PRODUCT_DIRECTIONS.md)。

| 方向 | 候选功能 | 进入开发的必要条件 |
|---|---|---|
| Evidence | claim-level source cards、evidence graph、引用纠错队列 | v1 Evidence/RunBundle 在真实流程稳定 |
| Earnings | earnings queue、pre/post dossier、跨季度 change ledger | 事件时间和核心来源覆盖可量化 |
| Thesis | thesis journal、证伪条件、thesis delta、decision log | 同 ticker 至少两个有效 RunBundle |
| Filing | 10-K/10-Q/8-K delta、措辞变化、covenant/risk-factor review | SEC locator 与 source-gap gate 稳定 |
| Valuation | deterministic DCF/WACC/comps、scenario lab、敏感性分析 | 输入 provenance、单位和公式测试完备 |
| Alerts | filing/guidance/ownership/disagreement state-change alerts | event dedupe、cooldown、误报指标就绪 |
| Evaluation | persona/prompt/factor chronological lab、ablation、baseline | point-in-time corpus 与 outcome 定义冻结 |
| MCP/Agent | prompts/resources、外部 Agent client、兼容测试 | typed MCP contract 与权限模型稳定 |
| Providers | OpenBB 可选 adapter、私有数据 adapter、provider health | canonical schema 不受第三方 metamodel 影响 |
| Export | Qlib/MLflow run export、Markdown/PDF、research pack | RunBundle schema/versioning 稳定 |
| Collaboration | watchlist sharing、研究模板、review/comment、团队审计 | 单用户闭环有复访证据 |
| Ecosystem | 官方 Skill catalog、贡献者 fixtures、compatibility badge | 至少一个外部贡献者通过安全/兼容门 |
| Research Ops | self-hosted deployment、私有 source、共享模板与支持 | 至少三个团队验证相同运维问题 |

## 暂不开发

本周明确不做：

- 加密、期权、ETF 专用因子体系；
- 新 persona 数量扩张；
- 完整 portfolio/accounting/broker integration；
- 公开托管 demo、多租户 SaaS、计费、移动端；
- 新的共识权重花样；
- 没有真实 outcome 支撑的“校准概率”营销；
- 大规模框架重写；
- OpenBB/Qlib/LEAN/LangGraph 运行时硬依赖；
- 任意第三方 Skill、MCP 或脚本的自动安装/执行；
- 第二条长期开发分支或独立的公开仓开发线。

## Owner 决策

以下决策不应由实现者暗自替 owner 决定：

- 是否正式确认 `augur-next` 为私有开发上游、`augur` 为公开稳定镜像。
- 是否记录 tip 后删除/归档两个过期私有分支。
- 下一正式版本是否采用 v11.0.0。
- PyPI project/name、Trusted Publisher、environment approver。
- Python/OS 支持矩阵。
- 公开版本支持策略；建议 solo maintainer 只支持最新 minor。
- 数据许可与历史 replay 的再分发边界。
- 未验证概率是隐藏，还是仅在 experimental 开关后显示。
- 是否允许匿名 opt-in telemetry；默认建议不开启，先用设计伙伴人工反馈。

## 维护节奏

- 每日：固定站会、合并窗口、风险与验证证据更新。
- Day 4：只允许删除范围或关闭未通过验证的功能，不新增需求。
- Day 7：基于 release gate 做 go/no-go，不因日期到了而绕过门禁。
- 每次 release：把完成项移入 CHANGELOG；ROADMAP 只保留仍需行动的内容。
