#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Augur — Bloomberg风格投资分析仪表盘
FastAPI + Jinja2 + Bloomberg暗色主题

Usage:
    python3 -m dashboard.app
    python3 -m dashboard.app --port 8080 --cors
"""

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
from typing import Optional, List, Dict, Any, Tuple
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, PlainTextResponse, Response
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Missing dependencies. Run: pip install fastapi uvicorn jinja2")
    sys.exit(1)

try:
    from augur.registry import AgentRegistry, DecisionCoordinator
    from augur.personas.base import MarketContext
except ImportError:
    from scanner.personas.registry import AgentRegistry, DecisionCoordinator
    from scanner.personas.base import MarketContext

from augur.report import generate_report

from augur.config import get_config, set_config, save_config, reset_config
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
    version="7.8.3",
)


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

# Mount docs/images for avatars
IMAGES_DIR = Path(__file__).parent.parent / "docs" / "images"
if IMAGES_DIR.exists():
    app.mount("/docs/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")

_registry: Optional[AgentRegistry] = None
_coordinator: Optional[DecisionCoordinator] = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def get_coordinator() -> DecisionCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = DecisionCoordinator(get_registry())
    return _coordinator


PERSONA_ENRICHMENT = {
    "buffett": {"cn_name": "沃伦·巴菲特", "en_name": "Warren Buffett", "school": "value", "core_principles": ["护城河决定长期价值", "只买看得懂的生意", "别人恐惧时贪婪"], "holdings": ["BRK.B", "AAPL", "KO", "AXP"]},
    "graham": {"cn_name": "本杰明·格雷厄姆", "en_name": "Benjamin Graham", "school": "value", "core_principles": ["安全边际是投资的基石", "市场先生情绪无常", "买入低于净资产的股票"], "holdings": ["GEICO", "BRK.B"]},
    "munger": {"cn_name": "查理·芒格", "en_name": "Charlie Munger", "school": "value", "core_principles": ["多元思维模型", "用合理价格买优质企业", "避免愚蠢比追求聪明更重要"], "holdings": ["BRK.B", "COST", "BAC"]},
    "fisher": {"cn_name": "菲利普·费雪", "en_name": "Philip Fisher", "school": "growth", "core_principles": ["成长股的真正价值在管理层", "闲聊法深入调研", "长期持有优质成长股"], "holdings": ["MOTOROLA", "TXN"]},
    "lynch": {"cn_name": "彼得·林奇", "en_name": "Peter Lynch", "school": "growth", "core_principles": ["在生活中发现十倍股", "PEG是成长股估值核心", "分散但集中于了解的领域"], "holdings": ["SBUX", "FNM"]},
    "cathie_wood": {"cn_name": "凯瑟琳·伍德", "en_name": "Cathie Wood", "school": "growth", "core_principles": ["颠覆性创新创造指数级增长", "5年投资视野", "拥抱波动性"], "holdings": ["TSLA", "COIN", "ROKU", "SQ"]},
    "aschenbrenner": {"cn_name": "利奥波德·阿申布伦纳", "en_name": "Leopold Aschenbrenner", "school": "growth", "core_principles": ["AI超级周期即将到来", "算力是新石油", "AGI将重塑所有行业"], "holdings": ["NVDA", "MSFT", "GOOGL"]},
    "thiel": {"cn_name": "彼得·蒂尔", "en_name": "Peter Thiel", "school": "growth", "core_principles": ["垄断企业才有真正价值", "从0到1比从1到N更重要", "逆向思维发现秘密"], "holdings": ["PLTR", "META", "TSLA"]},
    "dalio": {"cn_name": "瑞·达利欧", "en_name": "Ray Dalio", "school": "macro", "core_principles": ["理解债务周期驱动一切", "全天候组合应对不确定性", "激进透明与原则决策"], "holdings": ["SPY", "GLD", "TLT"]},
    "soros": {"cn_name": "乔治·索罗斯", "en_name": "George Soros", "school": "macro", "core_principles": ["反身性：认知影响现实", "先开枪后瞄准", "发现市场错误定价"], "holdings": ["MACRO_BETS"]},
    "marks": {"cn_name": "霍华德·马克斯", "en_name": "Howard Marks", "school": "macro", "core_principles": ["周期是投资中最确定的事", "风险来自过高的价格", "逆向投资需要勇气"], "holdings": ["OAK", "HY_BONDS"]},
    "serenity": {"cn_name": "宁静", "en_name": "Serenity", "school": "quant", "core_principles": ["波动率是可以管理的风险", "尾部风险对冲保护本金", "系统化消除情绪干扰"], "holdings": ["VIX_HEDGE", "OPTIONS"]},
    "arps": {"cn_name": "马丁·阿普斯", "en_name": "Martin Arps", "school": "quant", "core_principles": ["价格包含一切信息", "趋势是你的朋友", "量价背离是最强信号"], "holdings": ["TECH_MOMENTUM"]},
    "dayu": {"cn_name": "大宇", "en_name": "Dayu", "school": "quant", "core_principles": ["量化模型消除主观偏见", "资金流向揭示主力意图", "统计套利寻找确定性"], "holdings": ["A_SHARES"]},
    "duan_yongping": {"cn_name": "段永平", "en_name": "Duan Yongping", "school": "china", "core_principles": ["做对的事，停止做错的事", "商业模式比什么都重要", "极度集中持仓"], "holdings": ["AAPL", "PDD", "BABA"]},
    "zhang_lei": {"cn_name": "张磊", "en_name": "Zhang Lei", "school": "china", "core_principles": ["长期结构性价值创造", "研究驱动投资", "与伟大企业共同成长"], "holdings": ["PDD", "JD", "BYD"]},
    "li_lu": {"cn_name": "李录", "en_name": "Li Lu", "school": "china", "core_principles": ["价值投资在中国同样适用", "理解文明的演化", "集中投资少数确定机会"], "holdings": ["BRK.B", "BYD", "BABA"]},
    "dan_bin": {"cn_name": "但斌", "en_name": "Dan Bin", "school": "china", "core_principles": ["时间的玫瑰：长期主义", "消费龙头是最佳赛道", "长坡厚雪复利惊人"], "holdings": ["600519.SS", "AAPL", "MOUTAI"]},
}


def _persona_meta() -> List[Dict]:
    registry = get_registry()
    config = get_config()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    custom_dir = Path(__file__).parent.parent / "personas" / "custom"
    meta = []
    for agent in registry.get_all():
        # Chinese mainland investors only; Serenity is excluded because
        # the persona is international (anonymous, multi-market, non-China-based).
        chinese_investors = {"duan_yongping", "zhang_lei", "li_lu", "dan_bin", "dayu"}
        country = "\U0001f1e8\U0001f1f3 中国" if agent.agent_id in chinese_investors else ""
        enrichment = PERSONA_ENRICHMENT.get(agent.agent_id, {})
        is_custom = (custom_dir / f"{agent.agent_id}.yaml").exists()
        meta.append({
            "id": agent.agent_id,
            "agent_id": agent.agent_id,
            "name": agent.name,
            "cn_name": enrichment.get("cn_name", agent.name),
            "en_name": enrichment.get("en_name", agent.name),
            "school": enrichment.get("school", "value"),
            "core_principles": enrichment.get("core_principles", agent.philosophy[:3] if agent.philosophy else []),
            "holdings": enrichment.get("holdings", []),
            "style": " \u00b7 ".join(agent.philosophy[:2]) if agent.philosophy else "",
            "description": agent.identity.strip().replace("\n", " ").replace("  ", " "),
            "scenarios": agent.philosophy,
            "scoring_weights": agent.scoring_weights if agent.scoring_weights else {},
            "weight": f"{list(agent.scoring_weights.values())[0]:.0%}" if agent.scoring_weights else "\u5747\u7b49",
            "status": "\u5df2\u6ce8\u518c",
            "country": country,
            "is_chinese": agent.agent_id in chinese_investors,
            "is_custom": is_custom,
            "quote": agent.philosophy[0] if agent.philosophy else "\u6295\u8d44\uff0c\u5c31\u662f\u6295\u672a\u6765\u3002",
            "model": per_agent.get(agent.agent_id, default_model),
        })
    return meta


# ============ Rate Limiting ============

_rate_limits: Dict[str, List[float]] = {}
_rate_limit_lock = threading.Lock()
_RATE_LIMIT_MAX = 30  # max requests per window
_RATE_LIMIT_WINDOW = 60.0  # seconds


def _check_rate_limit(ticker: str) -> bool:
    """Check and enforce rate limit for a ticker. Returns True if allowed, False if exceeded."""
    now = _time.time()
    ticker_key = ticker.upper()
    with _rate_limit_lock:
        # Clean up expired entries for this ticker
        if ticker_key in _rate_limits:
            _rate_limits[ticker_key] = [
                ts for ts in _rate_limits[ticker_key] if now - ts < _RATE_LIMIT_WINDOW
            ]
        else:
            _rate_limits[ticker_key] = []

        # Check limit
        if len(_rate_limits[ticker_key]) >= _RATE_LIMIT_MAX:
            return False

        # Record this request
        _rate_limits[ticker_key].append(now)

        # Periodic eviction of stale ticker keys to prevent unbounded growth
        if len(_rate_limits) > 1000:
            stale_keys = [
                k for k, v in _rate_limits.items()
                if not v or all(now - ts >= _RATE_LIMIT_WINDOW for ts in v)
            ]
            for k in stale_keys:
                del _rate_limits[k]

        return True


# ============ Token Bucket Rate Limiter ============
# Per-endpoint token-bucket rate limiting for heavy LLM endpoints.
# Each bucket has a capacity (burst) and refill rate (tokens/second).
# This complements the global IP middleware with stricter per-route limits.

class TokenBucket:
    """Thread-safe token-bucket rate limiter.

    A bucket holds up to ``capacity`` tokens and refills at ``refill_rate`` tokens
    per second. ``consume()`` returns True and removes one token if a token is
    available, otherwise returns False without modifying state.
    """

    __slots__ = ("capacity", "refill_rate", "tokens", "last_refill", "_lock")

    def __init__(self, capacity: int, refill_rate: float):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_rate < 0:
            raise ValueError("refill_rate must be >= 0")
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = _time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = _time.time()
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(
                float(self.capacity), self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume ``tokens`` tokens. Returns True if allowed."""
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def reset(self) -> None:
        """Reset the bucket to full capacity (used in tests)."""
        with self._lock:
            self.tokens = float(self.capacity)
            self.last_refill = _time.time()


# Per-route token-bucket registry. Routes are registered lazily on first use.
_endpoint_buckets: Dict[str, TokenBucket] = {}
_endpoint_buckets_lock = threading.Lock()


def get_endpoint_bucket(
    name: str, capacity: int = 5, refill_rate: float = 0.5
) -> TokenBucket:
    """Return (creating if needed) the TokenBucket for a named endpoint.

    Defaults: capacity=5 burst tokens, refill=0.5 tok/s (~30/min steady-state).
    """
    with _endpoint_buckets_lock:
        bucket = _endpoint_buckets.get(name)
        if bucket is None:
            bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate)
            _endpoint_buckets[name] = bucket
        return bucket


def consume_endpoint_token(name: str) -> bool:
    """Convenience wrapper that consumes one token from a named endpoint bucket."""
    return get_endpoint_bucket(name).consume(1.0)


# ============ HTML Routes ============

