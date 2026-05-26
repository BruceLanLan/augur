# -*- coding: utf-8 -*-
"""Tests for augur.cron module (watchlist management)."""

import tempfile
from pathlib import Path
from unittest.mock import patch


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
