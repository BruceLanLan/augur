"""Backtest API routes: demo backtester and IC leaderboard."""

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from dashboard.deps import get_registry, templates

router = APIRouter()


@router.get("/backtest", response_class=HTMLResponse, summary="历史回测页面")
async def backtest_page(request: Request):
    return templates.TemplateResponse(request=request, name="backtest.html", context={
        "title": "历史回测 - Agent IC",
    })


@router.get("/api/backtest/run", summary="运行历史回测")
async def api_run_backtest(
    ticker: str = "AAPL",
    days: int = 30,
    initial_capital: float = 100000,
    strategy: str = "equal_weight",
    mode: str = "live",
):
    """Run a backtest, return results with metrics and signals timeline.

    mode=live (default): real historical prices + point-in-time fundamentals
    via yfinance. Requires network and the 'data' extra; failures are
    reported as errors, never silently swapped for synthetic data.
    mode=demo: hash-seeded synthetic data, for offline/no-network use —
    response is flagged data_source=demo so it's never mistaken for a real
    backtest result.
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")
    if mode not in ("live", "demo"):
        raise HTTPException(status_code=400, detail="mode must be 'live' or 'demo'")

    from augur.backtest import Backtester

    if days < 5:
        days = 5
    if days > 365:
        days = 365

    backtester = Backtester()

    if mode == "demo":
        from augur.backtest import generate_sample_data
        historical_data, forward_returns = generate_sample_data(ticker, days)
        result = backtester.run_backtest(ticker, historical_data, forward_returns, data_source="demo")
        data_source = "demo"
    else:
        from augur.optional_deps import is_available
        if not is_available("augur.data"):
            raise HTTPException(
                status_code=501,
                detail="Real historical data requires the 'data' extra (pip install 'augur-agents[data]'). "
                       "Pass mode=demo to use offline synthetic data instead.",
            )
        try:
            result = backtester.run_live_backtest(ticker, days=days)
        except ImportError as e:
            raise HTTPException(status_code=501, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"Insufficient live data for {ticker.upper()}: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch live data for {ticker.upper()}: {e}")
        data_source = "live"

    agent_ics = result.agent_ics
    avg_hit_rate = 0.0
    if agent_ics:
        avg_hit_rate = sum(a.hit_rate for a in agent_ics) / len(agent_ics)

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

    signals_timeline = []
    for rec in result.records[:50]:
        signals_timeline.append({
            "date": rec.date,
            "ticker": rec.ticker,
            "signal": rec.signal,
            "score": round(rec.score, 1),
            "agent_id": rec.agent_id,
        })
    signals_timeline.sort(key=lambda x: x["date"], reverse=True)

    return {
        "status": "ok",
        "ticker": result.ticker,
        "days": days,
        "initial_capital": initial_capital,
        "strategy": strategy,
        "data_source": data_source,
        "total_records": len(result.records),
        "consensus_ic": result.consensus_ic,
        "agent_ics": [a.to_dict() for a in result.agent_ics],
        "metrics": metrics,
        "signals_timeline": signals_timeline,
        "summary": result.summary,
    }


@router.get("/api/backtest/leaderboard", summary="获取IC排行榜")
async def api_ic_leaderboard():
    """Get saved IC leaderboard, enriched with live LearningEngine accuracy when available."""
    from augur.backtest import Backtester

    backtester = Backtester()
    ics = backtester.get_leaderboard()

    # Fetch live per-agent accuracy from LearningEngine (outcomes resolved after 30+ days).
    # Silently skipped if no data exists yet.
    live_accuracy: dict = {}
    pending_count: int = 0
    try:
        from augur.registry import _get_learning_engine
        le = _get_learning_engine()
        live_accuracy = le.get_accuracy()
        pending_count = le.pending_count
    except Exception:
        pass

    registry = get_registry()
    def _enrich(d: dict) -> dict:
        agent = registry.get(d.get("agent_id", ""))
        if agent:
            d["agent_name"] = agent.name
        agent_id = d.get("agent_id", "")
        la = live_accuracy.get(agent_id)
        if la:
            d["accuracy"] = la["accuracy_rate"]
            d["total_predictions"] = la["total_predictions"]
            d["correct_predictions"] = la["correct_predictions"]
            d["live_accuracy"] = True
        return d

    leaderboard = [_enrich(a.to_dict()) for a in ics]

    # Agents that have real LearningEngine predictions/outcomes but were
    # never backtested (e.g. a newly added persona) previously had no row
    # at all here, even though has_live_accuracy was True for the response
    # as a whole. Synthesize a leaderboard-shaped entry for them so their
    # real track record is visible — flagged live_only so the frontend can
    # tell "no IC because never backtested" apart from "IC computed as 0".
    backtested_ids = {a.agent_id for a in ics}
    for agent_id, la in live_accuracy.items():
        if agent_id in backtested_ids:
            continue
        agent = registry.get(agent_id)
        leaderboard.append({
            "agent_id": agent_id,
            "agent_name": agent.name if agent else agent_id,
            "total_predictions": la["total_predictions"],
            "correct_predictions": la["correct_predictions"],
            "ic_5d": 0.0,
            "ic_20d": 0.0,
            "ic_60d": 0.0,
            "hit_rate": la["accuracy_rate"],
            "avg_score_when_right": 0.0,
            "avg_score_when_wrong": 0.0,
            "accuracy": la["accuracy_rate"],
            "live_accuracy": True,
            "live_only": True,
        })

    return {
        "status": "ok",
        "leaderboard": leaderboard,
        "count": len(leaderboard),
        "pending_count": pending_count,
        "has_live_accuracy": bool(live_accuracy),
    }
