"""Analysis API routes: scanner, analyze, report.

All heavy-LLM routes are sync ``def`` so Starlette dispatches them to the
thread-pool instead of blocking the event loop.
"""

import re
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from augur.personas.base import MarketContext
from augur.report import generate_report
from augur.workspace import get_enabled_personas
from dashboard.deps import _check_rate_limit, _get_rules_engine, get_coordinator

router = APIRouter()


# ============ Scanner API ============

class ScannerRunBody(BaseModel):
    tickers: List[str] = []
    preset: Optional[str] = None


SCANNER_PRESETS = {
    "tech_giants": ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "META", "AMZN", "AMD"],
    "china_stocks": ["BABA", "PDD", "JD", "BIDU", "NIO", "LI", "XPEV"],
    "crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"],
}


@router.post("/api/scanner/run", summary="批量扫描标的评分")
async def api_scanner_run(body: ScannerRunBody):
    """批量扫描标的，返回所有大师评分矩阵"""
    tickers = body.tickers
    if body.preset and body.preset in SCANNER_PRESETS:
        tickers = SCANNER_PRESETS[body.preset]

    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")

    seen_upper: set = set()
    deduped: List[str] = []
    for t in tickers:
        upper = t.upper()
        if upper not in seen_upper:
            seen_upper.add(upper)
            deduped.append(t)
    tickers = deduped

    if len(tickers) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 tickers per scan")

    for t in tickers:
        if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', t):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {t}")

    coord = get_coordinator()
    results = []
    error_tickers: List[str] = []
    for ticker in tickers:
        try:
            ctx = MarketContext(ticker=ticker.upper())
            try:
                from augur.data import fetch_market_context
                ctx = fetch_market_context(ticker)
            except Exception:
                pass
            agent_responses = coord.analyze_with_all(ctx, enabled_personas=get_enabled_personas())
            consensus = coord.get_consensus(agent_responses, ticker=ticker.upper(), context=ctx)
            agents_data = []
            for agent_id, resp in agent_responses.items():
                agents_data.append({
                    "agent_id": agent_id,
                    "signal": resp.signal.value,
                    "score": round(resp.score, 1),
                })
            results.append({
                "ticker": ticker.upper(),
                "consensus_signal": consensus.signal.value,
                "consensus_score": round(consensus.score, 1),
                "agents": agents_data,
            })
        except Exception as e:
            error_tickers.append(ticker.upper())
            results.append({
                "ticker": ticker.upper(),
                "consensus_signal": "error",
                "consensus_score": 0,
                "agents": [],
                "error": {
                    "status": "error",
                    "detail": f"Scanner failed for {ticker.upper()}: {e}",
                    "code": "SCAN_FAILED",
                    "suggestion": "Verify the ticker is valid and the data source is reachable, then retry.",
                },
            })

    response: Dict[str, Any] = {"status": "ok", "results": results, "count": len(results)}
    if error_tickers:
        response["errors"] = error_tickers
    return response


# ============ Analyze API ============

