# Agent4 Dashboard/UI/i18n QA — Round 1

**Result:** 281 passed → 2 failed → fixed → **283/283 passed** (68s)

## Failures (fixed)

1. **`test_global_css_loop400::test_index_uses_compact_not_inline_border_reset`** — `index.html` "How it works" section used bare `section-title` instead of `section-title compact`. Fix: add `compact` class to match layout.css pattern used on scanner/compare pages.

2. **`test_error_envelope_v13::test_scanner_per_ticker_error_is_envelope`** — mock `_boom(_ctx)` rejected `enabled_personas=` kwarg from `analyze_with_all`, surfacing TypeError instead of simulated RuntimeError. Fix: accept `**kwargs` in test mock.

## Scope verified

- `dashboard/app.py` routes (HTML + API)
- `index.html`, i18n.js (4 langs via test_iteration12)
- test_global_css*, test_dashboard*, test_loop400*, test_error_envelope*

## Gaps

None remaining after fixes.
