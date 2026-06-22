# -*- coding: utf-8 -*-
"""Consensus enhancement modules (industry/regime weighting, calibration)."""

from augur.consensus.industry_matrix import classify_industry, detect_industry, get_agent_weights
from augur.consensus.macro_features import fetch_macro_features
from augur.consensus.paths import feedback_path, load_feedback_json
from augur.consensus.probability_calibrator import calibrate_confidence
from augur.consensus.regime_router import RegimeRouter
from augur.consensus.regime_weights import apply_regime_weights, detect_regime, get_regime_multipliers
from augur.consensus.weighting import (
    ConsensusWeightContext,
    build_consensus_weights,
    load_global_consensus_weights,
    restrict_weights_to_agents,
)

__all__ = [
    "ConsensusWeightContext",
    "RegimeRouter",
    "apply_regime_weights",
    "build_consensus_weights",
    "calibrate_confidence",
    "classify_industry",
    "detect_industry",
    "detect_regime",
    "feedback_path",
    "fetch_macro_features",
    "get_agent_weights",
    "get_regime_multipliers",
    "load_feedback_json",
    "load_global_consensus_weights",
    "restrict_weights_to_agents",
]
