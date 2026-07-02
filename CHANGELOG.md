# Changelog

All notable changes to augur-agents are documented in this file.

## [10.2.0] - 2026-07-02

Fixes a real PyPI packaging gap found during release-readiness verification: `dashboard/` (the entire web dashboard — templates, static assets, i18n, and all route modules) and `skills/` (Hermes/OpenClaw skill profiles) lived at the repo root, outside `src/`, which is the only directory `[tool.setuptools.packages.find]` packages. A local `python -m build` confirmed the built wheel contained zero `dashboard/*` files; `pip install augur-agents` followed by `augur serve` would fail with "Could not import dashboard app" — the dashboard is the flagship feature and this had never been caught because local dev/test runs only worked by incidental cwd-on-sys.path behavior when running from a repo checkout, not through the actual packaging configuration.

### Fixed

- **Moved `dashboard/` and `skills/` into `src/`** (`src/dashboard/`, `src/skills/`) so `packages.find` (and the new `package-data` globs for templates/static/i18n/md/json) actually bundle them into the wheel. No import path changes were needed — `dashboard.app`, `dashboard.routes.*` etc. keep their existing top-level names since both directories are now siblings of `augur/` under `src/`.
- **`src/augur/cli.py`**: `augur serve` and `augur skills` path resolution changed from `parents[2]` (assumed repo-root-relative, only true in a dev checkout) to `parents[1]` (correct for both a dev checkout and a real pip install, since `dashboard`/`skills` now sit alongside `augur/` in both cases).
- **`Dockerfile`**: removed the now-redundant separate `COPY dashboard/` and `COPY skills/` steps (already covered by the existing `COPY src/`).
- **`Makefile`**: `make serve` now calls `augur serve` instead of raw `python -m dashboard.app`, reusing the fixed path-resolution logic instead of duplicating the old repo-root assumption.
- **`scripts/generate_skills.py`**: `skills_dir` updated to `ROOT / "src" / "skills"`.
- **~20 test files** that read template/CSS/JS files directly by filesystem path (not via Python import — a common pattern here for i18n/a11y/content assertions) had `"dashboard"` path components updated to `"src" / "dashboard"`; one file updated similarly for `"skills"`.

### Verified

- Built a real wheel locally (`python -m build`), confirmed `dashboard/` (85 files, including all templates/static/i18n) and `skills/` are present in it.
- Installed that wheel into a throwaway virtualenv and ran `augur serve` end-to-end: server started, `/health` and `/stocks` both returned HTTP 200 — this exact sequence would have failed with an ImportError before this fix.
- Full test suite: 2180 passed, 0 failures, after both the move and the ~20-file test path-reference fix.

### Known residual gap (not fixed here, out of scope for this release)

- `personas/custom/` (user-defined custom persona YAML overrides, loaded by `registry.py`) and `docs/knowledge/personas/` (persona enrichment markdown, loaded by `soul.py`) have the same theoretical repo-root-relative gap, but both already have graceful multi-candidate fallback logic (including a `Path.cwd()`-based lookup) rather than a hard crash — lower severity than the dashboard's hard ImportError, and intentionally left out of this fix's scope.

## [10.1.0] - 2026-07-01

Dashboard router split — `dashboard/app.py` fully decomposed into 17 focused `APIRouter` modules under `dashboard/routes/`. No user-visible behavior changes; 111 HTTP routes and 2136 passing tests preserved throughout.

### Changed

- **`dashboard/app.py`**: Shrunk from ~4338 lines to ~438 lines of pure skeleton (imports, FastAPI instance, 17 `include_router` calls, middleware, exception handlers, static mounts, `main()`). All route logic moved to `dashboard/routes/`.
- **`dashboard/deps.py`**: Expanded to hold all shared singletons and helpers previously living in `app.py` — `get_registry()`, `get_coordinator()`, rate limiting, token bucket, i18n cache/loader, `_save_history_safe`, `_get_rules_engine`, `_APP_START_TIME`. Everything re-exported from `app.py` for backwards-compat (`from dashboard.app import X` still resolves).
- **New route modules** (each is a self-contained `APIRouter`):
  - `dashboard/routes/market.py` (R2): market data widgets — sector performance, sparklines, fear/greed, movers, global markets, search, real-time price
  - `dashboard/routes/history.py` + `auth.py` + `notifications_cron.py` + `config.py` (R3): history CRUD + auth/JWT + notification/cron + system config
  - `dashboard/routes/personas.py` (R4): persona CRUD + enrichment, `PERSONA_ENRICHMENT` dict, `_persona_meta()` helper
  - `dashboard/routes/analysis.py` (R5): stock analysis — scanner, `analyze_ticker`, signals, deep report, Leaderboard IC
  - `dashboard/routes/watchlist.py` (R6): watchlist GET/add/remove/batch-run
  - `dashboard/routes/backtest.py` (R7): backtest run + IC leaderboard + `/backtest` HTML page
  - `dashboard/routes/misc.py` (R8): health, robots.txt, PWA manifest, sitemap, cache clear/info
  - `dashboard/routes/committee.py` (R9): committee/compare/debate API + their HTML pages; `_save_history_safe` and i18n helpers moved to `deps.py`
  - `dashboard/routes/ws.py` (R10): all four WebSocket handlers — `/ws/analyze`, `/ws/committee`, `/ws/prices`, `/ws/workflow`
  - `dashboard/routes/chat.py` (R11): sentiment API + chat engine + `/chat` HTML page
  - `dashboard/routes/rules.py` (R12): rules engine CRUD
  - `dashboard/routes/optimizer.py` (R13): portfolio optimizer + i18n JSON API + lang cookie
  - `dashboard/routes/pages.py` (R14): all 10 browser-facing HTML pages (`/`, `/personas`, `/stocks`, `/signals`, `/scanner`, `/watchlist`, `/portfolio`, `/settings`, `/create-persona`, `/report/{ticker}`)
- **Patch-at-point-of-use** invariant applied throughout: test patch targets updated from `dashboard.app.*` to the new module where each handler now lives.

### Test status

- 2136 passed, 0 failures.

## [10.0.0] - 2026-06-29

Public release of Augur v10. Version consolidated from v10.16.13 (internal dev series) to v10.0.0 for the public `augur` repository release. All capabilities from v10.16.13 are included; see README.md changelog for user-facing feature summary.

### Summary of changes since v8.2.3

- Terminal Workspace (Bloomberg-style layout presets, multi-profile save/switch, enabled-persona subset, committee preset binding, workspace import/export)
- 13 MCP tools including 3 new workspace read/write/profiles tools
- `augur_workflow` multi-step pipeline with per-step failure isolation and preset-linked default steps
- WebSocket streaming: `/ws/workspace` state push, `/ws/workflow` step-by-step progress
- Consensus engine upgrade: industry-matrix weights, regime routing (hysteresis + confirmation), probability calibration, rolling IC, MetaModel blending, point-in-time fundamentals
- 19 Hermes Skills + augur-terminal meta-skill
- 4-language i18n, History heatmap, PWA install, Optimizer efficient frontier, keyboard shortcuts
- 2136 tests passing

### Test status

- 2136 passed, 0 failures.

## [10.16.13] - 2026-06-26

P1-9: Dashboard router split — workspace routes extracted to `dashboard/routes/workspace.py`.

### Changed

- **`dashboard/routes/workspace.py`** (new): All `/api/workspace*` REST endpoints (11 routes), `/ws/workspace` WebSocket, `_ws_workspace_clients` broadcast state, `_broadcast_workspace_change()`, and `WorkspaceBody`/`WorkspaceProfileBody`/`WorkspaceActiveBody` models moved here as an `APIRouter`. `authenticate_websocket` called directly instead of going through the `_ws_api_token_ok` wrapper.
- **`dashboard/routes/__init__.py`** (new): Package marker for the routes sub-package.
- **`dashboard/app.py`**: Shrunk from 4338 → 4133 lines (−205). Mounts workspace router via `app.include_router(_workspace_router)`. Trimmed `from augur.workspace import (...)` to only the 3 symbols used outside workspace routes: `get_workspace`, `get_enabled_personas`, `resolve_landing_url`.

### Test status

- 2136 passed, 0 failures. All existing workspace and WebSocket tests pass without modification.

## [10.16.12] - 2026-06-26

P2-5 + P2-8: Workspace streaming, workflow progress WebSocket, augur-terminal meta-skill, and Hermes committee agent.

### Added

