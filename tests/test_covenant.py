# -*- coding: utf-8 -*-
"""Tests for Debt Covenant Review (C03) + Unit Economics/KPI Model (D06)."""

import pytest

from augur.covenant import (
    CovenantCheck,
    CovenantReport,
    CovenantReviewer,
    KPIDashboard,
    KPIModel,
    KPISnapshot,
)


# ============================================================================
# C03 — Debt Covenant Review
# ============================================================================


class TestCheckDebtEbitda:
    """check_debt_ebitda(debt, ebitda, threshold)"""

    def test_compliant_well_below_threshold(self):
        """Debt/EBITDA = 2.0 vs threshold 3.5 -> compliant with healthy margin."""
        result = CovenantReviewer.check_debt_ebitda(
            debt=700.0, ebitda=350.0, threshold=3.5,
        )
        assert result.in_compliance is True
        assert result.current_value == pytest.approx(2.0)
        # margin = (3.5 - 2.0) / 3.5 * 100 ~ 42.86 %
        assert result.margin_of_safety_pct == pytest.approx(42.86, abs=0.01)
        assert result.trend == "stable"

    def test_in_breach(self):
        """Debt/EBITDA = 4.5 vs threshold 3.5 -> in breach."""
        result = CovenantReviewer.check_debt_ebitda(
            debt=900.0, ebitda=200.0, threshold=3.5,
        )
        assert result.in_compliance is False
        assert result.current_value == pytest.approx(4.5)
        # margin = (3.5 - 4.5) / 3.5 * 100 ~ -28.57 %
        assert result.margin_of_safety_pct == pytest.approx(-28.57, abs=0.01)
        assert result.trend == "deteriorating"

    def test_near_breach_low_margin(self):
        """Debt/EBITDA = 3.3 vs threshold 3.5 -> compliant but near breach."""
        result = CovenantReviewer.check_debt_ebitda(
            debt=660.0, ebitda=200.0, threshold=3.5,
        )
        assert result.in_compliance is True
        assert result.current_value == pytest.approx(3.3)
        # margin = (3.5 - 3.3) / 3.5 * 100 ~ 5.71 % (<= 15 %)
        assert result.margin_of_safety_pct == pytest.approx(5.71, abs=0.01)
        assert result.trend == "deteriorating"

    def test_zero_ebitda_with_debt(self):
        """Zero EBITDA with positive debt -> infinite ratio, in breach."""
        result = CovenantReviewer.check_debt_ebitda(
            debt=500.0, ebitda=0.0, threshold=3.5,
        )
        assert result.in_compliance is False
        assert result.current_value == float("inf")
        assert result.margin_of_safety_pct == float("-inf")
        assert result.trend == "deteriorating"

    def test_zero_debt_and_zero_ebitda(self):
        """Zero debt and zero EBITDA -> ratio 0, compliant."""
        result = CovenantReviewer.check_debt_ebitda(
            debt=0.0, ebitda=0.0, threshold=3.5,
        )
        assert result.in_compliance is True
        assert result.current_value == pytest.approx(0.0)

    def test_at_threshold_exactly(self):
        """Debt/EBITDA exactly equals threshold -> compliant (<= test)."""
        result = CovenantReviewer.check_debt_ebitda(
            debt=350.0, ebitda=100.0, threshold=3.5,
        )
        assert result.in_compliance is True
        assert result.current_value == pytest.approx(3.5)
        assert result.margin_of_safety_pct == pytest.approx(0.0)
        assert result.trend == "deteriorating"  # zero margin -> deteriorating


