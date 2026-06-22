# -*- coding: utf-8 -*-
"""
Loop 400 — API / MCP / CLI missing scenarios, rate limits, error envelopes.

Twenty focused regression tests covering gaps found after Loop 200:
  - Standalone `augur api` error envelope parity with dashboard
  - Auth verify/login rate-limit envelopes
  - IP / per-ticker / token-bucket 429 responses
  - MCP validation helpers (no mcp package required)
  - CLI error paths and JSON output
"""

import json
import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from dashboard.app import (
    TokenBucket,
    app as dashboard_app,
    consume_endpoint_token,
    get_endpoint_bucket,
    _rate_limits,
    _rate_limit_lock,
    _ip_rate_limits,
    _ip_rate_lock,
)
from augur.cli import main
from augur.mcp_server import _validate_model_name, _validate_persona_id, _validate_ticker


ENVELOPE_KEYS = {"status", "detail", "suggestion", "code", "timestamp", "path"}


def _assert_envelope(body, expected_code=None):
    assert isinstance(body, dict)
    missing = ENVELOPE_KEYS - body.keys()
    assert not missing, f"missing envelope keys: {missing}"
    assert body["status"] == "error"
    assert body["detail"]
    assert body["suggestion"]
    assert body["code"]
    assert body["timestamp"].endswith("Z")
    assert body["path"].startswith("/")
    if expected_code is not None:
        assert body["code"] == expected_code


@pytest.fixture
def dashboard_client():
    return TestClient(dashboard_app)


@pytest.fixture
def standalone_client(monkeypatch):
    monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
    monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
    from augur.api import app as standalone_app
    return TestClient(standalone_app)


@pytest.fixture
def standalone_client_with_token(monkeypatch):
    monkeypatch.setenv("AUGUR_API_TOKEN", "loop400-secret")
    monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
    from augur.api import app as standalone_app
    return TestClient(standalone_app)


# ============ Standalone API envelopes (loops 1–5) ============

class TestStandaloneAPIEnvelopes:
    def test_invalid_ticker_returns_envelope(self, standalone_client):
        resp = standalone_client.get("/api/analyze/BAD@TICK")
        assert resp.status_code == 400
        _assert_envelope(resp.json(), expected_code="INVALID_REQUEST")

    def test_persona_not_found_returns_envelope(self, standalone_client):
        resp = standalone_client.get("/api/persona/__no_such_persona__")
        assert resp.status_code == 404
        _assert_envelope(resp.json(), expected_code="NOT_FOUND")

    def test_unknown_route_returns_envelope(self, standalone_client):
        resp = standalone_client.get("/api/__loop400_missing__")
        assert resp.status_code == 404
        _assert_envelope(resp.json(), expected_code="NOT_FOUND")

    def test_auth_required_returns_envelope_with_suggestion(self, standalone_client_with_token):
        resp = standalone_client_with_token.get("/api/personas")
        assert resp.status_code == 401
        body = resp.json()
        _assert_envelope(body, expected_code="AUTH_REQUIRED")
        assert "Bearer" in body["suggestion"]

    def test_unhandled_exception_returns_envelope(self, standalone_client, monkeypatch):
        from unittest.mock import patch
        from augur.api import app as standalone_app
        client = TestClient(standalone_app, raise_server_exceptions=False)
        with patch("augur.api.get_registry", side_effect=RuntimeError("boom")):
            resp = client.get("/api/personas")
        assert resp.status_code == 500
        _assert_envelope(resp.json(), expected_code="INTERNAL_ERROR")


# ============ Dashboard auth + rate limits (loops 6–11) ============

