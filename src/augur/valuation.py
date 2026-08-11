"""
Deterministic DCF + WACC Builder + Scenario Lab
===============================================
Pure Python valuation engine. LLM 只做叙述，Python 负责计算。

All calculations use decimal.Decimal for precision.
Provenance: standard corporate finance methodology
(Brealey-Myers, Damodaran, McKinsey Valuation).
"""

from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Precision — financial calculations demand it
# ---------------------------------------------------------------------------
getcontext().prec = 28


def _d(val) -> Decimal:
    """Convert a float/int/str/Decimal to Decimal losslessly via str."""
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


# ============================================================================
# 1. WACC Builder
# ============================================================================

@dataclass
class WACCInputs:
    """Weighted Average Cost of Capital inputs.

    Provenance
    ----------
    risk_free_rate     — US 10Y Treasury constant-maturity yield
                          (source: treasury.gov / FRED series DGS10)
    equity_risk_premium — Damodaran implied ERP, typically 5–6 %
                          (source: pages.stern.nyu.edu/~adamodar)
    beta               — 5Y monthly stock beta vs S&P 500
                          (source: Bloomberg / Yahoo Finance / Reuters)
    cost_of_debt       — pre-tax YTM on outstanding corporate bonds
                          (source: FINRA TRACE / company filings)
    tax_rate           — statutory corporate income tax rate
                          (source: IRS / company 10-K)
    equity_weight      — E / (D + E)  from market cap & total debt
    debt_weight        — D / (D + E)
    """
    risk_free_rate: float
    equity_risk_premium: float
    beta: float
    cost_of_equity: float = 0.0    # auto-computed: CAPM  rf + β·ERP
    cost_of_debt: float = 0.0
    tax_rate: float = 0.21         # US federal statutory rate (21 %)
    equity_weight: float = 0.85
    debt_weight: float = 0.15


def compute_wacc(inputs: WACCInputs) -> float:
    """Weighted Average Cost of Capital — Damodaran formula.

    .. math::
        Ke  = R_f + β · ERP                (CAPM)
        WACC = Ke · E/(D+E) + Kd · (1 − t) · D/(D+E)

    All internal arithmetic uses decimal.Decimal; the final result is
    returned as float for downstream convenience.
    """
    rf = _d(inputs.risk_free_rate)
    erp = _d(inputs.equity_risk_premium)
    beta = _d(inputs.beta)
    kd = _d(inputs.cost_of_debt)
    t = _d(inputs.tax_rate)
    ew = _d(inputs.equity_weight)
    dw = _d(inputs.debt_weight)

    # CAPM — cost of equity
    ke = rf + beta * erp
    inputs.cost_of_equity = float(ke)

    # WACC
    after_tax_debt = kd * (Decimal("1") - t)
    wacc = ke * ew + after_tax_debt * dw

    return float(wacc)


# ============================================================================
# 2. Deterministic DCF (two-stage)
# ============================================================================

@dataclass
class DCFInputs:
    """Two-stage Discounted Cash Flow model inputs.

    Stage 1 — explicit high-growth period (``stage1_years``).
    Stage 2 — perpetual terminal growth (Gordon Growth Model).

    Provenance
    ----------
    free_cash_flow        — unlevered FCF = OpCF − CapEx
                             (source: cash-flow statement, latest FY)
    growth_rate_stage1    — near-term revenue / FCF CAGR
                             (source: sell-side consensus / mgmt guidance)
    stage1_years          — explicit forecast horizon (typically 5–10)
    growth_rate_terminal  — perpetual growth ≤ risk-free rate
                             (source: long-run nominal GDP, ~2–3 %)
    wacc                  — discount rate from ``compute_wacc()``
    shares_outstanding    — fully diluted shares (source: 10‑K / 10‑Q)
    net_debt              — total debt − cash & equivalents
    """
    free_cash_flow: float
    growth_rate_stage1: float
    stage1_years: int = 5
    growth_rate_terminal: float = 0.025
    wacc: float = 0.10
    shares_outstanding: float = 1_000_000_000.0
    net_debt: float = 0.0


@dataclass
class DCFOutput:
    """Two-stage DCF result.

    All monetary values in the same currency unit as ``free_cash_flow``.
    ``sensitivity`` is a WACC × terminal-growth fair-value grid
    (``{"wacc_0.0800": [{"growth": ..., "fair_value": ...}, …], …}``).
    Grid cells where WACC ≤ growth are ``None`` (Gordon model invalid).
    """
    enterprise_value: float
    equity_value: float
    fair_value_per_share: float
    stage1_pv: float
    terminal_pv: float
    sensitivity: Dict[str, List[Dict]]


