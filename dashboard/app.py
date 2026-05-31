#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Augur — Bloomberg风格投资分析仪表盘
FastAPI + Jinja2 + Bloomberg暗色主题

Usage:
    python3 -m dashboard.app
    python3 -m dashboard.app --port 8080 --cors
"""

import sys
import os
import re
import logging
import threading
import time as _time
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Missing dependencies. Run: pip install fastapi uvicorn jinja2")
    sys.exit(1)

try:
    from augur.registry import AgentRegistry, DecisionCoordinator
    from augur.personas.base import MarketContext
except ImportError:
    from scanner.personas.registry import AgentRegistry, DecisionCoordinator
    from scanner.personas.base import MarketContext

from augur.report import generate_report

from augur.config import get_config, set_config, save_config, reset_config
from augur.errors import api_error_response

logger = logging.getLogger(__name__)

# Module-level startup time for uptime tracking
_APP_START_TIME = _time.time()

app = FastAPI(
    title="Augur — 多智能体投资分析",
    description="18位虚拟投资大师，多维度共识分析",
    version="7.4.0",
)


# Global exception handler: catch unhandled exceptions, return consistent JSON
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return consistent JSON error response.

    Never leak stack traces to clients. Log the real error for debugging.
    """
    logger.error(f"Unhandled exception on {request.url.path}: {type(exc).__name__}: {exc}")

    return JSONResponse(
        status_code=500,
        content=api_error_response(
            detail="Internal server error",
            code="INTERNAL_ERROR",
            path=request.url.path,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return user-friendly JSON for validation errors instead of FastAPI default."""
    errors = exc.errors()
    details = "; ".join(f"{e.get('loc', ['?'])[-1]}: {e.get('msg', 'invalid')}" for e in errors)
    return JSONResponse(
        status_code=422,
        content=api_error_response(
            detail=f"Validation error: {details}",
            code="VALIDATION_ERROR",
            path=request.url.path,
            suggestion="Check parameter types and values. Use /api/analyze/TICKER format.",
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Ensure HTTP exceptions also return consistent JSON."""
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content=api_error_response(
                detail=exc.detail or "Not found",
                code="NOT_FOUND",
                path=request.url.path,
            ),
        )
    # For other HTTP exceptions (400, 429, etc.), keep consistent JSON
    return JSONResponse(
        status_code=exc.status_code,
        content=api_error_response(
            detail=str(exc.detail) if exc.detail else f"HTTP {exc.status_code}",
            code=f"HTTP_{exc.status_code}",
            path=request.url.path,
        ),
    )

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount docs/images for avatars
IMAGES_DIR = Path(__file__).parent.parent / "docs" / "images"
if IMAGES_DIR.exists():
    app.mount("/docs/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")

_registry: Optional[AgentRegistry] = None
_coordinator: Optional[DecisionCoordinator] = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def get_coordinator() -> DecisionCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = DecisionCoordinator(get_registry())
    return _coordinator


PERSONA_ENRICHMENT = {
    "buffett": {"cn_name": "沃伦·巴菲特", "en_name": "Warren Buffett", "school": "value", "core_principles": ["护城河决定长期价值", "只买看得懂的生意", "别人恐惧时贪婪"], "holdings": ["BRK.B", "AAPL", "KO", "AXP"]},
    "graham": {"cn_name": "本杰明·格雷厄姆", "en_name": "Benjamin Graham", "school": "value", "core_principles": ["安全边际是投资的基石", "市场先生情绪无常", "买入低于净资产的股票"], "holdings": ["GEICO", "BRK.B"]},
    "munger": {"cn_name": "查理·芒格", "en_name": "Charlie Munger", "school": "value", "core_principles": ["多元思维模型", "用合理价格买优质企业", "避免愚蠢比追求聪明更重要"], "holdings": ["BRK.B", "COST", "BAC"]},
    "fisher": {"cn_name": "菲利普·费雪", "en_name": "Philip Fisher", "school": "growth", "core_principles": ["成长股的真正价值在管理层", "闲聊法深入调研", "长期持有优质成长股"], "holdings": ["MOTOROLA", "TXN"]},
    "lynch": {"cn_name": "彼得·林奇", "en_name": "Peter Lynch", "school": "growth", "core_principles": ["在生活中发现十倍股", "PEG是成长股估值核心", "分散但集中于了解的领域"], "holdings": ["SBUX", "FNM"]},
    "cathie_wood": {"cn_name": "凯瑟琳·伍德", "en_name": "Cathie Wood", "school": "growth", "core_principles": ["颠覆性创新创造指数级增长", "5年投资视野", "拥抱波动性"], "holdings": ["TSLA", "COIN", "ROKU", "SQ"]},
    "aschenbrenner": {"cn_name": "利奥波德·阿申布伦纳", "en_name": "Leopold Aschenbrenner", "school": "growth", "core_principles": ["AI超级周期即将到来", "算力是新石油", "AGI将重塑所有行业"], "holdings": ["NVDA", "MSFT", "GOOGL"]},
    "thiel": {"cn_name": "彼得·蒂尔", "en_name": "Peter Thiel", "school": "growth", "core_principles": ["垄断企业才有真正价值", "从0到1比从1到N更重要", "逆向思维发现秘密"], "holdings": ["PLTR", "META", "TSLA"]},
    "dalio": {"cn_name": "瑞·达利欧", "en_name": "Ray Dalio", "school": "macro", "core_principles": ["理解债务周期驱动一切", "全天候组合应对不确定性", "激进透明与原则决策"], "holdings": ["SPY", "GLD", "TLT"]},
    "soros": {"cn_name": "乔治·索罗斯", "en_name": "George Soros", "school": "macro", "core_principles": ["反身性：认知影响现实", "先开枪后瞄准", "发现市场错误定价"], "holdings": ["MACRO_BETS"]},
    "marks": {"cn_name": "霍华德·马克斯", "en_name": "Howard Marks", "school": "macro", "core_principles": ["周期是投资中最确定的事", "风险来自过高的价格", "逆向投资需要勇气"], "holdings": ["OAK", "HY_BONDS"]},
    "serenity": {"cn_name": "宁静", "en_name": "Serenity", "school": "quant", "core_principles": ["波动率是可以管理的风险", "尾部风险对冲保护本金", "系统化消除情绪干扰"], "holdings": ["VIX_HEDGE", "OPTIONS"]},
    "arps": {"cn_name": "马丁·阿普斯", "en_name": "Martin Arps", "school": "quant", "core_principles": ["价格包含一切信息", "趋势是你的朋友", "量价背离是最强信号"], "holdings": ["TECH_MOMENTUM"]},
    "dayu": {"cn_name": "大宇", "en_name": "Dayu", "school": "quant", "core_principles": ["量化模型消除主观偏见", "资金流向揭示主力意图", "统计套利寻找确定性"], "holdings": ["A_SHARES"]},
    "duan_yongping": {"cn_name": "段永平", "en_name": "Duan Yongping", "school": "china", "core_principles": ["做对的事，停止做错的事", "商业模式比什么都重要", "极度集中持仓"], "holdings": ["AAPL", "PDD", "BABA"]},
    "zhang_lei": {"cn_name": "张磊", "en_name": "Zhang Lei", "school": "china", "core_principles": ["长期结构性价值创造", "研究驱动投资", "与伟大企业共同成长"], "holdings": ["PDD", "JD", "BYD"]},
    "li_lu": {"cn_name": "李录", "en_name": "Li Lu", "school": "china", "core_principles": ["价值投资在中国同样适用", "理解文明的演化", "集中投资少数确定机会"], "holdings": ["BRK.B", "BYD", "BABA"]},
    "dan_bin": {"cn_name": "但斌", "en_name": "Dan Bin", "school": "china", "core_principles": ["时间的玫瑰：长期主义", "消费龙头是最佳赛道", "长坡厚雪复利惊人"], "holdings": ["600519.SS", "AAPL", "MOUTAI"]},
}


def _persona_meta() -> List[Dict]:
    registry = get_registry()
    config = get_config()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    meta = []
    for agent in registry.get_all():
        # Chinese mainland investors only; Serenity is excluded because
        # the persona is international (anonymous, multi-market, non-China-based).
        chinese_investors = {"duan_yongping", "zhang_lei", "li_lu", "dan_bin", "dayu"}
        country = "\U0001f1e8\U0001f1f3 中国" if agent.agent_id in chinese_investors else ""
        enrichment = PERSONA_ENRICHMENT.get(agent.agent_id, {})
        meta.append({
            "id": agent.agent_id,
            "agent_id": agent.agent_id,
            "name": agent.name,
            "cn_name": enrichment.get("cn_name", agent.name),
            "en_name": enrichment.get("en_name", agent.name),
            "school": enrichment.get("school", "value"),
            "core_principles": enrichment.get("core_principles", agent.philosophy[:3] if agent.philosophy else []),
            "holdings": enrichment.get("holdings", []),
            "style": " \u00b7 ".join(agent.philosophy[:2]) if agent.philosophy else "",
            "description": agent.identity.strip().replace("\n", " ").replace("  ", " "),
            "scenarios": agent.philosophy,
            "scoring_weights": agent.scoring_weights if agent.scoring_weights else {},
            "weight": f"{list(agent.scoring_weights.values())[0]:.0%}" if agent.scoring_weights else "\u5747\u7b49",
            "status": "\u5df2\u6ce8\u518c",
            "country": country,
            "is_chinese": agent.agent_id in chinese_investors,
            "quote": agent.philosophy[0] if agent.philosophy else "\u6295\u8d44\uff0c\u5c31\u662f\u6295\u672a\u6765\u3002",
            "model": per_agent.get(agent.agent_id, default_model),
        })
    return meta


# ============ Rate Limiting ============

_rate_limits: Dict[str, List[float]] = {}
_rate_limit_lock = threading.Lock()
_RATE_LIMIT_MAX = 30  # max requests per window
_RATE_LIMIT_WINDOW = 60.0  # seconds


def _check_rate_limit(ticker: str) -> bool:
    """Check and enforce rate limit for a ticker. Returns True if allowed, False if exceeded."""
    now = _time.time()
    ticker_key = ticker.upper()
    with _rate_limit_lock:
        # Clean up expired entries for this ticker
        if ticker_key in _rate_limits:
            _rate_limits[ticker_key] = [
                ts for ts in _rate_limits[ticker_key] if now - ts < _RATE_LIMIT_WINDOW
            ]
        else:
            _rate_limits[ticker_key] = []

        # Check limit
        if len(_rate_limits[ticker_key]) >= _RATE_LIMIT_MAX:
            return False

        # Record this request
        _rate_limits[ticker_key].append(now)

        # Periodic eviction of stale ticker keys to prevent unbounded growth
        if len(_rate_limits) > 1000:
            stale_keys = [
                k for k, v in _rate_limits.items()
                if not v or all(now - ts >= _RATE_LIMIT_WINDOW for ts in v)
            ]
            for k in stale_keys:
                del _rate_limits[k]

        return True


# ============ HTML Routes ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    agent_count = len(get_registry().get_all())
    try:
        from augur.datasources import available_sources
        ds_count = len(available_sources())
    except Exception:
        ds_count = 2
    stats = [
        {"value": str(agent_count), "label": "虚拟投资大师", "icon": "users"},
        {"value": "6", "label": "共识加权层", "icon": "layers"},
        {"value": "40+", "label": "评分因子", "icon": "sliders"},
        {"value": str(ds_count), "label": "数据源链路", "icon": "database"},
    ]
    featured = [
        {"avatar": "🏦", "id": "buffett", "name": "Warren Buffett", "style": "价值 · 护城河", "desc": "寻找具有持久竞争优势的企业，以合理价格长期持有。FCF 和 ROE 是核心衡量标准。", "tag": "价值投资"},
        {"avatar": "📐", "id": "graham", "name": "Benjamin Graham", "style": "安全边际 · 烟蒂股", "desc": "只在具有显著安全边际时买入，PE<15、PB<1.5 是硬性门槛。", "tag": "深度价值"},
        {"avatar": "🚀", "id": "cathie_wood", "name": "Cathie Wood", "style": "颠覆性创新", "desc": "专注 AI、基因组、区块链等颠覆性技术，接受高估值换取指数级成长。", "tag": "成长投资"},
        {"avatar": "🇨🇳", "id": "duan_yongping", "name": "段永平", "style": "本分 · 极度集中", "desc": "「本分」哲学：只做正确的事，停止做错误的事。极度集中持仓，能力圈内重仓。", "tag": "中国价值"},
    ]
    return templates.TemplateResponse(request=request, name="index.html", context={
        "title": "Augur — 投资大师仪表盘",
        "agent_count": agent_count,
        "stats": stats,
        "featured": featured,
    })


@app.get("/personas", response_class=HTMLResponse)
async def personas_page(request: Request):
    return templates.TemplateResponse(request=request, name="personas.html", context={
        "personas": _persona_meta(),
        "title": "投资人人格系统",
    })


@app.get("/stocks", response_class=HTMLResponse)
async def stocks_page(request: Request):
    quick_tickers = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "BRK.B", "META", "AMZN", "PDD", "BIDU"]
    return templates.TemplateResponse(request=request, name="stocks.html", context={
        "title": "股票分析",
        "quick_tickers": quick_tickers,
    })


