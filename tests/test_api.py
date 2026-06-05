# -*- coding: utf-8 -*-
"""Test Config REST API endpoints in dashboard/app.py."""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app
from augur.config import reset_config


@pytest.fixture(autouse=True)
def reset_cfg():
    """Reset config state before each test."""
    reset_config()
    yield
    reset_config()


client = TestClient(app)


class TestConfigAPI:
    def test_get_config(self):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "defaults" in data or "per_agent" in data

    def test_get_models(self):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

    def test_get_persona_config(self):
        resp = client.get("/api/config/persona/buffett")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "buffett"
        assert "model" in data

    def test_put_persona_config(self):
        resp = client.put(
            "/api/config/persona/buffett",
            json={"model": "gpt-4o"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["model"] == "gpt-4o"

        # Verify it persisted in memory
        resp2 = client.get("/api/config/persona/buffett")
        assert resp2.json()["model"] == "gpt-4o"

    def test_get_persona_schema(self):
        resp = client.get("/api/schema/persona")
        assert resp.status_code == 200
        data = resp.json()
        assert "properties" in data
        assert "agent_id" in data["properties"]

    def test_settings_page_loads(self):
        resp = client.get("/settings")
        assert resp.status_code == 200
        assert "模型配置" in resp.text


class TestCustomPersonaAPI:
    """Tests for POST /api/custom-persona endpoint."""

    def test_create_custom_persona_valid(self):
        """Valid agent_id and YAML content should succeed."""
        from pathlib import Path
        resp = client.post(
            "/api/custom-persona",
            json={
                "agent_id": "test-agent-01",
                "yaml_content": "name: Test Agent\nidentity: A test persona\n",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "test-agent-01.yaml" in data["path"]
        # Clean up the created file
        created_file = Path(data["path"])
        if created_file.exists():
            created_file.unlink()

    def test_create_custom_persona_invalid_agent_id_with_slash(self):
        """agent_id containing '/' should be rejected."""
        resp = client.post(
            "/api/custom-persona",
            json={
                "agent_id": "../../etc/malicious",
                "yaml_content": "name: Evil\n",
            },
        )
        assert resp.status_code == 400
        assert "Invalid agent_id" in resp.json()["detail"]

    def test_create_custom_persona_invalid_agent_id_with_dots(self):
        """agent_id containing '..' should be rejected."""
        resp = client.post(
            "/api/custom-persona",
            json={
                "agent_id": "some..thing",
                "yaml_content": "name: Evil\n",
            },
        )
        assert resp.status_code == 400
        assert "Invalid agent_id" in resp.json()["detail"]

    def test_create_custom_persona_invalid_agent_id_uppercase(self):
        """agent_id with uppercase letters should be rejected."""
        resp = client.post(
            "/api/custom-persona",
            json={
                "agent_id": "BadAgent",
                "yaml_content": "name: Test\n",
            },
        )
        assert resp.status_code == 400
        assert "Invalid agent_id" in resp.json()["detail"]

    def test_create_custom_persona_invalid_yaml(self):
        """Invalid YAML content should return 400."""
        resp = client.post(
            "/api/custom-persona",
            json={
                "agent_id": "valid-id",
                "yaml_content": "invalid: yaml: [unclosed bracket",
            },
        )
        assert resp.status_code == 400
        assert "Invalid YAML" in resp.json()["detail"]


class TestPersonaConfigValidation:
    """Tests for agent_id validation on PUT /api/config/persona/{id}."""

    def test_put_nonexistent_persona_returns_404(self):
        """PUT with an agent_id not in registry should return 404."""
        resp = client.put(
            "/api/config/persona/nonexistent-agent-xyz",
            json={"model": "gpt-4o"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_put_valid_persona_succeeds(self):
        """PUT with a valid agent_id should succeed."""
        resp = client.put(
            "/api/config/persona/buffett",
            json={"model": "gpt-4o"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestTickerValidation:
    """Tests for ticker format validation on /api/analyze/{ticker}."""

    def test_analyze_valid_ticker(self):
        """GET /api/analyze/AAPL should return 200."""
        resp = client.get("/api/analyze/AAPL")
        assert resp.status_code == 200

    def test_analyze_invalid_ticker_with_spaces(self):
        """GET /api/analyze/AA%20PL should return 400."""
        resp = client.get("/api/analyze/AA PL")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_analyze_invalid_ticker_with_special_chars(self):
        """GET /api/analyze/AAPL;DROP should return 400."""
        resp = client.get("/api/analyze/AAPL;DROP")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_analyze_ticker_too_long(self):
        """GET /api/analyze/ABCDEFGHIJKLMNOP (16 chars) should return 400."""
        resp = client.get("/api/analyze/ABCDEFGHIJKLMNOP")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]


class TestStandaloneAPIValidation:
    """Tests for ticker validation in the standalone augur.api module."""

    def test_analyze_valid_ticker(self):
        from fastapi.testclient import TestClient
        from augur.api import app as standalone_app
        standalone_client = TestClient(standalone_app)
        resp = standalone_client.get("/api/analyze/AAPL")
        assert resp.status_code == 200

    def test_analyze_invalid_ticker_special_chars(self):
        from fastapi.testclient import TestClient
        from augur.api import app as standalone_app
        standalone_client = TestClient(standalone_app)
        resp = standalone_client.get("/api/analyze/AAPL;DROP")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_analyze_invalid_ticker_too_long(self):
        from fastapi.testclient import TestClient
        from augur.api import app as standalone_app
        standalone_client = TestClient(standalone_app)
        resp = standalone_client.get("/api/analyze/ABCDEFGHIJKLMNOP")
        assert resp.status_code == 400


class TestScannerAPI:
    """Integration tests for POST /api/scanner/run (dashboard/app.py)."""

    def test_run_with_preset_tech_giants(self):
        """POST /api/scanner/run with preset=tech_giants should return 8 results."""
        resp = client.post(
            "/api/scanner/run",
            json={"tickers": [], "preset": "tech_giants"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 8
        assert data["count"] == 8
        first = data["results"][0]
        assert "ticker" in first
        assert "consensus_signal" in first
        assert "consensus_score" in first
        assert "agents" in first
        # Each agent entry must have agent_id, signal, score
        assert len(first["agents"]) > 0
        agent = first["agents"][0]
        assert {"agent_id", "signal", "score"} <= set(agent.keys())

    def test_run_with_custom_tickers(self):
        """POST /api/scanner/run with explicit tickers should normalize and return one entry per ticker."""
        resp = client.post(
            "/api/scanner/run",
            json={"tickers": ["aapl", "msft", "baba"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["results"]) == 3
        # Tickers should be normalized to uppercase
        returned_tickers = {r["ticker"] for r in data["results"]}
        assert returned_tickers == {"AAPL", "MSFT", "BABA"}

    def test_run_preset_overrides_tickers(self):
        """When both preset and tickers are provided, preset should take precedence."""
        resp = client.post(
            "/api/scanner/run",
            json={"tickers": ["AAPL"], "preset": "crypto"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # crypto preset has 4 tickers
        assert len(data["results"]) == 4
        returned_tickers = {r["ticker"] for r in data["results"]}
        assert "BTC-USD" in returned_tickers

    def test_run_no_tickers_returns_400(self):
        """POST /api/scanner/run with no tickers and no preset should return 400."""
        resp = client.post("/api/scanner/run", json={"tickers": []})
        assert resp.status_code == 400
        assert "No tickers" in resp.json()["detail"]

    def test_run_invalid_ticker_returns_400(self):
        """POST /api/scanner/run with a malformed ticker should return 400."""
        resp = client.post(
            "/api/scanner/run",
            json={"tickers": ["AAPL;DROP"]},
        )
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_run_too_many_tickers_returns_400(self):
        """POST /api/scanner/run with >20 tickers should return 400."""
        resp = client.post(
            "/api/scanner/run",
            json={"tickers": [f"T{i:02d}" for i in range(21)]},
        )
        assert resp.status_code == 400
        assert "Maximum 20" in resp.json()["detail"]
