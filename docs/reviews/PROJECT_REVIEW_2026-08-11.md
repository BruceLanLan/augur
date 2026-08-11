# Augur 项目审计与迭代建议

**审计日期**：2026-08-11
**代码基线**：`eade71ad5a5bf60f1851fdd05bb808360ffad646`
**Tree hash**：`98f3891359502b8ad4bf1212b46c351c690082f0`
**审计对象**：私有仓库 `BruceLanLan/augur-next` 与公开仓库 `BruceLanLan/augur`

## 结论先行

当前所谓“私有版”和“公开版”没有代码或功能差异：两个仓库的 `main` 指向同一个 commit，tree hash 也完全相同。`augur-next` 独有的 `feature/v9-dev` 和 `release/v9.0` 都是已经被 `main` 完整包含的历史祖先，分别落后 72 和 106 个提交、领先 0 个提交。

因此，`augur-next` 目前并未履行“私有开发上游”的角色。后续计划也没有唯一权威入口：仓库里同时存在已执行完的路线图、明确声明不是路线图的头脑风暴、旧 session 恢复笔记和历史审查报告。新的唯一执行入口应为 [`docs/ROADMAP.md`](../ROADMAP.md)，并只在 `augur-next` 维护未发布计划。

项目的优势是真实的：测试覆盖广、数据时点纪律较强、Dashboard 与 CLI 已完成一次有效拆分、对无效模型敢于给出负结论。但在继续堆功能前，必须先解决四个可信度门槛：

1. 测试和运行状态不够可复现，能导入非当前 checkout 的 editable install，并会写真实 `~/.augur`。
2. `rolling_ic.json` 已默认改变共识权重，但现有证据接近噪声且没有做启用前后的 OOS 对照。
3. 历史回放把缺失的内部人/机构持股比例静默当作 0，影响 11 位 persona 的研究结论。
4. 发布工作流对任意 `v*` tag 直接获取 PyPI OIDC 权限，缺少 tag/version 一致性、测试和安装验收门。

## 一、两仓差异审计

| 维度 | `augur-next` | `augur` | 结论 |
|---|---|---|---|
| 可见性 | private | public | 仓库设置不同 |
| 默认分支 | `main` | `main` | 相同 |
| `main` commit | `eade71a` | `eade71a` | 完全相同 |
| `main` tree | `98f3891` | `98f3891` | 文件内容完全相同 |
| 独有分支 | `feature/v9-dev`、`release/v9.0` | 无 | 都是过期祖先 |
| 开放 PR | 0 | 0 | 没有开发队列 |
| 开放 Issue | 0 个可执行项 | 1 个推广性质 Issue | Issue 不是 backlog |

### 分支证据

- `origin/feature/v9-dev`：`e50101e`，相对 `main` 为 `72 behind / 0 ahead`。
- `origin/release/v9.0`：`484512e`，相对 `main` 为 `106 behind / 0 ahead`。
- 两个分支均为 `main` 的 ancestor，不应合并；保留只具有历史价值。

### 建议的仓库职责

结合 owner 已明确把 `augur-next` 定义为私有版本，本次建议采用：

- `augur-next/main`：唯一开发主干、未发布 roadmap 和 release candidate 的来源。
- `augur/main`：公开稳定镜像，只接收从 `augur-next/main` 选定的、已经验证的精确 commit。
- 禁止在公开仓直接开发后再反向合并；公开 `main` 必须始终等于或落后于私有 `main`，不能产生独立提交。
- 两仓不存储 secrets；“private”不是密钥管理方案。
- 功能使用短生命周期分支和 PR，完成后合并私有 `main`。只在维护已发布版本补丁时创建 `release/x.y`。
- 公开同步必须记录 source commit、版本、测试证据和 artifact digest。

这个方案保留私有预发布空间，但承认它比“单一公开主仓”多一层同步成本。若以后不再需要私有预发布，应直接收敛为公开单仓，而不是长期保留两个相同仓库。

## 二、现有 plan 在哪里

| 文档 | 性质 | 当前状态 | 是否权威 |
|---|---|---|---|
| `docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md` | 2026-07 项目 review 与 Phase A-F 计划 | P0/P1 主体已完成，仍有少量结构性 gate | 历史依据 |
| `docs/FUTURE_DIRECTIONS_BRAINSTORM_2026-07.md` | 14 个方向的发散清单 | 文档自己声明“不是 roadmap” | 否 |
| `docs/V9_ROADMAP.md` | v9-v10 session 日志与恢复说明 | 大部分完成；含过期分支和 push 指令 | 否 |
| `docs/FACTOR_ATTRIBUTION_FINDINGS_2026-07.md` | rolling IC 与因子归因研究结果 | 仍是重要证据 | 研究输入 |
| `docs/LOOP_200_REPORT.md` / `LOOP_400_REPORT.md` | v8 时期 review backlog | 多数被后续版本覆盖，状态难以直接复用 | 历史记录 |
| GitHub Issues / PRs | 外部协作队列 | 当前没有可执行开发项 | 否 |
| `docs/ROADMAP.md` | 新的滚动执行计划 | 从本次审计起生效 | **是** |

