# Agent2 Workflow QA — Round 6

**Fix:** R1-5 — warnings in human-readable summary

## Change

- `format_workflow_summary()` renders `── Warnings ──` section when `warnings` present
- CLI text mode and MCP `augur_workflow` header+summary now show low_participation etc.

## Pytest

**Result:** 40 passed (added `test_warnings_in_summary`)

## Status

R1-5 **fixed**
