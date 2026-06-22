# Agent1 Workspace QA — Round 4

**Result:** 248/248 passed

## Gaps (P1 fixed)

1. **`deleteWorkspaceProfile()` only blocked `default`, not active profile** — Severity: **P1**. Fix: compare selected name to `_workspaceActiveProfile` before DELETE.

**Re-run:** 248 passed.
