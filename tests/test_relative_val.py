# -*- coding: utf-8 -*-
"""
tests/test_relative_val.py — D03 Relative Valuation tests.

Validates:
  1. compute_pe returns correct ratio for positive EPS.
  2. compute_pe returns None for zero or negative EPS.
  3. compute_pb / compute_ps return correct ratios.
  4. compute_ev_ebitda / compute_ev_revenue return correct ratios.
  5. build_peer_table computes rankings correctly.
  6. build_peer_table raises ValueError when ticker not in peers.
  7. build_peer_table percentiles are 0–100 with 100 = best.
  8. format_peer_table produces expected column headers.
  9. PeerComparison with single peer gives 100th percentile.
 10. Multiple computation handles mixed missing values.
"""

from __future__ import annotations

import pytest

from augur.relative_val import (
    PeerComparison,
    PeerValuation,
    build_peer_table,
    compute_ev_ebitda,
    compute_ev_revenue,
    compute_pb,
    compute_pe,
    compute_ps,
    format_peer_table,
)


# ---------------------------------------------------------------------------
# 1. compute_pe
# ---------------------------------------------------------------------------

def test_compute_pe_normal():
    """P/E is price / EPS when EPS > 0."""
    assert compute_pe(150.0, 5.0) == 30.0
    assert compute_pe(100.0, 2.5) == 40.0


def test_compute_pe_zero_or_negative_eps():
    """P/E returns None when EPS <= 0."""
    assert compute_pe(150.0, 0.0) is None
    assert compute_pe(150.0, -2.0) is None


# ---------------------------------------------------------------------------
# 2. compute_pb / compute_ps
# ---------------------------------------------------------------------------

def test_compute_pb():
    """P/B is price / book value per share."""
    assert compute_pb(200.0, 50.0) == 4.0


def test_compute_pb_negative_book():
    """P/B returns None for negative book value."""
    assert compute_pb(200.0, -10.0) is None


def test_compute_ps():
    """P/S is price / sales per share."""
    assert compute_ps(150.0, 30.0) == 5.0


# ---------------------------------------------------------------------------
# 3. EV multiples
# ---------------------------------------------------------------------------

def test_compute_ev_ebitda():
    """EV/EBITDA returns enterprise value / ebitda."""
    assert compute_ev_ebitda(1_000_000_000.0, 100_000_000.0) == 10.0


def test_compute_ev_ebitda_negative():
    """EV/EBITDA returns None for negative EBITDA."""
    assert compute_ev_ebitda(1_000_000_000.0, -50_000_000.0) is None


def test_compute_ev_revenue():
    """EV/Revenue returns enterprise value / revenue."""
    assert compute_ev_revenue(500_000_000.0, 250_000_000.0) == 2.0


# ---------------------------------------------------------------------------
# 4. build_peer_table — ranking & percentile
# ---------------------------------------------------------------------------

def _make_peers(*ticker_pe_pairs) -> list:
    """Helper: build PeerValuation list from (ticker, pe) pairs."""
    return [
        PeerValuation(ticker=t, pe=pe)
        for t, pe in ticker_pe_pairs
    ]


def test_build_peer_table_ranking():
    """Lowest P/E gets rank 1 (cheapest)."""
    peers = _make_peers(
        ("AAPL", 25.0),
        ("MSFT", 30.0),
        ("GOOGL", 20.0),
    )
    result = build_peer_table("AAPL", peers)
    # Values: AAPL=25, MSFT=30, GOOGL=20 → GOOGL best(1), AAPL 2nd
    assert result.rankings["pe"] == 2


def test_build_peer_table_best_rank():
    """Ticker with the lowest multiple gets rank 1."""
    peers = _make_peers(("AAPL", 15.0), ("MSFT", 30.0), ("GOOGL", 25.0))
    result = build_peer_table("AAPL", peers)
    assert result.rankings["pe"] == 1
    assert result.percentiles["pe"] == 100.0


def test_build_peer_table_worst_rank():
    """Ticker with the highest multiple gets worst rank."""
    peers = _make_peers(("AAPL", 40.0), ("MSFT", 30.0), ("GOOGL", 20.0))
    result = build_peer_table("AAPL", peers)
    assert result.rankings["pe"] == 3


def test_build_peer_table_raises_missing_ticker():
    """Raises ValueError when primary ticker not in peer list."""
    peers = _make_peers(("MSFT", 30.0), ("GOOGL", 20.0))
    with pytest.raises(ValueError, match="AAPL"):
        build_peer_table("AAPL", peers)


def test_build_peer_table_single_peer():
    """Single peer: ticker is both best and worst → rank 1, percentile 100."""
    peers = _make_peers(("AAPL", 25.0))
    result = build_peer_table("AAPL", peers)
    assert result.rankings["pe"] == 1
    assert result.percentiles["pe"] == 100.0
    assert result.peers == []


# ---------------------------------------------------------------------------
# 5. build_peer_table — mixed missing values
# ---------------------------------------------------------------------------

def test_build_peer_table_none_value_ranked_last():
    """Ticker with None (missing) value gets worst rank."""
    pv_none = PeerValuation(ticker="AAPL", pe=None)
    pv_ok = PeerValuation(ticker="MSFT", pe=20.0)
    result = build_peer_table("AAPL", [pv_none, pv_ok])
    # AAPL has None → treated as worst
    assert result.rankings["pe"] == 2


# ---------------------------------------------------------------------------
# 6. format_peer_table
# ---------------------------------------------------------------------------

def test_format_peer_table_includes_headers():
    """Format output includes expected column headers and primary ticker."""
    peers = _make_peers(("AAPL", 25.0), ("MSFT", 30.0), ("GOOGL", 20.0))
    result = build_peer_table("AAPL", peers)
    output = format_peer_table(result)
    assert "P/E" in output
    assert "P/B" in output
    assert "P/S" in output
    assert "EV/EBITDA" in output
    assert "EV/Revenue" in output
    assert "Rank" in output
    assert "Pctl" in output


def test_format_peer_table_handles_all_none():
    """Format table with all-None values doesn't crash."""
    peers = [
        PeerValuation(ticker="AAPL"),
        PeerValuation(ticker="MSFT"),
    ]
    result = build_peer_table("AAPL", peers)
    output = format_peer_table(result)
    assert "N/A" in output
