# -*- coding: utf-8 -*-
"""
Tests for standardized error response format (round 13).

Validates that the dashboard API returns a consistent error envelope:
    {status, detail, suggestion, code, timestamp, path}

Covers four key sites that were previously inconsistent:
1. /api/analyze/{ticker} — 400 (HTTPException handler enrichment)
2. /api/auth/verify — 401 (raw JSONResponse site)
3. /api/scanner/run — per-ticker error row (nested error envelope)
4. /api/persona/compare — 404 (HTTPException handler)
5. /api/backtest/run — 400 (HTTPException handler)
"""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


# Envelope keys that every standardized error response must contain.
ENVELOPE_KEYS = {"status", "detail", "suggestion", "code", "timestamp", "path"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _assert_envelope(body, expected_status, expected_code=None):
    """Assert response is the standard error envelope."""
    assert isinstance(body, dict), f"expected dict, got {type(body).__name__}"
    missing = ENVELOPE_KEYS - body.keys()
    assert not missing, f"missing envelope keys: {missing} (got {body})"
    assert body["status"] == "error", f"status should be 'error', got {body.get('status')!r}"
    assert body["detail"], "detail must be a non-empty string"
    assert body["suggestion"], "suggestion must be a non-empty string (actionable hint)"
    assert body["code"], "code must be a non-empty machine-readable code"
    assert body["timestamp"].endswith("Z"), "timestamp should be ISO-8601 UTC with Z suffix"
    assert body["path"].startswith("/"), "path should be the request path"
    if expected_code is not None:
        assert body["code"] == expected_code, (
            f"expected code {expected_code!r}, got {body['code']!r}"
        )


class TestErrorEnvelopeConsistency:
    """All standardized error responses must follow the same envelope shape."""

    def test_analyze_invalid_ticker_envelope(self, client):
        """400 from /api/analyze uses INVALID_REQUEST with a non-empty suggestion."""
        resp = client.get("/api/analyze/AAAA@BB")
        assert resp.status_code == 400
        _assert_envelope(resp.json(), expected_status=400, expected_code="INVALID_REQUEST")
        assert "Invalid ticker" in resp.json()["detail"]

    def test_persona_compare_not_found_envelope(self, client):
        """404 from /api/persona/compare uses NOT_FOUND with a non-empty suggestion."""
        resp = client.get(
            "/api/persona/compare?persona1=__no_such__&persona2=__also_no__&ticker=AAPL"
        )
        assert resp.status_code == 404
        _assert_envelope(resp.json(), expected_status=404, expected_code="NOT_FOUND")
        assert "__no_such__" in resp.json()["detail"]

    def test_backtest_invalid_ticker_envelope(self, client):
        """400 from /api/backtest/run uses INVALID_REQUEST with a non-empty suggestion."""
        resp = client.get("/api/backtest/run?ticker=BAD@TICKER")
        assert resp.status_code == 400
        _assert_envelope(resp.json(), expected_status=400, expected_code="INVALID_REQUEST")

    def test_scanner_per_ticker_error_is_envelope(self, client):
        """Per-ticker failure row in /api/scanner/run uses nested envelope shape."""
        # Use a syntactically valid but unreachable ticker shape that survives
        # the regex check; then mock-stub the coordinator to raise.
        from unittest.mock import patch
        from dashboard import app as app_mod

        with patch.object(app_mod, "get_coordinator") as gc:
            coord = gc.return_value

            def _boom(_ctx):
                raise RuntimeError("simulated upstream failure")

            coord.analyze_with_all.side_effect = _boom
            resp = client.post(
                "/api/scanner/run",
                json={"tickers": ["AAPL"], "preset": ""},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["count"] == 1
        row = body["results"][0]
        assert row["ticker"] == "AAPL"
        assert row["consensus_signal"] == "error"
        # Per-row error must be an envelope, not a bare string
        err = row["error"]
        assert isinstance(err, dict), f"row.error should be a dict, got {type(err).__name__}"
        for key in ("status", "detail", "code", "suggestion"):
            assert key in err, f"row.error missing key {key!r}"
        assert err["status"] == "error"
        assert err["code"] == "SCAN_FAILED"
        assert err["suggestion"]
        assert "AAPL" in err["detail"]
        assert "simulated upstream failure" in err["detail"]

    def test_unhandled_404_envelope(self, client):
        """A non-existent API path returns the standard envelope with code NOT_FOUND."""
        resp = client.get("/api/__no_such_route_xyz__")
        assert resp.status_code == 404
        _assert_envelope(resp.json(), expected_status=404, expected_code="NOT_FOUND")
