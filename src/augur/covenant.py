# -*- coding: utf-8 -*-
"""
Debt Covenant Review (C03) + Unit Economics / KPI Model (D06)
=============================================================

C03 — Deterministic covenant compliance checking against financial data.
      Computes Debt/EBITDA, Interest Coverage ratios and evaluates them
      against contractual thresholds with margin-of-safety analysis.

D06 — Unit economics (ARPU, CAC, LTV, LTV/CAC) and SaaS-specific metrics
      (ARR, NDR, churn, CAC payback).

All calculations are pure Python — no LLM dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ============================================================================
# C03 — Debt Covenant Review
# ============================================================================

@dataclass
class CovenantCheck:
    """A single covenant compliance check result.

    Attributes
    ----------
    covenant_id : str
        Unique identifier for this covenant check.
    type : str
        Covenant type — "financial", "affirmative", or "negative".
    description : str
        Human-readable description of the covenant condition.
    threshold : float
        Contractual threshold value (e.g. 3.5 for Debt/EBITDA ≤ 3.5×).
    current_value : float
        Computed current ratio from financial data.
    in_compliance : bool
        Whether the current value satisfies the threshold.
    margin_of_safety_pct : float
        How much headroom exists before breach, as a percentage.
        Positive = headroom still available. Negative = already breached.
        +∞ for infinite headroom (e.g. zero debt), −∞ for infinite breach.
    trend : str
        "improving", "stable", or "deteriorating".
        For single-point assessments this is inferred from margin;
        callers with time-series data should override.
    """

    covenant_id: str
    type: str
    description: str
    threshold: float
    current_value: float
    in_compliance: bool
    margin_of_safety_pct: float
    trend: str


@dataclass
class CovenantReport:
    """Complete covenant review report for a ticker.

    Attributes
    ----------
    ticker : str
        Stock ticker symbol.
    total_checks : int
        Total number of covenant checks performed.
    passed : int
        Number of checks in compliance.
    failed : int
        Number of checks in breach.
    critical_breaches : list[CovenantCheck]
        Covenants currently in breach.
    checks : list[CovenantCheck]
        All covenant checks (compliant and non-compliant).
    overall : str
        Overall assessment — "compliant", "near_breach", or "in_breach".
    """

    ticker: str
    total_checks: int
    passed: int
    failed: int
    critical_breaches: List[CovenantCheck] = field(default_factory=list)
    checks: List[CovenantCheck] = field(default_factory=list)
    overall: str = ""


class CovenantReviewer:
    """Review covenant compliance against financial data and debt terms.

    Computes key financial covenant ratios and evaluates them against
    contractual thresholds extracted from debt agreements.

    Usage::

        report = CovenantReviewer.review(
            financials={"total_debt": 700, "ebitda": 200, "ebit": 150,
                         "interest_expense": 40, "ticker": "AAPL"},
            debt_terms={"debt_ebitda_max": 3.5, "interest_coverage_min": 2.5},
        )
        print(report.overall)  # "compliant" | "near_breach" | "in_breach"
    """

    # Margin ≤ this threshold → flagged as "near_breach"
    _NEAR_BREACH_MARGIN_PCT: float = 15.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def review(financials: dict, debt_terms: dict) -> CovenantReport:
        """Run a full covenant compliance review.

        Parameters
        ----------
        financials : dict
            Must contain ``ticker`` (str) and relevant financial metrics.
            Supported keys: ``total_debt``, ``ebitda``, ``ebit``,
            ``interest_expense``.
        debt_terms : dict
            Covenant thresholds. Supported keys:
            ``debt_ebitda_max`` (default 3.5), ``interest_coverage_min``
            (default 2.5).

        Returns
        -------
        CovenantReport
            Report with all checks, breach list, and overall classification.
        """
        ticker = financials.get("ticker", "")
        checks: List[CovenantCheck] = []

        # --- Debt / EBITDA ----------------------------------------------------
        total_debt = financials.get("total_debt")
        ebitda = financials.get("ebitda")
        if total_debt is not None and ebitda is not None:
            threshold = float(debt_terms.get("debt_ebitda_max", 3.5))
            checks.append(
                CovenantReviewer.check_debt_ebitda(
                    debt=float(total_debt),
                    ebitda=float(ebitda),
                    threshold=threshold,
                )
            )

        # --- Interest Coverage ------------------------------------------------
        ebit = financials.get("ebit")
        interest_expense = financials.get("interest_expense")
        if ebit is not None and interest_expense is not None:
            threshold = float(debt_terms.get("interest_coverage_min", 2.5))
            checks.append(
                CovenantReviewer.check_interest_coverage(
                    ebit=float(ebit),
                    interest_expense=float(interest_expense),
                    threshold=threshold,
                )
            )

        # --- Aggregate ---------------------------------------------------------
        passed = sum(1 for c in checks if c.in_compliance)
        failed = len(checks) - passed
        critical = [c for c in checks if not c.in_compliance]
        overall = CovenantReviewer._classify_overall(checks, failed)

        return CovenantReport(
            ticker=ticker,
            total_checks=len(checks),
            passed=passed,
            failed=failed,
            critical_breaches=critical,
            checks=checks,
            overall=overall,
        )

    @staticmethod
    def check_debt_ebitda(
        debt: float, ebitda: float, threshold: float,
    ) -> CovenantCheck:
        """Check Debt/EBITDA covenant.

        Covenant typically requires Debt/EBITDA ≤ *threshold*.
        Lower ratios are better.

        Parameters
        ----------
        debt : float
            Total debt outstanding.
        ebitda : float
            Earnings before interest, taxes, depreciation & amortization.
        threshold : float
            Maximum allowed Debt/EBITDA ratio (e.g. 3.5 for ≤ 3.5×).

        Returns
        -------
        CovenantCheck
        """
        if ebitda == 0.0:
            ratio = float("inf") if debt > 0 else 0.0
        else:
            ratio = debt / ebitda

        in_compliance = ratio <= threshold
        margin = CovenantReviewer._compute_margin(
            current=ratio, threshold=threshold, higher_is_bad=True,
        )
        trend = CovenantReviewer._infer_trend(
            current=ratio, threshold=threshold, higher_is_bad=True,
        )

        return CovenantCheck(
            covenant_id="cov-debt-ebitda",
            type="financial",
            description=f"Debt / EBITDA ≤ {threshold:.1f}×",
            threshold=threshold,
            current_value=round(ratio, 4),
            in_compliance=in_compliance,
            margin_of_safety_pct=round(margin, 2)
            if margin not in (float("inf"), float("-inf"))
            else margin,
            trend=trend,
        )

    @staticmethod
    def check_interest_coverage(
        ebit: float, interest_expense: float, threshold: float,
    ) -> CovenantCheck:
        """Check Interest Coverage covenant.

        Covenant typically requires EBIT / Interest Expense ≥ *threshold*.
        Higher ratios are better.

        Parameters
        ----------
        ebit : float
            Earnings before interest and taxes.
        interest_expense : float
            Total interest expense for the period.
        threshold : float
            Minimum required coverage ratio (e.g. 2.5 for ≥ 2.5×).

        Returns
        -------
        CovenantCheck
        """
        if interest_expense == 0.0:
            ratio = float("inf") if ebit > 0 else 0.0
        else:
            ratio = ebit / interest_expense

        in_compliance = ratio >= threshold
        margin = CovenantReviewer._compute_margin(
            current=ratio, threshold=threshold, higher_is_bad=False,
        )
        trend = CovenantReviewer._infer_trend(
            current=ratio, threshold=threshold, higher_is_bad=False,
        )

        return CovenantCheck(
            covenant_id="cov-interest-coverage",
            type="financial",
            description=f"EBIT / Interest Expense ≥ {threshold:.1f}×",
            threshold=threshold,
            current_value=round(ratio, 4),
            in_compliance=in_compliance,
            margin_of_safety_pct=round(margin, 2)
            if margin not in (float("inf"), float("-inf"))
            else margin,
            trend=trend,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_margin(
        current: float, threshold: float, higher_is_bad: bool,
    ) -> float:
        """Compute margin of safety as a percentage.

        - *higher_is_bad* (e.g. Debt/EBITDA):
          margin = (threshold − current) / threshold × 100
        - *higher_is_good* (e.g. Interest Coverage):
          margin = (current − threshold) / threshold × 100

        Returns ``float('inf')`` / ``float('-inf')`` for unbounded cases
        (zero debt, zero interest).
        """
        if current == float("inf"):
            return float("-inf") if higher_is_bad else float("inf")
        if current == float("-inf"):
            return float("inf") if higher_is_bad else float("-inf")
        if threshold == 0.0:
            return 0.0
        if higher_is_bad:
            return (threshold - current) / threshold * 100.0
        else:
            return (current - threshold) / threshold * 100.0

    @classmethod
    def _infer_trend(
        cls, current: float, threshold: float, higher_is_bad: bool,
    ) -> str:
        """Infer trend from the margin of safety (single-point heuristic).

        Without historical data this is a rough signal:
        - Large positive margin → "stable"
        - Margin ≤ near-breach threshold → "deteriorating"
        - Already breached → "deteriorating"
        """
        if current == float("inf"):
            return "stable" if not higher_is_bad else "deteriorating"
        if current == float("-inf"):
            return "stable" if higher_is_bad else "deteriorating"

        margin = cls._compute_margin(current, threshold, higher_is_bad)
        if margin == float("inf"):
            return "stable"
        if margin == float("-inf"):
            return "deteriorating"
        if margin < 0:
            return "deteriorating"
        if margin <= cls._NEAR_BREACH_MARGIN_PCT:
            return "deteriorating"
        return "stable"

    @classmethod
    def _classify_overall(
        cls, checks: List[CovenantCheck], failed: int,
    ) -> str:
        """Classify the overall covenant health.

        - Any breach → "in_breach"
        - All compliant but any within near-breach margin → "near_breach"
        - All compliant with comfortable margins → "compliant"
        """
        if failed > 0:
            return "in_breach"

        near = [
            c for c in checks
            if c.margin_of_safety_pct not in (float("inf"), float("-inf"))
            and 0 < c.margin_of_safety_pct <= cls._NEAR_BREACH_MARGIN_PCT
        ]
        return "near_breach" if near else "compliant"


# ============================================================================
# D06 — Unit Economics / KPI Model
# ============================================================================

@dataclass
class KPISnapshot:
    """A single KPI measurement for a given period.

    Attributes
    ----------
    metric : str
        Metric name (e.g. "ARPU", "LTV", "ARR").
    value : float
        Current period value.
    unit : str
        Unit of measurement ("USD", "%", "months", "×").
    period : str
        Reporting period label (e.g. "FY2024", "Q3 2024").
    yoy_change_pct : float
        Year-over-year percentage change.
    qoq_change_pct : float
        Quarter-over-quarter percentage change.
    """

    metric: str
    value: float
    unit: str
    period: str
    yoy_change_pct: float
    qoq_change_pct: float


@dataclass
class KPIDashboard:
    """A collection of KPI snapshots with trend summaries.

    Attributes
    ----------
    ticker : str
        Stock ticker symbol.
    kpis : list[KPISnapshot]
        All KPI snapshots in this dashboard.
    trends : dict[str, str]
        Metric-name → trend label ("improving", "stable", "deteriorating").
    """

    ticker: str
    kpis: List[KPISnapshot] = field(default_factory=list)
    trends: Dict[str, str] = field(default_factory=dict)


class KPIModel:
    """Compute unit economics and SaaS-specific metrics.

    Provides deterministic calculations for:
    - Unit economics: ARPU, CAC, LTV, LTV/CAC ratio
    - SaaS: ARR, NDR, churn, CAC payback period
    """

    # ------------------------------------------------------------------
    # Unit Economics
    # ------------------------------------------------------------------

    @staticmethod
    def compute_unit_economics(
        revenue: float,
        units: int,
        costs: dict,
    ) -> dict:
        """Compute unit economics metrics from revenue and cost data.

        Parameters
        ----------
        revenue : float
            Total revenue for the period.
        units : int
            Number of paying units/customers.
        costs : dict
            ``cac`` — total customer acquisition cost (required).
            ``variable_cost_per_unit`` — variable cost per unit (default 0).
            ``avg_lifetime_months`` — average customer lifetime in months
            (default 36).

        Returns
        -------
        dict
            ``arpu``, ``cac``, ``ltv``, ``gross_margin_per_unit``,
            ``ltv_cac_ratio``.
        """
        if units <= 0:
            return {
                "arpu": 0.0,
                "cac": 0.0,
                "ltv": 0.0,
                "gross_margin_per_unit": 0.0,
                "ltv_cac_ratio": 0.0,
            }

        arpu = revenue / units
        total_cac = float(costs.get("cac", 0.0))
        cac = total_cac / units
        variable_cost = float(costs.get("variable_cost_per_unit", 0.0))
        gross_margin_per_unit = arpu - variable_cost

        # LTV = ARPU × gross_margin% × avg_lifetime_months
        avg_lifetime_months = float(costs.get("avg_lifetime_months", 36.0))
        gross_margin_pct = (gross_margin_per_unit / arpu) if arpu > 0 else 0.0
        ltv = arpu * gross_margin_pct * avg_lifetime_months

        ltv_cac_ratio = (ltv / cac) if cac > 0 else float("inf")

        return {
            "arpu": round(arpu, 2),
            "cac": round(cac, 2),
            "ltv": round(ltv, 2),
            "gross_margin_per_unit": round(gross_margin_per_unit, 2),
            "ltv_cac_ratio": round(ltv_cac_ratio, 2)
            if ltv_cac_ratio != float("inf")
            else float("inf"),
        }

    # ------------------------------------------------------------------
    # SaaS Metrics
    # ------------------------------------------------------------------

    @staticmethod
    def compute_saas_metrics(mrr: float, churn: float, cac: float) -> dict:
        """Compute SaaS-specific metrics from MRR, churn rate, and CAC.

        Parameters
        ----------
        mrr : float
            Monthly Recurring Revenue.
        churn : float
            Monthly logo churn rate as a decimal (e.g. 0.05 = 5 %).
        cac : float
            Average Customer Acquisition Cost per new customer.

        Returns
        -------
        dict
            ``arr``, ``mrr``, ``churn_rate_pct``, ``annualized_churn_pct``,
            ``net_dollar_retention_pct``, ``ltv``, ``ltv_cac_ratio``,
            ``months_to_recover_cac``.
        """
        if churn < 0.0 or churn > 1.0:
            raise ValueError(
                f"Churn rate must be between 0 and 1, got {churn}"
            )

        arr = mrr * 12.0

        # Net Dollar Retention (NDR) — simplified, no expansion revenue
        ndr = (1.0 - churn) * 100.0

        # Annualized churn: 1 − (1 − churn_monthly)^12
        annualized_churn = (1.0 - (1.0 - churn) ** 12) * 100.0

        # LTV = ARPU / churn  (ARPU ≈ MRR per customer, simplified)
        ltv = (mrr / churn) if churn > 0 else float("inf")

        # LTV / CAC
        if cac > 0:
            ltv_cac_ratio = (ltv / cac) if ltv != float("inf") else float("inf")
        else:
            ltv_cac_ratio = float("inf")

        # Months to recover CAC = CAC / (ARPU × gross_margin)
        # Typical SaaS gross margin ≈ 70 %
        gross_margin = 0.70
        monthly_gross_profit = mrr * gross_margin
        months_to_recover_cac = (
            round(cac / monthly_gross_profit, 1)
            if monthly_gross_profit > 0
            else float("inf")
        )

        return {
            "arr": round(arr, 2),
            "mrr": round(mrr, 2),
            "churn_rate_pct": round(churn * 100, 2),
            "annualized_churn_pct": round(annualized_churn, 2),
            "net_dollar_retention_pct": round(ndr, 2),
            "ltv": round(ltv, 2) if ltv != float("inf") else float("inf"),
            "ltv_cac_ratio": round(ltv_cac_ratio, 2)
            if ltv_cac_ratio != float("inf")
            else float("inf"),
            "months_to_recover_cac": months_to_recover_cac,
        }
