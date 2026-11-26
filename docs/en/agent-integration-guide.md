English | [中文](../agent-integration-guide.md)

# Augur Agent Integration Guide

> Make 18 legendary investment masters your AI Agent companions, ready to analyze for you anytime, anywhere

One thing up front: the 18 masters' **scores are deterministic rules** (`src/augur/personas/`). They call no LLM and run offline. An LLM appears only on two optional paths: an external agent (Claude Code, Hermes, ...) that loads a Skill and converses with its own model, and dashboard chat, which writes persona-voiced replies when an OpenAI-compatible endpoint is configured.

---

## 1. Product Overview

| Form | Interaction | Use Case |
|------|------------|----------|
| 🖥️ **Augur Dashboard** | Web UI (FastAPI) | Deep analysis, multi-agent comparison, visualization |
| 🧩 **Skill + MCP** | Hermes Studio / Claude Desktop / Claude Code / OpenClaw, etc. | Conversational queries, daily analysis |
| 📱 **Telegram / Slack / WeChat** | Built-in bots | Query anytime, anywhere |
| 🔧 **REST API** | HTTP | Automated workflows |
| 🔗 **Agentic Workflow** | CLI / MCP / API | Multi-step fetch → analyze → consensus → committee |

---

## 2. Platform Integration Guides

### Method 1: Augur Dashboard (Built-in Web UI)

```bash
pip install 'augur-agents[data]'
augur serve              # default http://127.0.0.1:8000
augur serve --port 8080  # custom port
augur serve --open       # open the browser on start
```

All 18 masters load automatically. To expose it beyond localhost use `--host 0.0.0.0` and set `AUGUR_API_TOKEN` first.

Main pages:

| Page | Function |
|------|----------|
| 🏠 `/` | System overview + quick analysis entry |
| 🤖 `/personas` | 18 investment masters comparison |
| 📈 `/stocks` | Single-ticker deep analysis + real-time agent scoring |
| ⚡ `/signals`, `/scanner` | Signal monitoring and batch scanning |
| 🧪 `/backtest` | Historical backtest (hit rate / IC) |
| ⚙️ `/settings` | Settings |

---

### Method 2: Skill + MCP (Hermes Studio, Claude Desktop, OpenClaw, ...)

Each master is a Skill directory in the repo: `src/skills/augur-<id>/`, containing:

- `SKILL.md` — YAML frontmatter + persona system prompt
- `manifest.json` — universal JSON manifest (read by OpenClaw, Hermes Studio, Claude Desktop, ...)

There are also `src/skills/augur-committee/` (the investment-committee coordinator) and `src/skills/augur-terminal/`. Skills get data and scores from the Augur MCP server, so make sure `augur-mcp` works first:

```bash
pip install 'augur-agents[data,mcp]'
augur-mcp            # MCP server in stdio mode (same as `augur mcp-server`)
```

Per-platform setup is maintained in [src/skills/README.md](../../src/skills/README.md); the essentials:

#### Hermes Studio

```yaml
# hermes/config.yaml
mcp_servers:
  augur:
    command: augur-mcp

skills_dir: ./src/skills
```

Then activate in chat: `/skill augur-buffett`, `/skill augur-committee`, etc.

#### Claude Desktop

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp" }
  }
}
```

Use the relevant `SKILL.md` content as the system prompt.

#### OpenClaw

OpenClaw reads `manifest.json` from a Skill directory; see the OpenClaw section of [src/skills/README.md](../../src/skills/README.md) for the install command (point it at `src/skills/augur-<id>`).

#### Example Conversations

| User Command | Result |
|-------------|--------|
| `/skill augur-buffett` → "Analyze AAPL with Buffett's framework" | Buffett-perspective analysis (data and scores from the MCP tools) |
| `/skill augur-zhang-lei` → "Zhang Lei's view on PDD" | Zhang Lei's long-term structural value assessment |
| `/skill augur-dayu` → "Dayu, what's the current BTC sentiment?" | Dayu's crypto narrative analysis |
| `/skill augur-committee` → "What do all masters think of NVDA?" | Investment-committee consensus report |

---

### Method 3: Claude Code / Codex

Claude Code has no `--skill` flag. Register the MCP server, then put a Skill in Claude Code's skills directory.

```bash
# Register the Augur MCP server (stdio)
claude mcp add augur -- augur-mcp

