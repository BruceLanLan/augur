# Augur 竞品全景补充调研：Agent-Native 投研与 Skill 生态

- **状态**：Research / Product Input
- **调研日期**：2026-08-12
- **调研者**：BruceLanLan
- **前置文档**：[`FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK_2026-08-11.md`](FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK_2026-08-11.md)
- **适用**：v11 RC 产品决策、差异化策略、post-v11 方向

## 执行结论

之前的调研覆盖了基础设施层（OpenBB、Qlib、LEAN）和多 Agent 框架层（TradingAgents、Dexter），但遗漏了与 Augur **产品定位最接近的一批项目**。这些项目在 2025-2026 年间快速发展，构成了一个清晰的市场信号：

> **Agent-native 投研正在从"玩具"走向"工作台"，但还没有人把 persona 分歧、evidence ledger、point-in-time replay 和 thesis journal 做成一体的 local-first 产品。**

本轮补充了 8 个项目，分为四组。核心发现：

1. **Mira**（最直接对标）：Thesis System 与 Augur 的 P2 产品方向 90% 重合，但 Mira 没有 runtime——Augur 的 CLI/Dashboard/MCP 是壁垒。
2. **AI Berkshire**（产品方法论）：20 个 Skill 的分层设计 + 四大师对抗机制，是 Augur 18 Persona "从并列到对抗"的最佳参考。
3. **FinSight-AI**（工程参考）：snapshot-bound reports + workflow resilience，与 Augur 的 RunBundle 理念一致但有更完整的工程实践。
4. **LATO**（市场信号）：YC S26 投资，证明 agent-native 投研是 VC 认可的赛道。

## 调研方法与新增范围

在已有调研的三组（金融操作平台、金融分析 Agent、Skill/MCP 生态）之外，新增四组：

- **Agent-Native 研究平台**：Mira、LATO、Driven.ai
- **开源投研 Agent（本轮新发现）**：FinSight-AI、AlphaAnalyst、AI Berkshire
- **金融 MCP Server（扩增）**：OctagonAI、SEC-EDGAR AgentKit、sablier-mcp
- **中国竞品**：WindClaw（万得）、AlphaClaw（价值简单科技）

---

## 一、Agent-Native 研究平台

### 1. Mira (byteseek) ⭐⭐⭐ 最直接对标

| 维度 | Mira | Augur |
|---|---|---|
| **产品形态** | Skills 仓库（运行在 Claude Code/Codex 上） | Python package（CLI + Dashboard + REST + MCP + bots） |
| **核心对象** | Investment Thesis → Evidence → Refresh boundary | 18 Persona → Consensus → Report（正在向 Evidence/Claim 迁移） |
| **证据模型** | Evidence Log：source trail + time boundary + refresh condition | EvidenceItem（计划中）：effective_at/available_at/retrieved_at 三类时间 |
| **研究产出** | Standard research package（memo + evidence log + case notes） | 结构化 report + factor/consensus/sentiment 输出 |
| **变化追踪** | thesis delta、event delta、decision log、postmortem | 计划中的 Since-last-event Change Ledger |
| **Skill 体系** | 11 个 loops + skills，按场景路由 | 计划中的 earnings-prep + filing-delta 两个内置 Skill |
| **Runtime** | ❌ 无自有 runtime | ✅ CLI + Dashboard + MCP + bots + cron |
| **多视角** | 无 persona 概念 | 18 Persona |
| **Language** | 中英双语 | 中英双语 |

**Mira 的核心设计（值得借鉴）**：

```
source → claim → expectation → thesis → event delta → decision log → postmortem
```

这是目前开源社区中最完整的 "从证据到决策" 链条设计。每条结论带：
- `stale_after`：何时过期
- `must_refresh_if`：什么事件触发刷新
- controlled vocabulary：稳定的状态/动作 token（thesis_state、readiness、research_action、review_output）

**Task Routing 系统**：
- `loops/analysis-routing.md`：根据用户意图自动路由到正确的 loop
- 常见路由目标：research-loop、monitoring-loop、market-briefing-loop、position-review-loop
- 每个 loop 有明确的 input/output contract 和 delivery checklist

