# -*- coding: utf-8 -*-
"""Global test fixtures for augur test suite."""
import os
import tempfile
import atexit
import ipaddress
import shutil
import traceback

import pytest


# ---------------------------------------------------------------------------
# Hermetic data root: set AUGUR_DATA_DIR before ANY augur module is imported
# so that module-level get_data_dir() calls resolve to a temp directory.
# ---------------------------------------------------------------------------

_hermetic_root = tempfile.mkdtemp(prefix="augur_test_")


def _cleanup_hermetic_root():
    if os.path.isdir(_hermetic_root):
        shutil.rmtree(_hermetic_root, ignore_errors=True)


atexit.register(_cleanup_hermetic_root)


def pytest_configure(config):
    """Set AUGUR_DATA_DIR before collection so every import sees the temp root."""
    os.environ["AUGUR_DATA_DIR"] = _hermetic_root
    config.addinivalue_line(
        "markers",
        "network: test needs real network access; skipped unless "
        "AUGUR_TEST_ALLOW_NETWORK=1",
    )
    if not _network_allowed():
        _install_network_guard()


def pytest_unconfigure(config):
    _uninstall_network_guard()


# ---------------------------------------------------------------------------
# No real network by default.
#
# Every outbound connection attempt (TCP/UDP, IPv4/IPv6, including loopback)
# and every DNS lookup of a real hostname raises RuntimeError instead of
# reaching the network. Unmocked yfinance / SEC EDGAR / macro fetches used to
# try real requests and fall back, which made the suite slow (and flaky
# behind a hanging local proxy) without changing any result. AF_UNIX sockets,
# IP-literal and localhost lookups stay allowed (asyncio self-pipes).
#
# The guard is installed once for the whole session rather than per test so
# that background threads outliving a test cannot slip through. yfinance uses
# curl_cffi (libcurl opens its own sockets in C), so that is patched as well.
#
# Opt-out: mark a test ``@pytest.mark.network`` (skipped unless
# AUGUR_TEST_ALLOW_NETWORK=1), or set AUGUR_TEST_ALLOW_NETWORK=1 to disable
# the guard for the whole run. AUGUR_TEST_NETWORK_REPORT=1 prints every
# blocked attempt (test id, target, calling source line) at the end of the run.
# ---------------------------------------------------------------------------

_TRUTHY = ("1", "true", "yes")
_network_guard_originals = {}
_blocked_network_attempts = []
_current_test_nodeid = [None]


def _network_allowed():
    return os.environ.get("AUGUR_TEST_ALLOW_NETWORK", "").strip().lower() in _TRUTHY


def _network_blocked(target):
    origin = "?"
    for frame in reversed(traceback.extract_stack()[:-2]):
        parts = frame.filename.replace(os.sep, "/").split("/src/", 1)
        if len(parts) == 2 and "site-packages" not in parts[0]:
            origin = f"{parts[1]}:{frame.lineno}"
            break
    _blocked_network_attempts.append((_current_test_nodeid[0], f"{target} [{origin}]"))
    return RuntimeError(
        f"network disabled in tests: {target} "
        "(mock it, or mark the test @pytest.mark.network)"
    )


