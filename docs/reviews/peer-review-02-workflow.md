# Peer Review #2 — Agentic Workflow

**Reviewer domain:** `workflow.py`, `mcp_server.py` (`augur_workflow`), `cli.py`, `api.py`, `agent-integration-guide.md`  
**Cross-review targets:** `workspace.py`, `consensus/*`, `skills/README.md`  
**Date:** 2026-06-22 · **Scope:** v10.15 agentic pipeline

---

## Executive Summary

The v10.15 workflow stack delivers a usable **single-call orchestration** surface (CLI, REST, MCP) over six named steps. It aligns with Hermes/Claude Desktop expectations for tool discovery and string summaries. Gaps remain in **cross-layer persona filtering**, **partial-failure semantics**, and **step composability guarantees** compared to mature agent frameworks (Claude tool-use loops, Hermes skill + MCP chaining).

---

## Own Domain Review

### Strengths

| Area | Observation |
|------|-------------|
| **Surface parity** | Same `run_workflow()` backs CLI (`augur workflow`), REST (`POST /api/workflow`), and MCP (`augur_workflow`). Parameters and defaults are consistent. |
| **MCP ergonomics** | `_run_workflow_tool()` is extracted for unit testing; ticker validation and step errors return agent-readable strings (not stack traces). |
| **Documentation** | `agent-integration-guide.md` Method 8 and `skills/README.md` § `augur_workflow` give copy-paste examples for CLI, MCP, and curl. |
| **Step model** | Flat comma-separated steps are easy for LLMs to specify; `parse_steps()` validates early. |

### Gaps vs Claude / Hermes Agent Patterns

| Pattern | Claude / Hermes expectation | Current Augur behavior |
|---------|----------------------------|------------------------|
| **Tool loop with state** | Agent sees prior step output and decides next tool | Workflow runs a fixed chain internally; agent gets one final summary string (MCP) or JSON blob |
| **Partial failure** | Failed tool returns structured error; agent can retry or skip | Only `sentiment` catches exceptions; `fetch`/`analyze`/`debate` failures abort the whole run |
| **Persona scoping** | Skill manifest + workspace prefs define active agents | Dashboard respects `enabled_personas`; workflow ignored it until this review (now wired when `agents=""`) |
| **Observability** | Step-level status, timing, token/cost metadata | No per-step duration, no `step_status` envelope; debate re-runs analysis instead of reusing prior responses |
| **Composable primitives** | Each MCP tool is independently callable; workflow is optional sugar | Correct for individual tools, but workflow steps are not independently addressable mid-chain |

### Step Composability

**What works**

- Steps are order-agnostic at parse time: `fetch,consensus` skips analyze but still fetches context and runs all agents for consensus.
- `agents` param overrides persona set explicitly.
- `question` only affects committee output formatting.

**What does not**

- **No dependency validation:** `consensus` without upstream analyze still triggers a full `analyze_with_all` (implicit, undocumented). `committee` alone does the same. Agents cannot express "reuse cached analyze."
- **Duplicate work:** When both `consensus` and `committee` appear, `get_consensus()` is called twice with identical inputs (lines 76–84 and 86–100 in `workflow.py`).
- **Debate isolation:** `debate` calls `coordinator.run_debate()` independently; it does not build on prior `analyze` responses even when `analyze` is in the same chain.
- **Sentiment decoupling:** `sentiment` never receives ticker context from `fetch`; no shared `ctx` object in results for downstream agent reasoning.

### Error Handling

| Layer | Behavior | Gap |
|-------|----------|-----|
| **CLI** | Catches `ValueError` + generic `Exception`; exit code 1 | Good |
| **MCP** | Returns `"Error: …"` / `"Workflow failed …"` strings | Good for LLM parsing |
| **REST API** | Catches only `ValueError`; unhandled exceptions → 500 | Inconsistent with CLI/MCP |
| **Workflow core** | `sentiment` → `{"error": str}`; all other steps propagate | No partial result on fetch failure |
| **Agent selection** | Unknown agent IDs silently dropped (now reported as `agents_skipped`) | Was silent; still no hard fail option |

