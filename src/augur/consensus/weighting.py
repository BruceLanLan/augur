# -*- coding: utf-8 -*-
"""Orchestrate industry + regime agent weighting for consensus."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from augur.consensus.industry_matrix import detect_industry, get_agent_weights
from augur.consensus.macro_features import fetch_macro_features
from augur.consensus.paths import load_feedback_json
from augur.consensus.regime_router import RegimeRouter


@dataclass
class ConsensusWeightContext:
    """Resolved weighting inputs for ``get_consensus``."""

    weights: Dict[str, float] = field(default_factory=dict)
    industry: str = "general"
    industry_label: str = "General"
    regime: Optional[str] = None
    regime_features: Dict[str, Any] = field(default_factory=dict)


def _blend_weight_maps(
    primary: Dict[str, float],
    secondary: Dict[str, float],
    secondary_share: float = 0.35,
) -> Dict[str, float]:
    """Blend two weight maps; ``secondary_share`` is the router/regime overlay fraction."""
    if not primary:
        return dict(secondary)
    if not secondary:
        return dict(primary)
    share = max(0.0, min(1.0, secondary_share))
    keys = set(primary) | set(secondary)
    blended = {k: (1.0 - share) * primary.get(k, 0.0) + share * secondary.get(k, 0.0) for k in keys}
    total = sum(blended.values())
    if total <= 0:
        return primary
    return {k: v / total for k, v in blended.items()}


def build_consensus_weights(
    ticker: str = "",
    date_str: Optional[str] = None,
    context: Any = None,
) -> ConsensusWeightContext:
    """Build industry- and regime-aware agent weights for consensus scoring."""
    out = ConsensusWeightContext()

    if ticker or context is not None:
        industry, label = detect_industry(ticker, context=context)
        out.industry = industry
        out.industry_label = label
        trained = load_feedback_json("industry_matrix.json")
        out.weights = get_agent_weights(industry, trained)

    out.regime_features = fetch_macro_features(date_str)
    out.regime = out.regime_features.get("regime") or "SIDEWAYS"

    # Single regime overlay: blend industry base (65%) with router weights (35%).
    # Do not also call apply_regime_weights — that double-counts the same multipliers.
    router = RegimeRouter()
    router_weights = router.get_weights(regime=out.regime, features=out.regime_features)
    if router_weights:
        out.weights = _blend_weight_maps(out.weights, router_weights, secondary_share=0.35)

    return out


def restrict_weights_to_agents(
    weights: Dict[str, float],
    agent_ids: List[str],
) -> Dict[str, float]:
    """Keep weights for participating agents only and renormalize to sum 1."""
    if not agent_ids:
        return {}
    if not weights:
        n = len(agent_ids)
        return {aid: 1.0 / n for aid in agent_ids}
    restricted = {aid: weights[aid] for aid in agent_ids if aid in weights}
    if not restricted:
        n = len(agent_ids)
        return {aid: 1.0 / n for aid in agent_ids}
    total = sum(restricted.values())
    if total <= 0:
        n = len(agent_ids)
        return {aid: 1.0 / n for aid in agent_ids}
    return {aid: v / total for aid, v in restricted.items()}


def load_global_consensus_weights() -> Dict[str, float]:
    """Load optional global per-agent weights from ``feedback/weights.json``."""
    data = load_feedback_json("weights.json")
    weights = data.get("consensus_weights", data)
    if not isinstance(weights, dict):
        return {}
    return {str(k): float(v) for k, v in weights.items() if isinstance(v, (int, float))}
