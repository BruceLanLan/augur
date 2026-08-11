# Augur 开发路线图

**状态**：Active
**生效日期**：2026-08-11
**维护仓库**：`BruceLanLan/augur-next`
**当前基线**：`eade71a` / v10.15.0
**详细审计**：[`docs/reviews/PROJECT_REVIEW_2026-08-11.md`](reviews/PROJECT_REVIEW_2026-08-11.md)

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

## 0-30 天：建立单一、可复现的事实层

### F0.1 统一应用数据根目录

**优先级**：P0
**目标**：新增 `AUGUR_DATA_DIR`，所有 state/cache/profile/history/backtest/users/feedback 路径从同一个模块派生。
**完成定义**：

- 默认行为仍写 `~/.augur`。
- 测试使用独立临时根目录，不修改 `HOME`。
- 连续运行完整套件三次不产生跨 run 污染。
- CI 能检测任何写出临时根目录的行为。
- CI 明确断言 `augur.__file__` 和 `__version__` 来自当前被测 artifact。

### F0.2 双形态构建验证

**优先级**：P0
**目标**：同一 CI 同时验证 source/editable 与最终 wheel/sdist。
**完成定义**：

- Python 支持范围调整为 3.10+ 或 owner 明确的仍受支持版本。
- wheel fresh install 后通过 CLI help、最小离线报告、Dashboard import/startup、MCP startup。
- 增加 ruff、基础类型检查、依赖审计与 package-content 检查；质量工具缺失不得被当作成功。

### F0.3 replay schema v2 与缺失值 contract

**优先级**：P0
**目标**：停止把缺失 ownership 等字段静默解释为 0。
**完成定义**：

- 每个 replay feature 具有 value、availability、source、as_of。
- 11 个 ownership-dependent personas 在缺失时 abstain/renormalize，并输出 reason。
- live/replay feature availability 有 parity test。
- 旧 schema 有明确 migration/拒绝信息。
- schema 更新后，旧 `rolling_ic.json` 和 `agent_correlation.json` 自动判定为 stale，不能静默加载。

### F0.4 发布门与版本重置

**优先级**：P0
**建议版本**：v11.0.0
**完成定义**：

- tag 必须与 `pyproject.toml`、`augur.__version__` 一致。
- build/test job 不拥有 OIDC；publish job 只下载已验证 artifacts。
- tag protection + `pypi` environment owner approval 生效。
- TestPyPI/fresh-install 通过后才允许正式 PyPI。
- GitHub Release、PyPI 和 attestation 指向同一 commit 与 digest。

### F0.5 最小安全收口

**优先级**：P1，若开启公网/多用户部署则升级为 P0
**范围**：

- 合并 CORS 配置名与策略。
- 弃用 WebSocket query token，并做日志脱敏。
- 密码升级到 Argon2id，或 PBKDF2-SHA256 600k + 渐进迁移。
- SQLite corruption 不再直接删除用户 DB。
- 文档明确 local-first、proxy、TLS、multi-worker 和 rate-limit 边界。

### 30 天退出门

- 测试和工具不写真实用户目录。
- source 与 wheel 都能被 CI 证明是当前 commit。
- replay 缺失项可机器读取、可在 UI 显示。
- 公开仓没有独立开发提交。
- release workflow 不再允许未经测试的任意 `v*` tag 直接发布。

## 31-60 天：验证智能层并把可信度展示给用户

### C1.1 rolling IC OOS A/B

**优先级**：P0
**前置**：F0.3
**对照**：静态/简单基线 vs 50/50 rolling-IC blend。
**预注册 gate**：

- purged walk-forward folds；
- primary：Brier / log loss（有概率输出时）或预先定义的 rank-IC 指标；
- block bootstrap CI 排除零；
- 至少 2% 相对增益才考虑默认启用；
- 核心 cohort 不得退化超过 1%；
- 覆盖率和有效权重集中度不得恶化。

不达标即默认关闭或删除，不在同一 holdout 上继续调参。

### C1.2 calibration readiness

**优先级**：P1
**目标**：先建立评估框架和样本充足度门，不强行在 60 天内上线“已校准概率”。
**输出**：

- resolved outcome 数量、日期、horizon、覆盖 ticker；
- Brier、log loss、reliability、slope/intercept、ECE；
- raw / experimental / validated-calibrated 状态枚举；
- 未达到样本门槛时产品只显示 raw/experimental。

### C1.3 报告 provenance contract

