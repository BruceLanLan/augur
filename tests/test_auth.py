# -*- coding: utf-8 -*-
"""Tests for API Authentication (Bearer token + JWT multi-user)."""

import base64
import hashlib
import hmac
import json
import os
import time

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


class TestAuthUnitFunctions:
    """Direct unit tests for augur.auth module-level functions."""

    def test_extract_bearer_token_returns_none_for_missing_or_malformed(self, monkeypatch):
        monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
        monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
        from augur.auth import extract_bearer_token
        assert extract_bearer_token("") is None
        assert extract_bearer_token(None) is None  # type: ignore[arg-type]
        assert extract_bearer_token("Basic abc123") is None
        assert extract_bearer_token("Bearer") is None  # missing token part
        assert extract_bearer_token("Token foo") is None  # wrong scheme
        assert extract_bearer_token("Bearer ") is None  # empty token after scheme
        # Well-formed Bearer header returns the token
        assert extract_bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"

    def test_authenticate_bearer_open_mode_when_unconfigured(self, monkeypatch):
        monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
        monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
        from augur.auth import authenticate_bearer
        assert authenticate_bearer(None) == (True, "open")
        assert authenticate_bearer("anything") == (True, "open")

    def test_authenticate_bearer_rejects_missing_token_when_required(self, monkeypatch):
        monkeypatch.setenv("AUGUR_API_TOKEN", "secret-xyz")
        monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
        from augur.auth import authenticate_bearer
        # Token required, but None provided → rejected
        ok, mode = authenticate_bearer(None)
        assert ok is False
        assert mode == ""
        # Wrong token → rejected
        ok, mode = authenticate_bearer("wrong-token")
        assert ok is False
        assert mode == ""
        # Correct token → accepted as 'token' mode
        ok, mode = authenticate_bearer("secret-xyz")
        assert ok is True
        assert mode == "token"

    def test_verify_request_raises_401_on_missing_header(self, monkeypatch):
        monkeypatch.setenv("AUGUR_API_TOKEN", "secret-xyz")
        monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
        from fastapi import HTTPException

        from augur.auth import verify_request

        class FakeRequest:
            def __init__(self, header_value):
                self.headers = {"authorization": header_value}

        # No header at all → 401 "Authorization header is required"
        with pytest.raises(HTTPException) as excinfo:
            verify_request(FakeRequest(""))  # type: ignore[arg-type]
        assert excinfo.value.status_code == 401
        assert "required" in str(excinfo.value.detail).lower()

        # Wrong scheme → 401
        with pytest.raises(HTTPException) as excinfo:
            verify_request(FakeRequest("Basic foo"))  # type: ignore[arg-type]
        assert excinfo.value.status_code == 401

        # Bearer with empty token → 401
        with pytest.raises(HTTPException) as excinfo:
            verify_request(FakeRequest("Bearer "))  # type: ignore[arg-type]
        assert excinfo.value.status_code == 401

        # Wrong bearer token → 401
        with pytest.raises(HTTPException) as excinfo:
            verify_request(FakeRequest("Bearer wrong"))  # type: ignore[arg-type]
        assert excinfo.value.status_code == 401

    def test_check_auth_rate_limit_blocks_after_max_attempts(self, monkeypatch):
        from augur.auth import (
            _auth_rate_limits,
            _auth_rate_lock,
            check_auth_rate_limit,
        )
        # Ensure clean state
        with _auth_rate_lock:
            _auth_rate_limits.clear()
        ip = "10.20.30.40-unit-test"
        # First 10 attempts must be allowed
        for i in range(10):
            assert check_auth_rate_limit(ip) is True, f"attempt {i + 1} should be allowed"
        # 11th attempt must be blocked
        assert check_auth_rate_limit(ip) is False
        # Different IP should still be allowed
        assert check_auth_rate_limit("203.0.113.1") is True
        # Cleanup so we don't pollute other tests
        with _auth_rate_lock:
            _auth_rate_limits.clear()

    def test_verify_jwt_returns_none_in_single_user_mode(self, monkeypatch):
        """verify_jwt must short-circuit (return None) when multi-user is disabled."""
        monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)
        from augur.auth import verify_jwt
        # Any token string should be ignored
        assert verify_jwt("any.token.here") is None
        assert verify_jwt("") is None


