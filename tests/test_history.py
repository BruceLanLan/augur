# -*- coding: utf-8 -*-
"""Tests for augur.history module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from augur.history import (
    HISTORY_DIR,
    clear_history,
    delete_history,
    get_history,
    list_history,
    save_analysis,
)


@pytest.fixture(autouse=True)
def use_tmp_history_dir(tmp_path):
    """Redirect history storage to a temp directory for testing."""
    test_dir = tmp_path / "history"
    test_dir.mkdir()
    with patch("augur.history.HISTORY_DIR", test_dir):
        yield test_dir


class TestSaveAnalysis:
    def test_save_creates_file(self, use_tmp_history_dir):
        """save_analysis should create a JSON file in the history directory."""
        result = {
            "ticker": "AAPL",
            "consensus": {"signal": "bullish", "score": 7.5},
            "agents": [],
        }
        history_id = save_analysis("AAPL", result)

        assert history_id is not None
        assert "AAPL" in history_id

        filepath = use_tmp_history_dir / f"{history_id}.json"
        assert filepath.exists()

        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data["ticker"] == "AAPL"
        assert data["result"]["consensus"]["signal"] == "bullish"

    def test_save_multiple(self, use_tmp_history_dir):
        """Multiple saves should create multiple files."""
        save_analysis("AAPL", {"consensus": {"signal": "bullish", "score": 7}})
        save_analysis("NVDA", {"consensus": {"signal": "bearish", "score": 3}})

        files = list(use_tmp_history_dir.glob("*.json"))
        assert len(files) == 2


class TestListHistory:
    def test_list_empty(self, use_tmp_history_dir):
        """list_history should return empty list when no records exist."""
        records = list_history()
        assert records == []

    def test_list_returns_saved_records(self, use_tmp_history_dir):
        """list_history should return records that were saved."""
        save_analysis("AAPL", {"consensus": {"signal": "bullish", "score": 7.5}})
        save_analysis("NVDA", {"consensus": {"signal": "bearish", "score": 3.2}})

        records = list_history()
        assert len(records) == 2
        # Check structure
        for rec in records:
            assert "id" in rec
            assert "ticker" in rec
            assert "signal" in rec
            assert "score" in rec
            assert "timestamp" in rec

    def test_list_respects_limit(self, use_tmp_history_dir):
        """list_history should respect the limit parameter."""
        for i in range(10):
            save_analysis(f"T{i}", {"consensus": {"signal": "neutral", "score": 5}})

        records = list_history(limit=3)
        assert len(records) == 3


class TestGetHistory:
    def test_get_existing(self, use_tmp_history_dir):
        """get_history should return the full record for a valid ID."""
        history_id = save_analysis("AAPL", {
            "consensus": {"signal": "bullish", "score": 8.0},
            "agents": [{"agent_id": "buffett", "signal": "bullish"}],
        })

        record = get_history(history_id)
        assert record is not None
        assert record["ticker"] == "AAPL"
        assert record["result"]["consensus"]["score"] == 8.0

    def test_get_nonexistent(self, use_tmp_history_dir):
        """get_history should return None for an invalid ID."""
        record = get_history("nonexistent_id_12345")
        assert record is None


class TestClearHistory:
    def test_clear_removes_all(self, use_tmp_history_dir):
        """clear_history should remove all records."""
        save_analysis("AAPL", {"consensus": {"signal": "bullish", "score": 7}})
        save_analysis("NVDA", {"consensus": {"signal": "bearish", "score": 3}})
        save_analysis("MSFT", {"consensus": {"signal": "neutral", "score": 5}})

        count = clear_history()
        assert count == 3

        records = list_history()
        assert len(records) == 0

    def test_clear_empty_dir(self, use_tmp_history_dir):
        """clear_history on empty directory should return 0."""
        count = clear_history()
        assert count == 0


class TestDeleteHistory:
    def test_delete_existing(self, use_tmp_history_dir):
        """delete_history should remove a specific record."""
        id1 = save_analysis("AAPL", {"consensus": {"signal": "bullish", "score": 7}})
        id2 = save_analysis("NVDA", {"consensus": {"signal": "bearish", "score": 3}})

        result = delete_history(id1)
        assert result is True

        # Only id2 should remain
        records = list_history()
        assert len(records) == 1
        assert records[0]["id"] == id2

    def test_delete_nonexistent(self, use_tmp_history_dir):
        """delete_history should return False for a nonexistent ID."""
        result = delete_history("nonexistent_id_12345")
        assert result is False