def _dcf_core(inputs: DCFInputs) -> Tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    """Core two-stage DCF returning raw Decimals.

    Returns (enterprise_value, equity_value, fair_value_per_share,
             stage1_pv, terminal_pv).
    """
    fcf = _d(inputs.free_cash_flow)
    g1 = _d(inputs.growth_rate_stage1)
    g_term = _d(inputs.growth_rate_terminal)
    wacc = _d(inputs.wacc)
    n = inputs.stage1_years
    shares = _d(inputs.shares_outstanding)
    net_debt = _d(inputs.net_debt)

    # --- Stage 1: explicit forecast period --------------------------------
    stage1_pv = Decimal("0")
    for t in range(1, n + 1):
        fcf_t = fcf * (Decimal("1") + g1) ** t
        pv_t = fcf_t / (Decimal("1") + wacc) ** t
        stage1_pv += pv_t

    # --- Stage 2: terminal value (Gordon Growth Model) --------------------
    # TV = FCF_{n} · (1 + g_term) / (WACC − g_term)
    fcf_n = fcf * (Decimal("1") + g1) ** n
    terminal_value = fcf_n * (Decimal("1") + g_term) / (wacc - g_term)

    # Discount terminal value back to t=0
    terminal_pv = terminal_value / (Decimal("1") + wacc) ** n

    # --- Enterprise → Equity → per share ----------------------------------
    enterprise_value = stage1_pv + terminal_pv
    equity_value = enterprise_value - net_debt
    fair_value_per_share = equity_value / shares

    return enterprise_value, equity_value, fair_value_per_share, stage1_pv, terminal_pv


def compute_dcf(inputs: DCFInputs) -> DCFOutput:
    """Two-stage DCF valuation.

    1. Project FCF for ``stage1_years`` at ``growth_rate_stage1``.
    2. Discount each year's FCF at ``wacc``.
    3. Compute terminal value via Gordon Growth Model.
    4. Discount terminal value to present.
    5. Subtract net debt → equity value → fair value per share.
    6. Build a WACC × terminal-growth sensitivity grid.
    """
    ev, eq, fv, s1_pv, t_pv = _dcf_core(inputs)
    sensitivity = _build_sensitivity(inputs)
    return DCFOutput(
        enterprise_value=float(ev),
        equity_value=float(eq),
        fair_value_per_share=float(fv),
        stage1_pv=float(s1_pv),
        terminal_pv=float(t_pv),
        sensitivity=sensitivity,
    )


def _build_sensitivity(inputs: DCFInputs) -> Dict[str, List[Dict]]:
    """Build WACC × terminal-growth sensitivity grid.

    WACC varies ±2 pp in 0.5 pp steps around ``inputs.wacc``.
    Terminal growth varies ±2 pp in 0.5 pp steps around
    ``inputs.growth_rate_terminal``.

    Cells where WACC ≤ terminal growth are stored with
    ``fair_value: None`` (Gordon model denominator ≤ 0).
    """
    wacc_base = _d(inputs.wacc)
    g_base = _d(inputs.growth_rate_terminal)

    # ±2 pp in 0.5 pp steps → 9 points
    wacc_offsets = [_d(f"{i * 0.5 - 2:.1f}") for i in range(9)]
    growth_offsets = [_d(f"{i * 0.5 - 2:.1f}") for i in range(9)]

    wacc_values = [wacc_base + offset for offset in wacc_offsets]
    growth_values = [g_base + offset for offset in growth_offsets]

    result: Dict[str, List[Dict]] = {}
    for w in wacc_values:
        key = f"wacc_{float(w):.4f}"
        row: List[Dict] = []
        for g in growth_values:
            if w <= g:
                # Gordon model invalid — denominator ≤ 0
                row.append({"growth": float(g), "fair_value": None})
            else:
                variant = DCFInputs(
                    free_cash_flow=inputs.free_cash_flow,
                    growth_rate_stage1=inputs.growth_rate_stage1,
                    stage1_years=inputs.stage1_years,
                    growth_rate_terminal=float(g),
                    wacc=float(w),
                    shares_outstanding=inputs.shares_outstanding,
                    net_debt=inputs.net_debt,
                )
                _, _, fv, _, _ = _dcf_core(variant)
                row.append({"growth": float(g), "fair_value": float(fv)})
        result[key] = row

    return result


# ============================================================================
# 3. Bull / Base / Bear Scenario Lab
# ============================================================================

@dataclass
class ScenarioInputs:
    """Three-scenario growth assumptions.

    ``base_margin`` is the operating margin under the base case and is
    used to scale free cash flow proportionally in bull / bear cases
    (e.g. bull FCF = base FCF × (1 + Δmargin)).
    """
    base_growth: float
    base_margin: float = 0.20        # 20 % operating margin
    bull_growth: float = 0.15
    bear_growth: float = 0.0
    bull_probability: float = 0.25
    base_probability: float = 0.50
    bear_probability: float = 0.25


@dataclass
class ScenarioOutput:
    """Results for all three scenarios plus probability-weighted fair value."""
    bull_case: DCFOutput
    base_case: DCFOutput
    bear_case: DCFOutput
    probability_weighted: float  # probability-weighted fair value per share