在本次变更前，“接下来做什么”没有单一可靠答案。最接近的答案是 `FUTURE_DIRECTIONS_BRAINSTORM_2026-07.md`，但它只是候选池；真正未关闭的可信度问题散落在 `PROJECT_REVIEW...` 和 `FACTOR_ATTRIBUTION_FINDINGS...` 中。

## 三、架构与工程质量

### 已验证的优势

- 代码图谱识别出约 8,944 个节点、25,640 条关系、210 个 HTTP routes；系统已形成 CLI、Dashboard、REST、MCP、bots 和研究脚本等完整表面。
- 离线测试套件包含 2,473 个测试用例（本次执行为 2,472 passed + 1 个状态污染失败；该失败在全新状态目录单独复验通过）。
- Dashboard 已拆成 17 个 router；CLI 也从 God file 拆成 `cli_commands/`。
- 回测默认真实数据、EDGAR point-in-time、数据源 smoke test、provider stats 和负结论记录都说明项目已有不错的证据纪律。
- YAML persona 条件虽然使用 `eval`，但前置 AST allowlist 阻止属性访问、函数调用和未知变量；本次未发现直接任意代码执行路径。

### P0：可复现测试与统一数据根目录

本次第一次运行测试时，进程导入了机器上的另一份 `<repo>` editable checkout（当前 commit 与审计基线相同），而不是当前工作 checkout；同时多个测试写入 `~/.augur`，在受限环境中产生 13 个失败。强制当前 `src` 并隔离状态后，这 13 个失败全部消失。

随后完整运行出现 1 个 auth 失败：复用前一次测试数据库后，自增用户 ID 从 1 变成 2，而测试硬编码期望 `user_id == 1`。使用全新状态目录复验该用例通过。

这说明测试数量很多，但 hermeticity 仍不足：

- `Path.home() / ".augur"` 分散在 workspace、config、history、rules、users、learning、backtest、cron、EDGAR cache 和 bots。
- `tests/conftest.py` 只统一隔离 LearningEngine，没有隔离整个应用状态。
- CI 没有断言实际导入路径和版本。
- CI 只测试 editable source，没有测试最终 wheel/sdist。

建议引入单一 `AUGUR_DATA_DIR`，默认仍为 `~/.augur`；所有持久化路径必须从一个 settings/path 模块派生。测试全局 fixture 使用 `tmp_path_factory`，并断言没有写出临时根目录。CI 同时测试 source 与 built wheel。

### P0：历史回放的缺失值语义

`docs/FACTOR_ATTRIBUTION_FINDINGS_2026-07.md:30-38` 已记录：`fetch_ticker_replay_records` 不包含 `insider_ownership` 和 `institutional_ownership`，但 `MarketContext` 默认值是 0。11 位 persona 依赖这些字段，因此“未知”被解释成“确认为零持股”，污染了：

- rolling IC 权重；
- agent correlation；
- factor attribution；
- regime OOS；
- 任何后续 calibration 数据。

免费历史数据缺失并不等于这个问题无法改进。正确修复不是编造数据，而是：

- replay schema 对字段保存 `value + availability + as_of + source`；
- persona factor 对缺失输入 abstain/renormalize，并输出机器可读 degradation reason；
- live 与 replay 使用同一套 feature availability contract；
- schema 版本变化后重建全部 feedback artifacts；
- 旧 artifact 与新 runtime schema 不匹配时拒绝加载，不得静默继续。

### P0：未经证明的 rolling-IC 默认调权

`feedback/rolling_ic.json` 来自 37 只股票、2022-2026 窗口。研究文档记录 18 位 persona 的原始 IC 从约 +0.001 到 -0.062，接近噪声；但 `src/augur/consensus/engine.py:83-117` 在文件存在时会把它与基线权重 50/50 混合。

“生成器能跑”不等于“默认启用有益”。应先锁定评估协议，对以下两组做 purged walk-forward OOS 对照：

- 当前简单/静态基线；
- 启用 rolling IC 的 50/50 混合。

晋级门槛应在看结果前写死：覆盖率不能显著下降、核心 cohort 不得明显退化、block bootstrap 区间应排除零，并达到有业务意义的最小增益。若没有增益，应默认关闭或删除混合逻辑，而不是继续在同一 holdout 调参。

### P0：发布与版本治理

当前 release 安全存在三个问题：

