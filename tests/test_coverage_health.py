# -*- coding: utf-8 -*-
"""Tests for augur.coverage_health — A05 CoverageAnalyzer + F07 PromotionGate."""

from datetime import datetime, timedelta, timezone

import pytest

from augur.coverage_health import (
    CoverageAnalyzer,
    DataHealthReport,
    FieldCoverage,
    PromotionCandidate,
    PromotionGate,
)


# ============================================================================
# Shared test fixtures
# ============================================================================


def _make_periods(start_date: str, n: int, step_days: int = 30) -> list:
    """Build a list of period dicts starting from *start_date*."""
    dt = datetime.fromisoformat(start_date)
    periods = []
    for i in range(n):
        d = dt + timedelta(days=step_days * i)
        periods.append({"date": d.strftime("%Y-%m-%d"), "value": 100.0 + i})
    return periods


def _make_evidence_store(ticker: str = "AAPL") -> dict:
    """Create a realistic evidence store for testing.

    AAPL has market_cap (full coverage), pe_ratio (partial/stale),
    revenue_growth (missing periods), and dividend_yield (missing field).
    """
    now = datetime.now(timezone.utc)
    # Full coverage: 24 monthly periods ending now
    fresh_start = (now - timedelta(days=23 * 30)).strftime("%Y-%m-%d")
    # Old data: ends 120 days ago (stale)
    stale_end = (now - timedelta(days=120)).strftime("%Y-%m-%d")
    stale_start = (datetime.fromisoformat(stale_end) - timedelta(days=12 * 30)).strftime("%Y-%m-%d")

    return {
        ticker: {
            "fields": {
                "market_cap": {
                    "periods": _make_periods(fresh_start, 24),
                    "source": "yfinance",
                },
                "pe_ratio": {
                    "periods": _make_periods(stale_start, 13),
                    "source": "finnhub",
                },
                "revenue_growth": {
                    "periods": [],
                    "source": "alphavantage",
                },
            },
        },
        "MSFT": {
            "fields": {
                "market_cap": {
                    "periods": _make_periods(fresh_start, 20),
                    "source": "yfinance",
                },
            },
        },
    }


# ============================================================================
# A05 — CoverageAnalyzer tests
# ============================================================================


class TestFieldCoverage:
    """Unit tests for FieldCoverage dataclass."""

    def test_field_coverage_construction(self):
        fc = FieldCoverage(
            field="market_cap",
            coverage_pct=95.0,
            periods_available=24,
            first_available="2024-01-15",
            last_available="2025-12-15",
            source="yfinance",
        )
        assert fc.field == "market_cap"
        assert fc.coverage_pct == 95.0
        assert fc.periods_available == 24
        assert fc.first_available == "2024-01-15"
        assert fc.last_available == "2025-12-15"
        assert fc.source == "yfinance"

    def test_field_coverage_zero_periods(self):
        fc = FieldCoverage(
            field="no_data_field",
            coverage_pct=0.0,
            periods_available=0,
            first_available="",
            last_available="",
            source="unknown",
        )
        assert fc.coverage_pct == 0.0
        assert fc.periods_available == 0


class TestDataHealthReport:
    """Unit tests for DataHealthReport dataclass."""

    def test_healthy_report(self):
        report = DataHealthReport(
            ticker="AAPL",
            fields=[],
            overall_coverage=100.0,
            missing_fields=[],
            stale_fields=[],
            recommendation="healthy",
        )
        assert report.ticker == "AAPL"
        assert report.overall_coverage == 100.0
        assert report.recommendation == "healthy"
        assert not report.missing_fields
        assert not report.stale_fields