- **`/ws/workspace`** (P2-5): New WebSocket endpoint. Clients receive the current workspace state immediately on connect (`{"type": "workspace_state", "workspace": {...}}`), then receive live push messages (`{"type": "workspace_update", "workspace": {...}}`) whenever `PUT /api/workspace` or `PUT /api/workspace/active` commits a change. Uses an async broadcast fan-out (`_ws_workspace_clients: Set[WebSocket]`) via `asyncio.create_task()`.
- **`/ws/workflow`** (P2-5): New WebSocket endpoint for step-by-step workflow progress streaming. Client sends `{"ticker": "X", "steps": "fetch,analyze,consensus", "agents": ""}`. Server emits `{"type": "step_start", "step": "fetch", "step_index": 0, "total": 3}` and `{"type": "step_done", "step": "fetch", "result": {...}, "elapsed_ms": N}` for each step, finishing with `{"type": "done", "results": {...}, "step_status": {...}}`. Avoids event-loop blocking by running each step via `run_in_threadpool`.
- **`skills/augur-terminal/`** (P2-8): New meta-skill covering the full Augur Bloomberg-style terminal. Documents all 13 MCP tools, all 15 dashboard pages, workspace profiles and presets, and a standard workflow. Integrated into `scripts/generate_skills.py` (`terminal_skill()` + `generate_terminal_manifest()`).
- **`hermes-agents/committee.yaml`** (P2-8): New Hermes agent config for the Committee Chair role. Counterpart to the 18 persona YAMLs; uses `mcp_augur_committee`/`workflow`/`workspace_get` and a neutral facilitator system prompt.

### Changed

- `dashboard/app.py`: added `import asyncio` and `Set` to typing imports; `api_put_workspace` and `api_set_active_workspace_profile` now fire a background broadcast task after writing.
- `scripts/generate_skills.py`: extended to generate `augur-terminal` skill (SKILL.md + manifest.json) alongside the 18 persona skills and committee skill.

### Test status

- New: 6 tests in `tests/test_websocket.py` (`TestWorkspaceWebSocket` × 2, `TestWorkflowWebSocket` × 4). All 26 WebSocket tests pass.

## [10.16.11] - 2026-06-26

P2-1 + P2-6: ConsensusEngine extraction and lazy persona registration per profile.

### Changed

- **P2-1**: Extracted the full 338-line consensus logic from `DecisionCoordinator.get_consensus` into a new standalone class `ConsensusEngine` in `src/augur/consensus/engine.py`. `DecisionCoordinator.get_consensus` is now a 7-line delegation shim. All external call sites are unchanged. `_normalize_coverage_confidence` moved to `ConsensusEngine` as a `@staticmethod`. Lazy imports inside `ConsensusEngine.compute()` prevent circular dependencies at module load time.
- **P2-6**: `AgentRegistry._register_default_agents` now reads the active profile's `enabled_personas` list via `get_enabled_personas()` (lazy import). When non-empty, only the listed agents are imported and instantiated; when empty (the default), all 18 built-ins are loaded as before. The manifest is a new module-level `_BUILTIN_AGENTS` dict mapping `agent_id → (module_path, class_name)` for `importlib.import_module` dispatch. YAML personas are always loaded unconditionally (additive). A workspace import error silently falls back to loading all 18 agents.

### Fixed

- `tests/test_no_scanner_imports_v10_15.py`: added `src/augur/consensus/engine.py` to the `ALLOWED_SCANNER_IMPORTS` allowlist (engine.py has the same `scanner.ten_x_screener` optional try/except that `registry.py` already had).
- `hermes-agents/*.yaml`: bumped all 18 files from `10.16.9` to `10.16.10` (pre-existing drift — `generate_skills.py` only regenerates `SKILL.md`/`manifest.json`, not `hermes-agents/` YAMLs).

### Test status

- New P2-6 tests: `TestLazyPersonaRegistration` in `tests/test_registry.py` — 4 tests covering default all-load, filtered subset, unknown-ID skip, and workspace-error fallback.
- Full suite: **2109 passed, 21 pre-existing failures** (all in `test_pit_fundamentals.py`, `test_regime_v2.py`, `test_v10_14_workspace_workflow.py` — confirmed pre-existing via `git stash` baseline check before P2-6 changes).

## [10.16.9] - 2026-06-25

P2-4: the second (and final) half of the regime-weighting gate opened by P2-3 — does the hand-picked `_REGIME_ADJUSTMENTS` table in `src/augur/consensus/regime_weights.py` actually improve out-of-sample prediction quality, vs. a flat equal-weight consensus? Before this release, `Backtester.run_live_backtest` never populated real fundamentals during historical replay (pe/pb/roe stayed at the `MarketContext` dataclass default of 0 for every day), so any prior attempt at this validation would have been null by construction — reweighting a constant-zero value-agent score cannot move a rank-IC regardless of the multiplier. **This release adds the missing point-in-time fundamentals plumbing, a cross-sectional regime-bucketed IC harness, and runs the validation for real. The result: across 37 tickers and ~4.4 years, the regime-weighted consensus shows no clear, consistent improvement over flat weighting — deltas are tiny and mixed-sign in every regime bucket. Do not treat this gate as cleared in the sense of "the multipliers are confirmed to help"; treat it as cleared in the sense of "the multipliers were finally tested against real data, honestly, and the result is a wash."**

### Added
- `src/augur/consensus/pit_fundamentals.py` (`fetch_pit_fundamentals`): point-in-time fundamentals provider for backtest replay. Fetches yfinance's annual `financials`/`balance_sheet` once per ticker per process, applies a conservative 90-calendar-day filing-lag guard (a fiscal-year-end statement is not treated as "available" the day the fiscal year ends — only `period_end + 90 days` and later), and returns `{"insufficient": True}` (never zero-filled) when no period is as-of available for a given day. Wired into `Backtester.run_live_backtest`, which now drops (rather than zero-fills) any historical day lacking real point-in-time fundamentals.
- `src/augur/backtest.py`: `build_date_to_regime`, `fetch_ticker_replay_records`, `_signed_agent_scores`, `compute_cross_sectional_regime_ic` — a pure offline cross-sectional aggregator. Per day, ranks tickers' consensus scores (flat equal-weight vs. `apply_regime_weights`-based regime-weighted) against realized 20-day forward return, buckets per-day Spearman ICs by regime, and reports per-regime mean IC/delta/day-count, a per-agent-by-regime diagnostic, and a block-bootstrap CI for the BEAR_HIGH_VOL bucket specifically. Deliberately uses `apply_regime_weights(weights, regime)` rather than `RegimeRouter().get_weights(regime)`, since the latter silently zeroes every agent not named in `_REGIME_ADJUSTMENTS[regime]`.
- `scripts/regime_weight_oos.py`: manual (non-CI, makes live network calls) real-network OOS validation script. 37-ticker cross-sector universe (tech, financials, energy, staples, healthcare, industrials), 2022-01 through 2026-06. Prints per-regime IC deltas, the per-agent-by-regime diagnostic table, the BEAR_HIGH_VOL bootstrap CI, and explicit honest caveats about coverage and statistical power — deliberately emits no hardcoded pass/fail verdict.
- `tests/test_pit_fundamentals.py`: 16 offline, deterministic tests against synthetic/mocked `financials`/`balance_sheet` DataFrames (no network) — the 90-day look-ahead guard and its exact boundary, pe/pb/roe/margin arithmetic, YoY growth across two as-of-available periods, the `insufficient`-not-zero-filled path, and the two bugs below.

### Fixed
- **A NaN-padded "oldest retained" annual statement column could silently produce a successful-looking all-zero fundamentals result instead of the correct `insufficient` flag.** yfinance pads its oldest retained annual column with `NaN` once that period ages out of full retention. `_available_periods` originally treated any column whose label passed the 90-day date guard as "available," regardless of whether the column actually contained real values — so for an early date where only that NaN-padded column qualified, every field (`pe`, `pb`, `roe`, ...) silently fell through to its `0.0` default and the function returned a *non-insufficient* all-zero result. This is the exact null-by-construction failure mode the module exists to prevent: a value agent fed an all-zero `MarketContext` emits a constant neutral score, indistinguishable from "this company genuinely has zero fundamentals." Found via an anomalous all-zero `delta_mean` across every single regime bucket in an early smoke test of the Task 4 harness. Fixed by requiring at least one core row (Net Income / Total Revenue) to be a real, non-NaN value for a period column before treating it as "available" (`_period_has_real_data`).
- **`pit_fundamentals._get_statements` permanently cached whatever yfinance returned on the very first call, including a transiently-empty bad response.** Direct empirical testing confirmed yfinance's `.financials` property is itself nondeterministic for at least one ticker/environment combination observed during this work: three fresh-process calls for the same ticker returned valid 5-column annual data twice and a fully empty DataFrame once. Since the per-ticker statement cache is permanent for the life of a process, an unlucky first fetch within a long-running, multi-ticker OOS script would have silently and incorrectly poisoned that ticker as "no fundamentals" for the entire run. Fixed by retrying up to 3 times before accepting and caching an empty result as genuine.

