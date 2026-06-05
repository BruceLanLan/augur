# -*- coding: utf-8 -*-
"""Round 10 Agent B: watchlist REST API tests.

Covers the happy-path and validation behavior of /api/watchlist endpoints
(add, list, remove) by mocking the cron storage layer.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from dashboard.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestWatchlistAddAPI:
    """POST /api/watchlist/add — add ticker with optional metrics."""

    def test_add_ticker_with_metrics_returns_200_and_payload(self, client):
        """Happy path: ticker + metrics -> 200 with status ok and updated list."""
        fake_config = {
            "watchlist": [{"ticker": "AAPL", "pe": 28.5, "roe": 1.2}],
            "schedule": {},
        }
        with patch("augur.cron.add_to_watchlist", return_value=fake_config) as m:
            resp = client.post(
                "/api/watchlist/add",
                json={"ticker": "AAPL", "pe": 28.5, "roe": 1.2},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["ticker"] == "AAPL"
        assert data["watchlist"] == fake_config["watchlist"]
        # Ticker should be passed uppercased
        called_ticker, called_metrics = m.call_args.args
        assert called_ticker == "AAPL"
        assert called_metrics == {"pe": 28.5, "roe": 1.2}

    def test_add_invalid_ticker_format_returns_400(self, client):
        """Invalid characters in ticker -> 400, not 500."""
        resp = client.post("/api/watchlist/add", json={"ticker": "AA@PL!"})
        assert resp.status_code == 400
        assert "Invalid ticker format" in resp.json()["detail"]

    def test_add_ticker_too_long_returns_400(self, client):
        """Ticker longer than 15 chars -> 400."""
        long_ticker = "A" * 16
        resp = client.post("/api/watchlist/add", json={"ticker": long_ticker})
        assert resp.status_code == 400
        assert "Ticker too long" in resp.json()["detail"]


class TestWatchlistRemoveAPI:
    """DELETE /api/watchlist/{ticker} — remove ticker from watchlist."""

    def test_remove_existing_ticker_returns_200(self, client):
        """Happy path: remove existing ticker -> 200 with ok status."""
        with patch("augur.cron.remove_from_watchlist", return_value=True):
            resp = client.delete("/api/watchlist/MSFT")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["ticker"] == "MSFT"
        assert "已从自选股移除" in data["message"]

    def test_remove_nonexistent_ticker_returns_404(self, client):
        """Ticker not in watchlist -> 404 with helpful detail."""
        with patch("augur.cron.remove_from_watchlist", return_value=False):
            resp = client.delete("/api/watchlist/NOPE")
        assert resp.status_code == 404
        assert "NOPE" in resp.json()["detail"]
        assert "not found" in resp.json()["detail"].lower()

    def test_remove_invalid_ticker_format_returns_400(self, client):
        """Invalid ticker characters -> 400, never reaches storage layer."""
        with patch("augur.cron.remove_from_watchlist") as m:
            resp = client.delete("/api/watchlist/AA@PL")
        assert resp.status_code == 400
        assert "Invalid ticker format" in resp.json()["detail"]
        # Storage layer must not be called when validation fails
        m.assert_not_called()
