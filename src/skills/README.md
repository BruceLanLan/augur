# Augur Skills

MCP-compatible agent skill definitions for the 18 Augur investment personas plus the Investment Committee coordinator.

Each skill directory contains:
- `SKILL.md` — YAML frontmatter + persona system prompt (Hermes/Claude Desktop format)
- `manifest.json` — Universal JSON manifest (OpenClaw, Hermes Studio, Claude Desktop, any MCP client)

---

## What Are These Skills?

Each skill is a self-contained agent definition that wires a specific investor persona (Buffett, Graham, Dalio, etc.) to the Augur MCP server. Load a skill to get the full persona system prompt and automatic access to the Augur MCP tools (`mcp_augur_fetch`, `mcp_augur_analyze`, `mcp_augur_consensus`, `mcp_augur_debate`, `mcp_augur_committee`, `mcp_augur_sentiment`, `mcp_augur_workflow`, plus persona management tools).

---

## How to Use

### Hermes Studio

```yaml
# hermes/config.yaml
mcp_servers:
  augur:
    command: augur-mcp

skills_dir: ./skills
```

Then activate a skill in chat: `/skill augur-buffett`

### Claude Desktop

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp" }
  }
}
```

Copy the desired `SKILL.md` content as your system prompt, or load it via a skill loader extension.

### OpenClaw

OpenClaw reads `manifest.json` from any skills directory:

```bash
openclaw skill install ./skills/augur-buffett
```

Or install all skills at once:

```bash
for d in skills/augur-*; do openclaw skill install "$d"; done
```

### Any MCP Client

1. Start the Augur MCP server: `augur-mcp`
2. Use the `SKILL.md` content as the agent system prompt
3. The MCP tools are auto-discovered from the running server

### `augur_workflow` — Agentic Multi-Step Pipelines

Use `augur_workflow` when you want a single MCP call to run a configurable chain instead of orchestrating each tool manually:

```
augur_workflow(ticker="AAPL", steps="fetch,analyze,consensus")
augur_workflow(ticker="NVDA", steps="fetch,analyze,consensus,committee,debate", agents="buffett,duan_yongping,cathie_wood", question="Hold or trim?")
augur_workflow(ticker="TSLA", steps="fetch,sentiment")
```

Valid steps: `fetch`, `analyze`, `consensus`, `committee`, `debate`, `sentiment`. Default: `fetch,analyze,consensus`.

The **augur-committee** skill is the best fit for workflows that include the `committee` or `debate` steps.

### Terminal Workspace (Dashboard)

When running the Augur Dashboard alongside Hermes, customize the Bloomberg-style terminal layout under **Settings → Terminal Workspace** (or via `GET/PUT /api/workspace`). Presets: `analyst`, `trader`, `committee`, `minimal`. Preferences persist to `~/.augur/workspace.yaml` (default page, hidden nav, ticker tape, committee preset, enabled personas).

---

## manifest.json Format

```json
{
  "name": "augur-buffett",
  "version": "9.0.3",
  "description": "...",
  "author": "BruceBlue (https://x.com/BruceBlue)",
  "license": "MIT",
  "type": "mcp-skill",
  "model": {
    "default": "claude-sonnet-4-6",
    "alternatives": ["gpt-4o", "deepseek-chat"]
  },
  "mcp": {
    "server": "augur",
    "command": "augur-mcp",
    "required_tools": ["mcp_augur_analyze", "mcp_augur_fetch", "mcp_augur_consensus"]
  },
  "compatibility": ["hermes", "openclaw", "claude-desktop", "any-mcp"],
  "tags": ["investing", "value", "moat", "fundamental"],
  "language": "en",
  "persona_id": "buffett"
}
```

---

## Installing a Single Skill vs All Skills

**Single skill** — copy or symlink one directory:

```bash
cp -r skills/augur-buffett ~/.config/hermes/skills/
```

**All skills** — regenerate from source (requires the full Augur repo):

```bash
python3 scripts/generate_skills.py
```

This rewrites all `SKILL.md` and `manifest.json` files from the persona registry.

---

## Personas

| Skill | Persona | School | Language |
|---|---|---|---|
| augur-buffett | Warren Buffett | value | en |
| augur-graham | Benjamin Graham | deep-value | en |
| augur-munger | Charlie Munger | value | en |
| augur-lynch | Peter Lynch | garp | en |
| augur-dalio | Ray Dalio | macro | en |
| augur-soros | George Soros | macro | en |
| augur-marks | Howard Marks | cycle | en |
| augur-cathie-wood | Cathie Wood | growth | en |
| augur-fisher | Philip Fisher | growth | en |
| augur-thiel | Peter Thiel | monopoly | en |
| augur-arps | ARPS | macro | en |
| augur-aschenbrenner | Leopold Aschenbrenner | ai-geo | en |
| augur-dayu | 大宇 (BTCdayu) | momentum | en |
| augur-duan-yongping | 段永平 | benfun | zh |
| augur-zhang-lei | 张磊（高瓴） | structural | zh |
| augur-li-lu | 李录（喜马拉雅） | deep-value | zh |
| augur-dan-bin | 但斌（东方港湾） | brand | zh |
| augur-serenity | Serenity | ai-supply | en |
| augur-committee | Committee Chair | — | en |
