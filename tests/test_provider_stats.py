# -*- coding: utf-8 -*-
"""Tests for augur.provider_stats -- local history for `augur doctor`'s
data-source connectivity checks (see D2 in
docs/FUTURE_DIRECTIONS_BRAINSTORM_2026-07.md)."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from augur import provider_stats


@pytest.fixture
def stats_path(tmp_path):
    return tmp_path / "provider_stats.json"


class TestRecordAndSummary:
    def test_empty_summary_when_no_file(self, stats_path):
        assert provider_stats.summary(path=stats_path) == {}

    def test_single_success_recorded(self, stats_path):
        provider_stats.record("yfinance", ok=True, path=stats_path)
        assert provider_stats.summary(path=stats_path) == {"yfinance": {"ok": 1, "fail": 0}}

    def test_single_failure_recorded(self, stats_path):
        provider_stats.record("stooq", ok=False, path=stats_path)
        assert provider_stats.summary(path=stats_path) == {"stooq": {"ok": 0, "fail": 1}}

    def test_multiple_calls_accumulate(self, stats_path):
        provider_stats.record("yfinance", ok=True, path=stats_path)
        provider_stats.record("yfinance", ok=True, path=stats_path)
        provider_stats.record("yfinance", ok=False, path=stats_path)
        assert provider_stats.summary(path=stats_path) == {"yfinance": {"ok": 2, "fail": 1}}

    def test_multiple_providers_tracked_independently(self, stats_path):
        provider_stats.record("yfinance", ok=True, path=stats_path)
        provider_stats.record("stooq", ok=False, path=stats_path)
        result = provider_stats.summary(path=stats_path)
        assert result["yfinance"] == {"ok": 1, "fail": 0}
        assert result["stooq"] == {"ok": 0, "fail": 1}

    def test_persists_to_disk_as_json(self, stats_path):
        provider_stats.record("yfinance", ok=True, path=stats_path)
        assert stats_path.exists()
        data = json.loads(stats_path.read_text(encoding="utf-8"))
        assert "yfinance" in data


class TestRecordBatch:
    """record_batch() does one read-modify-write for N outcomes instead of
    N separate read-modify-writes (see D2 review follow-up, 2026-07-16)."""

    def test_batch_of_one_matches_record(self, stats_path):
        result = provider_stats.record_batch([("yfinance", True)], path=stats_path)
        assert result == {"yfinance": {"ok": 1, "fail": 0}}
        assert provider_stats.summary(path=stats_path) == {"yfinance": {"ok": 1, "fail": 0}}

    def test_batch_of_several_providers_in_one_call(self, stats_path):
        result = provider_stats.record_batch(
            [("yfinance", True), ("stooq", False), ("finnhub", True)], path=stats_path
        )
        assert result == {
            "yfinance": {"ok": 1, "fail": 0},
            "stooq": {"ok": 0, "fail": 1},
            "finnhub": {"ok": 1, "fail": 0},
        }

    def test_batch_return_value_matches_disk_state(self, stats_path):
        result = provider_stats.record_batch([("yfinance", True), ("yfinance", False)], path=stats_path)
        assert result == provider_stats.summary(path=stats_path)

    def test_only_one_write_for_whole_batch(self, stats_path, monkeypatch):
        write_calls = []
        original_write_text = type(stats_path).write_text

        def _counting_write_text(self, *args, **kwargs):
            write_calls.append(1)
            return original_write_text(self, *args, **kwargs)

        monkeypatch.setattr(type(stats_path), "write_text", _counting_write_text)
        provider_stats.record_batch(
            [("yfinance", True), ("stooq", False), ("finnhub", True), ("alphavantage", False)],
            path=stats_path,
        )
        assert len(write_calls) == 1

    def test_empty_batch_still_returns_current_summary(self, stats_path):
        provider_stats.record("yfinance", ok=True, path=stats_path)
        result = provider_stats.record_batch([], path=stats_path)
        assert result == {"yfinance": {"ok": 1, "fail": 0}}

    def test_batch_accumulates_with_prior_record_calls(self, stats_path):
        provider_stats.record("yfinance", ok=True, path=stats_path)
        result = provider_stats.record_batch([("yfinance", True)], path=stats_path)
        assert result == {"yfinance": {"ok": 2, "fail": 0}}

    def test_survives_corrupt_json_and_unwritable_path(self, stats_path):
        stats_path.write_text("not valid json {{{", encoding="utf-8")
        result = provider_stats.record_batch([("yfinance", True)], path=stats_path)
        assert result == {"yfinance": {"ok": 1, "fail": 0}}

    def test_write_failure_returns_empty_dict_not_raise(self, tmp_path):
        bad_path = tmp_path / "nonexistent_dir" / "sub" / "provider_stats.json"
        result = provider_stats.record_batch([("yfinance", True)], path=bad_path)  # must not raise
        assert result == {}


class TestPruning:
    def test_entries_older_than_retention_window_are_dropped(self, stats_path):
        stale_day = (datetime.now(timezone.utc) - timedelta(days=provider_stats.RETENTION_DAYS + 5)).strftime("%Y-%m-%d")
        stats_path.write_text(
            json.dumps({"yfinance": {stale_day: {"ok": 10, "fail": 0}}}), encoding="utf-8"
        )
        assert provider_stats.summary(path=stats_path) == {}

    def test_recent_entries_survive_pruning(self, stats_path):
        recent_day = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        stats_path.write_text(
            json.dumps({"yfinance": {recent_day: {"ok": 3, "fail": 1}}}), encoding="utf-8"
        )
        assert provider_stats.summary(path=stats_path) == {"yfinance": {"ok": 3, "fail": 1}}

    def test_mixed_stale_and_recent_only_recent_counted(self, stats_path):
        stale_day = (datetime.now(timezone.utc) - timedelta(days=provider_stats.RETENTION_DAYS + 3)).strftime("%Y-%m-%d")
        recent_day = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        stats_path.write_text(
            json.dumps(
                {"yfinance": {stale_day: {"ok": 100, "fail": 0}, recent_day: {"ok": 2, "fail": 0}}}
            ),
            encoding="utf-8",
        )
        assert provider_stats.summary(path=stats_path) == {"yfinance": {"ok": 2, "fail": 0}}

    def test_pruning_happens_on_write_not_just_read(self, stats_path):
        stale_day = (datetime.now(timezone.utc) - timedelta(days=provider_stats.RETENTION_DAYS + 5)).strftime("%Y-%m-%d")
        stats_path.write_text(
            json.dumps({"yfinance": {stale_day: {"ok": 10, "fail": 0}}}), encoding="utf-8"
        )
        provider_stats.record("yfinance", ok=True, path=stats_path)
        on_disk = json.loads(stats_path.read_text(encoding="utf-8"))
        assert stale_day not in on_disk.get("yfinance", {})


class TestNeverRaises:
    def test_record_survives_corrupt_json_on_disk(self, stats_path):
        stats_path.write_text("not valid json {{{", encoding="utf-8")
        provider_stats.record("yfinance", ok=True, path=stats_path)  # must not raise
        assert provider_stats.summary(path=stats_path) == {"yfinance": {"ok": 1, "fail": 0}}

    def test_summary_survives_corrupt_json_on_disk(self, stats_path):
        stats_path.write_text("not valid json {{{", encoding="utf-8")
        assert provider_stats.summary(path=stats_path) == {}

    def test_record_survives_unwritable_path(self, tmp_path):
        bad_path = tmp_path / "nonexistent_dir" / "sub" / "provider_stats.json"
        # Parent directory doesn't exist and record() must not create it blindly
        # nor raise -- it should just silently fail to persist.
        provider_stats.record("yfinance", ok=True, path=bad_path)  # must not raise
