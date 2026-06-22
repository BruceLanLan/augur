# -*- coding: utf-8 -*-
"""
augur.workspace - Terminal workspace customization (Bloomberg-like layout presets).

Persisted to ~/.augur/workspace.yaml
"""

import copy
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_workspace: Optional[Dict[str, Any]] = None

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
    },
    "trader": {
        "default_page": "/stocks",
        "hidden_nav": ["backtest", "optimizer", "performance", "hermes-setup"],
        "show_ticker_tape": True,
        "committee_preset": "value",
    },
    "committee": {
        "default_page": "/committee",
        "hidden_nav": ["scanner", "backtest", "optimizer"],
        "show_ticker_tape": False,
        "committee_preset": "all",
    },
    "minimal": {
        "default_page": "/stocks",
        "hidden_nav": [
            "backtest", "optimizer", "performance", "debate", "compare",
            "hermes-setup", "create-persona",
        ],
        "show_ticker_tape": True,
        "committee_preset": "value",
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


def get_workspace() -> Dict[str, Any]:
    """Load workspace config (thread-safe)."""
    global _workspace
    with _lock:
        if _workspace is not None:
            return copy.deepcopy(_workspace)
        stored = _load_yaml(_workspace_path())
        preset = stored.get("layout_preset", "analyst")
        if preset in LAYOUT_PRESETS and preset != "custom":
            _workspace = merge_preset_with_custom(preset, stored)
        else:
            _workspace = copy.deepcopy(DEFAULT_WORKSPACE)
            _workspace.update({k: v for k, v in stored.items() if k in DEFAULT_WORKSPACE})
            _workspace["layout_preset"] = stored.get("layout_preset", "custom")
        return copy.deepcopy(_workspace)


def save_workspace(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and persist workspace config."""
    global _workspace
    cleaned: Dict[str, Any] = {}
    preset = data.get("layout_preset", "analyst")
    if preset not in VALID_PRESETS:
        preset = "custom"
    cleaned["layout_preset"] = preset

    if preset in LAYOUT_PRESETS:
        base = apply_preset(preset)
    else:
        base = copy.deepcopy(DEFAULT_WORKSPACE)

    page = data.get("default_page", base.get("default_page", "/"))
    cleaned["default_page"] = page if page in VALID_PAGES else "/"

    cleaned["default_ticker"] = str(data.get("default_ticker", ""))[:20]
    cleaned["sidebar_collapsed"] = bool(data.get("sidebar_collapsed", False))
    cleaned["show_ticker_tape"] = bool(data.get("show_ticker_tape", base.get("show_ticker_tape", True)))
    cleaned["committee_preset"] = str(data.get("committee_preset", base.get("committee_preset", "all")))[:32]

    hidden = data.get("hidden_nav", base.get("hidden_nav", []))
    if not isinstance(hidden, list):
        hidden = []
    cleaned["hidden_nav"] = [str(x)[:32] for x in hidden if isinstance(x, str)]

    personas = data.get("enabled_personas", [])
    if not isinstance(personas, list):
        personas = []
    cleaned["enabled_personas"] = [str(x)[:64] for x in personas if isinstance(x, str)]

    with _lock:
        _workspace = cleaned
        _save_yaml(_workspace_path(), cleaned)
    return copy.deepcopy(cleaned)


def get_enabled_personas() -> List[str]:
    """Return workspace enabled_personas; empty list means use all agents."""
    return get_workspace().get("enabled_personas", []) or []


def list_presets() -> Dict[str, Dict[str, Any]]:
    """Return available layout presets for the UI."""
    return {
        name: {
            "name": name,
            "default_page": cfg["default_page"],
            "hidden_nav": cfg["hidden_nav"],
            "show_ticker_tape": cfg["show_ticker_tape"],
            "committee_preset": cfg["committee_preset"],
        }
        for name, cfg in LAYOUT_PRESETS.items()
    }
