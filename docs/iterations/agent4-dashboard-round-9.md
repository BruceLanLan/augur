# Agent4 Dashboard/UI/i18n QA — Round 9

**Result:** 282/283 passed — 1 flaky failure (98s)

## Failures

1. **`test_loop400_api_mcp_cli::test_per_ticker_analyze_429_envelope`** — transient rate-limit state under sustained back-to-back suite runs; not reproduced on isolated re-run or round 10.

## Fixes

None (flake cleared on next full run).

## Gaps

- Consider stronger rate-limit test isolation if flake recurs under CI load.
