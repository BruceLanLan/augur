# Agent1 Workspace QA — Round 3

**Result:** 248/248 passed

## Gaps (P1/P2 fixed)

1. **Profile GET slug validation inconsistent** — Severity: **P2**. Fix: `api_get_workspace_profile` uses `normalize_profile_name`; invalid slugs return 404.
2. **Invalid slug PUT returned unclear errors** — Severity: **P2**. Fix: `PUT` returns 400 for invalid profile names; test added.

**Re-run:** 248 passed.
