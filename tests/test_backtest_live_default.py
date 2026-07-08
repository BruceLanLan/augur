# -*- coding: utf-8 -*-
"""Tests for R2: backtest defaults to real data; synthetic data is opt-in and
never silently substituted, and is excluded from IC leaderboard aggregation.

See docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md debt 2 for the full finding:
the dashboard /backtest page and CLI backtest command ran on
generate_sample_data() (hash-seeded synthetic data) by default, and
get_leaderboard()/get_ic_report() aggregated IC across every persisted
record regardless of whether it came from demo or live data — meaning even
after tagging new records, historical demo records already on disk would
permanently contaminate the "IC leaderboard" number forever.
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from augur.backtest import Backtester, BacktestRecord, generate_sample_data
from augur.cli import main


# ---------------------------------------------------------------------------
# Backtester: data_source stamping + live_only filtering
# ---------------------------------------------------------------------------

class TestDataSourceStamping:
    def _tmp_backtester(self, tmpdir):
        bt = Backtester()
        bt.RECORDS_DIR = Path(tmpdir)
        bt.RECORDS_FILE = Path(tmpdir) / "records.jsonl"
        return bt

    def test_run_backtest_default_data_source_is_unknown(self):
        """A caller that doesn't specify data_source gets 'unknown', not a
        false 'live' or 'demo' claim."""
        hist, fwd = generate_sample_data("UNK", days=5)
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            result = bt.run_backtest("UNK", hist, fwd)
        assert all(r.data_source == "unknown" for r in result.records)

    def test_run_backtest_stamps_explicit_data_source(self):
        hist, fwd = generate_sample_data("TAG", days=5)
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            result = bt.run_backtest("TAG", hist, fwd, data_source="demo")
        assert result.records
        assert all(r.data_source == "demo" for r in result.records)

    def test_run_live_backtest_stamps_live(self):
        """run_live_backtest must tag every record data_source='live', since
        that's the whole point of the mechanism — verified via a real call
        through run_backtest with fetch_history/edgar_fundamentals mocked out."""
        prices = [
            {"date": f"2024-01-{i:02d}", "close": 100.0 + i}
            for i in range(1, 31)
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            with patch("augur.data.fetch_history", return_value=prices), \
                 patch("augur.data.calculate_technicals", return_value={"rsi": 50, "macd": 0, "sma20": 100, "sma50": 100}), \
                 patch("augur.consensus.edgar_fundamentals.fetch_edgar_fundamentals",
                       return_value={"insufficient": False, "pe": 20.0}):
                result = bt.run_live_backtest("LIVE", days=5)
        assert result.records
        assert all(r.data_source == "live" for r in result.records)


class TestLeaderboardLiveOnlyFilter:
    def _tmp_backtester(self, tmpdir):
        bt = Backtester()
        bt.RECORDS_DIR = Path(tmpdir)
        bt.RECORDS_FILE = Path(tmpdir) / "records.jsonl"
        return bt

    def test_leaderboard_excludes_demo_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            hist, fwd = generate_sample_data("DEMOONLY", days=5)
            bt.run_backtest("DEMOONLY", hist, fwd, data_source="demo")

            assert bt.get_leaderboard() == []

    def test_leaderboard_excludes_unknown_by_default(self):
        """Legacy records persisted before this field existed (or any bare
        run_backtest() call) must not count either — 'unknown' is not
        'live'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            hist, fwd = generate_sample_data("UNKONLY", days=5)
            bt.run_backtest("UNKONLY", hist, fwd)  # no data_source -> "unknown"

            assert bt.get_leaderboard() == []

    def test_leaderboard_includes_live_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            hist, fwd = generate_sample_data("LIVEONLY", days=5)
            bt.run_backtest("LIVEONLY", hist, fwd, data_source="live")

            assert len(bt.get_leaderboard()) > 0

    def test_live_only_false_includes_everything(self):
        """Escape hatch: live_only=False sees the old (contaminated) behavior
        for debugging/inspection purposes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            hist, fwd = generate_sample_data("MIXED", days=5)
            bt.run_backtest("MIXED", hist, fwd, data_source="demo")

            assert bt.get_leaderboard(live_only=True) == []
            assert len(bt.get_leaderboard(live_only=False)) > 0

    def test_get_ic_report_same_filter_behavior(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            hist, fwd = generate_sample_data("ICDEMO", days=5)
            bt.run_backtest("ICDEMO", hist, fwd, data_source="demo")

            assert bt.get_ic_report() == []
            assert len(bt.get_ic_report(live_only=False)) > 0

    def test_mixed_live_and_demo_only_counts_live(self):
        """A leaderboard built from a mix of demo and live records must
        compute IC using only the live subset — this is the exact
        contamination scenario debt 2 describes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bt = self._tmp_backtester(tmpdir)
            hist, fwd = generate_sample_data("MIX2", days=5)
            bt.run_backtest("MIX2", hist, fwd, data_source="demo")
            hist2, fwd2 = generate_sample_data("MIX2B", days=5)
            bt.run_backtest("MIX2B", hist2, fwd2, data_source="live")

            live_records = bt.load_records()
            live_only_count = sum(1 for r in live_records if r.data_source == "live")
            leaderboard = bt.get_leaderboard()

            total_predictions = sum(a.total_predictions for a in leaderboard)
            assert total_predictions == live_only_count
            assert total_predictions > 0


