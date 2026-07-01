"""HTML page routes: all browser-facing GET endpoints that render templates."""

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from augur.config import get_config
from augur.workspace import get_workspace, resolve_landing_url
from dashboard.deps import get_registry, templates
from dashboard.routes.personas import _persona_meta

router = APIRouter()


@router.get("/", response_class=HTMLResponse, summary="首页仪表盘")
async def index(request: Request):
    landing = resolve_landing_url(get_workspace(), path="/")
    if landing:
        return RedirectResponse(url=landing, status_code=302)
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


@router.get("/personas", response_class=HTMLResponse, summary="投资人人格系统页面")
async def personas_page(request: Request):
    return templates.TemplateResponse(request=request, name="personas.html", context={
        "personas": _persona_meta(),
        "title": "投资人人格系统",
    })


@router.get("/stocks", response_class=HTMLResponse, summary="股票分析页面")
async def stocks_page(request: Request):
    quick_tickers = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "BRK.B", "META", "AMZN", "PDD", "BIDU"]
    return templates.TemplateResponse(request=request, name="stocks.html", context={
        "title": "股票分析",
        "quick_tickers": quick_tickers,
    })


@router.get("/signals", response_class=HTMLResponse, summary="信号监控页面")
async def signals_page(request: Request):
    return templates.TemplateResponse(request=request, name="signals.html", context={
        "title": "信号监控",
    })


@router.get("/scanner", response_class=HTMLResponse, summary="市场扫描器页面")
async def scanner_page(request: Request):
    return templates.TemplateResponse(request=request, name="scanner.html", context={
        "title": "市场扫描器 - Scanner",
    })


@router.get("/watchlist", response_class=HTMLResponse, summary="自选股页面")
async def watchlist_page(request: Request):
    return templates.TemplateResponse(request=request, name="watchlist.html", context={
        "title": "自选股 - Watchlist",
    })


@router.get("/portfolio", response_class=HTMLResponse, summary="持仓管理页面")
async def portfolio_page(request: Request):
    return templates.TemplateResponse(request=request, name="portfolio.html", context={
        "title": "持仓管理 - Portfolio",
    })


@router.get("/settings", response_class=HTMLResponse, summary="设置页面")
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


@router.get("/create-persona", response_class=HTMLResponse, summary="创建自定义投资人页面")
async def create_persona_page(request: Request):
    return templates.TemplateResponse(request=request, name="create_persona.html", context={
        "title": "创建自定义投资人",
    })


@router.get("/report/{ticker}", response_class=HTMLResponse, summary="深度分析报告全屏页面")
async def report_view_page(request: Request, ticker: str):
    """Dedicated full-page report view for a ticker. Auto-fetches report on load."""
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format.")
    return templates.TemplateResponse(request=request, name="report_view.html", context={
        "title": f"{ticker.upper()} Deep Analysis Report - Augur",
        "ticker": ticker.upper(),
    })
