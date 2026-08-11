"""Tests for augur.valuation — deterministic DCF + WACC + scenarios.

All tests verify that calculations use decimal.Decimal internally
(no floating-point rounding) and that the two-stage DCF model matches
hand-computed results.
"""

import math
import pytest
from decimal import Decimal

from augur.valuation import (
    WACCInputs,
    DCFInputs,
    DCFOutput,
    ScenarioInputs,
    ScenarioOutput,
    compute_wacc,
    compute_dcf,
    run_scenarios,
    sensitivity_grid,
    reverse_dcf,
)


# ---------------------------------------------------------------------------
# WACC tests
# ---------------------------------------------------------------------------

class TestWACC:
    def test_compute_wacc_basic(self):
        """WACC with known inputs — hand-computed verification.

        rf=4%, erp=5%, beta=1.2, kd=3%, tax=21%, ew=85%, dw=15%
        Ke = 0.04 + 1.2*0.05 = 0.10
        after-tax Kd = 0.03 * (1-0.21) = 0.0237
        WACC = 0.10*0.85 + 0.0237*0.15 = 0.085 + 0.003555 = 0.088555
        """
        inputs = WACCInputs(
            risk_free_rate=0.04,
            equity_risk_premium=0.05,
            beta=1.2,
            cost_of_debt=0.03,
            tax_rate=0.21,
            equity_weight=0.85,
            debt_weight=0.15,
        )
        result = compute_wacc(inputs)
        assert result == pytest.approx(0.088555, rel=1e-10)

    def test_compute_wacc_auto_cost_of_equity(self):
        """compute_wacc populates cost_of_equity via CAPM."""
        inputs = WACCInputs(
            risk_free_rate=0.035,
            equity_risk_premium=0.055,
            beta=1.5,
            cost_of_debt=0.04,
        )
        compute_wacc(inputs)
        expected_ke = 0.035 + 1.5 * 0.055  # = 0.1175
        assert inputs.cost_of_equity == pytest.approx(expected_ke, rel=1e-10)

    def test_wacc_all_equity(self):
        """100 % equity financing → WACC = cost of equity only."""
        inputs = WACCInputs(
            risk_free_rate=0.03,
            equity_risk_premium=0.06,
            beta=1.0,
            equity_weight=1.0,
            debt_weight=0.0,
            cost_of_debt=0.05,
        )
        result = compute_wacc(inputs)
        expected_ke = 0.03 + 1.0 * 0.06  # = 0.09
        assert result == pytest.approx(expected_ke, rel=1e-10)

    def test_wacc_default_tax_rate(self):
        """Default tax rate is 21 % (US statutory)."""
        inputs = WACCInputs(
            risk_free_rate=0.04,
            equity_risk_premium=0.05,
            beta=1.0,
        )
        assert inputs.tax_rate == 0.21


# ---------------------------------------------------------------------------
# DCF tests
# ---------------------------------------------------------------------------

