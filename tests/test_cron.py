# -*- coding: utf-8 -*-
"""Tests for augur.cron module (watchlist management)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch


class TestCron:
    def test_load_watchlist_default(self):
        """Loading watchlist returns default config when file doesn't exist."""
        from augur.cron import load_watchlist

        config = load_watchlist()
        assert isinstance(config, dict)
        assert "watchlist" in config
        assert "schedule" in config

    def test_add_to_watchlist(self):
        """Adding a ticker creates an entry in the watchlist."""
        from augur.cron import add_to_watchlist

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "watchlist.yaml"
            with patch("augur.cron.WATCHLIST_PATH", tmp_path):
                config = add_to_watchlist("AAPL", {"pe": 30})
                assert any(w["ticker"] == "AAPL" for w in config.get("watchlist", []))

    def test_remove_from_watchlist(self):
        """Removing a ticker works correctly."""
        from augur.cron import add_to_watchlist, remove_from_watchlist

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "watchlist.yaml"
            with patch("augur.cron.WATCHLIST_PATH", tmp_path):
                add_to_watchlist("TSLA", None)
                assert remove_from_watchlist("TSLA") is True
                assert remove_from_watchlist("NONEXIST") is False


class TestRunWatchlistAnalysisLiveData:
    """run_watchlist_analysis() uses live data and saves history."""

    def _make_consensus(self, signal="bullish", score=7.0):
        c = MagicMock()
        c.signal = MagicMock()
        c.signal.value = signal
        c.score = score
        c.confidence = 0.75
        c.key_findings = ["finding1"]
        c.risks = []
        c.metadata = {"position_sizing": {"position_pct": 10}}
        return c

    def _make_mock_result(self, signal="neutral", score=5.0):
        """Agent result mock with typed fields (format_consensus_message needs floats)."""
        r = MagicMock()
        r.signal = MagicMock()
        r.signal.value = signal
        r.score = score
        r.agent_name = "TestAgent"
        return r

    def _make_live_ctx(self, ticker="AAPL"):
        from augur.personas.base import MarketContext
        ctx = MarketContext(ticker=ticker, price=150.0, pe=28.0, roe=0.5)
        return ctx

    def test_fetch_market_context_called_for_each_ticker(self):
        """run_watchlist_analysis calls fetch_market_context for each ticker."""
        from augur.cron import run_watchlist_analysis

        live_ctx = self._make_live_ctx("AAPL")
        consensus = self._make_consensus()
        mock_results = {"agent1": self._make_mock_result()}

        config = {
            "watchlist": [{"ticker": "AAPL"}],
            "notifications": {"alert_threshold": 0},
        }

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", return_value=live_ctx) as mock_fetch, \
             patch("augur.history.save_analysis"), \
             patch("augur.cron._send_notifications"):
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.return_value = mock_results
            coord_inst.get_consensus.return_value = consensus

            run_watchlist_analysis()

        mock_fetch.assert_called_once_with("AAPL")

    def test_manual_overrides_win_over_live_data(self):
        """Manual watchlist metrics overwrite live context values."""
        from augur.cron import run_watchlist_analysis
        from augur.personas.base import MarketContext

        live_ctx = MarketContext(ticker="AAPL", pe=28.0)  # live pe=28.0
        consensus = self._make_consensus()
        mock_results = {"agent1": self._make_mock_result()}

        config = {
            "watchlist": [{"ticker": "AAPL", "pe": 99.0}],  # manual pe=99
            "notifications": {"alert_threshold": 0},
        }

        captured_ctx = []

        def fake_analyze(ctx, **kw):
            captured_ctx.append(ctx)
            return mock_results

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", return_value=live_ctx), \
             patch("augur.history.save_analysis"), \
             patch("augur.cron._send_notifications"):
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.side_effect = fake_analyze
            coord_inst.get_consensus.return_value = consensus

            run_watchlist_analysis()

        assert captured_ctx[0].pe == 99.0  # manual value wins

    def test_falls_back_to_manual_metrics_when_fetch_fails(self):
        """When fetch_market_context raises, analysis continues with manual data."""
        from augur.cron import run_watchlist_analysis

        consensus = self._make_consensus()
        mock_results = {"agent1": self._make_mock_result()}

        config = {
            "watchlist": [{"ticker": "FAKE", "pe": 15.0}],
            "notifications": {"alert_threshold": 0},
        }

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", side_effect=RuntimeError("no data")), \
             patch("augur.history.save_analysis"), \
             patch("augur.cron._send_notifications"):
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.return_value = mock_results
            coord_inst.get_consensus.return_value = consensus

            results = run_watchlist_analysis()

        assert len(results) == 1  # analysis still completed

    def test_save_analysis_called_after_each_ticker(self):
        """History is saved for every successfully analyzed ticker."""
        from augur.cron import run_watchlist_analysis
        from augur.personas.base import MarketContext

        consensus = self._make_consensus()
        mock_results = {"agent1": self._make_mock_result()}

        config = {
            "watchlist": [{"ticker": "AAPL"}, {"ticker": "MSFT"}],
            "notifications": {"alert_threshold": 0},
        }

        def fake_fetch(ticker, **kw):
            return MarketContext(ticker=ticker)

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", side_effect=fake_fetch), \
             patch("augur.history.save_analysis") as mock_save, \
             patch("augur.cron._send_notifications"):
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.return_value = mock_results
            coord_inst.get_consensus.return_value = consensus

            run_watchlist_analysis()

        assert mock_save.call_count == 2
        saved_tickers = [c.args[0] for c in mock_save.call_args_list]
        assert "AAPL" in saved_tickers
        assert "MSFT" in saved_tickers

    def test_history_record_has_consensus_shape(self):
        """Saved history record contains consensus key so dashboard can render it."""
        from augur.cron import run_watchlist_analysis
        from augur.personas.base import MarketContext

        consensus = self._make_consensus(signal="bearish", score=3.5)
        mock_results = {"agent1": self._make_mock_result()}
        config = {
            "watchlist": [{"ticker": "AAPL"}],
            "notifications": {"alert_threshold": 0},
        }

        saved_records = []

        def capture_save(ticker, result_dict):
            saved_records.append((ticker, result_dict))

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", return_value=MarketContext(ticker="AAPL")), \
             patch("augur.history.save_analysis", side_effect=capture_save), \
             patch("augur.cron._send_notifications"):
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.return_value = mock_results
            coord_inst.get_consensus.return_value = consensus

            run_watchlist_analysis()

        assert len(saved_records) == 1
        _ticker, result_dict = saved_records[0]
        c = result_dict["consensus"]
        assert c["signal"] == "bearish"
        assert c["score"] == 3.5