class TestCheckInterestCoverage:
    """check_interest_coverage(ebit, interest_expense, threshold)"""

    def test_compliant_well_above_threshold(self):
        """EBIT/Interest = 6.0 vs threshold 2.5 -> compliant."""
        result = CovenantReviewer.check_interest_coverage(
            ebit=300.0, interest_expense=50.0, threshold=2.5,
        )
        assert result.in_compliance is True
        assert result.current_value == pytest.approx(6.0)
        # margin = (6.0 - 2.5) / 2.5 * 100 = 140 %
        assert result.margin_of_safety_pct == pytest.approx(140.0)
        assert result.trend == "stable"

    def test_in_breach(self):
        """EBIT/Interest = 1.0 vs threshold 2.5 -> in breach."""
        result = CovenantReviewer.check_interest_coverage(
            ebit=50.0, interest_expense=50.0, threshold=2.5,
        )
        assert result.in_compliance is False
        assert result.current_value == pytest.approx(1.0)
        # margin = (1.0 - 2.5) / 2.5 * 100 = -60 %
        assert result.margin_of_safety_pct == pytest.approx(-60.0)
        assert result.trend == "deteriorating"

    def test_zero_interest_expense_positive_ebit(self):
        """Zero interest expense -> infinite coverage, compliant."""
        result = CovenantReviewer.check_interest_coverage(
            ebit=100.0, interest_expense=0.0, threshold=2.5,
        )
        assert result.in_compliance is True
        assert result.current_value == float("inf")
        assert result.margin_of_safety_pct == float("inf")
        assert result.trend == "stable"

    def test_near_breach_margin(self):
        """EBIT/Interest = 2.7 vs threshold 2.5 -> near breach."""
        result = CovenantReviewer.check_interest_coverage(
            ebit=135.0, interest_expense=50.0, threshold=2.5,
        )
        assert result.in_compliance is True
        assert result.current_value == pytest.approx(2.7)
        # margin = (2.7 - 2.5) / 2.5 * 100 = 8 %
        assert result.margin_of_safety_pct == pytest.approx(8.0)
        assert result.trend == "deteriorating"

    def test_negative_ebit(self):
        """Negative EBIT -> ratio negative, in breach."""
        result = CovenantReviewer.check_interest_coverage(
            ebit=-10.0, interest_expense=50.0, threshold=2.5,
        )
        assert result.in_compliance is False
        assert result.current_value == pytest.approx(-0.2)


class TestCovenantReview:
    """CovenantReviewer.review(financials, debt_terms)"""

    @staticmethod
    def _healthy_financials() -> dict:
        return {
            "ticker": "HEALTH",
            "total_debt": 500.0,
            "ebitda": 250.0,
            "ebit": 180.0,
            "interest_expense": 30.0,
        }

    @staticmethod
    def _breached_financials() -> dict:
        return {
            "ticker": "BREACH",
            "total_debt": 1000.0,
            "ebitda": 200.0,
            "ebit": 40.0,
            "interest_expense": 50.0,
        }

    def test_full_report_compliant(self):
        """Healthy company -> both checks pass, overall 'compliant'."""
        report = CovenantReviewer.review(
            financials=self._healthy_financials(),
            debt_terms={"debt_ebitda_max": 3.5, "interest_coverage_min": 2.5},
        )
        assert isinstance(report, CovenantReport)
        assert report.ticker == "HEALTH"
        assert report.total_checks == 2
        assert report.passed == 2
        assert report.failed == 0
        assert report.critical_breaches == []
        assert report.overall == "compliant"

    def test_full_report_near_breach(self):
        """Both checks near threshold -> overall 'near_breach'."""
        report = CovenantReviewer.review(
            financials={
                "ticker": "TIGHT",
                "total_debt": 330.0,
                "ebitda": 100.0,  # Debt/EBITDA = 3.3, margin ~5.7 %
                "ebit": 135.0,
                "interest_expense": 50.0,  # EBIT/Int = 2.7, margin = 8 %
            },
            debt_terms={"debt_ebitda_max": 3.5, "interest_coverage_min": 2.5},
        )
        assert report.passed == 2
        assert report.failed == 0
        assert report.overall == "near_breach"

    def test_full_report_in_breach(self):
        """Breached company -> overall 'in_breach' with critical breaches."""
        report = CovenantReviewer.review(
            financials=self._breached_financials(),
            debt_terms={"debt_ebitda_max": 3.5, "interest_coverage_min": 2.5},
        )
        assert report.ticker == "BREACH"
        assert report.failed >= 1
        assert len(report.critical_breaches) >= 1
        assert report.overall == "in_breach"

    def test_partial_financials_only_debt_ebitda(self):
        """Only Debt/EBITDA data -> single check, skips interest coverage."""
        report = CovenantReviewer.review(
            financials={"ticker": "PART", "total_debt": 300.0, "ebitda": 100.0},
            debt_terms={"debt_ebitda_max": 4.0},
        )
        assert report.total_checks == 1
        assert report.checks[0].covenant_id == "cov-debt-ebitda"

    def test_default_thresholds_when_missing(self):
        """Missing debt_terms uses defaults (3.5 / 2.5)."""
        report = CovenantReviewer.review(
            financials={
                "ticker": "DEF",
                "total_debt": 350.0,
                "ebitda": 100.0,
                "ebit": 250.0,
                "interest_expense": 50.0,
            },
            debt_terms={},
        )
        # Debt/EBITDA = 3.5 exactly at default threshold -> compliant
        debt_check = next(
            c for c in report.checks if c.covenant_id == "cov-debt-ebitda"
        )
        assert debt_check.in_compliance is True
        assert debt_check.threshold == 3.5

    def test_empty_financials_empty_terms(self):
        """Empty financials -> valid report with zero checks."""
        report = CovenantReviewer.review({}, {})
        assert isinstance(report, CovenantReport)
        assert report.total_checks == 0
        assert report.overall in ("compliant", "near_breach", "in_breach")


