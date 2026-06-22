# Agent3 Consensus QA — Round 2

**Focus:** P0 deadlock in dashboard singleton init

## Fix

- `dashboard/app.py`: `_singleton_init_lock = threading.RLock()` (was `Lock()`)
- Root cause: `get_coordinator()` held lock while calling `get_registry()` which tried to acquire the same lock

## Pytest

```bash
python3 -c "from dashboard.app import get_coordinator; get_coordinator()"  # was infinite hang
python3 -m pytest tests/test_consensus_compare_api_v11c.py -q
```

**Result:** 5 passed in 7.2s (API suite unblocked)
