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
from pathlib import Path
from typing import Optional, List, Dict, Any
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("Missing dependencies. Run: pip install fastapi uvicorn jinja2")
    sys.exit(1)

from scanner.personas.registry import AgentRegistry
from scanner.personas.base import MarketContext

app = FastAPI(
    title="Augur — 多智能体投资分析",
    description="17位虚拟投资大师，多维度共识分析",
    version="3.0.0",
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def _persona_meta() -> List[Dict]:
    registry = get_registry()
    meta = []
    for agent in registry.get_all():
        meta.append({
            "agent_id": agent.agent_id,
            "name": agent.name,
            "style": " · ".join(agent.philosophy[:2]) if agent.philosophy else "",
            "description": agent.identity.strip().replace("\n", " ").replace("  ", " "),
            "scenarios": agent.philosophy,
            "weight": f"{list(agent.scoring_weights.values())[0]:.0%}" if agent.scoring_weights else "均等",
            "status": "Active",
        })
    return meta


# ============ HTML Routes ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("base.html", {
        "request": request,
        "title": "Augur — 投资大师仪表盘",
        "agent_count": len(get_registry().get_all()),
    })


@app.get("/personas", response_class=HTMLResponse)
async def personas_page(request: Request):
    return templates.TemplateResponse("personas.html", {
        "request": request,
        "personas": _persona_meta(),
        "title": "投资人人格系统",
    })


# ============ API Routes ============

@app.get("/api/personas")
async def list_personas():
    """返回所有投资人人格列表"""
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
    current_ratio: float = 1.5,
    earnings_growth: float = 0,
    sector: str = "",
    industry: str = "",
):
    """
    使用所有17位投资大师分析指定标的

    基本用法: GET /api/analyze/AAPL?price=210&pe=32&gross_margins=0.46
    """
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

    registry = get_registry()
    results = {}
    for agent in registry.get_all():
        try:
            resp = agent.analyze(ctx)
            results[agent.agent_id] = resp.to_dict()
        except Exception as e:
            results[agent.agent_id] = {
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "signal": "error",
                "score": 0,
                "confidence": 0,
                "reasoning": f"分析失败: {e}",
                "key_findings": [],
                "risks": [],
            }

    # 计算共识
    valid = [v for v in results.values() if v["signal"] not in ("error",)]
    if valid:
        avg_score = sum(v["score"] for v in valid) / len(valid)
        signal_counts = {}
        for v in valid:
            signal_counts[v["signal"]] = signal_counts.get(v["signal"], 0) + 1
        consensus_signal = max(signal_counts, key=signal_counts.get)
    else:
        avg_score = 0
        consensus_signal = "neutral"

    consensus = {
        "agent_id": "consensus",
        "agent_name": "多Agent共识",
        "signal": consensus_signal,
        "score": round(avg_score, 2),
        "confidence": 0.8,
        "reasoning": f"基于{len(valid)}个Agent的加权共识分析",
        "key_findings": [],
        "risks": [],
    }

    return {
        "ticker": ticker.upper(),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "consensus": consensus,
        "agents": list(results.values()),
        "agent_count": len(results),
    }


@app.get("/api/persona/{agent_id}")
async def get_persona(agent_id: str):
    """获取单个投资人的详细信息"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")
    return agent.to_dict()


@app.get("/health")
async def health():
    return {"status": "ok", "agents": len(get_registry().get_all())}


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(description="Augur Dashboard")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--cors", action="store_true",
                        help="Enable CORS for all origins (for Hermes integration)")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        print("CORS enabled for all origins")

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
