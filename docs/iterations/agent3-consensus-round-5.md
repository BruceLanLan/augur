# Agent3 Consensus QA — Round 5

**Focus:** Macro fetch performance + CI determinism

## Fix

- `src/augur/consensus/macro_features.py`:
  - In-process 5-minute TTL cache
  - `AUGUR_SKIP_MACRO_FETCH=1` returns defaults immediately
  - `clear_macro_cache()` for tests

## Pytest

Kelly property suite (`test_iteration11.py -k Kelly`): **31s** (was 278s)

```bash
AUGUR_SKIP_MACRO_FETCH=1 python3 -m pytest tests/test_iteration11.py -k Kelly -q
```

**Result:** 4 passed in 31s