@app.get("/", response_class=HTMLResponse, summary="首页仪表盘")
async def index(request: Request):
    agent_count = len(get_registry().get_all())
    try:
        from augur.datasources import available_sources
        ds_count = len(available_sources())
    except Exception:
        ds_count = 2
    stats = [
        {"value": str(agent_count), "label": "虚拟投资大师", "icon": "users"},
        {"value": "6", "label": "共识加权层", "icon": "layers"},
        {"value": "40+", "label": "评分因子", "icon": "sliders"},
        {"value": str(ds_count), "label": "数据源链路", "icon": "database"},
    ]
    featured = [
        {"avatar": "🏦", "id": "buffett", "name": "Warren Buffett", "style": "价值 · 护城河", "desc": "寻找具有持久竞争优势的企业，以合理价格长期持有。FCF 和 ROE 是核心衡量标准。", "tag": "价值投资"},
        {"avatar": "📐", "id": "graham", "name": "Benjamin Graham", "style": "安全边际 · 烟蒂股", "desc": "只在具有显著安全边际时买入，PE<15、PB<1.5 是硬性门槛。", "tag": "深度价值"},
        {"avatar": "🚀", "id": "cathie_wood", "name": "Cathie Wood", "style": "颠覆性创新", "desc": "专注 AI、基因组、区块链等颠覆性技术，接受高估值换取指数级成长。", "tag": "成长投资"},
        {"avatar": "🇨🇳", "id": "duan_yongping", "name": "段永平", "style": "本分 · 极度集中", "desc": "「本分」哲学：只做正确的事，停止做错误的事。极度集中持仓，能力圈内重仓。", "tag": "中国价值"},
    ]
    return templates.TemplateResponse(request=request, name="index.html", context={
        "title": "Augur — 投资大师仪表盘",
        "agent_count": agent_count,
        "stats": stats,
        "featured": featured,
    })


@app.get("/personas", response_class=HTMLResponse, summary="投资人人格系统页面")
async def personas_page(request: Request):
    return templates.TemplateResponse(request=request, name="personas.html", context={
        "personas": _persona_meta(),
        "title": "投资人人格系统",
    })


@app.get("/stocks", response_class=HTMLResponse, summary="股票分析页面")
async def stocks_page(request: Request):
    quick_tickers = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "BRK.B", "META", "AMZN", "PDD", "BIDU"]
    return templates.TemplateResponse(request=request, name="stocks.html", context={
        "title": "股票分析",
        "quick_tickers": quick_tickers,
    })


@app.get("/signals", response_class=HTMLResponse, summary="信号监控页面")
async def signals_page(request: Request):
    return templates.TemplateResponse(request=request, name="signals.html", context={
        "title": "信号监控",
    })


@app.get("/scanner", response_class=HTMLResponse, summary="市场扫描器页面")
async def scanner_page(request: Request):
    return templates.TemplateResponse(request=request, name="scanner.html", context={
        "title": "市场扫描器 - Scanner",
    })


@app.get("/watchlist", response_class=HTMLResponse, summary="自选股页面")
async def watchlist_page(request: Request):
    return templates.TemplateResponse(request=request, name="watchlist.html", context={
        "title": "自选股 - Watchlist",
    })


@app.get("/portfolio", response_class=HTMLResponse, summary="持仓管理页面")
async def portfolio_page(request: Request):
    return templates.TemplateResponse(request=request, name="portfolio.html", context={
        "title": "持仓管理 - Portfolio",
    })


@app.get("/settings", response_class=HTMLResponse, summary="设置页面")
async def settings_page(request: Request):
    config = get_config()
    available_models = config.get("available_models", {})
    models_flat = []
    for provider_models in available_models.values():
        if isinstance(provider_models, list):
            models_flat.extend(provider_models)
    personas = _persona_meta()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    for p in personas:
        p["current_model"] = per_agent.get(p["id"], default_model)
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "title": "设置",
        "personas": personas,
        "available_models": models_flat,
        "default_model": default_model,
    })


@app.get("/create-persona", response_class=HTMLResponse, summary="创建自定义投资人页面")
async def create_persona_page(request: Request):
    return templates.TemplateResponse(request=request, name="create_persona.html", context={
        "title": "创建自定义投资人",
    })


@app.get("/report/{ticker}", response_class=HTMLResponse, summary="深度分析报告全屏页面")
async def report_view_page(request: Request, ticker: str):
    """Dedicated full-page report view for a ticker. Auto-fetches report on load."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")
    return templates.TemplateResponse(request=request, name="report_view.html", context={
        "title": f"{ticker.upper()} Deep Analysis Report - Augur",
        "ticker": ticker.upper(),
    })


# ============ API Routes ============

@app.get("/api/personas", summary="获取所有投资人列表")
async def list_personas():
    """返回所有投资人人格列表"""
    registry = get_registry()
    return {
        "status": "ok",
        "count": len(registry.get_all()),
        "personas": [agent.to_dict() for agent in registry.get_all()],
    }


# ============ Scanner API ============

class ScannerRunBody(BaseModel):
    tickers: List[str] = []
    preset: Optional[str] = None


SCANNER_PRESETS = {
    "tech_giants": ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "META", "AMZN", "AMD"],
    "china_stocks": ["BABA", "PDD", "JD", "BIDU", "NIO", "LI", "XPEV"],
    "crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"],
}


@app.post("/api/scanner/run", summary="批量扫描标的评分")
async def api_scanner_run(body: ScannerRunBody):
    """批量扫描标的，返回所有大师评分矩阵"""
    tickers = body.tickers
    if body.preset and body.preset in SCANNER_PRESETS:
        tickers = SCANNER_PRESETS[body.preset]
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")
    if len(tickers) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 tickers per scan")

    # Validate tickers
    for t in tickers:
        if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', t):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {t}")

    coord = get_coordinator()
    results = []
    for ticker in tickers:
        try:
            ctx = MarketContext(ticker=ticker.upper())
            # Try auto-fetch
            try:
                from augur.data import fetch_market_context
                ctx = fetch_market_context(ticker)
            except Exception:
                pass
            agent_responses = coord.analyze_with_all(ctx)
            consensus = coord.get_consensus(agent_responses, ticker=ticker.upper(), context=ctx)
            agents_data = []
            for agent_id, resp in agent_responses.items():
                agents_data.append({
                    "agent_id": agent_id,
                    "signal": resp.signal.value,
                    "score": round(resp.score, 1),
                })
            results.append({
                "ticker": ticker.upper(),
                "consensus_signal": consensus.signal.value,
                "consensus_score": round(consensus.score, 1),
                "agents": agents_data,
            })
        except Exception as e:
            results.append({
                "ticker": ticker.upper(),
                "consensus_signal": "error",
                "consensus_score": 0,
                "agents": [],
                "error": {
                    "status": "error",
                    "detail": f"Scanner failed for {ticker.upper()}: {e}",
                    "code": "SCAN_FAILED",
                    "suggestion": "Verify the ticker is valid and the data source is reachable, then retry.",
                },
            })

    return {"status": "ok", "results": results, "count": len(results)}


@app.get("/api/analyze/{ticker}", summary="分析指定标的")
async def analyze_ticker(
    ticker: str,
    price: float = 0,
    pe: float = 0,
    pb: float = 0,
    revenue_growth: float = 0,
    gross_margins: float = 0,
    operating_margins: float = 0,
    roe: float = 0,
    debt_ratio: float = 0,
    fcf: float = 0,
    market_cap: float = 0,
    institutional_ownership: float = 0,
    insider_ownership: float = 0,
    current_ratio: float = 0,
    earnings_growth: float = 0,
    sector: str = "",
    industry: str = "",
    auto_fetch: bool = True,
):
    """
    使用所有18位投资大师分析指定标的

    基本用法: GET /api/analyze/AAPL (自动获取实时数据)
    手动指标: GET /api/analyze/AAPL?price=210&pe=32&gross_margins=0.46
    """
    # Validate ticker format to prevent injection issues with yfinance or URLs
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    # Rate limiting: max 30 requests per minute per ticker
    if not _check_rate_limit(ticker):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 30 requests per minute per ticker.")

    # Check if any meaningful metric was provided by user
    has_user_metrics = any([
        price > 0, pe > 0, pb > 0, revenue_growth != 0,
        gross_margins > 0, operating_margins != 0, roe > 0,
        debt_ratio > 0, fcf != 0, market_cap > 0,
    ])

    data_source = "manual"

    if not has_user_metrics and auto_fetch:
        # Try to auto-fetch from yfinance
        # When auto_fetch succeeds, manual params are ignored. This is intentional:
        # real-time data takes precedence over manually supplied values to avoid stale overrides.
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            data_source = "yfinance"
        except (ImportError, Exception):
            # Fallback to manual (empty) context
            data_source = "fallback"
            ctx = MarketContext(
                ticker=ticker.upper(),
                price=price,
                pe=pe,
                pb=pb,
                revenue_growth=revenue_growth,
                gross_margins=gross_margins,
                operating_margins=operating_margins,
                roe=roe,
                debt_ratio=debt_ratio,
                fcf=fcf,
                market_cap=market_cap,
                institutional_ownership=institutional_ownership,
                insider_ownership=insider_ownership,
                current_ratio=current_ratio,
                earnings_growth=earnings_growth,
                sector=sector,
                industry=industry,
            )
    else:
        ctx = MarketContext(
            ticker=ticker.upper(),
            price=price,
            pe=pe,
            pb=pb,
            revenue_growth=revenue_growth,
            gross_margins=gross_margins,
            operating_margins=operating_margins,
            roe=roe,
            debt_ratio=debt_ratio,
            fcf=fcf,
            market_cap=market_cap,
            institutional_ownership=institutional_ownership,
            insider_ownership=insider_ownership,
            current_ratio=current_ratio,
            earnings_growth=earnings_growth,
            sector=sector,
            industry=industry,
        )

    coord = get_coordinator()
    agent_responses = coord.analyze_with_all(ctx)
    consensus_resp = coord.get_consensus(
        agent_responses,
        ticker=ticker.upper(),
        context=ctx,
    )

    response = {
        "status": "ok",
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_source": data_source,
        "market_data": {
            "price": ctx.price,
            "pe": ctx.pe,
            "pb": ctx.pb,
            "roe": ctx.roe,
            "gross_margins": ctx.gross_margins,
            "sector": ctx.sector,
            "industry": ctx.industry,
            "business_summary": ctx.business_summary,
            "market_cap": ctx.market_cap,
            "fcf": ctx.fcf,
            "revenue_growth": ctx.revenue_growth,
            "debt_ratio": ctx.debt_ratio,
        },
        "consensus": consensus_resp.to_dict(),
        "agents": [r.to_dict() for r in agent_responses.values()],
        "agent_count": len(agent_responses),
    }

    if data_source == "fallback":
        response["data_note"] = "Auto-fetch failed, using provided parameters"

    return response


@app.get("/api/persona/compare", summary="对比两位投资大师对同一标的的观点")
async def compare_personas(persona1: str, persona2: str, ticker: str):
    """
    对比两位投资大师对同一标的的分析观点。

    - persona1: 第一位投资人ID
    - persona2: 第二位投资人ID
    - ticker: 股票代码
    """
    # Validate ticker format
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    # Get both agents
    registry = get_registry()
    agent1 = registry.get(persona1)
    agent2 = registry.get(persona2)

    if not agent1:
        raise HTTPException(status_code=404, detail=f"Persona '{persona1}' not found")
    if not agent2:
        raise HTTPException(status_code=404, detail=f"Persona '{persona2}' not found")

    # Build market context
    ctx = MarketContext(ticker=ticker.upper())
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        pass

    # Run both analyses
    try:
        resp1 = agent1.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {persona1}: {e}")

    try:
        resp2 = agent2.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {persona2}: {e}")

    enrichment1 = PERSONA_ENRICHMENT.get(persona1, {})
    enrichment2 = PERSONA_ENRICHMENT.get(persona2, {})

    def _build_result(agent_id, agent, resp, enrichment):
        return {
            "agent_id": agent_id,
            "agent_name": enrichment.get("cn_name", agent.name),
            "en_name": enrichment.get("en_name", agent.name),
            "school": enrichment.get("school", ""),
            "signal": resp.signal.value,
            "score": round(resp.score, 1),
            "confidence": round(resp.confidence, 2),
            "reasoning": resp.reasoning,
            "key_findings": resp.key_findings,
            "risks": resp.risks if hasattr(resp, "risks") else [],
        }

    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "persona1": _build_result(persona1, agent1, resp1, enrichment1),
        "persona2": _build_result(persona2, agent2, resp2, enrichment2),
        "agreement": resp1.signal == resp2.signal,
        "score_diff": round(abs(resp1.score - resp2.score), 1),
    }


@app.get("/api/persona/{agent_id}", summary="获取单个投资人详情")
async def get_persona(agent_id: str):
    """获取单个投资人的详细信息"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")
    return agent.to_dict()


