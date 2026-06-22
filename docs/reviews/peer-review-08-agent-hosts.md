# Peer Review #8 — Agent Host Integration

**Scope:** Hermes (`hermes-agents/*.yaml`, `docs/hermes-setup-guide.md`), OpenClaw (`docs/openclaw-setup-guide.md`, skill `manifest.json`), Claude Desktop (`.mcp.json`, `SKILL.md`), and the agentic Bloomberg vision (Dashboard terminal workspace + MCP workflow pipelines).

**Verdict:** MCP analysis tools are largely wired; **terminal workspace state is Dashboard-only**, and **workflow is inconsistently declared** across host manifests. Hosts can run single-step analysis but cannot yet orchestrate a unified “Bloomberg terminal” session from the agent side.

---

## Agentic Bloomberg Vision — Current Gap

The v10.14+ product story pairs two agentic primitives:

| Primitive | Implementation | Agent-host exposure |
|-----------|----------------|---------------------|
| **Workflow pipeline** | `augur_workflow` MCP tool (10 tools total in `mcp_server.py`) | Declared in Hermes docs and `augur-committee` skill; **missing from `.mcp.json` tools list and 17/18 persona manifests** |
| **Terminal workspace** | `src/augur/workspace.py` + Dashboard `/api/workspace*` | **REST-only** — no MCP tool; Hermes/OpenClaw agents cannot read or apply `analyst`/`trader`/`committee`/`minimal` presets |

An agent host that loads `augur-buffett` today gets analyze/fetch/consensus but cannot:

1. Run `fetch → analyze → consensus → committee` in one MCP call unless the host ignores manifest `required_tools` and discovers all server tools.
2. Switch the paired Dashboard to `committee` layout when convening a multi-master session.
3. Filter enabled personas via workspace profile before consensus.

The Dashboard remains the “terminal”; agent hosts remain “chat windows” with no shared layout state.

---

## Platform Audit

### Hermes

**Strengths**

- `docs/hermes-setup-guide.md` is the most accurate host doc: lists **10 MCP tools** including `augur_workflow`, with examples.
- `hermes-agents/*.yaml` provides copy-paste Studio configs for all 18 personas.
- Descriptions advertise `augur_workflow MCP`.

**Gaps**

- `hermes-agents/*.yaml` `required_tools` lists only `analyze`, `consensus`, `fetch` — **not** `mcp_augur_workflow`, despite description text.
- No Hermes yaml for `augur-committee` or a workflow coordinator agent.
- Workspace integration documented only as optional Dashboard curl examples; no MCP bridge for agents running beside the terminal.
- `agent-integration-guide.md` still references obsolete paths (`skills/buffett/SKILL.md` vs `skills/augur-buffett/`).

### OpenClaw

**Strengths**

- `manifest.json` per skill is a good universal contract (`compatibility: openclaw`).
- Setup guide covers bulk `openclaw skill install ./skills/augur-*`.
- `.mcp.json` auto-discovery path documented.

**Gaps**

- `docs/openclaw-setup-guide.md` (EN + ZH) still says **9 tools** and omits `mcp_augur_workflow` from the verification list.
- Quick-verify script expects 9 tools — will pass even when workflow is broken/unlisted.
- Persona `manifest.json` `required_tools` omit workflow (only committee includes it).
- Config examples use `augur` + `args: [mcp-server]` while `.mcp.json` uses `augur-mcp` — two entry points, no canonical note in OpenClaw docs.

### Claude Desktop

**Strengths**

- Minimal MCP config (`command: augur-mcp`) works; tools auto-discovered from server.
- `.mcp.json` at repo root supports Claude Code project discovery.

**Gaps**

- No Claude-native skill loader — users must manually paste `SKILL.md` system prompts.
- `.mcp.json` **tools** array lists 9 names and omits `augur_workflow`; **skills** array lists 19 skills but does not declare tool dependencies per skill.
- No Claude Desktop doc for workspace presets or pairing with Dashboard iframe.
- Version fields in persona manifests (`9.0.3`) vs committee (`10.14.0`) confuse “which Augur generation am I on?”