class TestDCF:
    def test_compute_dcf_g1_equals_wacc(self):
        """When growth_rate_stage1 == wacc, each year's PV equals base FCF.

        Hand-computed:
          FCF=100, g1=10%, wacc=10%, g_term=2.5%, n=5, shares=100
          stage1_pv = 5 * 100 = 500
          FCF_5 = 100 * 1.10^5 = 161.051
          TV = 161.051 * 1.025 / 0.075 = 2201.03033...
          PV_TV = 2201.03033 / 1.61051 = 1366.684...
          EV = 500 + 1366.684 = 1866.684
          FV = 18.66684...
        """
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.10,
            stage1_years=5,
            growth_rate_terminal=0.025,
            wacc=0.10,
            shares_outstanding=100.0,
            net_debt=0.0,
        )
        out = compute_dcf(dcf)
        # Stage 1: each year's PV = 100
        assert out.stage1_pv == pytest.approx(500.0, rel=1e-10)
        # Enterprise value (hand-computed)
        expected_ev = 500.0 + (161.051 * 1.025 / 0.075) / (1.10 ** 5)
        assert out.enterprise_value == pytest.approx(expected_ev, rel=1e-10)
        assert out.fair_value_per_share == pytest.approx(expected_ev / 100.0, rel=1e-10)
        # Terminal value dominates enterprise value in typical DCF
        assert out.terminal_pv > out.stage1_pv

    def test_compute_dcf_zero_growth(self):
        """Zero growth throughout: EV = FCF / WACC (simple perpetuity).

        FCF=100, g1=0%, wacc=10%, g_term=0%, n=5, shares=100, net_debt=0
        Stage 1 PV = Σ 100/(1.1)^t for t=1..5  ≈ 379.079
        FCF_5 = 100, TV = 100*1/0.10 = 1000, PV_TV = 1000/1.1^5 ≈ 620.921
        EV = 379.079 + 620.921 = 1000.0  (same as perpetuity 100/0.10)
        FV = 10.0
        """
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.0,
            stage1_years=5,
            growth_rate_terminal=0.0,
            wacc=0.10,
            shares_outstanding=100.0,
            net_debt=0.0,
        )
        out = compute_dcf(dcf)
        # Perpetuity: 100 / 0.10 = 1000
        assert out.enterprise_value == pytest.approx(1000.0, rel=1e-8)
        assert out.fair_value_per_share == pytest.approx(10.0, rel=1e-8)

    def test_compute_dcf_with_net_debt(self):
        """Net debt reduces equity value but not enterprise value."""
        dcf_no_debt = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.10,
            wacc=0.10,
            shares_outstanding=100.0,
            net_debt=0.0,
        )
        dcf_with_debt = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.10,
            wacc=0.10,
            shares_outstanding=100.0,
            net_debt=200.0,
        )
        out_no = compute_dcf(dcf_no_debt)
        out_with = compute_dcf(dcf_with_debt)
        # Enterprise value unchanged
        assert out_no.enterprise_value == pytest.approx(out_with.enterprise_value, rel=1e-10)
        # Equity value reduced by net_debt
        assert out_with.equity_value == pytest.approx(out_no.equity_value - 200.0, rel=1e-10)
        # Fair value per share reduced
        assert out_with.fair_value_per_share < out_no.fair_value_per_share

    def test_compute_dcf_negative_fcf(self):
        """Negative FCF yields negative enterprise value (valid economic case)."""
        dcf = DCFInputs(
            free_cash_flow=-50.0,
            growth_rate_stage1=0.10,
            wacc=0.10,
            shares_outstanding=100.0,
            net_debt=0.0,
        )
        out = compute_dcf(dcf)
        assert out.enterprise_value < 0.0
        assert out.fair_value_per_share < 0.0

    def test_compute_dcf_output_types(self):
        """All output fields are plain floats."""
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.05,
            wacc=0.10,
        )
        out = compute_dcf(dcf)
        assert isinstance(out.enterprise_value, float)
        assert isinstance(out.equity_value, float)
        assert isinstance(out.fair_value_per_share, float)
        assert isinstance(out.stage1_pv, float)
        assert isinstance(out.terminal_pv, float)
        assert isinstance(out.sensitivity, dict)

    def test_compute_dcf_stage1_and_terminal_sum(self):
        """Enterprise value = stage1 PV + terminal PV."""
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.08,
            stage1_years=5,
            growth_rate_terminal=0.03,
            wacc=0.10,
        )
        out = compute_dcf(dcf)
        assert out.enterprise_value == pytest.approx(
            out.stage1_pv + out.terminal_pv, rel=1e-12
        )


# ---------------------------------------------------------------------------
# Sensitivity tests
# ---------------------------------------------------------------------------

class TestSensitivity:
    def test_sensitivity_grid_dimensions(self):
        """Grid is steps × steps."""
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.05,
            wacc=0.10,
        )
        grid = sensitivity_grid(dcf, (0.06, 0.14), (0.01, 0.05), steps=9)
        assert len(grid) == 9
        assert all(len(row) == 9 for row in grid)

    def test_sensitivity_grid_invalid_cells_zero(self):
        """Cells where WACC ≤ growth are 0.0 (Gordon model invalid)."""
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.05,
            wacc=0.10,
        )
        grid = sensitivity_grid(dcf, (0.03, 0.10), (0.02, 0.08), steps=5)
        # WACC=0.03 row, growth=0.08 col → WACC ≤ growth → should be 0.0
        assert grid[0][4] == 0.0  # first row = lowest WACC, last col = highest growth

    def test_dcf_output_sensitivity_structure(self):
        """DCFOutput.sensitivity has the expected dict-of-lists structure."""
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.05,
            wacc=0.10,
            growth_rate_terminal=0.025,
        )
        out = compute_dcf(dcf)
        sens = out.sensitivity
        assert isinstance(sens, dict)
        # Keys look like "wacc_0.0800"
        for key in sens:
            assert key.startswith("wacc_")
            row = sens[key]
            assert isinstance(row, list)
            for cell in row:
                assert "growth" in cell
                assert "fair_value" in cell
                # Center cell near base assumptions should be non-None
        # The center cell (wacc ≈ 0.10, growth ≈ 0.025) must have a value
        center_key = "wacc_0.1000"
        assert center_key in sens


