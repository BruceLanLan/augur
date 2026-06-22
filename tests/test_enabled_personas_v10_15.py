# -*- coding: utf-8 -*-
"""Tests for v10.15: workspace enabled_personas filtering in analyze_with_all."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from augur.personas.base import AgentResponse, MarketContext, SignalType
from augur.registry import AgentRegistry, DecisionCoordinator


BUILTIN_IDS = [
    "buffett", "graham", "lynch", "dalio", "munger",
    "soros", "marks", "cathie_wood", "fisher", "arps",
    "aschenbrenner", "dayu", "thiel",
    "duan_yongping", "zhang_lei", "li_lu", "dan_bin",
    "serenity",
]


def _mock_response(agent_id: str) -> AgentResponse:
    return AgentResponse(
        agent_id=agent_id,
        agent_name=agent_id.title(),
        signal=SignalType.NEUTRAL,
        confidence=0.5,
        score=5.0,
        reasoning="mock",
    )


class TestAnalyzeWithAllPersonaFilter:
    def test_empty_list_runs_all_agents(self):
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="AAPL")

        with patch.object(DecisionCoordinator, "_analyze_single", side_effect=lambda a, c: _mock_response(a.agent_id)):
            results_none = coordinator.analyze_with_all(ctx)
            results_empty = coordinator.analyze_with_all(ctx, enabled_personas=[])

        assert set(results_none.keys()) == set(results_empty.keys())
        assert len(results_none) >= 18

    def test_subset_runs_only_selected(self):
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="AAPL")
        subset = ["buffett", "graham", "lynch"]

        with patch.object(DecisionCoordinator, "_analyze_single", side_effect=lambda a, c: _mock_response(a.agent_id)):
            results = coordinator.analyze_with_all(ctx, enabled_personas=subset)

        assert set(results.keys()) == set(subset)

    def test_unknown_ids_are_ignored(self):
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="AAPL")

        with patch.object(DecisionCoordinator, "_analyze_single", side_effect=lambda a, c: _mock_response(a.agent_id)):
            results = coordinator.analyze_with_all(
                ctx, enabled_personas=["buffett", "not_a_real_agent"],
            )

        assert set(results.keys()) == {"buffett"}

    def test_all_unknown_ids_returns_empty(self):
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="AAPL")

        with patch.object(DecisionCoordinator, "_analyze_single", side_effect=lambda a, c: _mock_response(a.agent_id)):
            results = coordinator.analyze_with_all(ctx, enabled_personas=["fake_one", "fake_two"])

        assert results == {}


class TestWorkspaceEnabledPersonas:
    def test_get_enabled_personas_default_empty(self):
        import augur.workspace as ws_mod

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod.reset_workspace_cache()
                assert ws_mod.get_enabled_personas() == []

    def test_get_enabled_personas_persisted(self):
        import augur.workspace as ws_mod

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod.reset_workspace_cache()
                ws_mod.save_workspace({
                    "layout_preset": "analyst",
                    "enabled_personas": ["buffett", "graham"],
                })
                ws_mod.reset_workspace_cache()
                assert ws_mod.get_enabled_personas() == ["buffett", "graham"]

    def test_save_workspace_strips_invalid_persona_entries(self):
        import augur.workspace as ws_mod

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod.reset_workspace_cache()
                saved = ws_mod.save_workspace({
                    "layout_preset": "analyst",
                    "enabled_personas": ["buffett", 123, None, "graham"],
                })
                assert saved["enabled_personas"] == ["buffett", "graham"]


class TestDashboardEnabledPersonas:
    def test_analyze_endpoint_passes_workspace_personas(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app

        mock_response = _mock_response("buffett")
        captured = {}

        mock_coord = MagicMock()
        mock_coord.analyze_with_all.side_effect = lambda ctx, enabled_personas=None: (
            captured.update({"enabled_personas": enabled_personas}) or {"buffett": mock_response}
        )
        mock_coord.get_consensus.return_value = mock_response

        with patch("dashboard.app.get_enabled_personas", return_value=["buffett", "graham"]):
            with patch("dashboard.app.get_coordinator", return_value=mock_coord):
                client = TestClient(app)
                r = client.get("/api/analyze/TEST?auto_fetch=false&price=100")

        assert r.status_code == 200
        assert captured["enabled_personas"] == ["buffett", "graham"]
        mock_coord.analyze_with_all.assert_called_once()

    def test_workspace_save_and_read_enabled_personas(self):
        import augur.workspace as ws_mod
        from fastapi.testclient import TestClient
        from dashboard.app import app

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workspace.yaml"
            with patch.object(ws_mod, "_workspace_path", return_value=path):
                ws_mod.reset_workspace_cache()
                client = TestClient(app)
                r = client.put("/api/workspace", json={
                    "layout_preset": "analyst",
                    "enabled_personas": BUILTIN_IDS[:3],
                })
                assert r.status_code == 200
                assert r.json()["workspace"]["enabled_personas"] == BUILTIN_IDS[:3]

                ws_mod.reset_workspace_cache()
                assert ws_mod.get_enabled_personas() == BUILTIN_IDS[:3]
