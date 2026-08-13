"""Batch analysis + freshness REST endpoints (data pipeline UI wiring)."""
from __future__ import annotations
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class BatchRequest(BaseModel):
    tickers: List[str]
    max_workers: int = 5


@router.post("/api/batch/analyze")
async def batch_analyze(body: BatchRequest) -> Dict[str, Any]:
    """Analyze multiple tickers in parallel (batch pipeline)."""
    if not body.tickers or len(body.tickers) > 50:
        raise HTTPException(status_code=400, detail="1-50 tickers required")

    from augur.data import fetch_market_context_batch
    contexts = fetch_market_context_batch(body.tickers, max_workers=body.max_workers)

    results = {}
    for t, ctx in contexts.items():
        results[t] = {
            "price": ctx.price,
            "pe": ctx.pe,
            "sector": ctx.sector,
            "industry": ctx.industry,
            "data_source": getattr(ctx, "data_source", "unknown"),
            "error": getattr(ctx, "data_error", None),
        }
    return {"results": results, "count": len(results)}


@router.get("/api/freshness")
async def freshness_report() -> Dict[str, Any]:
    """Return data freshness report (stale cache entries)."""
    from augur.freshness import FreshnessTracker
    tracker = FreshnessTracker()
    stale = tracker.list_stale()
    return {
        "stale_count": len(stale),
        "stale_items": [
            {"key": r.key, "age_hours": r.age_hours, "max_age_hours": r.max_age_hours}
            for r in stale[:20]
        ],
    }


@router.get("/api/cache/health")
async def cache_health() -> Dict[str, Any]:
    """Return EDGAR cache health statistics."""
    from augur.cache_health import cache_size_report, check_edgar_cache_freshness
    report = cache_size_report()
    stale = check_edgar_cache_freshness()
    report["stale_files"] = len(stale)
    report["stale_sample"] = stale[:10]
    return report
