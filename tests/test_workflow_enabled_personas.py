# -*- coding: utf-8 -*-
"""Peer review #2: workflow respects workspace enabled_personas."""

from unittest.mock import MagicMock, patch

import pytest

from augur.personas.base import AgentResponse, MarketContext, SignalType
from augur.registry import DecisionCoordinator


@pytest.fixture
def mock_ctx():
    return MarketContext(ticker="TEST", pe=20, roe=0.15, gross_margins=0.4, price=100.0)


@pytest.fixture
def mock_response():
    return AgentResponse(
        agent_id="buffett",
        agent_name="Warren Buffett",
        signal=SignalType.BULLISH,
        confidence=0.8,
        score=7.0,
        reasoning="Test",
    )


class TestWorkflowEnabledPersonas:
    def test_uses_workspace_filter_when_agents_empty(self, mock_ctx, mock_response):
        captured = {}

        def fake_analyze(self, ctx, enabled_personas=None):
            captured["enabled_personas"] = enabled_personas
            return {"buffett": mock_response}

        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch("augur.workspace.get_enabled_personas", return_value=["buffett", "graham"]):
                with patch.object(DecisionCoordinator, "analyze_with_all", fake_analyze):
                    with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_response):
                        from augur.workflow import run_workflow

                        result = run_workflow("TEST", steps="analyze,consensus")

        assert captured["enabled_personas"] == ["buffett", "graham"]
        assert result["agents_filter"] == ["buffett", "graham"]

    def test_explicit_agents_override_workspace(self, mock_ctx, mock_response):
        buffett_agent = MagicMock(agent_id="buffett", analyze=lambda c: mock_response)

        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch("augur.workspace.get_enabled_personas", return_value=["graham"]):
                with patch("augur.registry.AgentRegistry.get_all", return_value=[buffett_agent]):
                    with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_response):
                        from augur.workflow import run_workflow

                        result = run_workflow("TEST", steps="analyze", agents="buffett")

        assert "agents_filter" not in result
        assert "buffett" in result["results"]["analyze"]

    def test_reports_skipped_unknown_agent_ids(self, mock_ctx, mock_response):
        buffett_agent = MagicMock(agent_id="buffett", analyze=lambda c: mock_response)

        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch("augur.registry.AgentRegistry.get_all", return_value=[buffett_agent]):
                from augur.workflow import run_workflow

                result = run_workflow("TEST", steps="analyze", agents="buffett,not_real")

        assert result["agents_skipped"] == ["not_real"]
        assert "buffett" in result["results"]["analyze"]

    def test_consensus_called_once_for_consensus_and_committee(self, mock_ctx, mock_response):
        call_count = {"n": 0}

        def fake_consensus(self, responses, ticker="", date_str=None, context=None):
            call_count["n"] += 1
            mock_response.metadata = {}
            return mock_response

        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch.object(DecisionCoordinator, "analyze_with_all", return_value={"buffett": mock_response}):
                with patch.object(DecisionCoordinator, "get_consensus", fake_consensus):
                    from augur.workflow import run_workflow

                    run_workflow("TEST", steps="consensus,committee")

        assert call_count["n"] == 1

    def test_low_participation_warning_in_output(self, mock_ctx, mock_response):
        mock_response.metadata = {"low_participation": True}

        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch.object(DecisionCoordinator, "analyze_with_all", return_value={"buffett": mock_response}):
                with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_response):
                    from augur.workflow import run_workflow

                    result = run_workflow("TEST", steps="consensus")

        assert result["results"]["consensus"]["low_participation"] is True
        assert any("low_participation" in w for w in result.get("warnings", []))

    def test_all_invalid_agents_warning(self, mock_ctx, mock_response):
        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch.object(
                DecisionCoordinator, "analyze_with_all", return_value={"buffett": mock_response},
            ):
                from augur.workflow import run_workflow

                result = run_workflow("TEST", steps="analyze", agents="fake1,fake2")

        assert any("all_requested_agents_invalid" in w for w in result.get("warnings", []))

    def test_step_status_envelope(self, mock_ctx, mock_response):
        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch.object(
                DecisionCoordinator, "analyze_with_all", return_value={"buffett": mock_response},
            ):
                with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_response):
                    from augur.workflow import run_workflow

                    result = run_workflow("TEST", steps="fetch,analyze,consensus,sentiment")

        status = result["step_status"]
        assert status["fetch"] == "ok"
        assert status["analyze"] == "ok"
        assert status["consensus"] == "ok"
        assert status["committee"] == "skipped"
        assert "step_timings_ms" in result

    def test_debate_reuses_prior_responses(self, mock_ctx, mock_response):
        analyze_calls = {"n": 0}

        def fake_analyze(self, ctx, enabled_personas=None):
            analyze_calls["n"] += 1
            return {"buffett": mock_response}

        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch.object(DecisionCoordinator, "analyze_with_all", fake_analyze):
                with patch.object(
                    DecisionCoordinator, "run_debate", return_value={"buffett": mock_response},
                ) as mock_debate:
                    with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_response):
                        from augur.workflow import run_workflow

                        run_workflow("TEST", steps="analyze,debate")

        assert analyze_calls["n"] == 1
        mock_debate.assert_called_once()
        assert mock_debate.call_args.kwargs.get("initial_results") is not None

    def test_warnings_in_summary(self, mock_ctx, mock_response):
        mock_response.metadata = {"low_participation": True}

        with patch("augur.data.fetch_market_context", return_value=mock_ctx):
            with patch.object(
                DecisionCoordinator, "analyze_with_all", return_value={"buffett": mock_response},
            ):
                with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_response):
                    from augur.workflow import run_workflow

                    result = run_workflow("TEST", steps="consensus")

        assert "Warnings" in result["summary"]
        assert "low_participation" in result["summary"]
