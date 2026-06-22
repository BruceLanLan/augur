# Peer Review #9 — Architecture & Legacy

**Scope:** v10.15 module boundaries, `dashboard/app.py` scale, `scanner/` shim layer, consensus optional imports.  
**Reviewer lens:** What blocks user customization (workspace presets, persona subsets, weight tuning, third-party embedding)?  
**Date:** 2026-06-22

---

## Executive summary

v10.15 draws a clear **primary vs legacy** boundary: Dashboard, MCP, CLI, and `augur.registry` import from `augur.*` only; `scanner/` is documented as a backward-compat shim (`scanner/README.md`). Workspace profiles, `enabled_personas`, and `augur.consensus.*` are real steps toward DIY. Three structural debts still dominate customization friction: a ~4k-line monolithic dashboard, a dual-package import surface (`scanner` + `augur`), and consensus logic split across `registry.get_consensus` with silent optional imports.

---

## Tech debt blocking customization

### 1. Monolithic `dashboard/app.py` (~3,973 lines)

The FastAPI app is a single file owning HTML routes, 50+ REST endpoints, WebSocket streams (analyze, committee, prices), auth middleware, workspace API, optimizer, rules engine, i18n, and cron hooks. Section markers (`# ============ v8: … ============`) show accretion by release, not by domain.

**Why it blocks customization:**

| Concern | Impact |
|---------|--------|
| Layout presets (`augur.workspace`) | Can hide nav pages but cannot swap backend modules (e.g. committee-only deploy without shipping optimizer code paths). |
| Third-party embedding | Hermes/OpenClaw integrators must run or fork the entire app; no `APIRouter` subsets or plugin mount points. |
| Persona / consensus tuning | Settings and workspace APIs live beside unrelated domains; hard to expose a minimal “consensus-only” surface. |
| Testing & CI | Any change risks unrelated regressions; broad `TestClient(app)` fixtures mask boundary failures. |

Workspace v10.15 correctly persists `enabled_personas` and `hidden_nav`, but the **server remains one opaque bundle**—custom profiles change UI visibility, not deployable capability slices.

### 2. `scanner/` duplication and naming collision

`scanner/` contains ~26 thin re-export shims (`from augur.registry import *`, persona one-liners). Primary codepaths are guarded by `tests/test_no_scanner_imports_v10_15.py`, but:

- The **Dashboard route** `/scanner` (market screener) shares a name with the **legacy package** `scanner/`, confusing docs and onboarding.
- External scripts (e.g. `scripts/dayu.py`) still import `scanner.personas.*`.
- One primary-path exception remains: `scanner.ten_x_screener` inside `registry.get_consensus` (optional overlay, silent skip).

Users customizing imports or packaging see **two valid-looking entry points** (`scanner` vs `augur`) with different guarantees. That undermines the v10.15 “augur-only” story and makes PyPI / monorepo layouts ambiguous.

### 3. Consensus optional imports and opaque tuning

Consensus enhancement landed in `src/augur/consensus/` (industry matrix, regime weights, calibrator, meta-model, rolling IC, paths). Good extraction—but **`DecisionCoordinator.get_consensus` in `registry.py` remains the orchestrator** (~300 lines) with:

- Lazy imports of six consensus submodules per call.
- Feedback JSON loaded via `augur.consensus.paths` with warn-and-continue semantics.
- Legacy `scanner.ten_x_screener` try/except overlay.
- Learning-engine and sentiment singletons wired from the same file.

**Why it blocks customization:**

- DIY weight tuning requires knowing which of `feedback/industry_matrix.json`, `weights.json`, `agent_correlation.json`, rolling IC, and learning-engine outputs actually applied—failures are **silent or debug-only**.
- `consensus/__init__.py` eagerly imports the full public surface; importers pay cost even when only `paths` is needed.
- No stable “consensus profile” or workspace hook to select weighting strategy (analyst vs trader preset does not change consensus math).

---

## Module boundaries (v10.15) — assessment

