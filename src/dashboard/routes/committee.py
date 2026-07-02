"""Committee, compare, debate API routes and HTML pages."""

import re
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from augur.personas.base import MarketContext
from augur.workspace import get_enabled_personas
from dashboard.deps import (
    _i18n_context,
    _save_history_safe,
    consume_endpoint_token,
    get_coordinator,
    get_registry,
    templates,
)
from dashboard.routes.personas import _persona_meta

router = APIRouter()


class CompareBody(BaseModel):
    ticker: str
    agent_ids: List[str]


class DebateBody(BaseModel):
    ticker: str
    agent_ids: List[str]


@router.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request):
    ctx = {"title": "大师对决", "personas": _persona_meta()}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="compare.html", context=ctx)


@router.get("/debate", response_class=HTMLResponse)
async def debate_page(request: Request):
    ctx = {"title": "投资辩论", "personas": _persona_meta()}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="debate.html", context=ctx)


@router.get("/hermes-setup", response_class=HTMLResponse)
async def hermes_setup_page(request: Request):
    ctx = {"title": "Hermes Agent 接入指南"}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="hermes_setup.html", context=ctx)


@router.get("/committee", response_class=HTMLResponse)
async def committee_page(request: Request):
    ctx = {"title": "投资委员会", "personas": _persona_meta()}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="committee.html", context=ctx)


@router.get("/performance", response_class=HTMLResponse)
async def performance_page(request: Request):
    ctx = {"title": "大师排行榜"}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="performance.html", context=ctx)


@router.post("/api/committee")
def api_committee(body: dict):
    """Run an investment committee session with selected masters.

    同步 def：fetch_market_context 同步调用 yfinance，且全部投资人的 analyze()
    也是同步执行，async def 会阻塞事件循环——这是「投委会」体验卡死的根因之一。
    """
    ticker = body.get("ticker", "").upper()
    question = body.get("question", "")
    agent_ids = body.get("agents", [])

    if not ticker or not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        ctx = MarketContext(ticker=ticker)

    coord = get_coordinator()
    registry = coord._registry if hasattr(coord, "_registry") else get_registry()

    if agent_ids:
        all_agents = {a.agent_id: a for a in registry.get_all()}
        selected = {aid: all_agents[aid] for aid in agent_ids if aid in all_agents}
    else:
        selected = {a.agent_id: a for a in registry.get_all()}

    responses = {aid: agent.analyze(ctx) for aid, agent in selected.items()}
    consensus = coord.get_consensus(responses, ticker=ticker, context=ctx)

    opinions = [
        {
            "agent_id": aid,
            "agent_name": r.agent_name,
            "signal": r.signal.value,
            "score": round(r.score, 1),
            "confidence": round(r.confidence, 2),
            "key_findings": r.key_findings[:2],
            "risks": r.risks[:1],
        }
        for aid, r in sorted(responses.items(), key=lambda x: -x[1].score)
    ]

    bullish = sum(1 for r in responses.values() if r.signal.value == "bullish")
    bearish = sum(1 for r in responses.values() if r.signal.value == "bearish")
    neutral = sum(1 for r in responses.values() if r.signal.value == "neutral")
    kelly = consensus.metadata.get("position_sizing", {}).get("position_pct", 0)

    result = {
        "status": "ok",
        "ticker": ticker,
        "question": question,
        "opinions": opinions,
        "verdict": {
            "signal": consensus.signal.value,
            "score": round(consensus.score, 1),
            "confidence": round(consensus.confidence, 2),
            "kelly_pct": round(kelly, 1) if kelly else 0,
            "vote": {"bullish": bullish, "neutral": neutral, "bearish": bearish},
        },
        "market_data": {
            "price": ctx.price,
            "pe": ctx.pe,
            "sector": ctx.sector,
        },
        "session_type": "committee",
        "agents_used": agent_ids or [a.agent_id for a in registry.get_all()],
    }

    try:
        from augur.history import save_analysis
        history_payload = {
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session_type": "committee",
            "question": question,
            "consensus": {
                "signal": consensus.signal.value,
                "score": round(consensus.score, 1),
                "confidence": round(consensus.confidence, 2),
            },
            "agents": [op["agent_name"] for op in opinions],
            "opinions": opinions,
        }
        history_id = save_analysis(ticker, history_payload)
        result["history_id"] = history_id
    except Exception:
        pass

    return result


@router.post("/api/compare")
def api_compare(body: CompareBody):
    """同步 def：fetch_market_context 同步调用 yfinance，async def 会阻塞事件循环。"""
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


@router.post("/api/debate")
def api_debate(body: DebateBody):
    """同步 def：fetch_market_context 同步调用 yfinance，async def 会阻塞事件循环。"""
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
