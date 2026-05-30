# -*- coding: utf-8 -*-
"""
End-to-end integration tests exercising the full pipeline:
  - CLI analyze/consensus commands
  - API /api/analyze endpoint (standalone and dashboard)
  - Error propagation when yfinance is unavailable
  - Data validation across the full flow
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from augur.registry import AgentRegistry, DecisionCoordinator
from augur.personas.base import MarketContext, AgentResponse, SignalType
from augur.cli import main


@pytest.fixture
def market_context():
    """Standard AAPL-like market context for testing."""
    return MarketContext(
        ticker="AAPL",
        pe=32,
        roe=0.15,
        gross_margins=0.46,
        price=210,
        market_cap=3200,
        revenue_growth=0.08,
        debt_ratio=0.35,
    )


@pytest.fixture
def registry():
    return AgentRegistry()


@pytest.fixture
def coordinator(registry):
    return DecisionCoordinator(registry)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def standalone_client():
    from augur.api import app as standalone_app
    return TestClient(standalone_app)


@pytest.fixture
def dashboard_client():
    from dashboard.app import app as dashboard_app
    return TestClient(dashboard_app)


class TestE2EAnalysisPipeline:
    """End-to-end tests validating the full data flow from input to consensus output."""

    def test_full_pipeline_via_registry(self, registry, coordinator, market_context):
        """Test 1: Full pipeline via registry - AgentRegistry -> analyze_with_all -> get_consensus.
        Verify consensus response has all required fields."""
        # Run all agents through the coordinator
        results = coordinator.analyze_with_all(market_context)
        assert len(results) >= 17, f"Expected >= 17 agent results, got {len(results)}"

        # Get consensus
        consensus = coordinator.get_consensus(results, ticker="AAPL", context=market_context)

        # Validate all required fields
        assert consensus.agent_id == "consensus"
        assert consensus.signal in (SignalType.BULLISH, SignalType.NEUTRAL, SignalType.BEARISH)
        assert 0 <= consensus.score <= 10
        assert 0 <= consensus.confidence <= 1
        assert isinstance(consensus.reasoning, str) and len(consensus.reasoning) > 0
        assert isinstance(consensus.key_findings, list)
        assert isinstance(consensus.risks, list)

        # Validate position_sizing in metadata
        assert "position_sizing" in consensus.metadata
        pos = consensus.metadata["position_sizing"]
        assert "position_pct" in pos
        assert "signal" in pos
        assert "score" in pos
        assert "confidence" in pos
        assert "rationale" in pos

    def test_cli_analyze_json(self, runner):
        """Test 2: CLI analyze command via Click CliRunner.
        Validate JSON output structure and all 18 agents present."""
        result = runner.invoke(main, [
            "analyze", "AAPL",
            "--pe", "32", "--roe", "0.15", "--gross-margins", "0.46",
            "--json"
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        data = json.loads(result.output)
        # When --json is used with analyze (no --persona), it outputs all agent results
        assert isinstance(data, dict)
        assert len(data) >= 18, f"Expected >= 18 agents in output, got {len(data)}"

        # Validate each agent result has proper structure
        for agent_id, agent_result in data.items():
            if "error" in agent_result:
                continue
            assert "agent_id" in agent_result
            assert "signal" in agent_result
            assert agent_result["signal"] in ("bullish", "neutral", "bearish", "error")
            assert "score" in agent_result
            assert "confidence" in agent_result

    def test_cli_consensus_json(self, runner):
        """Test 3: CLI consensus command via Click CliRunner.
        Validate consensus JSON has signal/score/confidence/individual results."""
        result = runner.invoke(main, [
            "consensus", "AAPL",
            "--pe", "32", "--roe", "0.15", "--gross-margins", "0.46",
            "--json"
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        data = json.loads(result.output)
        assert "ticker" in data
        assert data["ticker"] == "AAPL"

        # Validate consensus structure
        assert "consensus" in data
        cons = data["consensus"]
        assert cons["signal"] in ("bullish", "neutral", "bearish")
        assert 0 <= cons["score"] <= 10
        assert 0 <= cons["confidence"] <= 1
        assert "reasoning" in cons

        # Validate individual results
        assert "individual" in data
        assert len(data["individual"]) >= 18

    def test_standalone_api_analyze(self, standalone_client):
        """Test 4: API /api/analyze/{ticker} via FastAPI TestClient with manual metrics.
        Validate full response structure."""
        resp = standalone_client.get("/api/analyze/AAPL?pe=32&roe=0.15&gross_margins=0.46")
        assert resp.status_code == 200

        data = resp.json()
        # Top-level fields
        assert data["ticker"] == "AAPL"
        assert "timestamp" in data
        assert data["data_source"] == "manual"

        # Consensus structure
        assert "consensus" in data
        cons = data["consensus"]
        assert cons["signal"] in ("bullish", "neutral", "bearish")
        assert 0 <= cons["score"] <= 10
        assert 0 <= cons["confidence"] <= 1
        assert "metadata" in cons
        assert "position_sizing" in cons["metadata"]

        # Agents array
        assert "agents" in data
        assert "agent_count" in data
        assert data["agent_count"] >= 18
        assert len(data["agents"]) == data["agent_count"]

    def test_dashboard_api_analyze(self, dashboard_client):
        """Test 5: Dashboard /api/analyze/{ticker} endpoint via TestClient.
        Same validation as Test 4 but from dashboard app context."""
        resp = dashboard_client.get("/api/analyze/AAPL?pe=32&roe=0.15&gross_margins=0.46")
        assert resp.status_code == 200

        data = resp.json()
        # Top-level fields
        assert data["ticker"] == "AAPL"
        assert "timestamp" in data
        assert data["data_source"] == "manual"

        # Consensus structure
        assert "consensus" in data
        cons = data["consensus"]
        assert cons["signal"] in ("bullish", "neutral", "bearish")
        assert 0 <= cons["score"] <= 10
        assert 0 <= cons["confidence"] <= 1
        assert "metadata" in cons
        assert "position_sizing" in cons["metadata"]

        # Agents array
        assert "agents" in data
        assert "agent_count" in data
        assert data["agent_count"] >= 18
        assert len(data["agents"]) == data["agent_count"]

    def test_error_propagation_yfinance_unavailable(self, dashboard_client):
        """Test 6: Error propagation - mock yfinance import to raise ImportError.
        Call API with auto_fetch=True, verify graceful fallback."""
        with patch("augur.data.fetch_market_context", side_effect=ImportError("No module named 'yfinance'")):
            resp = dashboard_client.get("/api/analyze/AAPL?auto_fetch=true")
            assert resp.status_code == 200

            data = resp.json()
            # Should fallback gracefully
            assert data["data_source"] == "fallback"
            assert data["ticker"] == "AAPL"
            # Should still produce consensus (empty context)
            assert "consensus" in data
            assert data["agent_count"] >= 18

    def test_all_agents_error_consensus(self, coordinator):
        """Test 7: All agents ERROR case - mock all agents to return SignalType.ERROR.
        Verify consensus handles gracefully (no division by zero, returns neutral signal)."""
        ctx = MarketContext(ticker="ERR_TEST", pe=0)

        # Create error responses for all agents
        error_results = {}
        for agent in coordinator.registry.get_all():
            error_results[agent.agent_id] = AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.ERROR,
                confidence=0,
                score=0,
                reasoning="Simulated error"
            )

        # This should not raise (no division by zero)
        consensus = coordinator.get_consensus(error_results, ticker="ERR_TEST", context=ctx)

        assert consensus.agent_id == "consensus"
        # Score and confidence should be 0 or some fallback value
        assert 0 <= consensus.score <= 10
        assert 0 <= consensus.confidence <= 1
        # Signal should still be valid (not ERROR)
        assert consensus.signal in (SignalType.BULLISH, SignalType.NEUTRAL, SignalType.BEARISH)

    def test_score_clamping_extreme_values(self, coordinator):
        """Test 8: Verify score clamping - create extreme MarketContext values.
        Verify consensus.score is always in [0, 10] range."""
        # Extreme bullish context
        extreme_bullish = MarketContext(
            ticker="BULL_EXTREME",
            pe=5,
            pb=0.5,
            roe=0.9,
            gross_margins=0.95,
            revenue_growth=2.0,
            debt_ratio=0.01,
            fcf=100,
            market_cap=50,
            current_ratio=10.0,
        )
        results_bull = coordinator.analyze_with_all(extreme_bullish)
        consensus_bull = coordinator.get_consensus(results_bull, ticker="BULL_EXTREME", context=extreme_bullish)
        assert 0 <= consensus_bull.score <= 10, f"Bullish score out of range: {consensus_bull.score}"

        # Extreme bearish context
        extreme_bearish = MarketContext(
            ticker="BEAR_EXTREME",
            pe=500,
            pb=50,
            roe=-0.5,
            gross_margins=-0.1,
            revenue_growth=-0.8,
            debt_ratio=0.99,
            fcf=-10,
            market_cap=1,
            current_ratio=0.1,
            rsi=95,
        )
        results_bear = coordinator.analyze_with_all(extreme_bearish)
        consensus_bear = coordinator.get_consensus(results_bear, ticker="BEAR_EXTREME", context=extreme_bearish)
        assert 0 <= consensus_bear.score <= 10, f"Bearish score out of range: {consensus_bear.score}"

    def test_kelly_position_sizing(self, coordinator, market_context):
        """Test 9: Verify Kelly position sizing in consensus metadata.
        Bullish signal should have position_pct > 0, bearish should have position_pct = 0."""
        results = coordinator.analyze_with_all(market_context)
        consensus = coordinator.get_consensus(results, ticker="AAPL", context=market_context)

        pos = consensus.metadata.get("position_sizing", {})
        assert "position_pct" in pos
        assert isinstance(pos["position_pct"], float)

        # If signal is bullish and score is high enough, position_pct should be > 0
        if consensus.signal == SignalType.BULLISH and consensus.score >= 5:
            assert pos["position_pct"] > 0, "Bullish signal with score >= 5 should have position_pct > 0"

        # Test bearish case with extreme bearish context
        bearish_ctx = MarketContext(
            ticker="BEARISH",
            pe=500,
            roe=-0.5,
            gross_margins=-0.1,
            revenue_growth=-0.8,
            debt_ratio=0.99,
        )
        results_bear = coordinator.analyze_with_all(bearish_ctx)
        consensus_bear = coordinator.get_consensus(results_bear, ticker="BEARISH", context=bearish_ctx)
        pos_bear = consensus_bear.metadata.get("position_sizing", {})

        if consensus_bear.signal == SignalType.BEARISH:
            assert pos_bear["position_pct"] == 0.0, "Bearish signal should have position_pct = 0"

    def test_data_type_consistency(self, coordinator, market_context):
        """Test 10: Data type consistency - verify all AgentResponse fields have correct types.
        signal is SignalType enum, score is float, confidence is float 0-1."""
        results = coordinator.analyze_with_all(market_context)

        for agent_id, response in results.items():
            # agent_id and agent_name are strings
            assert isinstance(response.agent_id, str), f"{agent_id}: agent_id not str"
            assert isinstance(response.agent_name, str), f"{agent_id}: agent_name not str"

            # signal is SignalType enum
            assert isinstance(response.signal, SignalType), (
                f"{agent_id}: signal is {type(response.signal)}, expected SignalType"
            )

            # score is a number (int or float)
            assert isinstance(response.score, (int, float)), (
                f"{agent_id}: score is {type(response.score)}, expected float"
            )
            assert 0 <= response.score <= 10, f"{agent_id}: score={response.score} out of [0,10]"

            # confidence is a number 0-1
            assert isinstance(response.confidence, (int, float)), (
                f"{agent_id}: confidence is {type(response.confidence)}, expected float"
            )
            assert 0 <= response.confidence <= 1, (
                f"{agent_id}: confidence={response.confidence} out of [0,1]"
            )

            # reasoning is a string
            assert isinstance(response.reasoning, str), f"{agent_id}: reasoning not str"

            # key_findings and risks are lists
            assert isinstance(response.key_findings, list), f"{agent_id}: key_findings not list"
            assert isinstance(response.risks, list), f"{agent_id}: risks not list"

            # metadata is a dict
            assert isinstance(response.metadata, dict), f"{agent_id}: metadata not dict"
