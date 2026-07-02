# -*- coding: utf-8 -*-
"""Tests for POST /api/watchlist/run — live data + history save behavior."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from dashboard.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _make_consensus(signal="bullish", score=7.0):
    c = MagicMock()
    c.signal = MagicMock()
    c.signal.value = signal
    c.score = score
    c.confidence = 0.75
    c.key_findings = ["finding1"]
    c.metadata = {"position_sizing": {"position_pct": 10}}
    return c


class TestWatchlistRunLiveData:
    """POST /api/watchlist/run uses fetch_market_context and saves history."""

    def test_run_calls_fetch_market_context(self, client):
        """Live data is fetched for each ticker when running watchlist analysis."""
        from augur.personas.base import MarketContext

        fake_config = {"watchlist": [{"ticker": "AAPL"}], "notifications": {}}
        consensus = _make_consensus()
        mock_results = {"a1": MagicMock(signal=MagicMock(value="bullish"))}
        live_ctx = MarketContext(ticker="AAPL", price=180.0, pe=29.0)

        with patch("augur.cron.load_watchlist", return_value=fake_config), \
             patch("augur.data.fetch_market_context", return_value=live_ctx) as mock_fetch, \
             patch("augur.history.save_analysis"), \
             patch("dashboard.routes.watchlist.get_coordinator") as mock_coord, \
             patch("dashboard.routes.watchlist.get_enabled_personas", return_value=None), \
             patch("dashboard.routes.watchlist._get_rules_engine") as mock_engine:
            coord = mock_coord.return_value
            coord.analyze_with_all.return_value = mock_results
            coord.get_consensus.return_value = consensus
            mock_engine.return_value.get_rules.return_value = []

            resp = client.post("/api/watchlist/run")

        assert resp.status_code == 200
        mock_fetch.assert_called_once_with("AAPL")

    def test_manual_metrics_override_live_data(self, client):
        """User-pinned metrics in watchlist.yaml overwrite live context values."""
        from augur.personas.base import MarketContext

        fake_config = {
            "watchlist": [{"ticker": "AAPL", "pe": 55.0}],  # manual pe
            "notifications": {},
        }
        consensus = _make_consensus()
        captured = []

        def fake_analyze(ctx, **kw):
            captured.append(ctx)
            return {"a1": MagicMock(signal=MagicMock(value="bullish"))}

        live_ctx = MarketContext(ticker="AAPL", pe=29.0)

        with patch("augur.cron.load_watchlist", return_value=fake_config), \
             patch("augur.data.fetch_market_context", return_value=live_ctx), \
             patch("augur.history.save_analysis"), \
             patch("dashboard.routes.watchlist.get_coordinator") as mock_coord, \
             patch("dashboard.routes.watchlist.get_enabled_personas", return_value=None), \
             patch("dashboard.routes.watchlist._get_rules_engine") as mock_engine:
            coord = mock_coord.return_value
            coord.analyze_with_all.side_effect = fake_analyze
            coord.get_consensus.return_value = consensus
            mock_engine.return_value.get_rules.return_value = []

            client.post("/api/watchlist/run")

        assert captured[0].pe == 55.0  # manual value wins

    def test_run_saves_history_for_each_ticker(self, client):
        """save_analysis is called once per analyzed ticker."""
        from augur.personas.base import MarketContext

        fake_config = {
            "watchlist": [{"ticker": "AAPL"}, {"ticker": "GOOG"}],
            "notifications": {},
        }
        consensus = _make_consensus()
        mock_results = {"a1": MagicMock(signal=MagicMock(value="neutral"))}

        def fake_fetch(ticker, **kw):
            return MarketContext(ticker=ticker)

        with patch("augur.cron.load_watchlist", return_value=fake_config), \
             patch("augur.data.fetch_market_context", side_effect=fake_fetch), \
             patch("augur.history.save_analysis") as mock_save, \
             patch("dashboard.routes.watchlist.get_coordinator") as mock_coord, \
             patch("dashboard.routes.watchlist.get_enabled_personas", return_value=None), \
             patch("dashboard.routes.watchlist._get_rules_engine") as mock_engine:
            coord = mock_coord.return_value
            coord.analyze_with_all.return_value = mock_results
            coord.get_consensus.return_value = consensus
            mock_engine.return_value.get_rules.return_value = []

            resp = client.post("/api/watchlist/run")

        assert resp.status_code == 200
        assert mock_save.call_count == 2

    def test_run_still_works_when_fetch_fails(self, client):
        """Network failure in fetch_market_context doesn't abort the run."""
        from augur.personas.base import MarketContext

        fake_config = {"watchlist": [{"ticker": "AAPL", "pe": 30.0}], "notifications": {}}
        consensus = _make_consensus()
        mock_results = {"a1": MagicMock(signal=MagicMock(value="bullish"))}

        with patch("augur.cron.load_watchlist", return_value=fake_config), \
             patch("augur.data.fetch_market_context", side_effect=OSError("network down")), \
             patch("augur.history.save_analysis"), \
             patch("dashboard.routes.watchlist.get_coordinator") as mock_coord, \
             patch("dashboard.routes.watchlist.get_enabled_personas", return_value=None), \
             patch("dashboard.routes.watchlist._get_rules_engine") as mock_engine:
            coord = mock_coord.return_value
            coord.analyze_with_all.return_value = mock_results
            coord.get_consensus.return_value = consensus
            mock_engine.return_value.get_rules.return_value = []

            resp = client.post("/api/watchlist/run")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["results"]) == 1


class TestCronRunNowSyncEndpoint:
    """POST /api/cron/run-now must be sync (not async) to avoid blocking event loop."""

    def test_run_now_is_sync_handler(self):
        """api_cron_run_now is a regular sync def, not async def."""
        import inspect
        from dashboard.routes.notifications_cron import api_cron_run_now
        assert not inspect.iscoroutinefunction(api_cron_run_now)