---

## Cross-Review: Workspace (`workspace.py`)

### Critique 1 — Persona prefs not propagated to workflow (fixed in this review)

`get_enabled_personas()` drives Dashboard analyze/committee/debate routes via `coordinator.analyze_with_all(ctx, enabled_personas=…)`, but `run_workflow()` previously called `analyze_with_all(ctx)` with no filter when `agents=""`. A Hermes user configuring **Settings → enabled personas** would see a different agent set in the terminal than in `augur_workflow(ticker="AAPL")`.

**Fix applied:** When `agents` is empty, workflow now reads workspace `enabled_personas` and exposes `agents_filter` in the JSON output.

### Critique 2 — Workspace is UI-centric, not workflow-aware

`LAYOUT_PRESETS` include `committee_preset` and page routing, but there is no preset that maps to workflow step defaults (e.g. `"trader"` → `fetch,analyze,consensus` vs `"committee"` → full chain). Terminal layout and agentic pipeline configuration live in separate silos. For Claude/Hermes users, a single `workflow_preset` field (or mapping from `layout_preset`) would reduce configuration drift.

---

## Cross-Review: Consensus (`consensus/*`)

### Critique 1 — Feedback paths assume repo checkout

`consensus/paths.py` resolves `FEEDBACK_DIR` to `repo_root/feedback/` via `Path(__file__).parents[3]`. Installed via PyPI (`pip install augur-agents`), this points at site-packages, not user data. `load_feedback_json("industry_matrix.json")` silently returns `{}`, so industry/regime weighting runs on hardcoded matrices only. Workflow consensus results differ between dev checkout and production install without any warning.

### Critique 2 — Weighting stack is invisible to workflow consumers

`build_consensus_weights()` blends industry matrix, regime multipliers, and `RegimeRouter` overlays — rich metadata (`industry`, `regime`, `regime_features`) that `get_consensus()` uses internally but never surfaces in workflow `results.consensus`. Agents following Claude-style "show your work" patterns cannot explain *why* consensus weighted Cathie Wood higher for NVDA. Exposing `weight_ctx` (or a summary) in workflow output would close the observability gap.

---

## Cross-Review: `skills/README.md`

The workflow section (lines 65–77) is accurate and well-placed after per-client setup. Minor gaps:

- No mention that **`agents` overrides workspace `enabled_personas`** (priority order undocumented).
- No **error/partial-result** guidance for agents (what if sentiment fails but consensus succeeded?).
- **`debate` rounds hardcoded to 2** in workflow but configurable via standalone `augur_debate` MCP tool — inconsistency not noted.

---

## Three Recommended Workflow Improvements

### 1. Per-step status envelope (partial failure)

Return a top-level `step_status: {step: "ok"|"error"|"skipped"}` and wrap each step in try/except (matching sentiment's pattern). Enables Hermes/Claude agents to continue reasoning on partial data instead of losing the entire run on a yfinance timeout.

### 2. Step dependency graph + deduplication

Define explicit prerequisites (`consensus` → requires agent responses; reuse if `analyze` already ran). Cache `responses` and first `consensus` result; pass into committee/debate. Document implicit analyze behavior or reject invalid orderings at `parse_steps()` time.

### 3. Structured MCP response option

Add `format="json"` (or return JSON by default) on `augur_workflow` so agents receive machine-parseable `results` without scraping the text summary. Claude tool-use and Hermes function calling both prefer structured payloads for multi-step chaining.

---

## Implementation in This Review

**Change:** Wire workspace `enabled_personas` into `run_workflow()` when `agents=""`; report `agents_filter` in output and `agents_skipped` for unknown explicit IDs.

**Test:** `tests/test_workflow_enabled_personas.py`

---

## Verdict

The workflow layer is **production-ready for happy-path demos** and correctly mirrors across CLI/API/MCP. To match Claude/Hermes agent-loop maturity, prioritize partial-failure semantics, eliminate duplicate consensus work, and surface consensus weighting metadata. Workspace and consensus modules are solid in isolation but were **not fully connected** to the agentic pipeline until persona filtering was bridged.
