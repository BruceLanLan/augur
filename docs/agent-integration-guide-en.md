English | [中文](agent-integration-guide.md)

# Augur Agent Integration Guide

> Make 17 legendary investment masters your AI Agent companions, ready to analyze for you anytime, anywhere

---

## 1. Product Form Overview

Augur's 17 investor Agents can exist independently and be embedded into your workflow in multiple forms:

| Form | Interaction | Use Case |
|------|------------|----------|
| 🖥️ **Augur Dashboard** | Web interface (FastAPI) | Deep analysis, multi-Agent comparison, visualization |
| 💬 **Hermes Agent Skill** | Conversational (/skill augur) | Quick inquiries, daily analysis |
| 🌐 **Hermes Web UI** | Chat interface | Seamless integration with existing Web UI |
| 🤖 **OpenClaude (OpenClaw)** | Standalone Agent | Complex reasoning tasks |
| 💻 **Claude Code / Codex** | IDE terminal | Investment analysis during development |
| 📱 **Telegram / Slack** | Messaging bot | On-the-go inquiries |
| 🔧 **API Calls** | REST API | Automated workflows |

---

## 2. Platform Integration Guide

### Method 1: Augur Dashboard (Built-in Web Interface)

Augur comes with a Bloomberg dark-theme FastAPI Web Dashboard where all 17 Agents are automatically loaded:

```bash
# Start
cd augur && python3 -m dashboard.app

# -> Visit http://localhost:8000
# -> All 17 Agents are automatically loaded, no extra configuration needed
```

Dashboard pages at a glance:

| Page | Function |
|------|----------|
| 🏠 Home | System overview + quick analysis entry |
| 🤖 Personas | 17 investment masters side-by-side |
| 📈 Stock Analysis | Single-stock deep analysis + real-time Agent scoring |
| ⚡ Signal Monitor | Watchlist batch scanning (in development) |
| ⚙️ Settings | Agent model configuration (in development) |

```bash
# Optional parameters
python3 -m dashboard.app --port 8000 --cors
```

---

### Method 2: Hermes Agent Skill

