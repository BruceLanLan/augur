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
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
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

from augur.config import get_config, set_config, save_config, reset_config

app = FastAPI(
    title="Augur — 多智能体投资分析",
    description="18位虚拟投资大师，多维度共识分析",
    version="6.0.0",
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


def _persona_meta() -> List[Dict]:
    registry = get_registry()
    config = get_config()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    meta = []
    for agent in registry.get_all():
        chinese_investors = {"duan_yongping", "zhang_lei", "li_lu", "dan_bin", "dayu"}
        country = "🇨🇳 中国" if agent.agent_id in chinese_investors else ""
        meta.append({
            "id": agent.agent_id,
            "agent_id": agent.agent_id,
            "name": agent.name,
            "style": " · ".join(agent.philosophy[:2]) if agent.philosophy else "",
            "description": agent.identity.strip().replace("\n", " ").replace("  ", " "),
            "scenarios": agent.philosophy,
            "scoring_weights": agent.scoring_weights if agent.scoring_weights else {},
            "weight": f"{list(agent.scoring_weights.values())[0]:.0%}" if agent.scoring_weights else "均等",
            "status": "已注册",
            "country": country,
            "is_chinese": agent.agent_id in chinese_investors,
            "quote": agent.philosophy[0] if agent.philosophy else "投资，就是投未来。",
            "model": per_agent.get(agent.agent_id, default_model),
        })
    return meta


# ============ HTML Routes ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    agent_count = len(get_registry().get_all())
    stats = [
        {"value": str(agent_count), "label": "虚拟投资大师"},
        {"value": "5", "label": "SEC 13F 数据源"},
        {"value": "17", "label": "维度权重系统"},
        {"value": "实时", "label": "共识决策引擎"},
    ]
    featured = [
        {"avatar": "🏦", "name": "Warren Buffett", "style": "价值 · 护城河", "desc": "寻找具有持久竞争优势的企业，以合理价格长期持有。FCF 和 ROE 是核心衡量标准。", "tag": "价值投资"},
        {"avatar": "📐", "name": "Benjamin Graham", "style": "安全边际 · 烟蒂股", "desc": "只在具有显著安全边际时买入，PE<15、PB<1.5 是硬性门槛。", "tag": "深度价值"},
        {"avatar": "🚀", "name": "Cathie Wood", "style": "颠覆性创新", "desc": "专注 AI、基因组、区块链等颠覆性技术，接受高估值换取指数级成长。", "tag": "成长投资"},
        {"avatar": "🇨🇳", "name": "段永平", "style": "本分 · 极度集中", "desc": "「本分」哲学：只做正确的事，停止做错误的事。极度集中持仓，能力圈内重仓。", "tag": "中国价值"},
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
    # Check if any meaningful metric was provided by user
    has_user_metrics = any([
        price > 0, pe > 0, pb > 0, revenue_growth != 0,
        gross_margins > 0, operating_margins != 0, roe > 0,
        debt_ratio > 0, fcf != 0, market_cap > 0,
    ])

    data_source = "manual"

    if not has_user_metrics and auto_fetch:
        # Try to auto-fetch from yfinance
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            data_source = "yfinance"
        except (ImportError, Exception):
            # Fallback to manual (empty) context
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

    return {
        "ticker": ticker.upper(),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
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


@app.get("/api/persona/{agent_id}")
async def get_persona(agent_id: str):
    """获取单个投资人的详细信息"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")
    return agent.to_dict()


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
    return {"status": "ok", "path": str(filepath)}


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
    from augur.cron import load_watchlist
    from augur.personas.base import MarketContext

    config = load_watchlist()
    watchlist = config.get("watchlist", [])

    if not watchlist:
        return {"status": "empty", "message": "自选股列表为空", "results": []}

    coordinator = get_coordinator()
    all_results = []

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

        all_results.append({
            "ticker": ticker,
            "signal": consensus.signal.value,
            "score": round(consensus.score, 1),
            "confidence": round(consensus.confidence, 2) if hasattr(consensus, 'confidence') else 0.0,
            "agent_count": len(results),
            "buy_count": sum(1 for r in results.values() if r.signal.value == "buy"),
            "sell_count": sum(1 for r in results.values() if r.signal.value == "sell"),
            "hold_count": sum(1 for r in results.values() if r.signal.value == "hold"),
        })

    return {"status": "ok", "results": all_results}


@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    return templates.TemplateResponse(request=request, name="backtest.html", context={
        "title": "历史回测 - Agent IC",
    })


@app.get("/api/backtest/run")
async def api_run_backtest(ticker: str = "AAPL", days: int = 30):
    """Run demo backtest, return results"""
    from augur.backtest import Backtester, generate_sample_data

    if days < 5:
        days = 5
    if days > 120:
        days = 120

    historical_data, forward_returns = generate_sample_data(ticker, days)
    backtester = Backtester()
    result = backtester.run_backtest(ticker, historical_data, forward_returns)

    return {
        "status": "ok",
        "ticker": result.ticker,
        "days": days,
        "total_records": len(result.records),
        "consensus_ic": result.consensus_ic,
        "agent_ics": [a.to_dict() for a in result.agent_ics],
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


# ============ Data Fetch API Routes ============

@app.get("/api/fetch/{ticker}")
async def api_fetch_ticker(ticker: str):
    """Fetch real-time market data for a ticker via yfinance"""
    try:
        from augur.data import fetch_market_context
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="yfinance not installed. Install with: pip install 'augur-agents[data]'"
        )

    try:
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

    try:
        from augur.data import search_ticker
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="yfinance not installed. Install with: pip install 'augur-agents[data]'"
        )

    try:
        results = search_ticker(q)
        return {"status": "ok", "query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


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
            allow_methods=["GET", "POST"],
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
