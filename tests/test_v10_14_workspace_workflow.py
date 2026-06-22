# -*- coding: utf-8 -*-
"""Tests for v10.14.0: workspace, consensus modules, workflow."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestWorkspace:
    def test_apply_preset_analyst(self):
        from augur.workspace import apply_preset
        ws = apply_preset("analyst")
        assert ws["layout_preset"] == "analyst"
        assert ws["default_page"] == "/"
        assert ws["hidden_nav"] == []

    def test_apply_preset_trader(self):
        from augur.workspace import apply_preset
        ws = apply_preset("trader")
        assert ws["default_page"] == "/stocks"
        assert "backtest" in ws["hidden_nav"]

    def test_save_and_load_workspace(self):
        import augur.workspace as ws_mod
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod._workspace = None
                saved = ws_mod.save_workspace({
                    "layout_preset": "minimal",
                    "default_page": "/stocks",
                    "hidden_nav": ["backtest"],
                })
                assert saved["layout_preset"] == "minimal"
                ws_mod._workspace = None
                loaded = ws_mod.get_workspace()
                assert loaded["default_page"] == "/stocks"
                assert "backtest" in loaded["hidden_nav"]

    def test_list_presets(self):
        from augur.workspace import list_presets
        presets = list_presets()
        assert "analyst" in presets
        assert "trader" in presets
        assert presets["committee"]["default_page"] == "/committee"

    def test_apply_preset_committee(self):
        from augur.workspace import apply_preset
        ws = apply_preset("committee")
        assert ws["layout_preset"] == "committee"
        assert ws["default_page"] == "/committee"
        assert ws["show_ticker_tape"] is False
        assert "scanner" in ws["hidden_nav"]

    def test_apply_preset_minimal(self):
        from augur.workspace import apply_preset
        ws = apply_preset("minimal")
        assert ws["default_page"] == "/stocks"
        assert "debate" in ws["hidden_nav"]
        assert ws["committee_preset"] == "value"

    def test_apply_preset_unknown_falls_back_to_analyst(self):
        from augur.workspace import apply_preset
        ws = apply_preset("nonexistent")
        assert ws["layout_preset"] == "analyst"

    def test_merge_preset_with_custom(self):
        from augur.workspace import merge_preset_with_custom
        ws = merge_preset_with_custom("trader", {"default_ticker": "NVDA", "sidebar_collapsed": True})
        assert ws["layout_preset"] == "trader"
        assert ws["default_ticker"] == "NVDA"
        assert ws["sidebar_collapsed"] is True
        assert ws["default_page"] == "/stocks"

    def test_save_workspace_invalid_page_fallback(self):
        import augur.workspace as ws_mod
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod._workspace = None
                saved = ws_mod.save_workspace({
                    "layout_preset": "analyst",
                    "default_page": "/not-a-real-page",
                })
                assert saved["default_page"] == "/"

    def test_save_workspace_custom_preset(self):
        import augur.workspace as ws_mod
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod._workspace = None
                saved = ws_mod.save_workspace({
                    "layout_preset": "custom",
                    "default_page": "/debate",
                    "hidden_nav": ["scanner"],
                    "enabled_personas": ["buffett", "graham"],
                })
                assert saved["layout_preset"] == "custom"
                assert saved["default_page"] == "/debate"
                assert saved["enabled_personas"] == ["buffett", "graham"]


class TestConsensusModules:
    def test_industry_matrix_weights(self):
        from augur.consensus.industry_matrix import get_agent_weights
        w = get_agent_weights("technology", {})
        assert "cathie_wood" in w
        assert sum(w.values()) == pytest.approx(1.0, abs=0.01)

    def test_regime_weights(self):
        from augur.consensus.regime_weights import apply_regime_weights
        base = {"buffett": 0.5, "marks": 0.5}
        adj = apply_regime_weights(base, "BEAR_LOW_VOL")
        assert sum(adj.values()) == pytest.approx(1.0, abs=0.01)

    def test_probability_calibrator(self):
        from augur.consensus.probability_calibrator import calibrate_confidence
        c = calibrate_confidence(8.0, 0.7, "consensus")
        assert 0.05 <= c <= 0.95

    def test_meta_model_median(self):
        from augur.consensus.meta_model import MetaModel
        mm = MetaModel.load()
        assert mm is not None
        score = mm.predict({"a": 4.0, "b": 6.0, "c": 8.0})
        assert score == 6.0

    def test_macro_features_defaults(self):
        from augur.consensus.macro_features import fetch_macro_features
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = None
            features = fetch_macro_features()
            assert "vix" in features
            assert "regime" in features

    def test_regime_router_normalizes_weights(self):
        from augur.consensus.regime_router import RegimeRouter
        router = RegimeRouter()
        weights = router.get_weights("BEAR_LOW_VOL")
        assert weights
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.01)

    def test_risk_manager_high_vix_reduces_size(self):
        from augur.consensus.risk_manager import RiskManager
        from augur.personas.base import MarketContext, AgentResponse, SignalType

        rm = RiskManager()
        ctx = MarketContext(ticker="TEST", beta_1y=2.0)
        consensus = AgentResponse(
            agent_id="consensus", agent_name="Consensus",
            signal=SignalType.BULLISH, confidence=0.7, score=7.0,
            reasoning="Test", metadata={"position_sizing": {"position_pct": 10.0}},
        )
        verdict = rm.evaluate(ctx, consensus, {}, vix=40.0)
        assert verdict.size_multiplier == 0.5
        adjusted = rm.apply_veto(consensus, verdict)
        assert adjusted.metadata["position_sizing"]["position_pct"] == pytest.approx(5.0)

    def test_rolling_ic_returns_dict(self):
        from augur.consensus.rolling_ic import load_rolling_ic_weights
        weights = load_rolling_ic_weights()
        assert isinstance(weights, dict)


class TestWorkflow:
    def test_run_workflow_minimal(self):
        from augur.personas.base import MarketContext, AgentResponse, SignalType
        from augur.registry import AgentRegistry, DecisionCoordinator

        ctx = MarketContext(ticker="TEST", pe=20, roe=0.15, gross_margins=0.4)
        mock_response = AgentResponse(
            agent_id="buffett", agent_name="Buffett",
            signal=SignalType.BULLISH, confidence=0.8, score=7.0,
            reasoning="Test",
        )

        with patch("augur.data.fetch_market_context", return_value=ctx):
            with patch.object(DecisionCoordinator, "analyze_with_all", return_value={"buffett": mock_response}):
                with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_response):
                    from augur.workflow import run_workflow
                    result = run_workflow("TEST", steps="fetch,consensus")
                    assert result["ticker"] == "TEST"
                    assert "fetch" in result["results"]
                    assert "consensus" in result["results"]
                    assert "summary" in result

    def test_invalid_step_raises(self):
        from augur.workflow import run_workflow
        with pytest.raises(ValueError, match="Unknown step"):
            run_workflow("AAPL", steps="invalid_step")

    def test_run_workflow_committee_step(self):
        from augur.personas.base import MarketContext, AgentResponse, SignalType
        from augur.registry import DecisionCoordinator

        ctx = MarketContext(ticker="TEST", pe=20, roe=0.15, price=100)
        bullish = AgentResponse(
            agent_id="buffett", agent_name="Buffett",
            signal=SignalType.BULLISH, confidence=0.8, score=8.0, reasoning="Quality",
        )
        bearish = AgentResponse(
            agent_id="marks", agent_name="Marks",
            signal=SignalType.BEARISH, confidence=0.7, score=4.0, reasoning="Risk",
        )
        responses = {"buffett": bullish, "marks": bearish}
        consensus = bullish

        with patch("augur.data.fetch_market_context", return_value=ctx):
            with patch.object(DecisionCoordinator, "analyze_with_all", return_value=responses):
                with patch.object(DecisionCoordinator, "get_consensus", return_value=consensus):
                    from augur.workflow import run_workflow
                    result = run_workflow("test", steps="fetch,committee", question="Buy?")
                    assert result["ticker"] == "TEST"
                    committee = result["results"]["committee"]
                    assert committee["question"] == "Buy?"
                    assert committee["vote"]["bullish"] == 1
                    assert committee["vote"]["bearish"] == 1
                    assert len(committee["opinions"]) == 2
                    assert committee["opinions"][0]["score"] >= committee["opinions"][1]["score"]

    def test_run_workflow_selected_agents(self):
        from augur.personas.base import MarketContext, AgentResponse, SignalType
        from augur.registry import AgentRegistry, DecisionCoordinator

        ctx = MarketContext(ticker="TEST", pe=20, roe=0.15, price=100)
        mock_response = AgentResponse(
            agent_id="buffett", agent_name="Buffett",
            signal=SignalType.BULLISH, confidence=0.8, score=7.0, reasoning="Test",
        )

        with patch("augur.data.fetch_market_context", return_value=ctx):
            with patch.object(AgentRegistry, "get_all", return_value=[MagicMock(agent_id="buffett", analyze=lambda c: mock_response)]):
                with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_response):
                    from augur.workflow import run_workflow
                    result = run_workflow("TEST", steps="analyze,consensus", agents="buffett")
                    assert "buffett" in result["results"]["analyze"]
                    assert result["results"]["consensus"]["signal"] == "bullish"

    def test_format_workflow_summary(self):
        from augur.workflow import format_workflow_summary
        summary = format_workflow_summary({
            "ticker": "AAPL",
            "steps": ["fetch", "consensus"],
            "results": {
                "fetch": {"price": 210.0, "pe": 32.0, "sector": "Technology"},
                "consensus": {"signal": "bullish", "score": 7.5, "confidence": 0.8},
            },
        })
        assert "AAPL" in summary
        assert "Consensus" in summary
        assert "BULLISH" in summary


class TestWorkspaceAPI:
    def test_workspace_endpoints(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app

        client = TestClient(app)
        r = client.get("/api/workspace/presets")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "analyst" in data["presets"]

        r2 = client.put("/api/workspace", json={
            "layout_preset": "trader",
            "default_page": "/stocks",
            "hidden_nav": ["backtest"],
        })
        assert r2.status_code == 200
        assert r2.json()["workspace"]["layout_preset"] == "trader"

        r3 = client.get("/api/workspace")
        assert r3.status_code == 200
        assert r3.json()["workspace"]["default_page"] == "/stocks"

    def test_workspace_committee_preset(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app

        client = TestClient(app)
        r = client.put("/api/workspace", json={
            "layout_preset": "committee",
            "default_page": "/committee",
            "show_ticker_tape": False,
        })
        assert r.status_code == 200
        ws = r.json()["workspace"]
        assert ws["layout_preset"] == "committee"
        assert ws["default_page"] == "/committee"
        assert ws["show_ticker_tape"] is False
        assert "scanner" in ws["hidden_nav"]
