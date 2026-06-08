# Changelog

All notable changes to augur-agents are documented in this file.

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
