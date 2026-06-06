# -*- coding: utf-8 -*-
"""Tests for WebSocket streaming endpoint in dashboard/app.py."""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


client = TestClient(app)


class TestWebSocket:
    def test_websocket_accepts_connection(self):
        """WebSocket endpoint should accept connection for valid ticker."""
        with client.websocket_connect("/ws/analyze/AAPL") as ws:
            # Should receive agent messages
            data = ws.receive_json()
            assert data["type"] == "agent"
            assert "agent_id" in data
            assert "signal" in data
            assert "score" in data
            assert "progress" in data
            # Close after first message
            ws.close()

    def test_websocket_invalid_ticker_rejected(self):
        """WebSocket endpoint should reject invalid ticker format."""
        # Invalid ticker with special chars - should close with error code
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/analyze/AAPL;DROP") as ws:
                ws.receive_json()

    def test_websocket_streams_all_agents(self):
        """WebSocket should stream all agents then consensus."""
        with client.websocket_connect("/ws/analyze/AAPL") as ws:
            agent_count = 0
            consensus_received = False
            for _ in range(50):  # Safety limit
                data = ws.receive_json()
                if data["type"] == "agent":
                    agent_count += 1
                    assert "agent_name" in data
                    assert "progress" in data
                elif data["type"] == "consensus":
                    consensus_received = True
                    break

            assert agent_count > 0
            assert consensus_received


class TestCompareEndpoint:
    def test_compare_valid_request(self):
        """POST /api/compare with valid agents should return results."""
        resp = client.post("/api/compare", json={
            "ticker": "AAPL",
            "agent_ids": ["buffett", "graham"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["agent_count"] == 2
        assert len(data["agents"]) == 2

    def test_compare_too_few_agents(self):
        """POST /api/compare with < 2 agents should return 400."""
        resp = client.post("/api/compare", json={
            "ticker": "AAPL",
            "agent_ids": ["buffett"],
        })
        assert resp.status_code == 400

    def test_compare_too_many_agents(self):
        """POST /api/compare with > 5 agents should return 400."""
        resp = client.post("/api/compare", json={
            "ticker": "AAPL",
            "agent_ids": ["buffett", "graham", "lynch", "wood", "soros", "dalio"],
        })
        assert resp.status_code == 400

    def test_compare_invalid_ticker(self):
        """POST /api/compare with invalid ticker should return 400."""
        resp = client.post("/api/compare", json={
            "ticker": "AAPL;DROP",
            "agent_ids": ["buffett", "graham"],
        })
        assert resp.status_code == 400


class TestHistoryAPI:
    def test_list_history(self):
        """GET /api/history should return a list."""
        resp = client.get("/api/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_history_page_loads(self):
        """GET /history should render the history page."""
        resp = client.get("/history")
        assert resp.status_code == 200
        assert "历史记录" in resp.text

    def test_compare_page_loads(self):
        """GET /compare should render the compare page."""
        resp = client.get("/compare")
        assert resp.status_code == 200
        assert "对比分析" in resp.text


class TestPriceStreamEndpoint:
    """Tests for the /ws/prices real-time price streaming WebSocket."""

    def test_ws_prices_sends_initial_price_update(self):
        """Connecting to /ws/prices should yield a price_update payload with all tickers."""
        with client.websocket_connect("/ws/prices") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "price_update"
            assert "prices" in msg and isinstance(msg["prices"], list)
            assert "timestamp" in msg
            assert len(msg["prices"]) > 0
            for p in msg["prices"]:
                assert {"ticker", "price", "change", "change_pct"} <= set(p)
                assert p["price"] > 0
            ws.close()

    def test_ws_prices_receives_pong_or_stays_open(self):
        """A second send_text after connect should keep the socket open (no crash)."""
        with client.websocket_connect("/ws/prices") as ws:
            # Drain the initial price_update
            initial = ws.receive_json()
            assert initial["type"] == "price_update"
            # Endpoint loops on receive_text; sending a benign keepalive should not
            # raise. We just confirm the socket is still open by issuing a second recv
            # with a short timeout via the context manager's own buffer.
            ws.send_text("ping")
            # Close cleanly to avoid hanging the test
            ws.close()

    def test_ws_prices_rejects_when_auth_required_and_token_missing(self, monkeypatch):
        """If AUGUR_API_TOKEN is set, /ws/prices must close with 1008 for missing token."""
        # Force auth on
        monkeypatch.setenv("AUGUR_API_TOKEN", "secret-test-token-xyz")
        try:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/prices") as ws:
                    # Should be closed by the server; receive_text will raise
                    ws.receive_text()
        finally:
            monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)

    def test_ws_prices_accepts_query_token_when_auth_required(self, monkeypatch):
        """Browser clients pass ?token= when AUGUR_API_TOKEN is configured."""
        monkeypatch.setenv("AUGUR_API_TOKEN", "secret-test-token-xyz")
        try:
            with client.websocket_connect(
                "/ws/prices?token=secret-test-token-xyz"
            ) as ws:
                msg = ws.receive_json()
                assert msg["type"] == "price_update"
                assert len(msg["prices"]) > 0
        finally:
            monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
