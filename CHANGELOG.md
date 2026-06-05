# Changelog

All notable changes to augur-agents are documented in this file.

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
