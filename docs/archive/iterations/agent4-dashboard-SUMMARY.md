# Agent4 Dashboard/UI/i18n — 10-Round QA Summary

**Branch:** `feature/v9-dev`  
**Scope:** dashboard routes, `index.html`, i18n (4 langs), iteration12 keys, global CSS, dashboard, loop400, error envelope tests  
**Final status:** **283/283 green** (final verification)

## Round scorecard

| Round | Passed | Failed | Notes |
|-------|--------|--------|-------|
| 1 | 281→283 | 2→0 | Fixed known failures |
| 2 | 283 | 0 | — |
| 3 | 283 | 0 | — |
| 4 | 283 | 0 | — |
| 5 | 283 | 0 | — |
| 6 | 283 | 0 | — |
| 7 | 283 | 0 | — |
| 8 | 283 | 0 | — |
| 9 | 282 | 1 | Transient `test_per_ticker_analyze_429_envelope` flake |
| 10 | 283 | 0 | — |

## Fixes applied (round 1)

1. **`dashboard/templates/index.html`** — "How it works" heading now uses `section-title compact` (matches `layout.css` and `test_global_css_loop400`).

2. **`tests/test_error_envelope_v13.py`** — scanner mock `_boom` accepts `**kwargs` so `analyze_with_all(ctx, enabled_personas=…)` surfaces the intended `RuntimeError` in the per-ticker error envelope.

## Observations

- All dashboard HTML pages, static assets, i18n key parity, error envelopes, and loop400 core/API tests pass after fixes.
- One rate-limit test flaked once under sustained back-to-back full-suite runs (round 9); immediate re-run passed. No code change required.
- urllib3/LibreSSL warning is environmental, not a dashboard defect.

## Files changed

- `dashboard/templates/index.html`
- `tests/test_error_envelope_v13.py`
- `docs/iterations/agent4-dashboard-round-{1..10}.md`
- `docs/iterations/agent4-dashboard-SUMMARY.md`