---

## Cross-Critiques

| Tension | Hermes says | OpenClaw says | Reality in code |
|---------|-------------|---------------|-----------------|
| Tool count | 10 tools | 9 tools | `mcp_server.py` registers **10** |
| Workflow | First-class in setup guide | Not in tool list or verify script | Server has it; manifests omit it (except committee) |
| MCP entry | `augur-mcp` | `augur mcp-server` | Both work; `.mcp.json` uses `augur-mcp` only |
| Workspace | curl to Dashboard API | Not mentioned | No MCP; agents and terminal are decoupled |
| Hermes yaml vs skills | `hermes-agents/buffett.yaml` | `skills/augur-buffett/manifest.json` | Parallel sources; yaml mentions workflow, manifest does not require it |

**Hermes → OpenClaw:** Hermes docs are ahead on workflow; OpenClaw docs will mislead operators running the verify script (false green on 9/10).

**OpenClaw → Claude Desktop:** OpenClaw’s `manifest.json` contract is richer than Claude’s bare MCP block, but Claude’s `.mcp.json` is the only project-level manifest — and it is stale on tool enumeration.

**Claude Desktop → Hermes:** Claude relies on server-side tool discovery (works); Hermes yaml `required_tools` gates may **block** workflow even when the server exposes it — description promises more than the gate allows.

---

## Three Integration Improvements

### 1. Expose workspace via MCP (`augur_workspace`)

Add MCP tools mirroring Dashboard REST:

- `augur_workspace_get` — active profile + preset fields (`default_page`, `enabled_personas`, `show_ticker_tape`, …)
- `augur_workspace_set` — apply preset or partial override
- `augur_workspace_profiles` — list/switch named profiles

**Why:** Lets an agent host say “convene committee on NVDA” and atomically set Dashboard to `committee` preset + enabled personas, completing the Bloomberg terminal vision without curl sidecars.

### 2. Normalize manifest tool contracts (regenerate + sync `.mcp.json`)

- Add `mcp_augur_workflow` to **all** persona `manifest.json` `required_tools` (and `scripts/generate_skills.py` source).
- Sync `.mcp.json` `tools` array to all 10 server tools.
- Update OpenClaw verify script and both setup guides to expect 10 tools.
- Bump manifest versions to match release train (10.15.x).

**Why:** Hosts that honor `required_tools` (OpenClaw, some Hermes builds) currently under-declare capability; committee-only workflow creates a false split between “single master” and “pipeline” skills.

### 3. Add `augur-terminal` meta-skill + Hermes committee yaml

Ship one coordinator skill (or extend `augur-committee`) whose `SKILL.md` documents the full agentic session:

```
augur_workflow(ticker, steps="fetch,analyze,consensus,committee", agents=...)
→ augur_workspace_set(preset="committee", enabled_personas=agents)
→ open Dashboard at resolved landing URL
```

Add `hermes-agents/committee.yaml` matching `skills/augur-committee`.

**Why:** Gives operators one entry point for “Bloomberg session” instead of 19 persona skills with divergent tool lists.

---

## Implemented Fix (this review)

**`.mcp.json` — add `augur_workflow` to the `tools` array** so Claude Code / OpenClaw project discovery matches the server’s 10-tool surface. Remaining manifest regeneration (persona `required_tools`, OpenClaw doc/tool-count sync) tracked as follow-up under improvement #2.

---

## References

| Artifact | Path |
|----------|------|
| MCP server (10 tools) | `src/augur/mcp_server.py` |
| Workspace module | `src/augur/workspace.py` |
| Project MCP manifest | `.mcp.json` |
| Skill manifests | `skills/augur-*/manifest.json` |
| Hermes agent configs | `hermes-agents/*.yaml` |
| Manifest generator | `scripts/generate_skills.py` |
| OpenClaw setup | `docs/openclaw-setup-guide.md` |
| Hermes setup | `docs/hermes-setup-guide.md` |
