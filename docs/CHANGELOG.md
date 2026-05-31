# Changelog

All notable changes to the Augur project are documented here.

---

## v7.8.0 (2026-06-01) - Bloomberg级可视化 & API Token & 自定义Persona CRUD

### 📊 Dashboard Bloomberg-Level Enhancement
- SVG 半圆恐慌贪婪仪表盘（Fear & Greed Gauge），颜色渐变 + 指针动画
- Market Pulse 数据脉搏条（S&P 500, VIX, 10Y, Gold, BTC 一行速览）
- 国际市场面板（亚洲: HSI, Nikkei, CSI300 | 欧洲: FTSE, DAX）
- 板块热力图增强（mini-bar 涨跌幅可视化 + tooltip）
- 新增 GET /api/fear-greed 独立端点

### 🎭 Custom Persona CRUD (自定义投资人完整管理)
- GET /api/custom-personas 列出所有自定义投资人
- PUT /api/custom-persona/{id} 编辑更新
- DELETE /api/custom-persona/{id} 删除
- 创建页面显示已有自定义 Persona 列表（编辑/删除）
- 人格列表页 "CUSTOM" 紫色徽章区分

### 🔐 API Token Authentication (API 认证)
- AUGUR_API_TOKEN 环境变量配置
- 中间件拦截 /api/* 请求验证 Bearer Token
- 未设置 Token 时完全开放（向后兼容）
- GET /api/auth/verify Token 验证端点
- 前端 fetchWithTimeout 自动携带 localStorage Token
- Settings 页面 Token 配置面板

### 🐳 Docker & Deploy
- docker-compose.yml 传递 AUGUR_API_TOKEN
- .env.example 补充 AUGUR_API_TOKEN 说明

### 🎨 UI Polish & QoL
- 全面板空状态优雅处理（图标 + 提示文案）
- JS 错误处理增强（localStorage 安全访问）
- CSS 一致性检查（统一 radius/padding/color）
- 移动端响应式完善（768px/480px 断点）

### 📖 Documentation
- docs/single-persona-integration.md 更新：MCP/REST/Python SDK/Hermes/OpenClaw 集成指南
- README 功能一览清单

---

## v7.7.0 (2026-06-01) - 持仓管理 & 深度交互 & 专业报告

### 💼 Portfolio Management (持仓管理)
- 新增 /portfolio 页面，支持持仓追踪（标的、买入价、数量、买入日期）
- 实时盈亏计算（通过 yfinance 获取当前价格）
- 总资产概览（已投资、当前市值、盈亏、回报率）
- SVG 折线图展示 7 日加权持仓价值曲线
- SVG 环形图展示资产配置（stroke-dasharray 圆环）
- "运行 Augur 分析" 按钮对持仓全量进行 18 大师评分
- localStorage 数据持久化，表格排序

### 🎭 Persona Deep Interaction (人格深度交互)
- 人格卡片 "Ask Question" 功能 - 向单个大师提问
- "Compare Two Masters" - 两位大师对同一标的的并排对比
- GET /api/persona/{id}/opinion 端点，单 Agent 分析
- GET /api/persona/compare 端点，双 Agent 对比

### 🔔 Notification & Cron Optimization (通知与定时任务优化)
- 修复定时通知阈值过滤逻辑（仅在评分 >= 阈值时告警）
- 设置页新增 "定时监控" 配置区域
- GET/PUT /api/cron/config 定时任务配置管理端点
- POST /api/cron/run-now 立即触发自选股分析

### 📊 Dashboard Data Enrichment (首页数据增强)
- 板块表现热力图（11 个板块 ETF，颜色编码涨跌幅）
- Top Movers（涨跌幅排行，来源于热门标的）
- Market Breadth 市场宽度指标（上涨/下跌比率条形图）
- Augur Consensus Leaderboard（localStorage 历史最高评分排行）
- 国际指数新增：FTSE、DAX、Nikkei

### 📄 Report Visualization (报告可视化)
- 独立 /report/{ticker} 全页报告视图
- 专业样式：评分仪表盘 SVG、信号徽章、可折叠区域
- 下载为 Markdown（.md 文件）
- 下载为 HTML（自包含内联暗色 CSS）
- 复制报告到剪贴板
- Agent 投票表格，带颜色信号指示

### 🎨 UI Polish (界面打磨)
- 全局表格排序工具函数 (initSortableTable)
- 所有路由（含 /portfolio）的活跃导航高亮
- 全部新页面统一 Bloomberg 暗色主题

---

## v7.6.0 (2026-06-01) - 自选股 & 可视化 & 导出增强

### 📋 自选股 Watchlist
- 新增 /watchlist 页面，支持添加/删除自选股
- 数据存储在 localStorage，无需注册登录
- "一键全部分析" 批量对自选股运行 18 位大师共识评分
- 每个标的展示：代码、公司名、当前价、涨跌幅、最后评分

### 📈 迷你走势图 Sparkline
- 新增 /api/sparkline/{ticker} 端点，返回最近 7 个交易日收盘价
- 首页热门标的卡片内嵌 SVG polyline 迷你走势图
- 自选股列表同样展示 sparkline
- 上涨绿色、下跌红色、横盘黄色

### 📊 历史分析对比
- stocks.html 新增"历史对比"面板
- 从 localStorage 缓存提取同一标的不同时间的分析记录
- 表格展示：日期、评分、信号、价格

### 📦 报告导出增强
- 新增"导出为 JSON"按钮（结构化分析数据，方便程序化处理）
- 新增"导出为 CSV"按钮（18 位大师评分表格）
- 纯前端 Blob URL 实现，无需后端支持

### 🔍 SEO & Open Graph
- base.html 添加完整 meta 标签：description、keywords、og:title/description/image/type、Twitter Card
- 新增 /robots.txt 和 /sitemap.xml 静态路由
- 每个页面 <title> 确保唯一且有意义

### 🏷️ 代码质量
- data.py 所有公开函数添加完整 type hints 和 docstring
- app.py 所有端点添加 OpenAPI summary 注释
- 新增 py.typed 标记文件（PEP 561，支持 mypy/pyright）

### 🔧 版本
- 版本升至 v7.6.0

---

## v7.5.0 (2026-06-01) - 国际化 & 安全 & Scanner 大版本升级

### 🌐 国际化 (i18n)
- 侧边栏语言切换按钮 (中/EN)，纯前端 JS 实现
- 所有静态文案支持中英文切换，data-i18n 属性体系
- 语言偏好存 localStorage，默认跟随浏览器语言

### 🔍 Scanner 市场扫描器
- 新增 /scanner 页面与 /api/scanner/run API
- 预设列表: 科技巨头 / 中概股 / 加密货币
- 18 位大师并行评分，结果以 heatmap 热力表展示
- 支持自定义标的列表 (最多 20 个)

### ⚡ 性能优化
- /api/market-overview 和 /api/hot-tickers 支持 ETag + 304 条件请求
- CSS/JS 静态资源添加 ?v=7.5.0 版本参数，解决浏览器缓存问题
- 新增 fetch_market_context_batch() 并发数据获取 (ThreadPoolExecutor)

### 🔒 安全加固
- IP 级别全局限流: 每 IP 每分钟最多 30 次 API 请求
- CORS 中间件: 默认允许所有来源，可通过 AUGUR_CORS_ORIGINS 环境变量配置
- API Key 脱敏: 配置接口中的密钥仅显示尾部 4 位 (***xxxx)
- 输入校验: ticker 格式正则验证 (防 XSS/注入)

### 🔔 通知系统
- POST /api/notifications/test 测试通知通道 (telegram/slack/lark/wechat)
- POST /api/notifications/config 保存通知配置到 config/notifications.yaml
- Signals 页面新增告警阈值设置 (评分 > N 时通知)

### 📄 报告与文档
- 报告页新增"下载报告"按钮 (导出为 .md 文件)
- 报告页新增"复制报告"按钮
- 新增 docs/api-reference.md API 完整参考文档
- 增强 docs/single-persona-integration.md 单 Agent 集成指南
- README.md / README_EN.md 更新

### 🔧 版本
- 版本升至 v7.5.0

---

## v7.4.0 (2026-06-01) — 全面深度升级

### 🎴 Personas 页面深度改造

- **卡片式布局**：18 位投资大师全部以卡片形式展示，含 SVG 头像、中英文名、投资风格、核心理念、代表性持仓
- **流派过滤器**：按价值/成长/宏观/量化/中国五大流派快速筛选
- **一键分析按钮**：每位大师卡片带"一键用TA的视角分析"直达分析页
- **搜索功能**：实时搜索大师名字/风格/ID

### 📈 Backtest 回测增强

- **参数配置面板**：初始资金（默认 10 万美元）、仓位策略选择（均等/Kelly/固定比例）、扩展时间范围（30-365 天）
- **关键指标卡片**：年化收益率、最大回撤、夏普比率、胜率四大核心指标可视化
- **历史信号时间线**：按时间顺序展示过去的买/卖信号记录

### ⚙️ Settings 设置完善

- **数据源 API Key 配置**：Finnhub / Alpha Vantage API Key 管理 + 测试连接按钮
- **通知渠道配置**：Telegram Bot Token / Slack Webhook / 微信配置（含测试按钮）
- **导出/导入配置**：一键 JSON 导出与导入，方便备份迁移
- **保留 LLM 模型分配**：原有的 per-agent 模型配置完整保留

### 📡 Signals 信号监控增强

- **信号统计摘要**：顶部面板显示总信号数、BUY/SELL/HOLD 占比条、平均评分
- **过滤器**：按信号类型（BUY/SELL/HOLD）过滤，按评分/代码排序
- **信号详情展开**：点击行可查看各 Agent 评分明细

### 🎨 全局 UX 优化

- **深色/浅色主题切换**：侧边栏 toggle 按钮，localStorage 记忆偏好
- **全局加载进度条**：页面顶部动画进度条，AJAX 请求自动显示/隐藏
- **统一 hover 动效**：所有卡片统一 translateY(-2px) + shadow 微动效
- **快捷键增强**：/ 聚焦搜索、Esc 关闭弹窗、数字键快速导航

### 🔧 代码健壮性

- **API 错误处理**：全局 422/404/500 异常处理器返回一致 JSON 格式，不泄露堆栈信息
- **缓存 TTL 增强**：`cache_stats()` 提供缓存条目年龄与过期状态监控
- **/api/health 扩展版**：返回数据源可达性、缓存状态、运行时间、版本号

