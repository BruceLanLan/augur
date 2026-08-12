# -*- coding: utf-8 -*-
"""Tests for Debt Covenant Review + KPI Model (C03 + D06)."""
import pytest
from augur.covenant import (
    CovenantCheck, CovenantReport, CovenantReviewer,
    KPISnapshot, KPIDashboard, KPIModel,
)


class TestCovenantCheck:
    def test_creation(self):
        cc = CovenantCheck(covenant_id="cv_001", type="financial", description="Debt/EBITDA < 3.5x", threshold=3.5, current_value=2.8, in_compliance=True, margin_of_safety_pct=20.0, trend="stable")
        assert cc.in_compliance is True

    def test_breach(self):
        cc = CovenantCheck(covenant_id="cv_002", type="financial", description="Interest coverage > 2x", threshold=2.0, current_value=1.2, in_compliance=False, margin_of_safety_pct=-40.0, trend="deteriorating")
        assert cc.in_compliance is False


class TestCovenantReport:
    def test_creation(self):
        checks = [CovenantCheck("cv_001", "financial", "test", 3.0, 2.5, True, 16.7, "stable")]
        report = CovenantReport(ticker="AAPL", total_checks=1, passed=1, failed=0, critical_breaches=[], checks=checks, overall="compliant")
        assert report.overall == "compliant"


class TestCovenantReviewer:
    def test_check_debt_ebitda_ok(self):
        check = CovenantReviewer.check_debt_ebitda(debt=1000, ebitda=400, threshold=3.5)
        assert check.in_compliance is True  # 1000/400 = 2.5 < 3.5

    def test_check_debt_ebitda_breach(self):
        check = CovenantReviewer.check_debt_ebitda(debt=2000, ebitda=400, threshold=3.5)
        assert check.in_compliance is False  # 2000/400 = 5.0 > 3.5

    def test_check_interest_coverage_ok(self):
        check = CovenantReviewer.check_interest_coverage(ebit=500, interest_expense=100, threshold=2.0)
        assert check.in_compliance is True  # 500/100 = 5.0 > 2.0

    def test_review_empty(self):
        report = CovenantReviewer.review({}, {})
        assert report.overall in ("compliant", "near_breach", "in_breach")


class TestKPISnapshot:
    def test_creation(self):
        kpi = KPISnapshot(metric="revenue", value=100e9, unit="USD", period="Q4_2025", yoy_change_pct=6.2, qoq_change_pct=1.5)
        assert kpi.yoy_change_pct == 6.2


class TestKPIModel:
    def test_compute_unit_economics(self):
        result = KPIModel.compute_unit_economics(revenue=100e6, units=int(1e6), costs={"cac": 10e6, "variable_cost_per_unit": 10})
        assert isinstance(result, dict)  # 100e6/1e6 = 100

    def test_compute_saas_metrics(self):
        result = KPIModel.compute_saas_metrics(mrr=1e6, churn=0.05, cac=5000)
        assert isinstance(result, dict)
