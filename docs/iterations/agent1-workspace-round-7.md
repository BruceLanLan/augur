# Agent1 Workspace QA — Round 7

**Result:** 252/252 passed

## Gaps (P1 fixed)

1. **Saving workspace did not clear landing-route session flag** — Severity: **P1**. Fix: `saveWorkspaceConfig` clears `augur-workspace-routed` so default page/ticker changes apply on next `/` visit.
2. **Non-active profile edit path untested end-to-end** — Severity: **P2**. Fix: added `test_put_non_active_profile_without_switching` in `test_peer_review_qa_v10_15.py`.

**Re-run:** 252 passed.