### 📝 版本与文档

- 版本升至 v7.4.0
- README.md / README_EN.md 添加 Dashboard 预览占位
- CHANGELOG 更新记录完整变更

---

## v7.3.1 (2026-06-01) — Dashboard 数据密度 & 报告深化

### 📊 Dashboard Data Density

- **热门标的实时行情**：首页新增 10 大热门股票/ETF 实时卡片（AAPL, NVDA, TSLA, MSFT, GOOGL, AMZN, BTC-USD, ETH-USD, META, AMD），展示价格与涨跌幅
- **恐慌与贪婪指标**：基于 VIX 指数自动判断市场情绪（贪婪/中性/恐慌），辅以美元指数与美债收益率
- **宏观经济快照**：黄金、原油、BTC 独立卡片 + 自动解读文字（避险需求/能源压力等）
- **新增 /api/hot-tickers 端点**：10 大热门标的实时数据 API

### 📈 Report Visualization Enhancement

- **投资风格标签**：每位大师评分卡片增加风格标签（价值投资/成长投资/宏观对冲/技术分析等）
- **关键财务指标面板**：报告头部展示 PE、PB、ROE、毛利率、市值等核心数据
- **打印优化**：@media print 样式隐藏导航/侧边栏，防止卡片被分页截断
- **复制报告链接**：一键生成带 ticker + 时间戳的分享 URL

