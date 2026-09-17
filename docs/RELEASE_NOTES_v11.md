# Augur v11.0.0-rc1 Release Notes

**Status**: Release Candidate 1
**Date**: 2026-08-12
**Base commit**: `12ff992`
**RC commit**: `5d3d9bf` (main)
**Developed by**: DSH (DeepSeek Harness) multi-agent continuous loop；后续由 owner 接管收尾

## Overview

v11 is a trustworthiness and product-foundation release. It does not add new
personas, asset classes, or dashboard pages. Instead it hardens the data
foundation, makes missing data explicit, freezes schema contracts, and adds
the infrastructure for evidence-tracked research workflows.

## New in v11

### F0 — Platform & Release Integrity

- **F0.1 Unified data root** (`src/augur/data_dir.py`): All persistent paths
  derive from `AUGUR_DATA_DIR` (default `~/.augur`). Tests use a fully
  hermetic temp root via `pytest_configure`, preventing writes to real user
  directories. CI asserts import path and version consistency.
- **F0.2 Dual-form build**: Makefile targets (`make build`, `make test-wheel`,
  `make test-sdist`, `make quality`, `make hermetic-test`) and CI workflow
  (`hermetic-smoke.yml`) test both source-editable and built-wheel installs.
- **F0.3 Replay schema v2**: `MarketContext` ownership fields are now
  `Optional[float]` (default `None`, not `0`). Missing data is explicitly
  propagated. Provider outputs include `field_availability` metadata and
  minimal `EvidenceItem` records.
- **F0.4 Release gates**: Tag/version consistency, build/publish isolation,
  and owner-approval workflow documented.
- **F0.5 Security baseline**: PBKDF2 iterations raised to 600k (OWASP 2025),
  SQLite corruption handled via atomic rename-to-backup (no silent data loss),
  CORS env var unified across Dashboard and API.

### C1 — Credibility & Calibration

- **C1.1 Rolling IC OOS harness** (`src/augur/consensus/oos_harness.py`):
  Purged walk-forward A/B evaluation with pre-registered gates. Computes
  Brier score, log loss, reliability curves, and ECE.
- **C1.2 Calibration status** (`src/augur/consensus/calibration.py`): Every
  probability output is tagged `raw` | `experimental` | `validated-calibrated`
  | `insufficient_data`. Non-validated weights are not blended by default.
- **C1.3 Provenance** (`src/augur/provenance.py`): Reports carry
  analysis-as-of, data source (live/replay/demo), freshness, persona
  enable/skip reasons, missing/degraded fields, and calibration status.
- **C1.4 Degradation observability**: Structured error recording in workflow
  step results; provider fallback failures are traceable.

### E1 — Evidence, Run & Skill Contracts

- **E1.1 Schema freeze** (`src/augur/schemas/`): `EvidenceItem` (three time
  semantics: `effective_at`/`available_at`/`retrieved_at`), `Claim`
  (classified evidence refs: `supports`/`contradicts`/`insufficient`),
  `StepResult` (typed output, provenance, content hash), `RunBundle`
  (immutable manifest, coverage stats, supersedes chain), `SkillSpec v1`
  (declarative-only, rejects executable keys).
- **E1.2 RunTracker** (`src/augur/run_tracker.py`): Wraps `run_workflow`
  phases with `StepResult` tracking, generates immutable `RunBundle` on
  completion, and supports checkpoint save/resume with input hash verification.
- **E1.3 Capability registry** (`src/augur/capability.py`): Singleton registry
  for named, typed, budget/timeout-controlled capabilities.
- **E1.4 Built-in Skills** (`src/augur/skills/`): `earnings-prep` and
  `filing-delta` SkillSpec manifests in YAML, with loader and Pydantic
  validation.
- **E1.5 MCP resources**: `augur://evidence/{id}` and `augur://runs/{id}`
  read-only resources accessible to external agents.
- **E1.6 Skill permissions** (`src/augur/skills/permissions.py`): Runtime
  enforcement of declared capabilities, resources, network domains, and file
  paths. `CitationValidator` checks claim-evidence coverage against manifest.

### P2 — Product

- **P2.1 Earnings event service** (`src/augur/earnings.py`): Detects upcoming
  earnings events from a watchlist/calendar, checks dossier readiness, and
  compares filing deltas between RunBundles.

## Known Limitations

Updated 2026-09-17 for the public release of the v11 line on `BruceLanLan/augur`.

- **Skills run built-in manifests only.** `augur skill run` / MCP
  `augur_run_skill` execute the four built-in skills; third-party manifests are
  validated but never executed. Covenant review uses reference thresholds
  unless you pass your own; earnings dates come from a local calendar file.
- **Dynamic weights are off by default.** Rolling-IC weights (`AUGUR_FORCE_RIC=1`)
  and learned weights (`AUGUR_FORCE_LEARNED=1`) have not passed a pre-registered
  out-of-sample gate; the resolved-outcome corpus is still too small.
- **Disagreement map uses a fixed dimension table.** Conflicts are derived from
  per-dimension persona scores and cite the evidence for that dimension's
  metrics; runs saved before 2026-09-17 have no factor scores and yield no
  conflict points.