**对 Augur 的关键判断**：
- Mira 与 Augur 的 PRODUCT_DIRECTIONS 在产品理念上高度重合（thesis journal、event delta、evidence graph）
- Augur 的核心优势是自有 runtime——Mira 依赖 Claude Code/Codex 而 Augur 可以独立运行
- Mira 缺少 persona 体系和 point-in-time 数据纪律——这正是 Augur 可以超越的地方
- **建议融合**：adopt Mira 的 thesis system 概念模型（source→claim→expectation→thesis→delta→decision→postmortem）；adopt refresh boundary 概念并融入 EvidenceItem schema

---

### 2. LATO (YC S26) ⭐⭐ 市场信号

| 维度 | 详情 |
|---|---|
| **融资** | Y Combinator Summer 2026 batch |
| **定位** | Agent-native research and simulation platform for investors |
| **团队** | Tien Chu (ML/CS/Math/Philosophy) + Tymek Staniszewski (PE at Verdane, $11B AUM) |
| **产品** | 结合公共数据 + 基金自有知识 + 一手访谈 + 市场仿真 |
| **目标用户** | Professional investors, funds |
| **状态** | Active, San Francisco, B2B |

**信号意义**：
- YC 正在押注 "agent-native investment research"，赛道成立
- LATO 面向机构（B2B），Augur 可以走 local-first individual researcher 路线差异化
- LATO 强调 "simulation"（市场仿真），Augur 强调 "evidence"（可验证性）——两个不同但互补的价值主张

---

## 二、开源投研 Agent

### 3. AI Berkshire (xbtlin) ⭐⭐⭐ 产品方法论最佳参考

- **Stars**：9,200+
- **定位**：`AI-era Berkshire: value investing research framework for Claude Code/Codex`
- **核心设计**：

**Skill 分层体系（20 个 Skills）**：
```
深度研究类（5个）：investment-research, investment-team, management-deep-dive,
                   private-company-research, deep-company-series
财报分析类（2个）：earnings-review, earnings-team
行业筛选类（5个）：industry-research, industry-funnel, quality-screen,
                   bottleneck-hunter, investment-checklist
持仓管理类（5个）：income-investment, portfolio-review, thesis-tracker,
                   thesis-drift, news-pulse
思维工具类（3个）：dyp-ask, financial-data, wechat-article
```

**四大师对抗机制**（Augur 最应该学习的）：
- 不是"分别用 4 个大师的方法分析"，而是产生**真实张力**
- 以拼多多为例：Buffett 说"真便宜"(4.4/5)，Li Lu 说"不确定就不买"(2.0/5)
- 这种冲突才是决策信号——Augur 的 18 Persona 目前只是并列输出，没有产生这种张力

**结构化反偏见机制**：
| 机制 | 解决什么问题 |
|---|---|
| 信息丰富度评级(A/B/C) | 防止"资料多=确定性高"的幻觉 |
| 芒格式逆向检验 | 强制思考失败场景 |
| 快速否决清单（8条红线） | 一票否决 |
| 反共识检查 | 避免和市场想法一样 |
| 留白原则 | 数据不足时标注"灰色地带" |
| 镜子测试 | 5 句话说清楚 thesis → 否则不买 |

**Thesis 系统**：
- `thesis-tracker`：持续追踪 thesis 是否被证伪
- `thesis-drift`：区分事实变化、估值变化、措辞变化
- 对比两份报告时，标记 `intact / weakened / refuted`

**`/investment-team` 模式**：
- Team Lead 并行调度 4 个独立 Agent
- 各自独立搜索、独立判断、互相挑战，最后综合
- 不是把一个 prompt 拆成四段——是 4 倍搜索量、4 倍信息源、4 个独立视角

**对 Augur 的关键判断**：
- 这是 Augur 18 Persona 理念在 Claude Code 生态的"野生实现"
- AI Berkshire 的 20 Skills 分层是 Augur Skill 体系的最佳参考
- 但其产品形态是 Skills 仓库（无 runtime），Augur 的完整 runtime 是优势
- **重点关注**：thesis-tracker 和 thesis-drift 的产品设计、反偏见机制、多层 Skill 成本梯度
- **不融合**：依赖 Claude Code/Codex 的运行方式、实盘 track record 展示、微信公众号分发

