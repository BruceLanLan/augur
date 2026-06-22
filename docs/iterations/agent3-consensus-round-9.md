# Agent3 Consensus QA — Round 9

**Focus:** Full scoped consensus gate

## Pytest

```bash
AUGUR_SKIP_MACRO_FETCH=1 python3 -m pytest \
  tests/test_consensus_v10_15.py tests/test_consensus_compare_api_v11c.py \
  tests/test_registry.py tests/test_iteration{2,3,7,8,9,11}.py \
  tests/test_peer_review_qa_v10_15.py \
  -k "consensus or get_consensus or analyze_with_all or weighting or build_consensus or load_global or Feedback or Kelly" -q
```

**Result:** **47 passed**, 176 deselected, 31.45s

## Deferred (P2)

- Remove duplicate sector boosts once industry matrix is fully fitted
- Regime detector v2 (hysteresis, historical `date_str`)
- Joint weight re-normalization after full per-agent overlay stack
