# -*- coding: utf-8 -*-
"""Macro regime detection and weight adjustment."""

from typing import Dict, Optional

from augur.consensus.macro_features import fetch_macro_features

_REGIME_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "BULL_LOW_VOL": {
        "lynch": 1.22, "cathie_wood": 1.18, "aschenbrenner": 1.12, "thiel": 1.08,
        "marks": 0.88, "graham": 0.9,
    },
    "BULL_HIGH_VOL": {
        "marks": 1.22, "dalio": 1.18, "graham": 1.12, "munger": 1.08,
        "cathie_wood": 0.85, "aschenbrenner": 0.88, "soros": 1.05,
    },
    "BEAR_LOW_VOL": {
        "graham": 1.28, "buffett": 1.22, "marks": 1.18, "munger": 1.12,
        "cathie_wood": 0.75, "aschenbrenner": 0.78, "thiel": 0.82,
    },
    "BEAR_HIGH_VOL": {
        "marks": 1.32, "dalio": 1.28, "soros": 1.18, "graham": 1.15, "buffett": 1.1,
        "cathie_wood": 0.72, "aschenbrenner": 0.75,
    },
    "SIDEWAYS": {
        "munger": 1.12, "fisher": 1.12, "marks": 1.08, "buffett": 1.05, "lynch": 1.05,
    },
}


def detect_regime(date_str: Optional[str] = None) -> str:
    """Detect market regime from macro features (VIX + SPY trend)."""
    features = fetch_macro_features(date_str)
    return features.get("regime", "SIDEWAYS")


def get_regime_multipliers(regime: str) -> Dict[str, float]:
    """Return raw regime multipliers for an agent overlay."""
    return dict(_REGIME_ADJUSTMENTS.get(regime, {}))


def apply_regime_weights(weights: Dict[str, float], regime: str) -> Dict[str, float]:
    """Apply regime-specific multipliers to agent weights."""
    if not weights or not regime:
        return weights
    adj = _REGIME_ADJUSTMENTS.get(regime, {})
    if not adj:
        return weights
    result = {agent_id: w * adj.get(agent_id, 1.0) for agent_id, w in weights.items()}
    total = sum(result.values())
    if total > 0:
        result = {k: v / total for k, v in result.items()}
    return result
