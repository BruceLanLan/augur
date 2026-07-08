# -*- coding: utf-8 -*-
"""Tests for R3: LearningEngine outcome-resolution actually closes the loop.

See docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md debt 3. Two distinct bugs
combined to mean ~/.augur/learned_weights.json never existed in production
despite the system running for many versions:

1. (root cause, found during implementation — deeper than the roadmap's
   original plan) record_prediction() never called _save_weights(), so
   every prediction lived only in the in-memory LearningEngine singleton.
   A process restart before an outcome resolved for a ticker (which only
   happens 30+ days later) wiped it — meaning predictions essentially never
   survived long enough to ever be resolved at all.
2. (the roadmap's original finding) even with persistence fixed, resolution
   only ever triggered for whatever ticker happened to be re-analyzed via
   ConsensusEngine.compute() — there was no scheduled sweep, so a ticker
   analyzed once and never revisited could never resolve.
"""
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from augur.learning import LearningEngine
from augur.registry import _check_and_record_outcomes, resolve_pending_outcomes


def _tmp_engine() -> LearningEngine:
    return LearningEngine(weights_path=Path(tempfile.mktemp(suffix=".json")))


# ---------------------------------------------------------------------------
# Root cause: predictions must survive a process restart
# ---------------------------------------------------------------------------

class TestPredictionPersistence:
    def test_record_prediction_persists_to_disk_immediately(self):
        """A single record_prediction() call, with no outcome ever resolved,
        must already be on disk — this is the exact scenario that
        previously left learned_weights.json never created."""
        path = Path(tempfile.mktemp(suffix=".json"))
        engine = LearningEngine(weights_path=path)
        engine.record_prediction("AAPL", "buffett", "bullish", 7.5, 0.8)

        assert path.exists()

    def test_prediction_survives_a_simulated_restart(self):
        """The direct proof of the fix: record a prediction, discard the
        LearningEngine instance (simulating a process exit), construct a
        fresh instance pointed at the same file (simulating a restart), and
        confirm the pending prediction is still there."""
        path = Path(tempfile.mktemp(suffix=".json"))
        engine1 = LearningEngine(weights_path=path)
        engine1.record_prediction("NVDA", "cathie_wood", "bullish", 8.0, 0.7)
        del engine1

        engine2 = LearningEngine(weights_path=path)
        assert engine2.pending_count == 1
        assert engine2.get_pending_tickers() == ["NVDA"]

    def test_multiple_predictions_across_restarts_all_survive(self):
        """Simulates the real usage pattern: analyze a ticker (18 agents
        each record_prediction), restart, analyze another ticker."""
        path = Path(tempfile.mktemp(suffix=".json"))
        engine1 = LearningEngine(weights_path=path)
        for agent_id in ["buffett", "graham", "munger"]:
            engine1.record_prediction("AAPL", agent_id, "bullish", 7.0, 0.6)
        del engine1

        engine2 = LearningEngine(weights_path=path)
        engine2.record_prediction("MSFT", "dalio", "neutral", 5.0, 0.5)
        del engine2

        engine3 = LearningEngine(weights_path=path)
        assert engine3.pending_count == 4
        assert engine3.get_pending_tickers() == ["AAPL", "MSFT"]


