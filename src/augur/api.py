# -*- coding: utf-8 -*-
"""
augur.api - REST API (FastAPI)

Provides endpoints:
  GET /api/personas - list all personas
  GET /api/analyze/{ticker} - analyze with all agents
  GET /api/persona/{agent_id} - get single persona info
  GET /health - health check
"""

import re
from typing import Optional, List, Dict
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    raise ImportError("fastapi is required: pip install fastapi uvicorn")

from augur.registry import AgentRegistry, DecisionCoordinator
from augur.personas.base import MarketContext

app = FastAPI(
    title="Augur API",
    description="Multi-agent investment analysis API",
    version="6.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
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

    import datetime
    return {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z",
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


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "agents": len(get_registry().get_all())}
