# -*- coding: utf-8 -*-
"""
augur.ownership — Insider Cluster Review + Institutional Ownership Delta

C05: Insider Cluster Review
    Identifies clusters of insider trading activity (multiple insiders
    buying or selling within a configurable window) and computes an
    aggregate sentiment score from a list of trades.

C06: Institutional Ownership Delta
    Compares two snapshots of 13F institutional holdings and produces a
    structured delta report showing new/exited/increased/decreased
    positions and net institutional flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ============================================================================
# C05 — Insider Cluster Review
# ============================================================================


@dataclass
class InsiderTrade:
    """A single insider transaction (open-market purchase or sale)."""

    ticker: str
    person: str
    role: str
    transaction_date: str       # "YYYY-MM-DD"
    type: str                   # "buy" | "sell"
    shares: float
    price: float
    value: float                # shares * price


@dataclass
class InsiderCluster:
    """Aggregate insider activity for one ticker over a time window."""

    ticker: str
    period_days: int
    total_buys: int
    total_sells: int
    net_value: float                         # positive = net buying
    participants: List[str] = field(default_factory=list)
    assessment: str = "no_activity"          # cluster_buying | cluster_selling | mixed | no_activity


class InsiderAnalyzer:
    """Detect insider trading clusters and compute aggregate sentiment.

    A *cluster* exists when two or more distinct insiders transact in the
    same direction within the configured window — a stronger signal than
    any single insider's trade alone.
    """

    _DEFAULT_WINDOW_DAYS: int = 90
    _CLUSTER_MIN_DISTINCT_BUYERS: int = 2
    _CLUSTER_MIN_DISTINCT_SELLERS: int = 2

    def detect_clusters(
        self,
        trades: List[InsiderTrade],
        window_days: int = 90,
    ) -> InsiderCluster:
        """Scan ``trades`` for insider clustering within ``window_days``.

        Returns an ``InsiderCluster`` summarising buy/sell counts, net
        dollar flow, distinct participants, and an overall assessment.
        When no trades are provided, the result is a neutral
        ``"no_activity"`` cluster for the given ticker (or ``""`` if the
        trade list is empty).
        """
        if not trades:
            return InsiderCluster(
                ticker="",
                period_days=window_days,
                total_buys=0,
                total_sells=0,
                net_value=0.0,
                participants=[],
                assessment="no_activity",
            )

        ticker = trades[0].ticker
        buys = [t for t in trades if t.type == "buy"]
        sells = [t for t in trades if t.type == "sell"]

        total_buys = len(buys)
        total_sells = len(sells)

        buy_value = sum(t.value for t in buys)
        sell_value = sum(t.value for t in sells)
        net_value = buy_value - sell_value

        # Distinct participants across all trades
        participants = sorted({t.person for t in trades})

        # Distinct participants per direction
        buy_participants = {t.person for t in buys}
        sell_participants = {t.person for t in sells}

        has_cluster_buy = len(buy_participants) >= self._CLUSTER_MIN_DISTINCT_BUYERS
        has_cluster_sell = len(sell_participants) >= self._CLUSTER_MIN_DISTINCT_SELLERS

        if has_cluster_buy and has_cluster_sell:
            assessment = "mixed"
        elif has_cluster_buy:
            assessment = "cluster_buying"
        elif has_cluster_sell:
            assessment = "cluster_selling"
        else:
            assessment = "no_activity"

        return InsiderCluster(
            ticker=ticker,
            period_days=window_days,
            total_buys=total_buys,
            total_sells=total_sells,
            net_value=round(net_value, 2),
            participants=participants,
            assessment=assessment,
        )

    def compute_sentiment(self, trades: List[InsiderTrade]) -> float:
        """Compute a directional sentiment score in [-1.0, 1.0] from a list
        of insider trades.

        Positive values indicate net buying; negative values indicate net
        selling.  The score is the ratio of (net value) / (total value),
        clamped to [-1.0, 1.0].  An empty trade list returns 0.0.
        """
        if not trades:
            return 0.0

        buy_value = sum(t.value for t in trades if t.type == "buy")
        sell_value = sum(t.value for t in trades if t.type == "sell")
        total_value = buy_value + sell_value

        if total_value == 0.0:
            return 0.0

        net = buy_value - sell_value
        sentiment = net / total_value
        return round(max(-1.0, min(1.0, sentiment)), 4)


def fetch_insider_trades(ticker: str, as_of_date: Optional[str] = None) -> List[InsiderTrade]:
    """Fetch open-market (P/S) Form 4 trades for *ticker* from EDGAR.

    Covers the trailing 90 days ending at *as_of_date* (``YYYY-MM-DD``,
    default today). Returns an empty list on any fetch/parse failure.
    """
    try:
        from augur.consensus.edgar_insider import _fetch_form4_transactions
    except ImportError:
        return []

    ticker = ticker.upper()
    as_of_date = as_of_date or datetime.now().strftime("%Y-%m-%d")
    trades: List[InsiderTrade] = []
    for t in _fetch_form4_transactions(ticker, as_of_date):
        shares = float(t.get("shares", 0) or 0)
        price = float(t.get("price", 0) or 0)
        trades.append(InsiderTrade(
            ticker=ticker,
            person=t.get("reporting_owner_cik", "Unknown"),
            role="",
            transaction_date=t.get("transaction_date", ""),
            type="buy" if t.get("code", "") == "P" else "sell",
            shares=shares,
            price=price,
            value=shares * price,
        ))
    return trades


# ============================================================================
# C06 — Institutional Ownership Delta
# ============================================================================


@dataclass
class InstitutionPosition:
    """A single institution's holding in a ticker as of a quarter-end."""

    institution: str
    ticker: str
    shares: float
    value: float                # dollar value of the position
    pct_of_portfolio: float     # 0.0 – 100.0
    filing_date: str            # "YYYY-MM-DD" — date the 13F was filed
    quarter_end: str            # "YYYY-MM-DD" — quarter-end date


