# -*- coding: utf-8 -*-
"""Round 10 Agent E: /api/backtest/run endpoint tests.

Exercises the four key behaviors of the demo backtest route:

  1. basic happy-path GET returns a well-formed payload
  2. missing ticker query param falls back to the default "AAPL"
  3. invalid ticker characters yield a 400 (not 500)
  4. invalid days values are clamped server-side to the [5, 365] range
"""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestApiBacktestRun:
    """Validate /api/backtest/run end-to-end behavior."""

    def test_basic_success_returns_well_formed_payload(self, client):
        """Default params return status=ok with metrics and signals timeline."""
        resp = client.get("/api/backtest/run")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Core envelope
        assert data["status"] == "ok"
        assert data["ticker"] == "AAPL"  # default ticker
        assert data["days"] == 30         # default days
        assert data["strategy"] == "equal_weight"
        assert isinstance(data["initial_capital"], (int, float))

        # Metrics block
        metrics = data["metrics"]
        for key in ("annualized_return", "max_drawdown", "sharpe_ratio", "win_rate"):
            assert key in metrics, f"missing metric: {key}"

        # Agent IC list + signals timeline present (may be empty lists)
        assert isinstance(data["agent_ics"], list)
        assert isinstance(data["signals_timeline"], list)
        assert isinstance(data["total_records"], int)
        assert "summary" in data

    def test_missing_ticker_param_uses_default(self, client):
        """No ticker query param at all -> route uses 'AAPL' default (not 422)."""
        # FastAPI would normally 422 on a missing required param, but ticker
        # has a default, so the route should accept and return 200.
        resp = client.get("/api/backtest/run?days=10")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"
        assert resp.json()["days"] == 10

    def test_invalid_ticker_returns_400(self, client):
        """Ticker with illegal characters -> 400 with detail, never 500."""
        # Space, slash, and dollar sign all fail the [A-Za-z0-9.-]{1,15} regex.
        for bad in ("AA PL", "AA/PL", "AA$PL"):
            resp = client.get(f"/api/backtest/run?ticker={bad}")
            assert resp.status_code == 400, (
                f"ticker={bad!r} should be rejected, got {resp.status_code}"
            )
            detail = resp.json().get("detail", "")
            assert "ticker" in detail.lower() or "invalid" in detail.lower()

    def test_invalid_days_are_clamped_to_range(self, client):
        """days<5 is bumped to 5; days>365 is capped to 365 (never 500)."""
        # Too few
        resp_low = client.get("/api/backtest/run?ticker=AAPL&days=1")
        assert resp_low.status_code == 200
        assert resp_low.json()["days"] == 5

        # Too many
        resp_high = client.get("/api/backtest/run?ticker=AAPL&days=9999")
        assert resp_high.status_code == 200
        assert resp_high.json()["days"] == 365

        # In-range value is preserved
        resp_ok = client.get("/api/backtest/run?ticker=MSFT&days=60")
        assert resp_ok.status_code == 200
        assert resp_ok.json()["days"] == 60
        assert resp_ok.json()["ticker"] == "MSFT"
