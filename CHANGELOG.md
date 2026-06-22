# Changelog

All notable changes to augur-agents are documented in this file.

## [10.15.0] - 2026-06-22

Bloomberg 风格终端工作区定制 + Agentic 工作流 MCP + 共识增强模块 + **Agent Peer Review** 集成迭代。

### Added
- **Terminal Workspace** (`src/augur/workspace.py`)：布局预设（analyst/trader/committee/minimal）、默认首页、隐藏导航、Ticker Tape 开关；持久化到 `~/.augur/workspace.yaml`。
- **Multi-profile workspace**：命名配置 CRUD、`/api/workspace/profiles`、export/import bundle。
- **Dashboard API**：`GET/PUT /api/workspace`、`GET /api/workspace/presets`；Settings 页「终端工作区」配置区。
- **Agentic Workflow**：`augur_workflow` MCP 工具 + `src/augur/workflow.py`（fetch → analyze → consensus → committee → debate → sentiment 可组合步骤链）。
- **Consensus 模块** (`src/augur/consensus/`)：industry_matrix、regime_weights、macro_features、probability_calibrator、meta_model、rolling_ic、regime_router、risk_manager。
- **Agent Peer Review synthesis** (`docs/AGENT_PEER_REVIEW_SYNTHESIS.md`)：6 份 peer review 汇总 + P0/P1/P2 backlog + mutual promotion 计划。

### Fixed
- **Persona-aware weights**：`restrict_weights_to_agents()` 将行业/机制权重重归一化到实际参与 agent。
- **Server-side landing**：`GET /` 使用 `resolve_landing_url` 302 跳转，避免 trader 配置下首页 widget 闪烁。
- **Workflow integration**：空 `--agents` 时读取 workspace `enabled_personas`；consensus+committee 步骤去重；输出 `low_participation` 警告。
- **Regime double-count**：`build_consensus_weights` 仅通过 65/35 blend 应用一次 regime overlay。
- **Sidebar precedence**：profile `sidebar_collapsed` 权威覆盖 stale `localStorage`。
- **MCP manifest**：`.mcp.json` 补齐 `augur_workflow`（10 tools）。
- Dashboard/registry 主路径移除 `scanner.*` fallback import；`scanner/` 标记 legacy。

### Notes
- Peer reviews: `docs/reviews/peer-review-*.md` (6/9 submitted).
- Tests: run `tests/test_v10_14*.py tests/test_*v10_15*.py tests/test_workflow_enabled_personas.py`.

## [10.13.0] - 2026-06-09

跨页面 Ticker 导航：Signals / History → Stocks 一键分析。

### Added
- **Signals 页面 ticker 链接**：自选股信号表中，代码列变为可点击链接（橙色下划线），跳转到 `/stocks?ticker=X`，stocks 页面自动触发分析（已有 URL 参数 auto-run 逻辑）。
- **History 页面 ticker 链接**：历史记录表中，代码列同样变为链接，`stopPropagation()` 防止触发展开行。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.12.0] - 2026-06-09

Scanner + Stocks 一键加入自选股。

### Added
- **Scanner → Watchlist**：扫描结果每行 Ticker 旁新增 `+` 按钮，点击直接调用 `/api/watchlist/add` 加入自选股，成功显示 toast 提示。
- **Stocks → Watchlist**：分析完成后 Header 按钮区出现"+ Watchlist"按钮（默认隐藏），点击将当前 ticker（含 PE/ROE/Price/MarketCap）加入自选股，添加成功后按钮变为"✓ Watchlist"并禁用避免重复。
- i18n: scanner-add-watchlist / scanner-added-watchlist / stocks-add-watchlist / stocks-added-watchlist 等 (zh+en)。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.11.0] - 2026-06-09

Compare 页因子级雷达修复 + 因子明细展开。

### Fixed
- **`_FACTOR_MAP` / `_catAvg` 作用域 bug**：两个变量定义在 `renderRadarChart` 内部，`renderFactorBreakdown` 无法访问（ReferenceError）——导致因子明细表格静默失效。将 `_FACTOR_MAP`、`_INVERT`、`_catAvg` 提升至模块作用域，因子真实分现在正确渲染。

### Added
- **因子明细展开按钮**：compare 页雷达图下方新增"▶ 展开因子明细"按钮（默认收起），展开后显示按类别（估值/成长/质量/动量/安全）分组的因子分表格，每个值附带彩色 mini 进度条（绿/橙/红）。
- i18n: compare-factor-toggle / compare-factor-collapse (zh+en)。

### Notes
- `metadata.factors` 已存在于所有 18 个 agent 的分析结果中，无需 API 改动。
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.10.0] - 2026-06-09