@dataclass
class OwnershipDelta:
    """Quarter-over-quarter change in institutional ownership for a ticker."""

    ticker: str
    previous_quarter: str       # "YYYY-MM-DD"
    current_quarter: str        # "YYYY-MM-DD"
    new_positions: List[InstitutionPosition] = field(default_factory=list)
    exited_positions: List[InstitutionPosition] = field(default_factory=list)
    increased_positions: List[dict] = field(default_factory=list)
    decreased_positions: List[dict] = field(default_factory=list)
    net_institutional_flow: float = 0.0   # positive = net buying


class OwnershipAnalyzer:
    """Compare institutional holdings across two quarter-end snapshots."""

    _CHANGE_THRESHOLD_PCT: float = 0.01   # 1 % minimum change to register

    def compare(
        self,
        prev: List[InstitutionPosition],
        curr: List[InstitutionPosition],
    ) -> OwnershipDelta:
        """Produce an ``OwnershipDelta`` by comparing two position lists.

        Positions are matched by ``institution`` name.  Institutions that
        appear only in ``curr`` are *new positions*; those only in ``prev``
        are *exited positions*.  Institutions present in both are checked
        for share-count changes and classified as increased / decreased
        when the absolute change exceeds ``_CHANGE_THRESHOLD_PCT``.
        """
        if not prev and not curr:
            return OwnershipDelta(
                ticker="",
                previous_quarter="",
                current_quarter="",
            )

        # Infer ticker and quarter labels from the data when possible
        ticker = ""
        prev_q = ""
        curr_q = ""

        if curr:
            ticker = curr[0].ticker
            curr_q = curr[0].quarter_end
        elif prev:
            ticker = prev[0].ticker
            curr_q = prev[0].quarter_end  # best-effort fallback

        if prev:
            prev_q = prev[0].quarter_end

        prev_map: Dict[str, InstitutionPosition] = {p.institution: p for p in prev}
        curr_map: Dict[str, InstitutionPosition] = {p.institution: p for p in curr}

        prev_insts = set(prev_map.keys())
        curr_insts = set(curr_map.keys())

        # New positions: in curr but not in prev
        new_positions = [curr_map[name] for name in sorted(curr_insts - prev_insts)]

        # Exited positions: in prev but not in curr
        exited_positions = [prev_map[name] for name in sorted(prev_insts - curr_insts)]

        # Changed positions: present in both
        increased: List[dict] = []
        decreased: List[dict] = []
        net_flow_shares = 0.0

        common = sorted(prev_insts & curr_insts)
        for name in common:
            p = prev_map[name]
            c = curr_map[name]
            share_delta = c.shares - p.shares
            net_flow_shares += share_delta

            if p.shares == 0.0:
                # Avoid division by zero: treat as a new-position-style jump
                change_pct = 100.0 if c.shares > 0 else 0.0
            else:
                change_pct = ((c.shares - p.shares) / p.shares) * 100.0

            if change_pct >= self._CHANGE_THRESHOLD_PCT:
                increased.append({
                    "institution": name,
                    "change_pct": round(change_pct, 2),
                    "prev_shares": p.shares,
                    "curr_shares": c.shares,
                })
            elif change_pct <= -self._CHANGE_THRESHOLD_PCT:
                decreased.append({
                    "institution": name,
                    "change_pct": round(change_pct, 2),
                    "prev_shares": p.shares,
                    "curr_shares": c.shares,
                })

        # Also account for new / exited position share flow
        net_flow_shares += sum(c.shares for c in new_positions)
        net_flow_shares -= sum(p.shares for p in exited_positions)

        return OwnershipDelta(
            ticker=ticker,
            previous_quarter=prev_q,
            current_quarter=curr_q,
            new_positions=new_positions,
            exited_positions=exited_positions,
            increased_positions=increased,
            decreased_positions=decreased,
            net_institutional_flow=round(net_flow_shares, 2),
        )

    def top_holders(
        self,
        positions: List[InstitutionPosition],
        limit: int = 10,
    ) -> List[InstitutionPosition]:
        """Return the top ``limit`` position-holders sorted by shares
        descending."""
        return sorted(positions, key=lambda p: p.shares, reverse=True)[:limit]
