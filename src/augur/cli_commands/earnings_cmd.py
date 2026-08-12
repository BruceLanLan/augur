# -*- coding: utf-8 -*-
"""Watchlist earnings queue CLI — upcoming events with readiness."""
from __future__ import annotations

import click

from augur.earnings import EarningsEventService


@click.command("earnings")
@click.option("--days", default=30, help="Lookahead window in days")
@click.option("--ticker", "-t", multiple=True, help="Filter to specific ticker(s)")
def earnings_cmd(days, ticker):
    """Show upcoming earnings events from the watchlist."""
    service = EarningsEventService()
    tickers = list(ticker) if ticker else None
    if tickers:
        events = service.detect_events(tickers, lookahead_days=days)
    else:
        events = service.identify_events_for_watchlist(lookahead_days=days)

    if not events:
        click.echo("No upcoming earnings events found.")
        return

    lines = ["═══ Earnings Queue ═══", ""]
    for e in events:
        lines.append(f"  {e.ticker:<8} {e.event_date}  ({e.confidence})")
        if e.fiscal_period:
            lines.append(f"             {e.fiscal_period}")
    lines.append("")
    lines.append(f"{len(events)} events in next {days} days")

    # Readiness check
    statuses = service.check_dossier_readiness(events)
    ready = sum(1 for s in statuses if s.ready)
    lines.append(f"  Ready dossiers: {ready}/{len(statuses)}")
    for s in statuses:
        if not s.ready:
            lines.append(f"  ⚠ {s.ticker}: missing {', '.join(s.missing_items)}")

    click.echo("\n".join(lines))
