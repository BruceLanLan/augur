# -*- coding: utf-8 -*-
"""Test dashboard error handling and HTTP status codes.

Validates that the dashboard API endpoints return proper error responses
(400, 404, 500) for invalid inputs, and that all HTML pages load correctly.
"""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient to avoid repeated startup overhead."""
    return TestClient(app)


class TestInvalidTickerFormats:
    """Test that invalid ticker formats return 400 with proper error messages."""

    def test_path_traversal_ticker(self, client):
        """Ticker with special chars like @ should return 400."""
        # Characters outside [A-Za-z0-9.-] are rejected
        resp = client.get("/api/analyze/A@B#C$D")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_script_injection_ticker(self, client):
        """GET /api/analyze/<script> should return 400."""
        resp = client.get("/api/analyze/<script>")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_very_long_ticker(self, client):
        """GET /api/analyze/AAAAAAAAAAAAAAAA (16 chars) should return 400."""
        long_ticker = "A" * 16
        resp = client.get(f"/api/analyze/{long_ticker}")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_ticker_with_semicolon(self, client):
        """GET /api/analyze/AAPL;DROP should return 400."""
        resp = client.get("/api/analyze/AAPL;DROP")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_ticker_with_spaces(self, client):
        """GET /api/analyze/AA PL should return 400."""
        resp = client.get("/api/analyze/AA PL")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]


class TestHTMLPagesLoad:
    """Test that all dashboard HTML pages load with 200 status."""

    @pytest.mark.parametrize("path", [
        "/",
        "/personas",
        "/stocks",
        "/signals",
        "/settings",
        "/create-persona",
        "/backtest",
    ])
    def test_page_loads(self, client, path):
        """All HTML pages should return 200."""
        resp = client.get(path)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")


class TestAnalyzeEndpoint:
    """Test /api/analyze with various parameter combinations."""

    def test_analyze_with_auto_fetch_false_zero_metrics(self, client):
        """GET /api/analyze/TEST with auto_fetch=false and zero metrics returns valid response."""
        resp = client.get("/api/analyze/TEST?auto_fetch=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "TEST"
        assert data["data_source"] == "manual"
        assert "consensus" in data
        assert "agents" in data
        assert data["agent_count"] > 0


class TestWatchlistErrors:
    """Test watchlist endpoint error handling."""

    def test_watchlist_add_invalid_ticker_special_chars(self, client):
        """POST /api/watchlist/add with invalid ticker returns 400."""
        resp = client.post("/api/watchlist/add", json={"ticker": "<script>alert(1)</script>"})
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_watchlist_add_ticker_too_long(self, client):
        """POST /api/watchlist/add with ticker longer than 15 chars returns 400."""
        resp = client.post("/api/watchlist/add", json={"ticker": "A" * 16})
        assert resp.status_code == 400
        assert "too long" in resp.json()["detail"].lower() or "Ticker" in resp.json()["detail"]


class TestPersonaEndpoint:
    """Test persona endpoint error handling."""

    def test_nonexistent_persona_returns_404(self, client):
        """GET /api/persona/nonexistent returns 404 with proper error detail."""
        resp = client.get("/api/persona/nonexistent-agent-xyz-99")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestCustomPersonaErrors:
    """Test custom persona creation error handling."""

    def test_invalid_yaml_returns_400(self, client):
        """POST /api/custom-persona with invalid YAML returns 400."""
        resp = client.post(
            "/api/custom-persona",
            json={
                "agent_id": "valid-id",
                "yaml_content": "invalid: yaml: [unclosed bracket",
            },
        )
        assert resp.status_code == 400
        assert "Invalid YAML" in resp.json()["detail"]

    def test_invalid_agent_id_uppercase_returns_400(self, client):
        """POST /api/custom-persona with uppercase agent_id returns 400."""
        resp = client.post(
            "/api/custom-persona",
            json={
                "agent_id": "BadAgent",
                "yaml_content": "name: Test\nidentity: A test persona\n",
            },
        )
        assert resp.status_code == 400
        assert "Invalid agent_id" in resp.json()["detail"]

    def test_invalid_agent_id_with_spaces_returns_400(self, client):
        """POST /api/custom-persona with spaces in agent_id returns 400."""
        resp = client.post(
            "/api/custom-persona",
            json={
                "agent_id": "bad agent",
                "yaml_content": "name: Test\nidentity: A test persona\n",
            },
        )
        assert resp.status_code == 400
        assert "Invalid agent_id" in resp.json()["detail"]
