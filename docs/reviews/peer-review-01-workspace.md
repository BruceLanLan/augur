# Peer Review #1 — Terminal Workspace UX

**Reviewer:** Reviewer #1 (Terminal Workspace UX)  
**Scope:** `src/augur/workspace.py`, `dashboard/templates/settings.html`, `dashboard/templates/base.html` (`applyTerminalWorkspace`), plus cross-cutting read of `src/augur/workflow.py`, `src/augur/cli.py` workflow command, `dashboard/templates/index.html`  
**Baseline:** v10.14 shipped; v10.15 WIP (multi-profile workspace, enabled_personas, workflow CLI)

---

## Executive summary

The workspace layer is the strongest v10.15 surface area: multi-profile YAML persistence, sane preset merge semantics, export/import hooks, and a Settings UI that reads like a Bloomberg “layout manager.” The terminal feel breaks down where **profile intent collides with ephemeral browser state**, where **backend fields exist without UI wiring**, and where **home/workflow remain oblivious to the active profile**. Fix the precedence and wiring gaps before adding more presets.

---

## Strengths

### 1. Solid persistence model (`src/augur/workspace.py`)

- **Multi-profile migration** (`_migrate_flat_to_profiles`) preserves legacy flat `workspace.yaml` without breaking existing installs.
- **Preset merge** via `merge_preset_with_custom` / `_normalize_profile_settings` keeps overrides explicit: preset seeds defaults, user fields win, invalid pages fall back to `/`.
- **Thread-safe cache** with `reset_workspace_cache()` gives tests a clean isolation hook.
- **`enabled_personas`** is normalized, persisted, and already plumbed into `DecisionCoordinator.analyze_with_all` via `get_enabled_personas()` in `dashboard/app.py` — the right place for a terminal “agent roster” filter.

### 2. Settings UI matches terminal mental model (`dashboard/templates/settings.html`)

- Named profiles (create / switch / delete) with copy-from-active on create.
- One-click preset buttons that preview fields before save — good Bloomberg pattern (preview ≠ commit).
- Hidden-nav toggles map to `data-page` slugs used in `base.html` nav — consistent selector contract.
- Profile switch clears `sessionStorage.augur-workspace-routed` so landing redirect re-evaluates — thoughtful.

### 3. Global shell application (`dashboard/templates/base.html`)

- `applyTerminalWorkspace()` runs on every page load, hiding nav items, ticker tape, and redirecting `/` → default ticker or default page.
- Hidden nav uses `[data-page="…"]`, which correctly targets **both** sidebar and bottom nav items.

### 4. API surface (`dashboard/app.py`)

- Full CRUD for profiles plus `/api/workspace/presets`, export/import — ready for desk backup/restore workflows.

---

## Gaps

| Gap | Location | Impact |
|-----|----------|--------|
| **Sidebar state fight** | `base.html` DOMContentLoaded restores `localStorage.augur-sidebar` *before* async workspace fetch; expanded profile loses to stale localStorage | Trader profile “sidebar collapsed” silently ignored |
| **`committee_preset` dead field** | Stored in `workspace.py` presets + `WorkspaceBody`; no consumer in committee UI or API | Preset promises “value committee” but UI never applies it |
| **`enabled_personas` no Settings UI** | Backend + analyze endpoints wired; `settings.html` has no toggles | Power feature invisible; users edit YAML or API only |
| **`resolve_landing_url` unused** | Defined in `workspace.py`; landing logic duplicated in JS | Drift risk; no server-side `/` redirect for non-JS clients |
| **Incomplete hidden-nav catalog** | `WORKSPACE_NAV_PAGES` omits `signals`, `watchlist`, `personas`, `settings` | Cannot hide core nav from Settings toggles |
| **Preset apply is preview-only** | `applyWorkspacePreset()` mutates form, requires separate Save | Fine for pros, confusing for retail; no “dirty” indicator |
| **Home ignores workspace** | `index.html` always renders full dashboard + onboarding | Trader/minimal profiles still flash home widgets before redirect |
| **Workflow ignores workspace** | `run_workflow()` / CLI never call `get_enabled_personas()` | CLI “all agents” ≠ dashboard “my desk roster” |

---

## Three actionable improvements (workspace)

### A. Establish profile precedence over browser ephemera

**Problem:** `base.html` lines 318–324 restore sidebar from `localStorage` synchronously; `applyTerminalWorkspace()` applies `sidebar_collapsed` later via fetch but never clears a conflicting localStorage value when profile says expanded.

**Fix:** When workspace loads, **authoritatively apply** `sidebar_collapsed` and sync `localStorage.setItem('augur-sidebar', …)` to match the active profile. Same pattern should eventually cover theme if profiles gain theme fields.

