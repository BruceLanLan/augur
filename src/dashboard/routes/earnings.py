"""Earnings Queue API routes: upcoming events, dossier readiness, comparisons."""

import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from augur.earnings import EarningsEventService, get_earnings_service

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


_TICKER_RE = re.compile(r'^[A-Za-z0-9.\-]{1,15}$')


def _utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dossier_text(text: str) -> list:
    """Split the CLI dossier text into ``[{"title", "lines"}]`` sections.

    The text comes from :func:`augur.cli_commands.dossier_cmd.run_earnings_dossier`,
    whose section headers look like ``── Prior Guidance ──``.
    """
    sections: list = []
    current: Optional[dict] = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("═══"):
            continue
        if line.startswith("──") and line.endswith("──"):
            current = {"title": line.strip("─ ").strip(), "lines": []}
            sections.append(current)
        elif current is not None:
            current["lines"].append(line)
    return sections


@router.get("/api/earnings/dossier/{ticker}", summary="获取某个 ticker 的 Pre-event Dossier")
async def api_earnings_dossier(ticker: str):
    """Return the pre-event dossier for *ticker*, built by the same function as
    ``augur dossier`` (CLI). Missing data is reported explicitly as
    ``{"status": "unavailable", "reason": ...}`` -- never filled with placeholders.
    """
    if not _TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")

    t = ticker.upper()

    from augur.cli_commands.dossier_cmd import run_earnings_dossier
    from augur.run_tracker import latest_run_id

    try:
        run_id = latest_run_id(t, require_persona_analysis=True)
    except Exception as e:  # unreadable runs dir: report, don't fake
        logger.warning("latest_run_id failed for %s: %s", t, e)
        run_id = None

    try:
        text = run_earnings_dossier(t)
    except Exception as e:
        logger.warning("Dossier build failed for %s: %s", t, e)
        return {"status": "unavailable", "ticker": t,
                "reason": f"Dossier build failed: {e}"}

    sections = _parse_dossier_text(text)
    # The Disagreement section is always emitted by the CLI (with a
    # "no saved run" hint when empty); it only counts as data when a run exists.
    data_sections = [s for s in sections
                     if s["title"] != "Disagreement" or run_id is not None]
    if not data_sections:
        return {
            "status": "unavailable",
            "ticker": t,
            "reason": (f"No saved analysis run, guidance, earnings event or open "
                       f"questions for {t}. Run `augur workflow {t}` first."),
        }

    return {
        "status": "ok",
        "dossier": {
            "ticker": t,
            "generated_at": _utc_now(),
            "run_id": run_id,
            "source": "augur.cli_commands.dossier_cmd.run_earnings_dossier",
            "text": text,
            "sections": sections,
        },
    }


_SCORECARD_UNAVAILABLE_REASON = (
    "Post-event scorecards need a pre-event prediction run and a post-event "
    "actuals run for the same earnings event; the dashboard does not yet "
    "persist that pairing, so no scorecard can be computed."
)


def _scorecard_unavailable(t: str) -> dict:
    from augur.run_tracker import list_run_ids

    try:
        n_runs = len(list_run_ids(t))
    except Exception:
        n_runs = 0
    return {
        "status": "unavailable",
        "ticker": t,
        "reason": _SCORECARD_UNAVAILABLE_REASON,
        "saved_runs": n_runs,
        "items": [],
    }


@router.get("/api/earnings/scorecard/{ticker}", summary="获取 Post-event Scorecard 对比")
async def api_earnings_scorecard(ticker: str):
    """Post-earnings scorecard (prediction vs actual). Explicitly unavailable
    until pre/post run pairing is persisted -- no zero-filled stub."""
    if not _TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")
    return _scorecard_unavailable(ticker.upper())


@router.get("/api/scorecard", summary="Post-event Scorecard（scorecard 页面使用）")
async def api_scorecard(ticker: str = Query(..., min_length=1, max_length=15)):
    """Endpoint used by ``scorecard.html``; same contract as the per-ticker route."""
    if not _TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")
    return _scorecard_unavailable(ticker.upper())
