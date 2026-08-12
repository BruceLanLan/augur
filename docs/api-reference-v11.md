# API Reference (v11)

Augur provides four product surfaces: CLI, REST API, MCP, and Python library.
This document covers the Python public API and REST endpoints.

## Python Public API

### Research & Analysis

| Module | Function | Description |
|---|---|---|
| `augur.workflow` | `run_workflow(ticker, steps, agents, question, resume_from, track)` | Six-stage analysis pipeline with RunTracker integration |
| `augur.data` | `fetch_market_context(ticker)` | Live market data via provider chain |
| `augur.data` | `fetch_history(ticker, period)` | Historical prices |
| `augur.registry` | `AgentRegistry()` | Persona registry access |
| `augur.registry` | `DecisionCoordinator(registry)` | Consensus/committee/debate orchestration |

### Evidence & Run (v11)

| Module | Class | Description |
|---|---|---|
| `augur.schemas` | `EvidenceItem` | Three-time evidence unit |
| `augur.schemas` | `Claim` | Classified evidence claim |
| `augur.schemas` | `StepResult` | Typed step output |
| `augur.schemas` | `RunBundle` | Immutable run record |
| `augur.schemas` | `SkillSpec` | Declarative skill contract |
| `augur.run_tracker` | `RunTracker` | Run lifecycle + checkpoint |
| `augur.provenance` | `ProvenanceBlock` | Source/freshness metadata |

### Research Memory

| Module | Class | Description |
|---|---|---|
| `augur.thesis` | `ThesisJournal` | Thesis CRUD + status |
| `augur.thesis` | `DecisionLog` | Decision record + outcome |
| `augur.questions` | `QuestionQueue` | Open research questions |
| `augur.questions` | `TemplateLibrary` | Research SOP templates |
| `augur.disagreement` | `DisagreementMapBuilder` | Persona conflict distillation |
| `augur.debate_engine` | `EvidenceSeekingDebate` | 4-stage debate protocol |

### Earnings & Filing

| Module | Class | Description |
|---|---|---|
| `augur.earnings` | `EarningsEventService` | Event detection + readiness |
| `augur.filing_delta` | `FilingDeltaBuilder` | Filing comparison |
| `augur.scorecard` | `ScorecardBuilder` | Post-earnings scorecard |
| `augur.guidance_tracker` | `GuidanceTracker` | Guidance range tracking |
| `augur.risk_review` | `RiskReviewer` | Risk factor analysis |
| `augur.covenant` | `CovenantReviewer` | Debt covenant checks |
| `augur.ownership` | `InsiderAnalyzer` | Insider cluster detection |
| `augur.ownership` | `OwnershipAnalyzer` | Institutional delta |
| `augur.accounting` | `AccountingReviewer` | Beneish M / Altman Z |
| `augur.capital_allocation` | `CapitalAllocationAnalyzer` | Buyback/dividend review |

### Valuation (all `decimal.Decimal`)

| Module | Function | Description |
|---|---|---|
| `augur.valuation` | `compute_wacc(inputs)` | WACC from CAPM + debt |
| `augur.valuation` | `compute_dcf(inputs)` | Two-stage DCF |
| `augur.valuation` | `run_scenarios(base, scenarios)` | Bull/base/bear |
| `augur.valuation` | `reverse_dcf(...)` | Implied growth |
| `augur.valuation` | `sensitivity_grid(...)` | WACC × growth matrix |
| `augur.relative_val` | `build_peer_table(...)` | Peer multiples |

### Evaluation

| Module | Class | Description |
|---|---|---|
| `augur.eval_lab` | `ChronologicalEvaluator` | Walk-forward A/B |
| `augur.eval_lab` | `PersonaAblator` | Marginal contribution |
| `augur.consensus.oos_harness` | — | Purged walk-forward OOS |
| `augur.prompt_eval` | `PromptEvaluator` | Prompt variant comparison |
| `augur.prompt_eval` | `FactorLab` | Factor IC analysis |

### Skills & Security

| Module | Class | Description |
|---|---|---|
| `augur.skills.loader` | `load_skill(path)` | Load + validate YAML |
| `augur.skills.permissions` | `SkillPermissionEnforcer` | Runtime permission checks |
| `augur.skills.permissions` | `CitationValidator` | Claim coverage check |
| `augur.capability` | `CapabilityRegistry` | Typed capability store |
| `augur.citation_queue` | `CitationCorrectionQueue` | User corrections |

