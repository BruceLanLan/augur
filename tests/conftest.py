# -*- coding: utf-8 -*-
"""Global test fixtures for augur test suite."""
import pytest


@pytest.fixture(autouse=True)
def reset_ip_rate_limits():
    """Clear IP-based rate limit state before each test to prevent cross-test pollution."""
    from dashboard.app import _ip_rate_limits, _ip_rate_lock
    with _ip_rate_lock:
        _ip_rate_limits.clear()
    yield
    with _ip_rate_lock:
        _ip_rate_limits.clear()
