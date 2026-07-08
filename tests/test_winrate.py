# -*- coding: utf-8 -*-
"""Tests for Feature C: Historical Win Rate (live LearningEngine accuracy exposure)."""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# LearningEngine.pending_count property
# ---------------------------------------------------------------------------

class TestPendingCount:
    """LearningEngine.pending_count returns unresolved prediction count."""

    def _make_engine_with_predictions(self, resolved: int, pending: int):
        import tempfile, time
        from pathlib import Path
        from augur.learning import LearningEngine

        engine = LearningEngine(weights_path=Path(tempfile.mktemp(suffix=".json")))
        now = time.time()
        for _ in range(resolved):
            engine._predictions.append({
                "ticker": "AAPL", "agent_id": "buffett",
                "signal": "bullish", "score": 7.0, "confidence": 0.7,
                "timestamp": now - 40 * 86400,
                "outcome": 0.05,  # resolved
            })
        for _ in range(pending):
            engine._predictions.append({
                "ticker": "AAPL", "agent_id": "buffett",
                "signal": "bullish", "score": 7.0, "confidence": 0.7,
                "timestamp": now,
                "outcome": None,  # unresolved
            })
        return engine

    def test_zero_when_no_predictions(self):
        import tempfile
        from pathlib import Path
        from augur.learning import LearningEngine
        engine = LearningEngine(weights_path=Path(tempfile.mktemp(suffix=".json")))
        assert engine.pending_count == 0

    def test_all_pending(self):
        engine = self._make_engine_with_predictions(resolved=0, pending=5)
        assert engine.pending_count == 5

    def test_mixed_resolved_and_pending(self):
        engine = self._make_engine_with_predictions(resolved=3, pending=2)
        assert engine.pending_count == 2

    def test_all_resolved_gives_zero(self):
        engine = self._make_engine_with_predictions(resolved=4, pending=0)
        assert engine.pending_count == 0


# ---------------------------------------------------------------------------
# /api/backtest/leaderboard — live accuracy enrichment
# ---------------------------------------------------------------------------