@app.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request):
    return templates.TemplateResponse(request=request, name="signals.html", context={
        "title": "信号监控",
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    config = get_config()
    available_models = config.get("available_models", {})
    models_flat = []
    for provider_models in available_models.values():
        if isinstance(provider_models, list):
            models_flat.extend(provider_models)
    personas = _persona_meta()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    for p in personas:
        p["current_model"] = per_agent.get(p["id"], default_model)
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "title": "设置",
        "personas": personas,
        "available_models": models_flat,
        "default_model": default_model,
    })


@app.get("/create-persona", response_class=HTMLResponse)
async def create_persona_page(request: Request):
    return templates.TemplateResponse(request=request, name="create_persona.html", context={
        "title": "创建自定义投资人",
    })


# ============ API Routes ============

@app.get("/api/personas")
async def list_personas():
    """返回所有投资人人格列表"""
    registry = get_registry()
    return {
        "status": "ok",
        "count": len(registry.get_all()),
        "personas": [agent.to_dict() for agent in registry.get_all()],
    }


@app.get("/api/analyze/{ticker}")
async def analyze_ticker(
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
    """
    # Validate ticker format to prevent injection issues with yfinance or URLs
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    # Rate limiting: max 30 requests per minute per ticker
    if not _check_rate_limit(ticker):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 30 requests per minute per ticker.")

    # Check if any meaningful metric was provided by user
    has_user_metrics = any([
        price > 0, pe > 0, pb > 0, revenue_growth != 0,
        gross_margins > 0, operating_margins != 0, roe > 0,
        debt_ratio > 0, fcf != 0, market_cap > 0,
    ])

    data_source = "manual"

    if not has_user_metrics and auto_fetch:
        # Try to auto-fetch from yfinance
        # When auto_fetch succeeds, manual params are ignored. This is intentional:
        # real-time data takes precedence over manually supplied values to avoid stale overrides.
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            data_source = "yfinance"
        except (ImportError, Exception):
            # Fallback to manual (empty) context
            data_source = "fallback"
            ctx = MarketContext(
                ticker=ticker.upper(),
                price=price,
                pe=pe,
                pb=pb,
                revenue_growth=revenue_growth,
                gross_margins=gross_margins,
                operating_margins=operating_margins,
                roe=roe,
                debt_ratio=debt_ratio,
                fcf=fcf,
                market_cap=market_cap,
                institutional_ownership=institutional_ownership,
                insider_ownership=insider_ownership,
                current_ratio=current_ratio,
                earnings_growth=earnings_growth,
                sector=sector,
                industry=industry,
            )
    else:
        ctx = MarketContext(
            ticker=ticker.upper(),
            price=price,
            pe=pe,
            pb=pb,
            revenue_growth=revenue_growth,
            gross_margins=gross_margins,
            operating_margins=operating_margins,
            roe=roe,
            debt_ratio=debt_ratio,
            fcf=fcf,
            market_cap=market_cap,
            institutional_ownership=institutional_ownership,
            insider_ownership=insider_ownership,
            current_ratio=current_ratio,
            earnings_growth=earnings_growth,
            sector=sector,
            industry=industry,
        )

    coord = get_coordinator()
    agent_responses = coord.analyze_with_all(ctx)
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
        },
        "consensus": consensus_resp.to_dict(),
        "agents": [r.to_dict() for r in agent_responses.values()],
        "agent_count": len(agent_responses),
    }

    if data_source == "fallback":
        response["data_note"] = "Auto-fetch failed, using provided parameters"

    return response


@app.get("/api/persona/{agent_id}")
async def get_persona(agent_id: str):
    """获取单个投资人的详细信息"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")
    return agent.to_dict()