# ============================================================================
# D06 — Unit Economics / KPI Model
# ============================================================================


class TestComputeUnitEconomics:
    """KPIModel.compute_unit_economics(revenue, units, costs)"""

    def test_normal_case(self):
        """Standard unit economics with all inputs."""
        result = KPIModel.compute_unit_economics(
            revenue=1_000_000.0,
            units=500,
            costs={"cac": 200_000.0, "variable_cost_per_unit": 300.0},
        )
        # ARPU = 1_000_000 / 500 = 2000
        assert result["arpu"] == pytest.approx(2000.0)
        # CAC = 200_000 / 500 = 400
        assert result["cac"] == pytest.approx(400.0)
        # Gross margin per unit = 2000 - 300 = 1700
        assert result["gross_margin_per_unit"] == pytest.approx(1700.0)
        # LTV = 2000 * (1700/2000) * 36 = 2000 * 0.85 * 36 = 61200
        assert result["ltv"] == pytest.approx(61200.0)
        # LTV/CAC = 61200 / 400 = 153
        assert result["ltv_cac_ratio"] == pytest.approx(153.0)

    def test_zero_units(self):
        """Zero units -> all zeros, no division error."""
        result = KPIModel.compute_unit_economics(
            revenue=0.0, units=0, costs={"cac": 0.0},
        )
        assert result["arpu"] == 0.0
        assert result["cac"] == 0.0
        assert result["ltv"] == 0.0

    def test_custom_lifetime(self):
        """Custom avg_lifetime_months affects LTV."""
        result = KPIModel.compute_unit_economics(
            revenue=100_000.0,
            units=100,
            costs={
                "cac": 10_000.0,
                "variable_cost_per_unit": 200.0,
                "avg_lifetime_months": 24.0,
            },
        )
        # ARPU = 1000, GM/unit = 800, LTV = 1000 * 0.8 * 24 = 19200
        assert result["ltv"] == pytest.approx(19200.0)

    def test_zero_cac_infinite_ratio(self):
        """Zero CAC -> LTV/CAC = inf."""
        result = KPIModel.compute_unit_economics(
            revenue=50_000.0,
            units=100,
            costs={"cac": 0.0},
        )
        assert result["ltv_cac_ratio"] == float("inf")

    def test_missing_cac_defaults_to_zero(self):
        """Missing 'cac' key -> CAC = 0, LTV/CAC = inf, no crash."""
        result = KPIModel.compute_unit_economics(
            revenue=100_000.0, units=100, costs={},
        )
        assert result["cac"] == 0.0
        assert result["ltv_cac_ratio"] == float("inf")


