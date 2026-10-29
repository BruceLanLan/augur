# Agent2 Workflow QA — Round 2

**Fix:** R1-1 — debate reuses prior analyze responses

## Change

- `registry.run_debate()` accepts optional `initial_results` kwarg
- `workflow.run_workflow()` passes existing `responses` into debate when available

## Pytest

**Result:** 37 passed (added `test_debate_reuses_prior_responses`)

## Status

R1-1 **fixed**
