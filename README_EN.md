中文 | [English](README_EN.md)

<div align="center">

<img src="docs/images/hero-banner-baoyu.svg" alt="Augur" width="100%"/>

# 🦉 Augur

**Your AI Investment Committee**

*18 legendary investors. One consensus. Every time.*

[![v6.1.0](https://img.shields.io/badge/v6.1.0-Latest-00d4aa?style=for-the-badge)](https://github.com/BruceLanLan/augur)
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

6 MCP tools: `augur_analyze` · `augur_consensus` · `augur_list_personas` · `augur_configure` · `augur_create_persona` · `augur_debate`

> All tools support **auto live data**: if no metrics are passed, yfinance fetches them automatically.

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

## ⚙️ Full CLI Reference

```bash
augur analyze AAPL                         # auto live data, all 18 masters
augur analyze TSLA --persona cathie_wood   # specific master only
augur consensus NVDA                       # weighted consensus + Kelly size
augur list-personas                        # show all investors

augur fetch 0700.HK --json                 # raw market data (JSON)
augur backtest AAPL --days 30 --live       # real historical backtest
augur ic-report                            # agent accuracy leaderboard

augur watchlist-add AAPL --pe 32 --roe 0.55 --gross-margins 0.46
augur cron-run                             # run watchlist analysis once
augur cron-start                           # start scheduled daemon (weekdays 9am)

augur inject-soul --profile my-buffett --persona buffett -f hermes
```

**Parameter conventions:**

| Type | Unit | Example |
|------|------|---------|
| Rates / margins | Decimal | `--roe 0.55` = 55% |
| Ownership | Integer percent | `--institutional-ownership 66` = 66% |
| Market cap / FCF | Billions USD | `--market-cap 2800` = $2.8T |

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

## ❓ Troubleshooting

<details>
<summary>"yfinance not installed" error</summary>

```bash
pip install -e ".[data]"
```
</details>

<details>
<summary>MCP Server "No module named mcp"</summary>

```bash
uv venv --python 3.11 .venv && uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server
```
</details>

<details>
<summary>Analysis always shows NEUTRAL</summary>

Use decimals for rates (`--roe 0.55` not `--roe 55`), billions for market cap (`--market-cap 2800` = $2.8T)
</details>

<details>
<summary>Dashboard stuck on "Loading"</summary>

```bash
curl http://localhost:8000/health  # should return {"status":"ok","agents":18}
pip install -e ".[data]"
```
</details>

---

## 🤝 Contributing

- **New investor** → Add YAML to `personas/custom/` or write Python like `src/augur/personas/buffett.py`
- **Algorithm** → Improve `src/augur/coordinator.py` consensus mechanism
- **New platform** → Add to `src/augur/bots/`
- **UI** → Improve `dashboard/` frontend

---

<div align="center">

MIT License · Built by [BruceLanLan](https://github.com/BruceLanLan)

*For educational and research purposes only — not investment advice*

</div>
