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
