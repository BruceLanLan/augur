# Agent1 Workspace QA — Round 6

**Result:** 252/252 passed

## Gaps (P2 fixed)

1. **`saveWorkspaceConfig` used fragile `borderColor` preset detection** — Severity: **P2**. Fix: rely on `_workspaceState.layout_preset`.
2. **`applyWorkspacePreset` did not track `committee_preset` in client state** — Severity: **P2**. Fix: copy preset `committee_preset` into `_workspaceState`.

**Re-run:** 252 passed.
