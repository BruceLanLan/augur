# -*- coding: utf-8 -*-
"""v13 earnings cycle: `augur cycle`, `augur thesis-delta`, `augur scorecard`."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest
from click.testing import CliRunner

from augur import cron
from augur import thesis as thesis_mod
from augur.cli import main
from augur.guidance_tracker import GuidanceRecord, GuidanceTracker
from augur.run_tracker import RunTracker
from augur.schemas.step_result import StepStatus


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(cron, "WATCHLIST_PATH", tmp_path / "watchlist.yaml")
    monkeypatch.setattr(thesis_mod, "THESIS_DIR", tmp_path / "thesis")
    return tmp_path


def _write_calendar(root, tickers):
    soon = (datetime.utcnow().date() + timedelta(days=7)).isoformat()
    cal = {t: [{"event_date": soon, "confidence": "confirmed", "fiscal_period": "Q3 2026"}] for t in tickers}
    (root / "earnings_calendar.json").write_text(json.dumps(cal), encoding="utf-8")


def _save_run(ticker, evidence_items, price=1.0):
    tracker = RunTracker(ticker)
    tracker.start_run(input_snapshot_hash="abc123")
    sid = tracker.start_step("fetch")
    tracker.finish_step(sid, StepStatus.SUCCESS, result={"price": price, "evidence_items": evidence_items})
    tracker.finish_run()
    return tracker.run_id


def _add_thesis(ticker):
    journal = thesis_mod.ThesisJournal()
    return journal.create(thesis_mod.Thesis(
        thesis_id="", ticker=ticker, statement="Services margin keeps expanding",
        catalysts=["services growth"], risks=["regulation"],
        falsification_conditions=["services decline"], created_at="",
    ))


def _cli(*args):
    result = CliRunner().invoke(main, list(args))
    assert result.exit_code == 0, result.output + repr(result.exception)
    return result.output


def test_cycle_ready_one_of_two(data_dir):
    cron.add_to_watchlist("AAPL")
    cron.add_to_watchlist("MSFT")
    _write_calendar(data_dir, ["AAPL", "MSFT"])
    run_id = _save_run("AAPL", [{"evidence_id": "ev_sec_edgar_1", "source": "sec_edgar"}])
    GuidanceTracker().add(GuidanceRecord(
        ticker="AAPL", metric="revenue", fiscal_period="Q4 2026", low=1.0, high=2.0,
        source_filing="0000320193-26-000001", published_date="2026-08-01",
    ))

    out = _cli("cycle", "--days", "14")
    assert "ready 1/2" in out
    assert run_id in out
    assert "Pre-Earnings Dossier: AAPL" in out
    assert "Pre-Earnings Dossier: MSFT" in out
    msft_block = out.split("MSFT ·")[1].split("Ledger:")[0]
    assert "missing: prior_guidance, fundamentals_snapshot, recent_filings" in msft_block
    assert "MSFT: record prior guidance" in out
    assert "Thesis delta: unavailable: no active thesis for AAPL" in out
    assert "Ledger: unavailable: need two saved runs" in out


def test_cycle_markdown_and_empty_watchlist(data_dir):
    out = _cli("cycle", "--format", "markdown")
    assert "# Earnings Cycle" in out
    assert "ready 0/0" in out
    assert "Watchlist is empty" in out


def test_cycle_ticker_without_event_is_listed(data_dir):
    cron.add_to_watchlist("TSLA")
    out = _cli("cycle")
    assert "ready 0/0" in out
    assert "No calendar event within 30 days: TSLA" in out


def test_thesis_delta_unavailable_without_thesis(data_dir):
    out = _cli("thesis-delta", "AAPL")
    assert "unavailable: no active thesis for AAPL" in out
    assert "next step:" in out


def test_thesis_delta_unavailable_with_one_run(data_dir):
    _add_thesis("AAPL")
    _save_run("AAPL", [])
    out = _cli("thesis-delta", "aapl")
    assert "unavailable: need two saved runs for AAPL (found 1)" in out


def test_thesis_delta_report_with_two_runs(data_dir):
    _add_thesis("AAPL")
    prev_id = _save_run("AAPL", [], price=1.0)
    new_id = _save_run("AAPL", [], price=2.0)
    out = _cli("thesis-delta", "AAPL")
    assert "# Thesis Review: AAPL" in out
    assert "**Assessment**" in out
    assert f"Compared {prev_id} → {new_id}" in out


def test_scorecard_unavailable_without_runs(data_dir):
    out = _cli("scorecard", "AAPL")
    assert "Scorecard AAPL unavailable: need a pre-event and a post-event saved run (found 0 runs" in out


def test_scorecard_unavailable_without_questions(data_dir):
    _save_run("AAPL", [])
    _save_run("AAPL", [])
    out = _cli("scorecard", "AAPL")
    assert "unavailable: no research questions recorded" in out


def test_scorecard_unknown_run_id(data_dir):
    _save_run("AAPL", [])
    _save_run("AAPL", [])
    out = _cli("scorecard", "AAPL", "--pre", "run_AAPL_nope")
    assert "unavailable" in out and "run_AAPL_nope" in out
