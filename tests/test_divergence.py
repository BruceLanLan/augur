# -*- coding: utf-8 -*-
"""Tests for Feature B: agent divergence score computed by ConsensusEngine."""

import pytest
from unittest.mock import MagicMock, patch

from augur.consensus.engine import ConsensusEngine
from augur.personas.base import AgentResponse, MarketContext, SignalType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _agent(signal: SignalType, score: float = 5.0, agent_id: str = None) -> AgentResponse:
    uid = agent_id or f"agent_{signal.value}_{score}"
    return AgentResponse(
        agent_id=uid,
        agent_name=uid,
        signal=signal,
        score=score,
        confidence=0.6,
        reasoning="",
        key_findings=[],
        risks=[],
    )


def _make_results(**signal_counts) -> dict:
    """Build agent results dict from signal → count mapping."""
    results = {}
    idx = 0
    for signal_name, count in signal_counts.items():
        sig = SignalType(signal_name)
        for _ in range(count):
            a = _agent(sig, score=5.0 + idx * 0.01, agent_id=f"{signal_name}_{idx}")
            results[a.agent_id] = a
            idx += 1
    return results


def _run_engine(results: dict, ticker: str = "TEST") -> AgentResponse:
    """Run ConsensusEngine.compute() with the given agent results."""
    ctx = MarketContext(ticker=ticker, price=100.0)
    engine = ConsensusEngine()
    # Patch macro features to avoid external network calls (same pattern as test_consensus_v10_15)
    with patch("augur.consensus.weighting.fetch_macro_features",
               return_value={"vix": 18.0, "trend": "bull", "regime": "BULL_LOW_VOL"}):
        return engine.compute(results, ticker=ticker, context=ctx)


# ---------------------------------------------------------------------------
# Tests: divergence score formula
# ---------------------------------------------------------------------------

class TestDivergenceScore:
    """ConsensusEngine.compute() stores divergence metadata."""

    def test_all_bullish_gives_zero(self):
        """All agents bullish → no disagreement, score = 0."""
        results = _make_results(bullish=9, neutral=3)
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["score"] == 0.0
        assert div["is_divergent"] is False
        assert div["bullish_count"] == 9
        assert div["bearish_count"] == 0

    def test_all_bearish_gives_zero(self):
        """All agents bearish → no disagreement, score = 0."""
        results = _make_results(bearish=8, neutral=2)
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["score"] == 0.0
        assert div["is_divergent"] is False

    def test_all_neutral_gives_zero(self):
        """No active agents (all neutral) → score = 0.0 (no active to split)."""
        results = _make_results(neutral=10)
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["score"] == 0.0
        assert div["is_divergent"] is False
        assert div["neutral_count"] == 10

    def test_perfect_tie_gives_one(self):
        """Equal bull/bear split → maximum divergence score = 1.0."""
        results = _make_results(bullish=5, bearish=5, neutral=2)
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["score"] == pytest.approx(1.0, abs=0.001)
        assert div["bullish_count"] == 5
        assert div["bearish_count"] == 5

    def test_tie_with_enough_agents_is_divergent(self):
        """5B/5Br with ≥2 on each side → is_divergent = True."""
        results = _make_results(bullish=5, bearish=5)
        consensus = _run_engine(results)
        assert consensus.metadata["divergence"]["is_divergent"] is True

    def test_one_vs_one_not_divergent(self):
        """1B/1Br: score=1.0 but min < 2 → is_divergent = False (noise guard)."""
        results = _make_results(bullish=1, bearish=1, neutral=8)
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["score"] == pytest.approx(1.0, abs=0.001)
        assert div["is_divergent"] is False

    def test_moderate_split_score(self):
        """3B / 9Br → score = 2*3/12 = 0.5; min(3,9)=3 ≥ 2 and 0.5 ≥ 0.4 → divergent."""
        results = _make_results(bullish=3, bearish=9)
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["score"] == pytest.approx(0.5, abs=0.001)
        assert div["is_divergent"] is True

    def test_slight_lean_not_divergent(self):
        """2B / 10Br → score = 2*2/12 ≈ 0.333 < 0.4 → not divergent."""
        results = _make_results(bullish=2, bearish=10)
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["score"] == pytest.approx(round(2 * 2 / 12, 3), abs=0.001)
        assert div["is_divergent"] is False

    def test_total_valid_excludes_error_agents(self):
        """ERROR signals are excluded from valid_results → not counted."""
        results = _make_results(bullish=4, bearish=4)
        # Add an ERROR agent manually
        err_agent = AgentResponse(
            agent_id="broken",
            agent_name="Broken",
            signal=SignalType.ERROR,
            score=0.0,
            confidence=0.0,
            reasoning="",
            key_findings=[],
            risks=[],
        )
        results["broken"] = err_agent

        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["total_valid"] == 8  # error excluded
        assert div["bullish_count"] == 4
        assert div["bearish_count"] == 4

    def test_divergence_key_in_metadata(self):
        """Metadata always contains the 'divergence' key after compute()."""
        results = _make_results(bullish=5, neutral=5)
        consensus = _run_engine(results)
        assert "divergence" in consensus.metadata
        div = consensus.metadata["divergence"]
        assert {"score", "bullish_count", "bearish_count", "neutral_count",
                "total_valid", "is_divergent"} == set(div.keys())

    def test_neutral_consensus_from_tie_is_flagged(self):
        """The key use-case: bull/bear tie → consensus NEUTRAL, but divergence fires.

        This distinguishes 'genuinely no conviction' from 'committee is split'.
        """
        results = _make_results(bullish=6, bearish=6)
        consensus = _run_engine(results)
        # Consensus signal should be neutral (tie) or could go either way —
        # the important thing is that divergence is flagged regardless.
        div = consensus.metadata["divergence"]
        assert div["is_divergent"] is True
        assert div["score"] == pytest.approx(1.0, abs=0.001)

    def test_exact_threshold_boundary_is_divergent(self):
        """2B / 8Br → score = 2*2/10 = 0.4 exactly; min(2,8)=2 exactly.

        Both guard conditions (`score >= 0.4`, `min >= 2`) are inclusive —
        this is the single case that sits exactly on both boundaries at once,
        so an off-by-one on either `>=` would flip this test.
        """
        results = _make_results(bullish=2, bearish=8)
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["score"] == pytest.approx(0.4, abs=0.001)
        assert div["is_divergent"] is True

    def test_all_agents_error_gives_empty_divergence(self):
        """Every agent returns ERROR (not just some) → valid_results is empty.

        Must degrade to a clean zero/false divergence report, not crash or
        divide by zero.
        """
        results = {}
        for i in range(3):
            results[f"broken_{i}"] = AgentResponse(
                agent_id=f"broken_{i}",
                agent_name=f"Broken {i}",
                signal=SignalType.ERROR,
                score=0.0,
                confidence=0.0,
                reasoning="",
                key_findings=[],
                risks=[],
            )
        consensus = _run_engine(results)
        div = consensus.metadata["divergence"]
        assert div["total_valid"] == 0
        assert div["bullish_count"] == 0
        assert div["bearish_count"] == 0
        assert div["score"] == 0.0
        assert div["is_divergent"] is False


