# -*- coding: utf-8 -*-
"""Regime-based agent routing weights."""

from typing import Dict, Optional

from augur.consensus.regime_weights import _REGIME_ADJUSTMENTS


class RegimeRouter:
    """Return normalized agent weights for a given regime."""

    def get_weights(self, regime: Optional[str] = None, features: Optional[dict] = None) -> Dict[str, float]:
        regime = regime or (features or {}).get("regime", "SIDEWAYS")
        adj = _REGIME_ADJUSTMENTS.get(regime, {})
        if not adj:
            return {}
        total = sum(adj.values())
        if total <= 0:
            return adj
        return {k: v / total for k, v in adj.items()}