### 🎨 UX Polish

- 首页板块重排：精选投资人移至数据源之前
- 版本号统一升级至 v7.3.1
- 所有页面 <title> 统一规范化
- Sidebar footer 添加 "Powered by Augur" 标识

---

## v7.3.0 (2026-06-01) — 公开发布版

Dashboard 全面增强 + 报告可视化升级 + 多数据源链路 + 文档完善。

### 📊 Dashboard Enhancement

- **数据源状态面板**：首页实时显示 yfinance / Finnhub / Alpha Vantage / Stooq 各数据源连接状态与健康度
- **快速分析热门标的**：预置 GOOGL / BTC-USD / 00700.HK / BABA 一键分析按钮
- **响应式移动布局**：全面适配手机端浏览，卡片网格与表格自动调整列数
- Engine 版本状态栏更新至 v7.3.0

### 📈 Report Visualization

- **18 位大师评分卡片网格**：每位大师独立可视化评分卡（分数 / 信号 / 流派标签）
- **Bull vs Bear 双栏辩论布局**：最看好 vs 最谨慎的大师观点对照展示
- **风险矩阵卡片**：结构化风险因子（流动性/估值/周期/竞争）可视化
- **执行摘要头部卡片**：核心结论高亮，一目了然
- **PDF 下载**：基于 window.print 优化打印样式，隐藏导航栏/侧边栏
- **Markdown 下载**：一键导出完整分析报告为 .md 文件

