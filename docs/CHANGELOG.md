# Changelog

All notable changes to the Augur project are documented here.

---

## v6.1.0 (2025-05-26)

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

## v6.0.1 (2025-05-26)

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