def run_scenarios(dcf_base: DCFInputs, scenarios: ScenarioInputs) -> ScenarioOutput:
    """Run Bull / Base / Bear DCF scenarios.

    Each scenario uses the same DCF structure but overrides
    ``growth_rate_stage1``.  Free cash flow is scaled by the margin
    ratio relative to the base margin (bull expands margin, bear
    contracts it).

    The probability-weighted fair value is returned in
    ``ScenarioOutput.probability_weighted``.
    """
    margin_base = _d(scenarios.base_margin)

    def _case(growth: float) -> DCFOutput:
        # Scale FCF by margin ratio (capped at 0 for bear)
        margin_ratio = (margin_base + _d(growth) - _d(scenarios.base_growth)) / margin_base
        adjusted_fcf = max(_d(dcf_base.free_cash_flow) * margin_ratio, Decimal("0"))
        variant = DCFInputs(
            free_cash_flow=float(adjusted_fcf),
            growth_rate_stage1=growth,
            stage1_years=dcf_base.stage1_years,
            growth_rate_terminal=dcf_base.growth_rate_terminal,
            wacc=dcf_base.wacc,
            shares_outstanding=dcf_base.shares_outstanding,
            net_debt=dcf_base.net_debt,
        )
        return compute_dcf(variant)

    bull = _case(scenarios.bull_growth)
    base = _case(scenarios.base_growth)
    bear = _case(scenarios.bear_growth)

    prob_weighted = (
        _d(scenarios.bull_probability) * _d(bull.fair_value_per_share)
        + _d(scenarios.base_probability) * _d(base.fair_value_per_share)
        + _d(scenarios.bear_probability) * _d(bear.fair_value_per_share)
    )

    return ScenarioOutput(
        bull_case=bull,
        base_case=base,
        bear_case=bear,
        probability_weighted=float(prob_weighted),
    )


# ============================================================================
# 4. Sensitivity Grid & Reverse DCF
# ============================================================================

def sensitivity_grid(
    dcf: DCFInputs,
    wacc_range: Tuple[float, float],
    growth_range: Tuple[float, float],
    steps: int = 9,
) -> List[List[float]]:
    """Compute a fair-value sensitivity matrix.

    Parameters
    ----------
    wacc_range : (min, max)  inclusive WACC range.
    growth_range : (min, max)  inclusive terminal-growth range.
    steps : number of points in each dimension (default 9).

    Returns
    -------
    A ``steps × steps`` matrix where rows are WACC values and columns
    are terminal-growth values.  Cells where WACC ≤ growth are ``0.0``.
    """
    wacc_min, wacc_max = wacc_range
    g_min, g_max = growth_range

    wacc_step = (wacc_max - wacc_min) / max(steps - 1, 1)
    g_step = (g_max - g_min) / max(steps - 1, 1)

    grid: List[List[float]] = []
    for i in range(steps):
        w = wacc_min + i * wacc_step
        row: List[float] = []
        for j in range(steps):
            g = g_min + j * g_step
            if w <= g:
                row.append(0.0)
            else:
                variant = DCFInputs(
                    free_cash_flow=dcf.free_cash_flow,
                    growth_rate_stage1=dcf.growth_rate_stage1,
                    stage1_years=dcf.stage1_years,
                    growth_rate_terminal=g,
                    wacc=w,
                    shares_outstanding=dcf.shares_outstanding,
                    net_debt=dcf.net_debt,
                )
                _, _, fv, _, _ = _dcf_core(variant)
                row.append(float(fv))
        grid.append(row)
    return grid


def reverse_dcf(
    market_price: float,
    shares: float,
    net_debt: float,
    wacc: float,
    free_cash_flow: float,
    growth_rate_terminal: float = 0.025,
    stage1_years: int = 5,
    tolerance: float = 1e-9,
    max_iterations: int = 100,
) -> Optional[float]:
    """Implied growth rate from current market price.

    Uses binary search to find the ``growth_rate_stage1`` that makes
    the DCF fair value equal to ``market_price``.  Terminal growth,
    WACC, and the explicit forecast horizon are held fixed.

    Returns
    -------
    The implied growth rate as a float, or ``None`` if the search does
    not converge within ``max_iterations``.
    """
    target_ev = _d(market_price) * _d(shares) + _d(net_debt)

    lo = Decimal("-0.99")   # -99 % floor — near-total collapse
    hi = Decimal("2.0")     # +200 % ceiling — hyper-growth

    for _ in range(max_iterations):
        mid = (lo + hi) / Decimal("2")
        variant = DCFInputs(
            free_cash_flow=free_cash_flow,
            growth_rate_stage1=float(mid),
            stage1_years=stage1_years,
            growth_rate_terminal=growth_rate_terminal,
            wacc=wacc,
            shares_outstanding=shares,
            net_debt=net_debt,
        )
        ev, _, _, _, _ = _dcf_core(variant)

        if abs(ev - target_ev) < _d(str(tolerance)):
            return float(mid)

        if ev < target_ev:
            lo = mid  # need higher growth
        else:
            hi = mid  # need lower growth

    return float((lo + hi) / Decimal("2"))