### Out of scope / honest caveats
- **BEAR_HIGH_VOL coverage is thin and clustered, not a general statistical sample.** Regime is a market-wide label (one VIX+SPY classification per day), not per-ticker — a wider ticker universe adds cross-sectional breadth within a day, it does not create more BEAR_HIGH_VOL days. Across the 37-ticker, 2022-01..2026-06 universe, only 9 days had >=5 tickers carrying real point-in-time fundamentals on a BEAR_HIGH_VOL day, clustered into two short market episodes (2024-08-07..09, the yen-carry-unwind selloff; 2025-04-07..14, the tariff-shock selloff). Calendar-year 2022 itself contributes ~zero usable BEAR_HIGH_VOL days for most December-fiscal-year-end tickers, since FY2022 filings are not as-of-available (90-day guard) until roughly late March 2023. The BEAR_HIGH_VOL bootstrap CI is therefore a mechanical computation over ~2 autocorrelated episodes, not an independent-sample estimate, and the script labels it as such — a CI excluding zero on n=9 clustered days is directional evidence about those two specific weeks, not a general statistical claim.
- **No pass/fail verdict is emitted by design.** The headline finding — small, mixed-sign deltas across SIDEWAYS, BULL_LOW_VOL, BEAR_LOW_VOL, BULL_HIGH_VOL, and BEAR_HIGH_VOL — is "no clear OOS improvement from `_REGIME_ADJUSTMENTS`," not "the multipliers are validated" and not "the multipliers are wrong." Whether to keep, retune, or remove the multipliers given this result is a product decision, deliberately left to the user rather than baked into this release.

### Test status
- New: `tests/test_pit_fundamentals.py`, 16/16 passed (offline, no network).
- Full suite: **2104 passed before this work, 2120 passed after** (2104 + 16 new, 0 failures, 0 regressions). The pre-existing 2108 figure cited in `docs/AGENT_PEER_REVIEW_SYNTHESIS.md` and the v10.16.8 changelog entry could not be exactly reconciled against this session's clean 2104 baseline (`--collect-only` independently confirmed 2104 collected with no silent skips) — suspected date/network-gated test wobble across the 06-24 -> 06-25 date rollover, not a regression from this release.
- Caught (via the pre-existing `test_all_hermes_yaml_match_live_version` test) and fixed a version-bump gap: `scripts/generate_skills.py` regenerates `skills/*/manifest.json` and `SKILL.md` but does **not** cover `hermes-agents/*.yaml` — those 18 files needed a separate manual version-string update. Future version bumps should account for this until a generator covers `hermes-agents/` too.

## [10.16.8] - 2026-06-25

P2-3 (narrow scope): regime detector v2 — hysteresis + point-in-time macro features. This was the one open "foundational architectural risk" named in `docs/AGENT_PEER_REVIEW_SYNTHESIS.md` ("do not treat consensus outputs as risk inputs until P2-3 regime validation lands"). That gate has two independent halves — (1) regime classification flip-flopping noisily, and (2) the hand-picked `_REGIME_ADJUSTMENTS` multipliers never having been validated to actually improve outcomes. **This release resolves only half (1).** Half (2) is explicitly out of scope (tracked as P2-4, the unified OOS calibration pipeline) — do not read this release as "the architectural risk is resolved."