- **Replay-derived artifacts predate the EDGAR market-cap unit fix.**
  `feedback/rolling_ic.json` and the factor-attribution / regime findings were
  generated while SEC EDGAR market cap was reported in raw USD instead of
  billions. They do not affect default consensus, but should be regenerated
  before being relied on.
- **Evaluation is a screen, not validation.** `augur eval` computes
  single-ticker time-series IC with overlapping forward returns, so
  significance is optimistic. `augur risk-review` is rule-based.
- `augur guidance` requires `AUGUR_EDGAR_GUIDANCE_EXTRACTION=1` and calls a paid
  LLM; PDF export requires the `[export]` extra.
- Test and build evidence: run `make verify`; CI runs the full suite on Python
  3.9 / 3.11 / 3.12 and wheel + sdist fresh-install smoke on 3.12.

## Migration from v10.x

Behaviour changes added during the 2026-09 public-release rounds:

- `augur serve` and `augur api` bind to `127.0.0.1` by default. Set
  `AUGUR_API_TOKEN` before passing `--host 0.0.0.0` (`augur api` has no auth).
- Learned (R6) weights are no longer blended into consensus unless
  `AUGUR_FORCE_LEARNED=1`.
- SEC EDGAR `market_cap` is reported in billions of USD, matching yfinance and
  every persona threshold (it was raw USD).
- `augur export` and the new `augur research-report` default to the newest run
  for the ticker; `--run-id` selects a specific one.
- Minimum Python is 3.9; the MCP server supports `mcp` 1.x and 2.x.

Original v11 migration notes:


1. Set `AUGUR_DATA_DIR` to your existing `~/.augur` for backward compatibility
   (the default behaviour is unchanged).
2. `MarketContext.insider_ownership` and `institutional_ownership` are now
   `Optional[float]` — code that assumes they are always `0` must be updated
   to handle `None`.
3. `feedback/rolling_ic.json` is still read but no longer blended into
   consensus weights by default unless marked `validated-calibrated`.
4. Old replay records without `field_availability` metadata will be rejected
   with a clear error message (not silently loaded).

## Verification

```bash
# Hermetic smoke test (3-run cycle)
make hermetic-test

# Schema + capability + skill + earnings tests (210+)
AUGUR_DATA_DIR=$(mktemp -d) PYTHONPATH=src pytest \
  tests/test_hermetic_ci.py tests/test_schemas.py \
  tests/test_run_tracker.py tests/test_capability.py \
  tests/test_skills.py tests/test_skill_permissions.py \
  tests/test_earnings.py tests/test_missingness.py \
  tests/test_oos_harness.py tests/smoke_test_*.py -v
```

## Credits

Developed by DeepSeek Harness (DSH) multi-agent continuous integration loop
across 11 commits, 77 files, 8,830 lines. Agents: A (data root), B (schemas),
C (CI), D (wheel build), E (run tracker), F (missingness), G (capabilities),
H (OOS harness), I (provenance).

---

## 补充更新 (Round 4-7, 持续循环)

### 新增模块

- `change_ledger.py` — Cross-quarter Change Ledger（6 分类变更账本）
- `citation_queue.py` — Citation Correction Queue（用户纠错队列）
- `coverage_health.py` — Coverage Health Center + Promotion Gate
- `provider_health.py` — Provider Health Dashboard
- `freshness.py` — Data Freshness Tracker
- `cache_health.py` — EDGAR 缓存新鲜度 + 大小统计
- `relative_val.py` — Relative Valuation（同行对比）
- `cost_budget.py` — Cost/Latency Budgeting
- `team_audit.py` — Team Audit 基础
- `compatibility.py` — Compatibility Badge（semver 约束）
- `prompt_eval.py` — Prompt/Model Evaluation + Factor Lab
- `adapters/openbb_adapter.py` — OpenBB schema-only adapter

### UI 新增

- `/thesis` — Thesis Journal + Decision Log + Open Questions 面板
- `/scorecard` — Post-Earnings Scorecard
- `/earnings` — Earnings Queue
- `/inbox` — Research Inbox
- `/valuation` — Valuation Lab（DCF 参数表单 + 敏感度网格）
- ⌘K 命令面板 · 暗色模式 · Evidence Graph（zoom/pan/tooltip）· 骨架屏/空状态/Toast

### 测试

249 tests 全部通过（零回归）

### Round 8+ 收尾 (2026-08-13, owner 接管)

- 版本对齐：`__version__` / `pyproject.toml` / skills / hermes-agents 统一为 `11.0.0rc1`
- ruff 收口：222 → 0 errors（修 `backtest.Any` 未定义、`workspace` UnboundLocalError、
  4 个 cli_commands 自导入、`field` 变量遮蔽、死变量、无占位符 f-string；`E402` 惰性导入全局忽略、
  `dashboard/app.py` facade per-file F401 忽略）
- 重新构建 `augur_agents-11.0.0rc1` wheel + sdist，双格式 fresh-venv smoke 通过
- 全量测试：**3422 passed + 1 skipped**
