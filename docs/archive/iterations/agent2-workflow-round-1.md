# Agent2 Workflow QA — Round 1

**Branch:** `feature/v9-dev`  
**Date:** 2026-06-22  
**Scope:** `workflow.py`, CLI `workflow`, MCP `augur_workflow`, `POST /api/workflow`, `test_workflow*`, `test_e2e_agentic*`

## Pytest

```bash
python3 -m pytest tests/test_workflow_cli_v10_15.py \
  tests/test_workflow_enabled_personas.py tests/test_e2e_agentic_v10_15.py -q
```

**Result:** 36 passed in 0.69s

## Findings

| ID | Sev | Issue |
|----|-----|-------|
| R1-1 | P1 | `debate` step calls `run_debate()` which re-runs `analyze_with_all` even when `analyze` already ran in the same chain |
| R1-2 | P1 | `run_debate` ignores workspace `enabled_personas` and explicit `--agents` filter |
| R1-3 | P1 | No `step_status` envelope (peer review P1-6) |
| R1-4 | P1 | REST API catches only `ValueError`; runtime errors become unhandled 500 without detail |
| R1-5 | P1 | `warnings` array not surfaced in CLI/MCP text `summary` |
| R1-6 | P2 | Fetch failure propagates and crashes downstream analyze steps |

## Action

Prioritize R1-1 through R1-5 for rounds 2–6.
