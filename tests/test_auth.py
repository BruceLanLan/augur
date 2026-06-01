# -*- coding: utf-8 -*-
"""Tests for API Authentication (Bearer token) feature."""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_no_token(monkeypatch):
    """Client with no AUGUR_API_TOKEN set."""
    monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
    # Re-import to ensure clean state
    from dashboard.app import app
    return TestClient(app)


@pytest.fixture
def client_with_token(monkeypatch):
    """Client with AUGUR_API_TOKEN set."""
    monkeypatch.setenv("AUGUR_API_TOKEN", "test-secret-token-123")
    from dashboard.app import app
    return TestClient(app)


class TestAuthNoToken:
    """When AUGUR_API_TOKEN is not set, API requests succeed without auth header."""

    def test_api_request_succeeds_without_auth(self, client_no_token):
        resp = client_no_token.get("/api/personas")
        assert resp.status_code == 200

    def test_health_endpoint_works(self, client_no_token):
        resp = client_no_token.get("/health")
        assert resp.status_code == 200


class TestAuthWithToken:
    """When AUGUR_API_TOKEN is set, API endpoints require Bearer token."""

    def test_api_without_header_returns_401(self, client_with_token):
        resp = client_with_token.get("/api/personas")
        assert resp.status_code == 401
        assert resp.json()["detail"] in ("Authentication required", "Authorization header is required")

    def test_api_with_correct_token_succeeds(self, client_with_token):
        resp = client_with_token.get(
            "/api/personas",
            headers={"Authorization": "Bearer test-secret-token-123"},
        )
        assert resp.status_code == 200

    def test_api_with_wrong_token_returns_401(self, client_with_token):
        resp = client_with_token.get(
            "/api/personas",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_html_pages_always_accessible(self, client_with_token):
        """HTML page routes are exempt from auth."""
        resp = client_with_token.get("/")
        assert resp.status_code == 200

        resp = client_with_token.get("/stocks")
        assert resp.status_code == 200

        resp = client_with_token.get("/personas")
        assert resp.status_code == 200

        resp = client_with_token.get("/portfolio")
        assert resp.status_code == 200

    def test_health_exempt_from_auth(self, client_with_token):
        """The /health endpoint is exempt from auth."""
        resp = client_with_token.get("/health")
        assert resp.status_code == 200