## REST API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/analyze/{ticker}` | Persona analysis |
| GET | `/api/consensus/{ticker}` | Weighted consensus |
| POST | `/api/committee` | Committee verdict |
| GET | `/api/scorecard?ticker=` | Post-earnings scorecard |
| GET | `/api/earnings/queue` | Earnings events |
| GET | `/api/inbox/list` | Research inbox |
| GET | `/api/thesis/list` | Theses |
| POST | `/api/thesis/create` | Create thesis |
| GET | `/api/disagreement?ticker=` | Disagreement map |
| GET | `/api/alerts/active` | Active alerts |
| GET | `/api/decisions/list` | Decision log |

## MCP Resources

- `augur://evidence/{evidence_id}` — EvidenceItem JSON
- `augur://runs/{run_id}` — RunBundle JSON
- `augur://thesis/{thesis_id}` — Thesis JSON
- `augur://decisions/{decision_id}` — Decision JSON
- `augur://ledger/{ticker}/{quarter}` — Change ledger

## MCP Tools

- `mcp_augur_analyze` / `consensus` / `committee` / `debate` / `workflow`
- `mcp_augur_workspace_get` / `set` / `profiles`
- `mcp_augur_fetch` / `sentiment` / `configure` / `create_persona` / `list_personas`

## MCP Prompts

- `earnings_prep_prompt(ticker)`
- `filing_delta_prompt(ticker, new_accession, previous_accession)`
- `thesis_review_prompt(ticker, thesis_statement)`
- `debt_covenant_review_prompt(ticker)`

## 新增模块（持续循环补充）

| 模块 | 类/函数 | 说明 |
|---|---|---|
| `augur.change_ledger` | `ChangeLedgerBuilder` | 跨季度变更账本（6 分类） |
| `augur.citation_queue` | `CitationCorrectionQueue` | 引用纠错队列 |
| `augur.coverage_health` | `CoverageAnalyzer` | 数据覆盖健康中心 |
| `augur.coverage_health` | `PromotionGate` | 实验→默认晋级门 |
| `augur.provider_health` | `ProviderHealthTracker` | 数据源健康追踪 |
| `augur.freshness` | `FreshnessTracker` | 数据新鲜度检查 |
| `augur.cache_health` | `check_edgar_cache_freshness` | EDGAR 缓存健康 |
| `augur.relative_val` | `build_peer_table` | 同行估值对比 |
| `augur.cost_budget` | `CostTracker` | 成本/延迟预算 |
| `augur.team_audit` | `AuditLog` | 团队审计 |
| `augur.compatibility` | `CompatibilityMatrix` | 兼容矩阵 |
| `augur.prompt_eval` | `PromptEvaluator` | Prompt 评估 |
| `augur.prompt_eval` | `FactorLab` | 因子实验室 |
| `augur.outcome_tracker` | `OutcomeTracker` | 决策结果追踪 |
| `augur.portfolio_risk` | `PortfolioRiskAnalyzer` | 组合集中度分析 |
| `augur.pack_digest` | `compute_manifest_digest` | 研究包完整性 |
| `augur.research_report` | `ResearchReportBuilder` | 综合研究报告 |
| `augur.adapters.openbb_adapter` | — | OpenBB schema-only 适配器 |

## 新增 REST 端点（持续循环补充）

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/disagreement?ticker=` | 分歧图 JSON |
| GET | `/api/evidence/{id}` | 证据查询 |
| GET | `/api/insider/{ticker}` | 内部人交易 |
| GET | `/api/ownership/{ticker}` | 机构持仓 |
| GET | `/api/inbox/list` | 研究收件箱 |
| GET | `/api/alerts/active` | 活跃提醒 |
| GET | `/api/coverage/{ticker}` | 数据覆盖报告 |
| GET | `/api/providers/health` | Provider 健康 |
| POST | `/api/batch/analyze` | 批量分析 |
| GET | `/api/freshness` | 新鲜度报告 |
| GET | `/api/cache/health` | 缓存健康 |
| GET | `/api/thesis/list` + POST `/api/thesis/create` | Thesis CRUD |
| GET | `/api/questions/list` + POST `/api/questions/add` | 问题队列 |
| GET | `/api/decisions/list` + POST `/api/decisions/record` | 决策日志 |
| GET | `/api/report/{ticker}` | 综合研究报告 |
