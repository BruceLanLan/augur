# -*- coding: utf-8 -*-
"""
Relative Valuation (D03)
========================

Peer-relative valuation module: compute standard market multiples (P/E, P/B,
P/S, EV/EBITDA, EV/Revenue), rank a ticker against its peers on each metric,
and produce structured comparison tables.

Provenance: standard equity research / investment banking methodology
(Damodaran, CFA curriculum, sell-side comp sheets).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================================
# Valuation multiples
# ============================================================================


@dataclass
class PeerValuation:
    """Valuation multiples for a single ticker.

    All fields are optional — a missing field means the data was unavailable
    (e.g. negative earnings make P/E meaningless).
    """

    ticker: str
    pe: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_revenue: Optional[float] = None


# ============================================================================
# Peer comparison result
# ============================================================================


@dataclass
class PeerComparison:
    """Multi-metric peer benchmarking result for a primary ticker.

    ``rankings`` is 1-based: rank 1 means best-in-peers for that metric
    (lower multiples are better = cheaper).  ``percentiles`` is 0–100
    (100 = cheapest / best rank).
    """

    ticker: str
    peers: List[str] = field(default_factory=list)
    valuations: Dict[str, PeerValuation] = field(default_factory=dict)
    metrics: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)
    rankings: Dict[str, int] = field(default_factory=dict)
    percentiles: Dict[str, float] = field(default_factory=dict)


# ============================================================================
# Multiple computation helpers
# ============================================================================


def compute_pe(price: float, earnings_per_share: float) -> Optional[float]:
    """Compute P/E ratio. Returns None when EPS <= 0."""
    if earnings_per_share <= 0:
        return None
    return price / earnings_per_share


def compute_pb(price: float, book_value_per_share: float) -> Optional[float]:
    """Compute P/B ratio. Returns None when BVPS <= 0."""
    if book_value_per_share <= 0:
        return None
    return price / book_value_per_share


def compute_ps(price: float, sales_per_share: float) -> Optional[float]:
    """Compute P/S ratio. Returns None when SPS <= 0."""
    if sales_per_share <= 0:
        return None
    return price / sales_per_share


def compute_ev_ebitda(enterprise_value: float, ebitda: float) -> Optional[float]:
    """Compute EV/EBITDA multiple. Returns None when EBITDA <= 0."""
    if ebitda <= 0:
        return None
    return enterprise_value / ebitda


def compute_ev_revenue(enterprise_value: float, revenue: float) -> Optional[float]:
    """Compute EV/Revenue multiple. Returns None when revenue <= 0."""
    if revenue <= 0:
        return None
    return enterprise_value / revenue


# ============================================================================
# Ranking & percentile helpers
# ============================================================================


def _rank_ticker(
    ticker: str,
    values: Dict[str, Optional[float]],
) -> int:
    """Compute 1-based rank for *ticker* among *values*.

    Lower multiples are better (cheapest = rank 1).
    Returns len(values) if ticker is absent or its value is None.
    """
    ticker_value = values.get(ticker)
    if ticker_value is None:
        return len(values)

    better = 0
    for v in values.values():
        if v is not None and v < ticker_value:
            better += 1
    return better + 1


def _percentile(rank: int, total: int) -> float:
    """Convert 1-based rank to percentile 0–100 (100 = best)."""
    if total <= 1:
        return 100.0
    return round((total - rank) / (total - 1) * 100, 2)


# ============================================================================
# build_peer_table
# ============================================================================


_METRIC_LABELS: Dict[str, str] = {
    "pe": "P/E",
    "pb": "P/B",
    "ps": "P/S",
    "ev_ebitda": "EV/EBITDA",
    "ev_revenue": "EV/Revenue",
}


def _extract_metric_values(
    valuations: Dict[str, PeerValuation],
    metric: str,
) -> Dict[str, Optional[float]]:
    """Pull one metric's values from a set of PeerValuation objects."""
    result: Dict[str, Optional[float]] = {}
    for t, pv in valuations.items():
        result[t] = getattr(pv, metric, None)
    return result


def build_peer_table(
    ticker: str,
    peers: List[PeerValuation],
) -> PeerComparison:
    """Build a peer comparison table for *ticker* against *peers*.

    Parameters
    ----------
    ticker : str
        The primary ticker to benchmark.
    peers : List[PeerValuation]
        Peer valuation data.  The primary ticker must be among them.

    Returns
    -------
    PeerComparison
        Contains valuations dict, per-metric lookup, rankings, and percentiles.

    Raises
    ------
    ValueError
        If *ticker* is not found among *peers*.
    """
    valuations: Dict[str, PeerValuation] = {}
    ticker_seen = False
    for pv in peers:
        valuations[pv.ticker] = pv
        if pv.ticker == ticker:
            ticker_seen = True

    if not ticker_seen:
        raise ValueError(
            f"Primary ticker {ticker!r} not found in peer list"
        )

    peer_tickers = [pv.ticker for pv in peers if pv.ticker != ticker]

    metric_names = list(_METRIC_LABELS.keys())
    metrics: Dict[str, Dict[str, Optional[float]]] = {}
    for metric in metric_names:
        metrics[metric] = _extract_metric_values(valuations, metric)

    rankings: Dict[str, int] = {}
    percentiles: Dict[str, float] = {}
    total = len(peers)

    for metric in metric_names:
        values = metrics[metric]
        rank = _rank_ticker(ticker, values)
        rankings[metric] = rank
        percentiles[metric] = _percentile(rank, total)

    return PeerComparison(
        ticker=ticker,
        peers=peer_tickers,
        valuations=valuations,
        metrics=metrics,
        rankings=rankings,
        percentiles=percentiles,
    )


def format_peer_table(comparison: PeerComparison) -> str:
    """Render a PeerComparison as a human-readable ASCII table."""
    lines: List[str] = []
    lines.append(f"\n{' Metric ':=^70}")
    lines.append(
        f"{'Metric':<14} {'Ticker':>8} {'Median':>8} "
        f"{'Min':>8} {'Max':>8} {'Rank':>6} {'Pctl':>6}"
    )
    lines.append("-" * 62)

    for metric, label in _METRIC_LABELS.items():
        values = comparison.metrics.get(metric, {})
        ticker_val = values.get(comparison.ticker)
        peer_vals = [
            v for t, v in values.items()
            if t != comparison.ticker and v is not None
        ]
        median_val = _safe_median(peer_vals)
        min_val = min(peer_vals) if peer_vals else None
        max_val = max(peer_vals) if peer_vals else None

        rank = comparison.rankings.get(metric, len(values))
        pctl = comparison.percentiles.get(metric, 0.0)

        lines.append(
            f"{label:<14} "
            f"{_fmt(ticker_val):>8} "
            f"{_fmt(median_val):>8} "
            f"{_fmt(min_val):>8} "
            f"{_fmt(max_val):>8} "
            f"{rank:>6} "
            f"{pctl:>6.1f}"
        )

    lines.append("=" * 62)
    return "\n".join(lines)


def _safe_median(values: List[float]) -> Optional[float]:
    """Return the median of a list, or None if empty."""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2


def _fmt(value: Optional[float]) -> str:
    """Format a float for table display, or 'N/A' if None."""
    if value is None:
        return "N/A"
    return f"{value:.1f}"