---

### 4. FinSight-AI (juanjuandog) ⭐⭐ 工程参考

| 维度 | 详情 |
|---|---|
| **定位** | Evidence-grounded equity research with recoverable workflows, snapshot-bound reports, hybrid RAG |
| **技术栈** | Java 17 / Spring Boot 3.3.5 + FastAPI sidecar + PostgreSQL/pgvector + Redis + RabbitMQ |
| **目标市场** | A-share research |
| **License** | MIT |

**核心工程亮点**：

1. **Snapshot-bound Reports**：
   - `dataSnapshotHash`、`contextHash`、`reportVersion` 绑定报告到数据状态
   - 缓存失效基于 hash 变化，不是时间

2. **Workflow Resilience**：
   - Idempotency keys + Redis Lua single-flight lease + fencing token
   - 相同请求不会重复触发昂贵工作
   - Task state machine：retry、timeout takeover、dead-letter handling

3. **Hybrid RAG + Evidence Trace**：
   - FTS + Vector + Reciprocal Rank Fusion + reranking
   - 每份报告保留 evidence trace

4. **架构边界**：
   - Spring Boot 拥有领域状态和编排
   - FastAPI sidecar 拥有模型操作
   - 工作流恢复和报告一致性独立于模型运行时

**对 Augur 的启示**：
- `dataSnapshotHash` 思路与 RunBundle 一致——但 FinSight-AI 的实现在工程上更完整
- Workflow resilience 设计（lease、fencing token、idempotency）值得在 Augur 的 Skill runner 中借鉴
- 但 Augur 不应引入 Redis/RabbitMQ/PostgreSQL 硬依赖——走 local-first 路线，可以用 SQLite + file-based queue

---

### 5. AlphaAnalyst (kbhujbal) ⭐⭐ 技术参考

| 维度 | 详情 |
|---|---|
| **核心定位** | "LLM is a writer, not a knower" |
| **数据层** | 10 数据源并行抓取（SEC EDGAR, Polygon, FMP, Finnhub, MarketAux, Google News, FRED, Voyage, sec-api XBRL, FMP transcripts） |
| **计算层** | 纯 Python `decimal.Decimal` DCF + Comps；LLM 永远不碰算术 |
| **Agent 层** | 5 constructive agents + 1 Devil's Advocate（强制使用不同模型族） |
| **验证层** | Citation Validator：任何数值 claim 必须 tagged to 真实 source；不满足则降级 section |

**对 Augur 的启示**：
- Devil's Advocate 使用不同模型族的设计，可以融入 Augur 的 evidence-seeking debate
- `decimal.Decimal` 纪律——Augur 的 `deterministic_compute` capability 应采用同样标准
- Citation Validator 作为 synthesizer 的内置 gate，不是事后检查

---

### 6. Dexter (virattt) ⭐⭐ Agent 架构参考

已有调研覆盖。补充几点工程细节：

- **Event-driven architecture**：`Agent.run()` 是 `AsyncGenerator<AgentEvent>`
- **Micro-compaction**：每轮轻量裁剪旧 ToolMessage
- **Scratchpad**：JSONL 格式的任务计划、工具调用、结果日志
- **Skills System**：多步工作流编排，与 prompt 分离

---

## 三、金融 MCP Server（扩增）

### 7. OctagonAI MCP Server ⭐

- 多 Agent（3 个核心 agent）+ 自然语言查询
- 覆盖 SEC filings、earnings transcripts、financials、market data、prediction markets
- 结构化、带来源的答案
- **判断**：与 Augur 的 MCP server 互补——Augur 应保持 evidence-first，不追求"自然语言回答一切"

### 8. SEC-EDGAR AgentKit ⭐

- 把 SEC EDGAR 数据封装为 LangChain/MCP/Gradio/Dify/smolagents 的 toolkit
- 支持 financial statements、insider trading、company filings
- **判断**：可评估作为可选 SEC 数据入口，但不替代 Augur 自己的 EDGAR 模块

---

## 四、中国竞品

### 9. WindClaw（万得）⭐⭐