class TestJWTTokenDecoding:
    """Unit tests for JWT verify/expired/wrong-issuer (wrong secret)/malformed."""

    def _craft_token(self, secret: str, payload: dict) -> str:
        """Helper: build a HS256 token signed with `secret` for `payload`."""
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        signing_input = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            secret.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def test_jwt_verify_accepts_valid_token(self, monkeypatch):
        """A valid token signed with the active secret round-trips back to its payload."""
        from augur import users

        # Make sure we have a stable secret for this test
        monkeypatch.setattr(users, "_JWT_SECRET", "pytest-jwt-secret-AAA")
        from augur.auth import verify_jwt
        from augur.users import is_multi_user_enabled
        if not is_multi_user_enabled():
            # verify_jwt is a no-op outside multi-user; still useful to exercise it
            assert verify_jwt("anything") is None
            return

        token = self._craft_token(
            "pytest-jwt-secret-AAA",
            {
                "user_id": 1,
                "username": "alice",
                "iat": time.time(),
                "exp": time.time() + 3600,
            },
        )
        payload = verify_jwt(token)
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["username"] == "alice"

    def test_jwt_verify_rejects_expired_token(self, monkeypatch):
        """A token whose `exp` is in the past must be rejected (returns None)."""
        from augur import users
        from augur.auth import verify_jwt
        from augur.users import is_multi_user_enabled

        monkeypatch.setattr(users, "_JWT_SECRET", "pytest-jwt-secret-BBB")
        if not is_multi_user_enabled():
            assert verify_jwt("anything") is None
            return

        expired = self._craft_token(
            "pytest-jwt-secret-BBB",
            {
                "user_id": 2,
                "username": "bob",
                "iat": time.time() - 7200,
                "exp": time.time() - 3600,  # expired 1h ago
            },
        )
        assert verify_jwt(expired) is None

    def test_jwt_verify_rejects_wrong_issuer_secret(self, monkeypatch):
        """Token signed with a *different* secret (wrong issuer) is rejected."""
        from augur import users
        from augur.auth import verify_jwt
        from augur.users import is_multi_user_enabled

        monkeypatch.setattr(users, "_JWT_SECRET", "pytest-jwt-secret-CCC")
        if not is_multi_user_enabled():
            assert verify_jwt("anything") is None
            return

        # Sign with the WRONG secret
        bad = self._craft_token(
            "some-other-secret-XXX",
            {
                "user_id": 3,
                "username": "mallory",
                "iat": time.time(),
                "exp": time.time() + 3600,
            },
        )
        assert verify_jwt(bad) is None

    def test_jwt_verify_rejects_malformed_token(self, monkeypatch):
        """Garbage / wrong-shape / wrong-alg tokens are all rejected."""
        from augur import users
        from augur.auth import verify_jwt
        from augur.users import is_multi_user_enabled

        monkeypatch.setattr(users, "_JWT_SECRET", "pytest-jwt-secret-DDD")
        if not is_multi_user_enabled():
            assert verify_jwt("anything") is None
            return

        # Completely wrong shape
        assert verify_jwt("not-a-jwt") is None
        assert verify_jwt("") is None
        # Only two parts (header.payload, no signature)
        assert verify_jwt("aaa.bbb") is None
        # Token with alg=none-style header (not HS256) must be rejected
        none_header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        none_payload = base64.urlsafe_b64encode(
            json.dumps({"user_id": 99, "exp": time.time() + 3600}).encode()
        ).rstrip(b"=").decode()
        assert verify_jwt(f"{none_header}.{none_payload}.sig") is None