@app.get("/api/persona/{agent_id}/opinion", summary="获取单个投资人对标的的分析观点")
async def get_persona_opinion(agent_id: str, ticker: str, question: Optional[str] = None):
    """
    使用单个投资大师分析指定标的，返回其独立观点。

    - agent_id: 投资人ID (如 buffett, munger, dalio)
    - ticker: 股票代码 (如 AAPL, NVDA)
    - question: 可选的用户问题上下文
    """
    # Validate ticker format
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    # Get agent
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")

    # Build market context
    ctx = MarketContext(ticker=ticker.upper())
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        pass

    # Run single agent analysis
    try:
        response = agent.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    enrichment = PERSONA_ENRICHMENT.get(agent_id, {})

    return {
        "status": "ok",
        "agent_id": agent_id,
        "agent_name": enrichment.get("cn_name", agent.name),
        "ticker": ticker.upper(),
        "signal": response.signal.value,
        "score": round(response.score, 1),
        "confidence": round(response.confidence, 2),
        "reasoning": response.reasoning,
        "key_findings": response.key_findings,
        "risks": response.risks if hasattr(response, "risks") else [],
        "question": question,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/api/report/{ticker}", summary="生成深度分析报告")
async def report_ticker(
    ticker: str,
    price: float = 0,
    pe: float = 0,
    pb: float = 0,
    revenue_growth: float = 0,
    gross_margins: float = 0,
    operating_margins: float = 0,
    roe: float = 0,
    debt_ratio: float = 0,
    fcf: float = 0,
    market_cap: float = 0,
    institutional_ownership: float = 0,
    insider_ownership: float = 0,
    current_ratio: float = 0,
    earnings_growth: float = 0,
    sector: str = "",
    industry: str = "",
    auto_fetch: bool = True,
):
    """
    生成深度分析报告（Markdown格式）

    基本用法: GET /api/report/AAPL (自动获取实时数据)
    手动指标: GET /api/report/AAPL?price=210&pe=32&auto_fetch=false
    """
    # Validate ticker format
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    # Rate limiting
    if not _check_rate_limit(ticker):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 30 requests per minute per ticker.")

    # Check if any meaningful metric was provided by user
    has_user_metrics = any([
        price > 0, pe > 0, pb > 0, revenue_growth != 0,
        gross_margins > 0, operating_margins != 0, roe > 0,
        debt_ratio > 0, fcf != 0, market_cap > 0,
    ])

    data_source = "manual"

    if not has_user_metrics and auto_fetch:
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            data_source = "yfinance"
        except (ImportError, Exception):
            data_source = "fallback"
            ctx = MarketContext(
                ticker=ticker.upper(),
                price=price,
                pe=pe,
                pb=pb,
                revenue_growth=revenue_growth,
                gross_margins=gross_margins,
                operating_margins=operating_margins,
                roe=roe,
                debt_ratio=debt_ratio,
                fcf=fcf,
                market_cap=market_cap,
                institutional_ownership=institutional_ownership,
                insider_ownership=insider_ownership,
                current_ratio=current_ratio,
                earnings_growth=earnings_growth,
                sector=sector,
                industry=industry,
            )
    else:
        ctx = MarketContext(
            ticker=ticker.upper(),
            price=price,
            pe=pe,
            pb=pb,
            revenue_growth=revenue_growth,
            gross_margins=gross_margins,
            operating_margins=operating_margins,
            roe=roe,
            debt_ratio=debt_ratio,
            fcf=fcf,
            market_cap=market_cap,
            institutional_ownership=institutional_ownership,
            insider_ownership=insider_ownership,
            current_ratio=current_ratio,
            earnings_growth=earnings_growth,
            sector=sector,
            industry=industry,
        )

    coord = get_coordinator()
    agent_responses = coord.analyze_with_all(ctx)
    consensus_resp = coord.get_consensus(
        agent_responses,
        ticker=ticker.upper(),
        context=ctx,
    )

    report = generate_report(ticker.upper(), ctx, agent_responses, consensus_resp)

    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "report": report,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_source": data_source,
    }


@app.post("/api/report/{ticker}", summary="从已有数据生成报告")
async def generate_report_from_data(ticker: str, request: Request):
    """Generate report from pre-computed analysis data (avoids re-running agents)."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Reconstruct from pre-computed data
    from augur.personas.base import AgentResponse, SignalType

    consensus_data = body.get("consensus", {})
    agents_data = body.get("agents", [])
    market_data = body.get("market_data", {})

    # Build context from market_data
    ctx = MarketContext(
        ticker=ticker.upper(),
        price=market_data.get("price", 0),
        pe=market_data.get("pe", 0),
        pb=market_data.get("pb", 0),
        roe=market_data.get("roe", 0),
        gross_margins=market_data.get("gross_margins", 0),
        operating_margins=market_data.get("operating_margins", 0),
        revenue_growth=market_data.get("revenue_growth", 0),
        debt_ratio=market_data.get("debt_ratio", 0),
        fcf=market_data.get("fcf", 0),
        market_cap=market_data.get("market_cap", 0),
        sector=market_data.get("sector", ""),
        industry=market_data.get("industry", ""),
    )

    # Reconstruct AgentResponses
    signal_map = {"bullish": SignalType.BULLISH, "neutral": SignalType.NEUTRAL, "bearish": SignalType.BEARISH, "error": SignalType.ERROR}
    results = {}
    for agent_data in agents_data:
        agent_id = agent_data.get("agent_id", "")
        results[agent_id] = AgentResponse(
            agent_id=agent_id,
            agent_name=agent_data.get("agent_name", agent_id),
            signal=signal_map.get(agent_data.get("signal", "neutral"), SignalType.NEUTRAL),
            confidence=agent_data.get("confidence", 0),
            score=agent_data.get("score", 0),
            reasoning=agent_data.get("reasoning", ""),
            key_findings=agent_data.get("key_findings", []),
            risks=agent_data.get("risks", []),
            metadata=agent_data.get("metadata", {}),
        )

    # Reconstruct consensus
    consensus_resp = AgentResponse(
        agent_id="consensus",
        agent_name="Multi-Agent Consensus",
        signal=signal_map.get(consensus_data.get("signal", "neutral"), SignalType.NEUTRAL),
        confidence=consensus_data.get("confidence", 0),
        score=consensus_data.get("score", 0),
        reasoning=consensus_data.get("reasoning", ""),
        key_findings=consensus_data.get("key_findings", []),
        risks=consensus_data.get("risks", []),
        metadata=consensus_data.get("metadata", {}),
    )

    report_md = generate_report(ticker.upper(), ctx, results, consensus_resp)

    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "report": report_md,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_source": "cached",
    }


# ============ Config API Routes ============

class ConfigUpdateBody(BaseModel):
    """Request body for full config update."""
    defaults: Optional[Dict[str, Any]] = None
    per_agent: Optional[Dict[str, Any]] = None
    available_models: Optional[Dict[str, Any]] = None


class PersonaModelBody(BaseModel):
    """Request body for persona model update."""
    model: str


class CustomPersonaBody(BaseModel):
    """Request body for custom persona creation."""
    yaml_content: str
    agent_id: str


@app.get("/api/config", summary="获取系统配置")
async def api_get_config():
    """返回完整配置（敏感信息脱敏）"""
    config = get_config()

    def _mask_sensitive(d, parent_key=""):
        """Recursively mask values whose keys contain 'key', 'token', or 'secret'."""
        if isinstance(d, dict):
            masked = {}
            for k, v in d.items():
                k_lower = k.lower()
                if any(s in k_lower for s in ("key", "token", "secret")) and isinstance(v, str) and len(v) > 4:
                    masked[k] = "***" + v[-4:]
                elif isinstance(v, dict):
                    masked[k] = _mask_sensitive(v, k)
                elif isinstance(v, list):
                    masked[k] = v
                else:
                    masked[k] = v
            return masked
        return d

    return _mask_sensitive(config)


@app.put("/api/config", summary="更新系统配置")
async def api_put_config(body: ConfigUpdateBody):
    """更新完整配置"""
    data = body.dict(exclude_none=True)
    for key, value in data.items():
        set_config(key, value)
    save_config()
    return {"status": "ok", "message": "配置已更新"}


@app.get("/api/config/persona/{agent_id}", summary="获取Agent模型配置")
async def api_get_persona_config(agent_id: str):
    """获取单个 Agent 的模型配置"""
    # Validate agent_id format to prevent injection / path traversal issues
    if not re.match(r'^[a-z0-9_-]{1,50}$', agent_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid agent_id format. Use 1-50 lowercase letters, digits, hyphens, or underscores.",
        )
    config = get_config()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    model = per_agent.get(agent_id, default_model)
    return {"agent_id": agent_id, "model": model}


@app.put("/api/config/persona/{agent_id}", summary="更新Agent模型配置")
async def api_put_persona_config(agent_id: str, body: PersonaModelBody):
    """更新单个 Agent 的模型配置"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found in registry")
    set_config(f"per_agent.{agent_id}", body.model)
    save_config()
    return {"status": "ok", "agent_id": agent_id, "model": body.model}


@app.get("/api/models", summary="获取可用模型列表")
async def api_get_models():
    """返回所有可用模型（扁平列表）"""
    config = get_config()
    available_models = config.get("available_models", {})
    models_flat = []
    for provider, provider_models in available_models.items():
        if isinstance(provider_models, list):
            models_flat.extend(provider_models)
    return {"models": models_flat}


@app.post("/api/custom-persona", summary="创建自定义投资人")
async def api_create_custom_persona(body: CustomPersonaBody):
    """保存自定义 Persona YAML 到 personas/custom/"""
    # Validate agent_id: only allow lowercase alphanumeric, hyphens, underscores
    if not re.match(r'^[a-z0-9_-]+$', body.agent_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid agent_id: only lowercase letters, digits, hyphens, and underscores are allowed"
        )
    # Length limit to prevent abuse
    if len(body.agent_id) > 50:
        raise HTTPException(status_code=400, detail="agent_id too long (max 50 characters)")
    # Explicit path traversal protection
    if '..' in body.agent_id:
        raise HTTPException(status_code=400, detail="agent_id contains invalid characters")
    # Validate YAML content is parseable
    try:
        yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML content: {e}")
    custom_dir = Path(__file__).parent.parent / "personas" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    filepath = custom_dir / f"{body.agent_id}.yaml"
    filepath.write_text(body.yaml_content, encoding="utf-8")

    # Hot-reload: register in the live registry immediately
    try:
        from augur.persona_loader import load_persona_yaml
        global _registry, _coordinator
        new_agent = load_persona_yaml(str(filepath))
        if _registry is not None and new_agent.agent_id not in {a.agent_id for a in _registry.get_all()}:
            _registry.register(new_agent)
            _coordinator = None  # reset coordinator so it uses updated registry
    except Exception:
        pass  # hot-reload is best-effort; YAML is saved and will load on restart

    return {"status": "ok", "path": str(filepath), "hot_loaded": True}


