"""Config, home-widgets, and test API routes.

Extracted from dashboard/app.py (router split R4).
Mounts via: app.include_router(config_router)
"""

import logging
import os
import re
import threading
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from augur.config import get_config, save_config, set_config
from dashboard.deps import get_registry

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Request models ----

class ConfigUpdateBody(BaseModel):
    """Request body for full config update."""
    defaults: Optional[Dict[str, Any]] = None
    per_agent: Optional[Dict[str, Any]] = None
    available_models: Optional[Dict[str, Any]] = None


class PersonaModelBody(BaseModel):
    """Request body for persona model update."""
    model: str


class HomeWidgetsBody(BaseModel):
    """Home dashboard widget customization."""
    pinned_tickers: Optional[List[str]] = None
    collapsed_panels: Optional[List[str]] = None


# ---- Home widgets helpers ----

_HOME_WIDGETS_LOCK = threading.RLock()
_HOME_WIDGETS_CACHE: Optional[Dict[str, Any]] = None
_DEFAULT_PINNED = ["AAPL", "NVDA", "MSFT", "TSLA", "GOOGL"]
_VALID_HOME_PANELS = frozenset({
    "market-pulse", "market-board", "hot-tickers", "sector-perf", "intl-markets",
    "crypto", "commodities-rates", "top-movers", "market-breadth", "fear-macro",
    "leaderboard", "recent-personas", "datasources",
})
_DEFAULT_HOME_WIDGETS: Dict[str, Any] = {
    "pinned_tickers": [],
    "collapsed_panels": [],
}


def _home_widgets_path() -> Path:
    path = Path.home() / ".augur" / "home_widgets.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_home_widgets_yaml() -> Dict[str, Any]:
    path = _home_widgets_path()
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Failed to load home widgets from %s: %s", path, e)
        return {}


def _normalize_ticker_list(items: Any, limit: int = 12) -> List[str]:
    if not isinstance(items, list):
        return []
    out: List[str] = []
    for raw in items:
        if not isinstance(raw, str):
            continue
        sym = raw.strip().upper()
        if not sym or not re.match(r"^[A-Z0-9._-]{1,20}$", sym):
            continue
        if sym not in out:
            out.append(sym)
        if len(out) >= limit:
            break
    return out


def _effective_pinned_tickers(widgets: Dict[str, Any]) -> List[str]:
    pinned = _normalize_ticker_list(widgets.get("pinned_tickers"))
    if pinned:
        return pinned
    try:
        from augur.cron import load_watchlist
        watchlist = load_watchlist().get("watchlist", [])
        from_watchlist = []
        for item in watchlist:
            if not isinstance(item, dict):
                continue
            sym = str(item.get("ticker", "")).strip().upper()
            if sym and sym not in from_watchlist:
                from_watchlist.append(sym)
            if len(from_watchlist) >= 8:
                break
        if from_watchlist:
            return from_watchlist
    except Exception:
        pass
    return list(_DEFAULT_PINNED)


def _normalize_collapsed_panels(items: Any) -> List[str]:
    if not isinstance(items, list):
        return []
    out: List[str] = []
    for raw in items:
        if not isinstance(raw, str):
            continue
        panel_id = raw.strip()
        if panel_id in _VALID_HOME_PANELS and panel_id not in out:
            out.append(panel_id)
    return out


def get_home_widgets() -> Dict[str, Any]:
    """Load persisted home dashboard widget preferences."""
    global _HOME_WIDGETS_CACHE
    with _HOME_WIDGETS_LOCK:
        if _HOME_WIDGETS_CACHE is not None:
            return dict(_HOME_WIDGETS_CACHE)
        stored = _load_home_widgets_yaml()
        merged = dict(_DEFAULT_HOME_WIDGETS)
        merged["pinned_tickers"] = _normalize_ticker_list(stored.get("pinned_tickers"))
        merged["collapsed_panels"] = _normalize_collapsed_panels(stored.get("collapsed_panels"))
        _HOME_WIDGETS_CACHE = merged
        return dict(merged)


