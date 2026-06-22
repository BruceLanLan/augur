# Agent 5 Full-Suite Gatekeeper — Round 1

**Date:** 2026-06-22  
**Branch:** feature/v9-dev @ fdaebff  
**Command:** `python3 -m pytest tests/ -q --tb=line --ignore=tests/test_analyze_api_v12.py`

## Result

| Metric | Value |
|--------|-------|
| **Passed** | 1944 |
| **Failed** | 4 |
| **Warnings** | 1 |
| **Duration** | 846.88s (~14m) |

## Failures

1. `tests/test_e2e_pipeline.py::TestE2EAnalysisPipeline::test_dashboard_api_analyze` — `agent_count` 2 vs expected ≥18 (workspace cache pollution)
2. `tests/test_e2e_pipeline.py::TestE2EAnalysisPipeline::test_error_propagation_yfinance_unavailable` — same root cause
3. `tests/test_error_envelope_v13.py::TestErrorEnvelopeConsistency::test_scanner_per_ticker_error_is_envelope` — mock `_boom` missing `enabled_personas` kwarg under suite order (already has `**kwargs`; passes in isolation)
4. `tests/test_integration_v8.py::TestSentimentIntegration::test_sentiment_factor_applied_to_consensus` — MetaModel 50/50 blend halves sentiment delta (0.25 vs 0.5)

## Fixes applied after round 1

- `tests/conftest.py`: autouse `reset_workspace_state` fixture
- `tests/test_integration_v8.py`: patch `MetaModel.load` to isolate sentiment hook

## Delta

Baseline round — no prior delta.
