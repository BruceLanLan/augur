# -*- coding: utf-8 -*-
"""
Peer review #6 — high-value tests for v10.15 coverage gaps.

Targets untested modules and integration boundaries called out in
docs/reviews/peer-review-06-testing.md.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from augur.personas.base import AgentResponse, MarketContext, SignalType
from augur.registry import DecisionCoordinator


MACRO_STUB = {"regime": "BULL_LOW_VOL", "vix": 14.0}


@pytest.fixture
def isolated_workspace(tmp_path):
    """Patch workspace storage to a temp file and reset cache."""
    import augur.workspace as ws_mod

    path = tmp_path / "workspace.yaml"
    with patch.object(ws_mod, "_workspace_path", return_value=path):
        ws_mod.reset_workspace_cache()
        yield ws_mod, path
        ws_mod.reset_workspace_cache()


class TestFeedbackPaths:
    def test_load_feedback_json_missing_returns_default(self, tmp_path):
        from augur.consensus import paths

        with patch.object(paths, "FEEDBACK_DIR", tmp_path):
            assert paths.load_feedback_json("missing.json") == {}
            assert paths.load_feedback_json("missing.json", default={"x": 1}) == {"x": 1}

    def test_load_feedback_json_invalid_returns_default(self, tmp_path):
        from augur.consensus import paths

        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        with patch.object(paths, "FEEDBACK_DIR", tmp_path):
            assert paths.load_feedback_json("bad.json", default={"fallback": True}) == {"fallback": True}

    def test_load_feedback_json_valid(self, tmp_path):
        from augur.consensus import paths

        payload = {"consensus_weights": {"buffett": 0.6, "marks": 0.4}}
        (tmp_path / "weights.json").write_text(json.dumps(payload), encoding="utf-8")
        with patch.object(paths, "FEEDBACK_DIR", tmp_path):
            assert paths.load_feedback_json("weights.json") == payload


class TestConsensusWeighting:
    def test_build_consensus_weights_tech_favors_growth_agents(self):
        from augur.consensus.weighting import build_consensus_weights

        ctx = MarketContext(
            ticker="NVDA",
            sector="Technology",
            industry="Semiconductors",
        )
        with patch("augur.consensus.weighting.fetch_macro_features", return_value=MACRO_STUB):
            wctx = build_consensus_weights("NVDA", context=ctx)

        assert wctx.industry == "technology"
        assert wctx.weights["cathie_wood"] > wctx.weights["graham"]
        assert sum(wctx.weights.values()) == pytest.approx(1.0, abs=0.01)

    def test_load_global_consensus_weights_nested_key(self, tmp_path):
        from augur.consensus import paths
        from augur.consensus.weighting import load_global_consensus_weights

        data = {"consensus_weights": {"buffett": 0.7, "graham": 0.3}}
        (tmp_path / "weights.json").write_text(json.dumps(data), encoding="utf-8")
        with patch.object(paths, "FEEDBACK_DIR", tmp_path):
            weights = load_global_consensus_weights()

        assert weights["buffett"] == pytest.approx(0.7)
        assert weights["graham"] == pytest.approx(0.3)

    def test_get_consensus_uses_industry_weighting_without_mock(self):
        """Real get_consensus path: only external macro I/O is stubbed."""
        coordinator = DecisionCoordinator()
        ctx = MarketContext(
            ticker="NVDA",
            sector="Technology",
            industry="Semiconductors",
        )
        responses = {
            "cathie_wood": AgentResponse(
                agent_id="cathie_wood",
                agent_name="Wood",
                signal=SignalType.BULLISH,
                confidence=0.9,
                score=9.0,
                reasoning="AI leader",
            ),
            "graham": AgentResponse(
                agent_id="graham",
                agent_name="Graham",
                signal=SignalType.BEARISH,
                confidence=0.8,
                score=3.0,
                reasoning="Overvalued",
            ),
        }
        with patch("augur.consensus.weighting.fetch_macro_features", return_value=MACRO_STUB):
            consensus = coordinator.get_consensus(responses, ticker="NVDA", context=ctx)

        assert consensus.signal == SignalType.BULLISH
        assert consensus.score > 5.0
        assert "technology" in consensus.reasoning.lower() or consensus.score >= 6.0


class TestWorkspaceProfiles:
    def test_create_switch_and_persist_profiles(self, isolated_workspace):
        ws_mod, path = isolated_workspace

        day = ws_mod.create_profile("day-trading", copy_from="default")
        assert day["layout_preset"] == "analyst"

        ws_mod.save_profile("day-trading", {
            "layout_preset": "trader",
            "default_ticker": "SPY",
            "enabled_personas": ["buffett", "marks"],
        })
        active = ws_mod.set_active_profile("day-trading")
        assert active["default_ticker"] == "SPY"
        assert active["enabled_personas"] == ["buffett", "marks"]

        ws_mod.reset_workspace_cache()
        reloaded = ws_mod.get_workspace()
        assert reloaded["layout_preset"] == "trader"
        assert reloaded["enabled_personas"] == ["buffett", "marks"]
        assert path.exists()

    def test_migrate_flat_yaml_to_profiles(self, isolated_workspace):
        ws_mod, path = isolated_workspace
        flat = {
            "layout_preset": "committee",
            "default_page": "/committee",
            "enabled_personas": ["lynch"],
        }
        path.write_text(yaml.safe_dump(flat), encoding="utf-8")
        ws_mod.reset_workspace_cache()

        state = ws_mod.get_workspace_state()
        # Migration happens on load; disk rewrite occurs on next persist.
        assert state["active_profile"] == "default"
        assert state["profiles"]["default"]["layout_preset"] == "committee"
        assert state["profiles"]["default"]["enabled_personas"] == ["lynch"]

        ws_mod.save_workspace(state["profiles"]["default"])
        persisted = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "profiles" in persisted
        assert persisted["active_profile"] == "default"

    def test_export_import_round_trip(self, isolated_workspace):
        ws_mod, _path = isolated_workspace
        ws_mod.save_workspace({
            "layout_preset": "minimal",
            "default_ticker": "QQQ",
            "enabled_personas": ["lynch", "buffett"],
        })
        bundle = ws_mod.export_workspace_bundle()
        ws_mod.save_workspace({"layout_preset": "analyst", "default_ticker": ""})
        imported = ws_mod.import_workspace_bundle(bundle, merge=False)

        assert imported["profiles"]["default"]["layout_preset"] == "minimal"
        assert imported["profiles"]["default"]["default_ticker"] == "QQQ"
        assert ws_mod.get_enabled_personas() == ["lynch", "buffett"]

    def test_resolve_landing_url_precedence(self):
        from augur.workspace import resolve_landing_url

        assert resolve_landing_url({"default_ticker": "aapl", "default_page": "/stocks"}) == "/stocks?ticker=AAPL"
        assert resolve_landing_url({"default_page": "/committee"}) == "/committee"
        assert resolve_landing_url({"default_page": "/"}) is None
        assert resolve_landing_url({}, path="/stocks") is None


class TestWorkspaceProfileAPI:
    def test_profiles_api_lifecycle(self, isolated_workspace):
        ws_mod, _path = isolated_workspace
        from dashboard.app import app

        client = TestClient(app)

        r = client.post("/api/workspace/profiles", json={"name": "research", "copy_from": "default"})
        assert r.status_code == 200
        body = r.json()
        assert body["profile"] == "research"
        assert body["workspace"]["layout_preset"] == "analyst"

        r = client.put("/api/workspace/active", json={"profile": "research"})
        assert r.status_code == 200
        assert r.json()["active_profile"] == "research"

        r = client.put("/api/workspace", json={
            "layout_preset": "committee",
            "enabled_personas": ["buffett", "graham"],
        })
        assert r.status_code == 200
        assert r.json()["workspace"]["enabled_personas"] == ["buffett", "graham"]

        r = client.get("/api/workspace/profiles")
        assert r.status_code == 200
        names = {p["name"] for p in r.json()["profiles"]}
        assert "research" in names
        assert r.json()["active_profile"] == "research"

    def test_put_non_active_profile_without_switching(self, isolated_workspace):
        ws_mod, _path = isolated_workspace
        from dashboard.app import app

        client = TestClient(app)
        client.post("/api/workspace/profiles", json={"name": "research"})
        client.put("/api/workspace", json={"layout_preset": "trader", "default_ticker": "SPY"})

        r = client.put("/api/workspace/profiles/research", json={
            "layout_preset": "minimal",
            "default_ticker": "QQQ",
        })
        assert r.status_code == 200
        assert r.json()["profile"] == "research"
        assert r.json()["workspace"]["default_ticker"] == "QQQ"
        assert r.json()["active"] is False

        active = client.get("/api/workspace").json()["workspace"]
        assert active["layout_preset"] == "trader"
        assert active["default_ticker"] == "SPY"

        research = client.get("/api/workspace/profiles/research").json()["workspace"]
        assert research["layout_preset"] == "minimal"
        assert research["default_ticker"] == "QQQ"


class TestWorkspaceWorkflowIntegration:
    def test_workflow_reads_workspace_enabled_personas(self, isolated_workspace):
        """run_workflow passes workspace persona filter when --agents is omitted."""
        ws_mod, _path = isolated_workspace
        ws_mod.save_workspace({
            "layout_preset": "analyst",
            "enabled_personas": ["buffett"],
        })

        ctx = MarketContext(ticker="TEST", sector="Technology", price=100)
        captured = {}

        def spy_analyze(self, context, enabled_personas=None):
            captured["enabled_personas"] = enabled_personas
            return {
                "buffett": AgentResponse(
                    agent_id="buffett",
                    agent_name="Buffett",
                    signal=SignalType.BULLISH,
                    confidence=0.8,
                    score=7.0,
                    reasoning="mock",
                )
            }

        mock_consensus = AgentResponse(
            agent_id="consensus",
            agent_name="Consensus",
            signal=SignalType.BULLISH,
            confidence=0.7,
            score=7.0,
            reasoning="mock",
        )

        with patch("augur.data.fetch_market_context", return_value=ctx):
            with patch.object(DecisionCoordinator, "analyze_with_all", spy_analyze):
                with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_consensus):
                    from augur.workflow import run_workflow
                    result = run_workflow("TEST", steps="fetch,analyze,consensus")

        assert captured["enabled_personas"] == ["buffett"]
        assert result.get("agents_filter") == ["buffett"]
        assert ws_mod.get_enabled_personas() == ["buffett"]

    def test_workflow_agents_param_overrides_default_behavior(self):
        """CLI --agents path is wired; explicit subset reaches analyze_with_all."""
        ctx = MarketContext(ticker="TEST", price=50)
        registry_agents = []

        class FakeAgent:
            def __init__(self, agent_id):
                self.agent_id = agent_id
                self.name = agent_id.title()

            def analyze(self, _ctx):
                return AgentResponse(
                    agent_id=self.agent_id,
                    agent_name=self.name,
                    signal=SignalType.NEUTRAL,
                    confidence=0.5,
                    score=5.0,
                    reasoning="fake",
                )

        from augur.registry import AgentRegistry

        fake = FakeAgent("buffett")
        mock_consensus = AgentResponse(
            agent_id="consensus",
            agent_name="Consensus",
            signal=SignalType.NEUTRAL,
            confidence=0.5,
            score=5.0,
            reasoning="mock",
        )

        with patch("augur.data.fetch_market_context", return_value=ctx):
            with patch.object(AgentRegistry, "get_all", return_value=[fake]):
                with patch.object(DecisionCoordinator, "get_consensus", return_value=mock_consensus):
                    from augur.workflow import run_workflow
                    result = run_workflow("TEST", steps="analyze", agents="buffett")

        assert set(result["results"]["analyze"].keys()) == {"buffett"}
