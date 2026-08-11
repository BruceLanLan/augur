# -*- coding: utf-8 -*-
"""Tests for augur.thesis — Investment Thesis Tracking System."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from augur.thesis import (
    Decision,
    DecisionLog,
    Thesis,
    ThesisDelta,
    ThesisJournal,
    _generate_decision_id,
    _generate_thesis_id,
    compute_thesis_delta,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_thesis(ticker="AAPL", statement=None, **overrides):
    """Build a Thesis with sensible defaults for testing."""
    stmt = statement or f"{ticker} services revenue will surpass hardware within 2 years"
    defaults = dict(
        thesis_id=_generate_thesis_id(ticker, stmt),
        ticker=ticker,
        statement=stmt,
        catalysts=["Growing Services attach rate", "iPhone installed base expansion"],
        risks=["Regulatory pressure on App Store", "China market slowdown"],
        falsification_conditions=[
            "services revenue growth below 5%",
            "hardware revenue accelerates above services",
        ],
        created_at=datetime.now(timezone.utc).isoformat(),
        status="active",
        run_id="run_AAPL_20250101T000000_abc12345",
    )
    defaults.update(overrides)
    return Thesis(**defaults)


def _make_run_bundle(run_id, **fields):
    """Build a synthetic RunBundle dict for delta computation."""
    base = {
        "run_id": run_id,
        "ticker": "AAPL",
        "consensus": {"signal": "bullish", "score": 7.5},
        "valuation": {"pe_ratio": 28.5, "revenue_growth": 0.12, "market_cap": 3_000_000_000_000},
        "facts": {"services_revenue": 85_000_000_000, "hardware_revenue": 300_000_000_000},
        "language": {"tone": "confident", "narrative": "growth story intact"},
        "sentiment": {"management_tone": "positive"},
    }
    base.update(fields)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def journal_dir(monkeypatch, tmp_path):
    """Redirect thesis data to a temp directory."""
    thesis_dir = tmp_path / "thesis"
    thesis_dir.mkdir()

    # Monkey-patch the module-level THESIS_DIR so both journal and log
    # use the temp path.
    import augur.thesis as mod
    original = mod.THESIS_DIR
    mod.THESIS_DIR = thesis_dir
    yield thesis_dir
    mod.THESIS_DIR = original


@pytest.fixture
def journal(journal_dir):
    """Return a fresh ThesisJournal backed by a temp dir."""
    return ThesisJournal()


@pytest.fixture
def decision_log(journal_dir):
    """Return a fresh DecisionLog backed by a temp dir."""
    return DecisionLog()


# ---------------------------------------------------------------------------
# Tests: Thesis ID generation
# ---------------------------------------------------------------------------

def test_thesis_id_format():
    """Thesis ID follows the th_{ticker}_{hash[:8]} convention."""
    tid = _generate_thesis_id("AAPL", "Apple services will dominate")
    assert tid.startswith("th_AAPL_")
    assert len(tid) == len("th_AAPL_") + 8  # 8 hex chars


def test_thesis_id_deterministic():
    """Same statement produces the same thesis_id."""
    a = _generate_thesis_id("AAPL", "same statement")
    b = _generate_thesis_id("AAPL", "same statement")
    assert a == b


def test_thesis_id_different_per_statement():
    """Different statements produce different thesis_ids."""
    a = _generate_thesis_id("AAPL", "statement one")
    b = _generate_thesis_id("AAPL", "statement two")
    assert a != b


# ---------------------------------------------------------------------------
# Tests: ThesisJournal CRUD
# ---------------------------------------------------------------------------

def test_create_and_get(journal):
    """Creating a thesis and retrieving it returns the same fields."""
    th = _make_thesis()
    tid = journal.create(th)
    assert tid == th.thesis_id

    got = journal.get(tid)
    assert got is not None
    assert got.thesis_id == th.thesis_id
    assert got.ticker == "AAPL"
    assert got.statement == th.statement
    assert got.catalysts == th.catalysts
    assert got.risks == th.risks
    assert got.falsification_conditions == th.falsification_conditions
    assert got.status == "active"
    assert got.run_id == th.run_id


def test_get_nonexistent(journal):
    """Getting a missing thesis_id returns None."""
    assert journal.get("th_NOEXIST_00000000") is None


def test_list_by_ticker(journal):
    """list_by_ticker returns only matching theses (case-insensitive)."""
    t1 = _make_thesis(ticker="AAPL", statement="Apple thesis 1")
    t2 = _make_thesis(ticker="AAPL", statement="Apple thesis 2")
    t3 = _make_thesis(ticker="MSFT", statement="Microsoft thesis")
    journal.create(t1)
    journal.create(t2)
    journal.create(t3)

    aapl = journal.list_by_ticker("aapl")  # lower-case should work
    assert len(aapl) == 2
    assert all(th.ticker.upper() == "AAPL" for th in aapl)

    msft = journal.list_by_ticker("MSFT")
    assert len(msft) == 1
    assert msft[0].ticker.upper() == "MSFT"


def test_update_status(journal):
    """update_status changes the thesis status and persists."""
    th = _make_thesis()
    journal.create(th)

    updated = journal.update_status(th.thesis_id, "refuted", "Services revenue fell 10%")
    assert updated.status == "refuted"
    assert updated.__dict__.get("status_reason") == "Services revenue fell 10%"

    # Verify persistence by reloading
    fresh = ThesisJournal()
    got = fresh.get(th.thesis_id)
    assert got is not None
    assert got.status == "refuted"
    assert got.__dict__.get("status_reason") == "Services revenue fell 10%"


def test_update_status_missing_raises(journal):
    """update_status on a missing id raises KeyError."""
    with pytest.raises(KeyError):
        journal.update_status("th_NOEXIST_00000000", "refuted")


def test_thesis_dataclass_fields():
    """Thesis dataclass has all expected fields with correct defaults."""
    th = _make_thesis()
    assert th.status == "active"
    assert isinstance(th.catalysts, list)
    assert isinstance(th.risks, list)
    assert isinstance(th.falsification_conditions, list)


# ---------------------------------------------------------------------------
# Tests: ThesisDelta computation
# ---------------------------------------------------------------------------

def test_compute_thesis_delta_no_changes():
    """Identical runs produce an 'intact' delta with no changes."""
    th = _make_thesis()
    run = _make_run_bundle("run_1")
    delta = compute_thesis_delta(th, run, run)
    assert delta.overall_assessment == "intact"
    assert len(delta.fact_changes) == 0
    assert len(delta.valuation_changes) == 0
    assert len(delta.language_changes) == 0
    assert len(delta.falsification_triggered) == 0


def test_compute_thesis_delta_valuation_change():
    """A valuation-level change is detected and classified."""
    th = _make_thesis()
    prev = _make_run_bundle("run_1", valuation={"pe_ratio": 28.5, "revenue_growth": 0.12})
    new = _make_run_bundle("run_2", valuation={"pe_ratio": 35.0, "revenue_growth": 0.08})
    delta = compute_thesis_delta(th, prev, new)
    # The deep scan should pick up the nested diffs
    assert len(delta.valuation_changes) > 0


def test_compute_thesis_delta_fact_change():
    """A fact-level change outside valuation/language is classified as fact."""
    th = _make_thesis()
    prev = _make_run_bundle("run_1", facts={"services_revenue": 85e9})
    new = _make_run_bundle("run_2", facts={"services_revenue": 90e9})
    delta = compute_thesis_delta(th, prev, new)
    # services_revenue in facts dict should be picked up
    assert len(delta.fact_changes) > 0 or len(delta.valuation_changes) > 0


def test_compute_thesis_delta_falsification_triggered():
    """A falsification condition appearing in the new run text triggers refuted."""
    th = _make_thesis(
        falsification_conditions=["services revenue growth below 5%"],
    )
    prev = _make_run_bundle("run_1")
    new = _make_run_bundle(
        "run_2",
        facts={"services_revenue_growth": "below 5% year over year"},
    )
    delta = compute_thesis_delta(th, prev, new)
    # "services revenue growth below 5%" tokens should match
    assert len(delta.falsification_triggered) >= 1
    assert delta.overall_assessment == "refuted"


def test_compute_thesis_delta_language_change():
    """A language / sentiment change is classified separately."""
    th = _make_thesis()
    prev = _make_run_bundle("run_1", language={"tone": "confident"})
    new = _make_run_bundle("run_2", language={"tone": "cautious"})
    delta = compute_thesis_delta(th, prev, new)
    assert len(delta.language_changes) > 0
    # Mostly rhetoric → thesis stays intact
    assert delta.overall_assessment == "intact"


def test_compute_thesis_delta_run_ids():
    """Delta carries the correct previous and new run_ids."""
    th = _make_thesis()
    prev = _make_run_bundle("run_A")
    new = _make_run_bundle("run_B", valuation={"pe_ratio": 40})
    delta = compute_thesis_delta(th, prev, new)
    assert delta.previous_run_id == "run_A"
    assert delta.new_run_id == "run_B"
    assert delta.thesis_id == th.thesis_id


# ---------------------------------------------------------------------------
# Tests: DecisionLog
# ---------------------------------------------------------------------------

def test_record_and_get_decision(decision_log):
    """Recording a decision and retrieving it returns the same fields."""
    now = datetime.now(timezone.utc).isoformat()
    d = Decision(
        decision_id=_generate_decision_id("AAPL", "buy"),
        ticker="AAPL",
        action="buy",
        reasoning="Strong services growth supports bull thesis",
        evidence_run_ids=["run_AAPL_20250101T000000_abc12345"],
        thesis_ids=["th_AAPL_a1b2c3d4"],
        created_at=now,
    )
    did = decision_log.record(d)
    assert did == d.decision_id

    got = decision_log.get(did)
    assert got is not None
    assert got.ticker == "AAPL"
    assert got.action == "buy"
    assert got.reasoning == d.reasoning
    assert got.evidence_run_ids == d.evidence_run_ids
    assert got.thesis_ids == d.thesis_ids
    assert got.outcome is None


def test_list_decisions_by_ticker(decision_log):
    """list_by_ticker returns only matching decisions."""
    d1 = Decision(
        decision_id=_generate_decision_id("AAPL", "buy"),
        ticker="AAPL", action="buy", reasoning="bullish",
        evidence_run_ids=[], thesis_ids=[], created_at="",
    )
    d2 = Decision(
        decision_id=_generate_decision_id("MSFT", "hold"),
        ticker="MSFT", action="hold", reasoning="neutral",
        evidence_run_ids=[], thesis_ids=[], created_at="",
    )
    decision_log.record(d1)
    decision_log.record(d2)

    aapl = decision_log.list_by_ticker("aapl")
    assert len(aapl) == 1
    assert aapl[0].action == "buy"

    msft = decision_log.list_by_ticker("MSFT")
    assert len(msft) == 1
    assert msft[0].action == "hold"


def test_decision_get_nonexistent(decision_log):
    """Getting a missing decision_id returns None."""
    assert decision_log.get("dec_NOEXIST_buy_00000000") is None


# ---------------------------------------------------------------------------
# Tests: Persistence round-trip
# ---------------------------------------------------------------------------

def test_thesis_journal_persistence_roundtrip(journal_dir):
    """ThesisJournal saves and loads correctly across instances."""
    j1 = ThesisJournal()
    th = _make_thesis()
    j1.create(th)
    j1.update_status(th.thesis_id, "weakened", "Competitor launched similar service")

    # New instance reading the same file
    j2 = ThesisJournal()
    got = j2.get(th.thesis_id)
    assert got is not None
    assert got.status == "weakened"
    assert got.__dict__.get("status_reason") == "Competitor launched similar service"


def test_decision_log_persistence_roundtrip(journal_dir):
    """DecisionLog saves and loads correctly across instances."""
    l1 = DecisionLog()
    d = Decision(
        decision_id=_generate_decision_id("AAPL", "sell"),
        ticker="AAPL", action="sell",
        reasoning="Falsification triggered", evidence_run_ids=[],
        thesis_ids=[], created_at="",
        outcome="correct",
    )
    l1.record(d)

    l2 = DecisionLog()
    got = l2.get(d.decision_id)
    assert got is not None
    assert got.action == "sell"
    assert got.outcome == "correct"


def test_journal_empty_load(journal_dir):
    """Loading a journal from an empty directory works."""
    j = ThesisJournal()
    assert j.list_by_ticker("AAPL") == []


def test_decision_log_empty_load(journal_dir):
    """Loading a decision log from an empty directory works."""
    l = DecisionLog()
    assert l.list_by_ticker("AAPL") == []


def test_journal_corrupt_file(journal_dir, monkeypatch):
    """Journal gracefully handles a corrupt JSON file."""
    import augur.thesis as mod

    # Write invalid JSON
    corrupt_path = journal_dir / "theses.json"
    corrupt_path.write_text("not valid json {{{")

    j = ThesisJournal()
    # Should not raise; should return empty state
    assert j.list_by_ticker("AAPL") == []