class TestSaveWeightsRetentionPolicy:
    def test_pending_predictions_never_pruned_even_over_100(self):
        """150 pending predictions must all survive a save/reload cycle —
        the old `predictions[-100:]` truncation would have silently dropped
        50 of them, each unrecoverable forever."""
        path = Path(tempfile.mktemp(suffix=".json"))
        engine = LearningEngine(weights_path=path)
        now = time.time()
        with engine._lock:
            for i in range(150):
                engine._predictions.append({
                    "ticker": f"T{i}", "agent_id": "buffett",
                    "signal": "bullish", "score": 7.0, "confidence": 0.6,
                    "timestamp": now, "outcome": None,
                })
            engine._save_weights()

        reloaded = LearningEngine(weights_path=path)
        assert reloaded.pending_count == 150

    def test_resolved_predictions_capped_at_100(self):
        path = Path(tempfile.mktemp(suffix=".json"))
        engine = LearningEngine(weights_path=path)
        now = time.time()
        with engine._lock:
            for i in range(150):
                engine._predictions.append({
                    "ticker": f"T{i}", "agent_id": "buffett",
                    "signal": "bullish", "score": 7.0, "confidence": 0.6,
                    "timestamp": now, "outcome": 0.05,
                })
            engine._save_weights()

        reloaded = LearningEngine(weights_path=path)
        assert len(reloaded._predictions) == 100

    def test_mixed_pending_and_resolved_both_handled_correctly(self):
        """120 pending (all must survive) + 150 resolved (capped to 100) —
        the exact scenario the retention policy needs to get right."""
        path = Path(tempfile.mktemp(suffix=".json"))
        engine = LearningEngine(weights_path=path)
        now = time.time()
        with engine._lock:
            for i in range(120):
                engine._predictions.append({
                    "ticker": f"P{i}", "agent_id": "buffett",
                    "signal": "bullish", "score": 7.0, "confidence": 0.6,
                    "timestamp": now, "outcome": None,
                })
            for i in range(150):
                engine._predictions.append({
                    "ticker": f"R{i}", "agent_id": "buffett",
                    "signal": "bullish", "score": 7.0, "confidence": 0.6,
                    "timestamp": now, "outcome": 0.03,
                })
            engine._save_weights()

        reloaded = LearningEngine(weights_path=path)
        assert reloaded.pending_count == 120
        resolved_count = sum(1 for p in reloaded._predictions if p["outcome"] is not None)
        assert resolved_count == 100


class TestGetPendingTickers:
    def test_empty_when_no_predictions(self):
        assert _tmp_engine().get_pending_tickers() == []

    def test_returns_distinct_sorted_tickers(self):
        engine = _tmp_engine()
        engine.record_prediction("MSFT", "buffett", "bullish", 7.0, 0.6)
        engine.record_prediction("AAPL", "graham", "bullish", 6.0, 0.5)
        engine.record_prediction("AAPL", "munger", "neutral", 5.0, 0.5)
        assert engine.get_pending_tickers() == ["AAPL", "MSFT"]

    def test_resolved_tickers_excluded(self):
        engine = _tmp_engine()
        engine.record_prediction("AAPL", "buffett", "bullish", 7.0, 0.6)
        engine.record_outcome("AAPL", 0.05, min_age_days=0)
        assert engine.get_pending_tickers() == []


class TestLastResolutionMetadata:
    def test_none_before_any_sweep(self):
        assert _tmp_engine().last_resolution is None

    def test_record_resolution_run_persists(self):
        path = Path(tempfile.mktemp(suffix=".json"))
        engine = LearningEngine(weights_path=path)
        engine.record_resolution_run(resolved=3, failed=1)

        assert engine.last_resolution["resolved"] == 3
        assert engine.last_resolution["failed"] == 1
        assert "timestamp" in engine.last_resolution

        reloaded = LearningEngine(weights_path=path)
        assert reloaded.last_resolution["resolved"] == 3

    def test_returns_a_copy_not_the_live_dict(self):
        engine = _tmp_engine()
        engine.record_resolution_run(resolved=1, failed=0)
        snapshot = engine.last_resolution
        snapshot["resolved"] = 999
        assert engine.last_resolution["resolved"] == 1


# ---------------------------------------------------------------------------
# _check_and_record_outcomes: per-ticker resolution attempt + reporting
# ---------------------------------------------------------------------------

