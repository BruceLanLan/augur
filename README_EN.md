中文 | [English](README_EN.md)

<div align="center">

<img src="docs/images/hero-banner-baoyu.svg" alt="Augur" width="100%"/>

# 🦉 Augur

**Your AI Investment Committee**

*18 legendary investors. One consensus. Every time.*

[![v7.0.0](https://img.shields.io/badge/v7.0.0-Latest-00d4aa?style=for-the-badge)](https://github.com/BruceLanLan/augur)
[![18 Masters](https://img.shields.io/badge/18-Investment%20Masters-brightgreen?style=for-the-badge)](#-18-investor-personas)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude%20%2F%20Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

> **Would Buffett buy this stock?** What does Dalio think about macro risk? Is management "benfun" (principled) by Duan Yongping's standard?
>
> Stop guessing from one angle. Augur lets **18 legendary investors** independently analyze any stock, each producing a structured score, then aggregates them into a weighted consensus with Kelly position sizing.

---

## ✨ See It In Action

```
$ augur analyze NVDA

Auto-fetching data for NVDA from yfinance...
  Price: 820.00 | PE: 45.0 | ROE: 65.0% | GM: 78.0%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NVDA — 18 Masters Consensus
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Signal:     BULLISH
  Score:      7.6 / 10
  Confidence: 82%
  Kelly Size: 9.2%

  Key Findings:
    • 🛡️ AI reinforcing moat, competitive advantage expanding
    • ⚡ Revenue 122%, clear AGI commercialisation path
    • 🚀 S-curve early rapid expansion phase

  BULLISH (11): buffett, fisher, aschenbrenner, cathie_wood, thiel...
  NEUTRAL  (5): dalio, marks, graham, soros, serenity
  BEARISH  (2): arps, munger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🚀 30-Second Setup

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
pip install -e ".[data]"

augur analyze AAPL         # auto-fetch live data + 18-master analysis
augur consensus NVDA       # consensus + Kelly position sizing
python3 -m dashboard.app   # launch Bloomberg-style Dashboard
# → open http://localhost:8000
```

---

## 💡 Why Augur?

| | Single Strategy | Ask ChatGPT | **Augur** |
|--|:--:|:--:|:--:|
| Analysis Angles | 1 | Random | **18 independent views** |
| Quantified Score | ✗ | ✗ | **0–10 structured score** |
| Chinese Investors | ✗ | Biased | **Duan / Zhang / Li Lu / Dan Bin** |
| Live Data | Manual | None | **yfinance auto-fetch** |
| Position Sizing | ✗ | ✗ | **Kelly formula** |
| Deploy to Claude/Hermes | ✗ | ✗ | **MCP Server** |

---

## 🧠 18 Investor Personas

<details>
<summary><strong>Classic Value</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🏆 **Warren Buffett** | Moat + owner earnings + FCF | Consumer/financial blue chips |
| 📐 **Benjamin Graham** | Margin of safety, P/E<15 P/B<1.5 | Deep value stocks |
| 🧠 **Charlie Munger** | Latticework + contrarian | Misunderstood quality businesses |
| 🔬 **Philip Fisher** | Scuttlebutt + margin sustainability | High-quality growth companies |

</details>

<details>
<summary><strong>Growth & Innovation</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🚀 **Peter Lynch** | PEG < 1.5 + everyday business | GARP growth stocks |
| 💡 **Cathie Wood** | Wright's Law + TAM expansion | AI/Genomics/Blockchain |
| 🏢 **Peter Thiel** | 0-to-1 monopoly + contrarian | Tech platforms / deep tech |
| 🤖 **Leopold Aschenbrenner** | AGI infrastructure + compute scarcity | AI / semiconductors |

</details>

<details>
<summary><strong>Macro & Cycle</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🌐 **Ray Dalio** | All-weather + debt cycle | Macro rotation |
| 🔄 **George Soros** | Reflexivity + self-reinforcing trends | Trend trading |
| 📉 **Howard Marks** | Pendulum sentiment + second-level thinking | Cycle bottoms |
| 🥇 **ARPS** | Real rates + Crypto/Gold macro | Inflation hedge |

</details>

<details>
<summary><strong>🇨🇳 Chinese Investors (Exclusive)</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🎯 **Duan Yongping** | Benfun (principled) + extreme concentration | Consumer tech with clear model |
| 🌏 **Zhang Lei (Hillhouse)** | Structural long-term value | Chinese growth sectors |
| 🏔️ **Li Lu (Himalaya)** | Deep value + margin of safety | HK/A-share undervaluation |
| 🫖 **Dan Bin (OrientalHarbour)** | Brand moat + era beta | Consumer champions |
| ₿ **BTCdayu** | Information edge + sentiment momentum | Crypto / narrative trading |

</details>

<details>
<summary><strong>Special Strategies</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🔭 **Serenity** | AI/semiconductor supply chain chokepoints | Critical bottleneck plays |

</details>

---

## 📊 Bloomberg Dashboard

```bash
python3 -m dashboard.app --port 8000 --cors
```

**7 pages** covering the complete analysis workflow:

| Page | Function | Highlight |
|------|----------|-----------|
| **Home** | Quick analysis + recent history | Press `/` to focus ticker |
| **Stock Analysis** | 18-master consensus + detail view | yfinance auto-fill |
| **Personas** | 18-master cards + search/filter | Expand for factor weights |
| **Signal Monitor** | Watchlist batch scan | Auto-refresh every 60s |
| **Backtest** | IC leaderboard + hit rate | Track master accuracy |
| **Settings** | Per-master model config | Saved instantly |
| **Create Persona** | No-code YAML custom agent | Registers immediately |

<p align="center">
  <img src="docs/images/dashboard-stocks.svg" alt="Stock Analysis Dashboard" width="100%"/>
</p>

---

## 🔌 Deploy Anywhere

### Claude Desktop / Hermes (MCP)

```bash
# Requires Python 3.10+ for MCP support
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # verify it starts
```

**Hermes** (`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  augur:
    command: /absolute/path/to/augur/.venv/bin/augur
    args: [mcp-server]

skills:
  external_dirs:
    - /absolute/path/to/augur/skills   # enables /skill augur-buffett etc.
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "augur": {
      "command": "/absolute/path/to/augur/.venv/bin/augur",
      "args": ["mcp-server"]
    }
  }
}
```

7 MCP tools: `augur_analyze` · `augur_consensus` · `augur_fetch` · `augur_list_personas` · `augur_configure` · `augur_create_persona` · `augur_debate`

| Tool | What it does |
|------|-------------|
| `augur_analyze` | Analyze with one or all personas. Returns signal, score, key_findings, risks, reasoning. |
| `augur_consensus` | 18-master weighted consensus + Kelly position sizing. |
| `augur_fetch` | Fetch live market data only (no analysis). Great for chaining with analyze. |
| `augur_list_personas` | List all 18 investors with their ID, name, and philosophy. |
| `augur_configure` | Set which LLM model a specific persona uses. |
| `augur_create_persona` | Create a new YAML persona on the fly. |
| `augur_debate` | Run multi-round debate among agents on a ticker. |

> All tools auto-fetch live data from yfinance when no metrics are provided.

### Telegram / Slack / WeChat / Lark

```bash
pip install -e ".[telegram]" && export TELEGRAM_TOKEN='...' && augur telegram
pip install -e ".[slack]" && export SLACK_BOT_TOKEN='...' SLACK_APP_TOKEN='...' && augur slack
pip install -e ".[wechat]" && augur wechat --mode personal
pip install -e ".[lark]" && export LARK_APP_ID='...' LARK_APP_SECRET='...' && augur lark
```

### Docker

```bash
docker compose up -d dashboard           # http://localhost:8000
docker compose --profile telegram up -d  # + Telegram Bot
```

---

## ⚙️ Full CLI Reference (17 commands)

```bash
# ── Core Analysis ────────────────────────────────────────────────────────────
augur analyze AAPL                            # auto live data, all 18 masters
augur analyze NVDA --persona buffett          # specific master only
augur analyze TSLA --persona cathie_wood --json  # JSON output (for scripting)
augur consensus AAPL                          # weighted consensus + Kelly size
augur consensus NVDA --json                   # JSON output (incl. individual)
augur list-personas                           # list all 18 investors

# ── Data ─────────────────────────────────────────────────────────────────────
augur fetch 0700.HK                           # fetch live data (no analysis)
augur fetch AAPL --json                       # JSON format

# ── Backtest & IC Tracking ───────────────────────────────────────────────────
augur backtest AAPL --days 30 --live          # real yfinance history
augur backtest AAPL --demo                    # simulated data (quick demo)
augur ic-report                               # agent accuracy leaderboard

# ── Watchlist Monitoring ─────────────────────────────────────────────────────
augur watchlist-add AAPL --roe 0.55 --gross-margins 0.46 --sector Technology
augur watchlist-show                          # display current watchlist
augur cron-run                                # run watchlist analysis once
augur cron-start                              # start scheduled daemon (weekdays 9am)

# ── Services ─────────────────────────────────────────────────────────────────
python3 -m dashboard.app --port 8000 --cors   # Bloomberg Dashboard (full API)
augur api --port 8900                         # lightweight REST API
augur mcp-server                              # MCP Server (stdio, Python 3.10+)

# ── Hermes / Claude Integration ──────────────────────────────────────────────
augur inject-soul --persona buffett -f hermes --profile my-buffett

# ── Platform Bots ────────────────────────────────────────────────────────────
augur telegram    # pip install -e ".[telegram]" && export TELEGRAM_TOKEN=...
augur slack       # pip install -e ".[slack]"
augur wechat      # pip install -e ".[wechat]" (GeWeChat personal mode)
augur lark        # pip install -e ".[lark]"
```

**Parameter conventions (across all commands):**

| Type | Unit | Correct | Wrong |
|------|------|---------|-------|
| Rates / margins / growth | Decimal (0-1) | `--roe 0.55` (55%) | ~~`--roe 55`~~ |
| Debt ratio | Decimal (0-1) | `--debt-ratio 0.35` (35%) | ~~`--debt-ratio 35`~~ |
| Ownership | Integer percent | `--institutional-ownership 66` (66%) | ~~`--institutional-ownership 0.66`~~ |
| Market cap / FCF | **Billions USD** | `--market-cap 2800` ($2.8T) | ~~`--market-cap 2800000000000`~~ |

---

## 🔧 YAML Custom Personas

```yaml
# personas/custom/my_quant.yaml
agent_id: my_quant
name: "My Quant Strategy"
philosophy: ["momentum", "value", "low volatility"]
scoring_weights:
  momentum: 0.40
  value:    0.35
  safety:   0.25
factors:
  momentum:
    base: 5
    rules:
      - {if: "rsi > 55 and rsi < 75", add: 2}
      - {if: "macd > macd_signal",     add: 1}
  value:
    base: 5
    rules:
      - {if: "pe > 0 and pe < 15",     add: 3}
      - {if: "pb < 1.5 and pb > 0",   add: 2}
  safety:
    base: 5
    rules:
      - {if: "debt_ratio < 0.3",       add: 2}
      - {if: "current_ratio > 2",      add: 2}
```

---

## 📡 Dashboard API Endpoints

When Dashboard is running (`python3 -m dashboard.app --port 8000`), the following endpoints are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze/{ticker}` | GET | 18-master consensus, auto-yfinance when no metrics |
| `/api/fetch/{ticker}` | GET | Fetch live market data only |
| `/api/personas` | GET | List all 18 investors |
| `/api/persona/{id}` | GET | Single investor details |
| `/api/config` | GET/PUT | Global config read/write |
| `/api/config/persona/{id}` | GET/PUT | Per-investor model config |
| `/api/models` | GET | Available LLM models |
| `/api/watchlist` | GET | Current watchlist |
| `/api/watchlist/add` | POST | Add to watchlist |
| `/api/watchlist/{ticker}` | DELETE | Remove from watchlist |
| `/api/watchlist/run` | POST | Batch analyze + save last signal |
| `/api/custom-persona` | POST | Create YAML persona (hot-reloads) |
| `/api/backtest/run` | GET | Run IC backtest |
| `/api/backtest/leaderboard` | GET | IC leaderboard |
| `/api/search` | GET | Ticker search |
| `/health` | GET | Health check |

---

## ❓ Troubleshooting

<details>
<summary>"yfinance not installed" error</summary>

```bash
pip install -e ".[data]"
```
</details>

<details>
<summary>MCP Server "No module named mcp"</summary>

The `mcp` package requires Python 3.10+:
```bash
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # verify it starts
# then register the absolute path in ~/.hermes/config.yaml
```
</details>

<details>
<summary>Analysis always returns NEUTRAL with low scores</summary>

Check parameter units (the #1 mistake):
- ✅ `--roe 0.55` (55%)  ❌ ~~`--roe 55`~~
- ✅ `--debt-ratio 0.35` (35%)  ❌ ~~`--debt-ratio 35`~~
- ✅ `--market-cap 2800` ($2.8T)  ❌ ~~`--market-cap 2800000000000`~~
- ✅ `--gross-margins 0.46` (46%)  ❌ ~~`--gross-margins 46`~~
</details>

<details>
<summary>Dashboard stuck on "Loading"</summary>

```bash
# 1. Verify service is running
curl http://localhost:8000/health   # should return {"status":"ok","agents":18}

# 2. Make sure yfinance is installed (for auto-fetch)
pip install -e ".[data]"

# 3. Enable CORS for frontend calls
python3 -m dashboard.app --port 8000 --cors
```
</details>

<details>
<summary>Telegram Bot /analyze AAPL returns NEUTRAL with zero data</summary>

Install yfinance:
```bash
pip install -e ".[data,telegram]"
# Bot auto-fetches live data when no metrics are passed
```
</details>

<details>
<summary>Kelly position shows 0% or N/A</summary>

Kelly only returns a non-zero suggestion for BULLISH signal with score > 5. NEUTRAL/BEARISH signals conservatively return 0.
</details>

<details>
<summary>Custom YAML persona doesn't appear after creation</summary>

The Dashboard supports hot-reload (saved YAML is immediately available in the same process). CLI/API will auto-load `personas/custom/*.yaml` on next restart.
</details>

---

## 📋 Changelog

### v7.0.0

Major version update after 7 iterations of code review, bug fixing, and optimization.

#### Security Fixes (Critical)
- **CRITICAL**: Replaced vulnerable `eval()` in `persona_loader.py` with AST-based sandbox, preventing arbitrary code execution via malicious YAML persona conditions
- **CRITICAL**: Fixed path traversal vulnerability in `soul.py` `inject_soul()`, preventing writes to arbitrary directories
- Fixed XSS vulnerability in Dashboard `signals.html` (inline onclick string interpolation)
- Added ticker regex validation across API, MCP, and Dashboard endpoints
- Added global exception handlers to prevent stack trace leakage via API responses

#### Bug Fixes
- Fixed ZeroDivisionError in `data.py` when yfinance returns negative `debt_to_equity`
- Fixed Dayu persona momentum elif chain ordering bug (shadowed branch)
- Fixed coordinator crash when all agents return ERROR (total_weight==0)
- Fixed CLI missing sector/industry parameters not passed to MarketContext
- Fixed cron config shallow merge losing nested default values (timezone, notifications)
- All 18 persona files now clamp scores to [0, 10] range
- Added division-by-zero guards in Munger and Dalio personas

#### Performance
- DecisionCoordinator now uses ThreadPoolExecutor for parallel 18-agent analysis (up to 8x speedup)
- Added 30s timeout per agent to prevent hanging
- Added performance timing instrumentation (analysis_ms + consensus_ms in metadata)
- Dashboard uses Page Visibility API to pause polling in background tabs

#### User Experience
- New `--no-color` CLI flag (also respects NO_COLOR environment variable)
- Improved CLI output formatting with aligned tables and bordered boxes
- All error messages are now actionable (include pip install commands, --help suggestions)
- Created `src/augur/errors.py` for consistent error response formatting
- Created `src/augur/optional_deps.py` for graceful degradation when optional deps missing
- Added ARIA accessibility labels across all Dashboard templates
- Dashboard API responses now include consistent `status` field and ISO 8601 timestamps

#### Infrastructure
- Dockerfile: Added non-root user `augur` for security
- docker-compose.yml: Removed deprecated `version` field, added healthchecks
- requirements.txt: Added missing `httpx>=0.24.0`
- Scanner module: Added 6 missing agent exports for backward compatibility
- Cron: Added PID file concurrency protection and SIGTERM handler

#### Testing
- Added 173 new regression tests (from 78 to 251 total)
- Full end-to-end pipeline tests (CLI + API)
- Data pipeline validation tests
- Dashboard error handling tests
- Security attack vector tests (eval injection, XSS, path traversal)
- Performance baseline tests

#### Architecture
- New modules: `cli_format.py`, `errors.py`, `optional_deps.py`, `bots/utils.py`
- Bot shared utils module eliminates ticker extraction code duplication

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide: new investors (YAML/Python), bug fixes, Dashboard work, Bot work, parameter conventions.

- **New investor** → Add YAML to `personas/custom/` or write Python like `src/augur/personas/buffett.py`
- **Algorithm** → Improve `src/augur/coordinator.py` consensus mechanism
- **New platform** → Add to `src/augur/bots/`, reference `telegram_bot.py`
- **UI** → Improve `dashboard/`, CSS variables in `bloomberg.css`

---

<div align="center">

MIT License · Built by [BruceLanLan](https://github.com/BruceLanLan)

*For educational and research purposes only — not investment advice*

</div>
