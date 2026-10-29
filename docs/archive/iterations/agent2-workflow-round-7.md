# Agent2 Workflow QA — Round 7

**Fix:** all-invalid `--agents` silent fallback

## Change

- When every requested agent ID is unknown, append `all_requested_agents_invalid` warning before falling back to workspace/default set

## Pytest

**Result:** 41 passed (added `test_all_invalid_agents_warning`)

## Status

**fixed**
