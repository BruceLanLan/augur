[🇨🇳 中文](README.md) | 🇺🇸 English

<div align="center">

# 🦉 Augur Next

**Your AI Investment Committee**

*18 legendary investors. Independent minds. One verdict.*

[![v9.0.2](https://img.shields.io/badge/v9.0.2-Latest-ff6b35?style=for-the-badge)](https://github.com/BruceLanLan/augur-next)
[![18 Agents](https://img.shields.io/badge/18-Independent_Agents-brightgreen?style=for-the-badge)](#-18-independent-agents)
[![MCP Ready](https://img.shields.io/badge/MCP-Hermes_%2F_Claude-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

> **Stable version → [augur](https://github.com/BruceLanLan/augur)**
> This repo is the next-generation feature preview.

</div>

---

## What is Augur Next?

Augur Next upgrades 18 legendary investors from a "scoring engine" into **true independent AI Agents** — each with their own personality, speaking style, decision framework, and tool access. Talk to them directly through Hermes Studio or Claude Desktop.

```
Stable (augur)               Dev (augur-next)
──────────────               ─────────────────
Dashboard scorecard  →       18 independent agent conversations
Batch consensus      →       Investment committee debates
Template chat        →       Real LLM persona conversations
```

---

## 🚀 5-Minute Quickstart

### Step 1: Install

```bash
git clone https://github.com/BruceLanLan/augur-next.git && cd augur-next
pip install -e ".[data,mcp]"    # Python 3.10+ required for MCP
augur-mcp --help                # verify the command works
```

### Step 2: Configure your AI client

**Hermes Studio** (`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  augur:
    command: augur-mcp
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp" }
  }
}
```

### Step 3: Start talking

```
/skill augur-buffett
"Is AAPL worth buying at PE=32, ROE=55%, Technology sector?"

/skill augur-committee
"China Value Committee: Duan Yongping, Zhang Lei, Li Lu, Dan Bin — assess Tencent 00700.HK"
```

---

## 🎭 18 Independent Agents

Each agent has a complete personality definition, decision framework, and tool permissions.

### Classic Value

| Skill | Investor | Framework | Language |
|-------|----------|-----------|----------|
| `augur-buffett` | Warren Buffett | Moat · Long-term hold | English |
| `augur-graham` | Benjamin Graham | Margin of safety · Deep value | English |
| `augur-munger` | Charlie Munger | Lattice thinking · Inversion | English |
| `augur-fisher` | Philip Fisher | Scuttlebutt · Growth quality | English |

### Growth & Innovation

| Skill | Investor | Framework | Language |
|-------|----------|-----------|----------|
| `augur-lynch` | Peter Lynch | GARP · PEG · Everyday edge | English |
| `augur-cathie-wood` | Cathie Wood | Disruptive innovation · Wright's Law | English |
| `augur-thiel` | Peter Thiel | 0→1 monopoly · Secrets | English |
| `augur-aschenbrenner` | Leopold Aschenbrenner | AGI infrastructure · Geopolitics | English |

### Macro & Cycle

| Skill | Investor | Framework | Language |
|-------|----------|-----------|----------|
| `augur-dalio` | Ray Dalio | All-weather · Debt cycles | English |
| `augur-soros` | George Soros | Reflexivity · Macro trading | English |
| `augur-marks` | Howard Marks | Pendulum · Second-level thinking | English |
| `augur-arps` | ARPS | Real rates · Gold/Crypto | English |

### 🇨🇳 Chinese Investors (full Chinese dialogue)

| Skill | Investor | Framework |
|-------|----------|-----------|
| `augur-duan-yongping` | 段永平 (Duan Yongping) | Integrity (本分) · Extreme concentration |
| `augur-zhang-lei` | 张磊 Zhang Lei (Hillhouse) | Structural long-term value |
| `augur-li-lu` | 李录 Li Lu (Himalaya) | Deep value · Margin of safety |
| `augur-dan-bin` | 但斌 Dan Bin | Brand moat · Era beta |

### Special Strategies

| Skill | Investor | Framework | Language |
|-------|----------|-----------|----------|
| `augur-dayu` | 大宇 BTCdayu | Information edge · Sentiment momentum | English |
| `augur-serenity` | Serenity | AI supply chain bottlenecks | English |

---

## 🏛️ Investment Committee Mode

### Via Hermes Agent (recommended)

```
/skill augur-committee
"Value Committee on NVDA — Buffett, Munger, Graham, Fisher, PE=35, AI chip leader"

"China Value Committee on Kweichow Moutai — Duan Yongping, Zhang Lei, Li Lu, Dan Bin"
```

### Via Dashboard

```bash
python3 -m dashboard.app
# Open http://localhost:8000/committee
# Select masters → enter ticker + question → view independent opinions + verdict
```

Committee sessions are automatically saved to history and can be reviewed at `/history`.

### Via MCP Tool

```
mcp_augur_committee(
    ticker="AAPL",
    question="Is the moat narrowing at this valuation?",
    agents="buffett,munger,duan_yongping,li_lu"
)
```

---

## 🔌 MCP Tools (9 total)

| Tool | Purpose |
|------|---------|
| `mcp_augur_analyze` | Single or all-master analysis |
| `mcp_augur_consensus` | Weighted consensus + Kelly position |
| `mcp_augur_committee` | Investment committee (independent opinions + verdict) |
| `mcp_augur_debate` | Multi-round structured debate |
| `mcp_augur_fetch` | Real-time market data (yfinance) |
| `mcp_augur_sentiment` | Social sentiment (StockTwits + news) |
| `mcp_augur_list_personas` | List all 18 agents |
| `mcp_augur_configure` | Set per-agent model parameters |
| `mcp_augur_create_persona` | Create custom YAML agent |

---

## 💻 CLI Commands

```bash
# Analysis
augur analyze AAPL                     # 18-master consensus
augur analyze AAPL --persona buffett   # single master
augur consensus NVDA                   # weighted consensus + Kelly

# Live monitoring
augur serve --port 8000 --open         # launch Dashboard, open browser
augur watch AAPL NVDA TSLA             # live monitoring (60s refresh)
augur watch NVDA --alert-above 7.5     # alert when score crosses threshold

# Portfolio
augur portfolio AAPL NVDA TSLA         # Kelly-weighted allocation suggestion

# Agent system
augur-mcp                              # start MCP server (for Hermes/Claude/OpenClaw)
augur skills                           # list all agent skills
augur skills --school value            # filter by school
augur inject-soul --persona buffett    # export agent soul to file

# Bots
augur telegram                         # start Telegram bot
augur slack                            # start Slack bot
```

---

## 📊 Dashboard

```bash
augur serve                    # simplest launch
augur serve --port 8080        # custom port
docker compose up              # Docker one-command
```

18 pages: Dashboard / Stocks / Signals / Scanner / Watchlist / Portfolio / Backtest / AI Chat / Optimizer / **Committee** / Compare / Debate / History / Leaderboard / Personas / **Hermes Setup** / Create Persona / Settings

---

## 🎨 Highly DIY — Custom Agents

```bash
# Option 1: Dashboard no-code builder (recommended)
augur serve → visit /create-persona

# Option 2: YAML file
cat > personas/custom/my_quant.yaml << EOF
agent_id: my_quant
name: "My Quant Strategy"
philosophy: ["momentum", "value", "low_vol"]
scoring_weights:
  momentum: 0.40
  value: 0.35
  safety: 0.25
EOF

# Option 3: Modify soul.py, regenerate all skills
python3 scripts/generate_skills.py

# Option 4: Via MCP
mcp_augur_create_persona(yaml_content="agent_id: ...")
```

---

## Comparison with Stable Version

| Feature | augur (stable v8.2.x) | augur-next (dev v9.0.x) |
|---------|----------------------|-------------------------|
| Dashboard | ✅ 18 pages | ✅ + Committee + Hermes Setup |
| MCP Server | 7 tools | **9 tools** (+committee +sentiment +create) |
| Hermes / OpenClaw Skills | ❌ | **19 SKILL.md + manifest.json** |
| Agent System Prompt | Generic template | **Handcrafted persona prompts** |
| `augur-mcp` command | ❌ | ✅ |
| `.mcp.json` auto-discovery | ❌ | ✅ |
| `augur serve/watch/skills/portfolio` | ❌ | ✅ |
| One-line installer | ❌ | ✅ `install.sh` |
| Committee history | ❌ | ✅ Auto-saved |

---

## 📝 Changelog

<details>
<summary><strong>v9.0.2 — Committee presets / sentiment MCP / augur-next README (current)</strong></summary>

- **Committee presets**: Classic Value / China Value / Macro All-Weather / Disruptive Growth / Full Council one-click load.
- **augur_sentiment MCP tool** (9th tool): StockTwits + news sentiment, score -1.0 to +1.0.
- **augur-next README**: Full rewrite telling the "18 independent agents" story.
- **Committee history**: Sessions auto-saved to history, retrievable via `/api/history`.
- **Hermes setup page** (`/hermes-setup`): Step-by-step integration guide with code copy buttons.
- **API reference**: `/api/committee` documented in both zh and en.
</details>

<details>
<summary><strong>v9.0.1 — 18 handcrafted Hermes Agent skills</strong></summary>

- 19 `skills/augur-*/SKILL.md` files with full persona-specific system prompts.
- Chinese investors (段永平/张磊/李录/但斌) get full Chinese system prompts.
- `augur_committee` MCP tool (structured committee flow).
- Dashboard `/committee` page.
- `augur-mcp` console script registered.
</details>

---

<div align="center">
MIT License · Built by <a href="https://github.com/BruceLanLan">BruceLanLan</a> · Development preview — API may change

*For educational purposes only, not investment advice*
</div>
