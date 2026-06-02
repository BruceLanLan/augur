# -*- coding: utf-8 -*-
"""
augur.auth - API authentication (Bearer token + optional JWT multi-user).

When AUGUR_API_TOKEN is set, /api/* requires Authorization: Bearer <token>.
When AUGUR_MULTI_USER=1, /api/* requires a valid JWT from /api/auth/login.
Either credential satisfies auth when both modes are enabled.

WebSocket endpoints accept the same token via Authorization header or ?token= query
param (browsers cannot set custom WS headers in JavaScript).
"""

import hmac
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request

_auth_rate_limits: Dict[str, List[float]] = {}
_auth_rate_lock = threading.Lock()
_AUTH_RATE_MAX = 10
_AUTH_RATE_WINDOW = 60.0


def get_token() -> Optional[str]:
    """Return the configured API token from environment."""
    return os.environ.get("AUGUR_API_TOKEN") or None


def extract_bearer_token(auth_header: str) -> Optional[str]:
    """Parse Bearer token from Authorization header."""
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def is_multi_user_mode() -> bool:
    from augur.users import is_multi_user_enabled
    return is_multi_user_enabled()


def auth_required() -> bool:
    """True when API token or multi-user JWT auth is enabled."""
    return get_token() is not None or is_multi_user_mode()


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Verify multi-user JWT and return payload, or None."""
    if not is_multi_user_mode():
        return None
    from augur.users import UserManager
    return UserManager().verify_token(token)


def authenticate_bearer(token: Optional[str]) -> Tuple[bool, str]:
    """Return (authenticated, mode) where mode is open|token|jwt|''."""
    api_token = get_token()
    multi = is_multi_user_mode()
    if not api_token and not multi:
        return True, "open"
    if not token:
        return False, ""
    if api_token and hmac.compare_digest(token, api_token):
        return True, "token"
    if multi and verify_jwt(token):
        return True, "jwt"
    return False, ""


def authenticate_request(request: Request) -> Tuple[bool, str]:
    """Authenticate an HTTP request from its Authorization header."""
    token = extract_bearer_token(request.headers.get("authorization", ""))
    return authenticate_bearer(token)


def get_websocket_token(websocket) -> Optional[str]:
    """Extract token from WS Authorization header or ?token= query param."""
    token = extract_bearer_token(websocket.headers.get("authorization", ""))
    if token:
        return token
    query_token = websocket.query_params.get("token")
    if query_token and query_token.strip():
        return query_token.strip()
    return None


def authenticate_websocket(websocket) -> bool:
    """Authenticate a WebSocket handshake."""
    if not auth_required():
        return True
    token = get_websocket_token(websocket)
    ok, _ = authenticate_bearer(token)
    return ok


def check_auth_rate_limit(client_ip: str) -> bool:
    """Rate-limit auth endpoints (login/register). Returns True if allowed."""
    now = time.time()
    with _auth_rate_lock:
        if client_ip not in _auth_rate_limits:
            _auth_rate_limits[client_ip] = []
        _auth_rate_limits[client_ip] = [
            t for t in _auth_rate_limits[client_ip] if now - t < _AUTH_RATE_WINDOW
        ]
        if len(_auth_rate_limits[client_ip]) >= _AUTH_RATE_MAX:
            return False
        _auth_rate_limits[client_ip].append(now)
        return True


def verify_request(request: Request) -> None:
    """Check Authorization header; raises HTTPException(401) when auth fails."""
    if not auth_required():
        return

    ok, _ = authenticate_request(request)
    if ok:
        return

    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header is required")

    if not auth_header.startswith("Bearer "):
        if auth_header.strip().lower() == "bearer":
            raise HTTPException(status_code=401, detail="Bearer token is empty")
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization scheme. Use 'Bearer <token>' format",
        )

    raise HTTPException(status_code=401, detail="Invalid API token")
