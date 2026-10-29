# Agent3 Consensus QA — Round 7

**Focus:** API consensus test reliability

## Fix

- `tests/test_consensus_compare_api_v11c.py`:
  - Autouse fixture: `AUGUR_SKIP_MACRO_FETCH`, stub macro, limit to 3 personas via `get_enabled_personas` patch
  - Manual metrics query (`auto_fetch=false`) to avoid yfinance on context fetch

## Pytest

```bash
AUGUR_SKIP_MACRO_FETCH=1 python3 -m pytest tests/test_consensus_compare_api_v11c.py -v
```

**Result:** 5 passed in 7.2s; real `get_consensus` still exercised end-to-end