**优先级**：P0
**覆盖表面**：Dashboard、CLI、MCP。
**每份报告必须显示**：

- analysis time 与 as-of date；
- 数据源、数据新鲜度和 live/replay/demo；
- 启用/跳过的 persona 与原因；
- 缺失/降级字段；
- weighting/model/artifact schema version；
- probability validation status；
- 非投资建议边界。

### C1.4 错误与降级可观测性

**优先级**：P1
**目标**：核心路径的宽泛 `except/pass` 改为结构化 degradation，不要求一次性清空所有 optional integration fallback。
**指标**：

- 核心 report/consensus/replay 持久化错误 100% 可见；
- provider fallback 原因可在 doctor 和报告中追踪；
- WebSocket 中断不吞掉最终失败状态。

### 60 天退出门

- rolling IC 有预注册、可复跑的正/负结论。
- 未验证模型不会默认改变用户结果。
- 100% 核心报告携带 provenance 与 degradation metadata。
- calibration 不再用“confidence”替代经验验证。

## 61-90 天：发布并证明一个窄工作流

### P2.1 财报事件研究工作流

**优先级**：P0
**目标用户**：有自选股的个人公开市场研究者。
**MVP**：

1. 输入 watchlist/ticker list。
2. 标记即将到来的财报事件。
3. 批量生成 pre-event 报告。
4. 与上次报告比较，突出新增 filing、guidance、风险和 persona 分歧变化。
5. 支持 CLI + Dashboard；MCP 暴露同一领域服务，不复制业务逻辑。
6. 可选接入现有 cron/bots 发送摘要。

**明确不包含**：broker sync、持仓成本、税务、订单、完整 portfolio accounting。

### P2.2 首次正式分发

**优先级**：P0
**前置**：F0.2、F0.4
**完成定义**：

- TestPyPI 与 PyPI 通过 trusted publishing。
- fresh machine 从安装到第一份有效报告 <10 分钟。
- CLI、Dashboard、MCP 使用同一版本和 provenance schema。
- GitHub Release 附 migration、known limitations 和 artifact digest。

### P2.3 设计伙伴验证

**优先级**：P1
**样本**：3-5 位目标用户。
**晋级门**：

- 至少 3 人不依赖维护者完成工作流；
- 至少 3 人完成第二次使用；
- 记录 time-to-report、理解错误、放弃原因和重复需求；
- 只有真实使用反复出现的需求才进入下季度。

### 90 天退出门

- 可复现安装和发布完成。
- 一个窄工作流被真实用户重复使用。
- 用户能解释报告来源、缺失项和概率状态。
- 下一季度范围由使用证据决定，而不是继续扩充页面清单。

## Backlog

| ID | 项目 | 优先级 | 前置 | 当前状态 |
|---|---|---:|---|---|
| F0.1 | 统一 `AUGUR_DATA_DIR` 与测试隔离 | P0 | 无 | Ready |
| F0.2 | source + wheel/sdist CI | P0 | F0.1 | Ready |
| F0.3 | replay schema v2 / missingness | P0 | F0.1 | Ready |
| F0.4 | v11 发布门 | P0 | F0.2 | Ready |
| F0.5 | 部署安全基线 | P1/P0 | F0.1 | Ready |
| C1.1 | rolling IC OOS A/B | P0 | F0.3 | Blocked |
| C1.2 | calibration readiness | P1 | resolved outcomes | Blocked |
| C1.3 | provenance contract | P0 | F0.3 | Ready |
| C1.4 | degradation observability | P1 | C1.3 | Ready |
| P2.1 | 财报事件研究工作流 | P0 | C1.3 | Planned |
| P2.2 | PyPI/GitHub Release | P0 | F0.2/F0.4 | Planned |
| P2.3 | 设计伙伴验证 | P1 | P2.1/P2.2 | Planned |

## 暂不开发

未来 90 天明确不做：

- 加密、期权、ETF 专用因子体系；
- 新 persona 数量扩张；
- 完整 portfolio/accounting/broker integration；
- 公开托管 demo、多租户 SaaS、计费、移动端；
- 新的共识权重花样；
- 没有真实 outcome 支撑的“校准概率”营销；
- 大规模框架重写；
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

- 每周：更新状态、风险和验证证据。
- 每两周：只选择一个最小可验收增量。
- 每月：复核指标与 owner decisions，删除已失效候选。
- 每次 release：把完成项移入 CHANGELOG；ROADMAP 只保留仍需行动的内容。
