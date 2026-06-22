# -*- coding: utf-8 -*-
"""Feedback file path helpers for consensus tuning data."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# repo root: src/augur/consensus/paths.py -> parents[3]
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FEEDBACK_DIR = _REPO_ROOT / "feedback"


def feedback_path(name: str) -> Path:
    """Return path to a file under repo-root ``feedback/``."""
    return FEEDBACK_DIR / name


def load_feedback_json(name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load JSON from ``feedback/{name}``; return *default* (or {}) if missing/invalid."""
    default = default if default is not None else {}
    path = feedback_path(name)
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        logger.warning("Feedback file %s is not a JSON object; ignoring", path)
    except Exception as exc:
        logger.warning("Failed to load feedback file %s: %s", path, exc)
    return dict(default)