- 2026 年 3 月上线公测
- "把研究交给 AI，把决策留给自己"
- 支持多 Agent 协作、数据源整合、研究团队组建
- 已上线鸿蒙电脑端
- **判断**：Wind 的数据壁垒是 Augur 无法竞争的。Augur 应聚焦 US 公开市场 + 公共数据，不与 Wind 在 A 股数据上竞争。

### 10. AlphaClaw（价值简单科技）⭐

- AI 投资研究助手，偏向机构服务
- **判断**：关注但不作为对标

---

## 五、竞争格局总图

```
                    有 runtime                 无 runtime
                 ┌─────────────────┐    ┌─────────────────┐
   有 Persona    │     Augur       │    │  AI Berkshire   │
   多视角        │  (CLI+Dash+MCP) │    │  (Claude/Codex) │
                 └─────────────────┘    └─────────────────┘
                 ┌─────────────────┐    ┌─────────────────┐
   有 Evidence   │   FinSight-AI   │    │      Mira       │
   /Thesis       │  (A-share/Java) │    │  (Claude/Codex) │
                 └─────────────────┘    └─────────────────┘
                 ┌─────────────────┐    ┌─────────────────┐
   纯数据/搜索   │    OpenBB       │    │  OctagonAI MCP  │
                 │    FinChat      │    │  SEC-EDGAR Kit  │
                 └─────────────────┘    └─────────────────┘
```

**Augur 的独特位置**：同时拥有 Persona 多视角 + Evidence/Run 合约 + 完整 runtime（CLI/Dashboard/MCP/Bots）+ local-first。这个组合目前没有竞品覆盖。

---

## 六、对 Augur 产品决策的影响

### 文档质量评价

Codex 写的四份文档（ROADMAP、PRODUCT_DIRECTIONS、PROJECT_REVIEW、FINANCIAL_BENCHMARK）质量很高，在以下方面特别强：

1. **北极星清晰**："用户能否在 10 分钟内从 ticker list 获得可追溯、可理解、不会把缺失数据冒充事实的研究报告"
2. **执行原则严格**：正确性和可复现性先于新功能、OOS gate、缺失数据显式传播
3. **kill criteria 明确**：每个方向都有停止条件
4. **功能登记册与排期分离**：不把候选池当作承诺

本轮补充的增量：

1. **发现最直接对标 Mira**：验证了 PRODUCT_DIRECTIONS 中 thesis journal + event delta 方向的市场可行性
2. **发现 AI Berkshire**：为 Persona 从"并列展示"升级到"结构化对抗"提供了可参考的产品设计
3. **验证 agent-native 赛道**：LATO 的 YC 融资证明这不是个人项目的小众偏好
4. **确认差异化窗口**：目前没有人把 Augur 的五件套（Persona + Evidence + Replay + Filing Delta + Local Runtime）做在一起

### 建议的文档更新

1. `PRODUCT_DIRECTIONS.md` 的竞品段（L19-L23）应加入 Mira、AI Berkshire、LATO
2. `FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK.md` 的竞品矩阵应加入 Mira、AI Berkshire、FinSight-AI、AlphaAnalyst
3. 新建 `DIFFERENTIATION_STRATEGY.md` 整合差异化分析

---

## 参考资料

- [Mira](https://github.com/byteseek/Mira) — Agent-native investment research workspace
- [AI Berkshire](https://github.com/xbtlin/ai-berkshire) — Value investing research framework
- [FinSight-AI](https://github.com/juanjuandog/FinSight-AI) — Evidence-grounded equity research agent
- [AlphaAnalyst](https://github.com/kbhujbal/AlphaAnalyst-open-source-autonomous-equity-research-agent) — Autonomous equity research agent
- [Dexter](https://github.com/virattt/dexter) — Autonomous agent for deep financial research
- [LATO](https://www.ycombinator.com/companies/lato) — YC S26 agent-native research platform
- [OctagonAI MCP](https://github.com/OctagonAI/octagon-mcp-server) — Financial research MCP server
- [SEC-EDGAR AgentKit](https://github.com/stefanoamorelli/sec-edgar-agentkit) — SEC filing AI agent toolkit
- [WindClaw](https://www.wind.com.cn/) — 万得 AI 投研智能体平台
