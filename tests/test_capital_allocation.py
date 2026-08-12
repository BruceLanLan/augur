# -*- coding: utf-8 -*-
"""Tests for Capital Allocation Review (C04) + Peer Comparison Pack (C08)."""

import pytest

from augur.capital_allocation import (
    BuybackRecord,
    CapitalAllocationAnalyzer,
    CapitalAllocationReport,
    DividendRecord,
    PeerComparison,
    build_peer_comparison,
    register_peer_metrics,
    PEER_METRIC_VALUES,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _sample_financials() -> list:
    """Three periods of financial data for a healthy dividend + buyback payer."""
    return [
        {
            "ticker": "ACME",
            "period": "FY2023",
            "net_income": 10_000_000_000,
            "shares_outstanding": 1_000_000_000,
            "avg_share_price": 150.0,
            "market_cap": 150_000_000_000,
            "revenue": 50_000_000_000,
        },
        {
            "ticker": "ACME",
            "period": "FY2024",
            "net_income": 11_000_000_000,
            "shares_outstanding": 950_000_000,
            "avg_share_price": 170.0,
            "market_cap": 161_500_000_000,
            "revenue": 53_000_000_000,
        },
        {
            "ticker": "ACME",
            "period": "FY2025",
            "net_income": 12_000_000_000,
            "shares_outstanding": 900_000_000,
            "avg_share_price": 200.0,
            "market_cap": 180_000_000_000,
            "revenue": 57_000_000_000,
        },
    ]


def _sample_cash_flow() -> list:
    """Matching three periods of cash-flow data."""
    return [
        {
            "ticker": "ACME",
            "period": "FY2023",
            "free_cash_flow": 15_000_000_000,
            "capex": 3_000_000_000,
            "buyback_spend": 5_000_000_000,
            "dividends_paid": 2_500_000_000,
            "mna_spend": 1_000_000_000,
            "debt_repaid": 500_000_000,
            "shares_retired": 33_000_000,
        },
        {
            "ticker": "ACME",
            "period": "FY2024",
            "free_cash_flow": 16_000_000_000,
            "capex": 3_200_000_000,
            "buyback_spend": 6_000_000_000,
            "dividends_paid": 2_800_000_000,
            "mna_spend": 500_000_000,
            "debt_repaid": 600_000_000,
            "shares_retired": 40_000_000,
        },
        {
            "ticker": "ACME",
            "period": "FY2025",
            "free_cash_flow": 17_000_000_000,
            "capex": 3_500_000_000,
            "buyback_spend": 7_000_000_000,
            "dividends_paid": 3_200_000_000,
            "mna_spend": 0,
            "debt_repaid": 700_000_000,
            "shares_retired": 50_000_000,
        },
    ]


def _concerning_cash_flow() -> list:
    """Cash flow where payout ratio exceeds 100 %."""
    return [
        {
            "ticker": "RISKY",
            "period": "FY2025",
            "free_cash_flow": 5_000_000_000,
            "capex": 1_000_000_000,
            "buyback_spend": 2_000_000_000,
            "dividends_paid": 8_000_000_000,  # high
            "mna_spend": 0,
            "debt_repaid": 0,
            "shares_retired": 10_000_000,
        },
    ]


def _concerning_financials() -> list:
    """Financials with low net income → payout > 100 %."""
    return [
        {
            "ticker": "RISKY",
            "period": "FY2025",
            "net_income": 5_000_000_000,  # dividends 8B > net income 5B
            "shares_outstanding": 500_000_000,
            "avg_share_price": 50.0,
            "market_cap": 25_000_000_000,
            "revenue": 20_000_000_000,
        },
    ]


# ============================================================================
# C04 — CapitalAllocationAnalyzer tests
# ============================================================================


class TestCapitalAllocationAnalyzer:
    """Tests for the core capital-allocation analysis."""

    def test_analyze_returns_report(self):
        """analyze() returns a CapitalAllocationReport with the correct ticker."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_sample_financials(), _sample_cash_flow())
        assert isinstance(report, CapitalAllocationReport)
        assert report.ticker == "ACME"

    def test_buyback_records_built(self):
        """Buyback records are populated for each period."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_sample_financials(), _sample_cash_flow())
        assert len(report.buybacks) == 3
        assert report.buybacks[0].period == "FY2023"
        assert report.buybacks[0].amount == 5_000_000_000
        assert report.buybacks[0].shares_retired == 33_000_000
        # pct_of_market_cap = 5B / 150B * 100 ≈ 3.3333
        assert report.buybacks[0].pct_of_market_cap == pytest.approx(3.3333, abs=0.01)

    def test_dividend_records_built(self):
        """Dividend records are populated with DPS, payout ratio, yield, growth."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_sample_financials(), _sample_cash_flow())
        assert len(report.dividends) == 3

        d0 = report.dividends[0]  # FY2023
        assert d0.dps == pytest.approx(2.5, abs=0.01)       # 2.5B / 1B shares
        assert d0.payout_ratio == pytest.approx(0.25, abs=0.01)  # 2.5B / 10B
        assert d0.yield_pct == pytest.approx(1.6667, abs=0.01)   # 2.5 / 150 * 100
        assert d0.growth_yoy == 0.0  # first period, no previous

        d1 = report.dividends[1]  # FY2024
        assert d1.dps == pytest.approx(2.9474, abs=0.01)    # 2.8B / 950M shares
        assert d1.growth_yoy == pytest.approx(0.1789, abs=0.01)  # (2.947-2.5)/2.5

    def test_mna_activity_built(self):
        """M&A activity records capture spend and targets per period."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_sample_financials(), _sample_cash_flow())
        assert len(report.mna_activity) == 3
        assert report.mna_activity[0]["spend"] == 1_000_000_000
        assert report.mna_activity[2]["spend"] == 0  # FY2025 has no M&A

    def test_capex_trend_built(self):
        """Capex trend includes absolute spend, capex-to-FCF, and capex-to-revenue."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_sample_financials(), _sample_cash_flow())
        assert len(report.capex_trend) == 3

        c0 = report.capex_trend[0]
        assert c0["capex"] == 3_000_000_000
        assert c0["capex_to_fcf"] == pytest.approx(0.2, abs=0.01)
        assert c0["capex_to_revenue"] == pytest.approx(6.0, abs=0.01)

    def test_fcf_usage_percentages(self):
        """FCF usage breakdown sums reasonably across categories."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_sample_financials(), _sample_cash_flow())
        usage = report.fcf_usage
        total_pct = (
            usage["pct_buybacks"]
            + usage["pct_dividends"]
            + usage["pct_capex"]
            + usage["pct_debt_reduction"]
        )
        assert total_pct == pytest.approx(100.0, abs=0.1)
        assert usage["total_fcf"] == 48_000_000_000  # 15+16+17 B

    def test_shareholder_return_yield(self):
        """Shareholder return yield is the average of buyback yield + dividend yield."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_sample_financials(), _sample_cash_flow())
        # Buyback yields: 3.33, 3.72, 3.89 → avg 3.65
        # Dividend yields: 1.67, 1.73, 1.78 → avg 1.73
        # Sum ≈ 5.38
        assert report.shareholder_return_yield == pytest.approx(5.38, abs=0.1)

    def test_assessment_shareholder_friendly(self):
        """Healthy company with strong buybacks + dividends → shareholder_friendly."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_sample_financials(), _sample_cash_flow())
        assert report.assessment == "shareholder_friendly"

    def test_assessment_concerning_payout_ratio(self):
        """Payout ratio ≥ 100 % → concerning."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(_concerning_financials(), _concerning_cash_flow())
        assert report.assessment == "concerning"

    def test_empty_input_returns_defaults(self):
        """Empty financials/cash_flow returns a report with zeros and neutral assessment."""
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze([], [])
        assert report.ticker == "UNKNOWN"
        assert report.buybacks == []
        assert report.dividends == []
        assert report.shareholder_return_yield == 0.0
        assert report.assessment == "neutral"

    def test_ticker_extracted_from_cash_flow_only(self):
        """When financials lack ticker, cash_flow provides it."""
        fin = [{"period": "FY2025", "net_income": 100, "shares_outstanding": 100,
                 "avg_share_price": 10, "market_cap": 1000, "revenue": 500}]
        cf = [{"ticker": "CF_ONLY", "period": "FY2025", "free_cash_flow": 200,
                "capex": 50, "buyback_spend": 30, "dividends_paid": 10,
                "mna_spend": 0, "debt_repaid": 0, "shares_retired": 5}]
        analyzer = CapitalAllocationAnalyzer()
        report = analyzer.analyze(fin, cf)
        assert report.ticker == "CF_ONLY"


# ============================================================================
# Dataclass smoke tests
# ============================================================================


class TestBuybackRecord:
    def test_creation(self):
        bb = BuybackRecord(
            period="FY2025", amount=5_000_000_000,
            shares_retired=33_000_000, pct_of_market_cap=3.33,
        )
        assert bb.period == "FY2025"
        assert bb.amount == 5_000_000_000


class TestDividendRecord:
    def test_creation(self):
        d = DividendRecord(
            period="FY2025", dps=2.5, payout_ratio=0.25,
            yield_pct=1.67, growth_yoy=0.12,
        )
        assert d.period == "FY2025"
        assert d.growth_yoy == 0.12


class TestCapitalAllocationReport:
    def test_defaults(self):
        r = CapitalAllocationReport(ticker="TEST")
        assert r.ticker == "TEST"
        assert r.buybacks == []
        assert r.assessment == "neutral"
        assert r.shareholder_return_yield == 0.0


# ============================================================================
# C08 — Peer Comparison tests
# ============================================================================


class TestPeerComparison:
    """Tests for build_peer_comparison and the metric registry."""

    @pytest.fixture(autouse=True)
    def _clear_registry(self):
        """Reset the metric registry before each test."""
        PEER_METRIC_VALUES.clear()

    def test_build_peer_comparison_basic(self):
        register_peer_metrics({
            "AAPL": {"pe_ratio": 28.0, "roe": 0.45, "debt_to_equity": 1.5},
            "MSFT": {"pe_ratio": 32.0, "roe": 0.40, "debt_to_equity": 0.8},
            "GOOGL": {"pe_ratio": 24.0, "roe": 0.30, "debt_to_equity": 0.3},
        })
        pc = build_peer_comparison("AAPL", ["MSFT", "GOOGL"], ["pe_ratio", "roe", "debt_to_equity"])
        assert isinstance(pc, PeerComparison)
        assert pc.ticker == "AAPL"
        assert set(pc.peers) == {"MSFT", "GOOGL"}

    def test_rankings_are_1_based(self):
        register_peer_metrics({
            "AAPL": {"pe_ratio": 28.0},
            "MSFT": {"pe_ratio": 32.0},
            "GOOGL": {"pe_ratio": 24.0},
        })
        pc = build_peer_comparison("AAPL", ["MSFT", "GOOGL"], ["pe_ratio"])
        # MSFT=32 (rank 1), AAPL=28 (rank 2), GOOGL=24 (rank 3)
        assert pc.rankings["pe_ratio"] == 2

    def test_percentile_computation(self):
        register_peer_metrics({
            "AAPL": {"roe": 0.45},
            "MSFT": {"roe": 0.40},
            "GOOGL": {"roe": 0.30},
        })
        pc = build_peer_comparison("AAPL", ["MSFT", "GOOGL"], ["roe"])
        # AAPL rank 1 out of 3 → percentile = (3-1)/(3-1)*100 = 100
        assert pc.percentile["roe"] == 100.0
        assert pc.rankings["roe"] == 1

    def test_ticker_auto_included(self):
        register_peer_metrics({
            "AAPL": {"roe": 0.45},
            "MSFT": {"roe": 0.40},
        })
        # "AAPL" not in peers list → automatically prepended
        pc = build_peer_comparison("AAPL", ["MSFT"], ["roe"])
        assert pc.ticker == "AAPL"
        assert "AAPL" in pc.metrics["roe"]

    def test_missing_metric_defaults_to_zero(self):
        register_peer_metrics({
            "AAPL": {"roe": 0.45},
            "MSFT": {},
        })
        pc = build_peer_comparison("AAPL", ["MSFT"], ["roe"])
        assert pc.metrics["roe"]["MSFT"] == 0.0

    def test_no_peers_returns_singleton(self):
        register_peer_metrics({"AAPL": {"roe": 0.45}})
        pc = build_peer_comparison("AAPL", [], ["roe"])
        assert pc.peers == []
        assert pc.rankings["roe"] == 1
        # percentile with n=1: (1-1)/0 * 100 = 0.0 (guard via max(n-1,1))
        assert pc.percentile["roe"] == 0.0
