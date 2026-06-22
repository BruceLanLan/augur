# Peer Review #5 — Customization & DIY

**Reviewer domain:** `create_persona`, workspace presets, `enabled_personas`, YAML personas, MCP `augur_create_persona`, home widgets  
**Cross-review targets:** `consensus/*`, `workflow.py`  
**Date:** 2026-06-22 · **Scope:** v10.15 customization surfaces

---

## Executive Summary

Augur’s DIY story is **split-brained**: persona authoring and terminal layout are genuinely user-facing, but consensus weighting and home layout remain opaque or API-only. Compared to a “user-built Bloomberg,” Augur delivers roughly **40% of terminal customization** (nav presets, profiles, persona roster) and **60% of agent authoring** (form + YAML + hot-reload), while **panel/widget DIY is ~15%** (persist API, no builder UI). The product reads as “configurable analyst desk,” not yet “build your own terminal.”

---

## How Close to a User-Built Bloomberg?

| Bloomberg expectation | Augur today | Gap |
|----------------------|-------------|-----|
| Drag/reorder panels, save layouts per desk | Fixed home grid; `collapsed_panels` + `pinned_tickers` via API only | No visual panel manager |
| Function keys / launchpad to any screen | 4 layout presets + hidden nav toggles | No user-defined preset authoring |
| Custom formulas / fields on screen | YAML factor rules (`pe < 15`) with AST-safe eval | No field picker; opaque ctx namespace |
| Watchlist strip you control | `pinned_tickers` persisted to `~/.augur/home_widgets.yaml` | No Settings or home UI to edit strip |
| Transparent weighting in multi-source views | Industry + regime + learning blend inside `get_consensus()` | No inspector; hardcoded matrices |
| User-defined “functions” (scripts) | Custom personas + MCP tools | MCP persona create is ephemeral |

**Verdict:** Augur is closest on **agent roster DIY** (create/edit personas, filter committee) and **nav shell DIY** (profiles, hide pages). It is farthest on **dashboard composition** and **consensus explainability** — the two places Bloomberg power users spend most customization time.

---

## Domain Review

### 1. `create_persona` (dashboard + API)

**Strengths**

- Form-first UX with live YAML preview, modal confirm, and three starter presets (`minimalist_value`, `momentum_trader`, `contrarian_macro`) in `create_persona.html`.
- Real-time Agent ID validation against existing custom personas.
- CRUD via `/api/custom-persona` persists to `personas/custom/*.yaml` and hot-reloads the registry — survives restart.
- Edit mode loads persona detail from `/api/persona/{id}` and PUT updates.

**Gaps**

- Factor `if:` conditions are free-text strings; no autocomplete for `MarketContext` fields (`pe`, `roe`, `fear_greed`, etc.).
- Presets are hardcoded in page JS — users cannot save their own template library.
- Scoring weights are not validated to sum to 1.0 in the UI (loader normalizes, but preview misleads).

### 2. Workspace presets (`src/augur/workspace.py`)

**Strengths**

- Four Bloomberg-style presets (`analyst`, `trader`, `committee`, `minimal`) with sensible defaults: landing page, hidden nav, ticker tape.
- Multi-profile YAML at `~/.augur/workspace.yaml` with export/import.
- Settings UI: create/switch/delete profiles, preview preset before save.

**Gaps**

