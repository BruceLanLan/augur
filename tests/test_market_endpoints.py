# -*- coding: utf-8 -*-
"""Tests for market data endpoints (market-overview, hot-tickers, sparkline, fear-greed) and rate limiter."""

import time
import threading
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app, _check_rate_limit, _rate_limits, _rate_limit_lock
from augur.data import clear_cache


@pytest.fixture(autouse=True)
def clean_state():
    """Clear data cache and per-ticker rate limits before each test."""
    clear_cache()
    with _rate_limit_lock:
        _rate_limits.clear()
    yield
    clear_cache()
    with _rate_limit_lock:
        _rate_limits.clear()


client = TestClient(app)


# ============ Helpers ============


def _make_mock_yf():
    """Build a mock yfinance module with Ticker returning controlled data."""
    mock_yf = MagicMock()
    mock_ticker = MagicMock()

    # fast_info attributes
    mock_fi = MagicMock()
    mock_fi.last_price = 150.0
    mock_fi.previous_close = 148.0
    mock_fi.market_cap = 2_500_000_000_000.0
    mock_fi.currency = "USD"
    mock_ticker.fast_info = mock_fi

    # history returns a DataFrame-like object
    import pandas as pd
    dates = pd.date_range(end="2024-01-30", periods=30, freq="B")
    prices = [100.0 + i * 0.5 for i in range(30)]
    hist_df = pd.DataFrame({
        "Open": prices,
        "High": [p + 1 for p in prices],
        "Low": [p - 1 for p in prices],
        "Close": prices,
        "Volume": [1_000_000] * 30,
    }, index=dates)
    mock_ticker.history.return_value = hist_df

    mock_yf.Ticker.return_value = mock_ticker
    return mock_yf


# ============ Unit Test: fetch_market_overview ============


class TestFetchMarketOverviewUnit:
    """Unit test for augur.data.fetch_market_overview()."""

    @patch("augur.data._get_yfinance")
    def test_fetch_market_overview_returns_expected_structure(self, mock_get_yf):
        """Verify fetch_market_overview returns dict with as_of, items, source."""
        mock_yf = _make_mock_yf()
        mock_get_yf.return_value = mock_yf

        from augur.data import fetch_market_overview
        clear_cache()

        result = fetch_market_overview(force_refresh=True)

        assert "as_of" in result
        assert "items" in result
        assert "source" in result
        assert isinstance(result["items"], list)
        assert len(result["items"]) > 0

        # Each item should have expected keys
        item = result["items"][0]
        assert "key" in item
        assert "symbol" in item
        assert "price" in item
        assert "change_pct" in item


# ============ Integration Tests: Endpoints ============


class TestApiMarketOverview:
    """Integration test for GET /api/market-overview."""

    @patch("augur.data._get_yfinance")
    def test_market_overview_200(self, mock_get_yf):
        """Verify 200 response with items array."""
        mock_yf = _make_mock_yf()
        mock_get_yf.return_value = mock_yf
        clear_cache()

        resp = client.get("/api/market-overview?refresh=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)


class TestApiHotTickers:
    """Integration test for GET /api/hot-tickers."""

    @patch("augur.data._get_yfinance")
    def test_hot_tickers_200(self, mock_get_yf):
        """Verify 200 response with tickers array."""
        mock_yf = _make_mock_yf()
        mock_get_yf.return_value = mock_yf
        clear_cache()

        resp = client.get("/api/hot-tickers?refresh=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "tickers" in data
        assert isinstance(data["tickers"], list)


class TestApiSparkline:
    """Integration tests for GET /api/sparkline/{ticker}."""

    @patch("augur.data._get_yfinance")
    def test_sparkline_valid_ticker(self, mock_get_yf):
        """Verify sparkline returns prices array and trend field for valid ticker."""
        mock_yf = _make_mock_yf()
        mock_get_yf.return_value = mock_yf
        clear_cache()

        resp = client.get("/api/sparkline/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert "prices" in data
        assert "trend" in data
        assert isinstance(data["prices"], list)
        assert data["trend"] in ("up", "down", "flat")

    def test_sparkline_invalid_ticker_bad_chars(self):
        """Verify sparkline rejects ticker with special characters."""
        resp = client.get("/api/sparkline/AAPL;DROP")
        assert resp.status_code == 400

    def test_sparkline_invalid_ticker_too_long(self):
        """Verify sparkline rejects ticker that is too long (>15 chars)."""
        resp = client.get("/api/sparkline/ABCDEFGHIJKLMNOP")
        assert resp.status_code == 400


class TestApiFearGreed:
    """Integration test for GET /api/fear-greed."""

    @patch("augur.data._get_yfinance")
    def test_fear_greed_returns_expected_structure(self, mock_get_yf):
        """Verify fear-greed endpoint returns index, label, vix_value."""
        mock_yf = _make_mock_yf()
        # Ensure VIX item is in the market overview
        mock_get_yf.return_value = mock_yf
        clear_cache()

        resp = client.get("/api/fear-greed")
        assert resp.status_code == 200
        data = resp.json()
        assert "index" in data
        assert "label" in data
        assert "vix_value" in data or "status" in data
        # Label should be one of the known values or degraded
        if data.get("status") == "ok":
            assert data["label"] in (
                "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
            )


# ============ Rate Limiter Tests ============


class TestRateLimiterIpBased:
    """Test the IP-based rate limiter middleware (60 requests/minute per IP)."""

    def test_rate_limiter_blocks_after_60_requests(self):
        """Send 61 rapid requests and verify the 61st returns 429."""
        # Use a lightweight endpoint
        for i in range(60):
            resp = client.get("/api/personas")
            assert resp.status_code == 200, f"Request {i+1} failed with {resp.status_code}"

        # The 61st request should be rate limited
        resp = client.get("/api/personas")
        assert resp.status_code == 429
        data = resp.json()
        assert "Rate limit" in data.get("detail", "")


class TestRateLimiterPerTicker:
    """Test the per-ticker rate limiter (_check_rate_limit)."""

    def test_check_rate_limit_allows_up_to_30(self):
        """Verify _check_rate_limit allows 30 calls for the same ticker."""
        with _rate_limit_lock:
            _rate_limits.clear()

        for i in range(30):
            assert _check_rate_limit("TEST") is True, f"Call {i+1} should be allowed"

    def test_check_rate_limit_blocks_31st(self):
        """Verify _check_rate_limit returns False on 31st call."""
        with _rate_limit_lock:
            _rate_limits.clear()

        for i in range(30):
            _check_rate_limit("BLOCKED")

        # 31st should be denied
        assert _check_rate_limit("BLOCKED") is False

    def test_check_rate_limit_different_tickers_independent(self):
        """Verify rate limits are independent per ticker."""
        with _rate_limit_lock:
            _rate_limits.clear()

        for i in range(30):
            _check_rate_limit("TICKER_A")

        # TICKER_A is exhausted
        assert _check_rate_limit("TICKER_A") is False

        # TICKER_B should still be allowed
        assert _check_rate_limit("TICKER_B") is True
