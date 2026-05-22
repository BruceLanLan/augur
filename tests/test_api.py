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
