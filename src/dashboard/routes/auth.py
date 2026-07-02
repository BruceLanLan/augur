"""Auth pages and API routes — /login, /register, /api/auth/*.

Extracted from dashboard/app.py (router split R4).
Mounts via: app.include_router(auth_router)
"""

import logging
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from augur.auth import (
    auth_required,
    authenticate_request,
    check_auth_rate_limit,
    extract_bearer_token,
    verify_jwt,
)
from augur.errors import api_error_response
from dashboard.deps import templates

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Request models ----

class AuthRegisterBody(BaseModel):
    username: str
    password: str


class AuthLoginBody(BaseModel):
    username: str
    password: str


# ---- HTML pages ----

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login"})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"title": "Register"})


# ---- Auth API ----

@router.get("/api/auth/config", summary="获取认证配置")
async def api_auth_config():
    """Return whether auth is enabled and which credential types are accepted."""
    from augur.auth import get_auth_config
    return {"status": "ok", **get_auth_config()}


@router.get("/api/auth/verify", summary="验证API Token")
async def api_auth_verify(request: Request):
    """验证 API Token 或 JWT 有效性。未启用认证时返回 open 模式。"""
    if not auth_required():
        return {"status": "ok", "authenticated": True, "mode": "open"}
    ok, mode = authenticate_request(request)
    if not ok:
        return JSONResponse(
            status_code=401,
            content=api_error_response(
                detail="Authentication required",
                code="AUTH_REQUIRED",
                suggestion="Provide a valid Bearer token (Authorization: Bearer <token>) and retry.",
                path=request.url.path,
            ),
        )
    return {"status": "ok", "authenticated": True, "mode": mode}


@router.get("/api/auth/me", summary="获取当前登录用户")
async def api_auth_me(request: Request):
    """Return the authenticated multi-user JWT identity."""
    from augur.users import is_multi_user_enabled
    if not is_multi_user_enabled():
        raise HTTPException(status_code=403, detail="Set AUGUR_MULTI_USER=1 to enable multi-user mode.")
    token = extract_bearer_token(request.headers.get("authorization", ""))
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"status": "ok", "user_id": payload["user_id"], "username": payload["username"]}


@router.post("/api/auth/register")
async def api_auth_register(body: AuthRegisterBody, request: Request):
    from augur.users import UserManager, is_multi_user_enabled
    if not is_multi_user_enabled():
        raise HTTPException(status_code=403, detail="Set AUGUR_MULTI_USER=1 to enable multi-user mode.")
    client_ip = request.client.host if request.client else "unknown"
    if not check_auth_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many auth attempts. Try again later.")
    if not body.username or not 3 <= len(body.username) <= 32 or not re.match(r'^[a-zA-Z0-9_]+$', body.username):
        raise HTTPException(status_code=400, detail="Username: 3-32 chars, letters/numbers/underscore only.")
    if not body.password or not 6 <= len(body.password) <= 128:
        raise HTTPException(status_code=400, detail="Password must be 6-128 characters.")
    manager = UserManager()
    user = manager.create_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=400, detail="Username already exists or invalid.")
    return {"status": "ok", "username": user["username"], "id": user["id"]}


@router.post("/api/auth/login")
async def api_auth_login(body: AuthLoginBody, request: Request):
    from augur.users import UserManager, is_multi_user_enabled
    if not is_multi_user_enabled():
        raise HTTPException(status_code=403, detail="Set AUGUR_MULTI_USER=1 to enable multi-user mode.")
    client_ip = request.client.host if request.client else "unknown"
    if not check_auth_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many auth attempts. Try again later.")
    if not body.username or len(body.username) > 32 or not body.password or len(body.password) > 128:
        raise HTTPException(status_code=400, detail="Invalid credentials.")
    token = UserManager().authenticate(body.username, body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {"status": "ok", "token": token, "username": body.username}


@router.get("/api/schema/persona", summary="获取Persona YAML结构")
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
