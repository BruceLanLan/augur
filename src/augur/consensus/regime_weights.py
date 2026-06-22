# -*- coding: utf-8 -*-
"""Macro regime detection and weight adjustment."""

from typing import Dict, Optional

_REGIME_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "BULL_LOW_VOL": {"lynch": 1.2, "cathie_wood": 1.15, "marks": 0.9},
    "BULL_HIGH_VOL": {"marks": 1.2, "dalio": 1.15, "graham": 1.1, "cathie_wood": 0.9},
    "BEAR_LOW_VOL": {"graham": 1.25, "buffett": 1.2, "marks": 1.15, "cathie_wood": 0.8},
    "BEAR_HIGH_VOL": {"marks": 1.3, "dalio": 1.25, "soros": 1.15, "graham": 1.1},
    "SIDEWAYS": {"munger": 1.1, "fisher": 1.1, "marks": 1.05},
}


def detect_regime(date_str: Optional[str] = None) -> str:
    """Detect market regime from VIX level."""
    try:
        from augur.consensus.macro_features import fetch_macro_features
        features = fetch_macro_features(date_str)
        vix = features.get("vix", 20.0)
        trend = features.get("trend", "sideways")
        high_vol = vix >= 25
        if trend == "bull":
            return "BULL_HIGH_VOL" if high_vol else "BULL_LOW_VOL"
        if trend == "bear":
            return "BEAR_HIGH_VOL" if high_vol else "BEAR_LOW_VOL"
        return "SIDEWAYS"
    except Exception:
        return "SIDEWAYS"


def apply_regime_weights(weights: Dict[str, float], regime: str) -> Dict[str, float]:
    """Apply regime-specific multipliers to agent weights."""
    if not weights or not regime:
        return weights
    adj = _REGIME_ADJUSTMENTS.get(regime, {})
    if not adj:
        return weights
    result = {}
    for agent_id, w in weights.items():
        result[agent_id] = w * adj.get(agent_id, 1.0)
    total = sum(result.values())
    if total > 0:
        result = {k: v / total for k, v in result.items()}
    return result