Each investor is an independent Skill (following the [agentskills.io](https://agentskills.io) standard) that can be installed directly into a Hermes Agent.

#### Install a Single Investor Agent

```bash
# Install from local
hermes skills install ./skills/buffett/SKILL.md --name buffett

# Or install from GitHub
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/buffett
```

Activate in conversation:

```
/skill buffett

-> "Analyze AAPL using the Buffett persona"
-> Returns Buffett-perspective scoring, reasoning, and signals
```

#### Install the Entire Augur System (All 17 Masters)

```bash
# Method 1: Install the main Skill (unified dispatch)
hermes skills install https://github.com/BruceLanLan/augur

# Method 2: Install the standalone SKILL.md (recommended for Hermes Agent)
hermes skills install ./SKILL.md --name augur
```

Activate in conversation:

```
/skill augur

-> "Analyze TSLA, compare Buffett and Musk"
-> Returns consensus results from all 17 Agents
```

#### Example Conversations

| User Command | Effect |
|-------------|--------|
| `/skill augur-buffett` -> "Analyze AAPL with the Buffett framework, PE=32, gross margin 46%, ROE=55%" | Returns Buffett-perspective deep analysis |
| `/skill augur-zhang-lei` -> "Zhang Lei's perspective on PDD, revenue growth 86%" | Zhang Lei's (Hillhouse) long-term structural value assessment |
| `/skill augur-dayu` -> "Dayu, what's the BTC sentiment right now?" | Dayu's crypto narrative analysis |
| `/skill augur` -> "What do all the masters think about NVDA?" | 17-master consensus report |

---

### Method 3: Hermes Web UI

Integrate with [Hermes Web UI](https://github.com/EKKOLearnAI/hermes-web-ui):

**Option A: Skill Mode (Recommended, Zero-Code)**

1. Open Hermes Web UI
2. Type `/skill augur` or `/skill buffett` in the chat window
3. Start conversational analysis immediately

```
/skill augur
-> "Analyze Apple AAPL using the Buffett persona"
-> Results stream back via Socket.IO
```

**Option B: Standalone Dashboard + iframe Embedding**

1. Start Augur Dashboard (`python3 -m dashboard.app --port 8000 --cors`)
2. Embed `http://localhost:8000` via iframe in Hermes Web UI

**Option C: Hermes Agent Skill Mode**

Load directly into any Hermes Agent instance via Skill:
```bash
hermes skills install ./skills/buffett/SKILL.md
# Then use /skill buffett on any platform
```

---

### Method 4: OpenClaude / OpenClaw

Register as a standalone Agent in OpenClaude or OpenClaw.

#### OpenClaude Configuration

Edit `openclaude.yaml`:

```yaml
agents:
  buffett:
    name: "Warren Buffett"
    description: "Moat value investing analysis Agent"
    skill: "./skills/buffett/SKILL.md"
    model: "claude-sonnet-4"
  graham:
    name: "Benjamin Graham"
    description: "Deep value / margin of safety analysis Agent"
    skill: "./skills/graham/SKILL.md"
    model: "claude-sonnet-4"
  lynch:
    name: "Peter Lynch"
    description: "GARP growth stock analysis Agent"
    skill: "./skills/lynch/SKILL.md"
    model: "claude-sonnet-4"
  dayu:
    name: "Dayu (BTCdayu)"
    description: "Crypto conviction-weighted analysis Agent"
    skill: "./skills/dayu/SKILL.md"
    model: "deepseek-v4"
  duan_yongping:
    name: "Duan Yongping (段永平)"
    description: "Ben Fen value / extreme concentration analysis Agent"
    skill: "./skills/duan_yongping/SKILL.md"
    model: "deepseek-v4"
  dan_bin:
    name: "Dan Bin (但斌)"
    description: "Brand moat / era beta analysis Agent"
    skill: "./skills/dan_bin/SKILL.md"
    model: "kimi-k2"
```

After registration, start chatting directly:

```
> Buffett, AAPL's current PE=32, gross margin 46%, ROE=55% - is it a buy?
> Dayu, BTC just broke below key support. What's your take?
> Duan Yongping, is Tencent's management team trustworthy?
```

#### OpenClaw Configuration

OpenClaw also supports Skill file registration with a similar configuration:

```json
{
  "agents": [
    {
      "id": "buffett",
      "name": "Warren Buffett",
      "skill": "./skills/buffett/SKILL.md",
      "model": "claude-sonnet-4"
    }
  ]
}
```

---

### Method 5: Claude Code / Codex

Use Claude Code or Codex to invoke Skills directly from the terminal.

#### Claude Code

```bash
# One-off analysis
claude -p "Analyze AAPL's current valuation" --skill ./skills/buffett/SKILL.md

# Comparative analysis
claude -p "Compare the moats of AAPL and NVDA" --skill ./skills/buffett/SKILL.md

# Chinese market analysis
claude -p "Is Moutai's current valuation reasonable?" --skill ./skills/duan_yongping/SKILL.md

# Crypto analysis
claude -p "What does the ETH on-chain data look like?" --skill ./skills/dayu/SKILL.md
```

#### Codex

```bash
# Basic usage
codex -p "NVDA moat analysis" --skill ./skills/buffett/SKILL.md

# Multi-turn conversation (requires skill pre-installation)
codex --skill ./skills/buffett/SKILL.md
-> "Analyze AAPL"
-> "What about MSFT?"
-> "Compare these two"
```

#### Development Workflow Scenarios

Analyze while coding in VSCode / Cursor:

```bash
# While researching a stock
claude -p "Analyze TSLA's current valuation, PE=85, revenue growth=8%"
-> Returns analysis from Buffett, Lynch, and Duan Yongping

# While writing investment notes
codex -p "Evaluate META's growth prospects using Fisher's framework, R&D ratio 20%"
```

---

### Method 6: Telegram / Slack Bot

Connect to messaging platforms via the Hermes Agent Gateway.

#### Telegram

```bash
# Connect via Hermes Gateway
hermes gateway setup --platform telegram

# Or use the built-in Bot
export TELEGRAM_TOKEN=your_bot_token
export AUGUR_API_URL=http://localhost:8000
python3 bots/telegram_bot.py
```

Chat directly in Telegram:

```
User: /analyze AAPL pe=32 gm=46 roe=55
Bot: 17-master analysis results...
  [Consensus Signal: BUY | Overall Score: 7.2/10]
  🏆 Buffett: BUY (7.5/10) - Excellent moat, gross margin meets requirements
  🌐 Dalio: HOLD (6.0/10) - Tight macro environment
  ...

User: /ask buffett Do you think Apple is worth holding right now?
Bot: Buffett-perspective analysis...

User: /consensus TSLA
Bot: 17-master consensus report...
```

#### Slack

```bash
# Connect via Hermes Gateway
hermes gateway setup --platform slack

# Or use the built-in Bot
export SLACK_TOKEN=your_slack_bot_token
export AUGUR_API_URL=http://localhost:8000
python3 bots/slack_bot.py
```

In Slack channels:

```
/ask-buffett AAPL
-> Buffett analysis results

/consensus NVDA
-> All 17 masters consensus
```

#### WeChat (In Development)

A WeChat bot adapter is planned. Contributions welcome (see `bots/` directory).

---

### Method 7: REST API Calls

Call Augur API endpoints directly for integration into automated workflows.

```bash
# Single-stock analysis (returns all Agent results)
curl http://localhost:8000/api/analyze/AAPL

# Get consensus report
curl http://localhost:8000/api/consensus/AAPL

# Specify Agent
curl "http://localhost:8000/api/analyze/AAPL?agent=buffett"

# Get investor list
curl http://localhost:8000/personas

# Get persona evolution timeline
curl http://localhost:8000/api/persona/buffett/evolution
```

Python example:

```python
import requests

response = requests.get("http://localhost:8000/api/consensus/AAPL")
data = response.json()
print(f"Consensus Signal: {data['signal']}")
print(f"Overall Score: {data['score']}")
for agent_id, result in data['agents'].items():
    print(f"  {result['name']}: {result['signal']} ({result['score']}/10)")
```

---

## 3. Skill File Reference

Each investor corresponds to a `skills/{persona_id}/SKILL.md` file. The file structure is:

```
skills/
├── buffett/SKILL.md             # Warren Buffett - Moat Value Investing
├── graham/SKILL.md              # Benjamin Graham - Deep Value / Margin of Safety
├── lynch/SKILL.md               # Peter Lynch - GARP Growth
├── dalio/SKILL.md               # Ray Dalio - Macro / All Weather
├── munger/SKILL.md              # Charlie Munger - Latticework of Mental Models
├── soros/SKILL.md               # George Soros - Reflexivity
├── marks/SKILL.md               # Howard Marks - Cycles / Contrarian
├── cathie_wood/SKILL.md         # Cathie Wood - Disruptive Innovation
├── fisher/SKILL.md              # Philip Fisher - Growth Stocks / Scuttlebutt
├── arps/SKILL.md                # ARPS - Crypto / Gold Macro
├── aschenbrenner/SKILL.md       # Leopold Aschenbrenner - AI Geopolitics
├── dayu/SKILL.md                # Dayu (BTCdayu) - Information Edge / Sentiment Momentum
├── thiel/SKILL.md               # Peter Thiel - Zero to One Monopoly
├── duan_yongping/SKILL.md       # Duan Yongping (段永平) - Ben Fen / Extreme Concentration
├── zhang_lei/SKILL.md           # Zhang Lei (张磊, Hillhouse) - Long-term Structural Value
├── li_lu/SKILL.md               # Li Lu (李录, Himalaya) - Deep Value
└── dan_bin/SKILL.md             # Dan Bin (但斌, Oriental Harbor) - Brand Moat
```

### Skill File Structure

Each `SKILL.md` follows the [agentskills.io](https://agentskills.io) standard and contains:

| Section | Content |
|---------|---------|
| **Identity Definition** | Investor's name, avatar, core philosophy |
| **Analysis Framework** | Dimensions and weights used by the investor to evaluate companies |
| **Scoring Rules** | How different factors are scored (positive/negative) |
| **Output Format** | Signal output specification (BUY/SELL/HOLD + score) |
| **Trigger Conditions** | When this persona is activated |
| **Example Conversations** | Demonstrates how to interact with this Agent |

### Example: Buffett Skill Summary

```markdown
# Warren Buffett

## Persona Definition
- Core Philosophy: Moat value investing
- Key Metrics: Gross margin > 40%, ROE > 15%, Debt ratio < 50%
- Style: Long-term holding, within circle of competence, values management quality

## Scoring Rules
- Moat Width: Wide(1~3) -> +2, Medium(0~1) -> +1, Narrow(<0) -> -2
- Profitability: Gross margin > 40% -> +1, ROE > 15% -> +1
- Debt Level: Total debt/Total assets < 50% -> +1, > 70% -> -1
- Management: Trusted -> +1, Not trusted -> -1

## Output Format
SCORE: X.X/10
SIGNAL: BUY | SELL | HOLD
REASONING: ...
KEY_METRICS: ...
```

---

## 4. Per-Agent Model Configuration

Different investors can use different LLM models. Edit `config/agents.yaml`:

```yaml
per_agent:
  buffett:       claude-sonnet-4-6       # English value analysis
  graham:        claude-sonnet-4-6       # English deep value
  lynch:         claude-sonnet-4-6       # GARP growth
  dalio:         claude-sonnet-4-6       # Macro analysis
  munger:        claude-sonnet-4-6       # Multi-disciplinary thinking
  soros:         claude-sonnet-4-6       # Reflexivity
  marks:         claude-sonnet-4-6       # Cycle investing
  cathie_wood:   claude-sonnet-4-6       # Disruptive innovation
  fisher:        claude-sonnet-4-6       # Growth stocks
  arps:          claude-sonnet-4-6       # Crypto / Gold
  aschenbrenner: claude-opus-4-7         # AI geopolitics (strongest reasoning)
  dayu:          deepseek-v4             # Crypto narrative (Chinese community)
  thiel:         claude-sonnet-4-6       # Monopoly analysis
  duan_yongping: deepseek-v4             # Chinese investment analysis
  zhang_lei:     deepseek-v4             # China structural sectors
  li_lu:         claude-sonnet-4-6       # Global value investing
  dan_bin:       kimi-k2                 # Chinese consumer culture context
```

Supported models: `claude-*` | `gpt-4o*` | `deepseek-v4` | `kimi-k2` | `minimax-01` | local Ollama

---

## 5. Custom Integration

### 5.1 Create a Custom Agent (YAML)

No code required. Simply add a YAML file under `personas/custom/` for automatic registration:

```yaml
agent_id: my_quant
name: "My Quant Strategy"
description: "Quantitative strategy Agent based on technical indicators"
scoring_weights:
  momentum: 0.50
  value: 0.50
factors:
  momentum:
    base: 5
    rules:
      - {if: "rsi > 60 and rsi < 75", add: 2}
      - {if: "macd > macd_signal", add: 1}
  value:
    base: 5
    rules:
      - {if: "pe < 15", add: 2}
      - {if: "pb < 1.5", add: 1}
```

### 5.2 Create a Custom Skill

Reference any `skills/*/SKILL.md` format to create a standalone Skill for any investment style:

```bash
mkdir -p skills/my_strategy
cp skills/buffett/SKILL.md skills/my_strategy/SKILL.md
# Edit the content to match your strategy
```

Then install to any platform:

```bash
hermes skills install ./skills/my_strategy/SKILL.md --name my-strategy
```

### 5.3 REST API Calls

Call the API directly in automated workflows:

```bash
# Schedule daily analysis with curl
0 9 * * 1-5 curl -s http://localhost:8000/api/analyze/AAPL >> ~/augur-reports.log

# Using a Python script
python3 -c "
from scanner.personas.registry import AgentRegistry, DecisionCoordinator
reg = AgentRegistry()
coord = DecisionCoordinator(reg)
results = coord.analyze_with_all(MarketContext(ticker='AAPL', ...))
print(coord.get_consensus(results, 'AAPL'))
"
```

### 5.4 Standalone Agent Process

Run in the background using tmux or systemd:

```bash
# tmux
tmux new-session -d -s augur 'cd /tmp/augur && python3 -m dashboard.app'

# systemd service
cat <<EOF | sudo tee /etc/systemd/system/augur.service
[Unit]
Description=Augur Investment Analysis Dashboard
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m dashboard.app
WorkingDirectory=/tmp/augur
Restart=always
User=bruce

[Install]
WantedBy=multi-user.target
EOF
```

### 5.5 Multi-Agent Comparative Analysis

Use the consensus engine to invoke any combination of Agents simultaneously for comparison:

```bash
python3 -c "
from scanner.personas.registry import AgentRegistry, DecisionCoordinator
reg = AgentRegistry()
# Enable only specific Agents for comparison
agents = ['buffett', 'lynch', 'dayu', 'duan_yongping']
coord = DecisionCoordinator(reg, enabled_agents=agents)
ctx = MarketContext(ticker='AAPL', ...)
results = coord.analyze_with_all(ctx)
for id, r in results.items():
    print(f'{r.agent_name:>30}: {r.signal.value.upper():>8} ({r.score:.1f}/10)')
"
```

---

## 6. Architecture Overview

![Augur Architecture](../docs/images/architecture-baoyu.svg)

```
User Input
  |
  |---> Hermes Agent Skill -> SKILL.md -> Call LLM -> Return analysis
  |---> Augur Dashboard (FastAPI) -> scanner/ -> 17 Agents -> Consensus -> Results
  |---> OpenClaude/OpenClaw -> Standalone Agent process
  |---> Claude Code/Codex -> Terminal one-off analysis
  |---> Telegram/Slack Bot -> Messaging platform interaction
  |---> REST API -> Automated workflows
```

---

## 7. Quick Reference Card

| Platform | One-Line Install | Interaction |
|----------|-----------------|-------------|
| Dashboard | `python3 -m dashboard.app` | Web browser |
| Hermes Agent | `hermes skills install ./SKILL.md` | Chat `/skill augur` |
| Hermes Web UI | Type `/skill augur` in chat | Conversational |
| OpenClaude | Edit `openclaude.yaml` | Direct chat |
| Claude Code | `claude -p "..." --skill ./SKILL.md` | Terminal |
| Codex | `codex -p "..." --skill ./SKILL.md` | Terminal |
| Telegram | `hermes gateway setup --platform telegram` | Messaging |
| Slack | `hermes gateway setup --platform slack` | Messaging |
| API | `curl localhost:8000/api/analyze/AAPL` | HTTP |

---

## 8. FAQ

**Q: Does it require GPU or high-performance hardware?**
A: No. All Agents call LLM APIs. Locally you only need to run the FastAPI service.

**Q: Can it be used offline?**
A: Network connectivity is required to call LLM APIs. However, the analysis engine itself can run locally by connecting to a local Ollama instance for offline use.

**Q: How do I add a new investor?**
A: Two methods: 1) Write a YAML file under `personas/custom/` (no code needed); 2) Write a Python Agent under `scanner/personas/` (more powerful).

**Q: Can all 17 Agents work simultaneously?**
A: Yes. The consensus engine supports parallel invocation of all Agents and automatically aggregates results.

**Q: What asset types are supported?**
A: US stocks, Hong Kong stocks, A-shares (China), and Crypto - one system covers all.

---

*For more questions, please submit a GitHub Issue or refer to [README.md](../README.md)*