def save_home_widgets(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and persist home dashboard widget preferences."""
    global _HOME_WIDGETS_CACHE
    cleaned = {
        "pinned_tickers": _normalize_ticker_list(data.get("pinned_tickers")),
        "collapsed_panels": _normalize_collapsed_panels(data.get("collapsed_panels")),
    }
    with _HOME_WIDGETS_LOCK:
        _HOME_WIDGETS_CACHE = cleaned
        _home_widgets_path().write_text(
            yaml.safe_dump(cleaned, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    return dict(cleaned)


from augur.optional_deps import is_available as _is_available  # noqa: E402
_HAS_AUGUR_DATA = _is_available("augur.data")


def _fetch_pinned_quotes(symbols: List[str]) -> List[Dict[str, Any]]:
    """Best-effort quotes for pinned watchlist strip."""
    if not symbols:
        return []
    quote_map: Dict[str, Dict[str, Any]] = {sym: {"symbol": sym} for sym in symbols}
    if _HAS_AUGUR_DATA:
        try:
            from augur.data import fetch_hot_tickers
            hot = fetch_hot_tickers(force_refresh=False)
            for row in hot or []:
                sym = str(row.get("symbol", "")).upper()
                if sym in quote_map:
                    quote_map[sym] = {
                        "symbol": sym,
                        "name": row.get("name", sym),
                        "price": row.get("price"),
                        "change_pct": row.get("change_pct"),
                    }
        except Exception as e:
            logger.debug("pinned quote fetch via hot tickers failed: %s", e)
    return [quote_map[sym] for sym in symbols]


# ---- Config routes ----

@router.get("/api/config", summary="获取系统配置")
async def api_get_config():
    """返回完整配置（敏感信息脱敏）"""
    config = get_config()

    def _mask_sensitive(d, parent_key=""):
        if isinstance(d, dict):
            masked = {}
            for k, v in d.items():
                k_lower = k.lower()
                if any(s in k_lower for s in ("key", "token", "secret")) and isinstance(v, str) and len(v) > 4:
                    masked[k] = "***" + v[-4:]
                elif isinstance(v, dict):
                    masked[k] = _mask_sensitive(v, k)
                elif isinstance(v, list):
                    masked[k] = v
                else:
                    masked[k] = v
            return masked
        return d

    return _mask_sensitive(config)


@router.put("/api/config", summary="更新系统配置")
async def api_put_config(body: ConfigUpdateBody):
    """更新完整配置"""
    data = body.dict(exclude_none=True)
    for key, value in data.items():
        set_config(key, value)
    save_config()
    return {"status": "ok", "message": "配置已更新"}


@router.get("/api/config/persona/{agent_id}", summary="获取Agent模型配置")
async def api_get_persona_config(agent_id: str):
    """获取单个 Agent 的模型配置"""
    if not re.match(r'^[a-z0-9_-]{1,50}$', agent_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid agent_id format. Use 1-50 lowercase letters, digits, hyphens, or underscores.",
        )
    config = get_config()
    per_agent = config.get("per_agent", {})
    default_model = config.get("defaults", {}).get("model", "")
    model = per_agent.get(agent_id, default_model)
    return {"agent_id": agent_id, "model": model}


@router.put("/api/config/persona/{agent_id}", summary="更新Agent模型配置")
async def api_put_persona_config(agent_id: str, body: PersonaModelBody):
    """更新单个 Agent 的模型配置"""
    agent = get_registry().get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Persona '{agent_id}' not found in registry")
    set_config(f"per_agent.{agent_id}", body.model)
    save_config()
    return {"status": "ok", "agent_id": agent_id, "model": body.model}


# ---- Home widgets routes ----

@router.get("/api/home/widgets", summary="获取首页小组件配置")
async def api_get_home_widgets():
    """Return Bloomberg-style home dashboard layout (pinned strip + collapsed panels)."""
    widgets = get_home_widgets()
    pinned = _effective_pinned_tickers(widgets)
    return {
        "status": "ok",
        "widgets": widgets,
        "pinned_tickers": pinned,
        "quotes": _fetch_pinned_quotes(pinned),
        "valid_panels": sorted(_VALID_HOME_PANELS),
    }


@router.put("/api/home/widgets", summary="保存首页小组件配置")
async def api_put_home_widgets(body: HomeWidgetsBody):
    """Persist pinned watchlist strip and collapsible panel state."""
    payload = body.model_dump(exclude_none=True)
    saved = save_home_widgets(payload)
    pinned = _effective_pinned_tickers(saved)
    return {
        "status": "ok",
        "widgets": saved,
        "pinned_tickers": pinned,
        "quotes": _fetch_pinned_quotes(pinned),
    }


@router.get("/api/models", summary="获取可用模型列表")
async def api_get_models():
    """返回所有可用模型（扁平列表）"""
    config = get_config()
    available_models = config.get("available_models", {})
    models_flat = []
    for provider, provider_models in available_models.items():
        if isinstance(provider_models, list):
            models_flat.extend(provider_models)
    return {"models": models_flat}


# ---- Config export/import/test routes ----

@router.get("/api/config/export", summary="导出配置")
async def api_config_export():
    """Export full config as JSON for backup/migration."""
    config = get_config()
    return JSONResponse(content=config)


@router.post("/api/config/import", summary="导入配置")
async def api_config_import(request: Request):
    """Import config from JSON body."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    for key, value in body.items():
        set_config(key, value)
    save_config()
    return {"status": "ok", "message": "配置已导入"}


@router.post("/api/config/test-datasource", summary="测试数据源连接")
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


@router.post("/api/config/test-notification", summary="测试通知渠道")
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