# Optional: use a master as a project Skill (Claude Code reads .claude/skills/<name>/SKILL.md)
mkdir -p .claude/skills/augur-buffett
cp src/skills/augur-buffett/SKILL.md .claude/skills/augur-buffett/SKILL.md

# One-shot, non-interactive
claude -p "Use the augur MCP tools to get the consensus on AAPL"
```

Codex and other MCP-capable terminal agents: register `augur-mcp` as a stdio MCP server (see that tool's docs for the exact command), then use the `SKILL.md` content as instructions.

#### MCP changes in v14

- **ETFs**: `augur_analyze`, `augur_consensus`, `augur_debate` and `augur_committee` accept `asset_type` (`equity` / `etf` / `fund`; empty = detect). On a fund, Dalio, Marks, Soros and ARPS of the 18 masters give readings from technical and market data; the others return "not applicable". With at least 3 applicable the result is a "fund consensus" (equal weights, no position size, no learning record); when missing technicals leave fewer than 3, the consensus is **withheld**: no signal and no position size. `augur_fetch` prints the ETF overview and health checklist for funds.
- **`augur_configure` is deprecated**: Augur's scoring does not call a model, and nothing ever read the setting this tool wrote. From v14 it only returns a deprecation note and writes nothing. The host agent (for example Claude Code) chooses its own model.

---

### Method 4: Telegram / Slack / WeChat Bots

#### Telegram

```bash
pip install 'augur-agents[telegram,data]'
export TELEGRAM_TOKEN=your_bot_token
augur telegram
```

Commands: `/analyze`, `/consensus`, `/ask`, `/personas`, `/help`.

```
User: /analyze AAPL pe=32 gm=46 roe=55
User: /ask buffett Is Apple worth holding right now?
User: /consensus TSLA
```

#### Slack

```bash
pip install 'augur-agents[slack,data]'
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
augur slack
```

Slash commands: `/augur-analyze TICKER [pe=X roe=X ...]` (or `/augur`), `/augur-ask`, `/augur-personas`, `/augur-help`.

#### WeChat

```bash
pip install 'augur-agents[wechat]'
export GEWECHAT_TOKEN='...' GEWECHAT_BASE_URL='http://127.0.0.1:2531/v2/api'
augur wechat --mode personal --port 8066
```

Supports personal WeChat (GeWeChat), WeCom, and Webhook modes. See [README](../../README_EN.md) for details.

---

### Method 5: REST API

Common endpoints on the dashboard (`augur serve`, port 8000):

```bash
# Single-ticker analysis: returns consensus + agents (one per master) + market_data
curl http://localhost:8000/api/analyze/AAPL

# Supply metrics by hand (no data fetch)
curl "http://localhost:8000/api/analyze/AAPL?price=210&pe=32&gross_margins=0.46&roe=0.55"

# Persona list / single persona
curl http://localhost:8000/api/personas
curl http://localhost:8000/api/persona/buffett

# Health check (includes the version)
curl http://localhost:8000/api/health
```

Python example:

```python
import requests

data = requests.get("http://localhost:8000/api/analyze/AAPL").json()
print(f"Consensus signal: {data['consensus']['signal']}")
print(f"Overall score: {data['consensus']['score']:.1f}")
for a in data["agents"]:
    print(f"  {a['agent_name']}: {a['signal']} ({a['score']:.1f}/10)")
```

---

### Method 6: Agentic Workflow Pipelines

Run a configurable multi-step pipeline: **fetch → analyze → consensus → committee → debate → sentiment**.

#### CLI

```bash
# Default: fetch, analyze, consensus
augur workflow AAPL

# Full committee pipeline
augur workflow AAPL --steps fetch,analyze,consensus,committee

