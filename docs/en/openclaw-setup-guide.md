🇨🇳 [中文](../openclaw-setup-guide.md) | 🇺🇸 English

# OpenClaw Integration with Augur — Complete Guide

> Augur exposes 14 MCP tools and 19 skills to OpenClaw.
> After setup, use `/skill augur-buffett` or just chat naturally.

---

## Prerequisites

- OpenClaw ≥ 0.8 (MCP skill registration support)
- Python 3.10+
- Augur installed

```bash
git clone https://github.com/BruceLanLan/augur.git
cd augur
pip install -e ".[data]"

# Verify
augur mcp-server   # No error = OK (Ctrl+C to exit)
```

---

## Option 1: MCP Server (Recommended)

OpenClaw calls `augur mcp-server` via stdio and auto-registers all 14 tools.

### Step 1 — Edit OpenClaw Config

Usually at `~/.openclaw/config.yaml`:

```yaml
mcp_servers:
  augur:
    command: augur
    args: [mcp-server]
    description: "Augur — 18-master multi-agent investment analysis"
```

Or via OpenClaw Web UI **Settings → MCP Servers → Add**:

| Field | Value |
|-------|-------|
| Name | `augur` |
| Command | `augur` |
| Args | `mcp-server` |

### Step 2 — Verify Tool Registration

Restart OpenClaw, then:

```
/tools list
```

You should see 14 `mcp_augur_*` tools:

```
mcp_augur_analyze       — Single or all-master analysis
mcp_augur_consensus     — Weighted consensus + Kelly sizing
mcp_augur_committee     — Investment committee session
mcp_augur_debate        — Structured bull/bear debate
mcp_augur_fetch         — Real-time market data (yfinance)
mcp_augur_sentiment     — Social sentiment (StockTwits + news)
mcp_augur_list_personas — List all 18 masters
mcp_augur_configure     — Configure per-master model params
mcp_augur_create_persona — Create a custom YAML persona
mcp_augur_workflow      — Composable multi-step pipeline (fetch→analyze→consensus→committee→debate→sentiment)
mcp_augur_workspace_get — Read the user's Dashboard layout/enabled personas
mcp_augur_workspace_set — Write terminal layout/enabled personas on the user's behalf
mcp_augur_workspace_profiles — List/create/delete/switch named workspace profiles
mcp_augur_run_skill     — Run a built-in skill (earnings-prep, etc.)
```

### Step 3 — Start Analyzing

```
Analyze NVDA from Warren Buffett's perspective

Convene the Classic Value committee (Buffett, Graham, Munger, Fisher) on TSLA

Give me AAPL multi-master weighted consensus and Kelly position sizing
```

---

## Option 2: Skill Registration

Augur ships 19 pre-built Hermes/OpenClaw skills — one per master.

### Install All Skills

```bash
# From augur directory
for d in skills/augur-*; do openclaw skill install "$d"; done
```

### Use a Specific Master

```
/skill augur-buffett AAPL
/skill augur-dalio TSLA
/skill augur-committee NVDA --preset value
```

### Skill Catalog

| Skill | Master | School |
|-------|--------|--------|
| `augur-buffett` | Warren Buffett | Classic Value |
| `augur-graham` | Benjamin Graham | Classic Value |
| `augur-munger` | Charlie Munger | Classic Value |
| `augur-fisher` | Philip Fisher | Classic Value |
| `augur-lynch` | Peter Lynch | Growth |
| `augur-cathie-wood` | Cathie Wood | Innovation |
| `augur-thiel` | Peter Thiel | Contrarian |
| `augur-aschenbrenner` | Leopold Aschenbrenner | AGI / Compute |
| `augur-dalio` | Ray Dalio | Macro |
| `augur-soros` | George Soros | Macro |
| `augur-marks` | Howard Marks | Macro |
| `augur-arps` | ARPS | Real Rates |
| `augur-duan-yongping` | Duan Yongping 段永平 | China Value (full Chinese) |
| `augur-zhang-lei` | Zhang Lei 张磊 | China Value (full Chinese) |
| `augur-li-lu` | Li Lu 李录 | China Value (full Chinese) |
| `augur-dan-bin` | Dan Bin 但斌 | China Value (full Chinese) |
| `augur-dayu` | BTCdayu 大宇 | Crypto Sentiment |
| `augur-serenity` | Serenity | AI Supply Chain |
| `augur-committee` | Investment Committee | Multi-master verdict |

---

## Option 3: `.mcp.json` Auto-Discovery

Drop a `.mcp.json` in your project root — OpenClaw and Claude Code discover it automatically:

```json
{
  "mcpServers": {
    "augur": {
      "command": "augur",
      "args": ["mcp-server"]
    }
  }
}
```

Augur ships this file at the repo root — cloning gives you auto-discovery for free.

---

## Troubleshooting

### `augur: command not found`

```bash
pip install -e ".[data]"
which augur          # should print a path
augur --version      # should print version number
```

If using a virtualenv, pin the full path in OpenClaw config:

```yaml
mcp_servers:
  augur:
    command: /path/to/.venv/bin/augur
    args: [mcp-server]
```

### Tool calls time out

Analysis takes 5–30 s depending on master count. Extend timeout:

```yaml
mcp_servers:
  augur:
    command: augur
    args: [mcp-server]
    timeout: 120   # seconds
```

### API key setup

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Quick Validation Script

```bash
( printf '%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"check","version":"0"}}}' \
    '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
  sleep 8 ) | augur mcp-server 2>/dev/null | python3 -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line)
    if d.get('id') == 2:
        tools = d['result']['tools']
        print(f'✅ {len(tools)} tools registered:')
        for t in tools: print(f'  - {t[\"name\"]}')
"
```

Expected output:
```
✅ 14 tools registered:
  - augur_analyze
  - augur_consensus
  - augur_list_personas
  ...
```

---

*For Hermes Agent setup, see [hermes-setup-guide.md](hermes-setup-guide.md)*
