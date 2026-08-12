"""Earnings Queue API routes: upcoming events, dossier readiness, comparisons."""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from augur.earnings import EarningsEventService, DossierStatus, FilingDelta, get_earnings_service

logger = logging.getLogger(__name__)

router = APIRouter()

_EVENT_SERVICE: Optional[EarningsEventService] = None


def _svc() -> EarningsEventService:
    global _EVENT_SERVICE
    if _EVENT_SERVICE is None:
        _EVENT_SERVICE = get_earnings_service()
    return _EVENT_SERVICE


@router.get("/api/earnings/events", summary="获取 watchlist 中所有 ticker 的临近财报事件")
async def api_earnings_events(lookahead_days: int = Query(60, ge=1, le=180)):
    """Return upcoming earnings events for every ticker in the watchlist."""
    from augur.cron import load_watchlist

    try:
        config = load_watchlist()
    except FileNotFoundError:
        return {"events": [], "lookahead_days": lookahead_days}
    except Exception as e:
        logger.warning("Watchlist load failed: %s", e)
        return {"events": [], "lookahead_days": lookahead_days, "error": str(e)}

    watchlist = config.get("watchlist", [])
    tickers = [item.get("ticker", "") for item in watchlist if item.get("ticker")]
    if not tickers:
        return {"events": [], "lookahead_days": lookahead_days}

    events = _svc().detect_events(tickers, lookahead_days=lookahead_days)
    statuses = _svc().check_dossier_readiness(events)

    result = []
    for ds in statuses:
        e = ds.event
        readiness = "ready" if ds.ready else ("partial" if len(ds.missing_items) <= 1 else "insufficient")
        result.append({
            "ticker": ds.ticker,
            "event_date": e.event_date,
            "confidence": e.confidence,
            "fiscal_period": e.fiscal_period,
            "source": e.source,
            "readiness": readiness,
            "ready": ds.ready,
            "missing_items": ds.missing_items,
            "last_generated": ds.last_generated,
            "run_id": ds.run_id,
        })

    return {"events": result, "lookahead_days": lookahead_days}


@router.get("/api/earnings/dossier/{ticker}", summary="获取某个 ticker 的 Pre-event Dossier")
async def api_earnings_dossier(ticker: str):
    """Return a pre-event dossier for *ticker* (MVP: static stub expanded by Skill)."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")

    t = ticker.upper()

    # MVP: return a structured stub built from available data
    dossier = {
        "ticker": t,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sections": {
            "guidance": {
                "title": "Prior Guidance",
                "items": [
                    {"label": "Revenue Guidance", "value": "Pending — run earnings-prep Skill to populate"},
                    {"label": "EPS Guidance", "value": "Pending — run earnings-prep Skill to populate"},
                    {"label": "Margin Outlook", "value": "Pending — run earnings-prep Skill to populate"},
                ],
            },
            "kpi": {
                "title": "Key Performance Indicators",
                "items": [
                    {"label": "Revenue Growth (YoY)", "value": "Pending"},
                    {"label": "Gross Margin", "value": "Pending"},
                    {"label": "Operating Margin", "value": "Pending"},
                    {"label": "FCF Yield", "value": "Pending"},
                    {"label": "Debt/Equity", "value": "Pending"},
                ],
            },
            "risks": {
                "title": "Risk Factors",
                "items": [
                    "Macro headwinds (rate sensitivity)",
                    "Supply chain concentration",
                    "Regulatory uncertainty",
                ],
            },
            "persona_divergence": {
                "title": "Persona Disagreement",
                "items": [
                    {
                        "topic": "Valuation",
                        "bulls": ["cathie_wood"],
                        "bears": ["graham", "buffett"],
                        "neutrals": ["lynch"],
                    },
                    {
                        "topic": "Growth Trajectory",
                        "bulls": ["cathie_wood", "lynch"],
                        "bears": ["dalio"],
                        "neutrals": ["marks"],
                    },
                ],
            },
            "pending_questions": {
                "title": "Questions to Resolve",
                "items": [
                    "Will management raise or lower guidance?",
                    "Is buyback activity accelerating?",
                    "Are insider sales increasing pre-earnings?",
                    "How does consensus estimate compare to prior quarters?",
                ],
            },
        },
    }

    return {"status": "ok", "dossier": dossier}


@router.get("/api/earnings/scorecard/{ticker}", summary="获取 Post-event Scorecard 对比")
async def api_earnings_scorecard(ticker: str):
    """Return a post-earnings scorecard comparing predictions to actuals."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")

    t = ticker.upper()

    # MVP stub: in production this queries saved prediction vs actual
    scorecard = {
        "ticker": t,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_predictions": 0,
            "confirmed": 0,
            "refuted": 0,
            "partial": 0,
            "unknown": 0,
        },
        "items": [],
    }

    return {"status": "ok", "scorecard": scorecard}
