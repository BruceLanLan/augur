[🇨🇳 中文](README.md) | 🇺🇸 English

<div align="center">

<img src="docs/images/en/hero-banner.png" alt="Augur v8.2.2 — Optimizer efficient frontier, Rules→Bot alerts, UI contrast fixes" width="100%"/>

# 🦉 Augur

**Your AI Investment Committee**

*18 legendary investors. One consensus. Every time.*

[![v8.2.2](https://img.shields.io/badge/v8.2.2-Latest-00d4aa?style=for-the-badge)](https://github.com/BruceLanLan/augur)
[![1657 Tests](https://img.shields.io/badge/Tests-1657%20passed-success?style=for-the-badge)](CHANGELOG.md)
[![18 Masters](https://img.shields.io/badge/18-Investment%20Masters-brightgreen?style=for-the-badge)](#-18-investor-personas)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude%20%2F%20Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

> **Would Buffett buy this stock?** What does Dalio think about macro risk? Is management "benfun" (principled) by Duan Yongping's standard?
>
> Stop guessing from one angle. Augur lets **18 legendary investors** independently analyze any stock, each producing a structured score, then aggregates them into a weighted consensus with Kelly position sizing.

## One analysis. 18 perspectives.

<p align="center">
  <img src="docs/images/screenshots/report-hd2d.png" alt="NVDA deep analysis — v8.2.1 report contrast fix, readable light-mode parchment" width="100%"/>
</p>

> **All-New HD-2D Visual System**: Fusing the data density of a Bloomberg Terminal with the "Gilt-Edged" parchment aesthetic of a classic JRPG.
> NVDA live analysis: BUY · Score 7.6/10 · Confidence 81% · Kelly position 20% · All 18 masters voted

> **🦉 Why a White Pixel Owl?**
> In Japanese culture, the white owl (*フクロウ, fukurou*) symbolizes luck, wealth, and wisdom. Its name can be written as "不苦労" (no hardship) or "福来郎" (luck arrives). We chose it as Augur's logo to represent our mission: **using AI wisdom to make investment decisions less painful and more rewarding.**

---

## 💡 Why Augur?

| | Single Strategy | Ask ChatGPT | **Augur** |
|--|:--:|:--:|:--:|
| **Analysis Angles** | 1 | Random | **18 independent schools** |
| **Quantified Score** | ✗ | ✗ | **0–10 structured score** |
| **Chinese Investors** | ✗ | Biased | **Duan / Zhang / Li Lu / Dan Bin** |
| **Live Data** | Manual | None | **yfinance auto-fetch** |
| **Position Sizing** | ✗ | ✗ | **Kelly formula** |
| **Self-Learning Weights** | ✗ | ✗ | **IC feedback auto-optimization** |
| **System Integration** | ✗ | ✗ | **MCP Server / Hermes** |

---

## 🧠 18 Investor Personas

<p align="center">
  <img src="docs/images/screenshots/personas-hd2d.png" alt="18 investor personas — Value / Growth / Macro / China" width="100%"/>
</p>

<details>
<summary><strong>Classic Value</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🏆 **Warren Buffett** | Moat + owner earnings + FCF | Consumer / financial blue chips |
| 📐 **Benjamin Graham** | Margin of safety, P/E<15 P/B<1.5 | Deep value stocks |
| 🧠 **Charlie Munger** | Latticework thinking + contrarian | Misunderstood quality businesses |
| 🔬 **Philip Fisher** | Scuttlebutt + margin sustainability | High-quality growth companies |

</details>

<details>
<summary><strong>Growth & Innovation</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🚀 **Peter Lynch** | PEG < 1.5 + everyday business | GARP growth stocks |
| 💡 **Cathie Wood** | Wright's Law + TAM expansion | AI / Genomics / Blockchain |
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
| 🥇 **ARPS** | Real rates + Crypto / Gold | Inflation hedge |

</details>

<details>
<summary><strong>🇨🇳 Chinese Investors (Exclusive)</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🎯 **Duan Yongping** | Benfun (principled) + extreme concentration | Consumer tech with clear model |
| 🌏 **Zhang Lei (Hillhouse)** | Structural long-term value | Chinese growth sectors |
| 🏔️ **Li Lu (Himalaya)** | Deep value + margin of safety | HK / A-share undervaluation |
| 🫖 **Dan Bin (OrientalHarbour)** | Brand moat + era beta | Consumer champions |
| ₿ **BTCdayu** | Information edge + sentiment momentum | Crypto / narrative trading |

</details>

<details>
<summary><strong>Special Strategies</strong></summary>

| Investor | Framework | Best For |
|----------|-----------|---------|
| 🔭 **Serenity** | AI / semiconductor supply chain chokepoints | Critical bottleneck plays |

</details>

---

## 🚀 30-Second Setup

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -e ".[data]"

# Analyze
augur analyze AAPL                  # 18-master consensus, live data auto-fetch
augur consensus NVDA                # weighted consensus + Kelly position sizing
augur report TSLA                   # generate deep analysis report

# v8 features
augur chat AAPL --persona buffett   # ask Buffett about a stock
augur sentiment NVDA                # social sentiment analysis

# Launch Dashboard
python3 -m dashboard.app            # → open http://localhost:8000
```

### 🔑 AI Chat LLM Configuration

The AI Master Chat module natively supports any standard OpenAI-compatible API, allowing you to easily connect to DeepSeek, GPT-4, or local models (e.g. Ollama).

1. Copy the environment configuration file:
   ```bash
   cp .env.example .env
   ```
2. Edit the `.env` file to input your API Key and endpoint details:
   ```ini
   # Required: Enable the AI chat LLM backend (falls back to local mock replies if unset)
   OPENAI_API_KEY=your_api_key_here

   # Optional: Custom API base URL (e.g. for DeepSeek, OneAPI, or local Ollama)
   # DeepSeek: https://api.deepseek.com/v1
   # Ollama: http://localhost:11434/v1
   OPENAI_BASE_URL=

   # Optional: Override chat model (default: gpt-4o)
   # DeepSeek: deepseek-chat
   AUGUR_CHAT_MODEL=
   ```

---

## ✨ See It In Action

```text
$ augur consensus NVDA

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
    • ⚡ AI revenue rapidly growing, AGI path clear
    • 🚀 Revenue 122%, S-curve early rapid expansion

  BULLISH (11): buffett, fisher, aschenbrenner, cathie_wood, thiel...
  NEUTRAL  (5): dalio, marks, graham, soros, serenity
  BEARISH  (2): arps, munger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🆕 What's New in v8.1.0

v8 upgrades Augur from an analysis tool to an **intelligent investment platform** with 10 new modules.

### 🖥️ New Dashboard Pages

| Page | URL | What It Does |
|------|-----|-------------|
| **AI Chat** | `/chat` | 11 personas with distinct voices — OpenAI-compatible LLM Universal Support (DeepSeek, GPT-4) or fallback to local templates |
| **Portfolio Optimizer** | `/optimizer` | Markowitz mean-variance optimization, pure Python |
| **Master Compare** | `/compare` | 2–5 personas independently analyze the same stock |
| **Debate Mode** | `/debate` | Personas argue in sequence, each rebutting the previous |
| **History** | `/history` | Persistent analysis history, searchable by ticker/date |
| **Leaderboard** | `/performance` | IC-based accuracy ranking across all agents |

### 🧠 Smarter Backend

| Module | What It Does |
|--------|-------------|
| **LearningEngine** | Tracks prediction accuracy, auto-adjusts consensus weights via IC feedback |
| **SentimentAnalyzer** | Fuses X / Reddit / StockTwits sentiment into the consensus score |
| **WebSocket Streaming** | `/ws/prices` real-time price tape, Bloomberg-style ticker |
| **RulesEngine** | DSL-based alert conditions with multi-channel notifications |

<table>
<tr>
<td width="50%">

**Crystal Clear Bull/Bear Debate**

<img src="docs/images/screenshots/04-bullish-critical.png" alt="Bull vs Bear Debate — Integrated HD-2D Style" width="100%"/>

</td>
<td width="50%">

**Available Everywhere (Multi-Platform)**

<img src="docs/images/screenshots/05-available-everywhere.png" alt="Multi-device support" width="100%"/>

</td>
</tr>
<tr>
<td width="50%">

**History** — every analysis, tracked

<img src="docs/images/screenshots/history.png" alt="Analysis history with signals and scores" width="100%"/>

</td>
<td width="50%">

**v8.1 real data**

- 📡 Streaming: yfinance live prices
- 😊 Sentiment: StockTwits real API
- 📊 Optimizer: real 3-month returns
- 🧠 Learning: auto-records predictions + outcomes

</td>
</tr>
</table>

### 🔧 Optional Advanced Features

| Module | How to Enable |
|--------|--------------|
| Multi-user system (JWT + SQLite) | `AUGUR_MULTI_USER=1` |
| API authentication (Bearer Token) | `AUGUR_API_TOKEN=your_token` |
| Plugin system (third-party agents) | setuptools `entry_points` |

---

## 📊 Bloomberg Terminal × JRPG Dashboard

```bash
python3 -m dashboard.app --port 8000
```

**17 pages** (Dashboard / Stocks / Signals / Scanner / Watchlist / Portfolio / Backtest / AI Chat / Optimizer / Compare / Debate / History / Leaderboard / Personas / Create / Settings / Login) covering the complete investment analysis workflow:

| Group | Page | Highlights |
|-------|------|-----------|
| **Analysis** | Dashboard | Quick analysis + global market overview panels |
| | Stock Analysis | 18-master consensus, score cards, bull/bear debate, deep report |
| | Signal Monitor | Watchlist batch scan, auto-refresh every 60s |
| | Scanner | Preset ticker scoring heatmap |
| | Watchlist | One-click analysis, localStorage persistence |
| | Portfolio | Position tracking, real-time P&L, asset allocation chart |
| | Backtest | IC leaderboard + agent accuracy history |
| **v8 Features** | AI Chat | 11 personas, each with unique voice and perspective |
| | Portfolio Optimizer | Markowitz efficient frontier optimization |
| | Master Compare | Side-by-side analysis from 2–5 chosen personas |
| | Debate Mode | Sequential debate with per-persona rebuttals |
| | History | Full analysis history with search and filtering |
| | Leaderboard | IC-weighted accuracy tracking per agent |
| **Investors** | Personas | 18-master cards, search and school filter |
| | Create Persona | No-code YAML custom agent builder |
| **System** | Settings | Per-master parameter configuration |

<p align="center">
  <img src="docs/images/screenshots/dashboard-hd2d.png" alt="Augur Dashboard v8.2.1 — zero-gap grid sidebar, AAPL onboarding, global markets panel" width="100%"/>
</p>

---

## 🔌 Deploy Anywhere

<p align="center">
  <img src="docs/images/en/architecture.png" alt="Augur Architecture" width="100%"/>
</p>

<p align="center">
  <img src="docs/images/en/consensus-flow.png" alt="Consensus Decision Flow" width="100%"/>
</p>

### Claude Desktop / Hermes (MCP)

```bash
# Requires Python 3.10+
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # verify it starts
```

**Hermes** (`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  augur:
    command: /path/to/augur/.venv/bin/augur
    args: [mcp-server]
skills:
  external_dirs:
    - /path/to/augur/skills
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "augur": {
      "command": "/path/to/augur/.venv/bin/augur",
      "args": ["mcp-server"]
    }
  }
}
```

7 MCP tools: `augur_analyze` · `augur_consensus` · `augur_fetch` · `augur_list_personas` · `augur_configure` · `augur_create_persona` · `augur_debate`

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

## ⚙️ CLI Reference

```bash
# ── Core Analysis ─────────────────────────────────────────────────────────────
augur analyze AAPL                            # 18-master consensus, live data
augur analyze NVDA --persona buffett          # single master
augur analyze TSLA --persona cathie_wood --json  # JSON output (for scripting)
augur consensus AAPL                          # weighted consensus + Kelly sizing
augur report TSLA                             # generate deep Markdown report
augur list-personas                           # list all 18 investors

# ── v8 New Commands ───────────────────────────────────────────────────────────
augur chat AAPL --persona buffett             # ask Buffett about a stock
augur chat NVDA                               # random persona response
augur sentiment TSLA                          # social sentiment (X/Reddit/StockTwits)

# ── Data ──────────────────────────────────────────────────────────────────────
augur fetch AAPL                              # fetch live data, no analysis
augur fetch 0700.HK --json                    # HK stocks, JSON format

# ── Backtest & IC Tracking ────────────────────────────────────────────────────
augur backtest AAPL --days 30 --live          # real yfinance history
augur ic-report                               # agent accuracy leaderboard

# ── Watchlist Monitoring ──────────────────────────────────────────────────────
augur watchlist-add AAPL --sector Technology
augur watchlist-show
augur cron-run                                # run watchlist analysis now
augur cron-start                              # start scheduled daemon (weekdays 9am)

# ── Services ──────────────────────────────────────────────────────────────────
python3 -m dashboard.app --port 8000 --cors   # Bloomberg Dashboard
augur api --port 8900                         # lightweight REST API
augur mcp-server                              # MCP Server (stdio, Python 3.10+)

# ── Platform Bots ─────────────────────────────────────────────────────────────
augur telegram / augur slack / augur wechat / augur lark
```

**Parameter unit conventions (critical):**

| Type | Unit | Correct | Wrong |
|------|------|---------|-------|
| Rates / margins / growth | Decimal (0–1) | `--roe 0.55` (= 55%) | ~~`--roe 55`~~ |
| Debt ratio | Decimal (0–1) | `--debt-ratio 0.35` | ~~`--debt-ratio 35`~~ |
| Ownership | Integer percent | `--institutional-ownership 66` | ~~`--institutional-ownership 0.66`~~ |
| Market cap / FCF | **Billions USD** | `--market-cap 2800` (= $2.8T) | ~~`--market-cap 2800000000000`~~ |

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

Hot-reloads in the Dashboard; CLI auto-loads on next start.

---

## 📡 Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze/{ticker}` | GET | 18-master consensus, auto live data |
| `/api/report/{ticker}` | GET | Deep Markdown report |
| `/api/sentiment/{ticker}` | GET | Social sentiment scores |
| `/api/chat` | POST | AI persona chat (body: message, agent_id) |
| `/api/optimize` | POST | Portfolio optimization (body: tickers, risk_free_rate) |
| `/api/compare` | POST | Master compare (body: ticker, agent_ids) |
| `/api/debate` | POST | Debate mode (body: ticker, agent_ids) |
| `/api/history` | GET | Analysis history list |
| `/api/rules` | GET/POST | Alert rule management |
| `/api/personas` | GET | List all 18 investors |
| `/api/watchlist` | GET/POST | Watchlist management |
| `/ws/prices` | WebSocket | Real-time price streaming |
| `/ws/analyze/{ticker}` | WebSocket | Streaming analysis progress |
| `/health` | GET | Health check |

Full API reference: [docs/api-reference.md](docs/api-reference.md)

---

## ❓ Troubleshooting

<details>
<summary>Local Installation Fails / Website Won't Open</summary>

- **Install error:** If you already have the `augur` folder downloaded, **do not** run `git clone` again (it will fail and break the rest of the commands). Just run: `cd augur && source .venv/bin/activate && python3 -m dashboard.app`
- **Website won't open:** After running the start command, your terminal will hang (it's listening for requests, do not close or press Ctrl+C). If `http://localhost:8000` doesn't open or your browser forces https, try navigating to the explicit IP: `http://127.0.0.1:8000`.
</details>

<details>
<summary>"yfinance not installed" error</summary>

```bash
pip install -e ".[data]"
```
</details>

<details>
<summary>MCP Server: "No module named mcp"</summary>

The `mcp` package requires Python 3.10+:
```bash
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server
```
</details>

<details>
<summary>Analysis always returns NEUTRAL with low scores</summary>

The #1 cause is wrong parameter units:
- ✅ `--roe 0.55` (55%)  ❌ ~~`--roe 55`~~
- ✅ `--debt-ratio 0.35`  ❌ ~~`--debt-ratio 35`~~
- ✅ `--market-cap 2800` ($2.8T)  ❌ ~~`--market-cap 2800000000000`~~
</details>

<details>
<summary>"File 'setup.py' not found" on pip install</summary>

Your pip version is too old to read `pyproject.toml`:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e ".[data]"
```
</details>

<details>
<summary>Kelly position shows 0%</summary>

Kelly only returns a non-zero suggestion for BULLISH signal with score > 5. NEUTRAL/BEARISH conservatively return 0.
</details>

---

## 📝 Changelog

<details>
<summary><strong>v8.2.2 — Optimizer frontier chart / Rules→Bot / UI contrast fixes (current)</strong></summary>

- **Optimizer efficient frontier:** New Chart.js scatter+line chart on the optimizer page — shows the Markowitz efficient frontier curve, optimal portfolio (gold star), and individual asset positions.
- **Rules→Bot integration:** Analysis and watchlist scan results now automatically trigger alert rules and push notifications to Telegram / Slack / WeChat / Lark.
- **UI contrast fixes:** Replaced hardcoded `#000/#fff` on orange backgrounds with CSS variables (WCAG AA compliant); replaced `rgba` literals with design-system tokens across debate, compare, scanner, settings, optimizer, stocks, and index pages.
- **Loop 400 code merge:** All Loop 400 stash code (34 files) merged into main; i18n.js +238 new translation keys; compare page now supports `?autorun=1`.
- **Tests:** **1657** passing (up from 1362 in v8.2.1, +295 new tests).
</details>

<details>
<summary><strong>v8.2.1 — Loop 200 review: layout fix, report contrast, UX & auth</strong></summary>

- **Layout fix:** Sidebar and main panel aligned with CSS Grid (`240px + 1fr`); eliminated the 240px visual gap; unified `--sidebar-width` when collapsed.
- **Report contrast:** Fixed unreadable light-mode parchment + pale text; added `--report-*` semantic tokens and theme-aware chart SVG colors.
- **UX improvements:** Global `window._t()` export, progress/copy i18n keys, consistent empty states across five pages, 44px touch targets, mobile table scroll hints, index AAPL onboarding, partial `data_error` surfacing.
- **Auth integration:** Dashboard fetch/WebSocket auto-attach `AUGUR_API_TOKEN`; `/ws/prices?token=` server validation; `GET /api/auth/config` discovery endpoint.
- **Backend hardening:** Price-series NaN/Inf sanitization, consensus tie → `NEUTRAL`, coverage-confidence normalization, persona YAML weight type checks.
- **Tests:** **1362** passing (up from ~1177 in v8.2.0). See [`docs/LOOP_200_REPORT.md`](docs/LOOP_200_REPORT.md).
</details>

<details>
<summary><strong>Loop 400 review (completed, merged in v8.2.2)</strong></summary>

- All stash code (34 files) merged into main as part of v8.2.2. Stash fully cleared.
- Status report: [`docs/LOOP_400_REPORT.md`](docs/LOOP_400_REPORT.md).
</details>

<details>
<summary><strong>v8.2.0 — Persona audit, makefile, pyproject polish, analyzer & ws prices</strong></summary>

- **Frontend Visual Architecture**: Fully integrated the "Bloomberg Terminal × JRPG HD-2D" frontend visual architecture, introducing `ExecCard`, `OracleSays`, and `ScorecardGrid` components.
- **UI/UX Polish**:
  - **Layout Spacing Fix**: Resolved the 240px layout gap between the sidebar and main panel, achieving a compact, flex-based responsive structure.
  - **Contrast Optimization**: Fixed contrast issues on the light parchment background (`.scroll .md-report`, school badges, etc.) by mapping hardcoded colors to adaptive semantic color variables (`var(--signal-buy)`, `var(--signal-sell)`).
  - **Responsive Grid**: Added responsive breakpoints (768px/480px) for small screens to prevent master avatar badge distortion.
  - **Chat Readability**: Standardized chat bubble fonts to modern sans-serif fonts to support Chinese and English text beautifully.
- **i18n Localization**:
  - Enabled dynamic number abbreviation formatting (e.g. `B`, `M`, `K`) and relative times (e.g. `5m ago`, `2d ago`) in English mode.
  - Fixed client-side missing translation keys (e.g., initial selection text in the Master Compare page).
</details>

<details>
<summary><strong>v8.0.0 — Intelligent Investment Platform</strong></summary>

- 6 new Dashboard pages: AI Chat, Portfolio Optimizer, Master Compare, Debate Mode, History, Leaderboard
- LearningEngine: IC-based feedback auto-adjusts consensus weights for all 18 agents
- SentimentAnalyzer: social sentiment factor fused into consensus calculation
- WebSocket real-time price streaming
- Multi-user system (opt-in), JWT auth, plugin system
- Tests: 653 (vs ~160 in v7.8.3)
</details>

<details>
<summary><strong>v7.8.x — Visual Redesign + Bug Fixes</strong></summary>

- DQ1 pixel-art brand redesign: white pixel owl logo, 18-master pixel portraits
- Report page voting table rendering fix (regex match bug)
- CRCL analysis fix: coverage_confidence gate prevents AGI labels on unrelated companies
- Crypto / commodities / treasury rates panels
- OG image path fix, bilingual README
</details>

---

## 📈 Star History

<a href="https://star-history.com/#BruceLanLan/augur&Timeline">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline" />
 </picture>
</a>

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

- **New investor** → add YAML to `personas/custom/` or write Python like `src/augur/personas/buffett.py`
- **Algorithm** → improve `src/augur/coordinator.py` consensus mechanism
- **New platform** → add to `src/augur/bots/`, reference `telegram_bot.py`
- **UI** → improve `dashboard/`, CSS variables in `bloomberg.css`

---

<div align="center">

MIT License · Built by <a href="https://github.com/BruceLanLan">BruceLanLan</a>

<em>For educational and research purposes only — not investment advice</em>

</div>
