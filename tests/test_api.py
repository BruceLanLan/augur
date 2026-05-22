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