class TestCheckAndRecordOutcomes:
    def test_no_eligible_predictions_returns_not_attempted(self):
        """A prediction younger than 30 days is not eligible yet."""
        engine = _tmp_engine()
        engine.record_prediction("AAPL", "buffett", "bullish", 7.0, 0.6)
        result = _check_and_record_outcomes(engine, "AAPL")
        assert result == {"attempted": False, "resolved": 0}

    def test_eligible_prediction_resolved_successfully(self):
        engine = _tmp_engine()
        with engine._lock:
            engine._predictions.append({
                "ticker": "AAPL", "agent_id": "buffett", "signal": "bullish",
                "score": 7.0, "confidence": 0.6,
                "timestamp": time.time() - 35 * 86400,  # 35 days old, eligible
                "outcome": None,
            })

        hist = [
            {"date": time.strftime("%Y-%m-%d", time.gmtime(time.time() - d * 86400)),
             "close": 100.0 + (35 - d) * 0.5}
            for d in range(40, -1, -1)
        ]
        with patch("augur.data.fetch_history", return_value=hist):
            result = _check_and_record_outcomes(engine, "AAPL")

        assert result["attempted"] is True
        assert result["resolved"] == 1
        assert engine.pending_count == 0

    def test_fetch_failure_reports_attempted_but_not_resolved(self):
        engine = _tmp_engine()
        with engine._lock:
            engine._predictions.append({
                "ticker": "AAPL", "agent_id": "buffett", "signal": "bullish",
                "score": 7.0, "confidence": 0.6,
                "timestamp": time.time() - 35 * 86400,
                "outcome": None,
            })

        with patch("augur.data.fetch_history", side_effect=RuntimeError("network down")):
            result = _check_and_record_outcomes(engine, "AAPL")

        assert result == {"attempted": True, "resolved": 0}
        assert engine.pending_count == 1  # still pending, not lost

    def test_empty_history_reports_attempted_but_not_resolved(self):
        engine = _tmp_engine()
        with engine._lock:
            engine._predictions.append({
                "ticker": "AAPL", "agent_id": "buffett", "signal": "bullish",
                "score": 7.0, "confidence": 0.6,
                "timestamp": time.time() - 35 * 86400,
                "outcome": None,
            })

        with patch("augur.data.fetch_history", return_value=[]):
            result = _check_and_record_outcomes(engine, "AAPL")

        assert result == {"attempted": True, "resolved": 0}

    def test_never_raises_on_unexpected_exception(self):
        engine = _tmp_engine()
        with engine._lock:
            engine._predictions.append({
                "ticker": "AAPL", "agent_id": "buffett", "signal": "bullish",
                "score": 7.0, "confidence": 0.6,
                "timestamp": time.time() - 35 * 86400,
                "outcome": None,
            })
        with patch("augur.data.fetch_history", side_effect=Exception("boom")):
            result = _check_and_record_outcomes(engine, "AAPL")
        assert result["attempted"] is True
        assert result["resolved"] == 0


# ---------------------------------------------------------------------------
# resolve_pending_outcomes: the sweep across all tickers
# ---------------------------------------------------------------------------