# ---------------------------------------------------------------------------
# Dashboard API: /api/backtest/run mode routing + no-silent-fallback
# ---------------------------------------------------------------------------

class TestBacktestRunApiMode:
    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        return TestClient(app)

    def _fake_result(self):
        result = MagicMock()
        result.records = []
        result.agent_ics = []
        result.consensus_ic = 0.1
        result.summary = "ok"
        result.ticker = "AAPL"
        return result

    def test_default_mode_is_live(self, client):
        """No mode param -> defaults to live, calls run_live_backtest."""
        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.optional_deps.is_available", return_value=True):
            bt = MockBT.return_value
            bt.run_live_backtest.return_value = self._fake_result()
            resp = client.get("/api/backtest/run?ticker=AAPL&days=30")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "live"
        bt.run_live_backtest.assert_called_once()
        bt.run_backtest.assert_not_called()

    def test_explicit_demo_mode_uses_synthetic_data(self, client):
        with patch("augur.backtest.Backtester") as MockBT:
            bt = MockBT.return_value
            bt.run_backtest.return_value = self._fake_result()
            resp = client.get("/api/backtest/run?ticker=AAPL&days=30&mode=demo")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "demo"
        bt.run_backtest.assert_called_once()
        # data_source="demo" must be threaded through to the persistence layer
        assert bt.run_backtest.call_args.kwargs.get("data_source") == "demo"

    def test_invalid_mode_rejected(self, client):
        resp = client.get("/api/backtest/run?ticker=AAPL&mode=bogus")
        assert resp.status_code == 400

    def test_live_failure_does_not_silently_fall_back_to_demo(self, client):
        """Core of debt 2's fix: a live fetch failure must surface as an
        error response, never silently swap in fake data that looks real."""
        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.optional_deps.is_available", return_value=True):
            bt = MockBT.return_value
            bt.run_live_backtest.side_effect = ValueError("Insufficient data for AAPL")
            resp = client.get("/api/backtest/run?ticker=AAPL&days=30")

        assert resp.status_code != 200
        data = resp.json()
        assert data.get("status") == "error"
        assert "AAPL" in data.get("detail", "")
        bt.run_backtest.assert_not_called()

    def test_live_generic_exception_reported_not_swallowed(self, client):
        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.optional_deps.is_available", return_value=True):
            bt = MockBT.return_value
            bt.run_live_backtest.side_effect = RuntimeError("network timeout")
            resp = client.get("/api/backtest/run?ticker=AAPL&days=30")

        assert resp.status_code != 200
        assert resp.json().get("status") == "error"

    def test_missing_data_extra_returns_not_implemented(self, client):
        with patch("augur.optional_deps.is_available", return_value=False):
            resp = client.get("/api/backtest/run?ticker=AAPL&days=30")

        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# CLI: default live, --demo opt-in, no silent fallback on failure
# ---------------------------------------------------------------------------

class TestBacktestCliDefaults:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def _fake_result(self):
        result = MagicMock()
        result.records = []
        result.summary = "Backtest summary"
        result.consensus_ic = 0.05
        return result

    def test_default_invokes_live_backtest(self, runner):
        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.optional_deps.is_available", return_value=True):
            bt = MockBT.return_value
            bt.run_live_backtest.return_value = self._fake_result()
            result = runner.invoke(main, ["backtest", "AAPL", "--days", "30"])

        assert result.exit_code == 0
        bt.run_live_backtest.assert_called_once()
        bt.run_backtest.assert_not_called()

    def test_demo_flag_skips_live_entirely(self, runner):
        with patch("augur.backtest.Backtester") as MockBT:
            bt = MockBT.return_value
            bt.run_backtest.return_value = self._fake_result()
            result = runner.invoke(main, ["backtest", "AAPL", "--days", "30", "--demo"])

        assert result.exit_code == 0
        bt.run_backtest.assert_called_once()
        assert bt.run_backtest.call_args.kwargs.get("data_source") == "demo"
        assert "演示数据" in result.output

    def test_live_failure_exits_nonzero_without_demo_fallback(self, runner):
        """The old behavior silently fell through to generate_sample_data()
        after printing a warning; the fix must stop and report failure."""
        with patch("augur.backtest.Backtester") as MockBT, \
             patch("augur.optional_deps.is_available", return_value=True), \
             patch("augur.backtest.generate_sample_data") as mock_demo:
            bt = MockBT.return_value
            bt.run_live_backtest.side_effect = RuntimeError("network down")
            result = runner.invoke(main, ["backtest", "AAPL", "--days", "30"])

        assert result.exit_code != 0
        mock_demo.assert_not_called()
        bt.run_backtest.assert_not_called()

    def test_live_and_demo_flags_are_mutually_exclusive(self, runner):
        result = runner.invoke(main, ["backtest", "AAPL", "--live", "--demo"])
        assert result.exit_code != 0

    def test_missing_data_extra_exits_nonzero_without_demo_fallback(self, runner):
        with patch("augur.optional_deps.is_available", return_value=False), \
             patch("augur.backtest.generate_sample_data") as mock_demo:
            result = runner.invoke(main, ["backtest", "AAPL"])

        assert result.exit_code != 0
        mock_demo.assert_not_called()
