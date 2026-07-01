"""WebSocket routes: analyze, committee, prices, workflow."""

import json
import re
import time as _time
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool

from augur.auth import authenticate_websocket
from augur.personas.base import MarketContext
from dashboard.deps import _save_history_safe, get_coordinator, get_registry

from fastapi import APIRouter

router = APIRouter()


def _ws_api_token_ok(websocket: WebSocket) -> bool:
    """WebSocket handshake bypasses HTTP middleware; enforce auth here."""
    return authenticate_websocket(websocket)


# ============ Price streamer singleton ============

_price_streamer = None


def _get_price_streamer():
    global _price_streamer
    if _price_streamer is None:
        from augur.streaming import PriceStreamer
        _price_streamer = PriceStreamer(interval=60.0)
    return _price_streamer


# ============ WebSocket handlers ============

@router.websocket("/ws/analyze/{ticker}")
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
            ctx = await run_in_threadpool(fetch_market_context, ticker.upper())
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


@router.websocket("/ws/committee")
async def ws_committee(websocket: WebSocket):
    if not _ws_api_token_ok(websocket):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    await websocket.accept()
    try:
        from datetime import datetime, timezone
        msg = await websocket.receive_json()
        ticker = (msg.get("ticker") or "").upper()
        question = msg.get("question") or f"分析 {ticker}"
        agent_ids = msg.get("agents") or []

        if not ticker or not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
            await websocket.send_json({"type": "error", "message": "Invalid ticker"})
            return

        try:
            from augur.data import fetch_market_context
            ctx = await run_in_threadpool(fetch_market_context, ticker)
        except Exception:
            ctx = MarketContext(ticker=ticker)

        coord = get_coordinator()
        registry = coord._registry if hasattr(coord, "_registry") else get_registry()

        if agent_ids:
            all_agents_map = {a.agent_id: a for a in registry.get_all()}
            agents = [all_agents_map[aid] for aid in agent_ids if aid in all_agents_map]
        else:
            agents = registry.get_all()

        total = len(agents)
        responses = {}

        for i, agent in enumerate(agents, 1):
            try:
                result = agent.analyze(ctx)
                responses[agent.agent_id] = result
                await websocket.send_json({
                    "type": "agent",
                    "agent_id": agent.agent_id,
                    "agent_name": result.agent_name,
                    "signal": result.signal.value,
                    "score": round(result.score, 1),
                    "confidence": round(result.confidence, 2),
                    "key_findings": result.key_findings[:2],
                    "risks": result.risks[:1],
                    "progress": f"{i}/{total}",
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "agent",
                    "agent_id": agent.agent_id,
                    "agent_name": getattr(agent, "name", agent.agent_id),
                    "signal": "neutral",
                    "score": 0,
                    "confidence": 0,
                    "key_findings": [],
                    "risks": [],
                    "progress": f"{i}/{total}",
                })

        consensus = coord.get_consensus(responses, ticker=ticker, context=ctx)
        bullish_cnt = sum(1 for r in responses.values() if r.signal.value == "bullish")
        bearish_cnt = sum(1 for r in responses.values() if r.signal.value == "bearish")
        neutral_cnt = sum(1 for r in responses.values() if r.signal.value == "neutral")
        kelly = consensus.metadata.get("position_sizing", {}).get("position_pct", 0)

        opinions_sorted = sorted(
            [
                {
                    "agent_id": aid,
                    "agent_name": r.agent_name,
                    "signal": r.signal.value,
                    "score": round(r.score, 1),
                    "confidence": round(r.confidence, 2),
                    "key_findings": r.key_findings[:2],
                    "risks": r.risks[:1],
                }
                for aid, r in responses.items()
            ],
            key=lambda x: -x["score"],
        )

        verdict = {
            "signal": consensus.signal.value,
            "score": round(consensus.score, 1),
            "confidence": round(consensus.confidence, 2),
            "kelly_pct": round(kelly, 1) if kelly else 0,
            "vote": {"bullish": bullish_cnt, "neutral": neutral_cnt, "bearish": bearish_cnt},
        }
        await websocket.send_json({"type": "verdict", "verdict": verdict, "opinions": opinions_sorted})

        try:
            from augur.history import save_analysis
            save_analysis(ticker, {
                "ticker": ticker,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "session_type": "committee",
                "question": question,
                "consensus": {"signal": consensus.signal.value, "score": round(consensus.score, 1), "confidence": round(consensus.confidence, 2)},
                "agents": [op["agent_name"] for op in opinions_sorted],
                "opinions": opinions_sorted,
            })
        except Exception:
            pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@router.websocket("/ws/prices")
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


