# -*- coding: utf-8 -*-
"""Tests for earnings event service (P2.1 MVP)."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from augur.earnings import (
    DossierStatus,
    EarningsEvent,
    EarningsEventService,
    FilingDelta,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_calendar(tmpdir: Path) -> Path:
    """Create a temporary earnings calendar JSON."""
    today = datetime.utcnow().date()
    next_week = today + timedelta(days=7)
    next_month = today + timedelta(days=40)

    cal = {
        "AAPL": [
            {
                "event_date": next_week.strftime("%Y-%m-%d"),
                "confidence": "confirmed",
                "fiscal_period": "Q4 2025",
                "source": "sec_edgar",
            },
        ],
        "MSFT": [
            {
                "event_date": next_month.strftime("%Y-%m-%d"),
                "confidence": "estimated",
                "fiscal_period": "Q2 2026",
                "source": "provider",
            },
        ],
        "TSLA": [
            {
                "event_date": "2020-01-15",  # past — should be excluded
                "confidence": "confirmed",
                "fiscal_period": "Q4 2019",
            },
        ],
    }
    path = tmpdir / "earnings_calendar.json"
    path.write_text(json.dumps(cal))
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEarningsEventService:
    def test_detect_upcoming_events(self, tmp_path):
        cal = _make_calendar(tmp_path)
        svc = EarningsEventService(calendar_path=cal)
        events = svc.detect_events(["AAPL", "MSFT", "TSLA"], lookahead_days=30)
        tickers = {e.ticker for e in events}
        assert "AAPL" in tickers  # within 30 days
        assert "MSFT" not in tickers  # 40 days out
        assert "TSLA" not in tickers  # past event

    def test_detect_with_longer_window(self, tmp_path):
        cal = _make_calendar(tmp_path)
        svc = EarningsEventService(calendar_path=cal)
        events = svc.detect_events(["AAPL", "MSFT"], lookahead_days=60)
        tickers = {e.ticker for e in events}
        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_unknown_ticker_returns_empty(self, tmp_path):
        cal = _make_calendar(tmp_path)
        svc = EarningsEventService(calendar_path=cal)
        events = svc.detect_events(["NONEXISTENT"], lookahead_days=30)
        assert events == []

    def test_event_fields_populated(self, tmp_path):
        cal = _make_calendar(tmp_path)
        svc = EarningsEventService(calendar_path=cal)
        events = svc.detect_events(["AAPL"], lookahead_days=30)
        assert len(events) == 1
        e = events[0]
        assert e.ticker == "AAPL"
        assert e.confidence == "confirmed"
        assert e.fiscal_period == "Q4 2025"

    def test_check_dossier_readiness_no_data(self, tmp_path):
        cal = _make_calendar(tmp_path)
        svc = EarningsEventService(calendar_path=cal)
        events = svc.detect_events(["AAPL"], lookahead_days=30)
        statuses = svc.check_dossier_readiness(events)
        assert len(statuses) == 1
        # No data directories exist by default → not ready
        assert statuses[0].ready is False
        assert len(statuses[0].missing_items) > 0

    def test_filing_delta_no_previous(self, tmp_path):
        cal = _make_calendar(tmp_path)
        svc = EarningsEventService(calendar_path=cal)
        delta = svc.compare_filings("AAPL", "run_new_001")
        assert delta.ticker == "AAPL"
        assert len(delta.changes) >= 1
        change_types = {c["type"] for c in delta.changes}
        assert any(t in change_types for t in ["initial_run", "step_added", "step_removed"])


class TestEarningsEvent:
    def test_creation(self):
        e = EarningsEvent(
            ticker="AAPL",
            event_date="2026-01-15",
            confidence="confirmed",
            fiscal_period="Q4 2025",
            source="sec_edgar",
        )
        assert e.ticker == "AAPL"
        assert e.event_date == "2026-01-15"


class TestDossierStatus:
    def test_ready(self):
        e = EarningsEvent(ticker="AAPL", event_date="2026-01-15", confidence="confirmed")
        ds = DossierStatus(ticker="AAPL", event=e, ready=True, missing_items=[])
        assert ds.ready is True

    def test_not_ready(self):
        e = EarningsEvent(ticker="MSFT", event_date="2026-01-15", confidence="estimated")
        ds = DossierStatus(
            ticker="MSFT", event=e, ready=False,
            missing_items=["prior_guidance", "recent_filings"],
        )
        assert ds.ready is False
        assert "prior_guidance" in ds.missing_items


class TestFilingDelta:
    def test_creation(self):
        fd = FilingDelta(
            ticker="AAPL",
            new_accession="acc_new",
            previous_accession="acc_prev",
        )
        assert fd.ticker == "AAPL"
        assert fd.new_accession == "acc_new"
