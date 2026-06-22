# Agent2 Workflow QA — Round 5

**Fix:** R1-4 — API error-handling parity with CLI/MCP

## Change

- `POST /api/workflow` catches generic `Exception`, logs, returns HTTP 500 with `Workflow failed: {e}`

## Pytest

**Result:** 39 passed (added `test_workflow_runtime_error_returns_500`)

## Status

R1-4 **fixed**