class TestComputeSaaSMetrics:
    """KPIModel.compute_saas_metrics(mrr, churn, cac)"""

    def test_normal_saas_metrics(self):
        """Standard SaaS company with 5 % monthly churn."""
        result = KPIModel.compute_saas_metrics(
            mrr=100_000.0, churn=0.05, cac=30_000.0,
        )
        # ARR = 100k * 12 = 1.2M
        assert result["arr"] == pytest.approx(1_200_000.0)
        # NDR = (1 - 0.05) * 100 = 95 %
        assert result["net_dollar_retention_pct"] == pytest.approx(95.0)
        # Annualized churn = (1 - (1-0.05)^12) * 100 ~ 45.96 %
        assert result["annualized_churn_pct"] == pytest.approx(45.96, abs=0.1)
        # LTV = 100k / 0.05 = 2M
        assert result["ltv"] == pytest.approx(2_000_000.0)
        # LTV/CAC = 2M / 30k ~ 66.67
        assert result["ltv_cac_ratio"] == pytest.approx(66.67, abs=0.1)
        # Months to recover CAC = 30k / (100k * 0.70) ~ 0.4
        assert result["months_to_recover_cac"] == pytest.approx(0.4, abs=0.1)

    def test_zero_churn(self):
        """Zero churn -> infinite LTV, 100 % NDR."""
        result = KPIModel.compute_saas_metrics(
            mrr=50_000.0, churn=0.0, cac=10_000.0,
        )
        assert result["net_dollar_retention_pct"] == pytest.approx(100.0)
        assert result["annualized_churn_pct"] == pytest.approx(0.0)
        assert result["ltv"] == float("inf")
        assert result["ltv_cac_ratio"] == float("inf")

    def test_invalid_churn_raises(self):
        """Churn > 1 or < 0 -> ValueError."""
        with pytest.raises(ValueError):
            KPIModel.compute_saas_metrics(mrr=10_000.0, churn=1.5, cac=5_000.0)
        with pytest.raises(ValueError):
            KPIModel.compute_saas_metrics(mrr=10_000.0, churn=-0.1, cac=5_000.0)

    def test_high_churn(self):
        """High churn (20 %) -> low NDR, short LTV."""
        result = KPIModel.compute_saas_metrics(
            mrr=20_000.0, churn=0.20, cac=40_000.0,
        )
        assert result["net_dollar_retention_pct"] == pytest.approx(80.0)
        # LTV = 20k / 0.20 = 100k
        assert result["ltv"] == pytest.approx(100_000.0)
        # LTV/CAC = 100k / 40k = 2.5
        assert result["ltv_cac_ratio"] == pytest.approx(2.5)


# ============================================================================
# Dataclass round-trip smoke tests
# ============================================================================


class TestDataclassRoundtrips:
    """Basic construction and field access for all dataclasses."""

    def test_covenant_check_fields(self):
        check = CovenantCheck(
            covenant_id="cov-001",
            type="financial",
            description="Debt/EBITDA <= 3.5x",
            threshold=3.5,
            current_value=2.8,
            in_compliance=True,
            margin_of_safety_pct=20.0,
            trend="stable",
        )
        assert check.covenant_id == "cov-001"
        assert check.type == "financial"
        assert check.in_compliance is True

    def test_covenant_report_fields(self):
        report = CovenantReport(
            ticker="TEST",
            total_checks=3,
            passed=2,
            failed=1,
            overall="in_breach",
        )
        assert report.ticker == "TEST"
        assert report.total_checks == 3
        assert report.checks == []
        assert report.critical_breaches == []

    def test_kpi_snapshot_fields(self):
        snap = KPISnapshot(
            metric="ARR",
            value=1_200_000.0,
            unit="USD",
            period="FY2024",
            yoy_change_pct=25.0,
            qoq_change_pct=8.0,
        )
        assert snap.metric == "ARR"
        assert snap.yoy_change_pct == 25.0

    def test_kpi_dashboard_builds_with_trends(self):
        kpis = [
            KPISnapshot(
                metric="LTV", value=5000.0, unit="USD",
                period="Q3", yoy_change_pct=10.0, qoq_change_pct=2.0,
            ),
        ]
        dash = KPIDashboard(
            ticker="SAAS",
            kpis=kpis,
            trends={"LTV": "improving"},
        )
        assert dash.ticker == "SAAS"
        assert len(dash.kpis) == 1
        assert dash.trends["LTV"] == "improving"
