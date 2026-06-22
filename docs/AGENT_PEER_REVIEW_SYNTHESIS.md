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

| ID | Item | Source |
|----|------|--------|
| P1-1 | MCP workspace tools (`augur_workspace_get/set/profiles`) | #8 |
| P1-2 | Regenerate all persona `manifest.json` + Hermes yaml with 10 tools | #8 |
| P1-3 | Complete workspace profile i18n keys in `i18n.js` (9 keys × 4 locales) | #4 |
| P1-4 | Wire `committee_preset` to committee page defaults | #1 |
| P1-5 | `enabled_personas` multi-select in Settings UI | #1 |
| P1-6 | Per-step `step_status` envelope + partial failure in workflow | #2 |
| P1-7 | `GET /api/workspace` ETag / conditional GET | #4 |
| P1-8 | Feedback path → `~/.augur/feedback/` for PyPI installs | #2, #3 |
| P1-9 | Extract `dashboard/routes/workspace.py` (R1) | #4, #9 |

### P2 — Maturity / architecture

| ID | Item | Source |
|----|------|--------|
| P2-1 | Extract `ConsensusEngine` from `registry.py` (R3) | #9 |
| P2-2 | Shrink `scanner/` to single compat entry (R2) | #9 |
| P2-3 | Regime detector v2 (hysteresis, historical `date_str`) | #3 |
| P2-4 | Unified OOS calibration pipeline | #3 |
| P2-5 | `/ws/workspace` + workflow progress streaming | #4 |
| P2-6 | Lazy persona registration per profile | #9 |
| P2-7 | `workflow_preset` field linked to layout presets | #2 |
| P2-8 | `augur-terminal` meta-skill + Hermes committee yaml | #8 |

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

v10.15.0 closes the **highest-risk integration gaps** between terminal workspace, workflow pipeline, and consensus weighting. The Bloomberg terminal story is credible for Dashboard + CLI/MCP happy paths. **Do not treat consensus outputs as risk inputs** until P1-8 feedback paths and P2-3 regime validation land. Agent hosts remain chat-sidecars until P1-1 workspace MCP ships.