class TestCoverageAnalyzer:
    """Tests for CoverageAnalyzer.analyze / field_status / get_universe_coverage."""

    def test_analyze_healthy_ticker(self):
        store = _make_evidence_store()
        report = CoverageAnalyzer.analyze("AAPL", store)

        assert report.ticker == "AAPL"
        assert len(report.fields) == 3  # market_cap, pe_ratio, revenue_growth
        assert report.overall_coverage > 0
        assert "revenue_growth" in report.missing_fields
        assert "pe_ratio" in report.stale_fields
        assert report.recommendation in (
            "needs_review", "needs_fill", "stale_review", "healthy"
        )

    def test_analyze_missing_ticker_returns_no_data(self):
        store = _make_evidence_store()
        report = CoverageAnalyzer.analyze("ZZZZ", store)

        assert report.ticker == "ZZZZ"
        assert len(report.fields) == 0
        assert report.overall_coverage == 0.0
        assert report.recommendation == "no_data"
        assert report.missing_fields == []
        assert report.stale_fields == []

    def test_analyze_empty_fields(self):
        store = {"EMPTY": {"fields": {}}}
        report = CoverageAnalyzer.analyze("EMPTY", store)

        assert report.ticker == "EMPTY"
        assert len(report.fields) == 0
        assert report.overall_coverage == 0.0
        assert report.recommendation == "no_data"

    def test_field_status_existing(self):
        store = _make_evidence_store()
        fc = CoverageAnalyzer.field_status("AAPL", "market_cap", store)

        assert fc.field == "market_cap"
        assert fc.coverage_pct > 0
        assert fc.periods_available == 24
        assert fc.source == "yfinance"

    def test_field_status_missing_field(self):
        store = _make_evidence_store()
        fc = CoverageAnalyzer.field_status("AAPL", "dividend_yield", store)

        assert fc.field == "dividend_yield"
        assert fc.coverage_pct == 0.0
        assert fc.periods_available == 0
        assert fc.source == "unknown"

    def test_field_status_missing_ticker(self):
        store = _make_evidence_store()
        fc = CoverageAnalyzer.field_status("ZZZZ", "market_cap", store)

        assert fc.field == "market_cap"
        assert fc.coverage_pct == 0.0
        assert fc.source == "unknown"

    def test_get_universe_coverage(self):
        store = _make_evidence_store()
        summary = CoverageAnalyzer.get_universe_coverage(
            ["AAPL", "MSFT", "ZZZZ"], store
        )

        assert len(summary) == 3
        assert summary["AAPL"]["fields"] == 3
        assert summary["MSFT"]["fields"] == 1
        assert summary["ZZZZ"]["fields"] == 0
        assert summary["ZZZZ"]["recommendation"] == "no_data"

    def test_analyze_stale_threshold_custom(self):
        """A very short threshold makes every historical field stale."""
        store = _make_evidence_store()
        # 1-day threshold: all fields with data > 1 day old are stale
        report = CoverageAnalyzer.analyze("AAPL", store, stale_threshold_days=1)
        # market_cap and pe_ratio both have data older than 1 day
        assert "market_cap" in report.stale_fields
        assert "pe_ratio" in report.stale_fields

    def test_analyze_very_large_threshold_nothing_stale(self):
        store = _make_evidence_store()
        report = CoverageAnalyzer.analyze("AAPL", store, stale_threshold_days=3650)
        # 10-year threshold: nothing should be stale
        assert "market_cap" not in report.stale_fields


# ============================================================================
# F07 — PromotionGate tests
# ============================================================================


class TestPromotionCandidate:
    """Unit tests for PromotionCandidate dataclass."""

    def test_default_values(self):
        pc = PromotionCandidate(
            feature="debate_engine",
            current_status="experimental",
            eval_results={"brier": 0.18, "accuracy": 0.62},
        )
        assert pc.feature == "debate_engine"
        assert pc.current_status == "experimental"
        assert pc.meets_criteria is False
        assert pc.recommended_action == "hold"


