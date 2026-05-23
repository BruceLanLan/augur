English | [中文](README.md)

<p align="center">
  <img src="https://img.shields.io/badge/v5.5-Latest-blue?style=for-the-badge" alt="v5.5"/>
  <img src="https://img.shields.io/badge/17-Investor%20Personas-brightgreen?style=for-the-badge" alt="17 Personas"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/pip%20install-augur--agents-orange?style=for-the-badge&logo=pypi" alt="pip install"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT"/>
</p>

<h1 align="center">Augur</h1>
<h3 align="center">Multi-Agent Investment Analysis System - 17 Virtual Investment Masters at Your Service</h3>

<p align="center">
  <img src="docs/images/hero-banner-baoyu.svg" alt="Augur" width="100%"/>
</p>

<p align="center">
  <em>17 AI Investment Masters (incl. 5 Chinese investors) | Multi-dimensional Consensus Analysis | Bloomberg-style Terminal Dashboard | Multi-platform Deployment</em>
</p>

---

## Quick Start

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
pip install -e .
augur analyze AAPL
```

---

## Core Features

| Feature | Description |
|---------|-------------|
| 17 Investor Personas | From value investing to crypto speculation, US equities to Chinese markets - each master has an independent personality and scoring logic |
| Multi-Agent Consensus | Industry-aware weighting + market regime routing + rolling IC dynamic weighting + diversity penalty |
| Real-time Data (yfinance) | Auto-fetches US/HK/A-share prices, valuations, fundamentals, and technical indicators |
| Bloomberg-style Dashboard | Dark-themed FastAPI interface with 7 pages covering the full analysis workflow |
| Backtesting + IC Tracking | Replay historical data, track each agent's prediction accuracy and rankings |
| MCP Server | 6 standard tools for direct invocation by Claude Desktop / Hermes |
| Multi-platform Bots | Telegram / Slack / WeChat (3 modes) / Lark/Feishu (2 modes) |
| Cron Scheduled Analysis | Watchlist monitoring + scheduled push notifications across all platforms |
| YAML Custom Personas | Create custom investment strategy agents via YAML - no coding required |

---

## 17 Investment Masters

| # | Investor | Skill | Style | Key Metrics | Recommended Model |
|---|----------|-------|-------|-------------|-------------------|
| 1 | Warren Buffett | `augur-buffett` | Economic Moat Value Investing | Gross Margin >40%, ROE >15%, Debt <50% | claude-sonnet-4-6 |
| 2 | Benjamin Graham | `augur-graham` | Deep Value / Margin of Safety | PE <15, PB <1.5, Current Ratio >2 | claude-sonnet-4-6 |
| 3 | Peter Lynch | `augur-lynch` | GARP Growth | PEG <1.5, Revenue Growth >15% | claude-sonnet-4-6 |
| 4 | Ray Dalio | `augur-dalio` | Macro / All-Weather | Four-quadrant analysis, debt cycles | claude-sonnet-4-6 |
| 5 | Charlie Munger | `augur-munger` | Latticework / Mental Models | ROE >20%, Moat + Management quality | claude-sonnet-4-6 |
| 6 | George Soros | `augur-soros` | Reflexivity / Macro Trading | Reflexivity signals, trend momentum | claude-sonnet-4-6 |
| 7 | Howard Marks | `augur-marks` | Cycles / Contrarian Investing | Cycle positioning, market sentiment | claude-sonnet-4-6 |
| 8 | Cathie Wood | `augur-cathie-wood` | Disruptive Innovation | Revenue Growth >30%, TAM | claude-sonnet-4-6 |
| 9 | Philip Fisher | `augur-fisher` | Growth Stocks / Scuttlebutt | R&D >10%, Gross Margin >50% | claude-sonnet-4-6 |
| 10 | ARPS | `augur-arps` | Crypto / Gold Macro | BTC correlation, gold as safe haven | claude-sonnet-4-6 |
| 11 | Leopold Aschenbrenner | `augur-aschenbrenner` | AI Geopolitics | AI investment, compute demand | claude-opus-4-7 |
| 12 | BTCdayu (大宇) | `augur-dayu` | Information Edge / Sentiment Momentum | Sentiment momentum > valuation | deepseek-v4 |
| 13 | Peter Thiel | `augur-thiel` | Zero-to-One Monopoly | Network effects, tech barriers | claude-sonnet-4-6 |
| 14 | Duan Yongping (段永平) | `augur-duan-yongping` | Integrity-focused / Extreme Concentration | Clear business model, principled management | deepseek-v4 |
| 15 | Zhang Lei (张磊) / Hillhouse | `augur-zhang-lei` | Long-term Structural Value | Revenue Growth >15%, structural trends | deepseek-v4 |
| 16 | Li Lu (李录) / Himalaya | `augur-li-lu` | Deep Value / Margin of Safety | PE <25, ROE >12%, no high leverage | claude-sonnet-4-6 |
| 17 | Dan Bin (但斌) / Oriental Harbor | `augur-dan-bin` | Brand Moat / Era Beta | Gross Margin >40%, pricing power | kimi-k2 |

> Each investor has: Full persona documentation (`personas/*.md`) + Independent Skill (`skills/*/SKILL.md`) + Python analysis engine (`src/augur/personas/*.py`)

---

## Persona Evolution Tracking

The system tracks each master's portfolio changes and style drift, automatically injecting current-state context during analysis:

| Investor | Key Evolution | Core Drift |
|----------|--------------|------------|
| Buffett | 1965 Berkshire - 1988 Coca-Cola - 2016 Apple - 2026 CRCL | Pure cigar-butt - Moat growth - Embracing tech |
| Munger | 1972 See's Candies - 2002 China - 2020 BYD | Graham-style - Latticework mental models |
| Dalio | 1982 Bad bet - 2008 Called subprime - 2012 All-Weather | Pure macro - Systematic all-weather |
| Duan Yongping (段永平) | 2001 BBK - 2011 Apple position - 2022 Tencent/NetEase | Entrepreneur-investor - Value concentration |
| Zhang Lei (张磊) | 2005 $20M start - 2012 JD.com - 2022 New energy pivot | China internet - New energy |
| Li Lu (李录) | 2002 BYD (20-year hold) - 2023 Heavy Alphabet | Deep value - Global concentration |
| Dan Bin (但斌) | 2003 Moutai - 2016 Crash resilience - 2023 AI + Consumer | Consumer brands - AI + Consumer |
| BTCdayu (大宇) | 2021 BTC at 3000 - 2024 MEME - 2026 AI + Crypto | Technical analysis - Narrative momentum |

---

## Usage

### CLI Commands (15+)

```bash
# Core Analysis
augur analyze AAPL                    # Single-target analysis (auto-fetches real-time data)
augur consensus NVDA                  # 17-master consensus
augur list-personas                   # List all investors
augur fetch 0700.HK --json            # Fetch market data only

# Service Launch
augur mcp-server                      # MCP Server (stdio, for Claude/Hermes)
augur api --port 8900                 # REST API service

# Persona Injection
augur inject-soul --profile my-buffett --persona buffett --format hermes

# Platform Bots
augur telegram                        # Telegram Bot
augur slack                           # Slack Bot (Socket Mode)
augur slack --mode http --port 3000   # Slack Bot (HTTP Mode)
augur wechat                          # Personal WeChat (GeWeChat, recommended)
augur wechat --mode wecom             # Enterprise WeChat (WeCom)
augur wechat --mode webhook           # WeChat Webhook push
augur lark                            # Lark/Feishu Event subscription
augur lark --mode webhook             # Lark/Feishu Webhook push

# Scheduling & Monitoring
augur cron-run                        # Manually trigger one analysis run
augur cron-start                      # Start scheduled daemon
augur watchlist-add AAPL --pe 32      # Add to watchlist
augur watchlist-show                  # View watchlist

# Backtesting
augur backtest AAPL --days 60 --live  # Backtest with real historical data
augur ic-report                       # IC leaderboard
augur ic-report --agent buffett       # Specific agent IC
```

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze/{ticker}` | GET | 17-master consensus analysis (supports auto-fetch) |
| `/api/fetch/{ticker}` | GET | Fetch real-time market data |
| `/api/search?q=` | GET | Search stock tickers |
| `/api/personas` | GET | List all investors |
| `/api/persona/{agent_id}` | GET | Get single investor details |
| `/api/config` | GET/PUT | Full configuration CRUD |
| `/api/config/persona/{id}` | GET/PUT | Individual investor model config |
| `/api/models` | GET | Available model list |
| `/api/custom-persona` | POST | Create custom investor |
| `/api/schema/persona` | GET | Persona YAML Schema |
| `/api/backtest/run?ticker=X&days=N` | GET | Run backtest |
| `/api/backtest/leaderboard` | GET | IC leaderboard |
| `/health` | GET | Health check |

### MCP Server (6 Tools)

| Tool | Description |
|------|-------------|
| `augur_analyze` | Single-investor analysis on a given target |
| `augur_consensus` | 17-master consensus analysis |
| `augur_list_personas` | List all available investors |
| `augur_configure` | Runtime configuration management |
| `augur_create_persona` | Create a custom investor persona |
| `augur_debate` | Multi-agent debate mode |

**Hermes Configuration:**
```yaml
mcp_servers:
  augur-agents:
    command: augur
    args: [mcp-server]
```

**Claude Desktop Configuration:**
```json
{
  "mcpServers": {
    "augur-agents": {
      "command": "augur",
      "args": ["mcp-server"]
    }
  }
}
```

### Web Dashboard (7 Pages)

```bash
python3 -m dashboard.app --port 8000 --cors
```

| Page | Path | Description |
|------|------|-------------|
| Home | `/` | System overview + quick analysis + status |
| Personas | `/personas` | 17 master cards + search/filter |
| Stock Analysis | `/stocks` | Deep analysis + real-time scoring + auto-fetch |
| Signal Monitor | `/signals` | Watchlist batch scanning |
| Backtest | `/backtest` | Historical backtesting + IC rankings |
| Settings | `/settings` | Agent model configuration |
| Create Persona | `/create_persona` | YAML custom investor creation |

---

## Real-time Data (yfinance)

Automatically fetches live market data - no manual financial metric input required.

**Supported Markets:**

| Market | Ticker Format | Examples | Delay |
|--------|--------------|----------|-------|
| US Equities (NYSE/NASDAQ) | `TICKER` | AAPL, NVDA | ~15 min |
| Hong Kong (HKEX) | `XXXX.HK` | 0700.HK | ~15 min |
| A-shares (Shanghai) | `XXXXXX.SS` | 600519.SS | ~15 min |
| A-shares (Shenzhen) | `XXXXXX.SZ` | 000858.SZ | ~15 min |

**Install:** `pip install 'augur-agents[data]'`

**Fetched Metrics:** Price, PE, PB, PS, ROE, Gross Margin, Operating Margin, Revenue Growth, Net Income Growth, Debt Ratio, Free Cash Flow, Market Cap, Current Ratio, RSI(14), MACD(12/26/9), SMA20/50

**Limitations:** Data is delayed approximately 15 minutes (not real-time Level 1), some A-share/HK fields may be missing, data is cached for 5 minutes, and depends on Yahoo Finance which may have regional access restrictions.

---

## Platform Bots

### Telegram

```bash
pip install 'augur-agents[telegram]'
export TELEGRAM_TOKEN='your-bot-token'
augur telegram
```

**Commands:** `/analyze AAPL` | `/consensus NVDA` | `/ask buffett analyze AAPL` | `/personas` | `/help`

Supports natural language: `@Buffett analyze AAPL`

### Slack

```bash
pip install 'augur-agents[slack]'
# Socket Mode (development)
export SLACK_BOT_TOKEN='xoxb-...' SLACK_APP_TOKEN='xapp-...'
augur slack
# HTTP Mode (production)
export SLACK_BOT_TOKEN='xoxb-...' SLACK_SIGNING_SECRET='...'
augur slack --mode http --port 3000
```

**Commands:** `/augur-analyze AAPL` | `/augur-ask buffett analyze AAPL` | `/augur-personas`

Mention `@augur analyze AAPL` in channels to trigger. Uses Block Kit rich text output.

### WeChat (3 Modes)

```bash
pip install 'augur-agents[wechat]'

# Mode 1: Personal WeChat (recommended, GeWeChat scan-to-use)
export GEWECHAT_TOKEN='...' GEWECHAT_BASE_URL='http://127.0.0.1:2531/v2/api'
augur wechat --mode personal --port 8066

# Mode 2: Enterprise WeChat (WeCom)
export WECHAT_CORP_ID='...' WECHAT_CORP_SECRET='...' WECHAT_AGENT_ID='...'
export WECHAT_TOKEN='...' WECHAT_AES_KEY='...'
augur wechat --mode wecom --port 8080

# Mode 3: Webhook (push-only, use with Cron)
export WECHAT_WEBHOOK_URL='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx'
augur wechat --mode webhook
```

Personal WeChat requires GeWeChat Docker running first:
```bash
docker compose --profile wechat up -d gewe
```

**Commands:** Enter a ticker directly like `AAPL` | `analyze NVDA pe=45` | `@DuanYongping TSLA` | `list personas`

### Lark / Feishu (2 Modes)

```bash
pip install 'augur-agents[lark]'

# Event Subscription Mode (receive + send)
export LARK_APP_ID='...' LARK_APP_SECRET='...'
export LARK_VERIFICATION_TOKEN='...' LARK_ENCRYPT_KEY='...'
augur lark --mode event --port 9000

# Webhook Mode (push-only)
export LARK_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'
augur lark --mode webhook
```

**Commands:** `analyze AAPL pe=32` | `@ZhangLei PDD` | `list personas`

Uses interactive card messages with signal colors, scores, and agent details.

---

## Cron Scheduled Analysis + Watchlist

```bash
augur watchlist-add AAPL --pe 32 --roe 0.55
augur watchlist-show
augur cron-run         # Manually trigger once
augur cron-start       # Start scheduled daemon
```

**Configuration File** (`~/.augur/watchlist.yaml`):
```yaml
watchlist:
  - ticker: AAPL
    pe: 32
    roe: 0.55
schedule:
  cron: "0 9 * * 1-5"
  timezone: "Asia/Shanghai"
notifications:
  telegram: { enabled: true, chat_id: "...", token: "..." }
  slack: { enabled: true, channel: "#signals", token: "xoxb-..." }
  wechat: { enabled: true, webhook_url: "https://..." }
  lark: { enabled: true, webhook_url: "https://..." }
  alert_threshold: 3
```

---

## Docker Deployment

```bash
# Dashboard + API
docker compose up -d dashboard        # http://localhost:8000

# Telegram Bot
export TELEGRAM_TOKEN=your_token
docker compose --profile telegram up -d

# All services
docker compose --profile full --profile telegram --profile cron up -d

# Makefile shortcuts
make docker-build && make docker-up
```

---

## Project Architecture

<p align="center">
  <img src="docs/images/architecture-baoyu.svg" alt="Augur Architecture" width="100%"/>
</p>

```
augur/
├── src/augur/                  # pip package main module
│   ├── cli.py                  # Click CLI (15+ commands)
│   ├── mcp_server.py           # MCP Server (6 tools, stdio)
│   ├── api.py                  # REST API (FastAPI)
│   ├── registry.py             # AgentRegistry + DecisionCoordinator
│   ├── data.py                 # Real-time data (yfinance)
│   ├── backtest.py             # Historical backtesting + IC
│   ├── cron.py                 # Scheduled analysis + Watchlist
│   ├── bots/                   # Multi-platform bots
│   │   ├── telegram_bot.py
│   │   ├── slack_bot.py
│   │   ├── wechat_bot.py
│   │   └── lark_bot.py
│   └── personas/               # 17 Investor Agents
│       ├── base.py             # Base class + MarketContext + AgentResponse
│       ├── buffett.py ... dan_bin.py
│       └── (17 Python modules)
├── scanner/                    # Backward-compatible shim
├── dashboard/                  # Bloomberg-style Web UI
│   ├── app.py                  # FastAPI + routes
│   └── templates/              # 7 page templates
├── skills/                     # Independent Skills (agentskills.io)
├── personas/                   # Investor deep-dive docs + custom/ YAML
├── config/agents.yaml          # Agent LLM model configuration
├── pyproject.toml              # pip package config (augur-agents)
├── Dockerfile                  # Containerization
└── docker-compose.yml          # Multi-service orchestration
```

**Consensus Mechanism:**

<p align="center">
  <img src="docs/images/consensus-flow.svg" alt="Consensus Flow" width="100%"/>
</p>

17 agents analyze independently, then results are aggregated through a 6-layer weighted system:
1. **Industry-aware Weighting** - Tech stocks give higher weight to Wood/Aschenbrenner
2. **Market Regime Routing** - Bear market increases weight for Marks/Dalio
3. **Rolling IC Weighting** - Agents with higher historical accuracy get dynamic weight boosts
4. **Diversity Penalty** - Agents with similar views have redundant weight reduced
5. **Kelly Position Sizing** - Suggests position size based on consensus and confidence
6. **Risk Veto Layer** - Can veto bullish consensus when debt is high + bear market detected

---

## Version Log

| Version | Changes |
|---------|---------|
| **v5.5** | Documentation overhaul + pyproject.toml metadata refinement |
| **v5.4** | Real-time market data (yfinance) - auto-fetch for US/HK/A-shares |
| **v5.3** | Personal WeChat integration (GeWeChat) - scan-to-use, 3-mode support |
| **v5.2** | UX polish - keyboard shortcuts + skeleton screens + score gauges + mobile support |
| **v5.1** | Historical backtesting system + agent IC tracking + leaderboard |
| **v5.0** | Docker containerization + docker-compose multi-service orchestration |
| **v4.6** | WeChat (WeCom + Webhook) + Lark/Feishu (Event + Webhook) |
| **v4.5** | Signal monitoring page + custom investor UI + Watchlist API |
| **v4.4** | Bloomberg Terminal-style UI + Hermes sidebar |
| **v4.3** | Slack Bot (Socket + HTTP) + Cron push notifications |
| **v4.2** | Telegram Bot + Cron scheduled analysis + Watchlist |
| **v4.1** | Config REST API + Dashboard UI/UX improvements |
| **v4.0** | pip packaging + CLI + MCP Server + Soul Injector |
| **v3.5** | Baoyu comic-style illustrations + 17 investor avatars |
| **v3.4** | Skill encapsulation + model configuration |
| **v3.3** | FastAPI Dashboard (5-page routing) |
| **v3.2** | 4 Chinese investors added (now 17 total) |
| **v3.0** | Renamed to Augur + Consensus Engine |
| **v2.0** | 13-investor persona system |
| **v1.0** | Buffett single-persona analysis |

---

## Why "Augur"?

> **Augur** - From Latin, the title of ancient Roman diviners. Augurs were responsible for interpreting omens and predicting the future, reading the trajectories of bird flocks and the direction of lightning to foresee coming changes. This is exactly what this system does: it lets 17 investment masters help you see opportunities before the market shifts.

| Figure | Role | Symbolism |
|--------|------|-----------|
| **Hermes** | Messenger of the gods | Information delivery, communication |
| **Augur** | Interpreter of omens, predictor of the future | Analysis, interpretation, foresight |

Hermes delivers information; Augur interprets it. One transmits, the other predicts - a natural complement.

---

## Contributing

1. **New Investors** - Add a YAML file in `personas/custom/`, or reference `src/augur/personas/buffett.py` to write a Python agent
2. **New Skills** - Follow the `skills/buffett/SKILL.md` format to create an independent Skill
3. **Algorithm Improvements** - Enhance scoring logic or the consensus mechanism
4. **Bot Adapters** - Add new platforms in `src/augur/bots/`
5. **Web UI** - Improve the `dashboard/` frontend

---

## License

MIT License - See [LICENSE](LICENSE)

<p align="center">
  <sub>Built with care by <a href="https://github.com/BruceLanLan">BruceLanLan</a></sub>
</p>