### Fixed
- **Regime classification had no hysteresis and could flip on a single noisy day**: `macro_features._macro_from_market` classified VIX/SPY into a regime bucket from a single live snapshot each call (hard `VIX >= 25` cutoff, no smoothing), so VIX oscillating around the boundary — or a single-day spike — could flip the regime, which `weighting.build_consensus_weights` blends 35% into the persona weights feeding investment consensus. Added a pure `classify_regime(vix_series, spy_series, end_idx, ...)` core that (a) uses an asymmetric Schmitt-trigger VIX band (enter high-vol at 25, exit at 23, instead of one hard cutoff) and (b) requires a new raw regime to persist for `confirm_days=3` consecutive trading days before it is "accepted" (a forward min-dwell scan). Both the live path and the historical backtest below call this same function, so live and backtest behavior are identical by construction, not by claim.
- **`date_str` was accepted by `fetch_macro_features`/`detect_regime` but silently ignored — there was no actual historical/point-in-time capability**: `_macro_from_market` always fetched "now" data (`period="5d"`/`"1mo"`) regardless of what `date_str` was passed, so the parameter was decorative. Rewrote it to fetch a trailing ~95-calendar-day window ending at `date_str` (or now, if `None`) via `start`/`end`, verified to have no look-ahead (yfinance's `end` is exclusive — confirmed empirically before implementing). Along the way found and fixed a real bug this exposed: `^VIX` and `SPY` history come back tz-localized to different exchange timezones (`America/Chicago` vs `America/New_York`), so the same trading day has different absolute timestamps in each index and a naive `index.intersection()` silently returned zero overlapping days. Normalized both to tz-naive calendar dates before aligning.
- **Macro cache could be polluted by historical lookups**: the previous single-slot `_CACHE` had no key, so once `date_str` started doing real historical fetches, a backtest call with a past date would have overwritten the live snapshot's cache slot. Live (`date_str=None`) snapshots are still cached for 5 minutes; historical lookups are never cached at all (a historical snapshot never goes stale, so caching it only grows memory for no benefit).

### Added
- `tests/test_regime_v2.py`: 8 offline, deterministic tests against synthetic VIX/SPY series (no network) — single-day VIX spikes don't flip the accepted regime, a persistent 3-day change is accepted, oscillation between two non-accepted states never flips, future data appended after `end_idx` cannot affect a historical classification, cache-keying behavior, and the existing `AUGUR_SKIP_MACRO_FETCH=1` / yfinance-unavailable fallback paths still work.
- `scripts/regime_backtest_v2.py`: manual (non-CI, makes live network calls) historical validation harness. Pulls ~9 years of `^VIX`/`SPY` history once, then runs the old hard-cutoff classifier and the new hysteresis classifier (mirroring the live path's exact trailing-window size) over every day. Measured results from one run (2015-01-02 .. 2026-06-23, 2884 aligned trading days): flip count 389 (old) -> 101 (new); whipsaw count (A->B->A within <=3 days) 146 (old) -> 10 (new). Responsiveness check against three known crash windows: new entered high-vol-bear within 2-4 days of old during the 2020 COVID crash and 2022 bear market. The 2018 Q4 window showed old firing once on 2018-10-24 — verified by hand to be a single noisy bear+VIX>=25 day inside an otherwise choppy, non-persistent stretch (one of the 146 old whipsaws) — while new's 2018-12-20 entry lines up with 3 consecutive bear+VIX>=25 days during the real December 2018 selloff; i.e. the gap there is the hysteresis correctly declining to fire on noise, not a responsiveness failure. Also verified window-length independence (the finite-window dwell scan's initial SIDEWAYS seed washes out): SIDEWAYS is also the seed state, so a SIDEWAYS-only sample can't distinguish "seed washed out" from "seed never challenged" — sampled 12 dates restricted to non-SIDEWAYS regimes (spanning all four other regime types) and confirmed the accepted regime is identical whether the trailing lookback is 65, 130, or 260 trading days.

### Out of scope (tracked separately)
- Whether the hand-picked `_REGIME_ADJUSTMENTS` multipliers themselves improve investment outcomes out-of-sample, vs. a flat-weight baseline — this requires a persona-replay harness and is P2-4's job, not P2-3's. Doing it now would also risk circularity (validating multipliers against the same intuition/period that produced them).

### Test status
- Full suite: **2108 passed** (2100 baseline + 8 new), 0 failures.

## [10.16.7] - 2026-06-25

Continued the live-testing sweep for "data isn't showing up in a lot of places" beyond the homepage and committee/report areas already covered in v10.16.5/v10.16.6 — this time across the rest of the dashboard (history, optimizer, portfolio, watchlist, scanner, signals, settings, chat). Found and fixed two concrete bugs (plus a follow-up display-consistency fix caught while verifying the second one), all real "missing/wrong data" defects rather than the async/event-loop class fixed previously.

### Fixed
- **`/history` page's 52-week calendar heatmap silently never rendered**: `loadCalendarData()` and `loadHistoryForDate()` in `dashboard/templates/history.html` called `/api/history?page=1&per_page=365`, but the `/api/history` paginated mode caps `per_page` at 100 and returns HTTP 400 above that — the frontend's `.catch(function(){})` swallowed the error with no visible message, so the calendar card just never appeared. Switched both calls to the endpoint's unpaginated `limit` mode (`/api/history?limit=365`, capped at 500), which the endpoint already supports and which exactly fits the calendar's need for a flat list of recent records; updated the response field from `data.items` to `data.records` to match that mode's shape.
- **Portfolio optimizer (`/optimizer`, `/api/optimize`) computed Sharpe ratio — and the optimal weights themselves — with mismatched units**: `PortfolioOptimizer.optimize()` and `.efficient_frontier()` in `src/augur/optimizer.py` work with *daily* returns (3 months of daily closes), but received `risk_free_rate` as an *annual* rate (e.g. 0.02 for 2%) and subtracted it directly from daily mean returns before dividing by daily volatility — both in the displayed `sharpe_ratio` and, more importantly, in the analytical max-Sharpe weight solution itself (`excess = mean_rets[i] - risk_free_rate`). Since a typical daily mean return (~0.001-0.003) is tiny next to an annual rate (0.02), this made `excess` strongly negative for every asset, skewing the "optimal" weights away from anything resembling a real max-Sharpe portfolio, and produced absurd displayed Sharpe ratios (observed: -1.44 for a portfolio with ~43% annualized return and ~20% annualized volatility, where the correct value is ~+0.18 daily / ~+2.0 annualized-equivalent). Fixed by converting `risk_free_rate` to a daily rate (`risk_free_rate / 252`) before combining it with daily returns/volatility anywhere in `optimize()` and `efficient_frontier()`.
- **`/optimizer` page displayed an annualized return/volatility next to a daily-basis Sharpe ratio**: `/api/optimize` in `dashboard/app.py` already added `expected_return_annual`/`volatility_annual` fields to the response "for display consistency" (per the existing code comment), but never added an annualized Sharpe to match — so `opt-sharpe` rendered the raw daily `sharpe_ratio` next to the two annualized figures, putting all three numbers on inconsistent time bases (e.g. a correct ~0.20 daily Sharpe sitting next to ~72%/~22% annualized return/vol, which still looks just as wrong as the original bug to anyone eyeballing it). Fixed by adding a `sharpe_ratio_annual` field (`sharpe_ratio * sqrt(252)`) alongside the other two `_annual` fields in `dashboard/app.py`, and updating `dashboard/templates/optimizer.html` to prefer it (falling back to a client-side `* sqrt(252)` if absent, matching the existing fallback pattern for the other two fields). The raw `sharpe_ratio` field is untouched (still daily-basis; existing tests unaffected).

### Test status
- Full suite: **2100 passed**, 0 failures (re-run after all three fixes, including the 5 network-dependent tests).
- `tests/test_optimizer.py` pre-existing tests only assert finiteness/type of `sharpe_ratio`, not its exact value, so none needed updating for the corrected numbers.

### Notes
- Found via a direct API sweep (not a structural code audit) of the remaining dashboard pages not yet covered by v10.16.5/v10.16.6: mapped every `fetch(`/`fetchWithTimeout(` call in each page's template to its backend endpoint, then exercised each endpoint against the live dev server with real tickers, looking for error responses, mismatched response shapes, or numerically implausible results. Most endpoints checked out fine; these two were the genuine defects found.
- Did not touch the already-documented GIL convoy-effect limitation in v10.16.6 (committee/deep-report concurrency) — that remains parked per explicit user decision.

## [10.16.6] - 2026-06-24

Found and fixed the same `async def` + blocking-I/O pattern as v10.16.5 in the investment-committee / deep-report code path — the area named directly in the original live-testing report (v10.16.4 only fixed a Kelly-percentage display bug there, not the freezing). **This significantly reduces, but does not fully eliminate, the freeze** — see "Known limitation" below; live concurrency testing after the fix found a second, deeper bottleneck (Python's GIL) that the same fix pattern does not solve.

### Fixed
- **Same `async def` + zero-`await` pattern, found in 8 more handlers**: `analyze_ticker` (`/api/analyze/{ticker}`), `report_ticker` (`/api/report/{ticker}` — the Deep Report endpoint), `api_committee` (`/api/committee`), `api_compare` (`/api/compare`), `api_debate` (`/api/debate`), `compare_personas` (`/api/persona/compare`), `get_persona_opinion` (`/api/persona/{agent_id}/opinion`), and `api_run_watchlist_analysis` (`/api/watchlist/run`) all called `fetch_market_context()` (synchronous yfinance I/O) and/or ran all 18 personas' `analyze()` synchronously, with zero `await` anywhere in their bodies. Converted all 8 to plain `def` so FastAPI/Starlette dispatches them to its worker threadpool instead of running them inline on the event loop.
- **`analyze_ticker`'s fire-and-forget rule dispatch relied on `asyncio.get_event_loop().run_in_executor(...)`**, which only works reliably from the main thread holding a running loop. Now that the handler runs in FastAPI's worker threadpool, that call would silently raise (swallowed by an existing broad `except Exception`), breaking notification dispatch. Replaced with a plain daemon `threading.Thread(...).start()`, which preserves the original fire-and-forget intent without depending on an event loop being present.
- **`ws_analyze` (`/ws/analyze/{ticker}`) and `ws_committee` (`/ws/committee`) cannot be converted to sync `def`** — Starlette requires WebSocket routes to stay `async def`. Instead, wrapped their `fetch_market_context()` calls in `await run_in_threadpool(fetch_market_context, ticker)`, so the blocking yfinance fetch no longer ties up the event loop while a committee/analyze WebSocket session is open. The per-agent `analyze()` loop was left as-is (CPU-only, no I/O, needed in the main coroutine to stream incremental progress over the socket).

### Added
- `tests/test_market_endpoints.py::TestBlockingHandlersAreSync`: extended the existing regression guard with the 8 newly-converted handler names (19 parametrized cases total, up from 11).

### Known limitation (not fixed by this release)
- Live concurrency testing after the `async def` → `def` conversion found that the fix removes the *guaranteed, total* event-loop freeze, but **does not eliminate severe slowdowns for other concurrent requests while a committee session or deep report is generating**. Confirmed empirically: while `/api/committee` (all 18 personas) ran, a concurrently-issued, normally-instant request (`/api/fear-greed`, baseline ~10-20ms) took 3.2-3.6s to return — sometimes longer than the committee request's own duration. Isolated five concurrent fast requests with no committee running at all: max latency 21ms, confirming the threadpool dispatch itself is not the bottleneck.
- Root cause is different from v10.16.5's: persona `analyze()` across 18 personas is CPU-bound, not I/O-bound. Moving CPU-bound work into a worker thread does not achieve real parallelism in CPython — only one thread can hold the GIL and execute bytecode at a time. A thread doing sustained CPU work can starve other threads' requests, a well-known CPython behavior sometimes called the GIL "convoy effect." Fixing this would require either reducing the analysis's own CPU time (profiling/optimizing `analyze()`), or moving it off-thread entirely (e.g. `ProcessPoolExecutor`, or multiple uvicorn worker processes) — both larger changes deferred pending user input, since the latter requires solving cross-process sharing for the in-memory registry/coordinator singletons, caches, and rate-limit counters.
- Net effect of this release: committee/deep-report generation no longer makes the *entire* dashboard server completely unresponsive for the full duration (the original bug); other users/pages will still see multi-second delays during that window.

### Notes
- Found via a follow-up sweep of every `async def` handler in `dashboard/app.py` that calls `fetch_market_context` or runs persona analysis directly, prompted by an advisor review flagging that the v10.16.5 fix only covered GET-style homepage widgets and hadn't checked the POST/WebSocket committee and analyze/report endpoints for the same pattern — which is exactly the code path behind the user's original "投委会" and "Deep Report" complaints. The GIL contention limitation above was itself found by the same kind of live concurrency test that verified v10.16.5, rather than relying on the structural "is it `async def`" test alone.
- Full suite: 2095 passed (excluding 5 network-dependent tests in `test_analyze_api_v12.py`; 2100 with them included), 0 failures.

## [10.16.5] - 2026-06-24

Root-caused and fixed the other two bugs from the same live user testing session: "homepage dashboard widgets won't respond to clicks" and "data not showing up in many places."

### Fixed
- **Event loop blocked by synchronous yfinance calls**: 11 handlers in `dashboard/app.py` (`api_sector_performance`, `api_crypto_overview`, `api_commodities`, `api_treasury_rates`, `api_hot_tickers`, `api_fetch_ticker`, `api_search_tickers`, `api_sparkline`, `api_market_overview`, `api_market_movers`, `api_fear_greed`) were declared `async def` but performed blocking synchronous yfinance/augur.data I/O (several additionally blocked on `future.result(timeout=...)` from a `ThreadPoolExecutor`, which is itself a blocking call). On the single-process uvicorn server (`workers=` is never passed to any of the three `uvicorn.run()` call sites), a blocking call inside any one `async def` handler freezes the entire event loop for every concurrent request being served — including AJAX calls triggered by clicks elsewhere on the page. This is a unified root cause for both "unclickable dashboard" and "missing data" reports: widgets relying on these endpoints stayed stuck on loading skeletons, and while one was mid-fetch, every other in-flight request (including user-triggered ones, and other homepage widgets like sparklines) stalled along with it. Fixed by changing all 11 handlers from `async def` to plain `def`; FastAPI/Starlette automatically dispatches sync path operations to its threadpool, so they no longer run on the event loop thread.
- **`api_sector_performance()` had zero timeout/parallelism protection**: unlike most of the others (which already used `ThreadPoolExecutor` + a 10s per-symbol timeout, or hit a TTL cache), it fetched 11 sector ETFs sequentially with no timeout and no fallback — measured at 9.8s–15s+ per request in isolation (one run timed out completely at the 15s test ceiling). Refactored to the same bounded `ThreadPoolExecutor(max_workers=11)` + `future.result(timeout=10)` pattern, so a single slow/hanging symbol degrades to a 0 entry instead of stalling the whole response.

### Added
- `tests/test_market_endpoints.py::TestBlockingHandlersAreSync`: structural regression test asserting all 11 handlers above are sync `def`, not `async def`, via `inspect.iscoroutinefunction`. Verified it fails when `async def` is reintroduced (manually reverted one handler, confirmed the test catches it, restored).
- `tests/test_market_endpoints.py::TestApiSectorPerformance/TestApiCryptoOverview/TestApiCommodities/TestApiTreasuryRates`: closed a pre-existing coverage gap — these four endpoints had zero test coverage before this fix, which is part of why the bug shipped unnoticed.

### Notes
- Root-caused via real headless-browser testing (Playwright + Chromium, newly installed this session — no browser automation tool was available in the prior session). Used a real browser to load the homepage against an isolated `HOME`-overridden test instance (mirroring the user's actual `daytrade`/`committee` profile config, never touching the real `~/.augur`), confirming 20+ stuck loading-skeleton elements and tracing unresolved `/api/*` requests.
- Confirmed the event-loop-blocking mechanism (not just inferred it) by firing a slow request (`/api/sector-performance`) and a normally-instant one (`/api/sparkline/AAPL`, baseline ~0.003s) concurrently: before the fix, both finished in lockstep at ~12.3s each; after the fix, the fast one returned in ~0.003s–2.5s while the slow one was still in flight at 1.5s–3.6s — fully decoupled.
- Initial pass only converted the 5 worst-offending widget endpoints; a follow-up review caught that `api_sparkline` (fired up to 10x concurrently on the homepage for per-ticker mini-charts), `api_market_overview`, and `api_market_movers` had the identical pattern and were still `async def`, as were the lower-traffic `api_fetch_ticker`, `api_search_tickers`, and `api_fear_greed`. All 6 were folded into this fix so the regression guard covers the whole class of blocking handlers, not a subset.
- Full suite: 2087 passed (excluding 5 network-dependent tests in `test_analyze_api_v12.py`; 2092 with them included), 0 failures.

## [10.16.4] - 2026-06-24

Bug found and fixed during live user testing of the dashboard: the investment committee's suggested position size was displaying as e.g. "1990.0%" instead of "19.9%".

### Fixed
- **`dashboard/app.py`** `api_committee()` (`POST /api/committee`) and `ws_committee()` (`/ws/committee`): both read `consensus.metadata["position_sizing"]["position_pct"]` — which is already a percentage value (e.g. `19.9` meaning 19.9%, computed in `src/augur/registry.py`'s half-Kelly sizing as `round(full_kelly * 0.5 * 100, 1)`) — and then multiplied it by 100 again before putting it in the `kelly_pct` field of the response. The committee page's `committee.html` renders this value directly as `v.kelly_pct.toFixed(1) + '%'`, so users saw nonsensical numbers like 1990.0% instead of 19.9%. Other call sites (`workflow.py`, `cli.py`, `mcp_server.py`, `report.py`) already used the value directly without the extra multiplication, so this was specific to the two dashboard committee endpoints.

### Added
- `tests/test_websocket.py::TestCommitteeWebSocket::test_committee_ws_kelly_pct_matches_position_sizing` and `test_committee_post_kelly_pct_matches_position_sizing`: assert `kelly_pct <= 20.0` (the half-Kelly cap) on both the WebSocket and REST committee paths, to catch any future re-introduction of the double-scaling.

### Notes
- Found via manual live-testing reproduction (curl + a `websockets` Python client against an isolated `HOME`-overridden test instance, not the developer's real `~/.augur` state) after the user reported committee-page and deep-report bugs while testing the app. Investigated but did not reproduce the user's other two reports ("homepage dashboard widgets not clickable", "missing data in many places") — no browser automation tool is available in this environment, and static JS/CSS analysis plus backend API checks (report/committee/workspace/home-widgets endpoints) did not turn up a root cause. Awaiting browser console output / screenshots from the user to investigate further.
- Full suite: 2072 passed (excluding 5 network-dependent tests in `test_analyze_api_v12.py`; 2077 with them included), 0 failures.

## [10.16.3] - 2026-06-24

落地 Agent Peer Review backlog 中的 P2-7：`augur_workflow` 默认步骤跟随终端布局预设，把"定制化"和"agentic"两条主线在执行层打通。

### Added
- **`workspace.LAYOUT_PRESETS[*]["workflow_steps"]`**：四个布局预设各自带一个默认 workflow 步骤组合——`analyst`=`fetch,analyze,consensus`，`trader`/`minimal`=`fetch,consensus`，`committee`=`fetch,analyze,consensus,committee`。
- **`workspace.get_default_workflow_steps()`**：读取当前激活 Profile 的 `layout_preset`，返回对应的默认步骤字符串；无法解析时回退到 `fetch,analyze,consensus`。
- `list_presets()` / `GET /api/workspace/presets` 响应体新增 `workflow_steps` 字段。
- 新增 4 个测试：`parse_steps("")` 跟随 trader 预设、`run_workflow(steps="")` 跟随 committee 预设、`get_default_workflow_steps()` 的预设切换、`list_presets()` 的 `workflow_steps` 字段断言。

### Changed
- `workflow.parse_steps()`：空/留空的 `steps` 不再直接回退到模块级常量 `DEFAULT_STEPS`，而是先查 `workspace.get_default_workflow_steps()`（拿不到工作区时才退回 `DEFAULT_STEPS`）。
- `workflow.run_workflow()` 的 `steps` 参数默认值从硬编码 `"fetch,analyze,consensus"` 改为 `""`（空字符串触发上述预设解析）。
- 三个调用点同步把硬编码默认值改成空字符串，交给 `run_workflow`/`parse_steps` 统一解析：CLI `--steps`（`cli.py`）、MCP 工具 `augur_workflow`（`mcp_server.py` 的 `_run_workflow_tool` 与 `@mcp.tool()` 注册函数）、HTTP `POST /api/workflow` 的 `WorkflowRequest.steps`（`api.py`）。显式传入非空 `steps` 时行为不变。

### Verified (re-checked, not a code change)
- 复核了 `docs/AGENT_PEER_REVIEW_SYNTHESIS.md` Verdict 里关于 P2-3（regime 检测）的风险提示：`regime_weights.py`/`macro_features.py` 目前确实是逐次独立分类 VIX+SPY 阈值，没有任何平滑/滞后机制，也没有历史 `date_str` 回测——这条"不要把共识结果当风险输入"的警告依然成立，不是文档过期误判。

### Notes
- Full suite: **2075 passed**, 0 failed（含需要网络的 5 个测试）。
- 测试隔离修正：`test_parse_steps_defaults`、`test_default_steps_when_empty` 原先依赖"空 steps → 固定默认值"的假设，现在显式隔离 `~/.augur/workspace.yaml` 路径，避免开发机/CI 上真实存在的 workspace 配置影响断言结果。

## [10.16.2] - 2026-06-24

收尾 P1 backlog 剩余的真实缺口（P1-6、P1-7），并纠正一条此前误判为"未完成"的状态（P1-8）。

### Fixed
- **`augur_workflow` 单步失败会拖垮整条流水线**（P1-6 真实缺口）：`analyze`/`consensus`/`committee` 三个步骤此前没有 try/except 保护——任何一步内部异常（比如某个大师的分析逻辑抛错）会直接让整个 `run_workflow()` 抛出，前面已经成功的 `fetch` 结果也拿不到。现在这三步都和 `fetch`/`debate`/`sentiment` 一样有独立的异常捕获，失败的步骤记录 `{"error": ...}` 并继续往后跑。
- **`format_workflow_summary()` 在某步骤失败时会再炸一次**：原来的渲染逻辑假设每个 step 的结果一定是正常结构（比如 `results["consensus"]["signal"]`），如果该 step 实际是 `{"error": ...}`，渲染会因为 `KeyError` 整个崩掉——这是上面那条修复出来后才暴露的连带 bug。现在统一加了 `"error" not in results[...]` 守卫，并新增"Step Errors"小节把失败的步骤列出来，方便排查。
- **`GET /api/workspace` 补上 ETag / 条件请求**（P1-7）：和仪表盘其它几个高频轮询端点（hot-tickers、market-overview、sector-performance）保持一致的模式，配置没变时客户端可以用 `If-None-Match` 换 304，不用每次都拉全量 JSON。

### Corrected (not actually a bug)
- **P1-8**（"Feedback path → `~/.augur/feedback/`"）核实后发现在更早的 v10.15.0 agent #3 共识引擎迭代里就已经实现（`USER_FEEDBACK_DIR` 覆盖优先级，配套测试 `test_user_feedback_dir_overrides_repo`/`test_user_feedback_precedence`），synthesis 文档的状态表没同步更新。本次只是纠正文档状态。

### Notes
- 新增 4 个测试：`run_workflow` 单步失败场景 ×2、ETag 条件请求 ×1，外加上一轮遗留的 1 个。
- P1 backlog 现在只剩 **P1-9**（`dashboard/routes/workspace.py` router 拆分）——这是个纯架构重构、收益主要是代码组织，没有直接的用户可见行为变化，先不动，等你这轮产品体验完、确认没有更紧急的事再排期。

## [10.16.1] - 2026-06-24

收尾 v10.16.0 文档巡检中发现的剩余 P1 项；同时纠正了两条此前误判为"未完成"的状态。

### Added
- **委员会页面读取工作区配置**（P1-4）：`committee.html` 现在在加载时 `fetch('/api/workspace')`，若存在已保存的 `committee_preset`（value/china/macro/growth/all）则自动套用，不再总是要求用户手动点选预设按钮。
- `tests/test_p1_followups_v10_16.py`：4 个回归测试，锁定 manifest/Hermes yaml 版本号与 `augur.__version__` 同步、SKILL.md frontmatter 同步、committee 页面的工作区接线。

### Fixed
- **`scripts/generate_skills.py` 版本漂移**（P1-2）：18 个 `skills/*/manifest.json` + `SKILL.md` 中硬编码的 `9.0.3` / `9.0.0` 改为从 `augur.__version__` 动态读取；`ZH_TOOL_SECTION`/`EN_TOOL_SECTION` 工具说明从仅列 5/13 个工具补全为完整的 13 个。
- **`hermes-agents/*.yaml` 版本漂移**：18 个文件的 `version: "10.10.0"` 同步为当前版本号（无生成脚本，手工同步）。

### Corrected (not actually bugs)
- 上一版 `docs/RELEASE_NOTES.md` 的"接下来还会做什么"里提到的两项实际**已经实现**，文档判断有误，本次予以纠正：
  - `enabled_personas` Settings 页多选 UI 在 v10.14.0/v10.15.0 就已存在（`settings.html` 的 `workspace-persona-enable` checkbox + `collectEnabledPersonas()`）。
  - workspace profile 的 9 个 i18n key 在 zh/en/ja/ko 四语言中均已完整。

### Notes
- Full suite: **2065 passed**, 0 failed.
- P1 backlog 剩余：P1-6（per-step status envelope）、P1-7（ETag）、P1-8（feedback path）、P1-9（router split）——均为内部架构打磨项，详见 `docs/AGENT_PEER_REVIEW_SYNTHESIS.md`。

## [10.16.0] - 2026-06-24

P1-1（Agent Peer Review backlog）：MCP Workspace 工具，闭合"终端定制 ↔ agentic 接入"的最后一块缺口。

### Added
- **`augur_workspace_get` / `augur_workspace_set` / `augur_workspace_profiles`** MCP 工具：agent host（OpenClaw/Hermes/任意 MCP 客户端）现在可以读取并代写用户在 Dashboard 设置的终端布局、enabled_personas、committee_preset，不再是"chat-sidecar"——这是项目自身 peer-review 终审结论里点名的唯一缺口。
- `consensus.meta_model_weight` 配置项（默认 0.5，0 表示完全关闭中位数混合），让 MetaModel 50/50 blend 不再是隐藏的硬编码行为。
- `tests/test_workspace_mcp_v10_16.py`：17 个新测试，含一个用 AST 静态解析 `.mcp.json` ↔ 源码 `@mcp.tool()` 数量一致性的防漂移测试。

### Fixed
- **代码审查（针对近期 workspace/workflow/consensus 批次）**：
  - `registry.py` 超时分支误判：`ThreadPoolExecutor.future.result(timeout=30)` 在 Python 3.9/3.10 抛 `concurrent.futures.TimeoutError`，与内置 `TimeoutError` 不是同一个类，原代码只捕获了内置类，导致"分析超时"提示从未真正触发（仍会被下层 `except Exception` 兜住，不影响功能，只是报错信息不准）。
  - `consensus/macro_features.py` 模块级缓存读写未加锁，与项目自身"线程安全加固"目标不一致；现用 `RLock` 包裹。
- **文档/manifest 漂移**（peer-review 已点名的系统性问题）：`docs/openclaw-setup-guide.md`、`docs/en/openclaw-setup-guide.md`、`docs/hermes-setup-guide.md`、`docs/en/hermes-setup-guide.md` 工具数量从过期的 9/10 个修正为 13 个，并补上缺失的 `augur_workflow`/`augur_workspace_*` 条目。
- **开发依赖缺口**：`pytest`/`pytest-asyncio`/`httpx` 已在 `dev` extra，但 `beautifulsoup4` 缺失导致全新 clone 跑不了 12 个 UX 测试文件；已补全到 `pyproject.toml` 的 `dev` extra。

### Notes
- Full suite: **2060 passed**, 0 failed (`pytest tests/ -q --ignore=tests/test_analyze_api_v12.py`).
- P1 backlog 剩余项（manifest regeneration、profile i18n、committee_preset 接线等）见 `docs/AGENT_PEER_REVIEW_SYNTHESIS.md`，下一 session 继续。

## [10.15.1] - 2026-06-22

50-round QA gatekeeper patch (Agent #5, 10 full-suite rounds).

### Fixed
- **Test isolation**: autouse workspace cache reset in `tests/conftest.py` — fixes e2e dashboard `agent_count` pollution from stale `enabled_personas`.
- **Sentiment integration test**: patch `MetaModel.load` in `test_integration_v8` so sentiment ±0.5 hook is tested without 50/50 meta-model dilution.

### Notes
- Full suite: **2043 passed**, 0 failed (rounds 2–10); see `docs/iterations/agent5-fullsuite-SUMMARY.md`.

## [10.15.0] - 2026-06-22

Bloomberg 风格终端工作区定制 + Agentic 工作流 MCP + 共识增强模块 + **Agent Peer Review** 集成迭代。

### Added
- **Terminal Workspace** (`src/augur/workspace.py`)：布局预设（analyst/trader/committee/minimal）、默认首页、隐藏导航、Ticker Tape 开关；持久化到 `~/.augur/workspace.yaml`。
- **Multi-profile workspace**：命名配置 CRUD、`/api/workspace/profiles`、export/import bundle。
- **Dashboard API**：`GET/PUT /api/workspace`、`GET /api/workspace/presets`；Settings 页「终端工作区」配置区。
- **Agentic Workflow**：`augur_workflow` MCP 工具 + `src/augur/workflow.py`（fetch → analyze → consensus → committee → debate → sentiment 可组合步骤链）。
- **Consensus 模块** (`src/augur/consensus/`)：industry_matrix、regime_weights、macro_features、probability_calibrator、meta_model、rolling_ic、regime_router、risk_manager。
- **Agent Peer Review synthesis** (`docs/AGENT_PEER_REVIEW_SYNTHESIS.md`)：6 份 peer review 汇总 + P0/P1/P2 backlog + mutual promotion 计划。

### Fixed
- **Persona-aware weights**：`restrict_weights_to_agents()` 将行业/机制权重重归一化到实际参与 agent。
- **Server-side landing**：`GET /` 使用 `resolve_landing_url` 302 跳转，避免 trader 配置下首页 widget 闪烁。
- **Workflow integration**：空 `--agents` 时读取 workspace `enabled_personas`；consensus+committee 步骤去重；输出 `low_participation` 警告。
- **Regime double-count**：`build_consensus_weights` 仅通过 65/35 blend 应用一次 regime overlay。
- **Sidebar precedence**：profile `sidebar_collapsed` 权威覆盖 stale `localStorage`。
- **MCP manifest**：`.mcp.json` 补齐 `augur_workflow`（10 tools）。
- Dashboard/registry 主路径移除 `scanner.*` fallback import；`scanner/` 标记 legacy。

### Notes
- Peer reviews: `docs/reviews/peer-review-*.md` (6/9 submitted).
- Tests: run `tests/test_v10_14*.py tests/test_*v10_15*.py tests/test_workflow_enabled_personas.py`.

## [10.13.0] - 2026-06-09

跨页面 Ticker 导航：Signals / History → Stocks 一键分析。

### Added
- **Signals 页面 ticker 链接**：自选股信号表中，代码列变为可点击链接（橙色下划线），跳转到 `/stocks?ticker=X`，stocks 页面自动触发分析（已有 URL 参数 auto-run 逻辑）。
- **History 页面 ticker 链接**：历史记录表中，代码列同样变为链接，`stopPropagation()` 防止触发展开行。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.12.0] - 2026-06-09

Scanner + Stocks 一键加入自选股。

### Added
- **Scanner → Watchlist**：扫描结果每行 Ticker 旁新增 `+` 按钮，点击直接调用 `/api/watchlist/add` 加入自选股，成功显示 toast 提示。
- **Stocks → Watchlist**：分析完成后 Header 按钮区出现"+ Watchlist"按钮（默认隐藏），点击将当前 ticker（含 PE/ROE/Price/MarketCap）加入自选股，添加成功后按钮变为"✓ Watchlist"并禁用避免重复。
- i18n: scanner-add-watchlist / scanner-added-watchlist / stocks-add-watchlist / stocks-added-watchlist 等 (zh+en)。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.11.0] - 2026-06-09

Compare 页因子级雷达修复 + 因子明细展开。

### Fixed
- **`_FACTOR_MAP` / `_catAvg` 作用域 bug**：两个变量定义在 `renderRadarChart` 内部，`renderFactorBreakdown` 无法访问（ReferenceError）——导致因子明细表格静默失效。将 `_FACTOR_MAP`、`_INVERT`、`_catAvg` 提升至模块作用域，因子真实分现在正确渲染。

### Added
- **因子明细展开按钮**：compare 页雷达图下方新增"▶ 展开因子明细"按钮（默认收起），展开后显示按类别（估值/成长/质量/动量/安全）分组的因子分表格，每个值附带彩色 mini 进度条（绿/橙/红）。
- i18n: compare-factor-toggle / compare-factor-collapse (zh+en)。

### Notes
- `metadata.factors` 已存在于所有 18 个 agent 的分析结果中，无需 API 改动。
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.10.0] - 2026-06-09

18 预生成 Hermes agent YAML + skill manifest 更新。

### Added
- **`hermes-agents/` 目录**：18 个预生成 Hermes Studio agent YAML（每位投资人一个文件），`cp hermes-agents/*.yaml ~/.hermes/agents/` 即可，无需跑任何命令。每个 YAML 包含完整 system prompt、MCP 工具依赖（`augur-mcp`）、语言标注（4 位中国投资人为 zh）。
- **hermes-setup-guide 更新**（中/英）：新增方式二"独立 Agent（预生成 YAML）"，所有方式编号重排（现共 6 种方式）。

### Changed
- **所有 skills/*/manifest.json**（19 个）：`command` 改为 `augur-mcp`，移除 `args: [mcp-server]`，与 v10.9 console script 对齐。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.9.0] - 2026-06-09

`augur-mcp` 独立 stdio 入口 + Hermes Studio 接入文档。

### Added
- **`augur-mcp` console script**：新增 `augur-mcp` 独立命令，作为 stdio MCP transport 专用入口，供 Hermes Studio / Claude Desktop / mcporter 等桌面 MCP 客户端直接 spawn（无需 `augur mcp-server` 子命令，兼容旧命令）。
- **`src/augur/mcp_entry.py`**：极简 stdio 启动器，`if __name__ == "__main__"` 直接调 `run_server()`。
- **Hermes Studio 接入文档**：hermes-setup-guide.md（中/英）补充 Option A（Hermes Studio / Claude Desktop）配置示例，更新全部示例命令为 `augur-mcp`。

### Notes
- `[project.entry-points."mcp.server"]` PEP 720 discovery 入口保持不变；新加的 `augur-mcp` 是给 stdio spawn 用的第二条路——两条路都通。
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.8.0] - 2026-06-09

键盘快捷键帮助 Modal。

### Added
- **键盘快捷键 Modal**：按 `?` 键（或侧边栏底部 `?` 按钮）弹出快捷键参考卡，列出所有可用快捷键（`/` / `Ctrl+K` 聚焦、`Ctrl+Enter` 提交、`Esc` 关闭、`1–6` 快速导航、`?` 显示帮助）。点击背景或按 Esc 关闭，四语言 i18n 支持。
- i18n: kbd-modal-title / kbd-focus-ticker / kbd-submit-analysis / kbd-close-panels / kbd-quick-nav / kbd-nav-pages / kbd-show-help / kbd-modal-close / kbd-or (zh+en)。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.7.0] - 2026-06-09

Stocks 页体验增强：最近分析 chips + URL 状态同步。

### Added
- **最近分析 chips**：stocks 页在"快速选择"下方显示"最近:"一行，展示最近 6 条已分析过的股票代码（localStorage 存储），点击可直接重新分析。每次分析成功后自动更新列表（去重 + 保持最新在前）。
- **URL 状态同步**：分析完成后通过 `history.pushState` 更新浏览器 URL 为 `/stocks?ticker=AAPL`，使当前分析可被浏览器记录/书签/分享；刷新页面会自动重新触发分析。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.6.0] - 2026-06-09

History 分析日历热力图。

### Added
- **History 日历热力图**：页面顶部新增 GitHub 贡献图风格的 52×7 日历格，按日期展示分析活动；绿色=看多、红色=看空、橙色=中性、灰色=无记录；点击有数据的日格过滤当日记录，"清除日期筛选"按钮恢复全览。
- 日历数据通过独立请求 `/api/history?per_page=365` 拉取最近 365 条，客户端按日期聚合，不影响分页主流程。
- i18n: history-cal-title / history-cal-clear (zh+en)。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.5.0] - 2026-06-09

Chat 对话导出与清除。

### Added
- **Chat 页 Export MD 按钮**：首条消息发送后显示"⤓ Export MD"按钮，将对话记录（含 Agent 名称/用户问题/Agent 回复）下载为 Markdown 文件，文件名含 Ticker 和日期。
- **Chat 页 Clear 按钮**：清空 DOM 消息和 `_chatHistory` 数组，恢复欢迎语，隐藏 Export/Clear 按钮。
- `_chatHistory` 数组在 `sendMessage()` 中维护；`_showChatActionBtns()` 首消息后显示按钮。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.4.0] - 2026-06-09

委员会报告导出 + 优化器权重 CSV 导出。

### Added
- **Committee 报告导出**：委员会裁决出来后显示"复制报告"和"导出报告"两个按钮；Markdown 格式含裁决摘要（信号/评分/置信度/Kelly/投票）及各大师意见（关键发现/风险/推理）；支持 clipboard API + 降级。
- **Optimizer 权重 CSV 导出**：最优组合计算后显示"Export CSV"按钮，输出 Ticker/Weight_% / 年化收益率/波动率/Sharpe 等字段。
- `_committeeVerdict`、`_committeeOpinions`、`_committeeTicker` 全局变量存储委员会会话状态；`_buildCommitteeMarkdown()` 统一构建报告内容。
- `_optWeights`、`_optMeta` 全局变量存储优化器计算结果。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.3.0] - 2026-06-09

导出功能扩展：信号监控 CSV + 辩论记录复制/下载。

### Added
- **Signals 信号监控 CSV 导出**：页面顶部"导出 CSV"按钮，包含 Ticker/PE/ROE/毛利率及分析信号/评分/投票数，UTF-8 BOM 兼容 Excel。
- **Debate 辩论记录导出**：辩论完成后显示"复制记录"和"下载 MD"两个按钮；Markdown 格式含各轮 Agent 评分与推理，支持 clipboard API 及 fallback。
- `_debateData` 全局变量存储最近辩论结果，`_buildDebateMarkdown()` 统一构建 MD 内容。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.2.0] - 2026-06-09

数据可视化与导出增强：IC 柱状图、回测/扫描器 CSV 导出。

### Added
- **Performance 页 IC 柱状图**：排行榜下方新增 Chart.js 水平柱状图，按 IC 60d 排序展示各 Agent 得分，绿色正 IC / 红色负 IC，主题切换自动重绘。
- **Performance 页 CSV 导出**：排行榜"导出 CSV"按钮，下载包含 Rank/Agent/IC_60d/Accuracy/Signals 的 UTF-8 BOM CSV。
- **Backtest 排行榜 CSV 导出**：IC 排行榜卡片头部"导出 CSV"按钮，文件名含标的+天数+日期，包含全部 IC 字段。
- **Scanner 扫描结果 CSV 导出**：扫描结果区"导出 CSV"按钮，输出 Ticker/Consensus/Score + 各 Agent 得分列。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.1.0] - 2026-06-09

功能扩展：因子细分、历史搜索、设置外观、持仓/自选导出。

### Added
- **Compare 因子细分表**：雷达图下方展示每个维度的实际因子得分（0-10，颜色编码），按 valuation/growth/quality/momentum/safety 分组，仅当存在真实 metadata.factors 时显示。
- **History 搜索/筛选**：ticker 搜索框（防抖 300ms）+ bullish/neutral/bearish 信号筛选片；后端 `/api/history` 新增 `ticker` 和 `signal` 查询参数，`history.py` 的 `list_history`/`count_history` 支持 ticker_filter + signal_filter。
- **Settings 外观设置区块**：设置页顶部新增语言选择器（4 语言按钮组）和主题选择器（深色/浅色），active 状态橙色边框高亮。
- **Portfolio CSV 导出**：持仓页"导出 CSV"按钮，包含 Ticker/Shares/Avg Cost/Current Price/Market Value/P&L/Buy Date，UTF-8 BOM 兼容 Excel。
- **Watchlist CSV 导出 + 导入**：自选股页导出（ticker 列表 CSV）+ 文件选择导入（支持逗号/换行/分号分隔，自动去重，验证 ticker 格式）。

### Changed
- **Compare `_FACTOR_MAP` 完整覆盖**：新增所有 18 个 persona 的 factor key 映射（duan_yongping/fisher/li_lu/lynch/marks/munger/soros/thiel/zhang_lei/dayu/serenity），`_INVERT` 增加 `supply_chain_bottleneck`。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [10.0.0] - 2026-06-09

v10 首发：日语/韩语国际化支持，四语言循环切换（中/英/日/韩），降级链机制。

### Added
- **日语 (ja) i18n**：181 个 key 的完整日语翻译，覆盖导航、委员会、股票分析、回测、对比、历史等全页面。
- **韩语 (ko) i18n**：181 个 key 的完整韩语翻译，与日语覆盖范围一致。
- **四语言循环切换**：语言 toggle 按钮由 zh↔en 双向切换升级为 zh→en→ja→ko→zh 循环；`localStorage` 持久化四种语言选择。
- **浏览器语言自动检测**：`navigator.language` 自动识别 zh/ja/ko/en，首次访问按浏览器偏好设语言。
- **降级链机制**：`t()` 和 `applyLanguage()` 支持 ja/ko → en → zh 三级降级，缺失 key 优雅回落到英文。
- **Agent detail modal（stocks 页）**：点击任意 agent scorecard 弹出详情 modal，展示 key_findings / risks / reasoning；ESC 或点击遮罩关闭。

### Changed
- **i18n.js 架构**：`toggleLanguage()` 改为基于 `_LANG_CYCLE` 数组的循环逻辑；`applyLanguage()` 重构为通过内部 `_getVal()` 函数支持降级；`html[lang]` 属性正确映射到 `zh-CN` / `en` / `ja` / `ko`。
- **测试 fixture 适配**：6 个测试文件的 `i18n_dicts` fixture 更新为仅解析 zh 和 en 块（边界到 `\n    ja:`），避免 ja/ko 覆盖 en 解析结果。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [9.1.0] - 2026-06-09

UI 全面升级：CSS token 统一、亮色模式修复、图表交互增强、Toast 升级、空状态统一。

### Added
- **Chart.js 主题联动**：主题切换时触发 `augur:theme-change` 事件，compare 雷达图与 stocks 历史图自动重绘以匹配新主题。
- **Ticker Tape 暂停 UX**：悬停自动暂停（amber overlay 反馈）；点击暂停显示居中 `⏸ 已暂停` badge；修复 hover-pause / click-pause 状态冲突。
- **Stocks 历史走势图交互**：点击数据点弹出摘要（日期/评分/信号）；30天/全部 range 切换；主题切换自动重绘。
- **Toast 通知升级**：4 种类型（✓ success / ⚠ warning / ✗ error / ℹ info）+ 对应颜色左边框 + icon 前缀；多条同时出现时垂直堆叠偏移。
- **空状态 SVG 插图统一**：history / watchlist / scanner 三页 emoji → Bloomberg 终端风格 inline SVG 线稿（时钟 / 剪贴板 / 放大镜）。
- **移动端底部导航收敛到 5 个 tab**：home / stocks / committee / history / settings；激活 tab 底部橙色圆点指示。

### Changed
- **CSS token 统一**：`colors_and_type.css` 成为唯一权威来源；补全所有 legacy alias（`--accent-*` / `--font-data` / `--radius-*` / `--transition-speed` / `--sidebar-width` / `--border-subtle` / `--bg-surface`）；`bloomberg.css` `:root` 和 `html.light` 整块替换为注释。
- **亮色模式完整性**：`ui-enhance.css` ticker-tape-pause 按钮背景改用 `var(--bg-card-hover)`；colors_and_type.css 补充 `--oracle-purple` / `--crystal` 亮色覆写；所有硬编码暗色 overlay 替换为 CSS var。

### Notes
- Tests: **1656 passed**（排除网络测试 test_analyze_api_v12.py）。

## [8.2.3] - 2026-06-07

Chat 数据卡片、UI inline style 清理、Scanner 边界加固、后端线程安全。

### Added
- **Chat 数据卡片**：对话页顶部嵌入实时行情卡片（价格、涨跌幅、Augur 共识信号+评分），60 秒自动刷新；分析结果 localStorage 缓存 10 分钟；任何 fetch 失败均静默隐藏。

### Fixed
- **Scanner 边界加固**：大小写不敏感去重（AAPL+aapl→1条）；单个 ticker 失败不影响整批扫描，失败列表记录在 `response.errors[]`。
- **后端线程安全**：`get_registry()`/`get_coordinator()` 双检锁（double-checked locking）；自定义 persona CRUD 操作包裹 `_singleton_init_lock`；`history.py` 改为 tmp+`os.replace()` 原子写，加 `_write_lock`。

### Changed
- **UI inline style 清理（MEDIUM 优先级）**：
  - `backtest.html`：30+ 处 inline style → `.backtest-form-row`/`.form-error-hint`/banner 类。
  - `create_persona.html`：`.cp-label`/`.required-star` 替代 verbose inline 标签样式。
  - `chat.html`：`.oracle-section-title`/`.oracle-welcome` 替代 inline h3/p 样式。
  - `history.html`：`.ticker-cell` 替代 JS 动态注入的 inline style。

### Notes
- Tests: **1652 passed**（排除网络测试）。

## [8.2.2] - 2026-06-07

全面整合 Loop 400 遗留代码、Optimizer 可视化、UI/UX 修复、Rules→Bot 打通。

### Added
- **Optimizer 有效前沿图**：`/optimizer` 页新增 Chart.js 散点+折线图，展示 Markowitz 有效前沿曲线，金色星标最优组合点，绿色圆点为各资产，蓝色折线为前沿边界。API 新增 `frontier_points`（40条前沿点）、`asset_points`、年化收益/波动率字段。
- **Rules→Bot 打通**：`/api/analyze/{ticker}` 与 `/api/watchlist/run` 现在在每次分析后自动触发 RulesEngine.evaluate()，满足条件即推送通知到 Telegram / Slack / WeChat / Lark（fire-and-forget，不阻塞响应）。

### Fixed
- **UI/UX 对比度**：orange 背景上 `color:#000/#fff` 全部替换为 `var(--bg-void)` / `var(--fg-1)`（WCAG AA 合规）。受影响页面：stocks、scanner、personas、optimizer、settings。
- **CSS 变量化**：debate/compare 硬编码 `rgba` → `var(--amber-wash)`；optimizer 5处 `#34c759/#ff9500/#5ac8fa/#ff3b30` → CSS 变量；index breadth bars `#fff` → `var(--bg-void)`。
- **页面标题统一**：personas.html 内联 `style="font:var(--h1)..."` → `.page-title` / `.page-lead` 标准类。
- **i18n 冲突解决**：合并 stash@{1} 带来的 i18n.js +238行新翻译键；修复 Jinja 模板表达式被当作 i18n literal 键的测试误报。
- **signals.html**：移除重复的 `.signals-header` inline CSS（已由 `layout.css` 的 `.page-header` 覆盖）。

### Changed
- Loop 400 stash 遗留代码（约 34 文件）全部合并进 main，解决 10 个冲突文件。
- compare.html：URL 参数 `?autorun=1` 支持自动触发对比分析。
- scanner.html：新增 `.heatmap-cell.error` 错误状态样式。

### Notes
- Tests: **1657 passed**（v8.2.1 为 1362，新增 295 项测试）。
- 新增 `tests/test_report_export_ux_v1.py`（报告导出 UX 回归套件）。

## [8.2.1] - 2026-06-06

Loop 200 review patch. 200-round multi-agent code review + UX walkthrough on top of v8.2.0.

### Fixed
- **Layout:** Sidebar and main content aligned via CSS Grid (`240px + 1fr`, gap 0); collapsed sidebar uses unified `--sidebar-width` token.
- **Report contrast:** Light-mode parchment + pale text unreadable; added `--report-*` semantic tokens and theme-aware SVG via `reportThemeColor()`.
- **Backend:** Price-series NaN/Inf sanitization, consensus tie → `NEUTRAL`, coverage-confidence normalization, persona YAML bool weights, sample-insufficient report messaging.
- **Auth:** WebSocket `/ws/prices?token=` validation; Dashboard fetch/WebSocket interceptors aligned with `augur.auth`; `GET /api/auth/config` discovery endpoint.

### Changed
- **UX / i18n / a11y:** Global `_t()` export, progress/copy i18n keys, empty-state parity across portfolio/compare/history/debate, 44px touch targets, reduced-motion support, stocks page `data-i18n`, mobile table scroll hints.
- **Pages:** Settings (redundant PUT removed), Scanner (explicit event args), Signals (reordered flow), Backtest (min capital validation), index onboarding/AAPL CTA, partial `data_error` surfacing.

### Notes
- Tests: **1362 passed** (up from ~1177 in v8.2.0).
- Review reports: [`docs/LOOP_200_REPORT.md`](docs/LOOP_200_REPORT.md) (complete) · [`docs/LOOP_400_REPORT.md`](docs/LOOP_400_REPORT.md) (partial — stash recovery pending).
- README screenshots refreshed for v8.2.1 grid layout and report contrast (see `scripts/capture_readme_screenshots.py`).

## [8.2.0] - 2026-06-06

v8.2.0 release. Version bump from 8.1.0 to 8.2.0.

### Added
- AI Chat with 11 personas, Portfolio Optimizer (Markowitz), Master Compare,
  Debate Mode, History, Leaderboard (dashboard pages).
- LearningEngine (IC-based weight auto-tuning), SentimentAnalyzer (social
  sentiment fusion), WebSocket price streaming at `/ws/prices`, RulesEngine
  (DSL alerts with multi-channel notifications).
- HD-2D design system: `ExecCard`, `OracleSays`, `ScorecardGrid` components,
  layout spacing fix (240px gap), adaptive color variables
  (`var(--signal-buy)`, `var(--signal-sell)`), responsive breakpoints
  (768px / 480px), bilingual number/date formatting.
- Persona audit, makefile, pyproject polish, and analyzer/ws prices work
  (rounds 11–12).

### Changed
- Bumped package version from 8.1.0 to 8.2.0 in `src/augur/__init__.py` and `pyproject.toml`.
- Added this `CHANGELOG.md` to document release history.

### Notes
- No breaking changes vs 8.1.0.
- All 1177 existing tests remain green.

## [8.1.0] - 2026-06-06

Round 7 release. Rate limiting, data error UX, agent registry, dashboard a11y,
route validation, branded 404/500, chat docstrings, learning log, rules YAML.