@router.websocket("/ws/workflow")
async def ws_workflow(websocket: WebSocket):
    """Stream workflow step progress to the client.

    Client sends: ``{"ticker": "NVDA", "steps": "fetch,analyze,consensus", "agents": ""}``
    Server sends one message per step:
      ``{"type": "step_start", "step": "fetch", "step_index": 0, "total": 3}``
      ``{"type": "step_done",  "step": "fetch", "result": {...}, "elapsed_ms": 120}``
    Final message: ``{"type": "done", "results": {...}, "step_status": {...}}``
    """
    if not _ws_api_token_ok(websocket):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    await websocket.accept()
    try:
        raw = await websocket.receive_json()
        ticker = str(raw.get("ticker", "")).upper().strip()
        steps_str = str(raw.get("steps", "")).strip()
        agents_str = str(raw.get("agents", "")).strip()
        question = str(raw.get("question", "")).strip()

        if not ticker or not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
            await websocket.send_json({"type": "error", "message": "Invalid ticker"})
            return

        from augur.workflow import parse_steps, VALID_STEPS, _record_step_status
        from augur.registry import AgentRegistry, DecisionCoordinator

        try:
            step_list = parse_steps(steps_str)
        except ValueError as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            return

        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        output: Dict[str, Any] = {"ticker": ticker, "steps": step_list, "results": {}}
        total = len(step_list)

        ctx = None
        responses = None
        consensus_result = None

        # ---------- fetch ----------
        if "fetch" in step_list:
            idx = step_list.index("fetch")
            await websocket.send_json({"type": "step_start", "step": "fetch", "step_index": idx, "total": total})
            t0 = _time.perf_counter()
            try:
                from augur.data import fetch_market_context
                ctx = await run_in_threadpool(fetch_market_context, ticker)
                result = {"price": ctx.price, "pe": ctx.pe, "sector": ctx.sector, "industry": ctx.industry}
                output["results"]["fetch"] = result
            except Exception as e:
                result = {"error": str(e)[:200]}
                output["results"]["fetch"] = result
            elapsed = round((_time.perf_counter() - t0) * 1000, 1)
            await websocket.send_json({"type": "step_done", "step": "fetch", "result": result, "elapsed_ms": elapsed})
        elif any(s in step_list for s in ("analyze", "consensus", "committee", "debate")):
            try:
                from augur.data import fetch_market_context
                ctx = await run_in_threadpool(fetch_market_context, ticker)
            except Exception:
                ctx = None

        # ---------- agent filter ----------
        from augur.workspace import get_enabled_personas
        persona_filter: Optional[List[str]] = None
        selected_agents = None
        if agents_str:
            selected_ids = [a.strip() for a in agents_str.split(",") if a.strip()]
            all_agents_map = {a.agent_id: a for a in registry.get_all()}
            selected_agents = {aid: all_agents_map[aid] for aid in selected_ids if aid in all_agents_map}
        else:
            persona_filter = get_enabled_personas() or None

        # ---------- analyze ----------
        if "analyze" in step_list:
            idx = step_list.index("analyze")
            await websocket.send_json({"type": "step_start", "step": "analyze", "step_index": idx, "total": total})
            t0 = _time.perf_counter()
            if ctx is None:
                result = {"error": "market data unavailable"}
                output["results"]["analyze"] = result
            else:
                try:
                    if selected_agents:
                        responses = await run_in_threadpool(
                            lambda: {aid: agent.analyze(ctx) for aid, agent in selected_agents.items()}
                        )
                    else:
                        responses = await run_in_threadpool(
                            coordinator.analyze_with_all, ctx, enabled_personas=persona_filter
                        )
                    result = {
                        aid: {"agent_name": r.agent_name, "signal": r.signal.value, "score": r.score, "confidence": r.confidence}
                        for aid, r in responses.items()
                    }
                    output["results"]["analyze"] = result
                except Exception as e:
                    result = {"error": str(e)[:200]}
                    output["results"]["analyze"] = result
            elapsed = round((_time.perf_counter() - t0) * 1000, 1)
            await websocket.send_json({"type": "step_done", "step": "analyze", "result": result, "elapsed_ms": elapsed})

        # ---------- consensus ----------
        if "consensus" in step_list or ("committee" in step_list and responses):
            if responses and "consensus" in step_list:
                idx = step_list.index("consensus")
                await websocket.send_json({"type": "step_start", "step": "consensus", "step_index": idx, "total": total})
            t0 = _time.perf_counter()
            if responses:
                try:
                    consensus_result = await run_in_threadpool(
                        coordinator.get_consensus, responses, ticker=ticker, context=ctx
                    )
                    meta = consensus_result.metadata or {}
                    cons_dict = {
                        "signal": consensus_result.signal.value,
                        "score": consensus_result.score,
                        "confidence": consensus_result.confidence,
                        "reasoning": consensus_result.reasoning,
                        "kelly_pct": meta.get("position_sizing", {}).get("position_pct"),
                        "regime": (meta.get("regime_features") or {}).get("regime"),
                    }
                    if "consensus" in step_list:
                        output["results"]["consensus"] = cons_dict
                except Exception as e:
                    cons_dict = {"error": str(e)[:200]}
                    if "consensus" in step_list:
                        output["results"]["consensus"] = cons_dict
                    consensus_result = None
            else:
                cons_dict = {"error": "no agent responses available"}
                if "consensus" in step_list:
                    output["results"]["consensus"] = cons_dict
            if "consensus" in step_list:
                elapsed = round((_time.perf_counter() - t0) * 1000, 1)
                await websocket.send_json({"type": "step_done", "step": "consensus", "result": cons_dict, "elapsed_ms": elapsed})

        # ---------- committee ----------
        if "committee" in step_list and responses:
            idx = step_list.index("committee")
            await websocket.send_json({"type": "step_start", "step": "committee", "step_index": idx, "total": total})
            t0 = _time.perf_counter()
            try:
                consensus = consensus_result or await run_in_threadpool(
                    coordinator.get_consensus, responses, ticker=ticker, context=ctx
                )
                bullish = sum(1 for r in responses.values() if r.signal.value == "bullish")
                bearish = sum(1 for r in responses.values() if r.signal.value == "bearish")
                result = {
                    "verdict": consensus.signal.value,
                    "score": consensus.score,
                    "vote": {"bullish": bullish, "neutral": len(responses) - bullish - bearish, "bearish": bearish},
                    "opinions": [
                        {"agent": r.agent_name, "signal": r.signal.value, "score": r.score}
                        for r in sorted(responses.values(), key=lambda x: -x.score)
                    ],
                }
                output["results"]["committee"] = result
            except Exception as e:
                result = {"error": str(e)[:200]}
                output["results"]["committee"] = result
            elapsed = round((_time.perf_counter() - t0) * 1000, 1)
            await websocket.send_json({"type": "step_done", "step": "committee", "result": result, "elapsed_ms": elapsed})

        # ---------- sentiment ----------
        if "sentiment" in step_list:
            idx = step_list.index("sentiment")
            await websocket.send_json({"type": "step_start", "step": "sentiment", "step_index": idx, "total": total})
            t0 = _time.perf_counter()
            try:
                from augur.sentiment import SentimentAnalyzer
                sentiment = await run_in_threadpool(SentimentAnalyzer().get_sentiment, ticker)
                result = sentiment
                output["results"]["sentiment"] = result
            except Exception as e:
                result = {"error": str(e)[:200]}
                output["results"]["sentiment"] = result
            elapsed = round((_time.perf_counter() - t0) * 1000, 1)
            await websocket.send_json({"type": "step_done", "step": "sentiment", "result": result, "elapsed_ms": elapsed})

        _record_step_status(output, step_list)
        await websocket.send_json({"type": "done", "results": output["results"], "step_status": output["step_status"]})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)[:300]})
        except Exception:
            pass
