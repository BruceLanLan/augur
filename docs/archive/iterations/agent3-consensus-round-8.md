# Agent3 Consensus QA — Round 8

**Focus:** Registry + iteration consensus regression sweep

## Pytest

```bash
AUGUR_SKIP_MACRO_FETCH=1 python3 -m pytest tests/test_registry.py \
  tests/test_iteration2.py tests/test_iteration8.py tests/test_iteration11.py \
  tests/test_iteration9.py tests/test_peer_review_qa_v10_15.py \
  -k "consensus or get_consensus or analyze_with_all or weighting or Kelly" -q
```

**Result:** all selected tests passed

## Notes

- `restrict_weights_to_agents` (P0-1) verified in registry edge-case tests
- Sector hard-code boosts retained (explicit tests in iteration11); industry matrix overlay documented as future dedup (P2)
