# -*- coding: utf-8 -*-
"""Tests for API Authentication (Bearer token + JWT multi-user)."""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_no_token(monkeypatch):
    """Client with no auth env vars set."""
    monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
    monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
    from dashboard.app import app
    return TestClient(app)


@pytest.fixture
def client_with_token(monkeypatch):
    """Client with AUGUR_API_TOKEN set."""
    monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
    monkeypatch.setenv("AUGUR_API_TOKEN", "test-secret-token-123")
    from dashboard.app import app
    return TestClient(app)


@pytest.fixture
def client_multi_user(monkeypatch, tmp_path):
    """Client with multi-user JWT auth enabled."""
    monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
    monkeypatch.setenv("AUGUR_MULTI_USER", "1")
    monkeypatch.setenv("AUGUR_JWT_SECRET", "test-jwt-secret-for-pytest")
    monkeypatch.setenv("HOME", str(tmp_path))
    from augur.users import UserManager
    UserManager().create_user("testuser", "password123")
    from dashboard.app import app
    return TestClient(app)


class TestAuthNoToken:
    """When auth is not configured, API requests succeed without auth header."""

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

    def test_verify_endpoint_accepts_valid_token(self, client_with_token):
        resp = client_with_token.get(
            "/api/auth/verify",
            headers={"Authorization": "Bearer test-secret-token-123"},
        )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "token"

    def test_html_pages_always_accessible(self, client_with_token):
        resp = client_with_token.get("/")
        assert resp.status_code == 200

        resp = client_with_token.get("/stocks")
        assert resp.status_code == 200

    def test_health_exempt_from_auth(self, client_with_token):
        resp = client_with_token.get("/health")
        assert resp.status_code == 200


class TestAuthMultiUserJWT:
    """When AUGUR_MULTI_USER=1, API endpoints accept JWT from login."""

    def test_api_requires_jwt(self, client_multi_user):
        resp = client_multi_user.get("/api/personas")
        assert resp.status_code == 401

    def test_login_returns_jwt(self, client_multi_user):
        resp = client_multi_user.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "password123"},
        )
        assert resp.status_code == 200
        assert resp.json()["token"]

    def test_api_accepts_jwt(self, client_multi_user):
        login = client_multi_user.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "password123"},
        )
        token = login.json()["token"]
        resp = client_multi_user.get(
            "/api/personas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_auth_me_returns_user(self, client_multi_user):
        login = client_multi_user.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "password123"},
        )
        token = login.json()["token"]
        resp = client_multi_user.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["user_id"] == 1

    def test_verify_endpoint_accepts_jwt(self, client_multi_user):
        login = client_multi_user.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "password123"},
        )
        token = login.json()["token"]
        resp = client_multi_user.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "jwt"


class TestWebSocketAuth:
    """WebSocket auth via header or ?token= query param."""

    def test_ws_open_without_token(self, client_no_token):
        with client_no_token.websocket_connect("/ws/analyze/AAPL") as ws:
            data = ws.receive_json()
            assert data["type"] == "agent"

    def test_ws_rejects_without_token_when_configured(self, client_with_token):
        with pytest.raises(Exception):
            with client_with_token.websocket_connect("/ws/analyze/AAPL") as ws:
                ws.receive_json()

    def test_ws_accepts_query_token(self, client_with_token):
        with client_with_token.websocket_connect(
            "/ws/analyze/AAPL?token=test-secret-token-123"
        ) as ws:
            data = ws.receive_json()
            assert data["type"] == "agent"

    def test_ws_accepts_authorization_header(self, client_with_token):
        with client_with_token.websocket_connect(
            "/ws/analyze/AAPL",
            headers={"Authorization": "Bearer test-secret-token-123"},
        ) as ws:
            data = ws.receive_json()
            assert data["type"] == "agent"
