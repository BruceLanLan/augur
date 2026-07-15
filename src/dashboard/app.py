#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Augur — Bloomberg风格投资分析仪表盘
FastAPI + Jinja2 + Bloomberg暗色主题

Usage:
    python3 -m dashboard.app
    python3 -m dashboard.app --port 8080 --cors
"""

import asyncio
import sys
import os
import re
import json
import math
import hashlib
import logging
import threading
import time as _time
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import (
        HTMLResponse, JSONResponse, FileResponse, PlainTextResponse, Response, RedirectResponse,
    )
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.exceptions import RequestValidationError
    from fastapi.concurrency import run_in_threadpool
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Missing dependencies. Run: pip install fastapi uvicorn jinja2")
    sys.exit(1)

from augur.registry import AgentRegistry, DecisionCoordinator
from augur.personas.base import MarketContext

from augur.report import generate_report

from augur.config import get_config, set_config, save_config, reset_config
from augur.workspace import (
    get_workspace,
    get_enabled_personas,
    resolve_landing_url,
)
from augur.errors import api_error_response
from augur.auth import (
    authenticate_request,
    authenticate_websocket,
    auth_required,
    check_auth_rate_limit,
    extract_bearer_token,
    verify_jwt,
)

logger = logging.getLogger(__name__)

# Module-level startup time for uptime tracking
_APP_START_TIME = _time.time()

app = FastAPI(
    title="Augur — 多智能体投资分析",
    description="18位虚拟投资大师，多维度共识分析",
    version="10.15.1",
)

from dashboard.routes.workspace import router as _workspace_router  # noqa: E402
from dashboard.routes.market import router as _market_router  # noqa: E402
from dashboard.routes.history import router as _history_router  # noqa: E402
from dashboard.routes.auth import router as _auth_router  # noqa: E402
from dashboard.routes.notifications_cron import router as _notifications_cron_router  # noqa: E402
from dashboard.routes.config import router as _config_router  # noqa: E402
from dashboard.routes.personas import router as _personas_router, PERSONA_ENRICHMENT, _persona_meta  # noqa: E402
from dashboard.routes.analysis import router as _analysis_router  # noqa: E402
from dashboard.routes.watchlist import router as _watchlist_router  # noqa: E402
from dashboard.routes.backtest import router as _backtest_router  # noqa: E402
from dashboard.routes.misc import router as _misc_router  # noqa: E402
from dashboard.routes.committee import router as _committee_router  # noqa: E402
from dashboard.routes.ws import router as _ws_router  # noqa: E402
from dashboard.routes.chat import router as _chat_router  # noqa: E402
from dashboard.routes.rules import router as _rules_router  # noqa: E402
from dashboard.routes.optimizer import router as _optimizer_router  # noqa: E402
from dashboard.routes.portfolio import router as _portfolio_router  # noqa: E402
from dashboard.routes.pages import router as _pages_router  # noqa: E402
import dashboard.deps as _deps
from dashboard.deps import get_registry, get_coordinator, _singleton_init_lock
from dashboard.deps import (  # re-export so existing `from dashboard.app import X` still works
    _APP_START_TIME,
    _rate_limits, _rate_limit_lock, _RATE_LIMIT_MAX, _RATE_LIMIT_WINDOW,
    _check_rate_limit,
    TokenBucket, _endpoint_buckets, _endpoint_buckets_lock,
    get_endpoint_bucket, consume_endpoint_token,
    _get_rules_engine,
    _i18n_cache, _load_translations, _i18n_context,
    _save_history_safe,
)
app.include_router(_workspace_router)
app.include_router(_market_router)
app.include_router(_history_router)
app.include_router(_auth_router)
app.include_router(_notifications_cron_router)
app.include_router(_config_router)
app.include_router(_personas_router)
app.include_router(_analysis_router)
app.include_router(_watchlist_router)
app.include_router(_backtest_router)
app.include_router(_misc_router)
app.include_router(_committee_router)
app.include_router(_ws_router)
app.include_router(_chat_router)
app.include_router(_rules_router)
app.include_router(_optimizer_router)
app.include_router(_portfolio_router)
app.include_router(_pages_router)


# Global exception handler: catch unhandled exceptions, return consistent JSON
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions.

    Browser clients get a friendly HTML 500 page; API/tooling clients get the
    standard JSON envelope. Never leak stack traces to clients; log the real
    error for debugging.
    """
    logger.error(f"Unhandled exception on {request.url.path}: {type(exc).__name__}: {exc}")

    if _wants_html(request):
        return _render_error_page(
            request, 500, "Internal server error",
            "Something broke on our end. We've logged the issue.",
            "Try again in a moment, or head back to the dashboard.",
        )

    return JSONResponse(
        status_code=500,
        content=api_error_response(
            detail="Internal server error",
            code="INTERNAL_ERROR",
            path=request.url.path,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return user-friendly JSON for validation errors instead of FastAPI default."""
    errors = exc.errors()
    details = "; ".join(f"{e.get('loc', ['?'])[-1]}: {e.get('msg', 'invalid')}" for e in errors)
    return JSONResponse(
        status_code=422,
        content=api_error_response(
            detail=f"Validation error: {details}",
            code="VALIDATION_ERROR",
            path=request.url.path,
            suggestion="Check parameter types and values. Use /api/analyze/TICKER format.",
        ),
    )


def _wants_html(request: Request) -> bool:
    """Return True if the client likely wants an HTML response (browser nav).

    Used by error handlers to choose between a styled HTML error page and a
    machine-readable JSON error body.
    """
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept or "application/xhtml" in accept:
        return True
    # No Accept header usually means a browser typing a URL in the address bar.
    if not accept:
        return True
    return False


def _render_error_page(request: Request, status_code: int, heading: str, message: str, suggestion: str = ""):
    """Render a friendly branded HTML error page for browser navigation.

    Falls back to a minimal inline page if the error template cannot be loaded.
    """
    try:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "title": f"{status_code} · {heading}",
                "status_code": status_code,
                "heading": heading,
                "message": message,
                "suggestion": suggestion,
                "path": request.url.path,
            },
            status_code=status_code,
        )
    except Exception:
        # Last-resort fallback so the user always gets HTML on a browser.
        body = (
            f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<title>{status_code} · {heading}</title>"
            f"<style>body{{font-family:system-ui,sans-serif;background:#0e0f12;color:#e6e6e6;"
            f"display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}"
            f".card{{max-width:520px;padding:32px;background:#1a1c22;border:1px solid #2a2d35;"
            f"border-radius:12px;text-align:center}}h1{{font-size:64px;margin:0;color:#ff8c00}}"
            f"p{{color:#9aa0a6;line-height:1.5}}</style></head><body><div class='card'>"
            f"<h1>{status_code}</h1><h2>{heading}</h2><p>{message}</p>"
            f"{('<p>' + suggestion + '</p>') if suggestion else ''}"
            f"<p><a href='/' style='color:#ff8c00'>← Back to Dashboard</a></p>"
            f"</div></body></html>"
        )
        return HTMLResponse(content=body, status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return JSON for API/tooling clients, a styled HTML page for browsers."""
    if _wants_html(request):
        if exc.status_code == 404:
            return _render_error_page(
                request, 404, "Page not found",
                f"We couldn't find anything at {request.url.path}.",
                "Check the URL for typos, or jump back to the dashboard.",
            )
        if exc.status_code == 403:
            return _render_error_page(
                request, 403, "Access denied",
                str(exc.detail) if exc.detail else "You don't have permission to view this page.",
                "Sign in with an authorized account, or contact your admin.",
            )
        if exc.status_code == 401:
            return _render_error_page(
                request, 401, "Authentication required",
                "Please sign in to continue.",
                "Use the Login button in the top-right corner.",
            )
        if exc.status_code == 429:
            return _render_error_page(
                request, 429, "Too many requests",
                "You're sending requests too quickly. Please slow down.",
                "Wait a few seconds and try again.",
            )
        return _render_error_page(
            request, exc.status_code, f"HTTP {exc.status_code}",
            str(exc.detail) if exc.detail else "Something went wrong.",
        )
    # API/tooling clients keep the consistent JSON envelope with a
    # stable, machine-readable code and a human-friendly suggestion.
    _ERROR_ENVELOPE: Dict[int, Tuple[str, str]] = {
        400: ("INVALID_REQUEST", "Check the request parameters (ticker format, body shape, required fields) and retry."),
        401: ("AUTH_REQUIRED", "Provide a valid Bearer token or sign in to continue."),
        403: ("FORBIDDEN", "You don't have permission for this resource. Ask an admin or enable multi-user mode."),
        404: ("NOT_FOUND", "The resource doesn't exist. Verify the path or ID and try again."),
        405: ("METHOD_NOT_ALLOWED", "This endpoint doesn't support the HTTP method you used. Check the docs."),
        409: ("CONFLICT", "The resource is in a conflicting state. Refresh and retry."),
        413: ("PAYLOAD_TOO_LARGE", "Request body is too large. Reduce the payload size and retry."),
        415: ("UNSUPPORTED_MEDIA_TYPE", "Use a supported Content-Type (e.g. application/json)."),
        422: ("UNPROCESSABLE_ENTITY", "The request was well-formed but contained invalid data. Check field types."),
        429: ("RATE_LIMITED", "You're sending requests too quickly. Slow down and retry after a moment."),
        500: ("INTERNAL_ERROR", "Something broke on our end. We've logged the issue — try again shortly."),
        501: ("NOT_IMPLEMENTED", "This feature isn't available in the current deployment."),
        502: ("BAD_GATEWAY", "Upstream service returned an invalid response. Try again in a moment."),
        503: ("SERVICE_UNAVAILABLE", "Service is temporarily unavailable. Retry with backoff."),
        504: ("GATEWAY_TIMEOUT", "Upstream service timed out. Retry in a moment."),
    }
    code, suggestion = _ERROR_ENVELOPE.get(
        exc.status_code,
        (f"HTTP_{exc.status_code}", "Check the request and try again."),
    )
    detail_text = str(exc.detail) if exc.detail else (
        "Not found" if exc.status_code == 404 else f"HTTP {exc.status_code}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=api_error_response(
            detail=detail_text,
            code=code,
            suggestion=suggestion,
            path=request.url.path,
        ),
    )


# ============ CORS Middleware (unconditional) ============

_cors_origins = os.environ.get("AUGUR_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ API Token Authentication Middleware ============

_AUTH_EXEMPT_PATHS = {
    "/api/auth/config",
    "/api/auth/verify",
    "/api/auth/register",
    "/api/auth/login",
    "/health",
    "/api/health",
}


@app.middleware("http")
async def api_token_auth_middleware(request: Request, call_next):
    """Enforce Bearer token or JWT auth on /api/* when configured."""
    if request.url.path.startswith("/api/") and request.url.path not in _AUTH_EXEMPT_PATHS:
        if auth_required():
            ok, _mode = authenticate_request(request)
            if not ok:
                return JSONResponse(
                    status_code=401,
                    content=api_error_response(
                        detail="Authentication required",
                        code="AUTH_REQUIRED",
                        suggestion="Provide a valid Bearer token (Authorization: Bearer <token>) and retry.",
                        path=request.url.path,
                    ),
                )
    response = await call_next(request)
    return response


# ============ IP-based Rate Limiting Middleware ============

_ip_rate_limits: Dict[str, List[float]] = {}
_ip_rate_lock = threading.Lock()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    remaining = None
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        now = _time.time()
        with _ip_rate_lock:
            if client_ip not in _ip_rate_limits:
                _ip_rate_limits[client_ip] = []
            _ip_rate_limits[client_ip] = [t for t in _ip_rate_limits[client_ip] if now - t < 60]
            if len(_ip_rate_limits[client_ip]) >= 60:
                return JSONResponse(
                    status_code=429,
                    content=api_error_response(
                        detail="Rate limit exceeded. Max 60 requests per minute.",
                        code="RATE_LIMITED",
                        suggestion="Slow down and retry after a few seconds.",
                        path=request.url.path,
                    ),
                    headers={"X-RateLimit-Remaining": "0"},
                )
            _ip_rate_limits[client_ip].append(now)
            remaining = str(max(0, 60 - len(_ip_rate_limits[client_ip])))
            # Periodic eviction of stale IP entries to prevent unbounded memory growth
            if len(_ip_rate_limits) > 10000:
                stale_ips = [
                    ip for ip, timestamps in _ip_rate_limits.items()
                    if not timestamps or all(now - ts >= 60 for ts in timestamps)
                ]
                for ip in stale_ips:
                    del _ip_rate_limits[ip]
    response = await call_next(request)
    if remaining is not None and response.status_code != 429:
        response.headers["X-RateLimit-Remaining"] = remaining
    return response


# ============ Pydantic Response Models ============

class HealthResponse(BaseModel):
    status: str
    agents: int


class AnalyzeResponse(BaseModel):
    status: str
    ticker: str
    timestamp: str
    data_source: str
    market_data: Dict[str, Any]
    consensus: Dict[str, Any]
    agents: List[Dict[str, Any]]
    agent_count: int

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount docs/images for avatars. Repo-root-relative -- "src/dashboard" ->
# "src" -> repo root in a dev checkout; docs/ isn't shipped in the wheel
# (not in package-data) so this correctly no-ops via the exists() guard in
# a real pip install. Off-by-one here (R7's dashboard/ -> src/dashboard/
# move shifted this one level without updating this path) silently 404'd
# every persona avatar dashboard-wide -- found via a real Playwright run,
# not caught by tests since nothing exercises actual image loading in a
# browser. See tests/test_packaging_layout.py for the regression guard.
IMAGES_DIR = Path(__file__).parent.parent.parent / "docs" / "images"
if IMAGES_DIR.exists():
    app.mount("/docs/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")

# All routes extracted to dashboard/routes/ (R5–R14 router splits)


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(description="Augur Dashboard")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--cors", action="store_true",
                        help="(deprecated: CORS is now always enabled via AUGUR_CORS_ORIGINS env var)")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    print(f"\n🦉 Augur Dashboard")
    print(f"   http://localhost:{args.port}")
    print(f"   http://localhost:{args.port}/personas")
    print(f"   http://localhost:{args.port}/api/analyze/AAPL?pe=32&gross_margins=0.46")
    print()

    uvicorn.run(
        "dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
