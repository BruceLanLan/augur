"""Research Inbox + Alerts REST endpoints (H01/B07 UI wiring)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


@router.get("/api/inbox/list")
async def inbox_list(ticker: str = "", priority: str = "", limit: int = 20) -> Dict[str, Any]:
    """List inbox items, optionally filtered."""
    from augur.research_inbox import ResearchInbox, InboxItem
    box = ResearchInbox()
    items = box.list(ticker=ticker or None, priority=priority or None, limit=limit)
    return {"items": [
        {"item_id": i.item_id, "item_type": i.item_type, "ticker": i.ticker,
         "title": i.title, "description": i.description, "priority": i.priority,
         "created_at": i.created_at, "dismissed": i.dismissed}
        for i in items if not i.dismissed
    ]}


@router.get("/api/alerts/active")
async def alerts_active(ticker: str = "") -> Dict[str, Any]:
    """List active alerts."""
    from augur.alerts import AlertEngine
    engine = AlertEngine()
    alerts = engine.get_active(ticker or None)
    return {"alerts": [
        {"alert_id": a.alert_id, "ticker": a.ticker, "alert_type": a.alert_type,
         "title": a.title, "description": a.description, "severity": a.severity,
         "created_at": a.created_at, "dismissed": a.dismissed}
        for a in alerts if not a.dismissed
    ]}
