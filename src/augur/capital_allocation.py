# -*- coding: utf-8 -*-
"""
Capital Allocation Review (C04) + Peer Comparison Pack (C08)
============================================================

Analyses how a company deploys its free cash flow — buybacks, dividends,
M&A, capex, debt reduction — and benchmarks key metrics against a
customisable peer group.

Provenance: standard corporate finance / investment analysis methodology
(Greenwald, Damodaran, McKinsey Valuation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ============================================================================
# C04 — Capital Allocation Review
# ============================================================================


@dataclass
class BuybackRecord:
    """A single period's share buyback / repurchase activity.

    Provenance
    ----------
    period           — fiscal period label (e.g. "FY2025", "Q3 2025")
    amount           — total cash spent on repurchases (USD)
    shares_retired   — number of shares retired (fully diluted)
    pct_of_market_cap — amount ÷ average market cap over the period
    """

    period: str
    amount: float
    shares_retired: float
    pct_of_market_cap: float


@dataclass
class DividendRecord:
    """A single period's dividend distribution.

    Provenance
    ----------
    period       — fiscal period label
    dps          — dividend per share (USD)
    payout_ratio — dividends paid ÷ net income
    yield_pct    — annualised dividend yield (dps × frequency ÷ avg price)
    growth_yoy   — year-over-year dps growth rate
    """

    period: str
    dps: float
    payout_ratio: float
    yield_pct: float
    growth_yoy: float


@dataclass
class CapitalAllocationReport:
    """Aggregate capital-allocation picture for a single ticker.

    ``assessment`` is one of:

    * ``"shareholder_friendly"`` — buyback + dividend yield ≥ 4 % and
      payout ratio < 80 %
    * ``"neutral"`` — neither extreme
    * ``"concerning"`` — payout ratio ≥ 100 % or negative FCF with high
      buybacks
    """

    ticker: str
    buybacks: List[BuybackRecord] = field(default_factory=list)
    dividends: List[DividendRecord] = field(default_factory=list)
    mna_activity: List[dict] = field(default_factory=list)
    capex_trend: List[dict] = field(default_factory=list)
    fcf_usage: dict = field(default_factory=dict)
    shareholder_return_yield: float = 0.0
    assessment: str = "neutral"


class CapitalAllocationAnalyzer:
    """Analyse capital-allocation patterns from financial and cash-flow data.

    The ``analyze`` method expects two lists of period-level dictionaries:

    * *financials* — each dict should include ``period``, ``net_income``,
      ``shares_outstanding``, ``avg_share_price``, ``market_cap``,
      ``total_debt``, ``cash_and_equivalents``.
    * *cash_flow* — each dict should include ``period``, ``free_cash_flow``,
      ``capex``, ``buyback_spend``, ``dividends_paid``, ``mna_spend``,
      ``debt_repaid`` (negative = new issuance), ``shares_retired``.

    All monetary values are in USD.  Missing optional keys default to 0.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        financials: List[dict],
        cash_flow: List[dict],
    ) -> CapitalAllocationReport:
        """Run a full capital-allocation analysis.

        Returns a ``CapitalAllocationReport`` with buyback/dividend
        records, M&A activity, capex trend, FCF usage breakdown, and a
        summary assessment.
        """
        # --- Determine ticker (first non-empty period field) -----------
        ticker = self._extract_ticker(financials, cash_flow)

        # --- Sort both lists by period (ascending) ---------------------
        financials = sorted(financials, key=lambda f: f.get("period", ""))
        cash_flow = sorted(cash_flow, key=lambda c: c.get("period", ""))

        # --- Pair financials and cash-flow by period -------------------
        paired = self._pair_periods(financials, cash_flow)

        # --- Build sub-records -----------------------------------------
        buybacks = self._build_buybacks(paired)
        dividends = self._build_dividends(paired)
        mna = self._build_mna(paired)
        capex_trend = self._build_capex_trend(paired)
        fcf_usage = self._build_fcf_usage(paired)
        shareholder_yield = self._compute_shareholder_yield(buybacks, dividends)
        assessment = self._assess(fcf_usage, dividends, buybacks, paired)

        return CapitalAllocationReport(
            ticker=ticker,
            buybacks=buybacks,
            dividends=dividends,
            mna_activity=mna,
            capex_trend=capex_trend,
            fcf_usage=fcf_usage,
            shareholder_return_yield=round(shareholder_yield, 4),
            assessment=assessment,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_ticker(financials: List[dict], cash_flow: List[dict]) -> str:
        for rec in financials:
            if "ticker" in rec:
                return rec["ticker"]
        for rec in cash_flow:
            if "ticker" in rec:
                return rec["ticker"]
        return "UNKNOWN"

    @staticmethod
    def _pair_periods(
        financials: List[dict],
        cash_flow: List[dict],
    ) -> List[dict]:
        """Merge financials and cash-flow dicts by period."""
        cf_by_period = {c.get("period", ""): c for c in cash_flow}
        paired: List[dict] = []
        for fin in financials:
            period = fin.get("period", "")
            cf = cf_by_period.get(period, {})
            paired.append({**fin, **cf})
        # Include cash-flow-only periods not covered by financials
        fin_periods = {f.get("period", "") for f in financials}
        for period, cf in cf_by_period.items():
            if period not in fin_periods:
                paired.append(cf)
        return paired

    # --- Buybacks -------------------------------------------------------

    def _build_buybacks(self, paired: List[dict]) -> List[BuybackRecord]:
        records: List[BuybackRecord] = []
        for p in paired:
            spend = float(p.get("buyback_spend", 0) or 0)
            retired = float(p.get("shares_retired", 0) or 0)
            market_cap = float(p.get("market_cap", 0) or 0)
            pct = (spend / market_cap * 100) if market_cap > 0 else 0.0
            records.append(BuybackRecord(
                period=p.get("period", ""),
                amount=round(spend, 2),
                shares_retired=round(retired, 2),
                pct_of_market_cap=round(pct, 4),
            ))
        return records

    # --- Dividends ------------------------------------------------------

    def _build_dividends(self, paired: List[dict]) -> List[DividendRecord]:
        records: List[DividendRecord] = []
        prev_dps: float | None = None
        for p in paired:
            dividends_paid = float(p.get("dividends_paid", 0) or 0)
            shares = float(p.get("shares_outstanding", 0) or 1)
            net_income = float(p.get("net_income", 0) or 0)
            avg_price = float(p.get("avg_share_price", 0) or 0)

            dps = round(dividends_paid / shares, 4) if shares > 0 else 0.0
            payout = round(dividends_paid / net_income, 4) if net_income > 0 else 0.0
            yld = round(dps / avg_price * 100, 4) if avg_price > 0 else 0.0
            growth = self._yoy_growth(prev_dps, dps)
            prev_dps = dps

            records.append(DividendRecord(
                period=p.get("period", ""),
                dps=dps,
                payout_ratio=payout,
                yield_pct=yld,
                growth_yoy=round(growth, 4),
            ))
        return records

    # --- M&A ------------------------------------------------------------

    @staticmethod
    def _build_mna(paired: List[dict]) -> List[dict]:
        deals: List[dict] = []
        for p in paired:
            spend = float(p.get("mna_spend", 0) or 0)
            deals.append({
                "period": p.get("period", ""),
                "spend": round(spend, 2),
                "targets": p.get("mna_targets", []),
            })
        return deals

    # --- Capex trend ----------------------------------------------------

    @staticmethod
    def _build_capex_trend(paired: List[dict]) -> List[dict]:
        trend: List[dict] = []
        for p in paired:
            capex = float(p.get("capex", 0) or 0)
            fcf = float(p.get("free_cash_flow", 0) or 0)
            revenue = float(p.get("revenue", 0) or 0)
            trend.append({
                "period": p.get("period", ""),
                "capex": round(capex, 2),
                "capex_to_fcf": round(capex / fcf, 4) if fcf > 0 else 0.0,
                "capex_to_revenue": round(capex / revenue * 100, 4) if revenue > 0 else 0.0,
            })
        return trend

    # --- FCF usage ------------------------------------------------------

    @staticmethod
    def _build_fcf_usage(paired: List[dict]) -> dict:
        total_fcf = 0.0
        total_buybacks = 0.0
        total_dividends = 0.0
        total_capex = 0.0
        total_debt_reduction = 0.0

        for p in paired:
            total_fcf += float(p.get("free_cash_flow", 0) or 0)
            total_buybacks += float(p.get("buyback_spend", 0) or 0)
            total_dividends += float(p.get("dividends_paid", 0) or 0)
            total_capex += float(p.get("capex", 0) or 0)
            total_debt_reduction += float(p.get("debt_repaid", 0) or 0)

        # Compute percentages of total uses (not FCF — uses may exceed FCF
        # when funded by debt issuance, so denominator is sum of uses).
        total_uses = total_buybacks + total_dividends + total_capex + max(total_debt_reduction, 0.0)
        if total_uses == 0:
            return {
                "pct_buybacks": 0.0,
                "pct_dividends": 0.0,
                "pct_capex": 0.0,
                "pct_debt_reduction": 0.0,
                "total_fcf": round(total_fcf, 2),
            }

        return {
            "pct_buybacks": round(total_buybacks / total_uses * 100, 2),
            "pct_dividends": round(total_dividends / total_uses * 100, 2),
            "pct_capex": round(total_capex / total_uses * 100, 2),
            "pct_debt_reduction": round(max(total_debt_reduction, 0.0) / total_uses * 100, 2),
            "total_fcf": round(total_fcf, 2),
        }

    # --- Shareholder yield ----------------------------------------------

    @staticmethod
    def _compute_shareholder_yield(
        buybacks: List[BuybackRecord],
        dividends: List[DividendRecord],
    ) -> float:
        """Aggregate buyback yield + dividend yield across all periods."""
        total_bb_yield = sum(b.pct_of_market_cap for b in buybacks)
        total_div_yield = sum(d.yield_pct for d in dividends)
        # Average across periods
        n = max(len(buybacks), len(dividends), 1)
        return (total_bb_yield + total_div_yield) / n

    # --- Assessment -----------------------------------------------------

    @staticmethod
    def _assess(
        fcf_usage: dict,
        dividends: List[DividendRecord],
        buybacks: List[BuybackRecord],
        paired: List[dict],
    ) -> str:
        """Classify the capital-allocation posture."""
        # Check for concerning signs
        for d in dividends:
            if d.payout_ratio >= 1.0:
                return "concerning"

        # Check for negative FCF with high buybacks
        for p in paired:
            fcf = float(p.get("free_cash_flow", 0) or 0)
            bb = float(p.get("buyback_spend", 0) or 0)
            market_cap = float(p.get("market_cap", 0) or 0)
            if fcf < 0 and market_cap > 0 and bb / market_cap > 0.05:
                return "concerning"

        # Shareholder-friendly: buyback + dividend yield ≥ 4 %
        total_yield = (
            sum(b.pct_of_market_cap for b in buybacks)
            + sum(d.yield_pct for d in dividends)
        )
        n_periods = max(len(buybacks), len(dividends), 1)
        avg_yield = total_yield / n_periods

        if avg_yield >= 4.0:
            return "shareholder_friendly"

        return "neutral"

    # --- Utility --------------------------------------------------------

    @staticmethod
    def _yoy_growth(prev: float | None, curr: float) -> float:
        if prev is None or prev == 0:
            return 0.0
        return (curr - prev) / abs(prev)


# ============================================================================
# C08 — Peer Comparison Pack
# ============================================================================


@dataclass
class PeerComparison:
    """Multi-metric peer benchmarking for a single ticker.

    ``rankings`` is 1-based: rank 1 means best-in-peers for that metric
    (where higher-is-better for all metrics).  ``percentile`` is 0–100
    (100 = best).
    """

    ticker: str
    peers: List[str] = field(default_factory=list)
    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    rankings: Dict[str, int] = field(default_factory=dict)
    percentile: Dict[str, float] = field(default_factory=dict)


def build_peer_comparison(
    ticker: str,
    peers: List[str],
    metrics: List[str],
) -> PeerComparison:
    """Build a peer comparison for *ticker* against *peers* on *metrics*.

    Parameters
    ----------
    ticker : str
        The primary ticker to benchmark.
    peers : List[str]
        Peer tickers to compare against (primary ticker included
        automatically if not already in the list).
    metrics : List[str]
        Metric names.  Each must be a key in the global
        ``PEER_METRIC_VALUES`` registry (populated externally).
        Higher values are always treated as better for ranking.

    Returns
    -------
    PeerComparison
        ``metrics`` maps metric → {ticker: value}.
        ``rankings`` maps metric → 1-based rank of *ticker* (1 = best).
        ``percentile`` maps metric → percentile 0–100 (100 = best).
    """
    all_tickers = list(dict.fromkeys([ticker] + peers))  # deduplicate, ticker first

    # Build metrics dict
    metrics_dict: Dict[str, Dict[str, float]] = {}
    for metric in metrics:
        values: Dict[str, float] = {}
        for t in all_tickers:
            values[t] = _lookup_metric(t, metric)
        metrics_dict[metric] = values

    # Compute rankings & percentiles
    rankings: Dict[str, int] = {}
    percentile: Dict[str, float] = {}
    for metric, values in metrics_dict.items():
        # Sort tickers by metric value descending (higher = better)
        sorted_tickers = sorted(values, key=values.get, reverse=True)  # type: ignore[arg-type]
        n = len(sorted_tickers)
        try:
            rank = sorted_tickers.index(ticker) + 1  # 1-based
        except ValueError:
            rank = n
        rankings[metric] = rank
        percentile[metric] = round((n - rank) / max(n - 1, 1) * 100, 2)

    return PeerComparison(
        ticker=ticker,
        peers=peers,
        metrics=metrics_dict,
        rankings=rankings,
        percentile=percentile,
    )


# ---------------------------------------------------------------------------
# Peer metric registry (populated externally)
# ---------------------------------------------------------------------------

PEER_METRIC_VALUES: Dict[str, Dict[str, float]] = {}


def register_peer_metrics(data: Dict[str, Dict[str, float]]) -> None:
    """Register metric values for multiple tickers at once.

    ``data`` should be ``{ticker: {metric_name: value, …}, …}``.
    Values for the same ticker/metric pair are overwritten on subsequent
    calls.
    """
    for t, m in data.items():
        PEER_METRIC_VALUES.setdefault(t, {}).update(m)


def _lookup_metric(ticker: str, metric: str) -> float:
    """Resolve a metric value for *ticker*, defaulting to 0.0."""
    return PEER_METRIC_VALUES.get(ticker, {}).get(metric, 0.0)
