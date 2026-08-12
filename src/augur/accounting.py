"""
Accounting Quality Review (C07)
===============================
Deterministic accounting quality checks: accruals analysis, red-flag
detection, Beneish M-Score (earnings manipulation probability), and
Altman Z-Score (bankruptcy risk).

Provenance
----------
Beneish M-Score — Beneish (1999), "The Detection of Earnings Manipulation"
  https://doi.org/10.2469/faj.v55.n5.2296
Altman Z-Score — Altman (1968), "Financial Ratios, Discriminant Analysis
  and the Prediction of Corporate Bankruptcy"
  https://doi.org/10.1111/j.1540-6261.1968.tb00843.x
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================================
# Data classes
# ============================================================================


@dataclass
class AccrualCheck:
    """Single accrual-quality metric result."""

    metric: str  # e.g. "accruals_to_assets"
    value: float
    threshold: float
    passed: bool
    severity: str  # "warning" | "critical" | "ok"


@dataclass
class RedFlag:
    """One red flag detected during accounting review."""

    flag_id: str
    category: str  # "revenue_recognition" | "expense_capitalization"
    #              | "cash_flow_quality" | "one_time_items" | "related_party"
    description: str
    severity: str  # "warning" | "critical"
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class AccountingQualityReport:
    """Complete output of an accounting quality review."""

    ticker: str
    period: str
    checks: List[AccrualCheck] = field(default_factory=list)
    red_flags: List[RedFlag] = field(default_factory=list)
    beneish_m_score: Optional[float] = None  # earnings manipulation probability
    altman_z_score: Optional[float] = None  # bankruptcy risk
    overall_assessment: str = "clean"  # "clean" | "watch" | "concerning" | "high_risk"


# ============================================================================
# AccountingReviewer
# ============================================================================


class AccountingReviewer:
    """Deterministic accounting-quality analysis engine.

    All computations are self-contained; no network, no LLM.
    """

    # ------------------------------------------------------------------
    # Accruals
    # ------------------------------------------------------------------

    @staticmethod
    def check_accruals(
        net_income: float,
        operating_cf: float,
        total_assets: float,
    ) -> AccrualCheck:
        """Compute total accruals as a fraction of total assets.

        Total Accruals = Net Income − Operating Cash Flow.
        A positive ratio means earnings exceed cash generation — a
        potential warning sign.  A large positive ratio is critical.

        Parameters
        ----------
        net_income : float
            Net income for the period.
        operating_cf : float
            Operating cash flow for the period.
        total_assets : float
            Total assets at period end.

        Returns
        -------
        AccrualCheck
        """
        if total_assets == 0:
            return AccrualCheck(
                metric="accruals_to_assets",
                value=0.0,
                threshold=0.10,
                passed=True,
                severity="ok",
            )

        value = (net_income - operating_cf) / total_assets

        if value > 0.15:
            severity = "critical"
            passed = False
        elif value > 0.05:
            severity = "warning"
            passed = True  # still passes but warning
        else:
            severity = "ok"
            passed = True

        return AccrualCheck(
            metric="accruals_to_assets",
            value=round(value, 6),
            threshold=0.05,
            passed=passed,
            severity=severity,
        )

    # ------------------------------------------------------------------
    # Revenue quality
    # ------------------------------------------------------------------

    @staticmethod
    def check_revenue_quality(
        revenue: float,
        receivables: float,
        deferred_revenue: float,
        prior_revenue: float = 0.0,
        prior_receivables: float = 0.0,
        prior_deferred_revenue: float = 0.0,
    ) -> List[RedFlag]:
        """Detect revenue-recognition red flags.

        1. Receivables growing faster than revenue (channel stuffing).
        2. Deferred revenue declining while reported revenue grows
           (pulling forward future sales).

        Returns
        -------
        List[RedFlag]
        """
        flags: List[RedFlag] = []

        # --- Receivables vs revenue growth ---
        if prior_revenue > 0 and prior_receivables > 0:
            rev_growth = (revenue - prior_revenue) / prior_revenue
            rec_growth = (receivables - prior_receivables) / prior_receivables

            # Receivables growing materially faster than revenue
            if rec_growth > rev_growth + 0.10:
                flags.append(
                    RedFlag(
                        flag_id="rev_rec_001",
                        category="revenue_recognition",
                        description=(
                            f"Receivables growth ({rec_growth:.1%}) exceeds "
                            f"revenue growth ({rev_growth:.1%}) by >10pp — "
                            f"possible channel stuffing or aggressive "
                            f"revenue recognition"
                        ),
                        severity="warning",
                        evidence_refs=[
                            f"revenue: {revenue}, receivables: {receivables}",
                            f"prior_revenue: {prior_revenue}, prior_receivables: {prior_receivables}",
                        ],
                    )
                )

        # --- Deferred revenue decline ---
        if prior_deferred_revenue > 0:
            def_rev_change = (
                (deferred_revenue - prior_deferred_revenue) / prior_deferred_revenue
            )
            if def_rev_change < -0.05:
                flags.append(
                    RedFlag(
                        flag_id="rev_rec_002",
                        category="revenue_recognition",
                        description=(
                            f"Deferred revenue declined "
                            f"({def_rev_change:.1%}) — may indicate "
                            f"pulling forward future sales to boost "
                            f"current-period revenue"
                        ),
                        severity="warning",
                        evidence_refs=[
                            f"deferred_revenue: {deferred_revenue}",
                            f"prior_deferred_revenue: {prior_deferred_revenue}",
                        ],
                    )
                )

        return flags

    # ------------------------------------------------------------------
    # Cash conversion
    # ------------------------------------------------------------------

    @staticmethod
    def check_cash_conversion(net_income: float, fcf: float) -> float:
        """Cash conversion ratio = FCF / Net Income.

        A ratio below 0.8 suggests earnings quality issues: reported
        income is not translating into free cash flow.  A ratio above
        1.0 is healthy.

        Parameters
        ----------
        net_income : float
            Net income for the period.
        fcf : float
            Free cash flow for the period.

        Returns
        -------
        float
            Cash conversion ratio.  Returns 0.0 when net_income is 0.
        """
        if net_income == 0:
            return 0.0
        return fcf / net_income

    # ------------------------------------------------------------------
    # Beneish M-Score (simplified 8-variable model)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_beneish_m(financials: dict) -> float:
        """Compute Beneish M-Score from two-period financial data.

        Uses the 8-index simplified model (Beneish 1999).

        ``financials`` must contain keys for the **current** period
        (plain names) and the **prior** period (``prior_`` prefix):

        - receivables, prior_receivables
        - revenue, prior_revenue
        - gross_margin, prior_gross_margin (or cogs, prior_cogs
          so we derive margin = (revenue - cogs) / revenue)
        - current_assets, prior_current_assets
        - ppe, prior_ppe
        - total_assets, prior_total_assets
        - depreciation, prior_depreciation
        - sga, prior_sga
        - long_term_debt, prior_long_term_debt
        - current_liabilities, prior_current_liabilities
        - net_income
        - operating_cash_flow

        M-Score = -4.84 + 0.920·DSRI + 0.528·GMI + 0.404·AQI
                       + 0.892·SGI + 0.115·DEPI − 0.172·SGAI
                       + 4.679·TATA − 0.327·LVGI

        M > −2.22 suggests a high probability of earnings manipulation.

        Returns
        -------
        float
            The Beneish M-Score.
        """

        def _safe_ratio(num: float, den: float, fallback: float = 1.0) -> float:
            """Return num/den, or fallback when den is 0."""
            if den == 0:
                return fallback
            return num / den

        # Helper: extract current & prior values
        c = financials  # shorthand
        p = {k.replace("prior_", ""): v for k, v in c.items() if k.startswith("prior_")}

        def _c(key: str, fallback: float = 0.0) -> float:
            return c.get(key, fallback)

        def _p(key: str, fallback: float = 0.0) -> float:
            return p.get(key, fallback)

        rev_c = _c("revenue")
        rev_p = _p("revenue")
        rec_c = _c("receivables")
        rec_p = _p("receivables")
        ta_c = _c("total_assets")
        ta_p = _p("total_assets")
        ca_c = _c("current_assets")
        ca_p = _p("current_assets")
        ppe_c = _c("ppe")
        ppe_p = _p("ppe")
        dep_c = _c("depreciation")
        dep_p = _p("depreciation")
        sga_c = _c("sga")
        sga_p = _p("sga")
        cogs_c = _c("cogs")
        cogs_p = _p("cogs")
        ltd_c = _c("long_term_debt")
        ltd_p = _p("long_term_debt")
        cl_c = _c("current_liabilities")
        cl_p = _p("current_liabilities")
        ni_c = _c("net_income")
        ocf_c = _c("operating_cash_flow")

        # Gross margin
        gm_c = _c("gross_margin")
        gm_p = _p("gross_margin")
        if gm_c == 0 and rev_c > 0 and cogs_c is not None:
            gm_c = (rev_c - cogs_c) / rev_c
        if gm_p == 0 and rev_p > 0 and cogs_p is not None:
            gm_p = (rev_p - cogs_p) / rev_p

        # --- DSRI: Days Sales Receivables Index ---
        dsri = _safe_ratio(
            _safe_ratio(rec_c, rev_c),
            _safe_ratio(rec_p, rev_p),
        )

        # --- GMI: Gross Margin Index ---
        gmi = _safe_ratio(
            _safe_ratio(gm_p, gm_c, fallback=1.0), 1.0
        ) if gm_c else 1.0
        # Actually: GMI = GrossMargin_{t-1} / GrossMargin_t
        if gm_c:
            gmi = gm_p / gm_c if gm_c != 0 else 1.0

        # --- AQI: Asset Quality Index ---
        nc_assets_c = 1.0 - _safe_ratio(ca_c + ppe_c, ta_c)
        nc_assets_p = 1.0 - _safe_ratio(ca_p + ppe_p, ta_p)
        aqi = _safe_ratio(nc_assets_c, nc_assets_p)

        # --- SGI: Sales Growth Index ---
        sgi = _safe_ratio(rev_c, rev_p)

        # --- DEPI: Depreciation Index ---
        dep_rate_c = _safe_ratio(dep_c, dep_c + ppe_c)
        dep_rate_p = _safe_ratio(dep_p, dep_p + ppe_p)
        depi = _safe_ratio(dep_rate_p, dep_rate_c)

        # --- SGAI: SG&A Index ---
        sgai = _safe_ratio(
            _safe_ratio(sga_c, rev_c),
            _safe_ratio(sga_p, rev_p),
        )

        # --- TATA: Total Accruals to Total Assets ---
        tata = _safe_ratio(ni_c - ocf_c, ta_c)

        # --- LVGI: Leverage Index ---
        lev_c = _safe_ratio(ltd_c + cl_c, ta_c)
        lev_p = _safe_ratio(ltd_p + cl_p, ta_p)
        lvgi = _safe_ratio(lev_c, lev_p)

        # --- Weighted M-Score ---
        m_score = (
            -4.84
            + 0.920 * dsri
            + 0.528 * gmi
            + 0.404 * aqi
            + 0.892 * sgi
            + 0.115 * depi
            - 0.172 * sgai
            + 4.679 * tata
            - 0.327 * lvgi
        )

        return round(m_score, 4)

    # ------------------------------------------------------------------
    # Altman Z-Score
    # ------------------------------------------------------------------

    @staticmethod
    def compute_altman_z(financials: dict) -> float:
        """Compute Altman Z-Score (original 1968 model for public
        manufacturers).

        Uses five financial ratios:

        - X1 = Working Capital / Total Assets
        - X2 = Retained Earnings / Total Assets
        - X3 = EBIT / Total Assets
        - X4 = Market Cap / Total Liabilities
        - X5 = Sales / Total Assets

        Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5

        Interpretation
        --------------
        Z > 2.99      Safe zone
        1.81 ≤ Z ≤ 2.99  Grey zone
        Z < 1.81      Distress zone

        Parameters
        ----------
        financials : dict
            Must contain: working_capital, total_assets, retained_earnings,
            ebit, market_cap, total_liabilities, revenue.

        Returns
        -------
        float
            The Altman Z-Score.
        """

        def _ratio(num: float, den: float, fallback: float = 0.0) -> float:
            if den == 0:
                return fallback
            return num / den

        wc = financials.get("working_capital", 0.0)
        ta = financials.get("total_assets", 1.0)
        re_ = financials.get("retained_earnings", 0.0)
        ebit = financials.get("ebit", 0.0)
        mcap = financials.get("market_cap", 0.0)
        tl = financials.get("total_liabilities", 1.0)
        rev = financials.get("revenue", 0.0)

        x1 = _ratio(wc, ta)
        x2 = _ratio(re_, ta)
        x3 = _ratio(ebit, ta)
        x4 = _ratio(mcap, tl)
        x5 = _ratio(rev, ta)

        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
        return round(z, 4)

    # ------------------------------------------------------------------
    # Full review
    # ------------------------------------------------------------------

    @staticmethod
    def review(
        financials: dict,
        cash_flow: dict,
        notes: dict,
    ) -> AccountingQualityReport:
        """Run a complete accounting-quality review.

        Parameters
        ----------
        financials : dict
            Two-period financials with ``prior_`` keys for the prior
            period (see ``compute_beneish_m`` for required keys).
        cash_flow : dict
            Must contain ``operating_cf`` and ``free_cash_flow``.
        notes : dict
            Additional context (e.g. ``ticker``, ``period``).

        Returns
        -------
        AccountingQualityReport
        """
        ticker = notes.get("ticker", "UNKNOWN")
        period = notes.get("period", "UNKNOWN")

        ni = financials.get("net_income", 0.0)
        ocf = cash_flow.get("operating_cf", 0.0)
        fcf = cash_flow.get("free_cash_flow", 0.0)
        ta = financials.get("total_assets", 0.0)
        rev = financials.get("revenue", 0.0)
        rec = financials.get("receivables", 0.0)
        def_rev = financials.get("deferred_revenue", 0.0)

        # Prior-period values (with prior_ prefix in the same dict)
        prior = {k.replace("prior_", ""): v for k, v in financials.items()
                 if k.startswith("prior_")}

        checks: List[AccrualCheck] = []
        red_flags: List[RedFlag] = []

        # 1. Accruals check
        acc = AccountingReviewer.check_accruals(ni, ocf, ta)
        checks.append(acc)

        # 2. Revenue quality
        rev_flags = AccountingReviewer.check_revenue_quality(
            revenue=rev,
            receivables=rec,
            deferred_revenue=def_rev,
            prior_revenue=prior.get("revenue", 0.0),
            prior_receivables=prior.get("receivables", 0.0),
            prior_deferred_revenue=prior.get("deferred_revenue", 0.0),
        )
        red_flags.extend(rev_flags)

        # 3. Cash conversion
        ccr = AccountingReviewer.check_cash_conversion(ni, fcf)
        if ccr < 0.8 and ni != 0:
            red_flags.append(
                RedFlag(
                    flag_id="cf_qual_001",
                    category="cash_flow_quality",
                    description=(
                        f"Cash conversion ratio ({ccr:.2f}) below 0.8 — "
                        f"earnings not translating to free cash flow"
                    ),
                    severity="warning",
                    evidence_refs=[
                        f"net_income: {ni}",
                        f"free_cash_flow: {fcf}",
                    ],
                )
            )
        checks.append(
            AccrualCheck(
                metric="cash_conversion",
                value=round(ccr, 4),
                threshold=0.8,
                passed=ccr >= 0.8,
                severity="ok" if ccr >= 0.8 else "warning",
            )
        )

        # 4. Beneish M-Score
        m_score = AccountingReviewer.compute_beneish_m(financials)

        # 5. Altman Z-Score
        z_score = AccountingReviewer.compute_altman_z(financials)

        # 6. Overall assessment
        critical_flags = [f for f in red_flags if f.severity == "critical"]
        warning_count = len(red_flags)
        failed_checks = [c for c in checks if not c.passed]

        if critical_flags or (m_score is not None and m_score > -1.78):
            overall = "high_risk"
        elif warning_count >= 3 or (m_score is not None and m_score > -2.22):
            overall = "concerning"
        elif warning_count >= 1 or failed_checks:
            overall = "watch"
        else:
            overall = "clean"

        return AccountingQualityReport(
            ticker=ticker,
            period=period,
            checks=checks,
            red_flags=red_flags,
            beneish_m_score=m_score,
            altman_z_score=z_score,
            overall_assessment=overall,
        )