# Specific agents + committee question
augur workflow NVDA --agents buffett,munger,dalio --steps fetch,analyze,committee -q "Is the moat widening or narrowing?"

# JSON output (for scripts)
augur workflow TSLA --steps fetch,consensus,sentiment --json
```

Valid steps: `fetch`, `analyze`, `consensus`, `committee`, `debate`, `sentiment`.

#### MCP Tool

With `augur-mcp` (or `augur mcp-server`), call the `augur_workflow` tool:

```
augur_workflow(ticker="AAPL", steps="fetch,analyze,consensus,committee")
```

Optional parameters: `agents` (comma-separated IDs), `question` (committee question).

#### REST API

The standalone REST API server (`augur api`, default port 8900) serves `/api/workflow`:

```bash
augur api   # http://127.0.0.1:8900

curl -X POST http://localhost:8900/api/workflow \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","steps":"fetch,analyze,consensus,committee"}'
```

Python example:

```python
import requests

resp = requests.post(
    "http://localhost:8900/api/workflow",
    json={
        "ticker": "AAPL",
        "steps": "fetch,analyze,consensus,committee",
        "question": "Is the current valuation worth adding to?",
    },
)
data = resp.json()
print(data["step_status"])
print(data["results"]["consensus"]["signal"])
```

---

## 3. Skill Files

```
src/skills/
├── augur-buffett/{SKILL.md,manifest.json}        # Warren Buffett - moat value investing
├── augur-graham/                                 # Benjamin Graham - deep value / margin of safety
├── augur-lynch/                                  # Peter Lynch - GARP growth
├── augur-dalio/                                  # Ray Dalio - macro / All Weather
├── augur-munger/                                 # Charlie Munger - latticework
├── augur-soros/                                  # George Soros - reflexivity
├── augur-marks/                                  # Howard Marks - cycles / contrarian
├── augur-cathie-wood/                            # Cathie Wood - disruptive innovation
├── augur-fisher/                                 # Philip Fisher - growth / scuttlebutt
├── augur-arps/                                   # ARPS - crypto / gold macro
├── augur-aschenbrenner/                          # Leopold Aschenbrenner - AI geopolitics
├── augur-dayu/                                   # Dayu (BTCdayu) - information edge / sentiment momentum
├── augur-thiel/                                  # Peter Thiel - zero to one monopoly
├── augur-duan-yongping/                          # Duan Yongping - integrity, extreme concentration
├── augur-zhang-lei/                              # Zhang Lei (Hillhouse) - long-term structural value
├── augur-li-lu/                                  # Li Lu (Himalaya) - deep value
├── augur-dan-bin/                                # Dan Bin (Oriental Harbor) - brand moats
├── augur-serenity/                               # Serenity - AI / semiconductor supply-chain bottlenecks
├── augur-committee/                              # investment-committee coordinator
└── augur-terminal/                               # terminal workspace
```

Directory names use hyphens (`augur-duan-yongping`); persona IDs in the CLI and API use underscores (`duan_yongping`).

### Skill File Structure

- **Frontmatter**: `name`, `description`, `version`, suggested model, `metadata.augur.persona` (the matching persona ID), `mcp_required: augur-mcp`.
- **Body**: the master's system prompt: voice, core convictions, and how to call the Augur MCP tools for data and scores.
- The actual scoring rules live in `src/augur/personas/<id>.py` (or `personas/custom/*.yaml`); a Skill contains no scoring logic.

---

## 4. Per-Agent Model Configuration

`config/agents.yaml` records a suggested LLM for each master (`defaults` + `per_agent`), and the dashboard settings page reads it. This file **does not affect scores**, which are deterministic rules; it is only a reference for external agents using the Skills and for the optional chat LLM path.

---

## 5. Custom Integration

### 5.1 Create a Custom Agent (YAML)

No code required: add a YAML file under `personas/custom/` and it registers automatically (see `personas/custom/thiel.yaml` for the format):

```yaml
agent_id: my_quant
name: "My Quant Strategy"
description: "Technical indicator-based quant strategy agent"
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

Use any Skill directory as a template:

```bash
cp -r src/skills/augur-buffett src/skills/augur-my-strategy
# Edit SKILL.md and manifest.json: name, description, metadata.augur.persona and the body
```

Then load it the way Method 2 describes for your platform.

### 5.3 Call from Python

```bash
# Scheduled analysis (cron)
0 9 * * 1-5 curl -s http://localhost:8000/api/analyze/AAPL >> ~/augur-reports.log
```

```python
from augur.personas.base import MarketContext
from augur.registry import AgentRegistry, DecisionCoordinator

coord = DecisionCoordinator(AgentRegistry())
ctx = MarketContext(ticker="AAPL", price=210, pe=32, gross_margins=0.46, roe=0.55)
results = coord.analyze_with_all(ctx)
consensus = coord.get_consensus(results, ticker="AAPL", context=ctx)
print(consensus.signal.value, round(consensus.score, 1))
```

### 5.4 Standalone Agent Process

Run in the background with tmux or systemd:

```bash
# tmux
tmux new-session -d -s augur 'augur serve --port 8000'

# systemd service (replace ExecStart with the absolute path of augur on your machine, e.g. `which augur`)
cat <<EOF | sudo tee /etc/systemd/system/augur.service
[Unit]
Description=Augur Investment Analysis Dashboard
After=network.target

[Service]
ExecStart=/usr/local/bin/augur serve --port 8000
Restart=always
User=augur

[Install]
WantedBy=multi-user.target
EOF
```

### 5.5 Multi-Agent Comparison

Run only a subset of masters:

```python
from augur.personas.base import MarketContext
from augur.registry import AgentRegistry, DecisionCoordinator

coord = DecisionCoordinator(AgentRegistry())
ctx = MarketContext(ticker="AAPL", price=210, pe=32, gross_margins=0.46, roe=0.55)
results = coord.analyze_with_all(ctx, enabled_personas=["buffett", "lynch", "dayu", "duan_yongping"])
for agent_id, r in results.items():
    print(f"{r.agent_name:>30}: {r.signal.value.upper():>8} ({r.score:.1f}/10)")
```

---

## 6. Architecture Overview

![Augur Architecture](../images/architecture-baoyu.svg)

```
User Input
  │
  ├──→ Skill (Hermes Studio / Claude Desktop / Claude Code / OpenClaw) → augur-mcp → 18 Agents → Consensus
  ├──→ Augur Dashboard (augur serve) → src/augur/ → 18 Agents → Consensus → Result
  ├──→ Telegram / Slack / WeChat Bot → Messaging platform interaction
  └──→ REST API (augur serve / augur api) → Automated workflow
```

---

## 7. Quick Reference Card

| Platform | One-line start | Interaction |
|----------|---------------|-------------|
| Dashboard | `augur serve` | Web browser |
| MCP server | `augur-mcp` | Any MCP client |
| Hermes Studio | `mcp_servers.augur.command: augur-mcp` + `skills_dir: ./src/skills` | Chat `/skill augur-buffett` |
| Claude Code | `claude mcp add augur -- augur-mcp` | Terminal |
| Telegram | `augur telegram` | Messaging |
| Slack | `augur slack` | Messaging |
| API | `curl localhost:8000/api/analyze/AAPL` | HTTP |

---

## 8. FAQ

**Q: Do I need a GPU or high-performance hardware?**
A: No. Scoring is local rule evaluation; you only need Python.

**Q: Can it work offline?**
A: The scoring engine runs fully offline (pass metrics by hand or use cached data); live market data needs a network connection. An LLM is used only on the optional chat path and by external agents.

**Q: How do I add a new investor?**
A: Two ways: 1) write YAML under `personas/custom/` (no code); 2) write a Python agent under `src/augur/personas/` (more powerful).

**Q: Can all 18 agents work simultaneously?**
A: Yes. `analyze_with_all` runs all agents in parallel and the consensus engine aggregates the results.

**Q: What asset types are supported?**
A: US stocks, HK stocks, A-shares, and crypto, all in one system.

---

*For more questions, open a GitHub Issue or see [README_EN.md](../../README_EN.md)*
