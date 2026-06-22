# Agent2 Workflow QA — Round 9

**Enhancement:** step timing observability

## Change

- Workflow records `step_timings_ms` per executed step (fetch, analyze, consensus, committee, debate, sentiment)

## Pytest

**Result:** 41 scoped / 310 gate tests passed

## Remaining P2 (deferred)

- `workflow_preset` linked to layout presets (P2-7)
- WebSocket progress streaming (P2-5)
- Structured JSON default for MCP workflow return

## Status

Observability increment **landed**; no open P0/P1 in workflow scope
