"""Sentiment and AI Chat routes."""

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from dashboard.deps import _i18n_context, templates

logger = logging.getLogger(__name__)

router = APIRouter()

# ============ Sentiment ============

@router.get("/api/sentiment/{ticker}")
async def api_sentiment(ticker: str):
    if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    from augur.sentiment import SentimentAnalyzer
    try:
        result = SentimentAnalyzer().get_sentiment(ticker)
    except Exception as e:
        logger.warning("sentiment fetch failed for %s: %s", ticker.upper(), e)
        return {
            "ticker": ticker.upper(),
            "overall_score": 0.0,
            "sources": {"stocktwits_score": 0.0, "reddit_score": 0.0, "x_score": 0.0},
            "volume": 0,
            "trending": False,
            "data_source": "degraded",
            "error": str(e),
        }
    return {
        "ticker": result.ticker,
        "overall_score": result.overall_score,
        "sources": result.sources,
        "volume": result.volume,
        "trending": result.trending,
        "data_source": result.data_source,
    }


# ============ AI Chat ============

_chat_engine = None


def _get_chat_engine():
    global _chat_engine
    if _chat_engine is None:
        from augur.chat import ChatEngine
        _chat_engine = ChatEngine()
    return _chat_engine


class ChatBody(BaseModel):
    message: str
    agent_id: Optional[str] = None


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    engine = _get_chat_engine()
    try:
        from augur.llm_client import is_llm_available
        llm_enabled = is_llm_available()
    except Exception:
        llm_enabled = False
    ctx = {"title": "AI Chat", "agents": engine.get_available_agents(), "llm_enabled": llm_enabled}
    ctx.update(_i18n_context(request=request))
    return templates.TemplateResponse(request=request, name="chat.html", context=ctx)


@router.post("/api/chat")
async def api_chat(body: ChatBody):
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    if len(body.message) > 2000:
        raise HTTPException(status_code=400, detail="消息过长（最多2000字符）")
    if body.agent_id and not re.match(r'^[a-z_]{1,50}$', body.agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    try:
        return _get_chat_engine().get_response(body.message, body.agent_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Agent '{body.agent_id}' not found: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid chat request: {e}")
    except Exception as e:
        logger.warning("chat engine failed: %s", e)
        raise HTTPException(status_code=500, detail=f"聊天服务暂时不可用: {e}")
