# -*- coding: utf-8 -*-
"""
augur.workspace - Terminal workspace customization (Bloomberg-like layout presets).

Persisted to ~/.augur/workspace.yaml with support for multiple named profiles.
"""

import copy
import logging
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_workspace_state: Optional[Dict[str, Any]] = None
_workspace: Optional[Dict[str, Any]] = None  # backward-compatible cache alias for tests

DEFAULT_PROFILE = "default"
PROFILE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")

VALID_PRESETS = ("analyst", "trader", "committee", "minimal", "custom")
VALID_PAGES = (
    "/", "/stocks", "/signals", "/scanner", "/watchlist", "/portfolio",
    "/backtest", "/personas", "/create-persona", "/optimizer", "/compare",
    "/debate", "/committee", "/hermes-setup", "/history", "/performance", "/settings",
)

LAYOUT_PRESETS: Dict[str, Dict[str, Any]] = {
    "analyst": {
        "default_page": "/",
        "hidden_nav": [],
        "show_ticker_tape": True,
        "committee_preset": "all",
        "workflow_steps": "fetch,analyze,consensus",
    },
    "trader": {
        "default_page": "/stocks",
        "hidden_nav": ["backtest", "optimizer", "performance", "hermes-setup"],
        "show_ticker_tape": True,
        "committee_preset": "value",
        "workflow_steps": "fetch,consensus",
    },
    "committee": {
        "default_page": "/committee",
        "hidden_nav": ["scanner", "backtest", "optimizer"],
        "show_ticker_tape": False,
        "committee_preset": "all",
        "workflow_steps": "fetch,analyze,consensus,committee",
    },
    "minimal": {
        "default_page": "/stocks",
        "hidden_nav": [
            "backtest", "optimizer", "performance", "debate", "compare",
            "hermes-setup", "create-persona",
        ],
        "show_ticker_tape": True,
        "committee_preset": "value",
        "workflow_steps": "fetch,consensus",
    },
}

DEFAULT_WORKSPACE: Dict[str, Any] = {
    "layout_preset": "analyst",
    "default_page": "/",
    "default_ticker": "",
    "sidebar_collapsed": False,
    "hidden_nav": [],
    "show_ticker_tape": True,
    "committee_preset": "all",
    "enabled_personas": [],
}

WORKSPACE_EXPORT_KEY = "workspace"


def _workspace_path() -> Path:
    data_dir = Path.home() / ".augur"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "workspace.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Failed to load workspace from %s: %s", path, e)
        return {}


