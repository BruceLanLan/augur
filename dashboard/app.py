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
    description="17位虚拟投资大师，多维度共识分析",
    version="3.0.0",
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
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Augur — 投资大师仪表盘",
        "agent_count": agent_count,
        "stats": stats,
        "featured": featured,
    })


@app.get("/personas", response_class=HTMLResponse)
async def personas_page(request: Request):
    return templates.TemplateResponse("personas.html", {
        "request": request,
        "personas": _persona_meta(),
        "title": "投资人人格系统",
    })


@app.get("/stocks", response_class=HTMLResponse)
async def stocks_page(request: Request):
    quick_tickers = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "BRK.B", "META", "AMZN", "PDD", "BIDU"]
    return templates.TemplateResponse("stocks.html", {
        "request": request,
        "title": "股票分析",
        "quick_tickers": quick_tickers,
    })


@app.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request):
    return templates.TemplateResponse("signals.html", {
        "request": request,
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
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "title": "设置",
        "personas": personas,
        "available_models": models_flat,
        "default_model": default_model,
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
    current_ratio: float = 1.5,
    earnings_growth: float = 0,
    sector: str = "",
    industry: str = "",
):
    """
    使用所有17位投资大师分析指定标的

    基本用法: GET /api/analyze/AAPL?price=210&pe=32&gross_margins=0.46
    """
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


@app.get("/health")
async def health():
    return {"status": "ok", "agents": len(get_registry().get_all())}


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
