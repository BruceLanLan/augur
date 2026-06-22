# Agent3 Consensus QA — Round 1

**Branch:** `feature/v9-dev`  
**Date:** 2026-06-22  
**Scope:** `src/augur/consensus/*`, registry `get_consensus`/`analyze_with_all`, feedback examples, consensus tests

## Pytest

```bash
AUGUR_SKIP_MACRO_FETCH=1 python3 -m pytest tests/test_consensus_v10_15.py \
  tests/test_consensus_compare_api_v11c.py tests/test_registry.py \
  tests/test_iteration{2,3,7,8,9,11}.py tests/test_peer_review_qa_v10_15.py \
  -k "consensus or get_consensus or analyze_with_all or weighting or Kelly or Feedback" -q
```

**Result:** 16 passed (unit); API suite **hung** on first `/api/analyze/AAPL` call (>5 min)

## Findings

| ID | Sev | Issue |
|----|-----|-------|
| R1-1 | P0 | `dashboard.app.get_coordinator()` deadlocks on first call — non-reentrant `Lock` re-entered via nested `get_registry()` |
| R1-2 | P1 | `fetch_macro_features()` hits yfinance on every `get_consensus`; Kelly property tests took 278s |
| R1-3 | P1 | Feedback only under repo `feedback/` — no `~/.augur/feedback/` override (P1-8) |
| R1-4 | P2 | Missing `agent_correlation.json.example` and `rolling_ic.json.example` |
| R1-5 | P2 | Consensus weighting invisible in API metadata |

## Action

Fix R1-1 first (blocks all dashboard analyze/consensus API tests).
