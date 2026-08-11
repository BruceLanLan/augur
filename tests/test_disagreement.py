# -*- coding: utf-8 -*-
"""Tests for DisagreementMap engine."""

import pytest

from augur.disagreement import (
    ConflictPoint,
    DisagreementMap,
    DisagreementMapBuilder,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def balanced_outputs() -> dict:
    """8 bulls, 7 bears, 3 neutrals — moderate consensus."""
    result = {}
    for i in range(8):
        result[f"bull_{i}"] = {"signal": "bullish", "score": 7.0 + i * 0.2, "confidence": 0.8}
    for i in range(7):
        result[f"bear_{i}"] = {"signal": "bearish", "score": 3.0 + i * 0.3, "confidence": 0.7}
    for i in range(3):
        result[f"neut_{i}"] = {"signal": "neutral", "score": 5.0, "confidence": 0.4}
    return result


@pytest.fixture
def strong_bull_outputs() -> dict:
    """15 bulls, 3 neutrals — strong consensus."""
    result = {}
    for i in range(15):
        result[f"bull_{i}"] = {"signal": "bullish", "score": 8.0, "confidence": 0.9}
    for i in range(3):
        result[f"neut_{i}"] = {"signal": "neutral", "score": 5.0, "confidence": 0.3}
    return result


@pytest.fixture
def divided_outputs() -> dict:
    """9 bulls, 9 bears — divided."""
    result = {}
    for i in range(9):
        result[f"bull_{i}"] = {"signal": "bullish", "score": 7.0, "confidence": 0.8}
    for i in range(9):
        result[f"bear_{i}"] = {"signal": "bearish", "score": 3.0, "confidence": 0.8}
    return result


# ---------------------------------------------------------------------------
# ConflictPoint
# ---------------------------------------------------------------------------

class TestConflictPoint:
    def test_creation(self):
        cp = ConflictPoint(
            claim="Valuation is high",
            bullish_personas=["buffett"],
            bearish_personas=["dalio", "soros"],
            information_that_would_resolve="Next earnings",
            impact="high",
        )
        assert cp.claim == "Valuation is high"
        assert len(cp.bearish_personas) == 2
        assert cp.impact == "high"

    def test_defaults(self):
        cp = ConflictPoint(claim="test")
        assert cp.bullish_personas == []
        assert cp.impact == "medium"

    def test_with_abstaining_and_evidence(self):
        cp = ConflictPoint(
            claim="Moat is widening",
            bullish_personas=["buffett", "munger"],
            bearish_personas=["dalio"],
            abstaining_personas={"soros": "Insufficient data"},
            evidence_supporting=["ev_001", "ev_002"],
            evidence_contradicting=["ev_003"],
            information_that_would_resolve="Market share report",
            impact="high",
        )
        assert len(cp.abstaining_personas) == 1
        assert "soros" in cp.abstaining_personas
        assert cp.evidence_supporting == ["ev_001", "ev_002"]
        assert cp.evidence_contradicting == ["ev_003"]


# ---------------------------------------------------------------------------
# DisagreementMap
# ---------------------------------------------------------------------------

class TestDisagreementMap:
    def test_creation(self):
        dm = DisagreementMap(ticker="AAPL", run_id="run_001")
        assert dm.ticker == "AAPL"
        assert dm.consensus_strength == "moderate"
        assert dm.conflict_points == []


# ---------------------------------------------------------------------------
# DisagreementMapBuilder
# ---------------------------------------------------------------------------

class TestBuilder:
    def test_build_balanced(self, balanced_outputs):
        builder = DisagreementMapBuilder("AAPL", "run_001")
        result = builder.build(balanced_outputs)
        assert result.ticker == "AAPL"
        assert result.run_id == "run_001"
        assert result.consensus_strength in ("weak", "divided")  # 8 vs 7 is weak
        assert len(result.conflict_points) <= 5
        assert len(result.silent_personas) == 3  # 3 neutrals
        assert len(result.summary) > 0

    def test_build_strong_bull(self, strong_bull_outputs):
        builder = DisagreementMapBuilder("MSFT", "run_002")
        result = builder.build(strong_bull_outputs)
        assert result.consensus_strength == "strong"  # 15/18 = 83%
        assert len(result.agreement_points) >= 1

    def test_build_divided(self, divided_outputs):
        builder = DisagreementMapBuilder("TSLA", "run_003")
        result = builder.build(divided_outputs)
        assert result.consensus_strength == "divided"  # 50/50

    def test_build_empty(self):
        builder = DisagreementMapBuilder("TEST", "run_empty")
        result = builder.build({})
        assert result.summary == "No persona responses available."

    def test_all_conflicts_have_required_fields(self, balanced_outputs):
        builder = DisagreementMapBuilder("AAPL", "run_001")
        result = builder.build(balanced_outputs)
        for cp in result.conflict_points:
            assert cp.claim
            assert cp.impact in ("high", "medium", "low")
            assert cp.information_that_would_resolve

    def test_summary_is_non_empty_string(self, balanced_outputs):
        builder = DisagreementMapBuilder("AAPL", "run_001")
        result = builder.build(balanced_outputs)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 10
