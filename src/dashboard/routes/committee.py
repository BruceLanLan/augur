"""Committee, compare, debate API routes and HTML pages."""

import re
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from augur.personas.base import MarketContext
from dashboard.deps import (
    _i18n_context,
    consume_endpoint_token,
    get_coordinator,
    get_registry,
    templates,
)
from dashboard.routes.personas import _persona_meta

router = APIRouter()



def _abstained(resp) -> bool:
    """True when a persona abstained because its rules do not apply (e.g. a fund)."""
    return bool((getattr(resp, "metadata", None) or {}).get("not_applicable"))


def committee_opinion(agent_id: str, resp) -> dict:
    """One persona's committee card payload."""
    return {
        "agent_id": agent_id,
        "agent_name": resp.agent_name,
        "signal": resp.signal.value,
        "score": round(resp.score, 1),
        "confidence": round(resp.confidence, 2),
        "key_findings": resp.key_findings[:2],
        "risks": resp.risks[:1],
        "not_applicable": _abstained(resp),
    }


def committee_verdict(responses: dict, consensus) -> tuple:
    """(opinions, verdict) shared by POST /api/committee and /ws/committee.

    Personas that abstained on a fund are listed last, flagged
    ``not_applicable`` and left out of the vote. When the engine withheld
    the consensus (too few applicable personas) the verdict says so instead
    of reporting the neutral placeholder score as a real reading.
    """
    meta = consensus.metadata or {}
    opinions = sorted(
        (committee_opinion(aid, r) for aid, r in responses.items()),
        key=lambda o: (o["not_applicable"], -o["score"]),
    )
    voting = [r for r in responses.values() if not _abstained(r)]
    withheld = bool(meta.get("consensus_withheld"))
    kelly = 0 if withheld else (meta.get("position_sizing", {}) or {}).get("position_pct", 0)
    verdict = {
        "signal": consensus.signal.value,
        "score": round(consensus.score, 1),
        "confidence": round(consensus.confidence, 2),
        "kelly_pct": round(kelly, 1) if kelly else 0,
        "vote": {
            "bullish": sum(1 for r in voting if r.signal.value == "bullish"),
            "neutral": sum(1 for r in voting if r.signal.value == "neutral"),
            "bearish": sum(1 for r in voting if r.signal.value == "bearish"),
            "abstained": len(responses) - len(voting),
        },
        "withheld": withheld,
        "applicable_count": len(voting),
        "abstained_count": len(responses) - len(voting),
    }
    return opinions, verdict


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

    opinions, verdict = committee_verdict(responses, consensus)

    result = {
        "status": "ok",
        "ticker": ticker,
        "question": question,
        "opinions": opinions,
        "verdict": verdict,
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