18 预生成 Hermes agent YAML + skill manifest 更新。

### Added
- **`hermes-agents/` 目录**：18 个预生成 Hermes Studio agent YAML（每位投资人一个文件），`cp hermes-agents/*.yaml ~/.hermes/agents/` 即可，无需跑任何命令。每个 YAML 包含完整 system prompt、MCP 工具依赖（`augur-mcp`）、语言标注（4 位中国投资人为 zh）。
- **hermes-setup-guide 更新**（中/英）：新增方式二"独立 Agent（预生成 YAML）"，所有方式编号重排（现共 6 种方式）。

### Changed
- **所有 skills/*/manifest.json**（19 个）：`command` 改为 `augur-mcp`，移除 `args: [mcp-server]`，与 v10.9 console script 对齐。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.9.0] - 2026-06-09

`augur-mcp` 独立 stdio 入口 + Hermes Studio 接入文档。

### Added
- **`augur-mcp` console script**：新增 `augur-mcp` 独立命令，作为 stdio MCP transport 专用入口，供 Hermes Studio / Claude Desktop / mcporter 等桌面 MCP 客户端直接 spawn（无需 `augur mcp-server` 子命令，兼容旧命令）。
- **`src/augur/mcp_entry.py`**：极简 stdio 启动器，`if __name__ == "__main__"` 直接调 `run_server()`。
- **Hermes Studio 接入文档**：hermes-setup-guide.md（中/英）补充 Option A（Hermes Studio / Claude Desktop）配置示例，更新全部示例命令为 `augur-mcp`。

### Notes
- `[project.entry-points."mcp.server"]` PEP 720 discovery 入口保持不变；新加的 `augur-mcp` 是给 stdio spawn 用的第二条路——两条路都通。
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.8.0] - 2026-06-09

键盘快捷键帮助 Modal。

### Added
- **键盘快捷键 Modal**：按 `?` 键（或侧边栏底部 `?` 按钮）弹出快捷键参考卡，列出所有可用快捷键（`/` / `Ctrl+K` 聚焦、`Ctrl+Enter` 提交、`Esc` 关闭、`1–6` 快速导航、`?` 显示帮助）。点击背景或按 Esc 关闭，四语言 i18n 支持。
- i18n: kbd-modal-title / kbd-focus-ticker / kbd-submit-analysis / kbd-close-panels / kbd-quick-nav / kbd-nav-pages / kbd-show-help / kbd-modal-close / kbd-or (zh+en)。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.7.0] - 2026-06-09

Stocks 页体验增强：最近分析 chips + URL 状态同步。

### Added
- **最近分析 chips**：stocks 页在"快速选择"下方显示"最近:"一行，展示最近 6 条已分析过的股票代码（localStorage 存储），点击可直接重新分析。每次分析成功后自动更新列表（去重 + 保持最新在前）。
- **URL 状态同步**：分析完成后通过 `history.pushState` 更新浏览器 URL 为 `/stocks?ticker=AAPL`，使当前分析可被浏览器记录/书签/分享；刷新页面会自动重新触发分析。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.6.0] - 2026-06-09

History 分析日历热力图。

### Added
- **History 日历热力图**：页面顶部新增 GitHub 贡献图风格的 52×7 日历格，按日期展示分析活动；绿色=看多、红色=看空、橙色=中性、灰色=无记录；点击有数据的日格过滤当日记录，"清除日期筛选"按钮恢复全览。
- 日历数据通过独立请求 `/api/history?per_page=365` 拉取最近 365 条，客户端按日期聚合，不影响分页主流程。
- i18n: history-cal-title / history-cal-clear (zh+en)。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.5.0] - 2026-06-09

Chat 对话导出与清除。

### Added
- **Chat 页 Export MD 按钮**：首条消息发送后显示"⤓ Export MD"按钮，将对话记录（含 Agent 名称/用户问题/Agent 回复）下载为 Markdown 文件，文件名含 Ticker 和日期。
- **Chat 页 Clear 按钮**：清空 DOM 消息和 `_chatHistory` 数组，恢复欢迎语，隐藏 Export/Clear 按钮。
- `_chatHistory` 数组在 `sendMessage()` 中维护；`_showChatActionBtns()` 首消息后显示按钮。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.4.0] - 2026-06-09

委员会报告导出 + 优化器权重 CSV 导出。

### Added
- **Committee 报告导出**：委员会裁决出来后显示"复制报告"和"导出报告"两个按钮；Markdown 格式含裁决摘要（信号/评分/置信度/Kelly/投票）及各大师意见（关键发现/风险/推理）；支持 clipboard API + 降级。
- **Optimizer 权重 CSV 导出**：最优组合计算后显示"Export CSV"按钮，输出 Ticker/Weight_% / 年化收益率/波动率/Sharpe 等字段。
- `_committeeVerdict`、`_committeeOpinions`、`_committeeTicker` 全局变量存储委员会会话状态；`_buildCommitteeMarkdown()` 统一构建报告内容。
- `_optWeights`、`_optMeta` 全局变量存储优化器计算结果。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.3.0] - 2026-06-09

导出功能扩展：信号监控 CSV + 辩论记录复制/下载。

### Added
- **Signals 信号监控 CSV 导出**：页面顶部"导出 CSV"按钮，包含 Ticker/PE/ROE/毛利率及分析信号/评分/投票数，UTF-8 BOM 兼容 Excel。
- **Debate 辩论记录导出**：辩论完成后显示"复制记录"和"下载 MD"两个按钮；Markdown 格式含各轮 Agent 评分与推理，支持 clipboard API 及 fallback。
- `_debateData` 全局变量存储最近辩论结果，`_buildDebateMarkdown()` 统一构建 MD 内容。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.2.0] - 2026-06-09

数据可视化与导出增强：IC 柱状图、回测/扫描器 CSV 导出。

### Added
- **Performance 页 IC 柱状图**：排行榜下方新增 Chart.js 水平柱状图，按 IC 60d 排序展示各 Agent 得分，绿色正 IC / 红色负 IC，主题切换自动重绘。
- **Performance 页 CSV 导出**：排行榜"导出 CSV"按钮，下载包含 Rank/Agent/IC_60d/Accuracy/Signals 的 UTF-8 BOM CSV。
- **Backtest 排行榜 CSV 导出**：IC 排行榜卡片头部"导出 CSV"按钮，文件名含标的+天数+日期，包含全部 IC 字段。
- **Scanner 扫描结果 CSV 导出**：扫描结果区"导出 CSV"按钮，输出 Ticker/Consensus/Score + 各 Agent 得分列。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.1.0] - 2026-06-09

功能扩展：因子细分、历史搜索、设置外观、持仓/自选导出。

### Added
- **Compare 因子细分表**：雷达图下方展示每个维度的实际因子得分（0-10，颜色编码），按 valuation/growth/quality/momentum/safety 分组，仅当存在真实 metadata.factors 时显示。
- **History 搜索/筛选**：ticker 搜索框（防抖 300ms）+ bullish/neutral/bearish 信号筛选片；后端 `/api/history` 新增 `ticker` 和 `signal` 查询参数，`history.py` 的 `list_history`/`count_history` 支持 ticker_filter + signal_filter。
- **Settings 外观设置区块**：设置页顶部新增语言选择器（4 语言按钮组）和主题选择器（深色/浅色），active 状态橙色边框高亮。
- **Portfolio CSV 导出**：持仓页"导出 CSV"按钮，包含 Ticker/Shares/Avg Cost/Current Price/Market Value/P&L/Buy Date，UTF-8 BOM 兼容 Excel。
- **Watchlist CSV 导出 + 导入**：自选股页导出（ticker 列表 CSV）+ 文件选择导入（支持逗号/换行/分号分隔，自动去重，验证 ticker 格式）。

### Changed
- **Compare `_FACTOR_MAP` 完整覆盖**：新增所有 18 个 persona 的 factor key 映射（duan_yongping/fisher/li_lu/lynch/marks/munger/soros/thiel/zhang_lei/dayu/serenity），`_INVERT` 增加 `supply_chain_bottleneck`。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.0.0] - 2026-06-09

v10 首发：日语/韩语国际化支持，四语言循环切换（中/英/日/韩），降级链机制。

### Added
- **日语 (ja) i18n**：181 个 key 的完整日语翻译，覆盖导航、委员会、股票分析、回测、对比、历史等全页面。
- **韩语 (ko) i18n**：181 个 key 的完整韩语翻译，与日语覆盖范围一致。
- **四语言循环切换**：语言 toggle 按钮由 zh↔en 双向切换升级为 zh→en→ja→ko→zh 循环；`localStorage` 持久化四种语言选择。
- **浏览器语言自动检测**：`navigator.language` 自动识别 zh/ja/ko/en，首次访问按浏览器偏好设语言。
- **降级链机制**：`t()` 和 `applyLanguage()` 支持 ja/ko → en → zh 三级降级，缺失 key 优雅回落到英文。
- **Agent detail modal（stocks 页）**：点击任意 agent scorecard 弹出详情 modal，展示 key_findings / risks / reasoning；ESC 或点击遮罩关闭。

### Changed
- **i18n.js 架构**：`toggleLanguage()` 改为基于 `_LANG_CYCLE` 数组的循环逻辑；`applyLanguage()` 重构为通过内部 `_getVal()` 函数支持降级；`html[lang]` 属性正确映射到 `zh-CN` / `en` / `ja` / `ko`。
- **测试 fixture 适配**：6 个测试文件的 `i18n_dicts` fixture 更新为仅解析 zh 和 en 块（边界到 `\n    ja:`），避免 ja/ko 覆盖 en 解析结果。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [9.1.0] - 2026-06-09

UI 全面升级：CSS token 统一、亮色模式修复、图表交互增强、Toast 升级、空状态统一。

### Added
- **Chart.js 主题联动**：主题切换时触发 `augur:theme-change` 事件，compare 雷达图与 stocks 历史图自动重绘以匹配新主题。
- **Ticker Tape 暂停 UX**：悬停自动暂停（amber overlay 反馈）；点击暂停显示居中 `⏸ 已暂停` badge；修复 hover-pause / click-pause 状态冲突。
- **Stocks 历史走势图交互**：点击数据点弹出摘要（日期/评分/信号）；30天/全部 range 切换；主题切换自动重绘。
- **Toast 通知升级**：4 种类型（✓ success / ⚠ warning / ✗ error / ℹ info）+ 对应颜色左边框 + icon 前缀；多条同时出现时垂直堆叠偏移。
- **空状态 SVG 插图统一**：history / watchlist / scanner 三页 emoji → Bloomberg 终端风格 inline SVG 线稿（时钟 / 剪贴板 / 放大镜）。
- **移动端底部导航收敛到 5 个 tab**：home / stocks / committee / history / settings；激活 tab 底部橙色圆点指示。

### Changed
- **CSS token 统一**：`colors_and_type.css` 成为唯一权威来源；补全所有 legacy alias（`--accent-*` / `--font-data` / `--radius-*` / `--transition-speed` / `--sidebar-width` / `--border-subtle` / `--bg-surface`）；`bloomberg.css` `:root` 和 `html.light` 整块替换为注释。
- **亮色模式完整性**：`ui-enhance.css` ticker-tape-pause 按钮背景改用 `var(--bg-card-hover)`；colors_and_type.css 补充 `--oracle-purple` / `--crystal` 亮色覆写；所有硬编码暗色 overlay 替换为 CSS var。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [8.2.3] - 2026-06-07

Chat 数据卡片、UI inline style 清理、Scanner 边界加固、后端线程安全。

### Added
- **Chat 数据卡片**：对话页顶部嵌入实时行情卡片（价格、涨跌幅、Augur 共识信号+评分），60 秒自动刷新；分析结果 localStorage 缓存 10 分钟；任何 fetch 失败均静默隐藏。

### Fixed
- **Scanner 边界加固**：大小写不敏感去重（AAPL+aapl→1条）；单个 ticker 失败不影响整批扫描，失败列表记录在 `response.errors[]`。
- **后端线程安全**：`get_registry()`/`get_coordinator()` 双检锁（double-checked locking）；自定义 persona CRUD 操作包裹 `_singleton_init_lock`；`history.py` 改为 tmp+`os.replace()` 原子写，加 `_write_lock`。

### Changed
- **UI inline style 清理（MEDIUM 优先级）**：
  - `backtest.html`：30+ 处 inline style → `.backtest-form-row`/`.form-error-hint`/banner 类。
  - `create_persona.html`：`.cp-label`/`.required-star` 替代 verbose inline 标签样式。
  - `chat.html`：`.oracle-section-title`/`.oracle-welcome` 替代 inline h3/p 样式。
  - `history.html`：`.ticker-cell` 替代 JS 动态注入的 inline style。

### Notes
- Tests: **1652 passed**（排除网络测试）。

## [8.2.2] - 2026-06-07

全面整合 Loop 400 遗留代码、Optimizer 可视化、UI/UX 修复、Rules→Bot 打通。

### Added
- **Optimizer 有效前沿图**：`/optimizer` 页新增 Chart.js 散点+折线图，展示 Markowitz 有效前沿曲线，金色星标最优组合点，绿色圆点为各资产，蓝色折线为前沿边界。API 新增 `frontier_points`（40条前沿点）、`asset_points`、年化收益/波动率字段。
- **Rules→Bot 打通**：`/api/analyze/{ticker}` 与 `/api/watchlist/run` 现在在每次分析后自动触发 RulesEngine.evaluate()，满足条件即推送通知到 Telegram / Slack / WeChat / Lark（fire-and-forget，不阻塞响应）。

### Fixed
- **UI/UX 对比度**：orange 背景上 `color:#000/#fff` 全部替换为 `var(--bg-void)` / `var(--fg-1)`（WCAG AA 合规）。受影响页面：stocks、scanner、personas、optimizer、settings。
- **CSS 变量化**：debate/compare 硬编码 `rgba` → `var(--amber-wash)`；optimizer 5处 `#34c759/#ff9500/#5ac8fa/#ff3b30` → CSS 变量；index breadth bars `#fff` → `var(--bg-void)`。
- **页面标题统一**：personas.html 内联 `style="font:var(--h1)..."` → `.page-title` / `.page-lead` 标准类。
- **i18n 冲突解决**：合并 stash@{1} 带来的 i18n.js +238行新翻译键；修复 Jinja 模板表达式被当作 i18n literal 键的测试误报。
- **signals.html**：移除重复的 `.signals-header` inline CSS（已由 `layout.css` 的 `.page-header` 覆盖）。

### Changed
- Loop 400 stash 遗留代码（约 34 文件）全部合并进 main，解决 10 个冲突文件。
- compare.html：URL 参数 `?autorun=1` 支持自动触发对比分析。
- scanner.html：新增 `.heatmap-cell.error` 错误状态样式。

### Notes
- Tests: **1657 passed**（v8.2.1 为 1362，新增 295 项测试）。
- 新增 `tests/test_report_export_ux_v1.py`（报告导出 UX 回归套件）。

## [8.2.1] - 2026-06-06

Loop 200 review patch. 200-round multi-agent code review + UX walkthrough on top of v8.2.0.

### Fixed
- **Layout:** Sidebar and main content aligned via CSS Grid (`240px + 1fr`, gap 0); collapsed sidebar uses unified `--sidebar-width` token.
- **Report contrast:** Light-mode parchment + pale text unreadable; added `--report-*` semantic tokens and theme-aware SVG via `reportThemeColor()`.
- **Backend:** Price-series NaN/Inf sanitization, consensus tie → `NEUTRAL`, coverage-confidence normalization, persona YAML bool weights, sample-insufficient report messaging.
- **Auth:** WebSocket `/ws/prices?token=` validation; Dashboard fetch/WebSocket interceptors aligned with `augur.auth`; `GET /api/auth/config` discovery endpoint.

### Changed
- **UX / i18n / a11y:** Global `_t()` export, progress/copy i18n keys, empty-state parity across portfolio/compare/history/debate, 44px touch targets, reduced-motion support, stocks page `data-i18n`, mobile table scroll hints.
- **Pages:** Settings (redundant PUT removed), Scanner (explicit event args), Signals (reordered flow), Backtest (min capital validation), index onboarding/AAPL CTA, partial `data_error` surfacing.

### Notes
- Tests: **1362 passed** (up from ~1177 in v8.2.0).
- Review reports: [`docs/LOOP_200_REPORT.md`](docs/LOOP_200_REPORT.md) (complete) · [`docs/LOOP_400_REPORT.md`](docs/LOOP_400_REPORT.md) (partial — stash recovery pending).
- README screenshots refreshed for v8.2.1 grid layout and report contrast (see `scripts/capture_readme_screenshots.py`).

## [8.2.0] - 2026-06-06

v8.2.0 release. Version bump from 8.1.0 to 8.2.0.

### Added
- AI Chat with 11 personas, Portfolio Optimizer (Markowitz), Master Compare,
  Debate Mode, History, Leaderboard (dashboard pages).
- LearningEngine (IC-based weight auto-tuning), SentimentAnalyzer (social
  sentiment fusion), WebSocket price streaming at `/ws/prices`, RulesEngine
  (DSL alerts with multi-channel notifications).
- HD-2D design system: `ExecCard`, `OracleSays`, `ScorecardGrid` components,
  layout spacing fix (240px gap), adaptive color variables
  (`var(--signal-buy)`, `var(--signal-sell)`), responsive breakpoints
  (768px / 480px), bilingual number/date formatting.
- Persona audit, makefile, pyproject polish, and analyzer/ws prices work
  (rounds 11–12).

### Changed
- Bumped package version from 8.1.0 to 8.2.0 in `src/augur/__init__.py` and `pyproject.toml`.
- Added this `CHANGELOG.md` to document release history.

### Notes
- No breaking changes vs 8.1.0.
- All 1177 existing tests remain green.

## [8.1.0] - 2026-06-06

Round 7 release. Rate limiting, data error UX, agent registry, dashboard a11y,
route validation, branded 404/500, chat docstrings, learning log, rules YAML.
