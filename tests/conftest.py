# -*- coding: utf-8 -*-
"""Global test fixtures for augur test suite."""
import pytest


@pytest.fixture(autouse=True)
def reset_ip_rate_limits():
    """Clear IP-based rate limit state before each test to prevent cross-test pollution."""
    from dashboard.app import _ip_rate_limits, _ip_rate_lock
    with _ip_rate_lock:
        _ip_rate_limits.clear()
    # Also clear the per-endpoint token bucket state so rate-limit tests
    # start from a known-good (full bucket) baseline.
    try:
        from dashboard.app import _endpoint_buckets, _endpoint_buckets_lock
        with _endpoint_buckets_lock:
            for _bucket in _endpoint_buckets.values():
                _bucket.reset()
    except Exception:
        # Don't fail collection if the symbol is absent on an older checkout.
        pass
    yield
    with _ip_rate_lock:
        _ip_rate_limits.clear()