@router.get("/api/analyze/{ticker}", summary="分析指定标的")
def analyze_ticker(
    ticker: str,
    price: float = 0,
    pe: float = 0,
    pb: float = 0,
    revenue_growth: float = 0,
    gross_margins: float = 0,
    operating_margins: float = 0,
    roe: float = 0,
    debt_ratio: float = 0,
    fcf: float = 0,
    market_cap: float = 0,
    institutional_ownership: float = 0,
    insider_ownership: float = 0,
    current_ratio: float = 0,
    earnings_growth: float = 0,
    sector: str = "",
    industry: str = "",
    auto_fetch: bool = True,
):
    """
    使用所有18位投资大师分析指定标的

    基本用法: GET /api/analyze/AAPL (自动获取实时数据)
    手动指标: GET /api/analyze/AAPL?price=210&pe=32&gross_margins=0.46

    同步 def：fetch_market_context 同步调用 yfinance，且 18 位投资大师的
    分析也是同步执行，async def 会在此期间阻塞事件循环——这正是「投委会」
    和「深度报告」体验卡死的根因之一。
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    if len(sector) > 100:
        raise HTTPException(status_code=400, detail="Sector too long (max 100 characters).")
    if len(industry) > 100:
        raise HTTPException(status_code=400, detail="Industry too long (max 100 characters).")

    if not _check_rate_limit(ticker):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 30 requests per minute per ticker.")

    has_user_metrics = any([
        price > 0, pe > 0, pb > 0, revenue_growth != 0,
        gross_margins > 0, operating_margins != 0, roe > 0,
        debt_ratio > 0, fcf != 0, market_cap > 0,
    ])

    data_source = "manual"

    if not has_user_metrics and auto_fetch:
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            data_source = "yfinance"
        except (ImportError, Exception):
            data_source = "fallback"
            ctx = MarketContext(
                ticker=ticker.upper(),
                price=price, pe=pe, pb=pb,
                revenue_growth=revenue_growth, gross_margins=gross_margins,
                operating_margins=operating_margins, roe=roe,
                debt_ratio=debt_ratio, fcf=fcf, market_cap=market_cap,
                institutional_ownership=institutional_ownership,
                insider_ownership=insider_ownership,
                current_ratio=current_ratio, earnings_growth=earnings_growth,
                sector=sector, industry=industry,
            )
    else:
        ctx = MarketContext(
            ticker=ticker.upper(),
            price=price, pe=pe, pb=pb,
            revenue_growth=revenue_growth, gross_margins=gross_margins,
            operating_margins=operating_margins, roe=roe,
            debt_ratio=debt_ratio, fcf=fcf, market_cap=market_cap,
            institutional_ownership=institutional_ownership,
            insider_ownership=insider_ownership,
            current_ratio=current_ratio, earnings_growth=earnings_growth,
            sector=sector, industry=industry,
        )

    coord = get_coordinator()
    agent_responses = coord.analyze_with_all(ctx, enabled_personas=get_enabled_personas())
    consensus_resp = coord.get_consensus(
        agent_responses,
        ticker=ticker.upper(),
        context=ctx,
    )

    response = {
        "status": "ok",
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_source": data_source,
        "market_data": {
            "price": ctx.price,
            "pe": ctx.pe,
            "pb": ctx.pb,
            "roe": ctx.roe,
            "gross_margins": ctx.gross_margins,
            "sector": ctx.sector,
            "industry": ctx.industry,
            "business_summary": ctx.business_summary,
            "market_cap": ctx.market_cap,
            "fcf": ctx.fcf,
            "revenue_growth": ctx.revenue_growth,
            "debt_ratio": ctx.debt_ratio,
        },
        "consensus": consensus_resp.to_dict(),
        "agents": [r.to_dict() for r in agent_responses.values()],
        "agent_count": len(agent_responses),
    }

    if getattr(ctx, "data_error", None):
        response["data_error"] = ctx.data_error
    elif data_source == "fallback":
        response["data_note"] = "Auto-fetch failed, using provided parameters"

    # Fire-and-forget rules evaluation (errors silently ignored)
    try:
        engine = _get_rules_engine()
        if engine.get_rules():
            rule_data = {
                "ticker": ticker.upper(),
                "signal": consensus_resp.signal,
                "score": consensus_resp.score,
                "confidence": consensus_resp.confidence,
                "kelly_fraction": consensus_resp.kelly_fraction,
                "price": ctx.price,
                "sector": ctx.sector,
            }
            threading.Thread(target=engine.evaluate, args=(rule_data,), daemon=True).start()
    except Exception:
        pass

    return response


# ============ Report API ============

@router.get("/api/report/{ticker}", summary="生成深度分析报告")
def report_ticker(
    ticker: str,
    price: float = 0,
    pe: float = 0,
    pb: float = 0,
    revenue_growth: float = 0,
    gross_margins: float = 0,
    operating_margins: float = 0,
    roe: float = 0,
    debt_ratio: float = 0,
    fcf: float = 0,
    market_cap: float = 0,
    institutional_ownership: float = 0,
    insider_ownership: float = 0,
    current_ratio: float = 0,
    earnings_growth: float = 0,
    sector: str = "",
    industry: str = "",
    auto_fetch: bool = True,
):
    """
    生成深度分析报告（Markdown格式）

    基本用法: GET /api/report/AAPL (自动获取实时数据)
    手动指标: GET /api/report/AAPL?price=210&pe=32&auto_fetch=false

    同步 def：fetch_market_context 同步调用 yfinance，且 18 位投资大师的
    分析也是同步执行，async def 会阻塞事件循环——这是「深度报告」加载卡死的根因之一。
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    if len(sector) > 100:
        raise HTTPException(status_code=400, detail="Sector too long (max 100 characters).")
    if len(industry) > 100:
        raise HTTPException(status_code=400, detail="Industry too long (max 100 characters).")

    if not _check_rate_limit(ticker):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 30 requests per minute per ticker.")

    has_user_metrics = any([
        price > 0, pe > 0, pb > 0, revenue_growth != 0,
        gross_margins > 0, operating_margins != 0, roe > 0,
        debt_ratio > 0, fcf != 0, market_cap > 0,
    ])

    data_source = "manual"

    if not has_user_metrics and auto_fetch:
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            data_source = "yfinance"
        except (ImportError, Exception):
            data_source = "fallback"
            ctx = MarketContext(
                ticker=ticker.upper(),
                price=price, pe=pe, pb=pb,
                revenue_growth=revenue_growth, gross_margins=gross_margins,
                operating_margins=operating_margins, roe=roe,
                debt_ratio=debt_ratio, fcf=fcf, market_cap=market_cap,
                institutional_ownership=institutional_ownership,
                insider_ownership=insider_ownership,
                current_ratio=current_ratio, earnings_growth=earnings_growth,
                sector=sector, industry=industry,
            )
    else:
        ctx = MarketContext(
            ticker=ticker.upper(),
            price=price, pe=pe, pb=pb,
            revenue_growth=revenue_growth, gross_margins=gross_margins,
            operating_margins=operating_margins, roe=roe,
            debt_ratio=debt_ratio, fcf=fcf, market_cap=market_cap,
            institutional_ownership=institutional_ownership,
            insider_ownership=insider_ownership,
            current_ratio=current_ratio, earnings_growth=earnings_growth,
            sector=sector, industry=industry,
        )

    coord = get_coordinator()
    agent_responses = coord.analyze_with_all(ctx, enabled_personas=get_enabled_personas())
    consensus_resp = coord.get_consensus(
        agent_responses,
        ticker=ticker.upper(),
        context=ctx,
    )

    report = generate_report(ticker.upper(), ctx, agent_responses, consensus_resp)

    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "report": report,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_source": data_source,
    }