**Acceptance:** Switch to a profile with `sidebar_collapsed: false` after manually collapsing sidebar → sidebar opens on next full page load.

### B. Wire `committee_preset` end-to-end

**Problem:** `LAYOUT_PRESETS["trader"].committee_preset == "value"` and `["committee"].committee_preset == "all"` are stored but never read.

**Fix:** On committee page load (and `/api/committee` if applicable), read active workspace and pre-select persona subset / default question template matching the preset slug. Surface read-only hint in Settings (“Committee preset: value”).

### C. Complete the desk configuration surface in Settings

**Problem:** `enabled_personas` and full nav hide list are backend-complete but UI-incomplete.

**Fix (phased):**
1. Add persona multi-select (reuse persona list from `/api/personas` or registry).
2. Extend `WORKSPACE_NAV_PAGES` to match all hideable `data-page` values in `base.html`.
3. Show active profile name in shell header (e.g. “Profile: day-trading”) — Bloomberg users expect visible context.

---

## Two critiques: workflow & home (with suggested fixes)

### Critique 1 — Workflow CLI is a parallel product, not a terminal function

**Observed in** `src/augur/workflow.py`, `src/augur/cli.py` (`workflow_cmd`):

- `run_workflow()` accepts `--agents` but **never** reads `get_enabled_personas()` from the active workspace profile. A trader who configured a 5-agent desk in Settings still runs 18 agents from `augur workflow AAPL`.
- `format_workflow_summary()` truncates analyze to top 5 agents with no indication that filtering occurred; committee/debate steps recompute consensus independently (committee calls `get_consensus` twice if both steps run).
- No `--profile` flag to load a named workspace profile for agent roster + committee preset context.

**Suggested fix:**

```python
# workflow.py — after parsing agents string
from augur.workspace import get_enabled_personas
if not agents.strip():
    roster = get_enabled_personas()
    if roster:
        selected_ids = roster
```

Add `augur workflow TICKER --profile day-trading` that calls `set_active_profile` (read-only, no persist) or loads profile via `get_profile()`. Document in CLI help that workspace roster applies when `--agents` is omitted.

### Critique 2 — Home dashboard fights the workspace landing contract

**Observed in** `dashboard/templates/index.html`:

- Dense Bloomberg-style board (market pulse, sectors, crypto, commodities, leaderboard) always renders for `/` before `applyTerminalWorkspace()` may redirect — **flash of wrong terminal** for trader/minimal/committee profiles.
- Onboarding banner (`augur-onboard-dismissed` in localStorage) ignores workspace: a committee-first profile still gets the “welcome to home dashboard” funnel.
- Hero quick-analyze always calls `/api/analyze/` with all agents (respects `enabled_personas` server-side) but UI copy hardcodes “18 masters” — contradicts a filtered desk.
- No workspace-aware widget density: minimal preset should not load six deferred API panels on a page the user never intends to see.

**Suggested fix:**

1. **Server-side landing** in `dashboard/app.py` for `GET /`:

```python
from augur.workspace import get_workspace, resolve_landing_url
target = resolve_landing_url(get_workspace(), path="/")
if target:
    return RedirectResponse(target, status_code=302)
```

2. Gate onboarding: skip `#onboard-banner` when `default_page != '/'` or profile preset is not `analyst`.
3. Replace hardcoded “18” with `{{ agent_count }}` or API-driven count reflecting enabled roster.

---

## Fix implemented in this review (Reviewer #1)

**Issue:** Workspace `sidebar_collapsed` loses to stale `localStorage.augur-sidebar` (Gap A above).

**Change:** `dashboard/templates/base.html` — `applyTerminalWorkspace()` now applies expanded/collapsed authoritatively and syncs localStorage to match the active profile.

---

## Test plan (recommended)

- [ ] Profile switch: collapsed ↔ expanded survives hard refresh
- [ ] `default_ticker` + `default_page` precedence on `/` (ticker wins)
- [ ] Hidden nav hides both sidebar and bottom nav for each slug in `WORKSPACE_NAV_PAGES`
- [ ] Workflow CLI with empty `--agents` respects `enabled_personas` (after Critique 1 fix)
- [ ] `GET /` with trader profile returns 302 to `/stocks` without rendering index widgets (after Critique 2 fix)

---

## Verdict

**Ship workspace persistence and profiles** — the data model is production-grade. **Do not ship** without resolving sidebar precedence (fixed here) and either wiring `committee_preset` / persona UI or removing those fields from presets until they work. Workflow and home need explicit integration with the active profile or they undermine the “Bloomberg terminal” story.
