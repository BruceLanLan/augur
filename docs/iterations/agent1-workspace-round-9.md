# Agent1 Workspace QA — Round 9

**Result:** 252/252 passed

## Gaps (P2 fixed / deferred)

1. **`base.html` ticker redirect encoding** — Severity: **P2**. Fix: verified `encodeURIComponent`; added regression test `test_base_landing_redirect_encodes_ticker`.
2. **No ETag on `GET /api/workspace`** — Severity: **P3**. Deferred: performance optimization, not functional bug.
3. **Home widgets persistence separate from workspace export** — Severity: **P3**. Deferred: architectural follow-up per peer review.

**Re-run:** 252 passed.