### 🔗 Multi-datasource

- 多数据源链路：yfinance（主） + Finnhub（可选） + Alpha Vantage（可选） + Stooq（兜底）
- 数据源自动降级：主源请求失败或超时时自动切换至下一源
- 新增 `src/augur/datasources/finnhub_provider.py` 和 `alphavantage_provider.py`

### 📚 Documentation

- 双语 README（中文 / 英文）同步至 v7.3.0
- 新增 `docs/single-persona-integration.md`：单个投资人 Agent 接入指南（Hermes / Open Claw / Claude Desktop 三种方式）
- 新增 `docs/data-sources.md`：数据源配置与 API Key 说明

### 🐛 Bug Fixes

- 修复 datasources 模块中 provider import 路径错误
- 修复 yfinance_provider 中 NaN 值未被 safe_num 清洗的边界情况
- 修复 base persona 类型注解兼容性（Python 3.8+）

---

## v6.1.0-final (2026-05-28) — 正式发布版

经过 **30 + 50 = 80 轮** 深度 Review、Debug、功能补全。

### 🐛 关键 Bug 修复

**数据精度 (data.py)**
- `debt_ratio` D/E 误用为 D/A → 改为正确的 `D/(D+E)` 转换公式
  - AAPL: 79.5% → 44.3%（真实资产负债率）
- `short_interest` 字段错误：`shortRatio`（换手天数）→ `shortPercentOfFloat`（空头占比）
- `macd_histogram` 字段缺失：yfinance 已计算但忘记传入 MarketContext
- 新增 8 个字段：`revenue`, `quick_ratio`, `institutional_ownership`, `insider_ownership`,
  `short_interest`, `beta_1y`, `price_vs_52w_high`, `price_vs_52w_low`

**核心逻辑 (registry.py / personas/)**
- `dayu.py`: market_cap 阈值用原始美元（500_000_000）→ 改为十亿单位（0.5）
- `serenity.py`: `debt_ratio < 60` → `< 0.60`（之前覆盖了惩罚逻辑）
- `dalio.py` / `munger.py`: scoring_weights 键名对齐 + 启用加权评分
- `zhang_lei.py` / `dan_bin.py`: reasoning 硬编码阈值 → 读 `self.thresholds`
- `soros.py`: reasoning 格式化统一为 `{factor:.1f}/10`
- `cron.py`: `add_to_watchlist()` 更新已有 ticker 后未调用 `save_watchlist()`
- `backtest.py`: PB 公式 `PE × ROE / 100 * 10` → 正确的 `PE × ROE`
- `registry.py`: `ctx_for_risk` 作用域 NameError 修复

**Kelly 仓位建议**
- 之前永远返回 N/A（依赖不存在的 `scanner.kelly_sizer`）
- 内联实现 half-Kelly 公式：`min(20%, 0.5 × edge × confidence × 100)`
- BULLISH 信号且 score > 5 时给出非零建议