- tags 只有 `v9.0.8` 和 `v10.13.0`，当前代码版本为 `10.15.0`。
- Changelog 里已经出现过 `10.16.13`，之后又回到 `10.0.0` 到 `10.15.0`，时间线与 SemVer 单调性冲突。
- `.github/workflows/publish.yml` 对任意 `v*` tag 直接 build + publish，没有测试、tag 与 `pyproject.toml` version 一致性、wheel 安装 smoke test 或 artifact 复用。

建议下一次正式 PyPI 版本使用 `11.0.0`，以结束历史版本号回退；在 release workflow 中把 build/test 与 OIDC publish 分成不同 jobs，只让 publish job 获得 `id-token: write`，并配置 environment owner approval 与 tag protection。PyPI 官方也明确建议保护 tag、缩小 OIDC job 权限并使用独立环境：[Trusted Publishing security model](https://docs.pypi.org/trusted-publishers/security-model/)。

### P1：对外部署前的安全基线

- Dashboard 使用 `AUGUR_CORS_ORIGINS`，REST API 使用 `AUGUR_CORS_ALLOW_ORIGINS`，两个服务的默认与 allowlist 语义不一致。
- WebSocket 接受 `?token=`，token 可能进入浏览器历史、反向代理与访问日志；应逐步迁移到 header/cookie/subprotocol，并至少做日志脱敏。
- 密码使用 PBKDF2-HMAC-SHA256 100,000 次。OWASP 当前建议优先 Argon2id；需要 PBKDF2 时建议 600,000 次，并提供登录时渐进迁移：[OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)。
- `UserManager._init_db` 对任何 `sqlite3.DatabaseError` 直接删除 users DB。应先原子重命名为损坏备份并停止自动恢复，避免把暂时性错误升级为用户数据丢失。
- rate limit 是单进程内存状态，不适合多 worker 或反向代理部署；部署文档必须明确 local-first 边界。
- Python 声明仍支持 3.8，但 Python 3.8 已于 2024-10-07 EOL：[Python version status](https://devguide.python.org/versions/)。

### P1：复杂度热点

当前最大维护热点包括：

- `src/augur/backtest.py`：1,217 行，`run_backtest` 112 行，跨数据准备、执行、统计与持久化。
- `src/augur/data.py` 与 `src/augur/report.py`：各约 1,028 行。
- `src/augur/mcp_server.py`：807 行，工具 schema 与领域编排高度集中。
- `src/augur/bots/wechat_bot.py`：1,134 行。
- `index.html`、`stocks.html`、`settings.html` 与 `base.html` 仍是大型服务端模板。

不建议做一次“大重写”。在下一项功能触及这些模块时，以领域边界拆出：

- replay schema / dataset builder；
- metrics / calibration；
- artifact store；
- report provenance model；
- MCP adapters；
- bot-independent notification service。

### P1：错误与可观测性

代码中仍有大量宽泛 `except ...: pass`。其中部分是可接受的 optional integration 降级，但核心 scoring、artifact loading、WebSocket fan-out 和持久化错误不应静默。建议统一错误类别、结构化 warning 和 degradation metadata，并在 Dashboard/CLI/MCP 显示“数据缺失/降级”，而不是只写日志。

## 四、产品方向

本周冲刺不应继续横向增加 persona、资产类别或大页面。最有效的产品楔子是：

> 从自选股或轻量 ticker list 出发，识别即将到来的财报事件，批量生成带来源、时点、缺失项和与上次变化对比的研究报告。

它复用现有 watchlist、EDGAR、guidance、cron、bots、Dashboard、CLI 和 MCP，不需要先建设完整 portfolio accounting。组合优化、broker sync、税务成本和交易执行应明确排除。

## 五、验证记录与边界

### 已执行

- 两仓 commit/tree/branch ancestor 比较。
- GitHub 仓库、开放 Issue 和 PR 状态核对。
- 代码知识图谱架构、route、关键调用面与复杂度热点审计。
- 离线 pytest：
  - 非隔离环境：13 failed / 2460 passed，确认由非当前 checkout 的 editable import 与用户目录写入引起。
  - 本地源码 + 隔离状态：1 failed / 2472 passed，唯一失败为复用 DB 后硬编码用户 ID。
  - 全新状态目录复验唯一失败：1 passed。
- 发布、认证、CORS、WebSocket、密码存储、反馈权重与 replay 路径定点检查。

### 未执行

- 真实联网数据源 smoke test。
- 浏览器端完整 E2E。
- rolling IC 新 OOS 跑批。
- PyPI/TestPyPI 实际发布。
- 依赖漏洞扫描和渗透测试。

这些项目属于后续 roadmap 的验收工作，不能把本次静态 review 当成已经完成。