# ---------------------------------------------------------------------------
# Tests: API response exposure
# ---------------------------------------------------------------------------

class TestDivergenceInApiResponse:
    """POST /api/analyze/{ticker} exposes divergence at top-level."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        return TestClient(app)

    def _make_consensus(self, signal="bullish", score=7.0, div_score=0.0, is_divergent=False,
                        bull=9, bear=0, neu=3):
        c = MagicMock()
        c.signal = MagicMock()
        c.signal.value = signal
        c.score = score
        c.confidence = 0.75
        c.key_findings = ["finding"]
        c.risks = []
        c.reasoning = ""
        c.kelly_fraction = 0.1
        c.metadata = {
            "position_sizing": {"position_pct": 10},
            "divergence": {
                "score": div_score,
                "bullish_count": bull,
                "bearish_count": bear,
                "neutral_count": neu,
                "total_valid": bull + bear + neu,
                "is_divergent": is_divergent,
            },
        }
        c.to_dict.return_value = {
            "signal": signal,
            "score": score,
            "confidence": 0.75,
            "metadata": c.metadata,
        }
        return c

    def _make_agent(self, signal="bullish"):
        a = MagicMock()
        a.signal = MagicMock()
        a.signal.value = signal
        a.score = 7.0
        a.confidence = 0.7
        a.agent_name = "TestAgent"
        a.agent_id = "test"
        a.to_dict.return_value = {"signal": signal, "score": 7.0, "agent_id": "test"}
        return a

    def test_divergence_field_in_response(self, client):
        """Top-level 'divergence' key is present when analysis returns metadata."""
        from augur.personas.base import MarketContext

        consensus = self._make_consensus(div_score=0.8, is_divergent=True, bull=5, bear=5, neu=2)
        mock_results = {"a1": self._make_agent("bullish")}

        with patch("dashboard.routes.analysis.get_coordinator") as mock_coord, \
             patch("dashboard.routes.analysis.get_enabled_personas", return_value=None), \
             patch("dashboard.routes.analysis._get_rules_engine") as mock_eng, \
             patch("augur.data.fetch_market_context",
                   return_value=MarketContext(ticker="AAPL", price=150.0)):
            coord = mock_coord.return_value
            coord.analyze_with_all.return_value = mock_results
            coord.get_consensus.return_value = consensus
            mock_eng.return_value.get_rules.return_value = []

            resp = client.get("/api/analyze/AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert "divergence" in data
        div = data["divergence"]
        assert div["is_divergent"] is True
        assert div["score"] == pytest.approx(0.8, abs=0.001)
        assert div["bullish_count"] == 5
        assert div["bearish_count"] == 5

    def test_divergence_none_when_not_in_metadata(self, client):
        """If engine produced no divergence key, API returns null gracefully."""
        from augur.personas.base import MarketContext

        consensus = self._make_consensus()
        consensus.metadata = {"position_sizing": {"position_pct": 10}}  # no divergence key
        consensus.to_dict.return_value = {"signal": "bullish", "score": 7.0, "metadata": {}}
        mock_results = {"a1": self._make_agent("bullish")}

        with patch("dashboard.routes.analysis.get_coordinator") as mock_coord, \
             patch("dashboard.routes.analysis.get_enabled_personas", return_value=None), \
             patch("dashboard.routes.analysis._get_rules_engine") as mock_eng, \
             patch("augur.data.fetch_market_context",
                   return_value=MarketContext(ticker="AAPL", price=150.0)):
            coord = mock_coord.return_value
            coord.analyze_with_all.return_value = mock_results
            coord.get_consensus.return_value = consensus
            mock_eng.return_value.get_rules.return_value = []

            resp = client.get("/api/analyze/AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert "divergence" in data
        assert data["divergence"] is None