**线程安全 (config.py)**
- `get_config` / `set_config` / `save_config` / `reset_config` 添加 `RLock` 保护
- 修复多并发请求时的竞态条件

### ✨ 新增功能

**MCP Server (6 → 7 工具)**
- 新增 `augur_fetch`：仅获取实时数据不分析
- `augur_consensus`：返回新增 Kelly 仓位
- `augur_analyze`：单 persona 模式返回完整 key_findings + risks
- `augur_debate`：补全 reasoning 输出

**CLI (15 → 20 命令)**
- 新增 `--json` 输出选项：`analyze` 和 `consensus` 支持机器可读输出
- 新增 `--sector` / `--industry` 参数
- 新增 `watchlist-show` 命令
- `consensus` 输出新增 Kelly Size 行

**Dashboard (7 页 + 25+ API)**
- 分析结果新增「导出 JSON」按钮（Blob 下载）
- `create-persona` 提交后热加载到运行中的 registry（无需重启）
- `/api/watchlist/run` 结果持久化 `last_signal` / `last_score` / `last_run`
- `stocks.html` 读取 URL 参数 `?persona=buffett`
- 新增 `industry` 输入框（细分行业）
- `personas.html` 「分析」按钮跳转后不再触发空 ticker 警告
- `signals.html`: ROE/毛利率单位换算修复 + placeholder 加 `%` 提示

**Telegram Bot 增强**
- 无指标参数时自动 yfinance 获取数据（之前全零分析）
- 补全 `serenity` / `arps` 的 AGENT_EMOJI 和 PERSONA_MENTIONS 映射

**Dashboard UI/UX**
- `bloomberg.css`: 新增 6 个 CSS 变量（`--accent-green/blue/red/yellow/bg-tertiary`）+ 3 个类
- `backtest.html`: 删除本地 `.btn-primary` 蓝色覆盖（恢复全局橙色主题）
- `backtest.html`: `consensus_ic` null check（防 `.toFixed()` 崩溃）
- `settings.html`: Promise.all 部分保存失败时明确提示失败数量
- `base.html`: 键盘导航 navMap 添加 `/signals` 页面
- `create_persona.html`: 双栏布局改为 `auto-fill minmax(360px, 1fr)`（移动端不溢出）
- `base.html`: 新增 `renderMarkdown()` 函数，分析结论以格式化 Markdown 展示

### 📚 文档

- 全面重写 README.md / README_EN.md（双语同步）
  - 新增真实运行效果示例
  - 新增「为什么是 Augur」对比表格
  - 18 位投资人改为可折叠分组（经典价值/成长创新/宏观周期/中国/特殊）
  - CLI 命令表扩充到 20 个
  - 完整 Dashboard API 端点列表（16+ 端点）
  - 参数约定表格（正确 vs 错误示例对比）
  - 7 个常见问题折叠展示
- 新建 [CONTRIBUTING.md](../CONTRIBUTING.md)：贡献指南 + PR 流程
- SKILL.md 版本号同步至 6.1.0
- 修正 CHANGELOG 年份 2025 → 2026
- README 修正市值单位（亿 USD → 十亿 USD），示例数字 28000 → 2800

### 🔧 兼容性

- 远程 v6.1.0 (`src/augur/personas/`) 主架构
- 本地 `scanner/personas/` 作为 backward-compat shim
- `augur-mcp` 命令通过 `main = run_server` 别名保持兼容

---

## v6.1.0 (2026-05-28) — 初始发布

### Release Summary
10 iterative Review-Debug-Fix-Optimize loops completed. All known bugs fixed, 
input validation added, test coverage expanded from 55 to 78+ tests, 
documentation verified accurate.

### Highlights
- Zero known issues remaining
- Input validation on all API endpoints (ticker format, length limits)
- Accessibility improvements (aria-labels, meta tags)
- Double-submit prevention in UI
- Comprehensive test suite covering backtest, data calculations, cron, soul injection
- All 18 personas verified working correctly
- Signal value consistency fixed across all endpoints

---

## v6.0.1 (2026-05-28)