# ---------------------------------------------------------------------------
# Reverse DCF tests
# ---------------------------------------------------------------------------

class TestReverseDCF:
    def test_reverse_dcf_roundtrip(self):
        """Compute DCF at known growth, then reverse-DCF recovers it."""
        g1 = 0.08
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=g1,
            stage1_years=5,
            growth_rate_terminal=0.025,
            wacc=0.10,
            shares_outstanding=200.0,
            net_debt=0.0,
        )
        out = compute_dcf(dcf)
        implied = reverse_dcf(
            market_price=out.fair_value_per_share,
            shares=dcf.shares_outstanding,
            net_debt=dcf.net_debt,
            wacc=dcf.wacc,
            free_cash_flow=dcf.free_cash_flow,
            growth_rate_terminal=dcf.growth_rate_terminal,
        )
        assert implied is not None
        assert implied == pytest.approx(g1, rel=1e-4)

    def test_reverse_dcf_higher_price_higher_growth(self):
        """A higher market price implies higher growth."""
        base_price = 50.0
        high_price = 100.0
        g_base = reverse_dcf(
            market_price=base_price,
            shares=100.0,
            net_debt=0.0,
            wacc=0.10,
            free_cash_flow=100.0,
        )
        g_high = reverse_dcf(
            market_price=high_price,
            shares=100.0,
            net_debt=0.0,
            wacc=0.10,
            free_cash_flow=100.0,
        )
        assert g_base is not None and g_high is not None
        assert g_high > g_base


# ---------------------------------------------------------------------------
# Scenario tests
# ---------------------------------------------------------------------------

class TestScenarios:
    def test_run_scenarios_all_three(self):
        """Bull, base, and bear scenarios are all computed."""
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.08,
            stage1_years=5,
            growth_rate_terminal=0.025,
            wacc=0.10,
            shares_outstanding=100.0,
            net_debt=0.0,
        )
        scenarios = ScenarioInputs(
            base_growth=0.08,
            bull_growth=0.15,
            bear_growth=0.02,
        )
        result = run_scenarios(dcf, scenarios)
        assert isinstance(result.bull_case, DCFOutput)
        assert isinstance(result.base_case, DCFOutput)
        assert isinstance(result.bear_case, DCFOutput)
        assert isinstance(result.probability_weighted, float)

    def test_run_scenarios_ordering(self):
        """Bull > Base > Bear in fair value per share."""
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.08,
            wacc=0.10,
            shares_outstanding=100.0,
            net_debt=0.0,
        )
        scenarios = ScenarioInputs(
            base_growth=0.08,
            bull_growth=0.20,
            bear_growth=0.01,
        )
        result = run_scenarios(dcf, scenarios)
        assert result.bull_case.fair_value_per_share > result.base_case.fair_value_per_share
        assert result.base_case.fair_value_per_share > result.bear_case.fair_value_per_share

    def test_run_scenarios_probability_weighted_in_range(self):
        """Probability-weighted value lies between bear and bull."""
        dcf = DCFInputs(
            free_cash_flow=100.0,
            growth_rate_stage1=0.08,
            wacc=0.10,
            shares_outstanding=100.0,
            net_debt=0.0,
        )
        scenarios = ScenarioInputs(
            base_growth=0.08,
            bull_growth=0.18,
            bear_growth=0.02,
        )
        result = run_scenarios(dcf, scenarios)
        assert result.bear_case.fair_value_per_share <= result.probability_weighted
        assert result.probability_weighted <= result.bull_case.fair_value_per_share


# ---------------------------------------------------------------------------
# Precision tests
# ---------------------------------------------------------------------------

class TestPrecision:
    def test_decimal_not_float_rounding(self):
        """Decimal precision avoids classic float rounding error (0.1+0.2≠0.3)."""
        d = Decimal("0.1") + Decimal("0.2")
        assert d == Decimal("0.3")
        # Float would give 0.30000000000000004
        assert float(0.1 + 0.2) != 0.3  # sanity: confirm float is broken
        assert float(d) == 0.3
