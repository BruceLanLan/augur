# Agent1 Workspace QA — Round 2

**Result:** 248/248 passed (pre-fix baseline after round-1 doc)

## Gaps (P1 fixed)

1. **Missing `PUT /api/workspace/profiles/{name}`** — Severity: **P1**. Fix: added endpoint wired to `save_profile()`; tests in `test_workspace_profiles_v10_15.py`.

**Re-run:** 248 passed after fix.
