# -*- coding: utf-8 -*-
"""Rolling IC weight loader."""

from pathlib import Path
from typing import Dict


def load_rolling_ic_weights() -> Dict[str, float]:
    """Load rolling IC weights from feedback file if present."""
    try:
        import json
        ic_file = Path(__file__).parent.parent.parent / "feedback" / "rolling_ic.json"
        if not ic_file.exists():
            ic_file = Path.home() / ".augur" / "rolling_ic.json"
        if ic_file.exists():
            data = json.loads(ic_file.read_text(encoding="utf-8"))
            weights = data.get("weights", data)
            if isinstance(weights, dict):
                return {k: float(v) for k, v in weights.items()}
    except Exception:
        pass
    return {}