def _install_network_guard():
    import socket

    if _network_guard_originals:
        return
    orig_connect = socket.socket.connect
    orig_connect_ex = socket.socket.connect_ex
    orig_create_connection = socket.create_connection
    _network_guard_originals["socket.connect"] = orig_connect
    _network_guard_originals["socket.connect_ex"] = orig_connect_ex
    orig_getaddrinfo = socket.getaddrinfo
    _network_guard_originals["create_connection"] = orig_create_connection
    _network_guard_originals["getaddrinfo"] = orig_getaddrinfo

    def guarded_connect(self, address):
        if getattr(socket, "AF_UNIX", None) is not None and self.family == socket.AF_UNIX:
            return orig_connect(self, address)
        raise _network_blocked(address)

    def guarded_connect_ex(self, address):
        if getattr(socket, "AF_UNIX", None) is not None and self.family == socket.AF_UNIX:
            return orig_connect_ex(self, address)
        raise _network_blocked(address)

    def guarded_create_connection(address, *args, **kwargs):
        raise _network_blocked(address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        # DNS lookups go out through the system resolver, not Python sockets.
        # IP literals and localhost resolve locally and stay allowed.
        name = host.decode() if isinstance(host, bytes) else host
        if name is None or name == "localhost":
            return orig_getaddrinfo(host, *args, **kwargs)
        try:
            ipaddress.ip_address(name.split("%", 1)[0])
        except ValueError:
            raise _network_blocked(f"DNS lookup {name}") from None
        return orig_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.create_connection = guarded_create_connection
    socket.getaddrinfo = guarded_getaddrinfo

    try:
        from curl_cffi import requests as curl_requests
        from curl_cffi.curl import Curl
    except Exception:  # optional dependency (pulled in by yfinance)
        return
    _network_guard_originals["curl.Session.request"] = curl_requests.Session.request
    _network_guard_originals["curl.AsyncSession.request"] = curl_requests.AsyncSession.request
    _network_guard_originals["curl.Curl.perform"] = Curl.perform

    def guarded_curl_request(self, method, url, *args, **kwargs):
        raise _network_blocked(f"{method} {url}")

    async def guarded_curl_async_request(self, method, url, *args, **kwargs):
        raise _network_blocked(f"{method} {url}")

    def guarded_curl_perform(self, *args, **kwargs):
        raise _network_blocked("curl_cffi Curl.perform")

    curl_requests.Session.request = guarded_curl_request
    curl_requests.AsyncSession.request = guarded_curl_async_request
    Curl.perform = guarded_curl_perform


def _uninstall_network_guard():
    import socket

    if not _network_guard_originals:
        return
    socket.socket.connect = _network_guard_originals.pop("socket.connect")
    socket.socket.connect_ex = _network_guard_originals.pop("socket.connect_ex")
    socket.create_connection = _network_guard_originals.pop("create_connection")
    socket.getaddrinfo = _network_guard_originals.pop("getaddrinfo")
    if "curl.Session.request" in _network_guard_originals:
        from curl_cffi import requests as curl_requests
        from curl_cffi.curl import Curl
        curl_requests.Session.request = _network_guard_originals.pop("curl.Session.request")
        curl_requests.AsyncSession.request = _network_guard_originals.pop("curl.AsyncSession.request")
        Curl.perform = _network_guard_originals.pop("curl.Curl.perform")


def pytest_terminal_summary(terminalreporter):
    if os.environ.get("AUGUR_TEST_NETWORK_REPORT", "").strip().lower() not in _TRUTHY:
        return
    terminalreporter.section("blocked network attempts")
    if not _blocked_network_attempts:
        terminalreporter.write_line("none")
        return
    counts = {}
    for nodeid, target in _blocked_network_attempts:
        counts[(nodeid, target)] = counts.get((nodeid, target), 0) + 1
    for (nodeid, target), n in sorted(counts.items(), key=lambda kv: str(kv[0])):
        terminalreporter.write_line(f"{n:4d}  {nodeid}  ->  {target}")


@pytest.fixture(autouse=True)
def block_network(request, monkeypatch):
    """Keep tests off the real network unless explicitly opted in.

    A ``@pytest.mark.network`` test is skipped unless
    AUGUR_TEST_ALLOW_NETWORK=1 (in which case the guard is not installed at
    all). Every other test also gets AUGUR_SKIP_MACRO_FETCH=1 so consensus
    code returns default VIX/SPY regime features instead of trying yfinance;
    tests that exercise the macro fetch path delenv it themselves.
    """
    if request.node.get_closest_marker("network") is not None:
        if not _network_allowed():
            pytest.skip("needs real network; set AUGUR_TEST_ALLOW_NETWORK=1 to run")
        yield
        return
    monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")
    _current_test_nodeid[0] = request.node.nodeid
    try:
        yield
    finally:
        _current_test_nodeid[0] = None


# ---------------------------------------------------------------------------


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


@pytest.fixture(autouse=True)
def assert_hermetic_data_dir():
    """Assert that get_data_dir() returns the temp root, not ~/.augur."""
    from augur.data_dir import get_data_dir
    actual = str(get_data_dir())
    expected = os.environ.get("AUGUR_DATA_DIR", "")
    assert actual == expected, (
        f"get_data_dir() returned {actual!r}, expected {expected!r} "
        f"(AUGUR_DATA_DIR). Test isolation is broken."
    )


@pytest.fixture(autouse=True)
def reset_market_data_cache():
    """Clear augur.data's in-process MarketContext cache before each test.

    fetch_market_context() caches per ticker for three minutes. Without real
    network round-trips the whole suite finishes inside that window, so a
    test mocking the provider chain for "AAPL" would otherwise get a context
    cached by an earlier test (with different fields and no evidence items).
    """
    try:
        from augur.data import clear_cache
        clear_cache()
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def reset_issued_run_ids():
    """Forget run ids issued by earlier tests.

    RunTracker.start_run() steps ``created_at`` forward by a second while the
    id is already on disk *or* in the process-global _ISSUED_RUN_IDS set.
    Each test has its own data dir, so ids left over from a previous test
    only push this test's runs into the future. When a later run in the same
    test has a different manifest hash (no collision, no bump) it then sorts
    as older than an earlier run, and "newest run" assertions flake whenever
    tests run faster than one second apart.
    """
    try:
        import augur.run_tracker as run_tracker
        with run_tracker._ISSUED_RUN_IDS_LOCK:
            run_tracker._ISSUED_RUN_IDS.clear()
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def reset_capability_registry_singleton():
    """Reset the CapabilityRegistry singleton before each test."""
    try:
        from augur.capability import reset_capability_registry
        reset_capability_registry()
    except Exception:
        pass
    yield
    try:
        from augur.capability import reset_capability_registry
        reset_capability_registry()
    except Exception:
        pass
