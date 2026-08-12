# -*- coding: utf-8 -*-
"""Batch analysis CLI — parallel multi-ticker market context fetch."""
from __future__ import annotations
from typing import List


def run_batch_analyze(tickers: List[str], max_workers: int = 5) -> str:
    """Fetch market context for multiple tickers in parallel.

    Returns a formatted table of price/PE/sector per ticker.
    """
    from augur.data import fetch_market_context_batch

    tickers = [t.upper() for t in tickers if t and t.strip()]
    if not tickers:
        return "Error: no tickers provided"
    if len(tickers) > 50:
        return "Error: max 50 tickers per batch"

    contexts = fetch_market_context_batch(tickers, max_workers=max_workers)

    lines = ["═══ Batch Analysis ═══", ""]
    lines.append(f"{'Ticker':<8} {'Price':>10} {'PE':>8} {'Sector':<20} {'Source':<10}")
    lines.append("-" * 60)

    for t in tickers:
        ctx = contexts.get(t)
        if not ctx:
            lines.append(f"{t:<8} {'—':>10} {'—':>8} {'—':<20} {'failed':<10}")
            continue
        err = getattr(ctx, "data_error", None)
        if err:
            lines.append(f"{t:<8} {'—':>10} {'—':>8} {'—':<20} {'error':<10}")
            continue
        src = getattr(ctx, "data_source", "unknown")
        lines.append(
            f"{t:<8} {ctx.price:>10.2f} {ctx.pe:>8.1f} "
            f"{ctx.sector or '—':<20} {src:<10}"
        )

    lines.append("")
    lines.append(f"{len(contexts)}/{len(tickers)} tickers fetched")
    return "\n".join(lines)