def _save_yaml(path: Path, data: Dict[str, Any]) -> None:
    import yaml
    path.write_text(yaml.safe_dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")


def normalize_profile_name(name: str) -> Optional[str]:
    """Return a validated profile slug or None."""
    slug = str(name or "").strip().lower()
    if not slug or not PROFILE_NAME_RE.match(slug):
        return None
    return slug


def merge_preset_with_custom(preset: str, custom: Dict[str, Any]) -> Dict[str, Any]:
    """Merge a layout preset with user overrides."""
    base = copy.deepcopy(DEFAULT_WORKSPACE)
    if preset in LAYOUT_PRESETS:
        base.update(LAYOUT_PRESETS[preset])
    base["layout_preset"] = preset if preset in VALID_PRESETS else "custom"
    for key, value in custom.items():
        if key in DEFAULT_WORKSPACE and value is not None:
            base[key] = value
    return base


def apply_preset(name: str) -> Dict[str, Any]:
    """Return workspace dict for a named preset."""
    if name not in LAYOUT_PRESETS:
        name = "analyst"
    ws = merge_preset_with_custom(name, {})
    ws["layout_preset"] = name
    return ws


def _normalize_profile_settings(stored: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize a single profile's settings."""
    preset = stored.get("layout_preset", "analyst")
    if preset not in VALID_PRESETS:
        preset = "custom"

    if preset in LAYOUT_PRESETS:
        base = apply_preset(preset)
    else:
        base = copy.deepcopy(DEFAULT_WORKSPACE)
        base.update({k: v for k, v in stored.items() if k in DEFAULT_WORKSPACE})
        base["layout_preset"] = preset

    page = stored.get("default_page")
    if page is None:
        page = base.get("default_page", "/")
    base["default_page"] = page if page in VALID_PAGES else "/"
    ticker = stored.get("default_ticker")
    if ticker is not None:
        base["default_ticker"] = str(ticker)[:20]
    if "sidebar_collapsed" in stored and stored["sidebar_collapsed"] is not None:
        base["sidebar_collapsed"] = bool(stored["sidebar_collapsed"])
    if "show_ticker_tape" in stored and stored["show_ticker_tape"] is not None:
        base["show_ticker_tape"] = bool(stored["show_ticker_tape"])
    if stored.get("committee_preset") is not None:
        base["committee_preset"] = str(stored["committee_preset"])[:32]

    if "hidden_nav" in stored and stored["hidden_nav"] is not None:
        hidden = stored["hidden_nav"]
        if isinstance(hidden, list):
            base["hidden_nav"] = [str(x)[:32] for x in hidden if isinstance(x, str)]

    if "enabled_personas" in stored and stored["enabled_personas"] is not None:
        personas = stored["enabled_personas"]
        if isinstance(personas, list):
            base["enabled_personas"] = [str(x)[:64] for x in personas if isinstance(x, str)]
    return base


def _migrate_flat_to_profiles(stored: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy flat workspace.yaml to multi-profile format."""
    if "profiles" in stored and isinstance(stored.get("profiles"), dict):
        return stored
    profile_data = {k: v for k, v in stored.items() if k in DEFAULT_WORKSPACE or k == "layout_preset"}
    if not profile_data:
        profile_data = copy.deepcopy(DEFAULT_WORKSPACE)
    return {
        "active_profile": DEFAULT_PROFILE,
        "profiles": {DEFAULT_PROFILE: profile_data},
    }


def _load_state() -> Dict[str, Any]:
    stored = _migrate_flat_to_profiles(_load_yaml(_workspace_path()))
    profiles_raw = stored.get("profiles") or {}
    if not isinstance(profiles_raw, dict):
        profiles_raw = {}

    profiles: Dict[str, Dict[str, Any]] = {}
    for name, cfg in profiles_raw.items():
        slug = normalize_profile_name(name)
        if slug and isinstance(cfg, dict):
            profiles[slug] = _normalize_profile_settings(cfg)

    if not profiles:
        profiles[DEFAULT_PROFILE] = copy.deepcopy(DEFAULT_WORKSPACE)

    active = normalize_profile_name(stored.get("active_profile", DEFAULT_PROFILE)) or DEFAULT_PROFILE
    if active not in profiles:
        active = next(iter(profiles))

    return {"active_profile": active, "profiles": profiles}


def _persist_state(state: Dict[str, Any]) -> None:
    payload = {
        "active_profile": state["active_profile"],
        "profiles": state["profiles"],
    }
    _save_yaml(_workspace_path(), payload)


def _ensure_state_loaded() -> Dict[str, Any]:
    global _workspace_state, _workspace
    if _workspace is None:
        _workspace_state = None
    if _workspace_state is None:
        _workspace_state = _load_state()
    _workspace = _workspace_state
    return _workspace_state


def get_workspace_state() -> Dict[str, Any]:
    """Return full workspace state including all profiles."""
    with _lock:
        return copy.deepcopy(_ensure_state_loaded())


def get_workspace() -> Dict[str, Any]:
    """Load active profile workspace config (thread-safe)."""
    state = get_workspace_state()
    return copy.deepcopy(state["profiles"][state["active_profile"]])


def save_workspace(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and persist the active profile's workspace config."""
    global _workspace_state, _workspace
    cleaned = _normalize_profile_settings(data)
    with _lock:
        state = _ensure_state_loaded()
        active = state["active_profile"]
        state["profiles"][active] = cleaned
        _workspace_state = state
        _workspace = state
        _persist_state(state)
    return copy.deepcopy(cleaned)


def list_profiles() -> List[Dict[str, Any]]:
    """Return named profiles with summary metadata."""
    state = get_workspace_state()
    active = state["active_profile"]
    result: List[Dict[str, Any]] = []
    for name in sorted(state["profiles"]):
        cfg = state["profiles"][name]
        result.append({
            "name": name,
            "active": name == active,
            "layout_preset": cfg.get("layout_preset", "analyst"),
            "default_page": cfg.get("default_page", "/"),
            "default_ticker": cfg.get("default_ticker", ""),
        })
    return result


def get_profile(name: str) -> Optional[Dict[str, Any]]:
    slug = normalize_profile_name(name)
    if not slug:
        return None
    state = get_workspace_state()
    cfg = state["profiles"].get(slug)
    return copy.deepcopy(cfg) if cfg else None


def create_profile(name: str, copy_from: Optional[str] = None) -> Dict[str, Any]:
    """Create a new named profile, optionally copying from another."""
    global _workspace_state, _workspace
    slug = normalize_profile_name(name)
    if not slug:
        raise ValueError("Invalid profile name")

    with _lock:
        state = _ensure_state_loaded()
        if slug in state["profiles"]:
            raise ValueError(f"Profile '{slug}' already exists")

        if copy_from:
            src = normalize_profile_name(copy_from)
            if src and src in state["profiles"]:
                cfg = copy.deepcopy(state["profiles"][src])
            else:
                cfg = copy.deepcopy(DEFAULT_WORKSPACE)
        else:
            cfg = copy.deepcopy(DEFAULT_WORKSPACE)

        state["profiles"][slug] = _normalize_profile_settings(cfg)
        _workspace_state = state
        _workspace = state
        _persist_state(state)
    return copy.deepcopy(state["profiles"][slug])


def delete_profile(name: str) -> None:
    """Delete a profile (cannot delete the last or active profile)."""
    global _workspace_state, _workspace
    slug = normalize_profile_name(name)
    if not slug:
        raise ValueError("Invalid profile name")

    with _lock:
        state = _ensure_state_loaded()
        if slug not in state["profiles"]:
            raise ValueError(f"Profile '{slug}' not found")
        if len(state["profiles"]) <= 1:
            raise ValueError("Cannot delete the last profile")
        if state["active_profile"] == slug:
            raise ValueError("Cannot delete the active profile; switch first")

        del state["profiles"][slug]
        _workspace_state = state
        _workspace = state
        _persist_state(state)


def set_active_profile(name: str) -> Dict[str, Any]:
    """Switch the active profile."""
    global _workspace_state, _workspace
    slug = normalize_profile_name(name)
    if not slug:
        raise ValueError("Invalid profile name")

    with _lock:
        state = _ensure_state_loaded()
        if slug not in state["profiles"]:
            raise ValueError(f"Profile '{slug}' not found")
        state["active_profile"] = slug
        _workspace_state = state
        _workspace = state
        _persist_state(state)
    return copy.deepcopy(state["profiles"][slug])


def save_profile(name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Save settings for a specific profile without switching active."""
    global _workspace_state, _workspace
    slug = normalize_profile_name(name)
    if not slug:
        raise ValueError("Invalid profile name")
    cleaned = _normalize_profile_settings(data)

    with _lock:
        state = _ensure_state_loaded()
        if slug not in state["profiles"]:
            raise ValueError(f"Profile '{slug}' not found")
        state["profiles"][slug] = cleaned
        _workspace_state = state
        _workspace = state
        _persist_state(state)
    return copy.deepcopy(cleaned)


def resolve_landing_url(workspace: Dict[str, Any], path: str = "/") -> Optional[str]:
    """Return redirect URL for landing page, or None to stay."""
    if path != "/":
        return None
    ticker = str(workspace.get("default_ticker", "")).strip()
    if ticker:
        return f"/stocks?ticker={ticker.upper()}"
    default_page = workspace.get("default_page", "/")
    if default_page and default_page != "/":
        return default_page
    return None


def export_workspace_bundle() -> Dict[str, Any]:
    """Export all profiles for config backup (/api/config/export integration)."""
    state = get_workspace_state()
    return {
        "active_profile": state["active_profile"],
        "profiles": copy.deepcopy(state["profiles"]),
    }


def import_workspace_bundle(data: Dict[str, Any], *, merge: bool = True) -> Dict[str, Any]:
    """Import profiles from a config export payload."""
    global _workspace_state, _workspace
    if not isinstance(data, dict):
        raise ValueError("Invalid workspace import payload")

    incoming_profiles = data.get("profiles")
    if not isinstance(incoming_profiles, dict) or not incoming_profiles:
        raise ValueError("Import payload must include a non-empty profiles map")

    normalized: Dict[str, Dict[str, Any]] = {}
    for name, cfg in incoming_profiles.items():
        slug = normalize_profile_name(name)
        if slug and isinstance(cfg, dict):
            normalized[slug] = _normalize_profile_settings(cfg)

    if not normalized:
        raise ValueError("No valid profiles in import payload")

    active = normalize_profile_name(data.get("active_profile", DEFAULT_PROFILE)) or DEFAULT_PROFILE
    if active not in normalized:
        active = next(iter(normalized))

    with _lock:
        if merge:
            state = copy.deepcopy(_ensure_state_loaded())
        else:
            state = {"active_profile": active, "profiles": {}}

        state["profiles"].update(normalized)
        state["active_profile"] = active if active in state["profiles"] else state["active_profile"]
        _workspace_state = state
        _workspace = state
        _persist_state(state)

    return export_workspace_bundle()


def get_enabled_personas() -> List[str]:
    """Return active profile enabled_personas; empty list means use all agents."""
    return get_workspace().get("enabled_personas", []) or []


def get_default_workflow_steps() -> str:
    """Return augur_workflow's default steps for the active profile's layout preset."""
    preset = get_workspace().get("layout_preset", "analyst")
    return LAYOUT_PRESETS.get(preset, {}).get("workflow_steps") or "fetch,analyze,consensus"


def list_presets() -> Dict[str, Dict[str, Any]]:
    """Return available layout presets for the UI."""
    return {
        name: {
            "name": name,
            "default_page": cfg["default_page"],
            "hidden_nav": cfg["hidden_nav"],
            "show_ticker_tape": cfg["show_ticker_tape"],
            "committee_preset": cfg["committee_preset"],
            "workflow_steps": cfg["workflow_steps"],
        }
        for name, cfg in LAYOUT_PRESETS.items()
    }


def reset_workspace_cache() -> None:
    """Clear in-memory cache (for tests)."""
    global _workspace_state, _workspace
    with _lock:
        _workspace_state = None
        _workspace = None
