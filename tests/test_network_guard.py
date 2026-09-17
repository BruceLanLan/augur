# -*- coding: utf-8 -*-
"""The suite-wide network guard in conftest.py actually blocks connections."""
import asyncio
import os
import socket

import pytest

guard_active = pytest.mark.skipif(
    os.environ.get("AUGUR_TEST_ALLOW_NETWORK", "").strip().lower() in ("1", "true", "yes"),
    reason="network guard disabled by AUGUR_TEST_ALLOW_NETWORK",
)


@guard_active
class TestNetworkGuard:
    def test_tcp_connect_is_blocked_even_for_loopback(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            with pytest.raises(RuntimeError, match="network disabled in tests"):
                s.connect(("127.0.0.1", 9))
            with pytest.raises(RuntimeError, match="network disabled in tests"):
                s.connect_ex(("127.0.0.1", 9))

    def test_create_connection_is_blocked(self):
        with pytest.raises(RuntimeError, match="network disabled in tests"):
            socket.create_connection(("example.com", 443), timeout=1)

    def test_dns_lookup_is_blocked_but_ip_literals_resolve(self):
        with pytest.raises(RuntimeError, match="network disabled in tests"):
            socket.getaddrinfo("example.com", 443)
        assert socket.getaddrinfo("127.0.0.1", 80)
        assert socket.getaddrinfo("localhost", 80)

    def test_requests_is_blocked(self):
        requests = pytest.importorskip("requests")
        with pytest.raises(Exception) as excinfo:
            requests.get("http://example.com", timeout=1)
        assert "network disabled in tests" in repr(excinfo.value) + str(excinfo.value.__context__)

    def test_curl_cffi_is_blocked(self):
        curl_requests = pytest.importorskip("curl_cffi.requests")
        with pytest.raises(RuntimeError, match="network disabled in tests"):
            curl_requests.get("http://127.0.0.1:9", timeout=1)

    def test_unix_socketpair_still_works(self):
        a, b = socket.socketpair()
        try:
            a.sendall(b"ok")
            assert b.recv(2) == b"ok"
        finally:
            a.close()
            b.close()

    def test_asyncio_event_loop_still_works(self):
        async def main():
            await asyncio.sleep(0)
            return 42

        assert asyncio.run(main()) == 42

    def test_macro_fetch_skipped_by_default(self):
        assert os.environ.get("AUGUR_SKIP_MACRO_FETCH") == "1"


@pytest.mark.network
def test_network_marker_is_skipped_without_opt_in():
    # Only runs with AUGUR_TEST_ALLOW_NETWORK=1, where the guard is off.
    assert os.environ.get("AUGUR_TEST_ALLOW_NETWORK", "").strip().lower() in ("1", "true", "yes")
