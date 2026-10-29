# -*- coding: utf-8 -*-
"""v13: EDGAR 8-K Item 2.02 backfill for the earnings calendar (offline)."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from click.testing import CliRunner

from augur import earnings_calendar as ec
from augur.earnings import EarningsEventService

TODAY = date(2026, 10, 29)


def _subs(rows):
    """rows: (form, filingDate, items, accession)"""
    return {
        "cik": "320193",
        "filings": {
            "recent": {
                "form": [r[0] for r in rows],
                "filingDate": [r[1] for r in rows],
                "items": [r[2] for r in rows],
                "reportDate": ["" for _ in rows],
                "accessionNumber": [r[3] for r in rows],
            }
        },
    }


# EDGAR lists newest first.
FIXTURE = _subs([
    ("8-K", "2026-07-31", "2.02,9.01", "a-6"),
    ("10-Q", "2026-08-01", "", "q-1"),
    ("8-K", "2026-06-10", "5.07", "x-1"),          # shareholder vote, not earnings
    ("8-K", "2026-05-01", "2.02,9.01", "a-5"),
    ("4", "2026-04-15", "", "f-1"),
    ("8-K", "2026-01-30", "2.02,9.01", "a-4"),
    ("8-K/A", "2026-01-30", "2.02", "a-4b"),       # same date: deduped
    ("8-K", "2025-10-30", "2.02,9.01", "a-3"),
    ("8-K", "2025-07-31", "2.02", "a-2"),
    ("8-K", "2025-05-01", "2.02", "a-1"),
    ("8-K", "2026-12-01", "2.02", "future"),       # after today: ignored
])


def test_picks_only_202_8ks():
    events = ec.estimate_events_from_edgar("AAPL", FIXTURE, TODAY)
    hist = [e for e in events if e["confidence"] == "historical"]
    assert [e["event_date"] for e in hist] == [
        "2025-05-01", "2025-07-31", "2025-10-30", "2026-01-30", "2026-05-01", "2026-07-31",
    ]
    assert all(e["source"] == "sec_8k_2.02" for e in hist)
    assert hist[-1]["accession"] == "a-6"
    assert "x-1" not in {e.get("accession") for e in events}


def test_cadence_estimate_uses_median_of_last_four_gaps():
    events = ec.estimate_events_from_edgar("AAPL", FIXTURE, TODAY)
    est = [e for e in events if e["confidence"] == "estimated"]
    assert len(est) == 1
    # last 4 gaps: 07-31→10-30=91, 10-30→01-30=92, 01-30→05-01=91, 05-01→07-31=91 → median 91
    assert est[0]["event_date"] == "2026-10-30"
    assert est[0]["source"] == "estimated_from_8k_cadence"
    assert not any(e["confidence"] == "confirmed" for e in events)


def test_less_than_two_events_no_estimate():
    one = _subs([("8-K", "2026-07-31", "2.02", "a-1"), ("8-K", "2026-06-01", "8.01", "b")])
    events = ec.estimate_events_from_edgar("X", one, TODAY)
    assert [e["confidence"] for e in events] == ["historical"]
    assert ec.estimate_events_from_edgar("X", {}, TODAY) == []


def test_merge_keeps_user_entries_and_is_idempotent(tmp_path):
    path = tmp_path / "earnings_calendar.json"
    user = {
        "AAPL": [{"event_date": "2026-10-30", "confidence": "confirmed", "fiscal_period": "Q4 2026"}],
        "MSFT": [{"event_date": "2026-10-28", "confidence": "confirmed"}],
    }
    path.write_text(json.dumps(user))

    r1 = ec.backfill_calendar(["aapl"], path, today=TODAY, fetch=lambda t: FIXTURE)
    cal = json.loads(path.read_text())
    aapl = {e["event_date"]: e for e in cal["AAPL"]}
    # user's confirmed entry on the estimated date wins, untouched
    assert aapl["2026-10-30"] == user["AAPL"][0]
    assert r1["AAPL"]["estimated"] == 0
    assert len(r1["AAPL"]["added"]) == 6
    assert cal["MSFT"] == user["MSFT"]

    before = path.read_text()
    r2 = ec.backfill_calendar(["AAPL"], path, today=TODAY, fetch=lambda t: FIXTURE)
    assert r2["AAPL"]["added"] == []
    assert path.read_text() == before


def test_fetch_error_is_per_ticker(tmp_path):
    path = tmp_path / "cal.json"

    def fetch(t):
        if t == "BAD":
            raise ec.EdgarFetchError("boom")
        return FIXTURE

    r = ec.backfill_calendar(["BAD", "AAPL"], path, today=TODAY, fetch=fetch)
    assert r["BAD"]["error"] == "boom"
    assert r["AAPL"]["estimated"] == 1
    assert "BAD" not in json.loads(path.read_text())


def test_estimated_event_is_detected_as_upcoming(tmp_path):
    path = tmp_path / "cal.json"
    path.write_text(json.dumps({"AAPL": [
        {"event_date": (date.today() + timedelta(days=2)).isoformat(), "confidence": "estimated",
         "source": "estimated_from_8k_cadence"},
    ]}))
    events = EarningsEventService(calendar_path=path).detect_events(["AAPL"], lookahead_days=5)
    assert [e.confidence for e in events] == ["estimated"]


def test_cli_backfill(tmp_path, monkeypatch):
    from augur.cli_commands.earnings_cmd import earnings_cmd

    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path))
    (tmp_path / "watchlist.yaml").write_text("watchlist:\n  - ticker: AAPL\n  - ticker: NOPE\n")

    def fake_fetch(t):
        if t == "NOPE":
            raise ec.EdgarFetchError("no CIK found for NOPE")
        return FIXTURE

    monkeypatch.setattr(ec, "fetch_submissions", fake_fetch)
    res = CliRunner().invoke(earnings_cmd, ["--backfill"])
    assert res.exit_code == 0, res.output
    assert "AAPL     added 7 (1 estimated)" in res.output
    assert "NOPE     error: no CIK found for NOPE" in res.output
    cal = json.loads((tmp_path / "earnings_calendar.json").read_text())
    assert len(cal["AAPL"]) == 7


def test_fetch_submissions_uses_existing_client(monkeypatch):
    import augur.consensus.edgar_fundamentals as ef

    class FakeClient:
        def get_cik(self, t):
            return 320193 if t == "AAPL" else None

        def get_submissions(self, cik):
            return FIXTURE if cik == 320193 else None

    monkeypatch.setattr(ef, "_get_client", lambda: FakeClient())
    assert ec.fetch_submissions("AAPL") is FIXTURE
    with pytest.raises(ec.EdgarFetchError):
        ec.fetch_submissions("ZZZZ")
