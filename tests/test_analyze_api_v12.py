# -*- coding: utf-8 -*-
"""Round 12 / Agent A: tests for GET /api/analyze/{ticker}.

Covers:
- Valid ticker (AAPL) returns 200 with full payload
- Invalid ticker (semicolon injection) returns 400
- Manual metrics bypass auto_fetch (data_source == "manual")
- Auto-fetch failure path falls back to manual mode
- Response payload shape: status, ticker, consensus, agents, market_data
"""

import logging

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


client = TestClient(app, raise_server_exceptions=False)


class TestAnalyzeEndpoint:
    def test_analyze_valid_ticker_returns_full_payload(self):
        """GET /api/analyze/AAPL returns 200 and a well-formed payload."""
        resp = client.get("/api/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        # Top-level shape
        assert data["status"] == "ok"
        assert data["ticker"] == "AAPL"
        # Consensus + agents present
        assert "consensus" in data
        assert isinstance(data["agents"], list)
        assert data["agent_count"] >= 1
        # Each agent dict has the standard keys
        agent = data["agents"][0]
        assert {"agent_id", "signal", "score"} <= set(agent.keys())
        # Market data block present
        assert "market_data" in data
        assert "price" in data["market_data"]
        # Timestamp is ISO-8601 UTC
        assert "T" in data["timestamp"]

    def test_analyze_invalid_ticker_rejected(self):
        """Ticker with disallowed characters returns 400."""
        resp = client.get("/api/analyze/AAA;DROP")
        assert resp.status_code == 400
        body = resp.json()
        assert "Invalid ticker" in body["detail"]

    def test_analyze_manual_metrics_use_manual_data_source(self):
        """When user provides metrics, auto_fetch is skipped (data_source='manual')."""
        resp = client.get(
            "/api/analyze/AAPL",
            params={
                "price": 210.0,
                "pe": 32.0,
                "pb": 50.0,
                "roe": 1.5,
                "gross_margins": 0.46,
                "auto_fetch": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "manual"
        # The user-supplied values should be reflected in market_data
        md = data["market_data"]
        assert md["price"] == 210.0
        assert md["pe"] == 32.0
        assert md["pb"] == 50.0
        assert md["gross_margins"] == 0.46

    def test_analyze_auto_fetch_fallback_when_yfinance_unavailable(self):
        """If yfinance raises, endpoint should fall back to manual with data_note."""
        from unittest.mock import patch

        def _raise(_ticker):
            raise RuntimeError("yfinance offline")

        with patch("dashboard.app.fetch_market_context", _raise, create=True):
            # Patch via the module's lazy import by patching the symbol on augur.data
            import augur.data as augur_data_mod
            with patch.object(augur_data_mod, "fetch_market_context", _raise):
                resp = client.get(
                    "/api/analyze/ZZZZ",
                    params={"auto_fetch": True},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "fallback"
        # Fallback response surfaces the data_note to the client
        assert data.get("data_note") == "Auto-fetch failed, using provided parameters"
        # Agents still ran with the empty manual context
        assert data["agent_count"] >= 1

    def test_analyze_error_path_coordinator_raises_returns_500(self, caplog):
        """If the coordinator raises, the endpoint returns 500."""
        from unittest.mock import patch

        class _BoomCoord:
            def analyze_with_all(self, ctx):
                raise RuntimeError("coordinator exploded")

            def get_consensus(self, *args, **kwargs):
                raise RuntimeError("consensus exploded")

        with caplog.at_level(logging.ERROR, logger="dashboard.app"):
            with patch("dashboard.app.get_coordinator", return_value=_BoomCoord()):
                resp = client.get(
                    "/api/analyze/ERRO",
                    params={"auto_fetch": False},
                )

        # The unhandled exception bubbles up as 500
        assert resp.status_code == 500
        # Log captured
        assert any(
            r.levelno >= logging.ERROR
            for r in caplog.records
            if r.name == "dashboard.app"
        )
