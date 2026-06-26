"""Workspace API routes — /api/workspace* and /ws/workspace.

Extracted from dashboard/app.py (P1-9 router split, R1).
Mounts via: app.include_router(workspace_router)
"""

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from augur.auth import authenticate_websocket
from augur.workspace import (
    WORKSPACE_EXPORT_KEY,
    create_profile,
    delete_profile,
    export_workspace_bundle,
    get_profile,
    get_workspace,
    get_workspace_state,
    import_workspace_bundle,
    list_presets,
    list_profiles,
    normalize_profile_name,
    save_profile,
    save_workspace,
    set_active_profile,
)

router = APIRouter()


# ---- Request models ----

class WorkspaceBody(BaseModel):
    """Terminal workspace customization."""
    layout_preset: Optional[str] = "analyst"
    default_page: Optional[str] = None
    default_ticker: Optional[str] = None
    sidebar_collapsed: Optional[bool] = None
    hidden_nav: Optional[List[str]] = None
    show_ticker_tape: Optional[bool] = None
    committee_preset: Optional[str] = None
    enabled_personas: Optional[List[str]] = None


class WorkspaceProfileBody(BaseModel):
    """Create a named workspace profile."""
    name: str
    copy_from: Optional[str] = None


class WorkspaceActiveBody(BaseModel):
    """Switch active workspace profile."""
    profile: str


# ---- WebSocket broadcast state ----

_ws_workspace_clients: Set[WebSocket] = set()


async def _broadcast_workspace_change(state: dict) -> None:
    """Push workspace state to all connected /ws/workspace subscribers."""
    disconnected: Set[WebSocket] = set()
    for ws in list(_ws_workspace_clients):
        try:
            await ws.send_json({"type": "workspace_update", "workspace": state})
        except Exception:
            disconnected.add(ws)
    _ws_workspace_clients -= disconnected


# ---- REST endpoints ----

@router.get("/api/workspace", summary="获取终端工作区配置")
async def api_get_workspace(request: Request):
    """Return Bloomberg-style terminal workspace preferences."""
    state = get_workspace_state()
    data = {
        "status": "ok",
        "workspace": get_workspace(),
        "active_profile": state["active_profile"],
        "profiles": list_profiles(),
    }
    data_json = json.dumps(data, sort_keys=True, default=str)
    etag = hashlib.md5(data_json.encode()).hexdigest()
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match.strip('"') == etag:
        return JSONResponse(status_code=304, content=None, headers={"ETag": f'"{etag}"'})
    return JSONResponse(content=data, headers={"ETag": f'"{etag}"'})


@router.get("/api/workspace/presets", summary="列出工作区布局预设")
async def api_workspace_presets():
    """Return available layout presets (analyst, trader, committee, minimal)."""
    return {"status": "ok", "presets": list_presets()}


@router.get("/api/workspace/profiles", summary="列出命名工作区配置")
async def api_list_workspace_profiles():
    """Return all named workspace profiles."""
    return {"status": "ok", "profiles": list_profiles(), "active_profile": get_workspace_state()["active_profile"]}


@router.get("/api/workspace/profiles/{profile_name}", summary="获取命名工作区配置详情")
async def api_get_workspace_profile(profile_name: str):
    """Return full workspace settings for a named profile without switching active."""
    slug = normalize_profile_name(profile_name)
    if not slug:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = get_profile(slug)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")
    return {
        "status": "ok",
        "profile": slug,
        "active": slug == get_workspace_state()["active_profile"],
        "workspace": profile,
    }


@router.put("/api/workspace/profiles/{profile_name}", summary="保存命名工作区配置")
async def api_save_workspace_profile(profile_name: str, body: WorkspaceBody):
    """Save settings for a named profile without switching active."""
    slug = normalize_profile_name(profile_name)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid profile name")
    try:
        profile = save_profile(slug, body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "status": "ok",
        "profile": slug,
        "active": slug == get_workspace_state()["active_profile"],
        "workspace": profile,
    }


@router.post("/api/workspace/profiles", summary="创建命名工作区配置")
async def api_create_workspace_profile(body: WorkspaceProfileBody):
    """Create a new named profile (e.g. day-trading, research)."""
    try:
        profile = create_profile(body.name, copy_from=body.copy_from)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "profile": body.name.strip().lower(), "workspace": profile}


@router.delete("/api/workspace/profiles/{profile_name}", summary="删除命名工作区配置")
async def api_delete_workspace_profile(profile_name: str):
    """Delete a named profile."""
    try:
        delete_profile(profile_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "deleted": profile_name.strip().lower()}


@router.put("/api/workspace/active", summary="切换活动工作区配置")
async def api_set_active_workspace_profile(body: WorkspaceActiveBody):
    """Switch the active workspace profile."""
    try:
        workspace = set_active_profile(body.profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    asyncio.create_task(_broadcast_workspace_change(workspace))
    return {"status": "ok", "active_profile": body.profile.strip().lower(), "workspace": workspace}


@router.put("/api/workspace", summary="保存终端工作区配置")
async def api_put_workspace(body: WorkspaceBody):
    """Save workspace layout preferences to ~/.augur/workspace.yaml."""
    data = body.model_dump(exclude_none=True)
    saved = save_workspace(data)
    asyncio.create_task(_broadcast_workspace_change(saved))
    return {"status": "ok", "workspace": saved, "active_profile": get_workspace_state()["active_profile"]}


@router.get("/api/workspace/export", summary="导出工作区配置")
async def api_workspace_export():
    """Export all workspace profiles for backup (also embedded in /api/config/export)."""
    return {"status": "ok", WORKSPACE_EXPORT_KEY: export_workspace_bundle()}


@router.post("/api/workspace/import", summary="导入工作区配置")
async def api_workspace_import(request: Request):
    """Import workspace profiles from export payload or full config JSON."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    payload = body.get(WORKSPACE_EXPORT_KEY, body)
    merge = body.get("merge", True)
    try:
        imported = import_workspace_bundle(payload, merge=bool(merge))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", WORKSPACE_EXPORT_KEY: imported}


# ---- WebSocket endpoint ----

@router.websocket("/ws/workspace")
async def ws_workspace(websocket: WebSocket):
    """Stream workspace state changes to dashboard clients in real time.

    Clients receive the current workspace immediately on connect, then receive
    ``{"type": "workspace_update", "workspace": {...}}`` push messages whenever
    any workspace-write endpoint (PUT /api/workspace, PUT /api/workspace/active,
    etc.) commits a change.
    """
    if not authenticate_websocket(websocket):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    await websocket.accept()
    _ws_workspace_clients.add(websocket)
    try:
        current = get_workspace()
        await websocket.send_json({"type": "workspace_state", "workspace": current})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _ws_workspace_clients.discard(websocket)
