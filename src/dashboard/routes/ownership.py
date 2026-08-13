"""Insider activity + ownership REST endpoints (C05/C06 UI surface)."""
from __future__ import annotations
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/api/insider/{ticker}")
async def get_insider_activity(ticker: str, days: int = 90) -> Dict[str, Any]:
    """Return recent insider trading activity for a ticker."""
    t = ticker.upper()
    if not t or len(t) > 15:
        raise HTTPException(status_code=400, detail="invalid ticker")

    # Placeholder trades — production reads from EDGAR Form 4 cache
    trades = [
        {"person": "CEO", "role": "Chief Executive Officer", "type": "buy",
         "shares": 10000, "price": 150.0, "date": "2026-01-15"},
        {"person": "CFO", "role": "Chief Financial Officer", "type": "buy",
         "shares": 5000, "price": 151.0, "date": "2026-01-16"},
    ]
    return {
        "ticker": t,
        "window_days": days,
        "trades": trades,
        "net_sentiment": "positive",
        "note": "Placeholder data — connect EDGAR Form 4 feed for production",
    }


@router.get("/api/ownership/{ticker}")
async def get_ownership_delta(ticker: str) -> Dict[str, Any]:
    """Return institutional ownership delta for a ticker."""
    t = ticker.upper()
    if not t or len(t) > 15:
        raise HTTPException(status_code=400, detail="invalid ticker")

    curr = [
        {"institution": "Vanguard", "shares": 1.1e9, "value": 165e9},
        {"institution": "BlackRock", "shares": 0.75e9, "value": 112e9},
    ]
    return {
        "ticker": t,
        "previous_quarter": "Q3_2025",
        "current_quarter": "Q4_2025",
        "top_holders": curr,
        "note": "Placeholder data — connect 13F feed for production",
    }
