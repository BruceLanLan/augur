# Agent2 Workflow QA — Round 3

**Fix:** R1-2 — debate respects persona / agent scoping

## Change

- `run_debate()` accepts `enabled_personas` when no `initial_results`
- Workflow derives `debate_personas` from explicit `--agents` or workspace filter

## Pytest

**Result:** 37 passed — persona tests unchanged, debate-only path uses filtered analyze

## Status

R1-2 **fixed**
