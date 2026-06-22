# Agent2 Workflow QA — Round 8

**Fix:** R1-6 — partial failure on fetch

## Change

- Fetch errors captured in `results.fetch.error` + `fetch_failed` warning
- Downstream analyze/consensus/committee/debate skipped when `ctx` unavailable (`context_unavailable` warning)
- Sentiment-only chains unaffected

## Pytest

**Result:** 41 passed (no regression; fetch mocked in unit tests)

## Status

R1-6 **fixed**
