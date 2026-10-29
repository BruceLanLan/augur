# -*- coding: utf-8 -*-
"""v12 earnings flywheel: watchlist shape + real dossier readiness sources."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from augur import cron
from augur.earnings import EarningsEventService, EarningsEvent
from augur.guidance_tracker import GuidanceRecord, GuidanceTracker
from augur.run_tracker import RunTracker
from augur.schemas.step_result import StepStatus


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cron, "WATCHLIST_PATH", tmp_path / "watchlist.yaml")
    return tmp_path


def _write_calendar(root, tickers):
    soon = (datetime.utcnow().date() + timedelta(days=7)).isoformat()
    cal = {t: [{"event_date": soon, "confidence": "confirmed", "fiscal_period": "Q3 2026"}] for t in tickers}
    (root / "earnings_calendar.json").write_text(json.dumps(cal), encoding="utf-8")


def _save_run(ticker, evidence_items):
    tracker = RunTracker(ticker)
    tracker.start_run(input_snapshot_hash="abc123")
    sid = tracker.start_step("fetch")
    tracker.finish_step(sid, StepStatus.SUCCESS, result={"price": 1.0, "evidence_items": evidence_items})
    tracker.finish_run()
    return tracker.run_id


def _event(ticker):
    return EarningsEvent(ticker=ticker, event_date="2026-11-05", confidence="confirmed")


def test_watchlist_add_shape_feeds_queue(data_dir):
    cron.add_to_watchlist("aapl")
    cron.add_to_watchlist("MSFT")
    _write_calendar(data_dir, ["AAPL", "MSFT", "TSLA"])
    events = EarningsEventService().identify_events_for_watchlist()
    assert sorted(e.ticker for e in events) == ["AAPL", "MSFT"]


def test_legacy_tickers_shape_still_supported(data_dir):
    (data_dir / "watchlist.yaml").write_text("tickers:\n  - nvda\n", encoding="utf-8")
    _write_calendar(data_dir, ["NVDA"])
    events = EarningsEventService().identify_events_for_watchlist()
    assert [e.ticker for e in events] == ["NVDA"]


def test_no_data_lists_all_missing(data_dir):
    [status] = EarningsEventService().check_dossier_readiness([_event("AAPL")])
    assert status.ready is False
    assert set(status.missing_items) == {"prior_guidance", "fundamentals_snapshot", "recent_filings"}
    assert status.run_id is None


def test_saved_run_satisfies_fundamentals_but_not_filings_without_sec(data_dir):
    run_id = _save_run("AAPL", [{"evidence_id": "ev_yfinance_1", "source": "yfinance"}])
    [status] = EarningsEventService().check_dossier_readiness([_event("AAPL")])
    assert status.run_id == run_id
    assert "fundamentals_snapshot" not in status.missing_items
    assert "recent_filings" in status.missing_items
    assert "prior_guidance" in status.missing_items
    assert status.ready is False


def test_missing_sec_evidence_item_does_not_count(data_dir):
    _save_run("AAPL", [{"evidence_id": "ev_sec_edgar_1", "source": "sec_edgar", "missing": True}])
    [status] = EarningsEventService().check_dossier_readiness([_event("AAPL")])
    assert "recent_filings" in status.missing_items


def test_ready_with_run_sec_evidence_and_guidance(data_dir):
    run_id = _save_run("AAPL", [{"evidence_id": "ev_sec_edgar_1", "source": "sec_edgar"}])
    GuidanceTracker().add(GuidanceRecord(
        ticker="AAPL", metric="revenue", fiscal_period="Q4 2026", low=1.0, high=2.0,
        source_filing="0000320193-26-000001", published_date="2026-08-01",
    ))
    [status] = EarningsEventService().check_dossier_readiness([_event("aapl")])
    assert status.missing_items == []
    assert status.ready is True
    assert status.run_id == run_id


def test_other_ticker_run_does_not_leak(data_dir):
    _save_run("MSFT", [{"evidence_id": "ev_sec_edgar_1", "source": "sec_edgar"}])
    [status] = EarningsEventService().check_dossier_readiness([_event("AAPL")])
    assert "fundamentals_snapshot" in status.missing_items


def test_add_to_watchlist_does_not_leak_into_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(cron, "WATCHLIST_PATH", tmp_path / "a.yaml")
    cron.add_to_watchlist("TSLA")
    monkeypatch.setattr(cron, "WATCHLIST_PATH", tmp_path / "b.yaml")
    assert [i["ticker"] for i in cron.load_watchlist().get("watchlist", [])] == []
