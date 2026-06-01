# -*- coding: utf-8 -*-
"""
augur.auth - Optional Bearer Token authentication for API endpoints.

When AUGUR_API_TOKEN environment variable is set, all /api/* endpoints
require a valid Authorization: Bearer <token> header. HTML page routes
and the /health endpoint are always exempt.

If AUGUR_API_TOKEN is not set, all requests pass through without auth.
"""

import hmac
import os
from typing import Optional

from fastapi import HTTPException, Request


def get_token() -> Optional[str]:
    """Return the configured API token from environment.

    Returns:
        The AUGUR_API_TOKEN value, or None if not set.
    """
    return os.environ.get("AUGUR_API_TOKEN") or None


def verify_request(request: Request) -> None:
    """Check Authorization header against AUGUR_API_TOKEN.

    If token is set and header doesn't match 'Bearer <token>',
    raises HTTPException(status_code=401).
    If AUGUR_API_TOKEN is NOT set, this function does nothing (open access).

    Uses hmac.compare_digest to prevent timing attacks.

    Handles edge cases:
    - Missing Authorization header
    - Malformed headers (e.g., "Basic xxx", random strings)
    - Empty bearer tokens ("Bearer " with no actual token)
    - "Bearer" with no trailing space/token

    Args:
        request: The incoming FastAPI Request object.

    Raises:
        HTTPException: 401 if token is configured but header is invalid.
    """
    token = get_token()
    if token is None:
        return

    auth_header = request.headers.get("authorization", "")

    # Handle missing header
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header is required")

    # Handle non-Bearer schemes
    if not auth_header.startswith("Bearer "):
        # Check if it's just "Bearer" with no space/token
        if auth_header.strip().lower() == "bearer":
            raise HTTPException(status_code=401, detail="Bearer token is empty")
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization scheme. Use 'Bearer <token>' format"
        )

    # Extract the token part
    provided_token = auth_header[7:]  # After "Bearer "

    # Handle empty token after "Bearer "
    if not provided_token or not provided_token.strip():
        raise HTTPException(status_code=401, detail="Bearer token is empty")

    # Compare tokens using constant-time comparison
    expected = f"Bearer {token}"
    if hmac.compare_digest(auth_header, expected):
        return

    raise HTTPException(status_code=401, detail="Invalid API token")
