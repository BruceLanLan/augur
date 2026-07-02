"""Persona list, detail, opinion, and custom-persona CRUD routes.

Extracted from dashboard/app.py (router split R4).
Mounts via: app.include_router(personas_router)
"""

import logging
import re
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from augur.config import get_config
from augur.personas.base import MarketContext
from dashboard.deps import get_registry
import dashboard.deps as _deps

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Persona enrichment metadata ----

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
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    meta = []
    for agent in registry.get_all():
        chinese_investors = {"duan_yongping", "zhang_lei", "li_lu", "dan_bin", "dayu"}
        country = "\U0001f1e8\U0001f1f3 中国" if agent.agent_id in chinese_investors else ""
        enrichment = PERSONA_ENRICHMENT.get(agent.agent_id, {})
        is_custom = (custom_dir / f"{agent.agent_id}.yaml").exists()
        meta.append({
            "id": agent.agent_id,
            "agent_id": agent.agent_id,
            "name": agent.name,
            "cn_name": enrichment.get("cn_name", agent.name),
            "en_name": enrichment.get("en_name", agent.name),
            "school": enrichment.get("school", "value"),
            "core_principles": enrichment.get("core_principles", agent.philosophy[:3] if agent.philosophy else []),
            "holdings": enrichment.get("holdings", []),
            "style": " · ".join(agent.philosophy[:2]) if agent.philosophy else "",
            "description": agent.identity.strip().replace("\n", " ").replace("  ", " "),
            "scenarios": agent.philosophy,
            "scoring_weights": agent.scoring_weights if agent.scoring_weights else {},
            "weight": f"{list(agent.scoring_weights.values())[0]:.0%}" if agent.scoring_weights else "均等",
            "status": "已注册",
            "country": country,
            "is_chinese": agent.agent_id in chinese_investors,
            "chip_name": (
                enrichment.get("en_name", agent.name)
                if agent.agent_id in chinese_investors
                else enrichment.get("en_name", agent.name).split()[-1]
            ),
            "is_custom": is_custom,
            "quote": agent.philosophy[0] if agent.philosophy else "投资，就是投未来。",
            "model": per_agent.get(agent.agent_id, default_model),
        })
    return meta


# ---- Request models ----

class CustomPersonaBody(BaseModel):
    """Request body for custom persona creation."""
    yaml_content: str
    agent_id: str


# ---- Routes ----

@router.get("/api/personas", summary="获取所有投资人列表")
async def list_personas():
    """返回所有投资人人格列表"""
    registry = get_registry()
    return {
        "status": "ok",
        "count": len(registry.get_all()),
        "personas": [agent.to_dict() for agent in registry.get_all()],
    }


@router.get("/api/persona/compare", summary="对比两位投资大师对同一标的的观点")
def compare_personas(persona1: str, persona2: str, ticker: str):
    """
    对比两位投资大师对同一标的的分析观点。

    同步 def：fetch_market_context 同步调用 yfinance，async def 会阻塞事件循环。
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    registry = get_registry()
    agent1 = registry.get(persona1)
    agent2 = registry.get(persona2)

    if not agent1:
        raise HTTPException(status_code=404, detail=f"Persona '{persona1}' not found")
    if not agent2:
        raise HTTPException(status_code=404, detail=f"Persona '{persona2}' not found")

    ctx = MarketContext(ticker=ticker.upper())
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        pass

    try:
        resp1 = agent1.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {persona1}: {e}")

    try:
        resp2 = agent2.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {persona2}: {e}")

    enrichment1 = PERSONA_ENRICHMENT.get(persona1, {})
    enrichment2 = PERSONA_ENRICHMENT.get(persona2, {})

    def _build_result(agent_id, agent, resp, enrichment):
        return {
            "agent_id": agent_id,
            "agent_name": enrichment.get("cn_name", agent.name),
            "en_name": enrichment.get("en_name", agent.name),
            "school": enrichment.get("school", ""),
            "signal": resp.signal.value,
            "score": round(resp.score, 1),
            "confidence": round(resp.confidence, 2),
            "reasoning": resp.reasoning,
            "key_findings": resp.key_findings,
            "risks": resp.risks if hasattr(resp, "risks") else [],
        }

    return {
        "status": "ok",
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "persona1": _build_result(persona1, agent1, resp1, enrichment1),
        "persona2": _build_result(persona2, agent2, resp2, enrichment2),
        "agreement": resp1.signal == resp2.signal,
        "score_diff": round(abs(resp1.score - resp2.score), 1),
    }


@router.get("/api/persona/{agent_id}", summary="获取单个投资人详情")
async def get_persona(agent_id: str):
    """获取单个投资人的详细信息"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")
    return agent.to_dict()


