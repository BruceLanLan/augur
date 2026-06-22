# -*- coding: utf-8 -*-
"""Tests for v10.15 consensus weighting and feedback templates."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from augur.consensus import (
    build_consensus_weights,
    classify_industry,
    detect_industry,
    feedback_path,
    get_agent_weights,
    load_feedback_json,
    restrict_weights_to_agents,
)
from augur.consensus.regime_weights import apply_regime_weights
from augur.personas.base import AgentResponse, MarketContext, SignalType
from augur.registry import DecisionCoordinator


REPO_ROOT = Path(__file__).parent.parent


class TestIndustryClassification:
    def test_classify_technology_from_context(self):
        key, label = classify_industry("Technology", "Software—Infrastructure")
        assert key == "technology"
        assert label == "Technology"

    def test_classify_healthcare_biotech_not_technology(self):
        key, _ = classify_industry("Healthcare", "Biotechnology")
        assert key == "healthcare"

    def test_classify_retail_as_consumer_not_technology(self):
        key, _ = classify_industry("Consumer Cyclical", "Retail")
        assert key == "consumer"

    def test_classify_china_from_hk_ticker(self):
        key, _ = classify_industry("", "", "0700.HK")
        assert key == "china"

    def test_detect_industry_prefers_market_context(self):
        ctx = MarketContext(ticker="WMT", sector="Consumer Cyclical", industry="Retail")
        key, _ = detect_industry("WMT", context=ctx)
        assert key == "consumer"


class TestWeightQuality:
    def test_industry_weights_normalize(self):
        weights = get_agent_weights("technology", {})
        assert weights
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.001)

    def test_regime_bear_boosts_defensive_agents(self):
        base = {"buffett": 0.34, "graham": 0.33, "cathie_wood": 0.33}
        adj = apply_regime_weights(base, "BEAR_HIGH_VOL")
        assert adj["graham"] > adj["cathie_wood"]
        assert adj["buffett"] > adj["cathie_wood"]

    def test_trained_matrix_overrides_base(self):
        trained = {"technology": {"buffett": 1.0, "graham": 0.0}}
        weights = get_agent_weights("technology", trained)
        assert weights == {"buffett": pytest.approx(1.0)}


class TestFeedbackTemplates:
    def test_example_files_exist_and_parse(self):
        matrix_example = REPO_ROOT / "feedback" / "industry_matrix.json.example"
        weights_example = REPO_ROOT / "feedback" / "weights.json.example"
        assert matrix_example.exists()
        assert weights_example.exists()
        matrix = json.loads(matrix_example.read_text(encoding="utf-8"))
        weights = json.loads(weights_example.read_text(encoding="utf-8"))
        assert "technology" in matrix
        assert "consensus_weights" in weights
        assert sum(weights["consensus_weights"].values()) == pytest.approx(1.0, abs=0.02)

    def test_feedback_path_resolves_to_repo_root(self):
        path = feedback_path("industry_matrix.json.example")
        assert path == REPO_ROOT / "feedback" / "industry_matrix.json.example"

    def test_load_feedback_json_missing_returns_default(self):
        data = load_feedback_json("nonexistent_file_xyz.json", default={"x": 1})
        assert data == {"x": 1}


class TestRestrictWeights:
    def test_renormalizes_to_participating_agents(self):
        weights = {"buffett": 0.5, "graham": 0.3, "cathie_wood": 0.2}
        out = restrict_weights_to_agents(weights, ["buffett", "graham"])
        assert set(out.keys()) == {"buffett", "graham"}
        assert sum(out.values()) == pytest.approx(1.0, abs=0.001)
        assert out["buffett"] == pytest.approx(0.625, abs=0.001)

    def test_equal_fallback_when_no_overlap(self):
        weights = {"cathie_wood": 1.0}
        out = restrict_weights_to_agents(weights, ["buffett", "graham"])
        assert out == {"buffett": 0.5, "graham": 0.5}


class TestBuildConsensusWeights:
    @patch("augur.consensus.weighting.fetch_macro_features")
    def test_build_includes_regime_and_industry(self, mock_macro):
        mock_macro.return_value = {"vix": 18.0, "trend": "bull", "regime": "BULL_LOW_VOL"}
        ctx = MarketContext(ticker="NVDA", sector="Technology", industry="Semiconductors")
        out = build_consensus_weights("NVDA", context=ctx)
        assert out.industry == "technology"
        assert out.regime == "BULL_LOW_VOL"
        assert out.weights


class TestGetConsensusIntegration:
    def _make_results(self, coordinator, bullish_score=7.0):
        results = {}
        for agent in coordinator.registry.get_all():
            results[agent.agent_id] = AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.BULLISH,
                confidence=0.7,
                score=bullish_score,
                reasoning="test",
                coverage_confidence=1.0,
            )
        return results

    @patch("augur.consensus.weighting.fetch_macro_features")
    def test_get_consensus_uses_consensus_modules(self, mock_macro):
        mock_macro.return_value = {"vix": 30.0, "trend": "bear", "regime": "BEAR_HIGH_VOL"}
        coordinator = DecisionCoordinator()
        ctx = MarketContext(
            ticker="JPM", price=100, sector="Financial Services", industry="Banks",
        )
        results = self._make_results(coordinator)
        consensus = coordinator.get_consensus(results, ticker="JPM", context=ctx)
        assert consensus.agent_id == "consensus"
        assert "Regime:" in consensus.reasoning
        assert consensus.metadata.get("regime_features", {}).get("regime") == "BEAR_HIGH_VOL"

    @patch("augur.consensus.build_consensus_weights")
    def test_get_consensus_calls_build_consensus_weights(self, mock_build):
        from augur.consensus.weighting import ConsensusWeightContext

        mock_build.return_value = ConsensusWeightContext(
            regime="SIDEWAYS",
            regime_features={"vix": 20.0, "trend": "sideways", "regime": "SIDEWAYS"},
        )
        coordinator = DecisionCoordinator()
        results = self._make_results(coordinator)
        coordinator.get_consensus(results, ticker="TEST")
        mock_build.assert_called_once()
