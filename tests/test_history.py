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


class TestGetRecordFetch:
    def test_get_returns_complete_nested_record(self, use_tmp_history_dir):
        """get_history should return the full record including nested result data,
        not the summary that list_history provides."""
        nested = {
            "consensus": {"signal": "bullish", "score": 9.1},
            "agents": [
                {"agent_id": "buffett", "signal": "bullish", "confidence": 0.9},
                {"agent_id": "wood", "signal": "bullish", "confidence": 0.8},
            ],
            "meta": {"request_id": "abc-123", "duration_ms": 1234},
        }
        history_id = save_analysis("TSLA", nested)

        record = get_history(history_id)
        assert record is not None
        # Full nested structure preserved
        assert record["id"] == history_id
        assert record["ticker"] == "TSLA"
        assert record["result"] == nested
        assert record["result"]["agents"][0]["agent_id"] == "buffett"
        assert record["result"]["meta"]["request_id"] == "abc-123"
        assert "timestamp" in record

    def test_get_rejects_path_traversal(self, use_tmp_history_dir):
        """get_history must guard against path traversal in the ID."""
        # Should not raise, should not escape the history dir
        assert get_history("") is None
        assert get_history("../etc/passwd") is None
        assert get_history("..\\windows\\system32") is None
        assert get_history("foo/../bar") is None
        assert get_history("legit\x00name") is None
        # And nothing was created outside the dir
        assert (use_tmp_history_dir.parent / "bar.json").exists() is False


class TestMalformedJson:
    def test_list_skips_malformed_json(self, use_tmp_history_dir):
        """list_history should silently skip files with invalid JSON."""
        # One valid record
        save_analysis("AAPL", {"consensus": {"signal": "bullish", "score": 7}})
        # One malformed file dropped directly into the history dir
        bad = use_tmp_history_dir / "20990101_000000_000000_BAD.json"
        bad.write_text("{this is : not, valid json,,,", encoding="utf-8")

        records = list_history()
        # Only the well-formed record should be returned
        assert len(records) == 1
        assert records[0]["ticker"] == "AAPL"

    def test_get_returns_none_for_malformed_json(self, use_tmp_history_dir):
        """get_history should return None (not raise) for a malformed JSON file."""
        bad_id = "20990101_000000_000000_BROKEN"
        bad_file = use_tmp_history_dir / f"{bad_id}.json"
        bad_file.write_text("not a json document at all", encoding="utf-8")

        assert get_history(bad_id) is None


class TestHistorySize:
    def test_count_history_reflects_disk(self, use_tmp_history_dir):
        """count_history should reflect the actual number of JSON files on disk."""
        from augur.history import count_history

        assert count_history() == 0
        save_analysis("AAPL", {"consensus": {"signal": "bullish", "score": 7}})
        save_analysis("NVDA", {"consensus": {"signal": "bearish", "score": 3}})
        save_analysis("MSFT", {"consensus": {"signal": "neutral", "score": 5}})

        assert count_history() == 3

        clear_history()
        # After clearing, count drops to zero (cache must be invalidated)
        assert count_history() == 0


class TestDeletePathGuard:
    def test_delete_rejects_path_traversal(self, use_tmp_history_dir):
        """delete_history must guard against path traversal just like get_history."""
        # Nothing should be deleted for any of these IDs
        assert delete_history("") is False
        assert delete_history("../something") is False
        assert delete_history("..\\something") is False
        assert delete_history("a/b") is False
        assert delete_history("foo\x00bar") is False
        # And the real AAPL record we saved must still be intact
        hid = save_analysis("AAPL", {"consensus": {"signal": "bullish", "score": 7}})
        assert delete_history("../AAPL") is False
        # Legitimate delete still works
        assert delete_history(hid) is True
