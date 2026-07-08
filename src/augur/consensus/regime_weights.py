# -*- coding: utf-8 -*-
"""Macro regime detection and weight adjustment."""

from typing import Dict, Optional

from augur.consensus.macro_features import fetch_macro_features

# Disabled as of Phase D (v10.6.0): scripts/regime_weight_oos.py ran a real
# cross-sectional OOS validation (37 tickers, 2022-01..2026-06, EDGAR
# point-in-time fundamentals) and found no clear rank-IC improvement from
# these hand-picked multipliers vs. a flat equal-weight consensus -- see
# CHANGELOG 10.4.0 for the full result. Rather than delete the mechanism
# outright, the multiplier tables are emptied so `apply_regime_weights` /
# `RegimeRouter.get_weights` become no-ops; regime *detection* (VIX+SPY
# classification) stays wired for display/diagnostics. Original multiplier
# values are recoverable from git history (commit f3df8ad and earlier) if
# a future retuning pass produces validated numbers.
_REGIME_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "BULL_LOW_VOL": {},
    "BULL_HIGH_VOL": {},
    "BEAR_LOW_VOL": {},
    "BEAR_HIGH_VOL": {},
    "SIDEWAYS": {},
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