class TestPromotionGate:
    """Tests for PromotionGate.evaluate / promote / demote / get_status."""

    def test_evaluate_meets_criteria_promotes_from_raw(self):
        gate = PromotionGate()
        pc = PromotionCandidate(
            feature="rolling_ic_weight",
            current_status="raw",
            eval_results={
                "brier": 0.15,
                "accuracy": 0.68,
                "ic": 0.08,
                "n_observations": 200,
            },
        )
        result = gate.evaluate(pc)
        assert result.meets_criteria is True
        assert result.recommended_action == "promote"

    def test_evaluate_does_not_meet_criteria_holds(self):
        gate = PromotionGate()
        pc = PromotionCandidate(
            feature="weak_signal",
            current_status="experimental",
            eval_results={
                "brier": 0.35,   # > 0.25 → fails
                "accuracy": 0.45,  # < 0.55 → fails
                "ic": 0.01,        # < 0.03 → fails
                "n_observations": 10,  # < 50 → fails
            },
        )
        result = gate.evaluate(pc)
        assert result.meets_criteria is False
        assert result.recommended_action == "hold"

    def test_evaluate_demotes_production_on_failure(self):
        gate = PromotionGate()
        pc = PromotionCandidate(
            feature="broken_feature",
            current_status="production",
            eval_results={"brier": 0.30, "n_observations": 100},
        )
        result = gate.evaluate(pc)
        assert result.meets_criteria is False
        assert result.recommended_action == "demote"

    def test_evaluate_holds_production_on_success(self):
        gate = PromotionGate()
        pc = PromotionCandidate(
            feature="solid_feature",
            current_status="production",
            eval_results={"brier": 0.10, "accuracy": 0.72, "n_observations": 300},
        )
        result = gate.evaluate(pc)
        assert result.meets_criteria is True
        assert result.recommended_action == "hold"  # already production

    def test_promote_raw_to_experimental(self):
        gate = PromotionGate()
        assert gate.get_status("new_feature") == "raw"
        gate.promote("new_feature")
        assert gate.get_status("new_feature") == "experimental"

    def test_promote_experimental_to_production(self):
        gate = PromotionGate()
        gate._statuses["mid_feature"] = "experimental"
        gate.promote("mid_feature")
        assert gate.get_status("mid_feature") == "production"

    def test_promote_production_stays_production(self):
        gate = PromotionGate()
        gate._statuses["prod_feature"] = "production"
        gate.promote("prod_feature")
        assert gate.get_status("prod_feature") == "production"

    def test_demote_production_to_experimental(self):
        gate = PromotionGate()
        gate._statuses["prod_feature"] = "production"
        gate.demote("prod_feature")
        assert gate.get_status("prod_feature") == "experimental"

    def test_demote_raw_stays_raw(self):
        gate = PromotionGate()
        assert gate.get_status("new_feature") == "raw"
        gate.demote("new_feature")
        assert gate.get_status("new_feature") == "raw"

    def test_demote_experimental_to_raw(self):
        gate = PromotionGate()
        gate._statuses["mid_feature"] = "experimental"
        gate.demote("mid_feature")
        assert gate.get_status("mid_feature") == "raw"

    def test_evaluate_custom_criteria(self):
        gate = PromotionGate()
        pc = PromotionCandidate(
            feature="moderate_signal",
            current_status="experimental",
            eval_results={"brier": 0.30, "accuracy": 0.60, "n_observations": 80},
        )
        # Default criteria would fail (brier 0.30 > 0.25)
        result_default = gate.evaluate(pc)
        assert result_default.meets_criteria is False

        # Relaxed criteria: pass
        relaxed = {"min_brier": 0.40, "min_accuracy": 0.50, "min_observations": 30}
        result_relaxed = gate.evaluate(pc, criteria=relaxed)
        assert result_relaxed.meets_criteria is True
        assert result_relaxed.recommended_action == "promote"

    def test_evaluate_missing_metrics_skips_check(self):
        """Missing metrics should be treated as "not applicable"."""
        gate = PromotionGate()
        pc = PromotionCandidate(
            feature="partial_metrics",
            current_status="raw",
            eval_results={"n_observations": 100},  # no brier, accuracy, or ic
        )
        result = gate.evaluate(pc)
        # No metric to fail → meets_criteria is True
        assert result.meets_criteria is True
        assert result.recommended_action == "promote"

    def test_get_status_default_is_raw(self):
        gate = PromotionGate()
        assert gate.get_status("never_seen") == "raw"

    def test_demote_unknown_status_to_raw(self):
        gate = PromotionGate()
        gate._statuses["weird"] = "deprecated"
        gate.demote("weird")
        # Non-standard statuses should reset to raw
        assert gate.get_status("weird") == "raw"