- Presets are **code-defined only** — users cannot fork “my day-trading layout” into a fifth preset slug.
- `committee_preset` is stored per preset but **never consumed** by committee UI (dead field since Review #1).
- `saveWorkspaceConfig()` previously omitted `enabled_personas` even though `WorkspaceBody` accepts it — backend/UI drift.

### 3. `enabled_personas`

**Strengths**

- Normalized in `_normalize_profile_settings`, exposed via `get_enabled_personas()`.
- Wired into dashboard analyze, committee, and debate routes through `analyze_with_all(..., enabled_personas=...)`.
- v10.15 tests cover filter semantics (empty = all, subset, unknown IDs ignored).
- Workflow layer now respects roster when `--agents` is empty (Review #2 fix).

**Gaps (before this review)**

- **No Settings UI** — power users had to `PUT /api/workspace` or hand-edit YAML.
- Home hero and copy still reference “18 masters” regardless of roster size.
- No per-page override (e.g. committee uses full roster but stock analyze uses subset).

### 4. YAML personas (`src/augur/persona_loader.py`)

**Strengths**

- Declarative schema: `agent_id`, `identity`, `philosophy`, `scoring_weights`, `factors` with `base` + `rules`.
- AST sandbox for rule conditions — no arbitrary code execution.
- Bulk load via `load_personas_from_dir()`; integrates with registry at startup.

**Gaps**

- No JSON Schema or CLI `augur persona validate` for offline authoring.
- Custom personas live under repo `personas/custom/` when created via dashboard (couples user data to checkout path unless symlinked).
- Built-in personas remain Python classes — asymmetric DIY (custom = YAML, builtin = code).

### 5. MCP `augur_create_persona` (`src/augur/mcp_server.py`)

**Strengths**

- Agent-friendly entry: paste YAML, get registered persona in one tool call.
- Size limit (10KB) and validation via `load_persona_yaml`.

**Gaps**

- Writes to a **temp file**, registers in memory, deletes temp file — **does not persist** to `personas/custom/`.
- Restart loses MCP-created personas unless user also calls dashboard API or drops YAML manually.
- Parity break: dashboard path persists + hot-reloads; MCP path is session-only.

---

## Three DIY Improvements (prioritized)

### A. Home widget builder UI (highest impact)

**Problem:** `/api/home/widgets` supports `pinned_tickers` and `collapsed_panels` across 12 panel IDs, but **no template exposes controls**. Users cannot DIY the Bloomberg-style home board without curl.

**Fix:** Add a “Customize Home” drawer on `index.html` (or Settings subsection): drag-to-reorder optional phase 2; phase 1 = pin ticker chips + panel show/hide toggles calling `PUT /api/home/widgets`.

### B. Persist MCP `create_persona` like the dashboard

**Problem:** Hermes/Claude users authoring personas via MCP lose work on process restart.

**Fix:** After successful `load_persona_yaml`, write to `~/.augur/personas/custom/{agent_id}.yaml` (or repo `personas/custom/` with configurable path), mirror dashboard hot-reload. Return path in tool response.

### C. Consensus weight inspector

**Problem:** Consensus is a black box — `build_consensus_weights()` blends industry matrix, regime router, and learning engine with no user visibility.

**Fix:** Expose `/api/consensus/weights?ticker=AAPL` returning `{industry, regime, per_agent_weights, sources}` and a collapsible “How we weighted this” panel on stock analyze. Optional: user override file `~/.augur/weight_overrides.yaml` merged last.

---

## Two Critiques: Other Modules

### Critique 1 — Consensus module (`consensus/*`, `registry.py`)

Industry boosts live in hardcoded `_SECTOR_WEIGHTS` in `industry_matrix.py`. Regime and learning overlays further adjust weights inside `get_consensus()` with no audit trail. A DIY-minded user can define custom personas but **cannot tune how their personas combine** — the opposite of Bloomberg’s user formulas. Feedback JSON paths (`load_feedback_json`) assume repo layout, so trained matrices may not load in pip-installed deployments.

**Suggested fix:** Ship default matrices as data files under `~/.augur/consensus/`, document override format, and surface active multipliers in analyze API metadata.

### Critique 2 — Workflow rigidity (`workflow.py`)

Workflow steps are a fixed comma-separated chain with implicit dependencies (`consensus` silently re-runs full analyze). Users cannot define custom pipelines (“my desk macro: fetch → sentiment → 3-agent subset → consensus”) as saved presets tied to workspace profiles. Layout preset `trader` and workflow default steps are unrelated silos.

**Suggested fix:** Add `workflow_steps` to workspace profile schema and `augur workflow --profile day-trading` that loads both roster and step list.

---

## Fix Implemented in This Review (Reviewer #5)

**Issue:** `enabled_personas` backend complete but invisible — Settings saved layout without roster, breaking the “custom committee desk” story.

**Change:** `dashboard/templates/settings.html` — added Analysis Committee toggles (per-persona checkboxes, Enable All / Clear All), wired `applyWorkspaceFields` / `saveWorkspaceConfig` to persist `enabled_personas`, with validation when zero personas selected. i18n keys added in `dashboard/static/js/i18n.js` (zh/en/ja/ko).

---

## Test Plan (recommended)

- [ ] Settings: select subset → Save → reload page → checkboxes match; analyze API runs only selected agents
- [ ] Settings: all checked → Save → `enabled_personas: []` in workspace YAML → analyze runs full roster
- [ ] Settings: none checked → Save blocked with toast
- [ ] Profile switch preserves per-profile `enabled_personas`
- [ ] MCP `create_persona` still session-only (document until Fix B)

---

## Verdict

**Ship persona authoring and workspace profiles** — they are the clearest DIY wins. **Do not claim Bloomberg-grade customization** until home widgets have UI, MCP personas persist, and consensus weights are inspectable (if not editable). Closing the `enabled_personas` Settings gap (done here) is necessary but not sufficient for a user-built terminal narrative.