class TestResolvePendingOutcomes:
    def _hist_for(self, days: int = 40) -> list:
        return [
            {"date": time.strftime("%Y-%m-%d", time.gmtime(time.time() - d * 86400)),
             "close": 100.0 + (days - d) * 0.5}
            for d in range(days, -1, -1)
        ]

    def test_no_pending_predictions_is_a_clean_noop(self):
        engine = _tmp_engine()
        result = resolve_pending_outcomes(engine)
        assert result == {"resolved": 0, "failed": 0, "still_pending": 0}

    def test_sweeps_multiple_tickers_and_aggregates(self):
        engine = _tmp_engine()
        old_ts = time.time() - 35 * 86400
        with engine._lock:
            for ticker in ("AAPL", "MSFT"):
                engine._predictions.append({
                    "ticker": ticker, "agent_id": "buffett", "signal": "bullish",
                    "score": 7.0, "confidence": 0.6, "timestamp": old_ts, "outcome": None,
                })

        with patch("augur.data.fetch_history", return_value=self._hist_for()):
            result = resolve_pending_outcomes(engine)

        assert result["resolved"] == 2
        assert result["failed"] == 0
        assert result["still_pending"] == 0

    def test_partial_failure_counted_correctly(self):
        """One ticker resolves, another's fetch fails — both counts must
        reflect reality, not a blanket success/failure."""
        engine = _tmp_engine()
        old_ts = time.time() - 35 * 86400
        with engine._lock:
            engine._predictions.append({
                "ticker": "GOOD", "agent_id": "buffett", "signal": "bullish",
                "score": 7.0, "confidence": 0.6, "timestamp": old_ts, "outcome": None,
            })
            engine._predictions.append({
                "ticker": "BAD", "agent_id": "buffett", "signal": "bullish",
                "score": 7.0, "confidence": 0.6, "timestamp": old_ts, "outcome": None,
            })

        def fake_fetch(ticker, **kw):
            if ticker == "BAD":
                raise RuntimeError("network down")
            return self._hist_for()

        with patch("augur.data.fetch_history", side_effect=fake_fetch):
            result = resolve_pending_outcomes(engine)

        assert result["resolved"] == 1
        assert result["failed"] == 1
        assert result["still_pending"] == 1

    def test_not_yet_eligible_tickers_are_neither_resolved_nor_failed(self):
        """A pending prediction younger than 30 days must not count as a
        'failed' resolution attempt — it just isn't due yet."""
        engine = _tmp_engine()
        engine.record_prediction("FRESH", "buffett", "bullish", 7.0, 0.6)

        result = resolve_pending_outcomes(engine)
        assert result == {"resolved": 0, "failed": 0, "still_pending": 1}

    def test_records_resolution_run_metadata(self):
        engine = _tmp_engine()
        old_ts = time.time() - 35 * 86400
        with engine._lock:
            engine._predictions.append({
                "ticker": "AAPL", "agent_id": "buffett", "signal": "bullish",
                "score": 7.0, "confidence": 0.6, "timestamp": old_ts, "outcome": None,
            })

        with patch("augur.data.fetch_history", return_value=self._hist_for()):
            resolve_pending_outcomes(engine)

        assert engine.last_resolution is not None
        assert engine.last_resolution["resolved"] == 1

    def test_never_raises_even_if_get_pending_tickers_throws(self):
        broken_engine = MagicMock()
        broken_engine.get_pending_tickers.side_effect = RuntimeError("corrupted state")
        broken_engine.pending_count = 0
        result = resolve_pending_outcomes(broken_engine)
        assert result["resolved"] == 0
        assert result["still_pending"] == 0


# ---------------------------------------------------------------------------
# cron integration: the sweep fires on every scheduled/manual watchlist run
# ---------------------------------------------------------------------------

class TestCronIntegration:
    def _make_consensus(self):
        c = MagicMock()
        c.signal = MagicMock()
        c.signal.value = "bullish"
        c.score = 7.0
        c.confidence = 0.75
        c.key_findings = []
        c.risks = []
        return c

    def test_run_watchlist_analysis_triggers_resolution_sweep(self):
        from augur.cron import run_watchlist_analysis
        from augur.personas.base import MarketContext

        config = {
            "watchlist": [{"ticker": "AAPL"}],
            "notifications": {"alert_threshold": 0},
        }
        mock_results = {"agent1": MagicMock(agent_name="Test", signal=MagicMock(value="bullish"), score=7.0)}

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", return_value=MarketContext(ticker="AAPL")), \
             patch("augur.history.save_analysis"), \
             patch("augur.cron._send_notifications"), \
             patch("augur.registry.resolve_pending_outcomes") as mock_resolve:
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.return_value = mock_results
            coord_inst.get_consensus.return_value = self._make_consensus()
            mock_resolve.return_value = {"resolved": 0, "failed": 0, "still_pending": 0}

            run_watchlist_analysis()

        mock_resolve.assert_called_once()

    def test_resolution_sweep_failure_does_not_break_watchlist_run(self):
        """The sweep is a bonus step, not a hard dependency of the primary
        watchlist analysis flow — a failure there must not lose the
        analysis results the user actually asked for."""
        from augur.cron import run_watchlist_analysis
        from augur.personas.base import MarketContext

        config = {
            "watchlist": [{"ticker": "AAPL"}],
            "notifications": {"alert_threshold": 0},
        }
        mock_results = {"agent1": MagicMock(agent_name="Test", signal=MagicMock(value="bullish"), score=7.0)}

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", return_value=MarketContext(ticker="AAPL")), \
             patch("augur.history.save_analysis"), \
             patch("augur.cron._send_notifications"), \
             patch("augur.registry.resolve_pending_outcomes", side_effect=RuntimeError("boom")):
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.return_value = mock_results
            coord_inst.get_consensus.return_value = self._make_consensus()

            results = run_watchlist_analysis()

        assert len(results) == 1
