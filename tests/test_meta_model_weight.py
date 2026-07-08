# -*- coding: utf-8 -*-
"""Tests for R1: meta_model_weight default changed from 0.5 to 0.0.

MetaModel is a self-described stub whose predict() is just the cross-agent
median score. It was never validated to improve consensus quality, but the
old default (meta_model_weight=0.5) blended it into every consensus score
at 50% weight, diluting all the upstream weighting logic (industry/regime/
learned/diversity). See docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md, debt 1.

This suite proves: (a) the stub is inert by default (no blending occurs,
predict() isn't even called), (b) the config knob still works exactly as
before when a user explicitly opts back in, so the fix is additive rather
than a breaking removal of the blend mechanism.
"""
import pytest
from unittest.mock import patch

from augur.consensus.engine import ConsensusEngine
from augur.consensus.meta_model import MetaModel
from augur.personas.base import AgentResponse, MarketContext, SignalType


def _agent(agent_id: str, score: float, signal: SignalType = SignalType.BULLISH) -> AgentResponse:
    return AgentResponse(
        agent_id=agent_id,
        agent_name=agent_id,
        signal=signal,
        score=score,
        confidence=0.6,
        reasoning="",
        key_findings=[],
        risks=[],
    )


def _make_results() -> dict:
    """Three agents with clearly distinct scores so a weighted-average
    consensus score is numerically distinguishable from the plain median."""
    return {
        "a": _agent("a", 3.0),
        "b": _agent("b", 6.0),
        "c": _agent("c", 9.0),
    }


def _run_engine(config_overrides: dict) -> AgentResponse:
    """Run ConsensusEngine.compute() with a given consensus config, network
    calls patched out (same pattern as test_divergence.py)."""
    ctx = MarketContext(ticker="TEST", price=100.0)
    engine = ConsensusEngine()
    with patch("augur.consensus.weighting.fetch_macro_features",
               return_value={"vix": 18.0, "trend": "bull", "regime": "BULL_LOW_VOL"}), \
         patch("augur.config.get_config", return_value=config_overrides):
        return engine.compute(_make_results(), ticker="TEST", context=ctx)


class TestMetaModelDefaultIsInert:
    """With no config override, the stub must not move the score at all."""

    def test_default_config_matches_explicit_zero_weight(self):
        """No 'consensus' key in config (real-world default) must produce the
        exact same score as explicitly setting meta_model_weight=0 — proving
        the new default is 0.0, not silently falling back to 0.5 somewhere."""
        default_result = _run_engine({})
        explicit_zero_result = _run_engine({"consensus": {"meta_model_weight": 0.0}})
        assert default_result.score == pytest.approx(explicit_zero_result.score, abs=1e-9)

    def test_default_config_does_not_call_predict(self):
        """Direct evidence the dilution literally doesn't happen anymore —
        not just that it happens to cancel out arithmetically."""
        with patch.object(MetaModel, "predict") as mock_predict:
            _run_engine({})
        mock_predict.assert_not_called()

    def test_malformed_config_value_falls_back_to_zero_not_half(self):
        """A non-numeric meta_model_weight must fail safe to the new inert
        default (0.0), not the old diluting default (0.5)."""
        with patch.object(MetaModel, "predict") as mock_predict:
            _run_engine({"consensus": {"meta_model_weight": "not-a-number"}})
        mock_predict.assert_not_called()


class TestMetaModelExplicitOptIn:
    """Backward compatibility: explicitly configuring the blend weight must
    still work exactly as it did before this change."""

    def test_full_weight_equals_pure_median(self):
        """meta_model_weight=1.0 fully overrides the weighted score, so the
        result must equal MetaModel().predict() on the raw agent scores —
        an exact, hand-computable assertion (median of 3.0/6.0/9.0 = 6.0)."""
        result = _run_engine({"consensus": {"meta_model_weight": 1.0}})
        assert result.score == pytest.approx(6.0, abs=1e-6)

    def test_half_weight_is_linear_interpolation(self):
        """meta_model_weight=0.5 (the old default) must produce the exact
        midpoint between the weight=0 and weight=1 results — this is what
        'blend' means, and it's the behavior a user opting back in expects."""
        zero_weight = _run_engine({"consensus": {"meta_model_weight": 0.0}})
        full_weight = _run_engine({"consensus": {"meta_model_weight": 1.0}})
        half_weight = _run_engine({"consensus": {"meta_model_weight": 0.5}})

        expected = 0.5 * zero_weight.score + 0.5 * full_weight.score
        assert half_weight.score == pytest.approx(expected, abs=1e-6)

    def test_weight_clamped_to_valid_range(self):
        """Out-of-range config values (e.g. 2.0) are clamped to [0, 1], not
        rejected or applied verbatim — matches the existing clamp logic."""
        over_range = _run_engine({"consensus": {"meta_model_weight": 2.0}})
        full_weight = _run_engine({"consensus": {"meta_model_weight": 1.0}})
        assert over_range.score == pytest.approx(full_weight.score, abs=1e-6)
