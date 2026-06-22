# -*- coding: utf-8 -*-
"""Feedback file path helpers for consensus tuning data."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# repo root: src/augur/consensus/paths.py -> parents[3]
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FEEDBACK_DIR = _REPO_ROOT / "feedback"
USER_FEEDBACK_DIR = Path.home() / ".augur" / "feedback"


def feedback_path(name: str) -> Path:
    """Return path to a feedback file.

    User overrides in ``~/.augur/feedback/`` take precedence over repo
    ``feedback/`` so PyPI installs can tune weights without touching the package.
    """
    user_path = USER_FEEDBACK_DIR / name
    if user_path.exists():
        return user_path
    return FEEDBACK_DIR / name


def load_feedback_json(name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load JSON from feedback dir; return *default* (or {}) if missing/invalid."""
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


def resolve_feedback_dirs() -> tuple:
    """Return (user_dir, repo_dir) for tests and diagnostics."""
    override = os.environ.get("AUGUR_FEEDBACK_DIR")
    if override:
        return Path(override), FEEDBACK_DIR
    return USER_FEEDBACK_DIR, FEEDBACK_DIR
