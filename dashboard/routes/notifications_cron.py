"""Notifications and cron config API routes — /api/notifications/* and /api/cron/*.

Extracted from dashboard/app.py (router split R5).
Mounts via: app.include_router(notifications_cron_router)
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from augur.config import get_config, save_config, set_config

logger = logging.getLogger(__name__)

# Project-level config directory (two levels up from dashboard/routes/)
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

router = APIRouter()


# ---- Request models ----

class NotificationTestBody(BaseModel):
    channel: str  # telegram, slack, wechat, lark


class CronConfigBody(BaseModel):
    """Request body for cron config update."""
    schedule: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None


# ---- Notifications ----

@router.post("/api/notifications/test", summary="发送测试通知")
async def api_notifications_test(body: NotificationTestBody):
    """Test notification channel by sending a test message."""
    channel = body.channel.lower()
    if channel not in ("telegram", "slack", "wechat", "lark"):
        raise HTTPException(status_code=400, detail=f"Unsupported channel: {channel}")

    config = get_config()
    notifications = config.get("notifications") or {}

    if channel == "telegram":
        token = notifications.get("telegram_token", "")
        chat_id = notifications.get("telegram_chat_id", "")
        if not token or not chat_id:
            return {"status": "error", "detail": "请先配置 Telegram Bot Token 和 Chat ID"}
        try:
            from augur.bots.telegram_bot import send_message
            send_message(token, chat_id, "Augur 测试通知: 通道配置成功!")
            return {"status": "ok", "detail": "Telegram 测试消息已发送"}
        except ImportError:
            try:
                import json as _json
                import urllib.request
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = _json.dumps({"chat_id": chat_id, "text": "Augur 测试通知: 通道配置成功!"}).encode()
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "ok", "detail": "Telegram 测试消息已发送"}
            except Exception as e:
                return {"status": "error", "detail": f"发送失败: {e}"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    elif channel == "slack":
        webhook = notifications.get("slack_webhook", "")
        if not webhook:
            return {"status": "error", "detail": "请先配置 Slack Webhook URL"}
        try:
            import json as _json
            import urllib.request
            data = _json.dumps({"text": "Augur 测试通知: Slack 通道配置成功!"}).encode()
            req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "Slack 测试消息已发送"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    elif channel == "lark":
        webhook = notifications.get("lark_webhook", "")
        if not webhook:
            return {"status": "error", "detail": "请先配置飞书 Webhook URL"}
        try:
            import json as _json
            import urllib.request
            data = _json.dumps({"msg_type": "text", "content": {"text": "Augur 测试通知: 飞书通道配置成功!"}}).encode()
            req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"status": "ok", "detail": "飞书测试消息已发送"}
        except Exception as e:
            return {"status": "error", "detail": f"发送失败: {e}"}
    elif channel == "wechat":
        return {"status": "error", "detail": "微信通知需要企业微信配置，请参考文档"}

    return {"status": "error", "detail": "测试失败"}


@router.post("/api/notifications/config", summary="保存通知配置")
async def api_notifications_config_save(request: Request):
    """Save notification configuration to config/notifications.yaml."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_file = _CONFIG_DIR / "notifications.yaml"
    config_file.write_text(yaml.dump(body, allow_unicode=True), encoding="utf-8")
    set_config("notifications", body)
    save_config()
    return {"status": "ok", "message": "通知配置已保存"}


@router.get("/api/notifications/config", summary="获取通知配置")
async def api_notifications_config_get():
    """Read notification configuration."""
    config_file = _CONFIG_DIR / "notifications.yaml"
    if config_file.exists():
        try:
            data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
            return {"status": "ok", "config": data}
        except Exception:
            pass
    config = get_config()
    return {"status": "ok", "config": config.get("notifications", {})}


# ---- Cron ----

@router.get("/api/cron/config", summary="获取定时监控配置")
async def api_get_cron_config():
    """返回当前 cron 配置 (schedule + notifications sections from watchlist.yaml)"""
    from augur.cron import load_watchlist
    config = load_watchlist()
    return {
        "status": "ok",
        "schedule": config.get("schedule", {}),
        "notifications": config.get("notifications", {}),
    }


@router.put("/api/cron/config", summary="更新定时监控配置")
async def api_put_cron_config(body: CronConfigBody):
    """更新 schedule/notifications sections in watchlist.yaml"""
    from augur.cron import load_watchlist, save_watchlist
    config = load_watchlist()
    if body.schedule is not None:
        config["schedule"] = body.schedule
    if body.notifications is not None:
        config["notifications"] = body.notifications
    save_watchlist(config)
    return {
        "status": "ok",
        "message": "定时监控配置已更新",
        "schedule": config.get("schedule", {}),
        "notifications": config.get("notifications", {}),
    }


@router.post("/api/cron/run-now", summary="立即执行一次监控分析")
async def api_cron_run_now():
    """触发一次 watchlist 分析并返回结果"""
    from augur.cron import run_watchlist_analysis
    try:
        results = run_watchlist_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析执行失败: {e}")
    serialized = []
    for r in results:
        consensus = r.get("consensus")
        item = {"ticker": r.get("ticker", ""), "message": r.get("message", "")}
        if consensus is not None:
            item["signal"] = consensus.signal.value if hasattr(consensus, "signal") else ""
            item["score"] = round(consensus.score, 1) if hasattr(consensus, "score") else 0
            item["confidence"] = round(consensus.confidence, 2) if hasattr(consensus, "confidence") else 0
        serialized.append(item)
    return {"status": "ok", "count": len(serialized), "results": serialized}
