# -*- coding: utf-8 -*-
"""Rolling IC weight loader."""

from typing import Dict

from augur.consensus.paths import load_feedback_json


def load_rolling_ic_weights() -> Dict[str, float]:
    """Load rolling IC weights from feedback file if present."""
    try:
        data = load_feedback_json("rolling_ic.json")
        weights = data.get("weights", data)
        if isinstance(weights, dict):
            return {k: float(v) for k, v in weights.items() if isinstance(v, (int, float))}
    except Exception:
        pass
    return {}
