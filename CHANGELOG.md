# Changelog

All notable changes to augur-agents are documented in this file.

## [8.2.1] - 2026-06-06

Loop 200 review patch. 200-round multi-agent code review + UX walkthrough on top of v8.2.0.

### Fixed
- **Layout:** Sidebar and main content aligned via CSS Grid (`240px + 1fr`, gap 0); collapsed sidebar uses unified `--sidebar-width` token.
- **Report contrast:** Light-mode parchment + pale text unreadable; added `--report-*` semantic tokens and theme-aware SVG via `reportThemeColor()`.
- **Backend:** Price-series NaN/Inf sanitization, consensus tie → `NEUTRAL`, coverage-confidence normalization, persona YAML bool weights, sample-insufficient report messaging.
- **Auth:** WebSocket `/ws/prices?token=` validation; Dashboard fetch/WebSocket interceptors aligned with `augur.auth`; `GET /api/auth/config` discovery endpoint.

### Changed
- **UX / i18n / a11y:** Global `_t()` export, progress/copy i18n keys, empty-state parity across portfolio/compare/history/debate, 44px touch targets, reduced-motion support, stocks page `data-i18n`, mobile table scroll hints.
- **Pages:** Settings (redundant PUT removed), Scanner (explicit event args), Signals (reordered flow), Backtest (min capital validation), index onboarding/AAPL CTA, partial `data_error` surfacing.

### Notes
- Tests: **1362 passed** (up from ~1177 in v8.2.0).
- Review reports: [`docs/LOOP_200_REPORT.md`](docs/LOOP_200_REPORT.md) (complete) · [`docs/LOOP_400_REPORT.md`](docs/LOOP_400_REPORT.md) (partial — stash recovery pending).
- README screenshots refreshed for v8.2.1 grid layout and report contrast (see `scripts/capture_readme_screenshots.py`).

## [8.2.0] - 2026-06-06

v8.2.0 release. Version bump from 8.1.0 to 8.2.0.

### Added
- AI Chat with 11 personas, Portfolio Optimizer (Markowitz), Master Compare,
  Debate Mode, History, Leaderboard (dashboard pages).
- LearningEngine (IC-based weight auto-tuning), SentimentAnalyzer (social
  sentiment fusion), WebSocket price streaming at `/ws/prices`, RulesEngine
  (DSL alerts with multi-channel notifications).
- HD-2D design system: `ExecCard`, `OracleSays`, `ScorecardGrid` components,
  layout spacing fix (240px gap), adaptive color variables
  (`var(--signal-buy)`, `var(--signal-sell)`), responsive breakpoints
  (768px / 480px), bilingual number/date formatting.
- Persona audit, makefile, pyproject polish, and analyzer/ws prices work
  (rounds 11–12).

### Changed
- Bumped package version from 8.1.0 to 8.2.0 in `src/augur/__init__.py` and `pyproject.toml`.
- Added this `CHANGELOG.md` to document release history.

### Notes
- No breaking changes vs 8.1.0.
- All 1177 existing tests remain green.

## [8.1.0] - 2026-06-06

Round 7 release. Rate limiting, data error UX, agent registry, dashboard a11y,
route validation, branded 404/500, chat docstrings, learning log, rules YAML.
