# -*- coding: utf-8 -*-
"""
End-to-end tests for v10.15 agentic workflow + workspace features.

Covers:
  - run_workflow step chains with mocked market data
  - Dashboard /api/workspace presets and persistence
  - Consensus modules integrated through workflow output
  - MCP augur_workflow validation (no live MCP server required)
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from augur.personas.base import AgentResponse, MarketContext, SignalType
from augur.registry import DecisionCoordinator


@pytest.fixture
def tech_context():
    return MarketContext(
        ticker="NVDA",
        pe=60,
        roe=0.45,
        gross_margins=0.72,
        price=500,
        market_cap=2800,
        revenue_growth=0.50,
        sector="Technology",
        industry="Semiconductors",
        beta_1y=1.8,
    )


@pytest.fixture
def mock_responses():
    return {
        "buffett": AgentResponse(
            agent_id="buffett", agent_name="Buffett",
            signal=SignalType.BULLISH, confidence=0.75, score=7.5,
            reasoning="Strong moat",
        ),
        "cathie_wood": AgentResponse(
            agent_id="cathie_wood", agent_name="Wood",
            signal=SignalType.BULLISH, confidence=0.85, score=9.0,
            reasoning="AI leader",
        ),
        "marks": AgentResponse(
            agent_id="marks", agent_name="Marks",
            signal=SignalType.NEUTRAL, confidence=0.6, score=5.5,
            reasoning="Fully priced",
        ),
    }


@pytest.fixture
def mock_consensus(mock_responses):
    return AgentResponse(
        agent_id="consensus",
        agent_name="Consensus",
        signal=SignalType.BULLISH,
        confidence=0.78,
        score=7.8,
        reasoning="Weighted bullish",
        metadata={"position_sizing": {"position_pct": 8.5}},
    )


@pytest.fixture
def dashboard_client():
    from dashboard.app import app
    return TestClient(app)


class TestAgenticWorkflowAPI:
    """Exercise run_workflow as the agentic pipeline API."""

    def test_full_chain_fetch_analyze_consensus(
        self, tech_context, mock_responses, mock_consensus,
    ):
        with patch("augur.data.fetch_market_context", return_value=tech_context):
            with patch.object(
                DecisionCoordinator, "analyze_with_all", return_value=mock_responses,
            ):
                with patch.object(
                    DecisionCoordinator, "get_consensus", return_value=mock_consensus,
                ):
                    from augur.workflow import run_workflow
                    result = run_workflow("nvda", steps="fetch,analyze,consensus")

        assert result["ticker"] == "NVDA"
        assert result["steps"] == ["fetch", "analyze", "consensus"]
        assert result["results"]["fetch"]["sector"] == "Technology"
        assert len(result["results"]["analyze"]) == 3
        consensus = result["results"]["consensus"]
        assert consensus["signal"] == "bullish"
        assert consensus["kelly_pct"] == pytest.approx(8.5)
        assert "NVDA" in result["summary"]
        assert "Consensus" in result["summary"]

    def test_committee_with_custom_question(
        self, tech_context, mock_responses, mock_consensus,
    ):
        with patch("augur.data.fetch_market_context", return_value=tech_context):
            with patch.object(
                DecisionCoordinator, "analyze_with_all", return_value=mock_responses,
            ):
                with patch.object(
                    DecisionCoordinator, "get_consensus", return_value=mock_consensus,
                ):
                    from augur.workflow import run_workflow
                    result = run_workflow(
                        "NVDA",
                        steps="fetch,committee",
                        question="Is NVDA overvalued at current PE?",
                    )

        committee = result["results"]["committee"]
        assert committee["question"] == "Is NVDA overvalued at current PE?"
        assert committee["verdict"] == "bullish"
        assert committee["vote"]["bullish"] == 2
        assert committee["vote"]["neutral"] == 1
        assert committee["vote"]["bearish"] == 0

    def test_debate_step_mocked(self, tech_context, mock_responses, mock_consensus):
        with patch("augur.data.fetch_market_context", return_value=tech_context):
            with patch.object(
                DecisionCoordinator, "run_debate", return_value=mock_responses,
            ):
                with patch.object(
                    DecisionCoordinator, "get_consensus", return_value=mock_consensus,
                ):
                    from augur.workflow import run_workflow
                    result = run_workflow("NVDA", steps="debate")

        debate = result["results"]["debate"]
        assert debate["signal"] == "bullish"
        assert debate["rounds"] == 2

    def test_sentiment_step_graceful_error(self, tech_context):
        with patch("augur.data.fetch_market_context", return_value=tech_context):
            with patch(
                "augur.sentiment.SentimentAnalyzer.get_sentiment",
                side_effect=RuntimeError("no sentiment backend"),
            ):
                from augur.workflow import run_workflow
                result = run_workflow("NVDA", steps="sentiment")

        assert "error" in result["results"]["sentiment"]

    def test_default_steps_when_empty(self, tech_context, mock_responses, mock_consensus):
        import augur.workspace as ws_mod

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod._workspace = None
                with patch("augur.data.fetch_market_context", return_value=tech_context):
                    with patch.object(
                        DecisionCoordinator, "analyze_with_all", return_value=mock_responses,
                    ):
                        with patch.object(
                            DecisionCoordinator, "get_consensus", return_value=mock_consensus,
                        ):
                            from augur.workflow import run_workflow
                            result = run_workflow("AAPL", steps="")

        assert result["steps"] == ["fetch", "analyze", "consensus"]

    def test_default_steps_follow_committee_preset(self, tech_context, mock_responses, mock_consensus):
        import augur.workspace as ws_mod

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod._workspace = None
                ws_mod.save_workspace({"layout_preset": "committee"})
                with patch("augur.data.fetch_market_context", return_value=tech_context):
                    with patch.object(
                        DecisionCoordinator, "analyze_with_all", return_value=mock_responses,
                    ):
                        with patch.object(
                            DecisionCoordinator, "get_consensus", return_value=mock_consensus,
                        ):
                            from augur.workflow import run_workflow
                            result = run_workflow("AAPL", steps="")

        assert result["steps"] == ["fetch", "analyze", "consensus", "committee"]


class TestWorkspacePresetsE2E:
    """Round-trip workspace preset API with isolated storage."""

    @pytest.mark.parametrize("preset,expected_page,check_hidden", [
        ("analyst", "/", []),
        ("trader", "/stocks", ["backtest"]),
        ("committee", "/committee", ["scanner"]),
        ("minimal", "/stocks", ["debate"]),
    ])
    def test_apply_preset_via_api(self, dashboard_client, preset, expected_page, check_hidden):
        import augur.workspace as ws_mod
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod._workspace = None
                r = dashboard_client.put("/api/workspace", json={
                    "layout_preset": preset,
                    "default_page": expected_page,
                })
                assert r.status_code == 200
                ws = r.json()["workspace"]
                assert ws["layout_preset"] == preset
                assert ws["default_page"] == expected_page
                for item in check_hidden:
                    assert item in ws["hidden_nav"]

                ws_mod._workspace = None
                r2 = dashboard_client.get("/api/workspace")
                assert r2.status_code == 200
                assert r2.json()["workspace"]["layout_preset"] == preset

    def test_list_presets_endpoint(self, dashboard_client):
        r = dashboard_client.get("/api/workspace/presets")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        for name in ("analyst", "trader", "committee", "minimal"):
            assert name in data["presets"]
            assert "default_page" in data["presets"][name]
            assert "hidden_nav" in data["presets"][name]

    def test_custom_overrides_persist(self, dashboard_client):
        import augur.workspace as ws_mod
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod._workspace = None
                body = {
                    "layout_preset": "trader",
                    "default_ticker": "AAPL",
                    "sidebar_collapsed": True,
                    "enabled_personas": ["buffett", "lynch"],
                }
                r = dashboard_client.put("/api/workspace", json=body)
                assert r.status_code == 200
                ws = r.json()["workspace"]
                assert ws["default_ticker"] == "AAPL"
                assert ws["sidebar_collapsed"] is True
                assert ws["enabled_personas"] == ["buffett", "lynch"]


class TestConsensusWithMockData:
    """Consensus enhancement modules exercised with controlled inputs."""

    def test_industry_weights_for_tech_sector(self):
        from augur.consensus.industry_matrix import get_agent_weights
        weights = get_agent_weights("technology", {})
        assert weights["cathie_wood"] > weights["graham"]
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.01)

    def test_regime_weights_shift_toward_defensive(self):
        from augur.consensus.regime_weights import apply_regime_weights
        base = {"buffett": 0.25, "cathie_wood": 0.25, "marks": 0.25, "graham": 0.25}
        adj = apply_regime_weights(base, "BEAR_HIGH_VOL")
        assert adj["marks"] >= adj["cathie_wood"]
        assert sum(adj.values()) == pytest.approx(1.0, abs=0.01)

    def test_workflow_consensus_reflects_mock_kelly(
        self, tech_context, mock_responses, mock_consensus,
    ):
        with patch("augur.data.fetch_market_context", return_value=tech_context):
            with patch.object(
                DecisionCoordinator, "analyze_with_all", return_value=mock_responses,
            ):
                with patch.object(
                    DecisionCoordinator, "get_consensus", return_value=mock_consensus,
                ):
                    from augur.workflow import run_workflow
                    result = run_workflow("NVDA", steps="consensus")

        c = result["results"]["consensus"]
        assert c["score"] == pytest.approx(7.8)
        assert c["confidence"] == pytest.approx(0.78)
        assert c["kelly_pct"] == pytest.approx(8.5)

    def test_probability_calibrator_bounds(self):
        from augur.consensus.probability_calibrator import calibrate_confidence
        low = calibrate_confidence(2.0, 0.9, "consensus")
        high = calibrate_confidence(9.5, 0.95, "consensus")
        assert 0.05 <= low <= 0.95
        assert 0.05 <= high <= 0.95
        assert high > low


class TestMCPWorkflowValidation:
    """MCP augur_workflow input validation without requiring the mcp package."""

    def test_invalid_ticker_rejected(self):
        from augur.mcp_server import _validate_ticker
        assert _validate_ticker("NVDA;DROP") is not None
        assert _validate_ticker("AAPL") is None

    def test_workflow_value_error_surfaces_as_error_string(self):
        from augur.mcp_server import _validate_ticker

        ticker = "AAPL"
        err = _validate_ticker(ticker)
        assert err is None

        try:
            from augur.workflow import run_workflow
            run_workflow(ticker, steps="not_a_step")
            raised = False
        except ValueError as e:
            raised = True
            message = f"Error: {e}"
        assert raised
        assert "Unknown step" in message

    def test_workflow_summary_returned_on_success(
        self, tech_context, mock_responses, mock_consensus,
    ):
        """Mirror augur_workflow MCP handler: return summary string on success."""
        with patch("augur.data.fetch_market_context", return_value=tech_context):
            with patch.object(
                DecisionCoordinator, "analyze_with_all", return_value=mock_responses,
            ):
                with patch.object(
                    DecisionCoordinator, "get_consensus", return_value=mock_consensus,
                ):
                    from augur.workflow import run_workflow
                    result = run_workflow("NVDA", steps="fetch,consensus")
                    output = result.get("summary", str(result))

        assert isinstance(output, str)
        assert "NVDA" in output
        assert "Consensus" in output
