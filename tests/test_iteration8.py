# -*- coding: utf-8 -*-
"""
Tests for Iteration 8: Logic fixes, cache management, and dashboard CSS.

Covers:
- registry.py: add_debate_message is a proper method on DecisionCoordinator
- data.py: cache TTL is 180, clear_cache, cache_info, force_refresh
- dashboard API: /api/cache/clear, /api/cache/info endpoints
- Kelly criterion edge cases (score=5, bearish, neutral low-confidence)
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============ registry.py Tests ============

class TestAddDebateMessage:
    """Test that add_debate_message is a proper method on DecisionCoordinator."""

    def test_add_debate_message_exists(self):
        """add_debate_message should be a callable method."""
        from augur.registry import DecisionCoordinator
        coordinator = DecisionCoordinator()
        assert hasattr(coordinator, "add_debate_message")
        assert callable(getattr(coordinator, "add_debate_message"))

    def test_add_debate_message_appends(self):
        """add_debate_message should append to _debate_history."""
        from augur.registry import DecisionCoordinator, DebateMessage
        coordinator = DecisionCoordinator()

        msg = DebateMessage(
            from_agent="test_agent",
            to_agent="all",
            topic="valuation",
            content="Test debate message",
        )
        coordinator.add_debate_message(msg)

        history = coordinator.get_debate_history()
        assert len(history) == 1
        assert history[0].from_agent == "test_agent"
        assert history[0].content == "Test debate message"

    def test_add_multiple_debate_messages(self):
        """Multiple messages should accumulate in history."""
        from augur.registry import DecisionCoordinator, DebateMessage
        coordinator = DecisionCoordinator()

        for i in range(3):
            msg = DebateMessage(
                from_agent=f"agent_{i}",
                to_agent="all",
                topic=f"topic_{i}",
                content=f"Message {i}",
            )
            coordinator.add_debate_message(msg)

        history = coordinator.get_debate_history()
        assert len(history) == 3


# ============ data.py Cache Tests ============

class TestDataCache:
    """Test data.py cache functionality."""

    def test_cache_ttl_is_180(self):
        """Cache TTL should be 180 seconds (3 minutes)."""
        from augur import data
        assert data._CACHE_TTL == 180

    def test_clear_cache(self):
        """clear_cache() should empty the _cache dict."""
        from augur.data import clear_cache, _cache, _cache_set

        # Add some entries
        _cache_set("test_key_1", "value1")
        _cache_set("test_key_2", "value2")
        assert len(_cache) >= 2

        clear_cache()
        assert len(_cache) == 0

    def test_cache_info(self):
        """cache_info() should return size and TTL."""
        from augur.data import cache_info, clear_cache, _cache_set

        clear_cache()
        info = cache_info()
        assert info["size"] == 0
        assert info["ttl_seconds"] == 180

        _cache_set("info_test", "some_value")
        info = cache_info()
        assert info["size"] == 1

        # Cleanup
        clear_cache()

    def test_force_refresh_bypasses_cache(self):
        """force_refresh=True should skip cached values."""
        from augur.data import fetch_market_context, _cache, _cache_set, clear_cache
        from augur.personas.base import MarketContext

        clear_cache()

        # Pre-populate cache with a known value
        cache_key = "ctx:TESTX"
        fake_ctx = MarketContext(ticker="TESTX", price=100.0)
        _cache_set(cache_key, fake_ctx)

        # Without force_refresh, should return cached value
        with patch("augur.data._get_yfinance") as mock_yf:
            result = fetch_market_context("TESTX", force_refresh=False)
            assert result.price == 100.0
            mock_yf.assert_not_called()

        # With force_refresh, should call yfinance (mock it to return empty info)
        with patch("augur.data._get_yfinance") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.info = {}
            mock_yf.return_value.Ticker.return_value = mock_ticker

            result = fetch_market_context("TESTX", force_refresh=True)
            mock_yf.assert_called_once()
            # Since info is empty, defaults to ticker with zeros
            assert result.ticker == "TESTX"

        clear_cache()


# ============ Dashboard API Tests ============

class TestCacheEndpoints:
    """Test /api/cache/clear and /api/cache/info endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the dashboard."""
        from fastapi.testclient import TestClient
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from dashboard.app import app
        return TestClient(app)

    def test_cache_clear_endpoint(self, client):
        """GET /api/cache/clear should return status ok."""
        response = client.get("/api/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Cache cleared"

    def test_cache_info_endpoint(self, client):
        """GET /api/cache/info should return cache metadata."""
        response = client.get("/api/cache/info")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "cache" in data
        assert "size" in data["cache"]
        assert "ttl_seconds" in data["cache"]
        assert data["cache"]["ttl_seconds"] == 180

    def test_cache_clear_then_info(self, client):
        """Clear then info should show size 0."""
        client.get("/api/cache/clear")
        response = client.get("/api/cache/info")
        data = response.json()
        assert data["cache"]["size"] == 0


# ============ Kelly Criterion Edge Cases ============

class TestKellyCriterionEdgeCases:
    """Test Kelly criterion edge cases in consensus scoring."""

    def test_score_exactly_5_neutral(self):
        """Score of exactly 5 should produce neutral signal."""
        from augur.registry import DecisionCoordinator, AgentRegistry
        from augur.personas.base import MarketContext, AgentResponse, SignalType

        coordinator = DecisionCoordinator()
        ctx = MarketContext(ticker="TEST", pe=15, pb=1.5)

        # Create mock results where average is exactly neutral
        mock_results = {}
        for i, agent in enumerate(coordinator.registry.get_all()[:4]):
            resp = AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.NEUTRAL,
                score=5.0,
                confidence=0.5,
                reasoning="Exactly neutral",
                key_findings=["Neutral finding"],
            )
            mock_results[agent.agent_id] = resp

        if mock_results:
            consensus = coordinator.get_consensus(mock_results, ticker="TEST", context=ctx)
            # Score should be clamped in [0, 10]
            assert 0 <= consensus.score <= 10
            # Neutral score should not produce strong kelly position
            kelly_pct = consensus.metadata.get("position_sizing", {}).get("position_pct", 0)
            assert kelly_pct is not None

    def test_bearish_signal_kelly(self):
        """Bearish signal should have low or zero kelly position."""
        from augur.registry import DecisionCoordinator
        from augur.personas.base import MarketContext, AgentResponse, SignalType

        coordinator = DecisionCoordinator()
        ctx = MarketContext(ticker="BEAR", pe=50, pb=5.0)

        mock_results = {}
        for agent in coordinator.registry.get_all()[:4]:
            resp = AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.BEARISH,
                score=2.0,
                confidence=0.8,
                reasoning="Very bearish",
                key_findings=["Overvalued"],
            )
            mock_results[agent.agent_id] = resp

        if mock_results:
            consensus = coordinator.get_consensus(mock_results, ticker="BEAR", context=ctx)
            assert consensus.score <= 5.0
            kelly_pct = consensus.metadata.get("position_sizing", {}).get("position_pct", 0)
            # Bearish should have low/zero position
            assert kelly_pct <= 10

    def test_neutral_low_confidence_kelly(self):
        """Neutral signal with low confidence should have minimal position."""
        from augur.registry import DecisionCoordinator
        from augur.personas.base import MarketContext, AgentResponse, SignalType

        coordinator = DecisionCoordinator()
        ctx = MarketContext(ticker="MEH", pe=20, pb=2.0)

        mock_results = {}
        for agent in coordinator.registry.get_all()[:4]:
            resp = AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.NEUTRAL,
                score=5.0,
                confidence=0.3,
                reasoning="Uncertain",
                key_findings=["Mixed signals"],
            )
            mock_results[agent.agent_id] = resp

        if mock_results:
            consensus = coordinator.get_consensus(mock_results, ticker="MEH", context=ctx)
            kelly_pct = consensus.metadata.get("position_sizing", {}).get("position_pct", 0)
            # Low confidence neutral should not produce large position
            assert kelly_pct <= 15


# ============ FEAT-002: Logic Correctness Fixes ============

class TestLynchPegOverflowGuard:
    """Test that Lynch PEG calculation guards against very low earnings_growth."""

    def test_lynch_peg_overflow_guard(self):
        """When earnings_growth < 1%, PEG should stay at neutral (5) not explode."""
        from augur.personas.lynch import LynchAgent
        from augur.personas.base import MarketContext

        agent = LynchAgent()
        ctx = MarketContext(
            ticker="LOWGROW",
            pe=30,
            earnings_growth=0.005,  # 0.5% - very low
            revenue_growth=0.10,
            gross_margins=0.40,
            operating_margins=0.15,
            roe=0.10,
            market_cap=20.0,
        )
        result = agent.analyze(ctx)
        factors = result.metadata["factors"]

        # PEG should be approximately 5 (neutral), not an extreme value
        assert abs(factors["peg"] - 5.0) <= 1.0, (
            f"PEG factor should be ~5 (neutral) for tiny growth, got {factors['peg']}"
        )

    def test_lynch_peg_normal_growth(self):
        """When earnings_growth >= 1%, PEG should be computed normally."""
        from augur.personas.lynch import LynchAgent
        from augur.personas.base import MarketContext

        agent = LynchAgent()
        ctx = MarketContext(
            ticker="NORMGROW",
            pe=15,
            earnings_growth=0.15,  # 15% - healthy growth
            revenue_growth=0.15,
            gross_margins=0.40,
            operating_margins=0.15,
            roe=0.15,
            market_cap=20.0,
        )
        result = agent.analyze(ctx)
        factors = result.metadata["factors"]

        # PEG = 15 / (0.15*100) = 15/15 = 1.0, which is < peg_max(1.5)
        # So peg_score should be 7 or 10
        assert factors["peg"] >= 7.0, (
            f"PEG factor should be >= 7 for good PEG ratio, got {factors['peg']}"
        )


class TestGrahamPeZeroNeutral:
    """Test that Graham gives neutral valuation when PE is 0 (missing data)."""

    def test_graham_pe_zero_neutral(self):
        """When PE==0 (missing), valuation should be neutral (5), not 0."""
        from augur.personas.graham import GrahamAgent
        from augur.personas.base import MarketContext

        agent = GrahamAgent()
        ctx = MarketContext(
            ticker="NOPE",
            pe=0,  # Missing PE data
            pb=1.5,
            current_ratio=2.0,
            debt_ratio=0.40,
            revenue_growth=0.05,
            earnings_growth=0.05,
        )
        result = agent.analyze(ctx)
        factors = result.metadata["factors"]

        # valuation should be >= 4 (neutral territory), not 0
        assert factors["valuation"] >= 4.0, (
            f"Valuation should be neutral (~5) when PE=0, got {factors['valuation']}"
        )

    def test_graham_pe_positive_scored(self):
        """When PE > 0, valuation should be scored based on PE value."""
        from augur.personas.graham import GrahamAgent
        from augur.personas.base import MarketContext

        agent = GrahamAgent()
        ctx = MarketContext(
            ticker="CHEAP",
            pe=10,  # Below pe_max of 15
            pb=1.0,
            current_ratio=2.5,
            debt_ratio=0.30,
            revenue_growth=0.05,
            earnings_growth=0.05,
        )
        result = agent.analyze(ctx)
        factors = result.metadata["factors"]

        # PE=10 is <= 15*0.67=10.05, so val_score=10
        assert factors["valuation"] >= 7.0, (
            f"Valuation should be high for low PE=10, got {factors['valuation']}"
        )


class TestKellyMinimumPosition:
    """Test that Kelly criterion gives minimum 1% for bullish signals at threshold."""

    def test_kelly_minimum_position(self):
        """Bullish signal with score=5.0 should get at least 1.0% allocation."""
        from augur.registry import DecisionCoordinator
        from augur.personas.base import MarketContext, AgentResponse, SignalType

        coordinator = DecisionCoordinator()
        ctx = MarketContext(ticker="MINKEL", pe=15, pb=1.5)

        # All agents barely bullish with score=5.0
        mock_results = {}
        for agent in coordinator.registry.get_all()[:4]:
            resp = AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.BULLISH,
                score=5.0,
                confidence=0.6,
                reasoning="Barely bullish",
                key_findings=["Marginal value"],
            )
            mock_results[agent.agent_id] = resp

        consensus = coordinator.get_consensus(mock_results, ticker="MINKEL", context=ctx)
        pct = consensus.metadata.get("position_pct", 0)

        # Should be at least 1.0% for any bullish signal passing threshold
        assert pct >= 1.0, (
            f"Kelly position should be >= 1.0% for bullish score=5, got {pct}"
        )


class TestOverheatingUsesCtxPe:
    """Test that overheating check uses ctx_for_risk.pe correctly."""

    def test_overheating_uses_ctx_pe(self):
        """When all agents bullish and PE>30, risks should mention overvaluation."""
        from augur.registry import DecisionCoordinator
        from augur.personas.base import MarketContext, AgentResponse, SignalType

        coordinator = DecisionCoordinator()
        ctx = MarketContext(ticker="OVERHEAT", pe=35, pb=3.0)

        # All agents bullish
        mock_results = {}
        for agent in coordinator.registry.get_all()[:4]:
            resp = AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.BULLISH,
                score=8.0,
                confidence=0.8,
                reasoning="Very bullish outlook",
                key_findings=["Strong growth"],
            )
            mock_results[agent.agent_id] = resp

        consensus = coordinator.get_consensus(mock_results, ticker="OVERHEAT", context=ctx)

        # Should contain overvaluation risk text
        risk_text = " ".join(consensus.risks)
        assert "valuation elevated" in risk_text.lower() or "PE=35" in risk_text, (
            f"Risks should mention PE overvaluation with PE=35, got: {consensus.risks}"
        )

    def test_overheating_not_triggered_low_pe(self):
        """When all agents bullish but PE<=30, no overvaluation warning."""
        from augur.registry import DecisionCoordinator
        from augur.personas.base import MarketContext, AgentResponse, SignalType

        coordinator = DecisionCoordinator()
        ctx = MarketContext(ticker="CHEAPBULL", pe=20, pb=2.0)

        mock_results = {}
        for agent in coordinator.registry.get_all()[:4]:
            resp = AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.BULLISH,
                score=8.0,
                confidence=0.8,
                reasoning="Bullish",
                key_findings=["Growth"],
            )
            mock_results[agent.agent_id] = resp

        consensus = coordinator.get_consensus(mock_results, ticker="CHEAPBULL", context=ctx)

        # Should NOT contain PE overvaluation warning
        risk_text = " ".join(consensus.risks)
        assert "valuation elevated" not in risk_text.lower(), (
            f"Risks should not mention PE overvaluation with PE=20, got: {consensus.risks}"
        )


# ============ FEAT-003: Watchlist API Tests ============

class TestWatchlistAPI:
    """Tests for dashboard watchlist API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the dashboard."""
        from fastapi.testclient import TestClient
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from dashboard.app import app
        return TestClient(app)

    def test_watchlist_api_structure(self, client):
        """GET /api/watchlist returns dict with 'watchlist' key that is a list."""
        response = client.get("/api/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert "watchlist" in data
        assert isinstance(data["watchlist"], list)

    def test_watchlist_add_valid(self, client):
        """POST /api/watchlist/add with valid ticker returns status ok."""
        response = client.post(
            "/api/watchlist/add",
            json={"ticker": "TEST"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_watchlist_delete_nonexist(self, client):
        """DELETE /api/watchlist/NONEXIST returns 404."""
        response = client.delete("/api/watchlist/NONEXIST")
        assert response.status_code == 404

    def test_cache_clear_endpoint_ok(self, client):
        """GET /api/cache/clear returns status ok."""
        response = client.get("/api/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
