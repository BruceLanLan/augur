# Agent1 Workspace QA — Round 8

**Result:** 252/252 passed

## Gaps (P2 fixed)

1. **`save_profile` missing-profile error untested** — Severity: **P2**. Fix: `test_save_profile_unknown_raises` in module tests.
2. **Settings save sessionStorage guard untested** — Severity: **P2**. Fix: `TestWorkspaceSettingsHTML.test_save_clears_landing_route_session_flag`.

**Re-run:** 252 passed.
