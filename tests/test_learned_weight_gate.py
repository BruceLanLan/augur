# -*- coding: utf-8 -*-
"""R6 learned-weight blend is opt-in until a validation gate exists.

Background (2026-09-03 review): ``LearningEngine.has_learned_weights`` flips
after 3 resolved outcomes per agent regardless of how many tickers or
independent windows those outcomes span. The first production data set was a
single watchlist ticker with 16 overlapping 30-day windows, which produced a
3.6x spread in learned weights. ``ConsensusEngine`` used to blend those in at
40% unconditionally; it now requires ``AUGUR_FORCE_LEARNED=1``, mirroring the
``AUGUR_FORCE_RIC`` gate that already protects rolling-IC weights.
"""
from unittest.mock import patch

import pytest

from augur.learning import LearningEngine
from augur.personas.base import MarketContext
from augur.registry import AgentRegistry, DecisionCoordinator
import augur.registry as registry_module


def _engine_with_extreme_learned_weights(tmp_path, agent_ids):
    """Build a LearningEngine whose learned weights would visibly move consensus."""
    engine = LearningEngine(weights_path=tmp_path / "learned_weights.json")
    favourite = sorted(agent_ids)[0]
    n = len(agent_ids)
    with engine._lock:
        engine._accuracy = {
            aid: {"correct": 3, "total": 3, "ic_sum": 0.0, "ic_count": 3}
            for aid in agent_ids
        }
        # One agent gets almost all the weight; the rest share the remainder.
        rest = 0.1 / max(n - 1, 1)
        engine._weights = {aid: (0.9 if aid == favourite else rest) for aid in agent_ids}
    assert engine.has_learned_weights
    return engine


@pytest.fixture
def consensus_inputs(tmp_path, monkeypatch):
    registry = AgentRegistry()
    coordinator = DecisionCoordinator(registry)
    ctx = MarketContext(ticker="MSFT", pe=35, roe=0.40, gross_margins=0.70, price=440)
    results = coordinator.analyze_with_all(ctx)
    engine = _engine_with_extreme_learned_weights(tmp_path, list(results.keys()))
    monkeypatch.setattr(registry_module, "_learning_engine", engine)
    return coordinator, results, ctx


def _consensus_score(coordinator, results, ctx):
    with patch("augur.consensus.meta_model.MetaModel.load", return_value=None):
        return coordinator.get_consensus(results, ticker="MSFT", context=ctx).score


def test_learned_weights_not_blended_by_default(consensus_inputs, monkeypatch, tmp_path):
    coordinator, results, ctx = consensus_inputs
    monkeypatch.delenv("AUGUR_FORCE_LEARNED", raising=False)

    gated = _consensus_score(coordinator, results, ctx)

    # Baseline: same inputs with a cold LearningEngine (no learned weights at all).
    cold = LearningEngine(weights_path=tmp_path / "cold.json")
    monkeypatch.setattr(registry_module, "_learning_engine", cold)
    baseline = _consensus_score(coordinator, results, ctx)

    assert gated == pytest.approx(baseline), (
        "learned weights leaked into consensus without AUGUR_FORCE_LEARNED"
    )


def test_learned_weights_blend_with_explicit_opt_in(consensus_inputs, monkeypatch):
    coordinator, results, ctx = consensus_inputs
    monkeypatch.delenv("AUGUR_FORCE_LEARNED", raising=False)
    gated = _consensus_score(coordinator, results, ctx)

    monkeypatch.setenv("AUGUR_FORCE_LEARNED", "1")
    forced = _consensus_score(coordinator, results, ctx)

    assert forced != pytest.approx(gated), (
        "AUGUR_FORCE_LEARNED=1 should re-enable the 60/40 learned blend"
    )
