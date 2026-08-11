# -*- coding: utf-8 -*-
"""Tests for GuidanceTracker."""

import pytest

from augur.guidance_tracker import GuidanceRecord, GuidanceTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker():
    """Return a fresh GuidanceTracker (hermetic via conftest AUGUR_DATA_DIR)."""
    return GuidanceTracker()


@pytest.fixture
def aapl_revenue_q1():
    return GuidanceRecord(
        ticker="AAPL",
        metric="revenue",
        fiscal_period="Q1 2025",
        low=120_000,
        high=125_000,
        actual_result=None,
        source_filing="0000320193-25-000001",
        published_date="2025-01-30",
    )


@pytest.fixture
def aapl_revenue_q2():
    return GuidanceRecord(
        ticker="AAPL",
        metric="revenue",
        fiscal_period="Q2 2025",
        low=88_000,
        high=92_000,
        actual_result=None,
        source_filing="0000320193-25-000050",
        published_date="2025-04-30",
    )


@pytest.fixture
def aapl_revenue_q3():
    return GuidanceRecord(
        ticker="AAPL",
        metric="revenue",
        fiscal_period="Q3 2025",
        low=82_000,
        high=86_000,
        actual_result=85_700,
        source_filing="0000320193-25-000100",
        published_date="2025-07-30",
    )


# ---------------------------------------------------------------------------
# GuidanceRecord
# ---------------------------------------------------------------------------

class TestGuidanceRecord:
    def test_creation(self):
        r = GuidanceRecord(
            ticker="AAPL",
            metric="eps",
            fiscal_period="FY2025",
            low=6.00,
            high=6.50,
            source_filing="acc_001",
            published_date="2025-01-30",
        )
        assert r.ticker == "AAPL"
        assert r.metric == "eps"
        assert r.low == 6.00
        assert r.high == 6.50
        assert r.actual_result is None

    def test_with_actual_result(self):
        r = GuidanceRecord(
            ticker="MSFT",
            metric="revenue",
            fiscal_period="Q4 2025",
            low=60000,
            high=62000,
            actual_result=61500,
            source_filing="acc_002",
            published_date="2025-08-15",
        )
        assert r.actual_result == 61500


# ---------------------------------------------------------------------------
# GuidanceTracker — add / get_history
# ---------------------------------------------------------------------------

class TestGuidanceTrackerAddGet:
    def test_add_and_get_history(self, tracker, aapl_revenue_q1, aapl_revenue_q2):
        tracker.add(aapl_revenue_q1)
        tracker.add(aapl_revenue_q2)

        history = tracker.get_history("AAPL", "revenue")
        assert len(history) == 2
        assert history[0].fiscal_period == "Q1 2025"
        assert history[1].fiscal_period == "Q2 2025"
        assert history[1].low == 88_000

    def test_get_history_empty_ticker(self, tracker):
        history = tracker.get_history("NONEXIST", "revenue")
        assert history == []

    def test_get_history_wrong_metric(self, tracker, aapl_revenue_q1):
        tracker.add(aapl_revenue_q1)
        history = tracker.get_history("AAPL", "eps")
        assert history == []

    def test_ticker_case_insensitive(self, tracker, aapl_revenue_q1):
        tracker.add(aapl_revenue_q1)
        history = tracker.get_history("aapl", "revenue")
        assert len(history) == 1


# ---------------------------------------------------------------------------
# GuidanceTracker — compare
# ---------------------------------------------------------------------------