@app.get("/api/custom-personas", summary="列出所有自定义投资人")
async def api_list_custom_personas():
    """列出 personas/custom/ 目录下的所有自定义投资人"""
    custom_dir = Path(__file__).parent.parent / "personas" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    personas = []
    for fp in sorted(custom_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
            personas.append({
                "agent_id": data.get("agent_id", fp.stem),
                "name": data.get("name", fp.stem),
                "filepath": str(fp),
            })
        except Exception:
            personas.append({
                "agent_id": fp.stem,
                "name": fp.stem,
                "filepath": str(fp),
            })
    return {"status": "ok", "personas": personas}


@app.delete("/api/custom-persona/{agent_id}", summary="删除自定义投资人")
async def api_delete_custom_persona(agent_id: str):
    """删除 personas/custom/ 下的自定义投资人 YAML 并从注册表注销"""
    if not re.match(r'^[a-z0-9_-]+$', agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    custom_dir = Path(__file__).parent.parent / "personas" / "custom"
    filepath = custom_dir / f"{agent_id}.yaml"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Custom persona '{agent_id}' not found")
    filepath.unlink()
    # Unregister from live registry
    global _registry, _coordinator
    if _registry is not None:
        try:
            _registry.unregister(agent_id)
            _coordinator = None
        except Exception:
            pass
    return {"status": "ok", "agent_id": agent_id, "message": "已删除"}


@app.put("/api/custom-persona/{agent_id}", summary="更新自定义投资人")
async def api_update_custom_persona(agent_id: str, body: CustomPersonaBody):
    """更新已有的自定义投资人 YAML，热重载"""
    if not re.match(r'^[a-z0-9_-]+$', agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    custom_dir = Path(__file__).parent.parent / "personas" / "custom"
    filepath = custom_dir / f"{agent_id}.yaml"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Custom persona '{agent_id}' not found")
    # Validate YAML
    try:
        yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML content: {e}")
    filepath.write_text(body.yaml_content, encoding="utf-8")
    # Hot-reload
    global _registry, _coordinator
    try:
        from augur.persona_loader import load_persona_yaml
        new_agent = load_persona_yaml(str(filepath))
        if _registry is not None:
            # Unregister old, register new
            try:
                _registry.unregister(agent_id)
            except Exception:
                pass
            _registry.register(new_agent)
            _coordinator = None
    except Exception:
        pass
    return {"status": "ok", "agent_id": agent_id, "path": str(filepath), "hot_loaded": True}


@app.get("/api/auth/verify", summary="验证API Token")
async def api_auth_verify(request: Request):
    """验证 API Token 或 JWT 有效性。未启用认证时返回 open 模式。"""
    if not auth_required():
        return {"status": "ok", "authenticated": True, "mode": "open"}
    ok, mode = authenticate_request(request)
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
    return {"status": "ok", "authenticated": True, "mode": mode}


@app.get("/api/auth/me", summary="获取当前登录用户")
async def api_auth_me(request: Request):
    """Return the authenticated multi-user JWT identity."""
    from augur.users import is_multi_user_enabled
    if not is_multi_user_enabled():
        raise HTTPException(status_code=403, detail="Set AUGUR_MULTI_USER=1 to enable multi-user mode.")
    token = extract_bearer_token(request.headers.get("authorization", ""))
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"status": "ok", "user_id": payload["user_id"], "username": payload["username"]}


@app.get("/api/schema/persona", summary="获取Persona YAML结构")
async def api_persona_schema():
    """返回 Persona YAML 结构描述"""
    return {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "唯一标识符"},
            "name": {"type": "string", "description": "显示名称"},
            "identity": {"type": "string", "description": "人格身份描述"},
            "philosophy": {"type": "array", "items": {"type": "string"}, "description": "投资哲学要点"},
            "scoring_weights": {"type": "object", "description": "评分权重 (维度 -> 0-1)"},
            "model": {"type": "string", "description": "使用的 LLM 模型"},
        },
        "required": ["agent_id", "name", "identity"],
    }


# ============ Watchlist API Routes ============

class WatchlistAddBody(BaseModel):
    """Request body for adding ticker to watchlist."""
    ticker: str
    pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    gross_margins: Optional[float] = None
    revenue_growth: Optional[float] = None
    debt_ratio: Optional[float] = None
    fcf: Optional[float] = None
    market_cap: Optional[float] = None
    price: Optional[float] = None


@app.get("/api/watchlist", summary="获取自选股列表")
async def api_get_watchlist():
    """Get current watchlist from ~/.augur/watchlist.yaml"""
    from augur.cron import load_watchlist
    try:
        config = load_watchlist()
    except FileNotFoundError:
        return {"watchlist": [], "schedule": {}}
    except Exception as e:
        # Graceful degradation: file may be corrupt or unreadable
        logger.warning("watchlist load failed: %s", e)
        return {
            "watchlist": [],
            "schedule": {},
            "error": "watchlist_unavailable",
            "message": f"自选股文件读取失败: {e}",
        }
    return {
        "watchlist": config.get("watchlist", []),
        "schedule": config.get("schedule", {}),
    }


@app.post("/api/watchlist/add", summary="添加自选股")
async def api_add_to_watchlist(body: WatchlistAddBody):
    """Add ticker to watchlist"""
    from augur.cron import add_to_watchlist
    # Validate ticker
    if not re.match(r'^[A-Za-z0-9.\-]+$', body.ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    if len(body.ticker) > 15:
        raise HTTPException(status_code=400, detail="Ticker too long (max 15 characters)")
    metrics = {}
    for field in ["pe", "pb", "roe", "gross_margins", "revenue_growth", "debt_ratio", "fcf", "market_cap", "price"]:
        val = getattr(body, field, None)
        if val is not None:
            metrics[field] = val
    try:
        config = add_to_watchlist(body.ticker.upper(), metrics if metrics else None)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"无写入权限: {e}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"写入自选股失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加自选股失败: {e}")
    return {"status": "ok", "ticker": body.ticker.upper(), "watchlist": config.get("watchlist", [])}


@app.delete("/api/watchlist/{ticker}", summary="删除自选股")
async def api_remove_from_watchlist(ticker: str):
    """Remove ticker from watchlist"""
    # Validate ticker format (alphanumerics, dots, hyphens; 1-15 chars)
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.",
        )
    from augur.cron import remove_from_watchlist
    removed = remove_from_watchlist(ticker.upper())
    if not removed:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker.upper()}' not found in watchlist")
    return {"status": "ok", "ticker": ticker.upper(), "message": "已从自选股移除"}


@app.post("/api/watchlist/run", summary="批量分析自选股")
async def api_run_watchlist_analysis():
    """Run consensus analysis on all watchlist tickers"""
    import time
    from augur.cron import load_watchlist
    from augur.personas.base import MarketContext

    config = load_watchlist()
    watchlist = config.get("watchlist", [])

    if not watchlist:
        return {"status": "empty", "message": "自选股列表为空", "results": []}

    coordinator = get_coordinator()
    all_results = []
    start_time = time.time()

    for item in watchlist:
        ticker = item.get("ticker", "")
        if not ticker:
            continue

        ctx_kwargs = {"ticker": ticker.upper()}
        for key in ["pe", "pb", "roe", "gross_margins", "revenue_growth",
                    "debt_ratio", "fcf", "market_cap", "price"]:
            if key in item:
                ctx_kwargs[key] = item[key]

        ctx = MarketContext(**ctx_kwargs)
        results = coordinator.analyze_with_all(ctx)
        consensus = coordinator.get_consensus(results, ticker=ticker, context=ctx)

        result_item = {
            "ticker": ticker,
            "signal": consensus.signal.value,
            "score": round(consensus.score, 1),
            "confidence": round(consensus.confidence, 2) if hasattr(consensus, 'confidence') else 0.0,
            "agent_count": len(results),
            "buy_count": sum(1 for r in results.values() if r.signal.value == "bullish"),
            "sell_count": sum(1 for r in results.values() if r.signal.value == "bearish"),
            "hold_count": sum(1 for r in results.values() if r.signal.value == "neutral"),
            "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            "key_findings": consensus.key_findings[:2] if consensus.key_findings else [],
            "kelly_pct": consensus.metadata.get("position_sizing", {}).get("position_pct"),
        }
        all_results.append(result_item)

        # Persist last signal back to watchlist item
        try:
            for w_item in watchlist:
                if w_item.get("ticker", "").upper() == ticker.upper():
                    w_item["last_signal"] = consensus.signal.value
                    w_item["last_score"] = result_item["score"]
                    w_item["last_run"] = result_item["last_run"]
                    break
        except Exception:
            pass

    # Save updated watchlist with last_signal
    try:
        from augur.cron import save_watchlist
        config["watchlist"] = watchlist
        save_watchlist(config)
    except Exception:
        pass

    return {"status": "ok", "results": all_results, "processing_time_ms": round((time.time() - start_time) * 1000)}


@app.get("/backtest", response_class=HTMLResponse, summary="历史回测页面")
async def backtest_page(request: Request):
    return templates.TemplateResponse(request=request, name="backtest.html", context={
        "title": "历史回测 - Agent IC",
    })


@app.get("/api/backtest/run", summary="运行历史回测")
async def api_run_backtest(ticker: str = "AAPL", days: int = 30, initial_capital: float = 100000, strategy: str = "equal_weight"):
    """Run demo backtest, return results with metrics and signals timeline"""
    # Validate ticker format
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    from augur.backtest import Backtester, generate_sample_data

    if days < 5:
        days = 5
    if days > 365:
        days = 365

    historical_data, forward_returns = generate_sample_data(ticker, days)
    backtester = Backtester()
    result = backtester.run_backtest(ticker, historical_data, forward_returns)

    # Compute metrics from agent_ics
    agent_ics = result.agent_ics
    avg_hit_rate = 0.0
    if agent_ics:
        avg_hit_rate = sum(a.hit_rate for a in agent_ics) / len(agent_ics)

    # Approximate metrics
    avg_gain = 0.02
    avg_loss = -0.015
    daily_return = (avg_hit_rate * avg_gain + (1 - avg_hit_rate) * avg_loss)
    annualized_return = daily_return * 252
    max_drawdown = -((1 - avg_hit_rate) * 0.15 + 0.05)
    vol = abs(max_drawdown) * 1.5
    sharpe_ratio = (annualized_return - 0.04) / vol if vol > 0 else 0.0

    metrics = {
        "annualized_return": round(annualized_return, 4),
        "max_drawdown": round(max_drawdown, 4),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "win_rate": round(avg_hit_rate, 4),
    }

    # Build signals timeline from records
    signals_timeline = []
    for rec in result.records[:50]:
        signals_timeline.append({
            "date": rec.date,
            "ticker": rec.ticker,
            "signal": rec.signal,
            "score": round(rec.score, 1),
            "agent_id": rec.agent_id,
        })
    # Sort by date descending
    signals_timeline.sort(key=lambda x: x["date"], reverse=True)

    return {
        "status": "ok",
        "ticker": result.ticker,
        "days": days,
        "initial_capital": initial_capital,
        "strategy": strategy,
        "total_records": len(result.records),
        "consensus_ic": result.consensus_ic,
        "agent_ics": [a.to_dict() for a in result.agent_ics],
        "metrics": metrics,
        "signals_timeline": signals_timeline,
        "summary": result.summary,
    }


@app.get("/api/backtest/leaderboard", summary="获取IC排行榜")
async def api_ic_leaderboard():
    """Get saved IC leaderboard"""
    from augur.backtest import Backtester

    backtester = Backtester()
    ics = backtester.get_leaderboard()

    registry = get_registry()
    def _enrich(d: dict) -> dict:
        agent = registry.get(d.get("agent_id", ""))
        if agent:
            d["agent_name"] = agent.name
        return d

    return {
        "status": "ok",
        "leaderboard": [_enrich(a.to_dict()) for a in ics],
        "count": len(ics),
    }


@app.get("/health", summary="健康检查")
async def health():
    return {"status": "ok", "agents": len(get_registry().get_all())}


@app.get("/robots.txt", response_class=PlainTextResponse, summary="Robots.txt", include_in_schema=False)
async def robots_txt():
    return "User-agent: *\nAllow: /\nSitemap: https://augur.example.com/sitemap.xml\n"