@router.post("/api/report/{ticker}", summary="从已有数据生成报告")
async def generate_report_from_data(ticker: str, request: Request):
    """Generate report from pre-computed analysis data (avoids re-running agents)."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    from augur.personas.base import AgentResponse, SignalType

    consensus_data = body.get("consensus", {})
    agents_data = body.get("agents", [])
    market_data = body.get("market_data", {})

    ctx = MarketContext(
        ticker=ticker.upper(),
        price=market_data.get("price", 0),
        pe=market_data.get("pe", 0),
        pb=market_data.get("pb", 0),
        roe=market_data.get("roe", 0),
        gross_margins=market_data.get("gross_margins", 0),
        operating_margins=market_data.get("operating_margins", 0),
        revenue_growth=market_data.get("revenue_growth", 0),
        debt_ratio=market_data.get("debt_ratio", 0),
        fcf=market_data.get("fcf", 0),
        market_cap=market_data.get("market_cap", 0),
        sector=market_data.get("sector", ""),
        industry=market_data.get("industry", ""),
    )

    signal_map = {
        "bullish": SignalType.BULLISH,
        "neutral": SignalType.NEUTRAL,
        "bearish": SignalType.BEARISH,
        "error": SignalType.ERROR,
    }
    results = {}
    for agent_data in agents_data:
        agent_id = agent_data.get("agent_id", "")
        results[agent_id] = AgentResponse(
            agent_id=agent_id,
            agent_name=agent_data.get("agent_name", agent_id),
            signal=signal_map.get(agent_data.get("signal", "neutral"), SignalType.NEUTRAL),
            confidence=agent_data.get("confidence", 0),
            score=agent_data.get("score", 0),
            reasoning=agent_data.get("reasoning", ""),
            key_findings=agent_data.get("key_findings", []),
            risks=agent_data.get("risks", []),
            metadata=agent_data.get("metadata", {}),
        )

    consensus_resp = AgentResponse(
        agent_id="consensus",
        agent_name="Multi-Agent Consensus",
        signal=signal_map.get(consensus_data.get("signal", "neutral"), SignalType.NEUTRAL),
        confidence=consensus_data.get("confidence", 0),
        score=consensus_data.get("score", 0),
        reasoning=consensus_data.get("reasoning", ""),
        key_findings=consensus_data.get("key_findings", []),
        risks=consensus_data.get("risks", []),
        metadata=consensus_data.get("metadata", {}),
    )

    report_md = generate_report(ticker.upper(), ctx, results, consensus_resp)

    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "report": report_md,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_source": "cached",
    }
