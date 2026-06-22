# -*- coding: utf-8 -*-
"""Load per-agent optimized thresholds from feedback/agent_hyperparams.json."""

from typing import Any, Dict, Optional

from augur.consensus.paths import load_feedback_json

_CACHE: Optional[Dict[str, Any]] = None


def _load_all() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        data = load_feedback_json("agent_hyperparams.json")
        agents = data.get("agents") if isinstance(data.get("agents"), dict) else data
        _CACHE = agents if isinstance(agents, dict) else {}
    return _CACHE


def load_optimized_thresholds(agent_id: str) -> Dict[str, Any]:
    """Return threshold overrides for *agent_id*, or {} if none configured."""
    if not agent_id:
        return {}
    entry = _load_all().get(agent_id)
    if not isinstance(entry, dict):
        return {}
    return {k: v for k, v in entry.items() if isinstance(k, str)}