@app.get("/sitemap.xml", summary="Sitemap XML", include_in_schema=False)
async def sitemap_xml():
    base = "https://augur.example.com"
    urls = ["/", "/stocks", "/personas", "/signals", "/scanner", "/backtest", "/settings", "/watchlist"]
    xml_entries = "\n".join(
        f"  <url><loc>{base}{u}</loc><changefreq>daily</changefreq></url>"
        for u in urls
    )
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_entries}
</urlset>'''
    return Response(content=xml, media_type="application/xml")


@app.get("/api/health", summary="扩展健康检查")
async def api_health_extended():
    """Extended health check - returns datasource reachability, cache info, uptime."""
    # Check datasources
    datasources = []
    try:
        from augur.datasources import available_sources
        sources = available_sources()
        for src in sources:
            datasources.append({"name": src, "reachable": True})
    except Exception as e:
        datasources.append({"name": "unknown", "reachable": False, "error": str(e)})

    # Cache info
    try:
        from augur.data import cache_stats
        cache = cache_stats()
    except Exception:
        try:
            from augur.data import cache_info
            cache = cache_info()
        except Exception:
            cache = {}

    uptime = _time.time() - _APP_START_TIME

    return {
        "status": "ok",
        "agents": len(get_registry().get_all()),
        "datasources": datasources,
        "cache": cache,
        "uptime_seconds": round(uptime, 1),
        "version": "7.8.3",
    }


# ============ Cache Management API Routes ============

@app.post("/api/cache/clear", summary="清除数据缓存")
async def api_cache_clear():
    """Clear the data cache to force fresh fetches."""
    from augur.data import clear_cache
    clear_cache()
    return {"status": "ok", "message": "Cache cleared"}


@app.get("/api/cache/info", summary="缓存状态信息")
async def api_cache_info():
    """Return cache size and TTL info."""
    from augur.data import cache_info
    info = cache_info()
    return {"status": "ok", "cache": info}


# ============ Data Fetch API Routes ============

# Module-level flag: check once at import time whether augur.data is available
from augur.optional_deps import is_available as _is_available, get_install_hint
_HAS_AUGUR_DATA = _is_available("augur.data")


@app.get("/api/fetch/{ticker}", summary="获取实时行情数据")
async def api_fetch_ticker(ticker: str):
    """Fetch real-time market data for a ticker via yfinance"""
    # Validate ticker format to prevent injection issues
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.",
        )
    if not _HAS_AUGUR_DATA:
        feature, install_cmd = get_install_hint("augur.data")
        raise HTTPException(
            status_code=501,
            detail=f"Package 'yfinance' is required for {feature} but is not installed. Install with: {install_cmd}"
        )

    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
        return {
            "status": "ok",
            "ticker": ctx.ticker,
            "source": "yfinance",
            "data": ctx.to_dict(),
        }
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e}")


@app.get("/api/search", summary="搜索标的")
async def api_search_tickers(q: str = ""):
    """Search for tickers by name/symbol"""
    # Reject empty / excessively long queries up front
    if not q or len(q) < 1:
        return {"results": []}
    if len(q) > 64:
        raise HTTPException(
            status_code=400,
            detail="Search query too long (max 64 characters).",
        )
    # Reject control characters / suspicious bytes
    if any(ord(c) < 0x20 for c in q):
        raise HTTPException(
            status_code=400,
            detail="Search query contains invalid control characters.",
        )

    if not _HAS_AUGUR_DATA:
        feature, install_cmd = get_install_hint("augur.data")
        raise HTTPException(
            status_code=501,
            detail=f"Package 'yfinance' is required for {feature} but is not installed. Install with: {install_cmd}"
        )

    try:
        from augur.data import search_ticker
        results = search_ticker(q)
        return {"status": "ok", "query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


# ============ Sparkline API Route ============

@app.get("/api/sparkline/{ticker}", summary="获取7日迷你走势数据")
async def api_sparkline(ticker: str):
    """Return last 7 trading days close prices for sparkline rendering."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    try:
        from augur.data import fetch_history
        history = fetch_history(ticker, period="1mo")
        # Get last 7 data points
        prices = [h["close"] for h in history[-7:]] if history else []
        trend = "flat"
        if len(prices) >= 2:
            trend = "up" if prices[-1] > prices[0] else "down" if prices[-1] < prices[0] else "flat"
        return {"status": "ok", "ticker": ticker.upper(), "prices": prices, "trend": trend}
    except Exception as e:
        return {"status": "error", "ticker": ticker.upper(), "prices": [], "trend": "flat", "error": str(e)}


# ============ Hot Tickers API Route ============

@app.get("/api/hot-tickers", summary="热门标的实时行情")
async def api_hot_tickers(request: Request, refresh: bool = False):
    """热门标的实时行情：AAPL, NVDA, TSLA, MSFT, GOOGL, AMZN, BTC-USD, ETH-USD, META, AMD。

    供首页「热门标的实时行情」面板使用。无 yfinance 时优雅降级为空列表。
    """
    try:
        if not _HAS_AUGUR_DATA:
            return {
                "status": "degraded",
                "tickers": [],
                "note": "yfinance 未安装，热门标的不可用。",
            }
        from augur.data import fetch_hot_tickers
        tickers = fetch_hot_tickers(force_refresh=refresh)
        data = {"status": "ok", "tickers": tickers}
        # ETag support
        data_json = json.dumps(data, sort_keys=True, default=str)
        etag = hashlib.md5(data_json.encode()).hexdigest()
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            return JSONResponse(status_code=304, content=None, headers={"ETag": f'"{etag}"'})
        return JSONResponse(content=data, headers={"ETag": f'"{etag}"'})
    except Exception as e:
        logger.warning("hot tickers failed: %s", e)
        return {"status": "error", "tickers": [], "error": str(e)}


# ============ Market Overview API Routes ============

@app.get("/api/market-overview", summary="全球市场总览")
async def api_market_overview(request: Request, refresh: bool = False):
    """市场总览快照：主要指数、VIX、利率、商品、加密的实时价与涨跌幅。

    供首页 Dashboard 的「全球市场总览」板块使用。无 yfinance 时优雅降级为空列表。
    """
    if not _HAS_AUGUR_DATA:
        return {
            "status": "degraded",
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": [],
            "source": "none",
            "note": "yfinance 未安装，市场总览不可用。安装: pip install 'augur-agents[data]'",
        }
    try:
        from augur.data import fetch_market_overview
        overview = fetch_market_overview(force_refresh=refresh)
        data = {"status": "ok", **overview}
        # ETag support
        data_json = json.dumps(data, sort_keys=True, default=str)
        etag = hashlib.md5(data_json.encode()).hexdigest()
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            return JSONResponse(status_code=304, content=None, headers={"ETag": f'"{etag}"'})
        return JSONResponse(content=data, headers={"ETag": f'"{etag}"'})
    except Exception as e:
        logger.warning("market overview failed: %s", e)
        return {
            "status": "degraded",
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": [],
            "source": "none",
            "note": f"市场总览获取失败: {e}",
        }


@app.get("/api/market-movers", summary="涨跌幅领先")
async def api_market_movers():
    """Top 5 gainers and top 5 losers extracted from hot tickers data.

    Returns: {"status": "ok", "gainers": [...], "losers": [...]}
    """
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "gainers": [], "losers": []}
    try:
        from augur.data import fetch_hot_tickers
        tickers = fetch_hot_tickers(force_refresh=False)
        if not tickers:
            return {"status": "degraded", "gainers": [], "losers": []}
        sorted_tickers = sorted(tickers, key=lambda t: t.get("change_pct", 0), reverse=True)
        gainers = sorted_tickers[:5]
        losers = sorted_tickers[-5:][::-1]  # worst first
        return {"status": "ok", "gainers": gainers, "losers": losers}
    except Exception as e:
        logger.warning("market movers failed: %s", e)
        return {"status": "degraded", "gainers": [], "losers": [], "error": str(e)}


@app.get("/api/crypto-overview", summary="加密货币总览")
async def api_crypto_overview():
    """Fetch BTC, ETH, SOL, DOGE, XRP prices and 24h change from yfinance.

    Returns: {"status": "ok", "coins": [{symbol, name, price, change_pct, market_cap}]}
    """
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "coins": []}

    CRYPTO_SYMBOLS = [
        ("BTC-USD", "Bitcoin"),
        ("ETH-USD", "Ethereum"),
        ("SOL-USD", "Solana"),
        ("DOGE-USD", "Dogecoin"),
        ("XRP-USD", "XRP"),
    ]

    try:
        yf = __import__("yfinance")
    except ImportError:
        return {"status": "degraded", "coins": []}

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    def _safe_float_local(value):
        try:
            f = float(value)
            if f != f or f in (float("inf"), float("-inf")):
                return 0.0
            return f
        except (TypeError, ValueError):
            return 0.0

    def _fetch_crypto(entry):
        symbol, name = entry
        price = 0.0
        prev = 0.0
        market_cap = 0.0
        try:
            tk = yf.Ticker(symbol)
            fi = getattr(tk, "fast_info", None)
            if fi is not None:
                price = _safe_float_local(getattr(fi, "last_price", 0))
                prev = _safe_float_local(getattr(fi, "previous_close", 0))
                market_cap = _safe_float_local(getattr(fi, "market_cap", 0))
            if price <= 0 or prev <= 0:
                hist = tk.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = [c for c in hist["Close"].tolist() if c and c == c]
                    if closes:
                        price = price or float(closes[-1])
                        prev = prev or (float(closes[-2]) if len(closes) >= 2 else float(closes[-1]))
        except Exception as exc:
            logger.debug("crypto fetch failed for %s: %s", symbol, exc)
        change_pct = ((price - prev) / prev) if prev else 0.0
        return {
            "symbol": symbol,
            "name": name,
            "price": round(price, 2),
            "change_pct": round(change_pct, 4),
            "market_cap": round(market_cap, 0),
        }

    coins = []
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_fetch_crypto, entry): entry for entry in CRYPTO_SYMBOLS}
            for future in futures:
                try:
                    coin = future.result(timeout=10)
                    coins.append(coin)
                except (FuturesTimeoutError, Exception) as exc:
                    entry = futures[future]
                    logger.debug("crypto timeout for %s: %s", entry[0], exc)
                    coins.append({"symbol": entry[0], "name": entry[1], "price": 0.0, "change_pct": 0.0, "market_cap": 0.0})
    except Exception as e:
        logger.warning("crypto overview failed: %s", e)
        return {"status": "degraded", "coins": []}

    return {"status": "ok", "coins": coins}


@app.get("/api/commodities", summary="大宗商品行情")
async def api_commodities():
    """Fetch Gold, Silver, Oil (WTI), Natural Gas prices and changes from yfinance.

    Returns: {"status": "ok", "commodities": [{symbol, name, price, change_pct}]}
    """
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "commodities": []}

    COMMODITY_SYMBOLS = [
        ("GC=F", "Gold"),
        ("SI=F", "Silver"),
        ("CL=F", "Oil WTI"),
        ("NG=F", "Natural Gas"),
    ]

    try:
        yf = __import__("yfinance")
    except ImportError:
        return {"status": "degraded", "commodities": []}

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    def _safe_float_local(value):
        try:
            f = float(value)
            if f != f or f in (float("inf"), float("-inf")):
                return 0.0
            return f
        except (TypeError, ValueError):
            return 0.0

    def _fetch_commodity(entry):
        symbol, name = entry
        price = 0.0
        prev = 0.0
        try:
            tk = yf.Ticker(symbol)
            fi = getattr(tk, "fast_info", None)
            if fi is not None:
                price = _safe_float_local(getattr(fi, "last_price", 0))
                prev = _safe_float_local(getattr(fi, "previous_close", 0))
            if price <= 0 or prev <= 0:
                hist = tk.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = [c for c in hist["Close"].tolist() if c and c == c]
                    if closes:
                        price = price or float(closes[-1])
                        prev = prev or (float(closes[-2]) if len(closes) >= 2 else float(closes[-1]))
        except Exception as exc:
            logger.debug("commodity fetch failed for %s: %s", symbol, exc)
        change_pct = ((price - prev) / prev) if prev else 0.0
        return {
            "symbol": symbol,
            "name": name,
            "price": round(price, 2),
            "change_pct": round(change_pct, 4),
        }

    commodities = []
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_fetch_commodity, entry): entry for entry in COMMODITY_SYMBOLS}
            for future in futures:
                try:
                    item = future.result(timeout=10)
                    commodities.append(item)
                except (FuturesTimeoutError, Exception) as exc:
                    entry = futures[future]
                    logger.debug("commodity timeout for %s: %s", entry[0], exc)
                    commodities.append({"symbol": entry[0], "name": entry[1], "price": 0.0, "change_pct": 0.0})
    except Exception as e:
        logger.warning("commodities fetch failed: %s", e)
        return {"status": "degraded", "commodities": []}

    return {"status": "ok", "commodities": commodities}


@app.get("/api/treasury-rates", summary="美国国债收益率")
async def api_treasury_rates():
    """Fetch US 2Y, 5Y, 10Y, 30Y treasury yields from yfinance.

    Symbols: ^IRX (13-week as 2Y proxy), ^FVX (5Y), ^TNX (10Y), ^TYX (30Y)
    Returns: {"status": "ok", "rates": [{maturity, symbol, yield_pct}]}
    """
    if not _HAS_AUGUR_DATA:
        return {"status": "degraded", "rates": []}

    TREASURY_SYMBOLS = [
        ("^IRX", "2Y", "US 2-Year"),
        ("^FVX", "5Y", "US 5-Year"),
        ("^TNX", "10Y", "US 10-Year"),
        ("^TYX", "30Y", "US 30-Year"),
    ]

    try:
        yf = __import__("yfinance")
    except ImportError:
        return {"status": "degraded", "rates": []}

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    def _safe_float_local(value):
        try:
            f = float(value)
            if f != f or f in (float("inf"), float("-inf")):
                return 0.0
            return f
        except (TypeError, ValueError):
            return 0.0

    def _fetch_rate(entry):
        symbol, maturity, name = entry
        yield_pct = 0.0
        try:
            tk = yf.Ticker(symbol)
            fi = getattr(tk, "fast_info", None)
            if fi is not None:
                yield_pct = _safe_float_local(getattr(fi, "last_price", 0))
            if yield_pct <= 0:
                hist = tk.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = [c for c in hist["Close"].tolist() if c and c == c]
                    if closes:
                        yield_pct = float(closes[-1])
        except Exception as exc:
            logger.debug("treasury rate fetch failed for %s: %s", symbol, exc)
        return {
            "maturity": maturity,
            "symbol": symbol,
            "name": name,
            "yield_pct": round(yield_pct, 3),
        }

    rates = []
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_fetch_rate, entry): entry for entry in TREASURY_SYMBOLS}
            for future in futures:
                try:
                    item = future.result(timeout=10)
                    rates.append(item)
                except (FuturesTimeoutError, Exception) as exc:
                    entry = futures[future]
                    logger.debug("treasury rate timeout for %s: %s", entry[0], exc)
                    rates.append({"maturity": entry[1], "symbol": entry[0], "name": entry[2], "yield_pct": 0.0})
    except Exception as e:
        logger.warning("treasury rates fetch failed: %s", e)
        return {"status": "degraded", "rates": []}

    return {"status": "ok", "rates": rates}


@app.get("/api/fear-greed", summary="恐慌与贪婪指数")
async def api_fear_greed():
    """基于 VIX 计算恐慌与贪婪指数 (0-100)。

    公式: index = max(0, min(100, 100 - ((VIX - 12) / 38) * 100))
    0-25: Extreme Fear, 25-45: Fear, 45-55: Neutral, 55-75: Greed, 75-100: Extreme Greed
    """
    if not _HAS_AUGUR_DATA:
        return {
            "status": "degraded",
            "index": 50,
            "label": "Neutral",
            "vix_value": 0.0,
            "description": "yfinance 未安装，无法计算实时恐慌贪婪指数",
        }
    try:
        from augur.data import fetch_market_overview
        overview = fetch_market_overview(force_refresh=False)
        items = overview.get("items", [])
        vix_item = next((it for it in items if it.get("key") == "vix"), None)
        if not vix_item or not vix_item.get("price"):
            return {
                "status": "degraded",
                "index": 50,
                "label": "Neutral",
                "vix_value": 0.0,
                "description": "VIX 数据暂时不可用",
            }
        vix_val = float(vix_item["price"])
        index = max(0, min(100, int(100 - ((vix_val - 12) / 38) * 100)))
        if index >= 75:
            label = "Extreme Greed"
            desc = f"VIX={vix_val:.2f}，市场处于极度贪婪状态，波动率极低"
        elif index >= 55:
            label = "Greed"
            desc = f"VIX={vix_val:.2f}，市场偏贪婪，投资者情绪乐观"
        elif index >= 45:
            label = "Neutral"
            desc = f"VIX={vix_val:.2f}，市场情绪中性"
        elif index >= 25:
            label = "Fear"
            desc = f"VIX={vix_val:.2f}，市场偏恐慌，投资者趋于谨慎"
        else:
            label = "Extreme Fear"
            desc = f"VIX={vix_val:.2f}，市场处于极度恐慌状态，波动率极高"
        return {
            "status": "ok",
            "index": index,
            "label": label,
            "vix_value": vix_val,
            "description": desc,
        }
    except Exception as e:
        logger.warning("fear-greed calc failed: %s", e)
        return {
            "status": "degraded",
            "index": 50,
            "label": "Neutral",
            "vix_value": 0.0,
            "description": f"恐慌贪婪指数计算失败: {e}",
        }


@app.get("/api/datasources", summary="数据源状态")
async def api_datasources():
    """返回当前可用的数据源链（用于 UI 展示数据来源覆盖情况）。"""
    try:
        from augur.datasources import available_sources
        sources = available_sources()
    except Exception:
        sources = ["yfinance", "stooq"]
    # 数据源元信息（中文展示名 + 是否需要 key + 覆盖范围）
    catalog = {
        "yfinance": {"label": "Yahoo Finance", "needs_key": False, "coverage": "行情+基本面+技术指标", "active": "yfinance" in sources},
        "finnhub": {"label": "Finnhub", "needs_key": True, "coverage": "基本面+分析师评级", "active": "finnhub" in sources, "env": "FINNHUB_API_KEY"},
        "alphavantage": {"label": "Alpha Vantage", "needs_key": True, "coverage": "基本面 OVERVIEW", "active": "alphavantage" in sources, "env": "ALPHAVANTAGE_API_KEY"},
        "stooq": {"label": "Stooq", "needs_key": False, "coverage": "行情兜底 (CSV)", "active": "stooq" in sources},
    }
    return {"status": "ok", "active_chain": sources, "catalog": catalog}


# ============ Config Export/Import + Test Endpoints ============

@app.get("/api/config/export", summary="导出配置")
async def api_config_export():
    """Export full config as JSON for backup/migration."""
    config = get_config()
    return JSONResponse(content=config)


@app.post("/api/config/import", summary="导入配置")
async def api_config_import(request: Request):
    """Import config from JSON body."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    # Validate and set config
    for key, value in body.items():
        set_config(key, value)
    save_config()
    return {"status": "ok", "message": "配置已导入"}


@app.post("/api/config/test-datasource", summary="测试数据源连接")
async def api_test_datasource(request: Request):
    """Test datasource connectivity."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    source = body.get("source", "")
    if source == "finnhub":
        config = get_config()
        key = (config.get("datasource_keys") or {}).get("finnhub", "")
        env_key = os.environ.get("FINNHUB_API_KEY", "")
        api_key = key or env_key
        if not api_key:
            return {"status": "error", "detail": "未配置 Finnhub API Key"}
        try:
            import urllib.request
            url = f"https://finnhub.io/api/v1/stock/profile2?symbol=AAPL&token={api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Augur/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Finnhub 连接成功"}
        except Exception as e:
            return {"status": "error", "detail": f"连接失败: {e}"}
    elif source == "alphavantage":
        config = get_config()
        key = (config.get("datasource_keys") or {}).get("alphavantage", "")
        env_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        api_key = key or env_key
        if not api_key:
            return {"status": "error", "detail": "未配置 Alpha Vantage API Key"}
        try:
            import urllib.request
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Augur/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Alpha Vantage 连接成功"}
        except Exception as e:
            return {"status": "error", "detail": f"连接失败: {e}"}
    else:
        return {"status": "error", "detail": f"未知数据源: {source}"}
    return {"status": "error", "detail": "连接测试失败"}


@app.post("/api/config/test-notification", summary="测试通知渠道")
async def api_test_notification(request: Request):
    """Test notification channel connectivity."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    channel = body.get("channel", "")
    config = get_config()
    notifications = config.get("notifications") or {}

    if channel == "telegram":
        token = notifications.get("telegram_token", "")
        chat_id = notifications.get("telegram_chat_id", "")
        if not token or not chat_id:
            return {"status": "error", "detail": "请先配置 Telegram Bot Token 和 Chat ID"}
        try:
            import urllib.request
            import json as _json
            msg = "Augur 测试消息: 通知渠道配置成功!"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = _json.dumps({"chat_id": chat_id, "text": msg}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Telegram 测试消息已发送"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    elif channel == "slack":
        webhook = notifications.get("slack_webhook", "")
        if not webhook:
            return {"status": "error", "detail": "请先配置 Slack Webhook URL"}
        try:
            import urllib.request
            import json as _json
            data = _json.dumps({"text": "Augur 测试消息: Slack 通知渠道配置成功!"}).encode()
            req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Slack 测试消息已发送"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    else:
        return {"status": "error", "detail": f"不支持的通知渠道: {channel}"}
    return {"status": "error", "detail": "测试失败"}


# ============ Notification API Routes ============

class NotificationTestBody(BaseModel):
    channel: str  # telegram, slack, wechat, lark


@app.post("/api/notifications/test", summary="发送测试通知")
async def api_notifications_test(body: NotificationTestBody):
    """Test notification channel by sending a test message."""
    channel = body.channel.lower()
    if channel not in ("telegram", "slack", "wechat", "lark"):
        raise HTTPException(status_code=400, detail=f"Unsupported channel: {channel}")

    config = get_config()
    notifications = config.get("notifications") or {}

    if channel == "telegram":
        token = notifications.get("telegram_token", "")
        chat_id = notifications.get("telegram_chat_id", "")
        if not token or not chat_id:
            return {"status": "error", "detail": "请先配置 Telegram Bot Token 和 Chat ID"}
        try:
            from augur.bots.telegram_bot import send_message
            send_message(token, chat_id, "Augur 测试通知: 通道配置成功!")
            return {"status": "ok", "detail": "Telegram 测试消息已发送"}
        except ImportError:
            # Fallback to direct HTTP
            try:
                import urllib.request
                import json as _json
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = _json.dumps({"chat_id": chat_id, "text": "Augur 测试通知: 通道配置成功!"}).encode()
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "ok", "detail": "Telegram 测试消息已发送"}
            except Exception as e:
                return {"status": "error", "detail": f"发送失败: {e}"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    elif channel == "slack":
        webhook = notifications.get("slack_webhook", "")
        if not webhook:
            return {"status": "error", "detail": "请先配置 Slack Webhook URL"}
        try:
            import urllib.request
            import json as _json
            data = _json.dumps({"text": "Augur 测试通知: Slack 通道配置成功!"}).encode()
            req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Slack 测试消息已发送"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    elif channel == "lark":
        webhook = notifications.get("lark_webhook", "")
        if not webhook:
            return {"status": "error", "detail": "请先配置飞书 Webhook URL"}
        try:
            import urllib.request
            import json as _json
            data = _json.dumps({"msg_type": "text", "content": {"text": "Augur 测试通知: 飞书通道配置成功!"}}).encode()
            req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "飞书测试消息已发送"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    elif channel == "wechat":
        return {"status": "error", "detail": "微信通知需要企业微信配置，请参考文档"}

    return {"status": "error", "detail": "测试失败"}


@app.post("/api/notifications/config", summary="保存通知配置")
async def api_notifications_config_save(request: Request):
    """Save notification configuration to config/notifications.yaml."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    config_dir = Path(__file__).parent.parent / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "notifications.yaml"
    config_file.write_text(yaml.dump(body, allow_unicode=True), encoding="utf-8")
    # Also update in-memory config
    set_config("notifications", body)
    save_config()
    return {"status": "ok", "message": "通知配置已保存"}


@app.get("/api/notifications/config", summary="获取通知配置")
async def api_notifications_config_get():
    """Read notification configuration."""
    config_dir = Path(__file__).parent.parent / "config"
    config_file = config_dir / "notifications.yaml"
    if config_file.exists():
        try:
            data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
            return {"status": "ok", "config": data}
        except Exception:
            pass
    # Fallback to in-memory config
    config = get_config()
    return {"status": "ok", "config": config.get("notifications", {})}


# ============ Cron Config API Routes ============


class CronConfigBody(BaseModel):
    """Request body for cron config update."""
    schedule: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None


@app.get("/api/cron/config", summary="获取定时监控配置")
async def api_get_cron_config():
    """返回当前 cron 配置 (schedule + notifications sections from watchlist.yaml)"""
    from augur.cron import load_watchlist
    config = load_watchlist()
    return {
        "status": "ok",
        "schedule": config.get("schedule", {}),
        "notifications": config.get("notifications", {}),
    }


@app.put("/api/cron/config", summary="更新定时监控配置")
async def api_put_cron_config(body: CronConfigBody):
    """更新 schedule/notifications sections in watchlist.yaml"""
    from augur.cron import load_watchlist, save_watchlist
    config = load_watchlist()

    if body.schedule is not None:
        config["schedule"] = body.schedule
    if body.notifications is not None:
        config["notifications"] = body.notifications

    save_watchlist(config)
    return {
        "status": "ok",
        "message": "定时监控配置已更新",
        "schedule": config.get("schedule", {}),
        "notifications": config.get("notifications", {}),
    }


@app.post("/api/cron/run-now", summary="立即执行一次监控分析")
async def api_cron_run_now():
    """触发一次 watchlist 分析并返回结果"""
    from augur.cron import run_watchlist_analysis

    try:
        results = run_watchlist_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析执行失败: {e}")

    # Serialize results for JSON response
    serialized = []
    for r in results:
        consensus = r.get("consensus")
        item = {
            "ticker": r.get("ticker", ""),
            "message": r.get("message", ""),
        }
        if consensus is not None:
            item["signal"] = consensus.signal.value if hasattr(consensus, "signal") else ""
            item["score"] = round(consensus.score, 1) if hasattr(consensus, "score") else 0
            item["confidence"] = round(consensus.confidence, 2) if hasattr(consensus, "confidence") else 0
        serialized.append(item)

    return {
        "status": "ok",
        "count": len(serialized),
        "results": serialized,
    }


# ============ Sector Performance API Route ============

@app.get("/api/sector-performance", summary="板块行情")
async def api_sector_performance(request: Request, refresh: bool = False):
    """板块ETF行情：XLK, XLV, XLF, XLE, XLY, XLP, XLI, XLU。

    供首页「板块行情」面板使用。无 yfinance 时优雅降级为空列表。
    """
    if not _HAS_AUGUR_DATA:
        return {
            "status": "degraded",
            "sectors": [],
            "note": "yfinance 未安装，板块行情不可用。",
        }

    sector_etfs = [
        ("XLK", "科技", "Technology"),
        ("XLV", "医疗", "Healthcare"),
        ("XLF", "金融", "Financials"),
        ("XLE", "能源", "Energy"),
        ("XLY", "可选消费", "Consumer Disc."),
        ("XLP", "必需消费", "Consumer Staples"),
        ("XLI", "工业", "Industrials"),
        ("XLU", "公用事业", "Utilities"),
        ("XLRE", "房地产", "Real Estate"),
        ("XLB", "材料", "Materials"),
        ("XLC", "通信", "Communication"),
    ]

    try:
        import yfinance as yf

        sectors = []
        for symbol, cn_name, en_name in sector_etfs:
            try:
                tk = yf.Ticker(symbol)
                fi = getattr(tk, "fast_info", None)
                price = 0.0
                prev = 0.0
                if fi is not None:
                    price = float(getattr(fi, "last_price", 0) or 0)
                    prev = float(getattr(fi, "previous_close", 0) or 0)
                if price <= 0 or prev <= 0:
                    hist = tk.history(period="5d")
                    if hist is not None and not hist.empty:
                        closes = [c for c in hist["Close"].tolist() if c and c == c]
                        if closes:
                            price = price or float(closes[-1])
                            prev = prev or (float(closes[-2]) if len(closes) >= 2 else float(closes[-1]))
                change_pct = ((price - prev) / prev) if prev else 0.0
                sectors.append({
                    "symbol": symbol,
                    "name": cn_name,
                    "en_name": en_name,
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 4),
                })
            except Exception as exc:
                logger.debug("sector fetch failed for %s: %s", symbol, exc)
                sectors.append({
                    "symbol": symbol,
                    "name": cn_name,
                    "en_name": en_name,
                    "price": 0,
                    "change_pct": 0,
                })

        data = {
            "status": "ok",
            "sectors": sectors,
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        # ETag support
        data_json = json.dumps(data, sort_keys=True, default=str)
        etag = hashlib.md5(data_json.encode()).hexdigest()
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            return JSONResponse(status_code=304, content=None, headers={"ETag": f'"{etag}"'})
        return JSONResponse(content=data, headers={"ETag": f'"{etag}"'})
    except ImportError:
        return {
            "status": "degraded",
            "sectors": [],
            "note": "yfinance 未安装，板块行情不可用。",
        }
    except Exception as e:
        logger.warning("sector performance failed: %s", e)
        return {
            "status": "degraded",
            "sectors": [],
            "note": f"板块行情获取失败: {e}",
        }


# ============ v8: I18n helpers ============

_i18n_cache: Dict[str, Dict[str, Any]] = {}

def _load_translations(lang: str = "zh") -> Dict[str, Any]:
    if lang in _i18n_cache:
        return _i18n_cache[lang]
    i18n_dir = Path(__file__).parent / "i18n"
    filepath = i18n_dir / f"{lang}.json"
    if filepath.exists():
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            _i18n_cache[lang] = data
            return data
        except Exception:
            pass
    return {}

def _i18n_context(lang: str = "zh", request: Request = None) -> Dict[str, Any]:
    if request is not None and lang == "zh":
        cookie_lang = request.cookies.get("augur_lang")
        if cookie_lang in ("en", "zh"):
            lang = cookie_lang
    return {"t": _load_translations(lang), "lang": lang}


# ============ v8: History helpers ============

def _save_history_safe(ticker: str, result: Any) -> None:
    try:
        from augur.history import save_analysis
        save_analysis(ticker, result)
    except Exception:
        pass


# ============ v8: History API ============

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse(request=request, name="history.html", context={"title": "历史记录"})


@app.get("/api/history")
async def api_list_history(limit: int = 50, page: Optional[int] = None, per_page: int = 20):
    from augur.history import list_history, count_history
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if page is not None:
        if page < 1 or per_page < 1:
            raise HTTPException(status_code=400, detail="page and per_page must be >= 1")
        if per_page > 100:
            raise HTTPException(status_code=400, detail="per_page must be <= 100")
        try:
            total = count_history()
            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            records = list_history(page=page, per_page=per_page)
        except Exception as e:
            # Graceful degradation: storage may be locked, corrupt, or missing
            logger.warning("history list (paginated) failed: %s", e)
            return {"items": [], "total": 0, "page": page, "per_page": per_page, "pages": 0, "error": "history_unavailable", "message": f"历史记录读取失败: {e}"}
        return {"items": records, "total": total, "page": page, "per_page": per_page, "pages": total_pages}
    try:
        records = list_history(limit=limit)
    except Exception as e:
        logger.warning("history list failed: %s", e)
        return {"records": [], "count": 0, "error": "history_unavailable", "message": f"历史记录读取失败: {e}"}
    return {"records": records, "count": len(records)}


@app.get("/api/history/{history_id}")
async def api_get_history(history_id: str):
    # Validate history_id format to prevent path traversal / injection
    if not re.match(r'^[A-Za-z0-9._\-]{1,64}$', history_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid history_id format. Use 1-64 alphanumeric characters, dots, hyphens, or underscores.",
        )
    from augur.history import get_history
    record = get_history(history_id)
    if not record:
        raise HTTPException(status_code=404, detail="History record not found")
    return record


@app.delete("/api/history/{history_id}")
async def api_delete_history_item(history_id: str):
    # Validate history_id format to prevent path traversal / injection
    if not re.match(r'^[A-Za-z0-9._\-]{1,64}$', history_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid history_id format. Use 1-64 alphanumeric characters, dots, hyphens, or underscores.",
        )
    from augur.history import delete_history
    deleted = delete_history(history_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History record not found")
    return {"status": "ok", "message": "已删除"}


@app.delete("/api/history")
async def api_clear_history():
    from augur.history import clear_history
    try:
        count = clear_history()
    except Exception as e:
        # Graceful degradation: storage failure
        logger.warning("clear history failed: %s", e)
        raise HTTPException(status_code=500, detail=f"清除历史记录失败: {e}")
    return {"status": "ok", "deleted": count, "message": f"已清除 {count} 条记录"}


# ============ v8: Compare & Debate ============

class CompareBody(BaseModel):
    ticker: str
    agent_ids: List[str]

class DebateBody(BaseModel):
    ticker: str
    agent_ids: List[str]


@app.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request):
    ctx = {"title": "大师对决", "personas": _persona_meta()}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="compare.html", context=ctx)


@app.get("/debate", response_class=HTMLResponse)
async def debate_page(request: Request):
    ctx = {"title": "投资辩论", "personas": _persona_meta()}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="debate.html", context=ctx)


@app.get("/performance", response_class=HTMLResponse)
async def performance_page(request: Request):
    ctx = {"title": "大师排行榜"}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="performance.html", context=ctx)


@app.post("/api/compare")
async def api_compare(body: CompareBody):
    if not consume_endpoint_token("api_compare"):
        raise HTTPException(
            status_code=429,
            detail="Compare rate limit exceeded. Please wait and retry.",
        )
    ticker = body.ticker.strip().upper()
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    if len(body.agent_ids) < 2 or len(body.agent_ids) > 5:
        raise HTTPException(status_code=400, detail="需要2-5个投资人")
    if len(body.agent_ids) != len(set(body.agent_ids)):
        raise HTTPException(status_code=400, detail="投资人不能重复")
    registry = get_registry()
    for aid in body.agent_ids:
        if not registry.get(aid):
            raise HTTPException(status_code=404, detail=f"Agent '{aid}' not found")
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        ctx = MarketContext(ticker=ticker)
    agents_results = []
    for aid in body.agent_ids:
        agent = registry.get(aid)
        try:
            result = agent.analyze(ctx)
            agents_results.append(result.to_dict())
        except Exception as e:
            agents_results.append({"agent_id": aid, "agent_name": getattr(agent, "name", aid), "signal": "error", "score": 0, "confidence": 0, "reasoning": str(e), "key_findings": [], "risks": []})
    return {"ticker": ticker, "agent_count": len(agents_results), "agents": agents_results, "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.post("/api/debate")
async def api_debate(body: DebateBody):
    if not consume_endpoint_token("api_debate"):
        raise HTTPException(
            status_code=429,
            detail="Debate rate limit exceeded. Please wait and retry.",
        )
    ticker = body.ticker.strip().upper()
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    if len(body.agent_ids) < 2 or len(body.agent_ids) > 4:
        raise HTTPException(status_code=400, detail="需要2-4个投资人")
    if len(body.agent_ids) != len(set(body.agent_ids)):
        raise HTTPException(status_code=400, detail="投资人不能重复")
    registry = get_registry()
    for aid in body.agent_ids:
        if not registry.get(aid):
            raise HTTPException(status_code=404, detail=f"Agent '{aid}' not found")
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        ctx = MarketContext(ticker=ticker)
    rounds = []
    previous_reasoning = ""
    for i, aid in enumerate(body.agent_ids):
        agent = registry.get(aid)
        try:
            result = agent.analyze(ctx)
            reasoning = result.reasoning or ""
            if i > 0 and previous_reasoning:
                reasoning = f"[对前者观点的回应] {reasoning}"
            rounds.append({"agent_id": aid, "agent_name": result.agent_name, "signal": result.signal.value, "score": round(result.score, 1), "confidence": round(result.confidence, 2), "reasoning": reasoning, "round": i + 1})
            previous_reasoning = result.reasoning or ""
        except Exception as e:
            rounds.append({"agent_id": aid, "agent_name": getattr(agent, "name", aid), "signal": "error", "score": 0, "confidence": 0, "reasoning": str(e), "round": i + 1})
    signals = [r["signal"] for r in rounds if r["signal"] != "error"]
    buy_count = sum(1 for s in signals if s == "bullish")
    sell_count = sum(1 for s in signals if s == "bearish")
    if buy_count > sell_count:
        summary = f"辩论结束: {buy_count}/{len(signals)} 位投资人看多 {ticker}。"
    elif sell_count > buy_count:
        summary = f"辩论结束: {sell_count}/{len(signals)} 位投资人看空 {ticker}。"
    else:
        summary = f"辩论结束: 投资人对 {ticker} 分歧较大，建议多维度分析。"
    return {"ticker": ticker, "rounds": rounds, "summary": summary, "timestamp": datetime.utcnow().isoformat() + "Z"}


# ============ v8: WebSocket Analysis Streaming ============

@app.websocket("/ws/analyze/{ticker}")
async def ws_analyze(websocket: WebSocket, ticker: str):
    if not _ws_api_token_ok(websocket):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        await websocket.close(code=1008, reason="Invalid ticker format")
        return
    await websocket.accept()
    try:
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker.upper())
        except Exception:
            ctx = MarketContext(ticker=ticker.upper())
        registry = get_registry()
        all_agents = registry.get_all()
        total = len(all_agents)
        agent_responses = {}
        for i, agent in enumerate(all_agents, 1):
            try:
                result = agent.analyze(ctx)
                agent_responses[agent.agent_id] = result
                await websocket.send_json({"type": "agent", "agent_id": agent.agent_id, "agent_name": result.agent_name, "signal": result.signal.value, "score": round(result.score, 1), "confidence": round(result.confidence, 2), "reasoning": result.reasoning, "progress": f"{i}/{total}"})
            except Exception as e:
                await websocket.send_json({"type": "agent", "agent_id": agent.agent_id, "agent_name": getattr(agent, "name", agent.agent_id), "signal": "error", "score": 0, "confidence": 0, "reasoning": str(e), "progress": f"{i}/{total}"})
        coord = get_coordinator()
        consensus_resp = coord.get_consensus(agent_responses, ticker=ticker.upper(), context=ctx)
        consensus_dict = consensus_resp.to_dict()
        consensus_dict["type"] = "consensus"
        await websocket.send_json(consensus_dict)
        _save_history_safe(ticker.upper(), {"ticker": ticker.upper(), "consensus": consensus_resp.to_dict(), "agents": [r.to_dict() for r in agent_responses.values()], "agent_count": len(agent_responses)})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ============ v8: Real-time Price WebSocket ============

_price_streamer = None

def _get_price_streamer():
    global _price_streamer
    if _price_streamer is None:
        from augur.streaming import PriceStreamer
        _price_streamer = PriceStreamer(interval=60.0)
    return _price_streamer


def _ws_api_token_ok(websocket: WebSocket) -> bool:
    """WebSocket handshake bypasses HTTP middleware; enforce auth here."""
    return authenticate_websocket(websocket)


@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    if not _ws_api_token_ok(websocket):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    streamer = _get_price_streamer()
    if not await streamer.connect(websocket):
        await websocket.close(code=1008, reason="Too many connections")
        return
    registered = True
    try:
        await websocket.accept()
        if not streamer.is_running:
            await streamer.start()
        try:
            initial = {"type": "price_update", "prices": streamer.get_current_prices(), "timestamp": _time.time()}
            await websocket.send_text(json.dumps(initial))
        except Exception:
            pass
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if registered:
            await streamer.disconnect(websocket)


# ============ v8: Sentiment API ============

@app.get("/api/sentiment/{ticker}")
async def api_sentiment(ticker: str):
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    from augur.sentiment import SentimentAnalyzer
    try:
        result = SentimentAnalyzer().get_sentiment(ticker)
    except Exception as e:
        # Graceful degradation: return neutral sentiment rather than 500
        logger.warning("sentiment fetch failed for %s: %s", ticker.upper(), e)
        return {
            "ticker": ticker.upper(),
            "overall_score": 0.0,
            "sources": {"stocktwits_score": 0.0, "reddit_score": 0.0, "x_score": 0.0},
            "volume": 0,
            "trending": False,
            "data_source": "degraded",
            "error": str(e),
        }
    return {
        "ticker": result.ticker,
        "overall_score": result.overall_score,
        "sources": result.sources,
        "volume": result.volume,
        "trending": result.trending,
        "data_source": result.data_source,
    }


# ============ v8: AI Chat ============

_chat_engine = None

def _get_chat_engine():
    global _chat_engine
    if _chat_engine is None:
        from augur.chat import ChatEngine
        _chat_engine = ChatEngine()
    return _chat_engine


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    engine = _get_chat_engine()
    try:
        from augur.llm_client import is_llm_available
        llm_enabled = is_llm_available()
    except Exception:
        llm_enabled = False
    ctx = {"title": "AI Chat", "agents": engine.get_available_agents(), "llm_enabled": llm_enabled}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="chat.html", context=ctx)


class ChatBody(BaseModel):
    message: str
    agent_id: Optional[str] = None


@app.post("/api/chat")
async def api_chat(body: ChatBody):
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    if len(body.message) > 2000:
        raise HTTPException(status_code=400, detail="消息过长（最多2000字符）")
    if body.agent_id and not re.match(r'^[a-z_]{1,50}$', body.agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    try:
        return _get_chat_engine().get_response(body.message, body.agent_id)
    except KeyError as e:
        # Unknown agent_id surfaced by engine
        raise HTTPException(status_code=404, detail=f"Agent '{body.agent_id}' not found: {e}")
    except ValueError as e:
        # Engine validation rejected the input
        raise HTTPException(status_code=400, detail=f"Invalid chat request: {e}")
    except Exception as e:
        # Engine internal error — degrade gracefully
        logger.warning("chat engine failed: %s", e)
        raise HTTPException(status_code=500, detail=f"聊天服务暂时不可用: {e}")


# ============ v8: Multi-User Auth (opt-in via AUGUR_MULTI_USER=1) ============

class AuthRegisterBody(BaseModel):
    username: str
    password: str

class AuthLoginBody(BaseModel):
    username: str
    password: str


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login"})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"title": "Register"})


@app.post("/api/auth/register")
async def api_auth_register(body: AuthRegisterBody, request: Request):
    from augur.users import UserManager, is_multi_user_enabled
    if not is_multi_user_enabled():
        raise HTTPException(status_code=403, detail="Set AUGUR_MULTI_USER=1 to enable multi-user mode.")
    client_ip = request.client.host if request.client else "unknown"
    if not check_auth_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many auth attempts. Try again later.")
    if not body.username or not 3 <= len(body.username) <= 32 or not re.match(r'^[a-zA-Z0-9_]+$', body.username):
        raise HTTPException(status_code=400, detail="Username: 3-32 chars, letters/numbers/underscore only.")
    if not body.password or not 6 <= len(body.password) <= 128:
        raise HTTPException(status_code=400, detail="Password must be 6-128 characters.")
    manager = UserManager()
    user = manager.create_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=400, detail="Username already exists or invalid.")
    return {"status": "ok", "username": user["username"], "id": user["id"]}


@app.post("/api/auth/login")
async def api_auth_login(body: AuthLoginBody, request: Request):
    from augur.users import UserManager, is_multi_user_enabled
    if not is_multi_user_enabled():
        raise HTTPException(status_code=403, detail="Set AUGUR_MULTI_USER=1 to enable multi-user mode.")
    client_ip = request.client.host if request.client else "unknown"
    if not check_auth_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many auth attempts. Try again later.")
    if not body.username or len(body.username) > 32 or not body.password or len(body.password) > 128:
        raise HTTPException(status_code=400, detail="Invalid credentials.")
    token = UserManager().authenticate(body.username, body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {"status": "ok", "token": token, "username": body.username}


# ============ v8: Rules Engine ============

_rules_engine = None

def _get_rules_engine():
    global _rules_engine
    if _rules_engine is None:
        from augur.rules import RulesEngine
        _rules_engine = RulesEngine()
    return _rules_engine


class RuleCreateBody(BaseModel):
    name: str
    conditions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    enabled: bool = True


@app.get("/api/rules")
async def api_list_rules():
    engine = _get_rules_engine()
    rules = engine.get_rules()
    return {"rules": [r.to_dict() for r in rules], "count": len(rules)}


@app.post("/api/rules")
async def api_create_rule(body: RuleCreateBody):
    from augur.rules import Rule
    if not body.name or len(body.name) > 100:
        raise HTTPException(status_code=400, detail="Rule name: 1-100 characters.")
    engine = _get_rules_engine()
    rule = Rule(id="", name=body.name, conditions=body.conditions, actions=body.actions, enabled=body.enabled)
    created = engine.add_rule(rule)
    return {"status": "ok", "rule": created.to_dict()}


@app.delete("/api/rules/{rule_id}")
async def api_delete_rule(rule_id: str):
    # Validate rule_id format to prevent path traversal / injection
    if not re.match(r'^[A-Za-z0-9._\-]{1,64}$', rule_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid rule_id format. Use 1-64 alphanumeric characters, dots, hyphens, or underscores.",
        )
    engine = _get_rules_engine()
    if not engine.remove_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return {"status": "ok", "message": "Rule deleted"}


# ============ v8: Portfolio Optimizer ============

class OptimizeBody(BaseModel):
    tickers: List[str]
    risk_free_rate: float = 0.02


@app.get("/optimizer", response_class=HTMLResponse)
async def optimizer_page(request: Request):
    ctx = {"title": "Portfolio Optimizer"}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="optimizer.html", context=ctx)


@app.post("/api/optimize")
async def api_optimize(body: OptimizeBody):
    if not consume_endpoint_token("api_optimize"):
        raise HTTPException(
            status_code=429,
            detail="Optimize rate limit exceeded. Please wait and retry.",
        )
    from augur.optimizer import PortfolioOptimizer
    import random
    if not body.tickers or len(body.tickers) > 10:
        raise HTTPException(status_code=400, detail="需要1-10个股票代码")
    for t in body.tickers:
        if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', t):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {t}")

    returns_data = {}
    data_source = "mock"

    # Phase A: try to fetch real 3-month daily returns from yfinance
    try:
        from augur.data import fetch_history
        real_count = 0
        for ticker in body.tickers:
            hist = fetch_history(ticker.upper(), period="3mo")
            if hist and len(hist) >= 10:
                closes = [h["close"] for h in hist if h.get("close") and h["close"] > 0]
                if len(closes) >= 10:
                    daily_returns = [
                        (closes[i] - closes[i - 1]) / closes[i - 1]
                        for i in range(1, len(closes))
                    ]
                    returns_data[ticker.upper()] = daily_returns
                    real_count += 1
        if real_count == len(body.tickers):
            data_source = "live"
        elif real_count > 0:
            data_source = "partial"
    except Exception:
        pass

    # Fallback: deterministic mock for any ticker still missing
    for ticker in body.tickers:
        if ticker.upper() not in returns_data:
            seed = int(hashlib.sha256(ticker.upper().encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
            returns_data[ticker.upper()] = [rng.gauss(0.001, 0.02) for _ in range(60)]

    result = PortfolioOptimizer().optimize(returns_data, risk_free_rate=body.risk_free_rate)
    return {
        "status": "ok",
        "portfolio": result.to_dict(),
        "tickers": [t.upper() for t in body.tickers],
        "data_source": data_source,
    }


# ============ v8: I18n API ============

@app.get("/api/i18n/{lang}")
async def api_i18n(lang: str):
    if lang not in ("en", "zh"):
        raise HTTPException(status_code=400, detail="Supported languages: en, zh")
    i18n_dir = Path(__file__).parent / "i18n"
    filepath = i18n_dir / f"{lang}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Language file not found: {lang}")
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        # File exists but content is corrupt — surface as 500 with explanation
        raise HTTPException(status_code=500, detail=f"翻译文件格式错误: {e}")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=500, detail=f"翻译文件编码错误: {e}")
    except OSError as e:
        # Permission / IO error reading the file
        raise HTTPException(status_code=500, detail=f"翻译文件读取失败: {e}")
    return data


@app.post("/api/lang/{lang}")
async def api_set_lang(lang: str):
    if lang not in ("en", "zh"):
        raise HTTPException(status_code=400, detail="Supported languages: en, zh")
    response = JSONResponse(content={"status": "ok", "lang": lang})
    response.set_cookie(key="augur_lang", value=lang, max_age=365 * 24 * 3600, httponly=False, samesite="lax")
    return response


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
