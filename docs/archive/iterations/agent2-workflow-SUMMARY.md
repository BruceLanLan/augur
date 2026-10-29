# Agent2 Workflow QA — 10-Round Summary

**Branch:** `feature/v9-dev`  
**Date:** 2026-06-22  
**Agent:** #2 Workflow QA loop

## Executive summary

Ten-round test-fix loop on the agentic workflow surface completed with **310 gate tests green** (41 scoped workflow tests). Seven P1 issues from peer review #2 and synthesis doc were fixed; three P2 items deferred.

## Round index

| Round | Focus | Outcome |
|-------|-------|---------|
| 1 | Baseline audit | 36 passed; 6 issues logged |
| 2 | Debate reuses analyze | `initial_results` in `run_debate` |
| 3 | Debate persona scoping | `enabled_personas` on debate |
| 4 | `step_status` envelope | P1-6 landed |
| 5 | API error parity | 500 + detail on runtime errors |
| 6 | Warnings in summary | CLI/MCP text output |
| 7 | Invalid agents warning | `all_requested_agents_invalid` |
| 8 | Fetch partial failure | `context_unavailable` guard |
| 9 | `step_timings_ms` | Observability |
| 10 | Final gate | 310 passed |

## Files changed

| File | Changes |
|------|---------|
| `src/augur/workflow.py` | step_status, timings, debate reuse, warnings, fetch guard |
| `src/augur/registry.py` | `run_debate(initial_results, enabled_personas)` |
| `src/augur/api.py` | Generic exception → HTTP 500 |
| `tests/test_workflow_enabled_personas.py` | +4 tests |
| `tests/test_workflow_cli_v10_15.py` | +1 API error test |

## Test gate

```bash
python3 -m pytest tests/test_v10_14*.py tests/test_*v10_15*.py \
  tests/test_peer*.py tests/test_workflow_enabled_personas.py -q --tb=short
```

**Final:** 310 passed, 1 warning (urllib3/LibreSSL — env, not workflow)

## Deferred (P2)

- MCP structured JSON default for workflow
- `workflow_preset` workspace field
- `/ws` workflow progress streaming

## Verdict

Workflow CLI, REST API, and MCP `augur_workflow` are **integration-ready** for v10.15.x with persona-aware debate, observability envelopes, and consistent error surfaces.
