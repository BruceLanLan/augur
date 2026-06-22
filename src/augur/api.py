# -*- coding: utf-8 -*-
"""
augur.api - REST API (FastAPI)

Provides endpoints:
  GET /api/personas - list all personas
  GET /api/analyze/{ticker} - analyze with all agents
  GET /api/persona/{agent_id} - get single persona info
  POST /api/workflow - run multi-step agentic pipeline
  GET /health - health check
"""

import os
import re
import logging
from datetime import datetime, timezone
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    from starlette.exceptions import HTTPException as StarletteHTTPException
except ImportError:
    raise ImportError("fastapi is required: pip install fastapi uvicorn")

from augur.auth import auth_required, authenticate_request

# Ticker pattern: 1-15 alphanumeric, dot, hyphen, or colon (e.g. BRK.B, 0700.HK, BTC-USD)
_TICKER_PATTERN = re.compile(r'^[A-Za-z0-9.\-:]{1,15}$')

from augur.registry import AgentRegistry, DecisionCoordinator
from augur.personas.base import MarketContext
from augur.errors import HTTP_ERROR_ENVELOPE, api_error_response

app = FastAPI(
    title="Augur API",
    description="Multi-agent investment analysis API",
    version="10.15.1",
)


# Global exception handler: catch unhandled exceptions, return consistent JSON
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Catch all unhandled exceptions and return consistent JSON error response."""
    logger = logging.getLogger("augur.api")
    logger.error(f"Unhandled exception on {request.url.path}: {type(exc).__name__}: {exc}")

    code, suggestion = HTTP_ERROR_ENVELOPE[500]
    return JSONResponse(
        status_code=500,
        content=api_error_response(
            detail="Internal server error",
            code=code,
            suggestion=suggestion,
            path=request.url.path,
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return the standard JSON error envelope for HTTP errors."""
    code, suggestion = HTTP_ERROR_ENVELOPE.get(
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


# CORS: restrict to a configurable allowlist to prevent any-origin access
# in deployments with auth. Set AUGUR_CORS_ALLOW_ORIGINS to a comma-separated
# list of allowed origins (e.g. "https://app.example.com,https://admin.example.com").
# Default is "*" for backwards compatibility with local/dev usage.
_cors_origins_env = os.environ.get("AUGUR_CORS_ALLOW_ORIGINS", "").strip()
if _cors_origins_env:
    _cors_allow_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
else:
    _cors_allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    # Only allow credentials when origins are explicitly restricted (not "*"),
    # since browsers reject credentialed requests with wildcard origins.
    allow_credentials=_cors_allow_origins != ["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

_AUTH_EXEMPT_PATHS = {"/health"}


@app.middleware("http")
async def api_auth_middleware(request: Request, call_next):
    """Enforce Bearer token or JWT on /api/* when AUGUR_API_TOKEN or multi-user is set."""
    if request.url.path.startswith("/api/") and request.url.path not in _AUTH_EXEMPT_PATHS:
        if auth_required():
            ok, _mode = authenticate_request(request)
            if not ok:
                code, suggestion = HTTP_ERROR_ENVELOPE[401]
                return JSONResponse(
                    status_code=401,
                    content=api_error_response(
                        detail="Authentication required",
                        code=code,
                        suggestion=suggestion,
                        path=request.url.path,
                    ),
                )
    return await call_next(request)

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


@app.get("/api/personas")
async def list_personas():
    """List all investor personas"""
    registry = get_registry()
    return {
        "status": "ok",
        "count": len(registry.get_all()),
        "personas": [agent.to_dict() for agent in registry.get_all()],
    }


@app.get("/api/analyze/{ticker}")
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
    """Analyze a ticker with all agents and return consensus.

    Auto-fetches live data from yfinance when no metrics are provided.
    """
    if not _TICKER_PATTERN.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    has_metrics = any([price, pe, pb, revenue_growth, gross_margins, market_cap])
    data_source = "manual"

    if not has_metrics and auto_fetch:
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            data_source = "yfinance"
        except Exception:
            ctx = MarketContext(ticker=ticker.upper())
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

    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_source": data_source,
        "consensus": consensus_resp.to_dict(),
        "agents": [r.to_dict() for r in agent_responses.values()],
        "agent_count": len(agent_responses),
    }


@app.get("/api/persona/{agent_id}")
async def get_persona(agent_id: str):
    """Get single persona details"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")
    return agent.to_dict()


class WorkflowRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol (e.g. AAPL, NVDA)")
    steps: str = Field(
        default="fetch,analyze,consensus",
        description="Comma-separated steps: fetch, analyze, consensus, committee, debate, sentiment",
    )
    agents: str = Field(default="", description="Optional comma-separated agent IDs")
    question: str = Field(default="", description="Optional question for committee step")


@app.post("/api/workflow")
async def run_workflow_endpoint(body: WorkflowRequest):
    """Run a multi-step agentic analysis workflow."""
    if not _TICKER_PATTERN.match(body.ticker):
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.",
        )

    try:
        from augur.workflow import run_workflow
        result = run_workflow(
            body.ticker,
            steps=body.steps,
            agents=body.agents,
            question=body.question,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Workflow failed for %s", body.ticker)
        raise HTTPException(status_code=500, detail=f"Workflow failed: {e}")

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **result,
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "agents": len(get_registry().get_all())}
