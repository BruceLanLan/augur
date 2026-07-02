"""History page and API routes — /history and /api/history*.

Extracted from dashboard/app.py (router split R3).
Mounts via: app.include_router(history_router)
"""

import logging
import math
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from dashboard.deps import templates

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse(request=request, name="history.html", context={"title": "历史记录"})


@router.get("/api/history")
def api_list_history(
    limit: int = 50,
    page: Optional[int] = None,
    per_page: int = 20,
    ticker: Optional[str] = None,
    signal: Optional[str] = None,
):
    from augur.history import list_history, count_history
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    ticker_filter = ticker.strip().upper() if ticker and ticker.strip() else None
    signal_filter = signal.strip().lower() if signal and signal.strip() in ("bullish", "neutral", "bearish") else None
    if page is not None:
        if page < 1 or per_page < 1:
            raise HTTPException(status_code=400, detail="page and per_page must be >= 1")
        if per_page > 100:
            raise HTTPException(status_code=400, detail="per_page must be <= 100")
        try:
            total = count_history(ticker_filter=ticker_filter, signal_filter=signal_filter)
            total_pages = math.ceil(total / per_page) if per_page > 0 else 0
            records = list_history(page=page, per_page=per_page, ticker_filter=ticker_filter, signal_filter=signal_filter)
        except Exception as e:
            logger.warning("history list (paginated) failed: %s", e)
            return {"items": [], "total": 0, "page": page, "per_page": per_page, "pages": 0, "error": "history_unavailable", "message": f"历史记录读取失败: {e}"}
        return {"items": records, "total": total, "page": page, "per_page": per_page, "pages": total_pages}
    try:
        records = list_history(limit=limit, ticker_filter=ticker_filter, signal_filter=signal_filter)
    except Exception as e:
        logger.warning("history list failed: %s", e)
        return {"records": [], "count": 0, "error": "history_unavailable", "message": f"历史记录读取失败: {e}"}
    return {"records": records, "count": len(records)}


@router.get("/api/history/{history_id}")
async def api_get_history(history_id: str):
    if not re.match(r'^[A-Za-z0-9._\-]{1,64}$', history_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid history_id format. Use 1-64 alphanumeric characters, dots, hyphens, or underscores.",
        )
    from augur.history import get_history
    record = get_history(history_id)
    if not record:
        raise HTTPException(status_code=404, detail="History record not found")
    return record


@router.delete("/api/history/{history_id}")
async def api_delete_history_item(history_id: str):
    if not re.match(r'^[A-Za-z0-9._\-]{1,64}$', history_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid history_id format. Use 1-64 alphanumeric characters, dots, hyphens, or underscores.",
        )
    from augur.history import delete_history
    deleted = delete_history(history_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History record not found")
    return {"status": "ok", "message": "已删除"}


@router.delete("/api/history")
async def api_clear_history():
    from augur.history import clear_history
    try:
        count = clear_history()
    except Exception as e:
        logger.warning("clear history failed: %s", e)
        raise HTTPException(status_code=500, detail=f"清除历史记录失败: {e}")
    return {"status": "ok", "deleted": count, "message": f"已清除 {count} 条记录"}
