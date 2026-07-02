"""Watchlist API routes: get, add, remove, run analysis."""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from augur.workspace import get_enabled_personas
from dashboard.deps import _get_rules_engine, get_coordinator

logger = logging.getLogger(__name__)

router = APIRouter()


class WatchlistAddBody(BaseModel):
    """Request body for adding ticker to watchlist."""
    ticker: str
    pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    gross_margins: Optional[float] = None
    revenue_growth: Optional[float] = None
    debt_ratio: Optional[float] = None
    fcf: Optional[float] = None
    market_cap: Optional[float] = None
    price: Optional[float] = None


@router.get("/api/watchlist", summary="获取自选股列表")
async def api_get_watchlist():
    """Get current watchlist from ~/.augur/watchlist.yaml"""
    from augur.cron import load_watchlist
    try:
        config = load_watchlist()
    except FileNotFoundError:
        return {"watchlist": [], "schedule": {}}
    except Exception as e:
        logger.warning("watchlist load failed: %s", e)
        return {
            "watchlist": [],
            "schedule": {},
            "error": "watchlist_unavailable",
            "message": f"自选股文件读取失败: {e}",
        }
    return {
        "watchlist": config.get("watchlist", []),
        "schedule": config.get("schedule", {}),
    }


@router.post("/api/watchlist/add", summary="添加自选股")
async def api_add_to_watchlist(body: WatchlistAddBody):
    """Add ticker to watchlist"""
    from augur.cron import add_to_watchlist
    if not re.match(r'^[A-Za-z0-9.\-]+$', body.ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    if len(body.ticker) > 15:
        raise HTTPException(status_code=400, detail="Ticker too long (max 15 characters)")
    metrics = {}
    for field in ["pe", "pb", "roe", "gross_margins", "revenue_growth", "debt_ratio", "fcf", "market_cap", "price"]:
        val = getattr(body, field, None)
        if val is not None:
            metrics[field] = val
    try:
        config = add_to_watchlist(body.ticker.upper(), metrics if metrics else None)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"无写入权限: {e}")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"写入自选股失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加自选股失败: {e}")
    return {"status": "ok", "ticker": body.ticker.upper(), "watchlist": config.get("watchlist", [])}


@router.delete("/api/watchlist/{ticker}", summary="删除自选股")
async def api_remove_from_watchlist(ticker: str):
    """Remove ticker from watchlist"""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.",
        )
    from augur.cron import remove_from_watchlist
    removed = remove_from_watchlist(ticker.upper())
    if not removed:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker.upper()}' not found in watchlist")
    return {"status": "ok", "ticker": ticker.upper(), "message": "已从自选股移除"}


@router.post("/api/watchlist/run", summary="批量分析自选股")
def api_run_watchlist_analysis():
    """Run consensus analysis on all watchlist tickers

    同步 def：对自选股列表里的每个标的都要跑全部投资大师的同步分析，
    标的多时累积耗时不短，async def 会阻塞事件循环。
    """
    import time
    from augur.cron import load_watchlist
    from augur.personas.base import MarketContext

    config = load_watchlist()
    watchlist = config.get("watchlist", [])

    if not watchlist:
        return {"status": "empty", "message": "自选股列表为空", "results": []}

    coordinator = get_coordinator()
    all_results = []
    start_time = time.time()

    for item in watchlist:
        ticker = item.get("ticker", "")
        if not ticker:
            continue

        manual_overrides = {}
        for key in ["pe", "pb", "roe", "gross_margins", "revenue_growth",
                    "debt_ratio", "fcf", "market_cap", "price"]:
            if key in item:
                manual_overrides[key] = item[key]

        # Live-base + manual-override
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            for key, val in manual_overrides.items():
                setattr(ctx, key, val)
        except Exception:
            ctx_kwargs = {"ticker": ticker.upper(), **manual_overrides}
            ctx = MarketContext(**ctx_kwargs)

        results = coordinator.analyze_with_all(ctx, enabled_personas=get_enabled_personas())
        consensus = coordinator.get_consensus(results, ticker=ticker, context=ctx)

        result_item = {
            "ticker": ticker,
            "signal": consensus.signal.value,
            "score": round(consensus.score, 1),
            "confidence": round(consensus.confidence, 2) if hasattr(consensus, 'confidence') else 0.0,
            "agent_count": len(results),
            "buy_count": sum(1 for r in results.values() if r.signal.value == "bullish"),
            "sell_count": sum(1 for r in results.values() if r.signal.value == "bearish"),
            "hold_count": sum(1 for r in results.values() if r.signal.value == "neutral"),
            "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            "key_findings": consensus.key_findings[:2] if consensus.key_findings else [],
            "kelly_pct": consensus.metadata.get("position_sizing", {}).get("position_pct"),
        }
        all_results.append(result_item)

        try:
            from augur.history import save_analysis
            save_analysis(ticker, {
                "consensus": {
                    "signal": result_item["signal"],
                    "score": result_item["score"],
                    "confidence": result_item["confidence"],
                    "key_findings": result_item["key_findings"],
                },
                "agent_count": result_item["agent_count"],
                "source": "watchlist",
            })
        except Exception:
            pass

        try:
            engine = _get_rules_engine()
            if engine.get_rules():
                rule_data = {
                    "ticker": ticker.upper(),
                    "signal": consensus.signal.value,
                    "score": result_item["score"],
                    "confidence": result_item["confidence"],
                    "kelly_fraction": (result_item.get("kelly_pct") or 0) / 100,
                    "price": ctx.price,
                    "sector": ctx.sector if hasattr(ctx, "sector") else "",
                }
                engine.evaluate(rule_data)
        except Exception:
            pass

        try:
            for w_item in watchlist:
                if w_item.get("ticker", "").upper() == ticker.upper():
                    w_item["last_signal"] = consensus.signal.value
                    w_item["last_score"] = result_item["score"]
                    w_item["last_run"] = result_item["last_run"]
                    break
        except Exception:
            pass

    try:
        from augur.cron import save_watchlist
        config["watchlist"] = watchlist
        save_watchlist(config)
    except Exception:
        pass

    return {"status": "ok", "results": all_results, "processing_time_ms": round((time.time() - start_time) * 1000)}