| Layer | Intended boundary | Actual state |
|-------|-------------------|--------------|
| `augur.personas.*` | Agent logic | Clean; YAML custom personas via `persona_loader` |
| `augur.registry` | Registration + coordination | **Registry + consensus engine + learning/sentiment hooks** |
| `augur.consensus.*` | Weighting / calibration | Partially extracted; orchestration still in registry |
| `augur.workspace` | Terminal layout DIY | Solid presets/profiles; no backend capability flags |
| `dashboard/app.py` | HTTP/WS transport | **God module** |
| `scanner/` | Legacy shim only | Documented deprecated; still 26 files + external script usage |

`tests/test_no_scanner_imports_v10_15.py` and `tests/test_enabled_personas_v10_15.py` encode the intended boundary well; architecture docs (`V9_ROADMAP.md`, `scanner/README.md`) match. Implementation lag is in **registry/dashboard size**, not test intent.

---

## Refactor recommendations (3)

### R1 — Split `dashboard/app.py` into domain routers

Extract FastAPI `APIRouter` modules, e.g. `dashboard/routes/pages.py`, `api/analyze.py`, `api/workspace.py`, `ws/committee.py`. Keep `app.py` as factory: middleware, static mounts, router includes.

**Customization unlock:** Deploy subsets (API-only, committee kiosk), register third-party routers, and map workspace presets to `include_router` sets without forking 4k lines.

**Risk:** Low if done mechanically; preserve route paths and OpenAPI tags. Incremental: one domain per PR.

### R2 — Finish `scanner/` deprecation with a single compat entry

After migrating remaining optional hooks (`ten_x_screener` → `augur.consensus.ten_x` or drop), reduce `scanner/` to `scanner/__init__.py` + README deprecation warnings (`DeprecationWarning` on import). Remove per-persona shim files; rely on `from augur.personas import BuffettAgent` pattern.

**Customization unlock:** One import path for PyPI, docs, and agent skills; eliminates dual-package confusion and shrinks repo surface for forks.

**Risk:** Medium for downstream scripts; keep one release with shim re-exports + changelog before file deletion.

### R3 — Extract `ConsensusEngine` from `registry.py`

Move `get_consensus` orchestration to `augur/consensus/engine.py` with an explicit `ConsensusConfig` (enabled stages: industry, regime, calibrator, meta-model, risk, ten-x overlay). Return structured `metadata` listing which stages ran and which feedback files loaded.

**Customization unlock:** Workspace or config can select consensus profiles; users see why weights changed instead of silent skips.

**Risk:** Medium; requires golden tests on consensus outputs. Registry keeps thin delegate: `engine.build(results, ctx, config)`.

---

## Feature critiques (2)

### F1 — `enabled_personas` filters execution, not registration

v10.15 workspace stores `enabled_personas` and `DecisionCoordinator.analyze_with_all` respects the list. **`AgentRegistry` still instantiates all 18+ agents at startup** (plus YAML personas). Custom profiles that disable personas pay full import/instantiation cost; registry listing APIs still expose disabled agents unless callers filter client-side.

For true DIY, registration should be lazy or profile-scoped: load only enabled personas per workspace profile, and document that list endpoints respect the active profile.

### F2 — Workspace presets are UI-only, not capability presets

Presets (`analyst`, `trader`, `committee`, `minimal`) adjust `hidden_nav`, default page, and ticker tape—not consensus depth, data dependencies, or MCP tool exposure. A “committee” user still pulls scanner/optimizer code paths in the same process; a “minimal” trader cannot declare “consensus without meta-model” without editing Python.

Align preset IDs with backend flags (consensus profile, optional modules, rate limits) so layout customization matches analytical behavior.

---

## Cleanup applied in this review (no commit)

Migrated dead `scanner.agent_hyperparams` imports to **`augur.agent_hyperparams`**, reading `feedback/agent_hyperparams.json` via existing `augur.consensus.paths`. Removes two allowlist exceptions from `tests/test_no_scanner_imports_v10_15.py`. Only remaining primary-path scanner import: `scanner.ten_x_screener`.

---

## Suggested follow-up order

1. **R1** (dashboard routers) — unblocks deployment variants fastest.  
2. **R3** (consensus engine) — unblocks transparent tuning.  
3. **R2** (scanner shrink) — after `ten_x` migration and script updates.