class TestDashboardAuthAndRateLimits:
    def test_auth_verify_401_envelope(self, monkeypatch):
        monkeypatch.setenv("AUGUR_API_TOKEN", "verify-test-token")
        monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
        client = TestClient(dashboard_app)
        resp = client.get("/api/auth/verify")
        assert resp.status_code == 401
        _assert_envelope(resp.json(), expected_code="AUTH_REQUIRED")

    def test_auth_login_429_after_burst(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
        monkeypatch.setenv("AUGUR_MULTI_USER", "1")
        monkeypatch.setenv("AUGUR_JWT_SECRET", "loop400-jwt")
        monkeypatch.setenv("HOME", str(tmp_path))
        from augur.auth import _auth_rate_limits, _auth_rate_lock, check_auth_rate_limit
        with _auth_rate_lock:
            _auth_rate_limits.clear()
        client = TestClient(dashboard_app)
        for _ in range(10):
            assert check_auth_rate_limit("testclient") is True
        resp = client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "wrongpass"},
        )
        assert resp.status_code == 429
        _assert_envelope(resp.json(), expected_code="RATE_LIMITED")
        with _auth_rate_lock:
            _auth_rate_limits.clear()

    def test_ip_rate_limit_429_envelope_and_header(self, monkeypatch):
        from dashboard import app as app_mod
        with app_mod._ip_rate_lock:
            app_mod._ip_rate_limits.clear()
        client = TestClient(dashboard_app)
        for _ in range(60):
            client.get("/api/personas")
        resp = client.get("/api/personas")
        assert resp.status_code == 429
        _assert_envelope(resp.json(), expected_code="RATE_LIMITED")
        assert resp.headers.get("X-RateLimit-Remaining") == "0"
        with app_mod._ip_rate_lock:
            app_mod._ip_rate_limits.clear()

    def test_per_ticker_analyze_429_envelope(self, dashboard_client):
        with _rate_limit_lock:
            _rate_limits.clear()
        with _ip_rate_lock:
            _ip_rate_limits.clear()
        for _ in range(31):
            dashboard_client.get("/api/analyze/LOOP?auto_fetch=false")
        resp = dashboard_client.get("/api/analyze/LOOP?auto_fetch=false")
        assert resp.status_code == 429
        _assert_envelope(resp.json(), expected_code="RATE_LIMITED")
        with _rate_limit_lock:
            _rate_limits.clear()
        with _ip_rate_lock:
            _ip_rate_limits.clear()

    @pytest.mark.parametrize("endpoint,bucket,body", [
        ("api_compare", "api_compare", {"ticker": "AAPL", "agent_ids": ["buffett", "graham"]}),
        ("api_debate", "api_debate", {"ticker": "AAPL", "agent_ids": ["buffett", "graham"]}),
        ("api_optimize", "api_optimize", {"tickers": ["AAPL"], "risk_free_rate": 0.02}),
    ])
    def test_token_bucket_endpoints_429_envelope(self, endpoint, bucket, body):
        b = get_endpoint_bucket(bucket)
        b.reset()
        for _ in range(b.capacity + 1):
            b.consume()
        resp = TestClient(dashboard_app).post(f"/api/{endpoint.replace('api_', '')}", json=body)
        assert resp.status_code == 429
        _assert_envelope(resp.json(), expected_code="RATE_LIMITED")


# ============ MCP validation (loops 12–14) ============

class TestMCPValidationHelpers:
    def test_validate_ticker_rejects_injection_chars(self):
        for bad in ("", "A" * 16, "BAD;DROP", "BTC:USD", "../x"):
            assert _validate_ticker(bad) is not None
        for good in ("AAPL", "0700.HK", "BRK.B", "BTC-USD"):
            assert _validate_ticker(good) is None

    def test_validate_persona_id_rejects_unsafe_values(self):
        for bad in ("", "bad.id", "../../x", "a" * 65):
            assert _validate_persona_id(bad) is not None
        assert _validate_persona_id("buffett") is None

    def test_validate_model_name_rejects_unsafe_values(self):
        for bad in ("", "x" * 129, "model with spaces", "model<script>"):
            assert _validate_model_name(bad) is not None
        for good in ("gpt-4o", "claude-sonnet-4-6", "deepseek-v4", "openai/gpt-4"):
            assert _validate_model_name(good) is None


# ============ CLI scenarios (loops 15–17) ============

class TestCLIScenarios:
    def test_analyze_unknown_persona_actionable_error(self):
        runner = CliRunner()
        result = runner.invoke(main, ["analyze", "AAPL", "--persona", "not-real", "--pe", "25"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "list-personas" in result.output

    def test_consensus_json_error_free_on_valid_input(self):
        runner = CliRunner()
        result = runner.invoke(main, ["consensus", "AAPL", "--pe", "25", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ticker"] == "AAPL"
        assert "consensus" in data

    def test_health_exempt_on_standalone_api_with_token(self, standalone_client_with_token):
        resp = standalone_client_with_token.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ============ Dashboard API edge envelopes (loops 18–20) ============

class TestDashboardAPIEdgeEnvelopes:
    def test_scanner_no_tickers_envelope(self, dashboard_client):
        resp = dashboard_client.post("/api/scanner/run", json={"tickers": []})
        assert resp.status_code == 400
        _assert_envelope(resp.json(), expected_code="INVALID_REQUEST")

    def test_custom_persona_invalid_id_envelope(self, dashboard_client):
        resp = dashboard_client.post(
            "/api/custom-persona",
            json={"agent_id": "BadAgent", "yaml_content": "name: x\n"},
        )
        assert resp.status_code == 400
        _assert_envelope(resp.json(), expected_code="INVALID_REQUEST")

    def test_errors_module_rate_limited_has_actionable_suggestion(self):
        from augur.errors import ERRORS, HTTP_ERROR_ENVELOPE
        err = ERRORS["rate_limited"]
        assert err["code"] == "RATE_LIMITED"
        assert "retry" in err["suggestion"].lower() or "wait" in err["suggestion"].lower()
        code, suggestion = HTTP_ERROR_ENVELOPE[429]
        assert code == "RATE_LIMITED"
        assert suggestion


class TestTokenBucketRegression:
    """Sanity check token bucket still behaves after loop-400 changes."""

    def test_consume_endpoint_token_resets_cleanly(self):
        name = "loop400_bucket_sanity"
        get_endpoint_bucket(name, capacity=2, refill_rate=0.0).reset()
        assert consume_endpoint_token(name) is True
        assert consume_endpoint_token(name) is True
        assert consume_endpoint_token(name) is False
        TokenBucket(capacity=1, refill_rate=0.0).reset()