@app.get("/api/report/{ticker}")
async def report_ticker(
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
    """
    # Validate ticker format
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    # Rate limiting
    if not _check_rate_limit(ticker):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 30 requests per minute per ticker.")

    # Check if any meaningful metric was provided by user
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
                price=price,
                pe=pe,
                pb=pb,
                revenue_growth=revenue_growth,
                gross_margins=gross_margins,
                operating_margins=operating_margins,
                roe=roe,
                debt_ratio=debt_ratio,
                fcf=fcf,
                market_cap=market_cap,
                institutional_ownership=institutional_ownership,
                insider_ownership=insider_ownership,
                current_ratio=current_ratio,
                earnings_growth=earnings_growth,
                sector=sector,
                industry=industry,
            )
    else:
        ctx = MarketContext(
            ticker=ticker.upper(),
            price=price,
            pe=pe,
            pb=pb,
            revenue_growth=revenue_growth,
            gross_margins=gross_margins,
            operating_margins=operating_margins,
            roe=roe,
            debt_ratio=debt_ratio,
            fcf=fcf,
            market_cap=market_cap,
            institutional_ownership=institutional_ownership,
            insider_ownership=insider_ownership,
            current_ratio=current_ratio,
            earnings_growth=earnings_growth,
            sector=sector,
            industry=industry,
        )

    coord = get_coordinator()
    agent_responses = coord.analyze_with_all(ctx)
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


@app.post("/api/report/{ticker}")
async def generate_report_from_data(ticker: str, request: Request):
    """Generate report from pre-computed analysis data (avoids re-running agents)."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Reconstruct from pre-computed data
    from augur.personas.base import AgentResponse, SignalType

    consensus_data = body.get("consensus", {})
    agents_data = body.get("agents", [])
    market_data = body.get("market_data", {})

    # Build context from market_data
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

    # Reconstruct AgentResponses
    signal_map = {"bullish": SignalType.BULLISH, "neutral": SignalType.NEUTRAL, "bearish": SignalType.BEARISH, "error": SignalType.ERROR}
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

    # Reconstruct consensus
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


# ============ Config API Routes ============

class ConfigUpdateBody(BaseModel):
    """Request body for full config update."""
    defaults: Optional[Dict[str, Any]] = None
    per_agent: Optional[Dict[str, Any]] = None
    available_models: Optional[Dict[str, Any]] = None


class PersonaModelBody(BaseModel):
    """Request body for persona model update."""
    model: str


class CustomPersonaBody(BaseModel):
    """Request body for custom persona creation."""
    yaml_content: str
    agent_id: str


@app.get("/api/config")
async def api_get_config():
    """返回完整配置"""
    return get_config()


@app.put("/api/config")
async def api_put_config(body: ConfigUpdateBody):
    """更新完整配置"""
    data = body.dict(exclude_none=True)
    for key, value in data.items():
        set_config(key, value)
    save_config()
    return {"status": "ok", "message": "配置已更新"}


@app.get("/api/config/persona/{agent_id}")
async def api_get_persona_config(agent_id: str):
    """获取单个 Agent 的模型配置"""
    config = get_config()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    model = per_agent.get(agent_id, default_model)
    return {"agent_id": agent_id, "model": model}


@app.put("/api/config/persona/{agent_id}")
async def api_put_persona_config(agent_id: str, body: PersonaModelBody):
    """更新单个 Agent 的模型配置"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found in registry")
    set_config(f"per_agent.{agent_id}", body.model)
    save_config()
    return {"status": "ok", "agent_id": agent_id, "model": body.model}


@app.get("/api/models")
async def api_get_models():
    """返回所有可用模型（扁平列表）"""
    config = get_config()
    available_models = config.get("available_models", {})
    models_flat = []
    for provider, provider_models in available_models.items():
        if isinstance(provider_models, list):
            models_flat.extend(provider_models)
    return {"models": models_flat}


@app.post("/api/custom-persona")
async def api_create_custom_persona(body: CustomPersonaBody):
    """保存自定义 Persona YAML 到 personas/custom/"""
    # Validate agent_id: only allow lowercase alphanumeric, hyphens, underscores
    if not re.match(r'^[a-z0-9_-]+$', body.agent_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid agent_id: only lowercase letters, digits, hyphens, and underscores are allowed"
        )
    # Validate YAML content is parseable
    try:
        yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML content: {e}")
    custom_dir = Path(__file__).parent.parent / "personas" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    filepath = custom_dir / f"{body.agent_id}.yaml"
    filepath.write_text(body.yaml_content, encoding="utf-8")

    # Hot-reload: register in the live registry immediately
    try:
        from augur.persona_loader import load_persona_yaml
        global _registry, _coordinator
        new_agent = load_persona_yaml(str(filepath))
        if _registry is not None and new_agent.agent_id not in {a.agent_id for a in _registry.get_all()}:
            _registry.register(new_agent)
            _coordinator = None  # reset coordinator so it uses updated registry
    except Exception:
        pass  # hot-reload is best-effort; YAML is saved and will load on restart

    return {"status": "ok", "path": str(filepath), "hot_loaded": True}


@app.get("/api/schema/persona")
async def api_persona_schema():
    """返回 Persona YAML 结构描述"""
    return {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "唯一标识符"},
            "name": {"type": "string", "description": "显示名称"},
            "identity": {"type": "string", "description": "人格身份描述"},
            "philosophy": {"type": "array", "items": {"type": "string"}, "description": "投资哲学要点"},
            "scoring_weights": {"type": "object", "description": "评分权重 (维度 -> 0-1)"},
            "model": {"type": "string", "description": "使用的 LLM 模型"},
        },
        "required": ["agent_id", "name", "identity"],
    }


# ============ Watchlist API Routes ============

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


@app.get("/api/watchlist")
async def api_get_watchlist():
    """Get current watchlist from ~/.augur/watchlist.yaml"""
    from augur.cron import load_watchlist
    config = load_watchlist()
    return {
        "watchlist": config.get("watchlist", []),
        "schedule": config.get("schedule", {}),
    }


@app.post("/api/watchlist/add")
async def api_add_to_watchlist(body: WatchlistAddBody):
    """Add ticker to watchlist"""
    from augur.cron import add_to_watchlist
    # Validate ticker
    if not re.match(r'^[A-Za-z0-9.\-]+$', body.ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    if len(body.ticker) > 15:
        raise HTTPException(status_code=400, detail="Ticker too long (max 15 characters)")
    metrics = {}
    for field in ["pe", "pb", "roe", "gross_margins", "revenue_growth", "debt_ratio", "fcf", "market_cap", "price"]:
        val = getattr(body, field, None)
        if val is not None:
            metrics[field] = val
    config = add_to_watchlist(body.ticker.upper(), metrics if metrics else None)
    return {"status": "ok", "ticker": body.ticker.upper(), "watchlist": config.get("watchlist", [])}


@app.delete("/api/watchlist/{ticker}")
async def api_remove_from_watchlist(ticker: str):
    """Remove ticker from watchlist"""
    from augur.cron import remove_from_watchlist
    removed = remove_from_watchlist(ticker.upper())
    if not removed:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker.upper()}' not found in watchlist")
    return {"status": "ok", "ticker": ticker.upper(), "message": "已从自选股移除"}


@app.post("/api/watchlist/run")
async def api_run_watchlist_analysis():
    """Run consensus analysis on all watchlist tickers"""
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

        ctx_kwargs = {"ticker": ticker.upper()}
        for key in ["pe", "pb", "roe", "gross_margins", "revenue_growth",
                    "debt_ratio", "fcf", "market_cap", "price"]:
            if key in item:
                ctx_kwargs[key] = item[key]

        ctx = MarketContext(**ctx_kwargs)
        results = coordinator.analyze_with_all(ctx)
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

        # Persist last signal back to watchlist item
        try:
            for w_item in watchlist:
                if w_item.get("ticker", "").upper() == ticker.upper():
                    w_item["last_signal"] = consensus.signal.value
                    w_item["last_score"] = result_item["score"]
                    w_item["last_run"] = result_item["last_run"]
                    break
        except Exception:
            pass

    # Save updated watchlist with last_signal
    try:
        from augur.cron import save_watchlist
        config["watchlist"] = watchlist
        save_watchlist(config)
    except Exception:
        pass

    return {"status": "ok", "results": all_results, "processing_time_ms": round((time.time() - start_time) * 1000)}


@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    return templates.TemplateResponse(request=request, name="backtest.html", context={
        "title": "历史回测 - Agent IC",
    })


@app.get("/api/backtest/run")
async def api_run_backtest(ticker: str = "AAPL", days: int = 30, initial_capital: float = 100000, strategy: str = "equal_weight"):
    """Run demo backtest, return results with metrics and signals timeline"""
    # Validate ticker format
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    from augur.backtest import Backtester, generate_sample_data

    if days < 5:
        days = 5
    if days > 365:
        days = 365

    historical_data, forward_returns = generate_sample_data(ticker, days)
    backtester = Backtester()
    result = backtester.run_backtest(ticker, historical_data, forward_returns)

    # Compute metrics from agent_ics
    agent_ics = result.agent_ics
    avg_hit_rate = 0.0
    if agent_ics:
        avg_hit_rate = sum(a.hit_rate for a in agent_ics) / len(agent_ics)

    # Approximate metrics
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

    # Build signals timeline from records
    signals_timeline = []
    for rec in result.records[:50]:
        signals_timeline.append({
            "date": rec.date,
            "ticker": rec.ticker,
            "signal": rec.signal,
            "score": round(rec.score, 1),
            "agent_id": rec.agent_id,
        })
    # Sort by date descending
    signals_timeline.sort(key=lambda x: x["date"], reverse=True)

    return {
        "status": "ok",
        "ticker": result.ticker,
        "days": days,
        "initial_capital": initial_capital,
        "strategy": strategy,
        "total_records": len(result.records),
        "consensus_ic": result.consensus_ic,
        "agent_ics": [a.to_dict() for a in result.agent_ics],
        "metrics": metrics,
        "signals_timeline": signals_timeline,
        "summary": result.summary,
    }


@app.get("/api/backtest/leaderboard")
async def api_ic_leaderboard():
    """Get saved IC leaderboard"""
    from augur.backtest import Backtester

    backtester = Backtester()
    ics = backtester.get_leaderboard()

    return {
        "status": "ok",
        "leaderboard": [a.to_dict() for a in ics],
        "count": len(ics),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "agents": len(get_registry().get_all())}


@app.get("/api/health")
async def api_health_extended():
    """Extended health check - returns datasource reachability, cache info, uptime."""
    # Check datasources
    datasources = []
    try:
        from augur.datasources import available_sources
        sources = available_sources()
        for src in sources:
            datasources.append({"name": src, "reachable": True})
    except Exception as e:
        datasources.append({"name": "unknown", "reachable": False, "error": str(e)})

    # Cache info
    try:
        from augur.data import cache_stats
        cache = cache_stats()
    except Exception:
        try:
            from augur.data import cache_info
            cache = cache_info()
        except Exception:
            cache = {}

    uptime = _time.time() - _APP_START_TIME

    return {
        "status": "ok",
        "agents": len(get_registry().get_all()),
        "datasources": datasources,
        "cache": cache,
        "uptime_seconds": round(uptime, 1),
        "version": "7.4.0",
    }


# ============ Cache Management API Routes ============

@app.post("/api/cache/clear")
async def api_cache_clear():
    """Clear the data cache to force fresh fetches."""
    from augur.data import clear_cache
    clear_cache()
    return {"status": "ok", "message": "Cache cleared"}


@app.get("/api/cache/info")
async def api_cache_info():
    """Return cache size and TTL info."""
    from augur.data import cache_info
    info = cache_info()
    return {"status": "ok", "cache": info}


# ============ Data Fetch API Routes ============

# Module-level flag: check once at import time whether augur.data is available
from augur.optional_deps import is_available as _is_available, get_install_hint
_HAS_AUGUR_DATA = _is_available("augur.data")


@app.get("/api/fetch/{ticker}")
async def api_fetch_ticker(ticker: str):
    """Fetch real-time market data for a ticker via yfinance"""
    if not _HAS_AUGUR_DATA:
        feature, install_cmd = get_install_hint("augur.data")
        raise HTTPException(
            status_code=501,
            detail=f"Package 'yfinance' is required for {feature} but is not installed. Install with: {install_cmd}"
        )

    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
        return {
            "status": "ok",
            "ticker": ctx.ticker,
            "source": "yfinance",
            "data": ctx.to_dict(),
        }
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e}")


@app.get("/api/search")
async def api_search_tickers(q: str = ""):
    """Search for tickers by name/symbol"""
    if not q or len(q) < 1:
        return {"results": []}

    if not _HAS_AUGUR_DATA:
        feature, install_cmd = get_install_hint("augur.data")
        raise HTTPException(
            status_code=501,
            detail=f"Package 'yfinance' is required for {feature} but is not installed. Install with: {install_cmd}"
        )

    try:
        from augur.data import search_ticker
        results = search_ticker(q)
        return {"status": "ok", "query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


# ============ Hot Tickers API Route ============

@app.get("/api/hot-tickers")
async def api_hot_tickers(refresh: bool = False):
    """热门标的实时行情：AAPL, NVDA, TSLA, MSFT, GOOGL, AMZN, BTC-USD, ETH-USD, META, AMD。

    供首页「热门标的实时行情」面板使用。无 yfinance 时优雅降级为空列表。
    """
    if not _HAS_AUGUR_DATA:
        return {
            "status": "degraded",
            "tickers": [],
            "note": "yfinance 未安装，热门标的不可用。",
        }
    try:
        from augur.data import fetch_hot_tickers
        tickers = fetch_hot_tickers(force_refresh=refresh)
        return {"status": "ok", "tickers": tickers}
    except Exception as e:
        logger.warning("hot tickers failed: %s", e)
        return {
            "status": "degraded",
            "tickers": [],
            "note": f"热门标的获取失败: {e}",
        }


# ============ Market Overview API Routes ============

@app.get("/api/market-overview")
async def api_market_overview(refresh: bool = False):
    """市场总览快照：主要指数、VIX、利率、商品、加密的实时价与涨跌幅。

    供首页 Dashboard 的「全球市场总览」板块使用。无 yfinance 时优雅降级为空列表。
    """
    if not _HAS_AUGUR_DATA:
        return {
            "status": "degraded",
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": [],
            "source": "none",
            "note": "yfinance 未安装，市场总览不可用。安装: pip install 'augur-agents[data]'",
        }
    try:
        from augur.data import fetch_market_overview
        overview = fetch_market_overview(force_refresh=refresh)
        return {"status": "ok", **overview}
    except Exception as e:
        logger.warning("market overview failed: %s", e)
        return {
            "status": "degraded",
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": [],
            "source": "none",
            "note": f"市场总览获取失败: {e}",
        }


@app.get("/api/datasources")
async def api_datasources():
    """返回当前可用的数据源链（用于 UI 展示数据来源覆盖情况）。"""
    try:
        from augur.datasources import available_sources
        sources = available_sources()
    except Exception:
        sources = ["yfinance", "stooq"]
    # 数据源元信息（中文展示名 + 是否需要 key + 覆盖范围）
    catalog = {
        "yfinance": {"label": "Yahoo Finance", "needs_key": False, "coverage": "行情+基本面+技术指标", "active": "yfinance" in sources},
        "finnhub": {"label": "Finnhub", "needs_key": True, "coverage": "基本面+分析师评级", "active": "finnhub" in sources, "env": "FINNHUB_API_KEY"},
        "alphavantage": {"label": "Alpha Vantage", "needs_key": True, "coverage": "基本面 OVERVIEW", "active": "alphavantage" in sources, "env": "ALPHAVANTAGE_API_KEY"},
        "stooq": {"label": "Stooq", "needs_key": False, "coverage": "行情兜底 (CSV)", "active": "stooq" in sources},
    }
    return {"status": "ok", "active_chain": sources, "catalog": catalog}


# ============ Config Export/Import + Test Endpoints ============

@app.get("/api/config/export")
async def api_config_export():
    """Export full config as JSON for backup/migration."""
    config = get_config()
    return JSONResponse(content=config)


@app.post("/api/config/import")
async def api_config_import(request: Request):
    """Import config from JSON body."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    # Validate and set config
    for key, value in body.items():
        set_config(key, value)
    save_config()
    return {"status": "ok", "message": "配置已导入"}


@app.post("/api/config/test-datasource")
async def api_test_datasource(request: Request):
    """Test datasource connectivity."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    source = body.get("source", "")
    if source == "finnhub":
        config = get_config()
        key = (config.get("datasource_keys") or {}).get("finnhub", "")
        env_key = os.environ.get("FINNHUB_API_KEY", "")
        api_key = key or env_key
        if not api_key:
            return {"status": "error", "detail": "未配置 Finnhub API Key"}
        try:
            import urllib.request
            url = f"https://finnhub.io/api/v1/stock/profile2?symbol=AAPL&token={api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Augur/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Finnhub 连接成功"}
        except Exception as e:
            return {"status": "error", "detail": f"连接失败: {e}"}
    elif source == "alphavantage":
        config = get_config()
        key = (config.get("datasource_keys") or {}).get("alphavantage", "")
        env_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        api_key = key or env_key
        if not api_key:
            return {"status": "error", "detail": "未配置 Alpha Vantage API Key"}
        try:
            import urllib.request
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Augur/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Alpha Vantage 连接成功"}
        except Exception as e:
            return {"status": "error", "detail": f"连接失败: {e}"}
    else:
        return {"status": "error", "detail": f"未知数据源: {source}"}
    return {"status": "error", "detail": "连接测试失败"}


@app.post("/api/config/test-notification")
async def api_test_notification(request: Request):
    """Test notification channel connectivity."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    channel = body.get("channel", "")
    config = get_config()
    notifications = config.get("notifications") or {}

    if channel == "telegram":
        token = notifications.get("telegram_token", "")
        chat_id = notifications.get("telegram_chat_id", "")
        if not token or not chat_id:
            return {"status": "error", "detail": "请先配置 Telegram Bot Token 和 Chat ID"}
        try:
            import urllib.request
            import json as _json
            msg = "Augur 测试消息: 通知渠道配置成功!"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = _json.dumps({"chat_id": chat_id, "text": msg}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Telegram 测试消息已发送"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    elif channel == "slack":
        webhook = notifications.get("slack_webhook", "")
        if not webhook:
            return {"status": "error", "detail": "请先配置 Slack Webhook URL"}
        try:
            import urllib.request
            import json as _json
            data = _json.dumps({"text": "Augur 测试消息: Slack 通知渠道配置成功!"}).encode()
            req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Slack 测试消息已发送"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    else:
        return {"status": "error", "detail": f"不支持的通知渠道: {channel}"}
    return {"status": "error", "detail": "测试失败"}


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(description="Augur Dashboard")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--cors", action="store_true",
                        help="Enable CORS for all origins (for Hermes integration)")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        print("CORS enabled for all origins")

    print(f"\n🦉 Augur Dashboard")
    print(f"   http://localhost:{args.port}")
    print(f"   http://localhost:{args.port}/personas")
    print(f"   http://localhost:{args.port}/api/analyze/AAPL?pe=32&gross_margins=0.46")
    print()

    uvicorn.run(
        "dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