class TestGuidanceTrackerCompare:
    def test_compare_two_periods_raised(self, tracker, aapl_revenue_q1, aapl_revenue_q2):
        # Q1: 120k-125k → midpoint 122.5k
        # Q2: 88k-92k → midpoint 90k (lowered significantly)
        tracker.add(aapl_revenue_q1)
        tracker.add(aapl_revenue_q2)
        result = tracker.compare("AAPL", "revenue")
        assert result["direction"] == "lowered"
        assert result["midpoint_delta_pct"] < -20.0

    def test_compare_only_one_record(self, tracker, aapl_revenue_q1):
        tracker.add(aapl_revenue_q1)
        result = tracker.compare("AAPL", "revenue")
        assert result["direction"] == "initial"
        assert result["latest"] is not None
        assert result["previous"] is None

    def test_compare_no_history(self, tracker):
        result = tracker.compare("AAPL", "revenue")
        assert result["direction"] == "no_history"

    def test_compare_unchanged(self, tracker):
        r1 = GuidanceRecord(
            ticker="TSLA", metric="eps", fiscal_period="Q1 2025",
            low=0.70, high=0.80, source_filing="a", published_date="2025-01-30",
        )
        r2 = GuidanceRecord(
            ticker="TSLA", metric="eps", fiscal_period="Q2 2025",
            low=0.72, high=0.78, source_filing="b", published_date="2025-04-30",
        )
        tracker.add(r1)
        tracker.add(r2)
        result = tracker.compare("TSLA", "eps")
        assert result["direction"] == "unchanged"


# ---------------------------------------------------------------------------
# GuidanceTracker — check_accuracy
# ---------------------------------------------------------------------------

class TestGuidanceTrackerCheckAccuracy:
    def test_no_results(self, tracker):
        result = tracker.check_accuracy("AAPL", "eps")
        assert result["total_periods"] == 0
        assert result["accuracy_pct"] == 0.0

    def test_one_met_result(self, tracker, aapl_revenue_q3):
        # Q3: 82k-86k, actual=85.7k → met
        tracker.add(aapl_revenue_q3)
        result = tracker.check_accuracy("AAPL", "revenue")
        assert result["total_periods"] == 1
        assert result["met"] == 1
        assert result["missed"] == 0
        assert result["accuracy_pct"] == 100.0

    def test_missed_result(self, tracker):
        r = GuidanceRecord(
            ticker="MSFT", metric="eps", fiscal_period="Q4 2025",
            low=3.00, high=3.20, actual_result=2.80,
            source_filing="acc", published_date="2025-08-15",
        )
        tracker.add(r)
        result = tracker.check_accuracy("MSFT", "eps")
        assert result["total_periods"] == 1
        assert result["met"] == 0
        assert result["missed"] == 1
        assert result["accuracy_pct"] == 0.0

    def test_mixed_accuracy(self, tracker, aapl_revenue_q3):
        # Q3 met, add one missed
        r = GuidanceRecord(
            ticker="AAPL", metric="revenue", fiscal_period="Q4 2025",
            low=90_000, high=95_000, actual_result=88_000,
            source_filing="acc", published_date="2025-10-30",
        )
        tracker.add(aapl_revenue_q3)
        tracker.add(r)
        result = tracker.check_accuracy("AAPL", "revenue")
        assert result["total_periods"] == 2
        assert result["met"] == 1
        assert result["missed"] == 1
        assert result["accuracy_pct"] == 50.0


# ---------------------------------------------------------------------------
# GuidanceTracker — to_evidence_items
# ---------------------------------------------------------------------------

class TestGuidanceTrackerToEvidence:
    def test_to_evidence_items(self, tracker, aapl_revenue_q1):
        tracker.add(aapl_revenue_q1)
        items = tracker.to_evidence_items("AAPL")
        assert len(items) == 1
        item = items[0]
        assert item.instrument == "AAPL"
        assert item.metric == "guidance_revenue"
        # Midpoint of 120k-125k = 122500
        assert item.value == 122500.0

    def test_to_evidence_items_empty(self, tracker):
        items = tracker.to_evidence_items("AAPL")
        assert items == []

    def test_multiple_records(self, tracker, aapl_revenue_q1, aapl_revenue_q2, aapl_revenue_q3):
        tracker.add(aapl_revenue_q1)
        tracker.add(aapl_revenue_q2)
        tracker.add(aapl_revenue_q3)
        items = tracker.to_evidence_items("AAPL")
        assert len(items) == 3
        metrics = {it.metric for it in items}
        assert metrics == {"guidance_revenue"}