@router.get("/api/persona/{agent_id}/opinion", summary="获取单个投资人对标的的分析观点")
def get_persona_opinion(agent_id: str, ticker: str, question: Optional[str] = None):
    """
    使用单个投资大师分析指定标的，返回其独立观点。

    同步 def：fetch_market_context 同步调用 yfinance，async def 会阻塞事件循环。
    """
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens.")

    if question is not None and len(question) > 500:
        raise HTTPException(status_code=400, detail="Question too long (max 500 characters).")

    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found")

    ctx = MarketContext(ticker=ticker.upper())
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
    except Exception:
        pass

    try:
        response = agent.analyze(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    enrichment = PERSONA_ENRICHMENT.get(agent_id, {})

    return {
        "status": "ok",
        "agent_id": agent_id,
        "agent_name": enrichment.get("cn_name", agent.name),
        "ticker": ticker.upper(),
        "signal": response.signal.value,
        "score": round(response.score, 1),
        "confidence": round(response.confidence, 2),
        "reasoning": response.reasoning,
        "key_findings": response.key_findings,
        "risks": response.risks if hasattr(response, "risks") else [],
        "question": question,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@router.post("/api/custom-persona", summary="创建自定义投资人")
async def api_create_custom_persona(body: CustomPersonaBody):
    """保存自定义 Persona YAML 到 personas/custom/"""
    if not re.match(r'^[a-z0-9_-]+$', body.agent_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid agent_id: only lowercase letters, digits, hyphens, and underscores are allowed",
        )
    if len(body.agent_id) > 50:
        raise HTTPException(status_code=400, detail="agent_id too long (max 50 characters)")
    if '..' in body.agent_id:
        raise HTTPException(status_code=400, detail="agent_id contains invalid characters")
    try:
        yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML content: {e}")
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    filepath = custom_dir / f"{body.agent_id}.yaml"
    filepath.write_text(body.yaml_content, encoding="utf-8")

    try:
        from augur.persona_loader import load_persona_yaml
        new_agent = load_persona_yaml(str(filepath))
        with _deps._singleton_init_lock:
            if _deps._registry is not None and new_agent.agent_id not in {a.agent_id for a in _deps._registry.get_all()}:
                _deps._registry.register(new_agent)
                _deps._coordinator = None
    except Exception:
        pass

    return {"status": "ok", "path": str(filepath), "hot_loaded": True}


@router.get("/api/custom-personas", summary="列出所有自定义投资人")
async def api_list_custom_personas():
    """列出 personas/custom/ 目录下的所有自定义投资人"""
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    personas = []
    for fp in sorted(custom_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
            personas.append({
                "agent_id": data.get("agent_id", fp.stem),
                "name": data.get("name", fp.stem),
                "filepath": str(fp),
            })
        except Exception:
            personas.append({
                "agent_id": fp.stem,
                "name": fp.stem,
                "filepath": str(fp),
            })
    return {"status": "ok", "personas": personas}


@router.delete("/api/custom-persona/{agent_id}", summary="删除自定义投资人")
async def api_delete_custom_persona(agent_id: str):
    """删除 personas/custom/ 下的自定义投资人 YAML 并从注册表注销"""
    if not re.match(r'^[a-z0-9_-]+$', agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    filepath = custom_dir / f"{agent_id}.yaml"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Custom persona '{agent_id}' not found")
    filepath.unlink()
    with _deps._singleton_init_lock:
        if _deps._registry is not None:
            try:
                _deps._registry.unregister(agent_id)
                _deps._coordinator = None
            except Exception:
                pass
    return {"status": "ok", "agent_id": agent_id, "message": "已删除"}


@router.put("/api/custom-persona/{agent_id}", summary="更新自定义投资人")
async def api_update_custom_persona(agent_id: str, body: CustomPersonaBody):
    """更新已有的自定义投资人 YAML，热重载"""
    if not re.match(r'^[a-z0-9_-]+$', agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
    filepath = custom_dir / f"{agent_id}.yaml"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Custom persona '{agent_id}' not found")
    try:
        yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML content: {e}")
    filepath.write_text(body.yaml_content, encoding="utf-8")
    try:
        from augur.persona_loader import load_persona_yaml
        new_agent = load_persona_yaml(str(filepath))
        with _deps._singleton_init_lock:
            if _deps._registry is not None:
                try:
                    _deps._registry.unregister(agent_id)
                except Exception:
                    pass
                _deps._registry.register(new_agent)
                _deps._coordinator = None
    except Exception:
        pass
    return {"status": "ok", "agent_id": agent_id, "path": str(filepath), "hot_loaded": True}