class TestLeaderboardWinRate:
    """GET /api/backtest/leaderboard merges LearningEngine accuracy into items."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        return TestClient(app)

    def _mock_leaderboard_item(self, agent_id="buffett", hit_rate=0.55, total=20):
        item = MagicMock()
        item.agent_id = agent_id  # route code reads a.agent_id directly, not just via to_dict()
        item.to_dict.return_value = {
            "agent_id": agent_id,
            "hit_rate": hit_rate,
            "total_predictions": total,
            "correct_predictions": int(hit_rate * total),
            "ic_60d": 0.12,
            "ic_20d": 0.08,
            "ic_5d": 0.05,
            "avg_score_when_right": 7.0,
            "avg_score_when_wrong": 4.0,
        }
        return item

    def test_pending_count_in_response_when_no_data(self, client):
        """pending_count=0 and has_live_accuracy=False when LearningEngine is empty."""
        mock_le = MagicMock()
        mock_le.get_accuracy.return_value = {}
        mock_le.pending_count = 0
        mock_le.last_resolution = None

        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", return_value=mock_le):
            bt = MockBT.return_value
            bt.get_leaderboard.return_value = []
            resp = client.get("/api/backtest/leaderboard")

        assert resp.status_code == 200
        data = resp.json()
        assert "pending_count" in data
        assert data["pending_count"] == 0
        assert data["has_live_accuracy"] is False

    def test_live_accuracy_merged_into_leaderboard_item(self, client):
        """When LearningEngine has accuracy for an agent, it overwrites hit_rate."""
        mock_le = MagicMock()
        mock_le.get_accuracy.return_value = {
            "buffett": {
                "accuracy_rate": 0.72,
                "total_predictions": 25,
                "correct_predictions": 18,
                "ic": 0.34,
            }
        }
        mock_le.pending_count = 3
        mock_le.last_resolution = None

        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", return_value=mock_le):
            bt = MockBT.return_value
            bt.get_leaderboard.return_value = [self._mock_leaderboard_item("buffett", 0.55, 20)]
            resp = client.get("/api/backtest/leaderboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_live_accuracy"] is True
        assert data["pending_count"] == 3
        items = data["leaderboard"]
        assert len(items) == 1
        buffett = items[0]
        assert buffett["accuracy"] == pytest.approx(0.72, abs=0.001)
        assert buffett["total_predictions"] == 25
        assert buffett["correct_predictions"] == 18
        assert buffett["live_accuracy"] is True

    def test_agent_without_live_accuracy_keeps_backtest_hit_rate(self, client):
        """Agent not in LearningEngine keeps backtest hit_rate unchanged."""
        mock_le = MagicMock()
        mock_le.get_accuracy.return_value = {}  # no live data
        mock_le.pending_count = 0
        mock_le.last_resolution = None

        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", return_value=mock_le):
            bt = MockBT.return_value
            bt.get_leaderboard.return_value = [self._mock_leaderboard_item("marks", 0.61, 15)]
            resp = client.get("/api/backtest/leaderboard")

        assert resp.status_code == 200
        items = resp.json()["leaderboard"]
        assert len(items) == 1
        marks = items[0]
        # live_accuracy flag absent or False — backtest hit_rate is untouched
        assert marks.get("live_accuracy") is not True
        assert marks["hit_rate"] == pytest.approx(0.61, abs=0.001)

    def test_learning_engine_error_does_not_break_endpoint(self, client):
        """If LearningEngine import fails, leaderboard still works (graceful degradation)."""
        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", side_effect=RuntimeError("no engine")):
            bt = MockBT.return_value
            bt.get_leaderboard.return_value = [self._mock_leaderboard_item("buffett")]
            resp = client.get("/api/backtest/leaderboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["pending_count"] == 0
        assert data["has_live_accuracy"] is False

    def test_multiple_agents_mixed_live_and_backtest(self, client):
        """Partial live accuracy: only agents with outcomes get live_ flag."""
        mock_le = MagicMock()
        mock_le.get_accuracy.return_value = {
            "buffett": {"accuracy_rate": 0.80, "total_predictions": 10, "correct_predictions": 8, "ic": 0.5},
        }
        mock_le.pending_count = 2
        mock_le.last_resolution = None

        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", return_value=mock_le):
            bt = MockBT.return_value
            bt.get_leaderboard.return_value = [
                self._mock_leaderboard_item("buffett", 0.55, 20),
                self._mock_leaderboard_item("marks", 0.60, 15),
            ]
            resp = client.get("/api/backtest/leaderboard")

        items = {i["agent_id"]: i for i in resp.json()["leaderboard"]}
        assert items["buffett"]["live_accuracy"] is True
        assert items["buffett"]["accuracy"] == pytest.approx(0.80, abs=0.001)
        assert items["marks"].get("live_accuracy") is not True

    def test_agent_with_only_live_accuracy_gets_synthesized_row(self, client):
        """An agent with real LearningEngine predictions/outcomes but no
        backtest history (e.g. a brand-new persona) gets a synthesized
        leaderboard row rather than being silently dropped — flagged
        live_only=True and IC fields zeroed (never measured, not "measured
        as zero") so the frontend can distinguish the two cases.
        """
        mock_le = MagicMock()
        mock_le.get_accuracy.return_value = {
            "brand_new_persona": {
                "accuracy_rate": 0.90, "total_predictions": 5,
                "correct_predictions": 4, "ic": 0.6,
            },
        }
        mock_le.pending_count = 0
        mock_le.last_resolution = None

        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", return_value=mock_le):
            bt = MockBT.return_value
            bt.get_leaderboard.return_value = [self._mock_leaderboard_item("buffett", 0.55, 20)]
            resp = client.get("/api/backtest/leaderboard")

        data = resp.json()
        assert data["has_live_accuracy"] is True
        assert data["count"] == 2
        items = {i["agent_id"]: i for i in data["leaderboard"]}
        assert set(items.keys()) == {"buffett", "brand_new_persona"}

        synth = items["brand_new_persona"]
        assert synth["live_only"] is True
        assert synth["live_accuracy"] is True
        assert synth["accuracy"] == pytest.approx(0.90, abs=0.001)
        assert synth["total_predictions"] == 5
        assert synth["correct_predictions"] == 4
        assert synth["ic_60d"] == 0.0
        assert synth["agent_name"]  # falls back to agent_id when not in registry

        # The real backtested agent is untouched and NOT flagged live_only
        assert items["buffett"].get("live_only") is not True

    def test_agent_with_only_live_accuracy_uses_registry_name(self, client):
        """When the live-only agent_id IS in the persona registry, its real
        display name is used instead of falling back to the raw agent_id."""
        mock_agent = MagicMock()
        mock_agent.name = "Warren Buffett"
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        mock_le = MagicMock()
        mock_le.get_accuracy.return_value = {
            "buffett": {"accuracy_rate": 0.7, "total_predictions": 4, "correct_predictions": 3, "ic": 0.2},
        }
        mock_le.pending_count = 0
        mock_le.last_resolution = None

        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", return_value=mock_le), \
             patch("dashboard.routes.backtest.get_registry", return_value=mock_registry):
            bt = MockBT.return_value
            bt.get_leaderboard.return_value = []  # nothing backtested yet
            resp = client.get("/api/backtest/leaderboard")

        data = resp.json()
        assert len(data["leaderboard"]) == 1
        assert data["leaderboard"][0]["agent_name"] == "Warren Buffett"


class TestLastResolutionField:
    """/api/backtest/leaderboard exposes LearningEngine.last_resolution for
    dashboard visibility into the R3 outcome-resolution sweep (see
    docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md debt 3 / augur.registry.
    resolve_pending_outcomes)."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        return TestClient(app)

    def test_last_resolution_null_when_sweep_never_ran(self, client):
        mock_le = MagicMock()
        mock_le.get_accuracy.return_value = {}
        mock_le.pending_count = 0
        mock_le.last_resolution = None

        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", return_value=mock_le):
            MockBT.return_value.get_leaderboard.return_value = []
            resp = client.get("/api/backtest/leaderboard")

        assert resp.json()["last_resolution"] is None

    def test_last_resolution_reflects_most_recent_sweep(self, client):
        mock_le = MagicMock()
        mock_le.get_accuracy.return_value = {}
        mock_le.pending_count = 4
        mock_le.last_resolution = {"timestamp": 1750000000.0, "resolved": 6, "failed": 1}

        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.registry._get_learning_engine", return_value=mock_le):
            MockBT.return_value.get_leaderboard.return_value = []
            resp = client.get("/api/backtest/leaderboard")

        data = resp.json()["last_resolution"]
        assert data["resolved"] == 6
        assert data["failed"] == 1
        assert data["timestamp"] == pytest.approx(1750000000.0)
