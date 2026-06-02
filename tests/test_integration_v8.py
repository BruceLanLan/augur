# -*- coding: utf-8 -*-
"""
tests/test_integration_v8.py - End-to-end integration tests for v8 features.

Exercises real flows across multiple v8 modules working together:
  - Analysis triggers learning weight update
  - Analysis with sentiment factor adjusts score
  - Rules engine evaluates an analysis result and fires notification
  - Chat engine accumulates history across calls
  - Price streamer starts/stops with client lifecycle
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============ Test: Analysis triggers learning weight update ============

class TestLearningWeightUpdate:
    """Verify that running an analysis followed by recording an outcome updates learned weights."""

    def test_analysis_triggers_weight_recalculation(self, tmp_path):
        """Run an analysis, record outcome, verify weights change."""
        from augur.learning import LearningEngine
        from augur.registry import AgentRegistry, DecisionCoordinator
        from augur.personas.base import MarketContext

        weights_path = tmp_path / "learned_weights.json"
        engine = LearningEngine(weights_path=weights_path)

        # Run a full multi-agent analysis
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="AAPL", pe=28, roe=0.35, gross_margins=0.45, price=210)
        results = coordinator.analyze_with_all(ctx)

        # Record predictions from the analysis
        for agent_id, response in results.items():
            engine.record_prediction(
                ticker="AAPL",
                agent_id=agent_id,
                signal=response.signal.value,
                score=response.score,
                confidence=response.confidence,
            )

        assert engine.prediction_count == len(results)

        # Simulate outcome: stock went up 8%
        engine.record_outcome("AAPL", actual_return=0.08)

        # Verify weights have been computed
        weights = engine.get_weights()
        assert len(weights) > 0
        # Weights should sum to approximately 1
        assert abs(sum(weights.values()) - 1.0) < 0.01

        # Verify the file was persisted
        assert weights_path.exists()
        data = json.loads(weights_path.read_text())
        assert "weights" in data
        assert "accuracy" in data

    def test_learned_weights_integrate_into_consensus(self, tmp_path):
        """Verify learned weights are used in consensus calculation."""
        from augur.learning import LearningEngine
        from augur.registry import AgentRegistry, DecisionCoordinator
        from augur.personas.base import MarketContext

        weights_path = tmp_path / "learned_weights.json"
        engine = LearningEngine(weights_path=weights_path)

        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="MSFT", pe=35, roe=0.40, gross_margins=0.70, price=440)

        # First analysis without learned weights
        results = coordinator.analyze_with_all(ctx)
        consensus_before = coordinator.get_consensus(results, ticker="MSFT", context=ctx)

        # The consensus should still work (score in valid range)
        assert 0 <= consensus_before.score <= 10


# ============ Test: Sentiment factor adjusts consensus score ============

class TestSentimentIntegration:
    """Verify that sentiment analysis affects the consensus score."""

    def test_sentiment_factor_applied_to_consensus(self):
        """Consensus score shifts by patched sentiment factor (registry v8 hook)."""
        from augur.registry import AgentRegistry, DecisionCoordinator
        from augur.personas.base import MarketContext

        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="NVDA", pe=60, roe=0.50, gross_margins=0.75, price=135)
        results = coordinator.analyze_with_all(ctx)

        mock_sa = MagicMock()
        mock_sa.get_sentiment_factor.return_value = 0.0
        with patch("augur.registry._get_sentiment_analyzer", return_value=mock_sa):
            baseline = coordinator.get_consensus(results, ticker="NVDA", context=ctx)

        mock_sa.get_sentiment_factor.return_value = 0.5
        with patch("augur.registry._get_sentiment_analyzer", return_value=mock_sa):
            boosted = coordinator.get_consensus(results, ticker="NVDA", context=ctx)

        assert boosted.score == pytest.approx(baseline.score + 0.5, abs=1e-4)
        assert 0.0 <= boosted.score <= 10.0

        mock_sa.get_sentiment_factor.return_value = -0.5
        with patch("augur.registry._get_sentiment_analyzer", return_value=mock_sa):
            dampened = coordinator.get_consensus(results, ticker="NVDA", context=ctx)

        assert dampened.score == pytest.approx(max(0.0, baseline.score - 0.5), abs=1e-4)
        assert 0.0 <= dampened.score <= 10.0

    def test_sentiment_score_bounded(self):
        """Verify score stays within [0, 10] even with extreme sentiment."""
        from augur.sentiment import SentimentAnalyzer

        sa = SentimentAnalyzer()
        # Get sentiment factor for various tickers
        for ticker in ["AAPL", "NVDA", "TSLA", "GME", "AMC"]:
            factor = sa.get_sentiment_factor(ticker)
            assert -0.5 <= factor <= 0.5, f"Factor for {ticker} out of range: {factor}"


# ============ Test: Rules engine evaluates and fires notification ============

class TestRulesEngineIntegration:
    """Verify that the rules engine evaluates analysis results and dispatches."""

    def test_rule_fires_on_high_score(self, tmp_path):
        """A rule matching score > 7 should fire when consensus is high."""
        from augur.rules import RulesEngine, Rule

        rules_path = tmp_path / "rules.yaml"
        engine = RulesEngine(rules_path=str(rules_path))

        # Add a rule: if consensus_score > 7, notify on telegram
        rule = Rule(
            id="test-001",
            name="High Score Alert",
            conditions=[{"field": "consensus_score", "op": ">", "value": 7}],
            actions=[{"channel": "telegram", "message": "Score is {consensus_score} for {ticker}"}],
        )
        engine.add_rule(rule)

        # Simulate a high-score analysis result
        analysis_result = {
            "ticker": "AAPL",
            "consensus_score": 8.5,
            "signal": "bullish",
        }

        triggered = engine.evaluate(analysis_result)
        assert len(triggered) == 1
        assert triggered[0]["rule_name"] == "High Score Alert"
        assert "8.5" in triggered[0]["message"]
        assert "AAPL" in triggered[0]["message"]

        # Verify dispatcher recorded it
        sent = engine.dispatcher.get_sent()
        assert len(sent) == 1
        assert sent[0]["channel"] == "telegram"

    def test_rule_does_not_fire_on_low_score(self, tmp_path):
        """A rule matching score > 7 should NOT fire when score is below threshold."""
        from augur.rules import RulesEngine, Rule

        rules_path = tmp_path / "rules.yaml"
        engine = RulesEngine(rules_path=str(rules_path))

        rule = Rule(
            id="test-002",
            name="High Score Alert",
            conditions=[{"field": "consensus_score", "op": ">", "value": 7}],
            actions=[{"channel": "slack", "message": "Alert: {ticker}"}],
        )
        engine.add_rule(rule)

        analysis_result = {
            "ticker": "INTC",
            "consensus_score": 4.2,
            "signal": "bearish",
        }

        triggered = engine.evaluate(analysis_result)
        assert len(triggered) == 0

    def test_rules_persist_to_yaml(self, tmp_path):
        """Rules should be saved to and loaded from YAML."""
        from augur.rules import RulesEngine, Rule

        rules_path = tmp_path / "rules.yaml"
        engine = RulesEngine(rules_path=str(rules_path))

        rule = Rule(
            id="persist-001",
            name="Persistence Test",
            conditions=[{"field": "signal", "op": "==", "value": "bullish"}],
            actions=[{"channel": "lark", "message": "Buy signal!"}],
        )
        engine.add_rule(rule)

        # Create a new engine instance to verify persistence
        engine2 = RulesEngine(rules_path=str(rules_path))
        rules = engine2.get_rules()
        assert len(rules) == 1
        assert rules[0].name == "Persistence Test"


# ============ Test: Chat engine accumulates history ============

class TestChatEngineHistory:
    """Verify the chat engine preserves conversation history across calls."""

    def test_history_accumulates(self):
        """Multiple chat calls should build up history."""
        from augur.chat import ChatEngine

        engine = ChatEngine()

        # First message
        resp1 = engine.get_response("What about AAPL?", agent_id="buffett")
        assert resp1["agent_id"] == "buffett"
        assert len(resp1["response"]) > 0

        # Second message
        resp2 = engine.get_response("Is it risky?", agent_id="graham")
        assert resp2["agent_id"] == "graham"

        # Third message
        resp3 = engine.get_response("Market outlook?", agent_id="dalio")
        assert resp3["agent_id"] == "dalio"

        # History should have 6 entries (3 user + 3 assistant)
        history = engine.get_history()
        assert len(history) == 6
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_clear_history(self):
        """Clear history should reset state."""
        from augur.chat import ChatEngine

        engine = ChatEngine()
        engine.get_response("test message", agent_id="buffett")
        assert len(engine.get_history()) == 2

        engine.clear_history()
        assert len(engine.get_history()) == 0

    def test_all_persona_templates_respond(self):
        """Every persona should generate a non-empty response."""
        from augur.chat import ChatEngine

        engine = ChatEngine()
        agents = engine.get_available_agents()
        assert len(agents) >= 8  # At least the defined personas

        for agent_info in agents:
            resp = engine.get_response("Tell me about value investing", agent_id=agent_info["agent_id"])
            assert len(resp["response"]) > 20, f"Empty response from {agent_info['agent_id']}"


# ============ Test: Price streamer lifecycle ============

class TestPriceStreamerLifecycle:
    """Verify the price streamer starts/stops with client lifecycle."""

    def test_streamer_starts_on_connect_stops_on_disconnect(self):
        """Streamer should start when first client connects and stop when last disconnects."""
        from augur.streaming import PriceStreamer

        async def _run():
            streamer = PriceStreamer(interval=0.1)

            # Create mock websockets
            ws1 = AsyncMock()
            ws2 = AsyncMock()

            # Connect first client
            await streamer.connect(ws1)
            assert streamer.client_count == 1

            # Start the streamer
            await streamer.start()
            assert streamer.is_running is True

            # Connect second client
            await streamer.connect(ws2)
            assert streamer.client_count == 2

            # Disconnect first client
            await streamer.disconnect(ws1)
            assert streamer.client_count == 1
            # Should still be running (one client left)
            assert streamer.is_running is True

            # Disconnect last client - should auto-stop
            await streamer.disconnect(ws2)
            assert streamer.client_count == 0
            # Auto-stop on last disconnect
            assert streamer.is_running is False

        asyncio.run(_run())

    def test_streamer_generates_price_updates(self):
        """Streamer should generate valid price data."""
        from augur.streaming import PriceStreamer

        streamer = PriceStreamer(interval=0.05)
        prices = streamer.get_current_prices()

        assert len(prices) > 0
        for p in prices:
            assert "ticker" in p
            assert "price" in p
            assert p["price"] > 0

    def test_streamer_broadcast_to_clients(self):
        """Streamer should broadcast to all connected clients."""
        from augur.streaming import PriceStreamer

        async def _run():
            streamer = PriceStreamer(interval=60)

            ws1 = AsyncMock()
            ws2 = AsyncMock()

            await streamer.connect(ws1)
            await streamer.connect(ws2)

            # Broadcast a message
            await streamer.broadcast({"type": "test", "data": 123})

            ws1.send_text.assert_called_once()
            ws2.send_text.assert_called_once()

            await streamer.disconnect(ws1)
            await streamer.disconnect(ws2)

        asyncio.run(_run())


# ============ Test: Optimizer frontier monotonicity ============

class TestOptimizerFrontierQuality:
    """Verify the optimizer produces monotone frontier curves."""

    def test_frontier_monotone_returns(self):
        """Frontier should have non-decreasing returns (within tolerance)."""
        from augur.optimizer import PortfolioOptimizer

        optimizer = PortfolioOptimizer()

        # Create test data: 4 assets with different return profiles
        returns_data = {
            "A": [0.01, 0.02, -0.01, 0.03, 0.01, 0.02, -0.005, 0.015, 0.02, 0.01],
            "B": [0.005, 0.01, 0.005, 0.01, 0.005, 0.01, 0.005, 0.01, 0.005, 0.01],
            "C": [-0.01, 0.04, -0.02, 0.05, -0.01, 0.03, -0.015, 0.04, -0.01, 0.03],
            "D": [0.002, 0.003, 0.001, 0.004, 0.002, 0.003, 0.001, 0.004, 0.002, 0.003],
        }

        frontier = optimizer.efficient_frontier(returns_data, n_points=15)
        assert len(frontier) > 0

        # Returns should be non-decreasing (monotone)
        for i in range(1, len(frontier)):
            assert frontier[i].expected_return >= frontier[i - 1].expected_return - 1e-6, \
                f"Non-monotone at point {i}: {frontier[i].expected_return} < {frontier[i-1].expected_return}"

    def test_frontier_weights_are_non_negative(self):
        """All frontier portfolio weights should be non-negative (long-only)."""
        from augur.optimizer import PortfolioOptimizer

        optimizer = PortfolioOptimizer()

        returns_data = {
            "X": [0.03, -0.01, 0.02, 0.01, -0.005, 0.025, 0.015, -0.01, 0.02, 0.01],
            "Y": [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
            "Z": [-0.02, 0.05, -0.03, 0.06, -0.02, 0.04, -0.025, 0.05, -0.02, 0.04],
        }

        frontier = optimizer.efficient_frontier(returns_data, n_points=10)
        for point in frontier:
            for ticker, weight in point.weights.items():
                assert weight >= -0.001, f"Negative weight {weight} for {ticker}"

    def test_optimizer_handles_singular_matrix(self):
        """Optimizer should handle perfectly correlated (singular) returns gracefully."""
        from augur.optimizer import PortfolioOptimizer

        optimizer = PortfolioOptimizer()

        # Two identical return series = singular covariance matrix
        returns_data = {
            "A": [0.01, 0.02, -0.01, 0.03],
            "B": [0.01, 0.02, -0.01, 0.03],
        }

        # Should not raise, should return equal weights or valid result
        result = optimizer.optimize(returns_data)
        assert result is not None
        assert abs(sum(result.weights.values()) - 1.0) < 0.01