### Bug Fixes
- Fix critical signal value mismatch in watchlist analysis (`bullish`/`bearish`/`neutral` vs `buy`/`sell`/`hold`)
- Fix `src/augur/api.py` version (was "0.1.0", now "6.0.0")
- Fix `current_ratio` default value inflation (1.5 -> 0)
- Fix CORS allow_methods to include PUT/DELETE
- Guard telegram_bot import in cron.py to prevent crash without extras
- Remove unused threading import from personas/base.py

### Improvements
- Add ticker format validation (regex, max 15 chars) on analyze/backtest/watchlist endpoints
- Add accessibility improvements (aria-label, meta description)
- Add double-submit prevention in stocks analysis UI
- Add section comments to registry.py get_consensus() for readability
- Add serenity to test expected agent IDs

### Test Coverage
- Add test_backtest.py (6 tests)
- Add test_data.py (6 tests)
- Add test_cron.py (3 tests)
- Add test_soul.py (4 tests)
- Add TestTickerValidation (4 tests)
- Total tests: 55 -> 78+

---

## v6.0.0 (2025)

- Bug fixes: TemplateResponse API deprecation, persona count consistency (17->18)
- UI/UX overhaul: one-click analysis, inline results display, loading skeletons, preset configurations
- Documentation restructure: professional README rewrite, dedicated CHANGELOG, updated integration guides
- All references updated to 18 agents
- Version bump across all modules

## v5.6

- 第18位投资人: Serenity (@aleabitoreddit) - AI/半导体供应链瓶颈交易
- 18th investor persona added to system

## v5.5

- 文档重构 + pyproject.toml 元数据完善
- Documentation overhaul + pyproject.toml metadata refinement

## v5.4

- 实时行情接入 (yfinance) - 自动获取美股/港股/A股数据
- Real-time market data integration via yfinance

## v5.3

- 个人微信接入 (GeWeChat) - 扫码即用, 三模式支持
- Personal WeChat integration (GeWeChat) - scan-to-use, 3-mode support

## v5.2

- UX打磨 - 键盘快捷键 + 骨架屏 + Score仪表 + 移动端
- UX polish - keyboard shortcuts + skeleton screens + score gauges + mobile support

## v5.1

- 历史回测系统 + Agent IC追踪 + 排行榜
- Historical backtesting system + Agent IC tracking + leaderboard

## v5.0

- Docker容器化 + docker-compose多服务编排
- Docker containerization + docker-compose multi-service orchestration

## v4.6

- 微信(企业微信+Webhook) + 飞书(Event+Webhook)
- WeChat (WeCom + Webhook) + Lark/Feishu (Event + Webhook)

## v4.5

- 信号监控页 + 自定义投资人UI + Watchlist API
- Signal monitoring page + custom investor UI + Watchlist API

## v4.4

- Bloomberg Terminal风格UI + Hermes侧边栏
- Bloomberg Terminal-style UI + Hermes sidebar

## v4.3

- Slack Bot (Socket+HTTP) + Cron推送
- Slack Bot (Socket + HTTP) + Cron push notifications

## v4.2

- Telegram Bot + Cron定时分析 + Watchlist
- Telegram Bot + Cron scheduled analysis + Watchlist

## v4.1

- Config REST API + Dashboard UI/UX优化
- Config REST API + Dashboard UI/UX improvements

## v4.0

- pip包化 + CLI + MCP Server + Soul Injector
- pip packaging + CLI + MCP Server + Soul Injector

## v3.5

- Baoyu漫画风格配图 + 投资人头像SVG
- Baoyu comic-style illustrations + investor avatar SVGs

## v3.4

- Skill封装 + 模型配置
- Skill encapsulation + model configuration

## v3.3

- FastAPI Dashboard (5页路由)
- FastAPI Dashboard (5-page routing)

## v3.2

- 4位中国投资人加入
- 4 Chinese investors added

## v3.0

- 正式更名Augur + 共识引擎
- Renamed to Augur + Consensus Engine

## v2.0

- 13位投资人人格系统
- 13-investor persona system

## v1.0

- 巴菲特单人格分析
- Buffett single-persona analysis
