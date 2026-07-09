# -*- coding: utf-8 -*-
"""Global test fixtures for augur test suite."""
import pytest


@pytest.fixture(autouse=True)
def reset_workspace_state():
    """Reset workspace in-memory cache before/after each test to prevent cross-test pollution."""
    try:
        from augur.workspace import reset_workspace_cache
        reset_workspace_cache()
    except Exception:
        pass
    yield
    try:
        from augur.workspace import reset_workspace_cache
        reset_workspace_cache()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def isolate_learning_engine(tmp_path, monkeypatch):
    """Point the LearningEngine singleton at a per-test temp file.

    augur.registry._get_learning_engine() is a process-global singleton
    that, absent this fixture, resolves to the real
    ~/.augur/learned_weights.json. Since record_prediction() now persists
    immediately (docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md debt 3 — R3),
    any test that exercises real consensus computation without explicitly
    mocking this singleton will genuinely write synthetic test predictions
    into the user's real application data file. Before that fix this was a
    latent, invisible gap (leaked state only lived in memory and vanished
    at process exit); it is not invisible anymore, so every test gets an
    isolated engine unconditionally rather than relying on each test to
    remember to mock it individually.
    """
    import augur.registry as registry
    from augur.learning import LearningEngine
    test_engine = LearningEngine(weights_path=tmp_path / "learned_weights.json")
    monkeypatch.setattr(registry, "_learning_engine", test_engine)
    yield


@pytest.fixture(autouse=True)
def disable_edgar_overlay_by_default(monkeypatch):
    """Make augur.data._overlay_edgar_fundamentals() a no-op by default.

    fetch_market_context() now overlays SEC EDGAR fundamentals for any
    ticker with a real CIK and a positive price (Phase B, B1 — see
    docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md). Since "AAPL" is the most
    common test fixture ticker in this suite and genuinely has a CIK,
    tests that call the real fetch_market_context() without mocking this
    would otherwise make a real network call to SEC EDGAR on every run and
    silently overwrite mocked yfinance field values with real EDGAR data
    (confirmed directly: a pre-existing test asserting a mocked
    market_cap=3000.0 started failing with a real ~$2.8T EDGAR-sourced
    value once the overlay was wired in). A test that specifically wants to
    exercise the overlay re-patches fetch_edgar_fundamentals locally, which
    takes precedence over this default within that test's scope.
    """
    from augur.consensus import edgar_fundamentals
    monkeypatch.setattr(
        edgar_fundamentals, "fetch_edgar_fundamentals",
        lambda ticker, as_of_date, price=None: {"insufficient": True},
    )
    yield


@pytest.fixture(autouse=True)
def disable_watchlist_fetch_delay(monkeypatch):
    """Zero out the inter-ticker delay in run_watchlist_analysis() for tests.

    See cron.py's _WATCHLIST_FETCH_DELAY_SECONDS docstring: production runs
    sleep between watchlist tickers to avoid tripping yfinance's rate limit.
    Tests mock fetch_market_context so no real network happens either way,
    but a real time.sleep() would still slow down every multi-ticker
    watchlist test for no benefit.
    """
    import augur.cron as cron
    monkeypatch.setattr(cron, "_WATCHLIST_FETCH_DELAY_SECONDS", 0.0)
    yield


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
