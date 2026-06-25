# Agent Peer Review Synthesis — v10.15.1

**Integration Lead:** Reviewer #10  
**Date:** 2026-06-22  
**Inputs:** 6 peer reviews (#1 Workspace, #2 Workflow, #3 Consensus, #4 Dashboard, #8 Agent Hosts, #9 Architecture) + v10.14/v10.15 diff  
**Missing reviews:** #5 Testing, #6 Docs, #7 MCP — inferred from code/tests where noted

---

## 50-round QA (5 agents × 10 rounds)

**Gatekeeper program:** Five agents each run 10 full-suite iterations (`pytest tests/ -q --ignore=tests/test_analyze_api_v12.py`). Agent #5 (Testing) completed rounds 1–10 on 2026-06-22.

| Agent | Rounds | Final pass/fail | Status |
|-------|--------|-----------------|--------|
| #5 Testing | 10/10 | 2043 / 0 | ✅ Green (rounds 2–10) |

### P0 resolved in QA pass

| ID | Item | Resolution |
|----|------|------------|
| P0-QA-1 | E2E dashboard `agent_count` ≥ 18 | Workspace cache reset in `conftest.py` |
| P0-QA-2 | Scanner error envelope (`enabled_personas` kwarg) | Suite isolation + existing `**kwargs` mock |
| P0-QA-3 | Sentiment factor consensus delta | MetaModel isolated in integration test |

### P1 deferred (unchanged)

Workspace MCP tools (P1-1), profile i18n (P1-3), step_status envelope (P1-6) remain next-session items — not regressions in full suite.

**Artifact:** `docs/iterations/agent5-fullsuite-SUMMARY.md`

---

## Consensus themes (9-reviewer lens)

| Theme | Reviewers | Summary |
|-------|-----------|---------|
| **Terminal ↔ agent pipeline disconnect** | #1, #2, #3, #8 | Workspace profiles, `enabled_personas`, and landing presets are Dashboard-centric; workflow/MCP ran full 18-agent chains until v10.15 wiring. Agent hosts cannot read/apply workspace state. |
| **Cross-layer persona contract** | #1, #2, #3, #9 | `enabled_personas` must propagate consistently through analyze, consensus weights, workflow CLI/MCP/API, and debate. Filtered runs need weight renormalization, not silent equal-weight drift. |
| **Observability & partial failure** | #2, #3, #4 | Workflow lacks step envelopes, duplicate consensus work, and surfaces `low_participation` only in registry metadata. Consensus weighting stack is invisible to agents. |
| **Monolith & dual-app debt** | #4, #9 | `dashboard/app.py` (~4k lines) and `augur.api` duplicate auth/CORS; workflow HTTP only on slim API app. Blocks deploy variants and third-party embedding. |
| **Manifest / doc drift** | #8 | 10 MCP tools in server; `.mcp.json` and persona manifests lag (workflow omitted, version skew). OpenClaw verify script expects 9 tools. |
| **Legacy `scanner/` surface** | #9 | Primary paths guarded by tests; optional `ten_x_screener` + external scripts remain. Confuses packaging and onboarding. |
| **UI completeness for workspace** | #1, #4 | Profile CRUD i18n missing; `committee_preset` stored but unused; incomplete `WORKSPACE_NAV_PAGES`; home flash before JS redirect. |

---

## Ranked backlog

### P0 — Ship blockers / integration breaks

| ID | Item | Source | Status v10.15.0 |
|----|------|--------|-----------------|
| P0-1 | **Persona-aware consensus weight renormalization** (`restrict_weights_to_agents`) | #3 | ✅ Implemented |
| P0-2 | **Server-side landing redirect** via `resolve_landing_url` on `GET /` | #1 | ✅ Implemented |
| P0-3 | **Workflow dedupe + low_participation warnings** in JSON output | #2, #3 | ✅ Implemented |
| P0-4 | Wire `enabled_personas` into `run_workflow()` when `--agents` empty | #1, #2, #3 | ✅ (Review #2) |
| P0-5 | Fix regime double-count in `build_consensus_weights` | #3 | ✅ (Review #3) |
| P0-6 | Sidebar `localStorage` vs profile precedence | #1 | ✅ (Review #1) |
| P0-7 | Add `augur_workflow` to `.mcp.json` tools list | #8 | ✅ (Review #8) |

### P1 — Next session high value

| ID | Item | Source | Status v10.16.2 |
|----|------|--------|------------------|
| P1-1 | MCP workspace tools (`augur_workspace_get/set/profiles`) | #8 | ✅ Implemented |
| P1-2 | Regenerate all persona `manifest.json` + Hermes yaml with 13 tools | #8 | ✅ Implemented |
| P1-3 | Complete workspace profile i18n keys in `i18n.js` (9 keys × 4 locales) | #4 | ✅ Already done (verified, predates v10.16.0) |
| P1-4 | Wire `committee_preset` to committee page defaults | #1 | ✅ Implemented |
| P1-5 | `enabled_personas` multi-select in Settings UI | #1 | ✅ Already done (verified, predates v10.16.0) |
| P1-6 | Per-step `step_status` envelope + partial failure in workflow | #2 | ✅ Implemented (envelope existed; analyze/consensus/committee lacked try/except — fixed) |
| P1-7 | `GET /api/workspace` ETag / conditional GET | #4 | ✅ Implemented |
| P1-8 | Feedback path → `~/.augur/feedback/` for PyPI installs | #2, #3 | ✅ Already done (verified, shipped in agent3-consensus round 3, predates v10.15.0) |
| P1-9 | Extract `dashboard/routes/workspace.py` (R1) | #4, #9 | Pending — deferred, larger architectural refactor, held back pending user product review |

### P2 — Maturity / architecture

| ID | Item | Source | Status v10.16.3 |
|----|------|--------|------------------|
| P2-1 | Extract `ConsensusEngine` from `registry.py` (R3) | #9 | Pending |
| P2-2 | Shrink `scanner/` to single compat entry (R2) | #9 | Pending |
| P2-3 | Regime detector v2 (hysteresis, historical `date_str`) | #3 | **Narrow scope shipped in v10.16.8** — `macro_features.classify_regime` adds an asymmetric VIX band (enter 25 / exit 23) + a 3-day min-dwell confirmation scan; `date_str` now does a real point-in-time fetch (no look-ahead, verified empirically) instead of being ignored. Historical validation (`scripts/regime_backtest_v2.py`, 2015-2026): flip count 389→101, whipsaw count 146→10, crash-window response lag 2-4 days, window-length independence confirmed (sampling restricted to non-SIDEWAYS dates — SIDEWAYS is also the dwell scan's seed state, so a SIDEWAYS-only sample can't tell "seed washed out" from "seed never challenged"). **Still open / explicitly out of scope:** whether the hand-picked `_REGIME_ADJUSTMENTS` multipliers themselves improve outcomes was not touched — that's the other half of this gate, deferred to P2-4. |
| P2-4 | Unified OOS calibration pipeline (also: validate `_REGIME_ADJUSTMENTS` multipliers against a flat-weight baseline out-of-sample) | #3 | **Shipped in v10.16.9** — added point-in-time fundamentals (`pit_fundamentals.py`) so historical replay finally has real, look-ahead-safe pe/pb/roe instead of constant 0 (previously this made any such validation null by construction); built a cross-sectional, per-day, regime-bucketed rank-IC harness (`compute_cross_sectional_regime_ic`) using `apply_regime_weights` against a flat baseline; ran it for real over 37 tickers, 2022-01..2026-06 (`scripts/regime_weight_oos.py`). **Result: deltas are small and mixed-sign. SIDEWAYS (n=746, the statistically credible bucket): delta=+0.0009, essentially zero. BEAR_HIGH_VOL (n=9, two clustered episodes Aug 2024 + Apr 2025): delta=+0.0081 nominally positive but underpowered — 2022 bear market not covered due to 90-day filing lag.** Per-agent cross-sectional IC in BEAR_HIGH_VOL: graham +0.086 (supports the table's hypothesis), marks −0.030 (contradicts it for these 9 days), dalio 0.000 (no differentiation). The BEAR_HIGH_VOL bucket is too underpowered to draw a general conclusion about bear-market regime weighting; the statistically meaningful result (SIDEWAYS ≈ zero) says the multipliers neither help nor hurt in normal conditions. Whether to keep/retune/drop them is a product decision left open. |
| P2-5 | `/ws/workspace` + workflow progress streaming | #4 | Pending |
| P2-6 | Lazy persona registration per profile | #9 | Pending |
| P2-7 | `workflow_preset` field linked to layout presets | #2 | ✅ Implemented — `LAYOUT_PRESETS[*]["workflow_steps"]` + `get_default_workflow_steps()`; CLI `--steps` / MCP `augur_workflow` / `POST /api/workflow` default to `""` and resolve via the active profile's layout preset when not explicitly given. |
| P2-8 | `augur-terminal` meta-skill + Hermes committee yaml | #8 | Pending |

---

## Fixes landed in this integration pass (Reviewer #10)

1. **`restrict_weights_to_agents`** — consensus industry/regime weights renormalized to participating agents before scoring.
2. **`GET /` server redirect** — trader/minimal/committee profiles skip home widget flash; uses existing `resolve_landing_url`.
3. **Workflow consensus cache** — single `get_consensus` call when both `consensus` and `committee` steps run; exposes `low_participation`, `regime`, and top-level `warnings`.

---

## Mutual promotion iteration plan (next session)

Nine reviewers rotate **one promotion each** — each agent implements one P1 item and updates one other reviewer's follow-up:

| Agent slot | Promote (implement) | Cross-promote (document/test) |
|------------|---------------------|-------------------------------|
| #1 Workspace | P1-4 committee_preset wiring | Verify #8 MCP workspace story |
| #2 Workflow | P1-6 step_status envelope | Add tests for #3 weight metadata export |
| #3 Consensus | P1-8 feedback path to `~/.augur` | Golden tests for #10 integration fixes |
| #4 Dashboard | P1-3 profile i18n keys | ETag spike for #1 landing cache |
| #5 Testing | E2E: profile → workflow → consensus parity | Cover P0-1..P0-3 regression suite |
| #6 Docs | Sync OpenClaw/Hermes tool counts | Agent-integration-guide workspace section |
| #7 MCP | P1-1 workspace MCP tools | Structured JSON default for workflow |
| #8 Agent Hosts | P1-2 manifest regeneration | `.mcp.json` + verify script = 10 tools |
| #9 Architecture | P1-9 router split (workspace first) | Scanner shrink plan for #9 R2 |
| #10 Integration | Synthesis refresh + P1 triage | Merge conflicts, test gate, release notes |

**Session gate:** `python3 -m pytest tests/test_v10_14*.py tests/test_*v10_15*.py tests/test_peer*.py tests/test_workflow_enabled_personas.py -q --tb=short`

**Release cadence:** v10.15.x patch for P0/P1 integration; v10.16 for router split + MCP workspace.

---

## Verdict

v10.15.0 closed the **highest-risk integration gaps** between terminal workspace, workflow pipeline, and consensus weighting. v10.16.0/10.16.1 closed the remaining agentic gap: agent hosts are no longer chat-sidecars now that `augur_workspace_get/set/profiles` (P1-1) has shipped, and the committee page itself now reflects workspace state (P1-4). v10.16.2 added workflow partial-failure resilience (P1-6) and workspace ETag support (P1-7); P1-8's feedback path was confirmed already shipped (predates v10.15.0), not a gap. v10.16.3 (P2-7) closed the loop on the customization↔agentic story specifically for workflows: the layout preset chosen in `/settings` now also drives the default behavior of agent-triggered `augur_workflow` calls, not just Dashboard display. The Bloomberg terminal story is credible end-to-end (Dashboard + CLI/MCP). **Do not treat consensus outputs as risk inputs** until P2-3 regime validation lands — this gate has two halves. v10.16.8 closed the first half (regime classification was a noisy single-snapshot with no hysteresis; now uses a confirmed/smoothed classifier with real point-in-time `date_str` support, validated against ~9 years of history). v10.16.9 closed the second half: whether `_REGIME_ADJUSTMENTS`'s hand-picked multipliers actually improve outcomes out-of-sample was tested for real, using point-in-time fundamentals and a cross-sectional regime-bucketed rank-IC harness over 37 tickers and ~4.4 years. **The result is not a confirmation that the multipliers help — the statistically credible bucket (SIDEWAYS, n=746) shows delta≈+0.0009 (essentially zero), and the BEAR_HIGH_VOL bucket (n=9, two clustered episodes in Aug 2024 and Apr 2025) is too underpowered to generalize — the 2022 bear market isn't covered because the 90-day filing lag pushes FY2022 annual data past March 2023. Per-agent cross-sectional IC in BEAR_HIGH_VOL shows mixed results: graham supports the hypothesis (+0.086), marks contradicts it (−0.030).** Do not read either P2-3 or P2-4 as "the regime-weighting system is proven to add value" — P2-3 means classification no longer flip-flops on noise, and P2-4 means the weighting multipliers have been honestly tested against the real data available; the bear regime that motivated the table remains under-covered by free annual filings. Whether to keep, retune, or remove `_REGIME_ADJUSTMENTS` given this result is an open product decision, not resolved by this gate. P1-9 (router split) is the only remaining P1 item, deliberately deferred pending real-world product feedback.
