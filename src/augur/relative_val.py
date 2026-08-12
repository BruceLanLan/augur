
"""Relative Valuation (D03) — peer comparison multiples and rankings."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class PeerValuation:
    ticker: str; pe: float = 0; pb: float = 0; ps: float = 0
    ev_ebitda: float = 0; ev_revenue: float = 0

@dataclass
class RelativeValuationReport:
    ticker: str; peers: List[str]; metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    rankings: Dict[str, int] = field(default_factory=dict)
    percentile: Dict[str, float] = field(default_factory=dict)
    valuation_summary: str = ""

def build_peer_table(ticker: str, peers_data: Dict[str, PeerValuation]) -> RelativeValuationReport:
    metrics = {}
    for metric in ["pe", "pb", "ps", "ev_ebitda", "ev_revenue"]:
        values = {}
        for t, pv in peers_data.items():
            val = getattr(pv, metric, 0)
            if val and val > 0:
                values[t] = val
        metrics[metric] = values

    rankings = {}
    percentile = {}
    if ticker in peers_data:
        for metric, values in metrics.items():
            if ticker in values:
                sorted_vals = sorted(values.items(), key=lambda x: x[1])
                rank = sum(1 for _, v in sorted_vals if v < values[ticker]) + 1
                rankings[metric] = rank
                n = len(values)
                percentile[metric] = round((n - rank) / max(n - 1, 1) * 100, 1)

    summary = "neutral"
    if rankings:
        avg_rank = sum(rankings.values()) / len(rankings)
        n = len(peers_data)
        if avg_rank <= n * 0.25: summary = "undervalued"
        elif avg_rank <= n * 0.50: summary = "fairly_valued"
        elif avg_rank <= n * 0.75: summary = "overvalued"
        else: summary = "significantly_overvalued"

    return RelativeValuationReport(
        ticker=ticker, peers=list(peers_data.keys()),
        metrics=metrics, rankings=rankings, percentile=percentile,
        valuation_summary=summary,
    )
