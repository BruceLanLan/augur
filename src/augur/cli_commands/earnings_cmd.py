# -*- coding: utf-8 -*-
"""Watchlist earnings queue CLI — upcoming events with readiness."""
from __future__ import annotations

import click

from augur.earnings import EarningsEventService


@click.command("earnings")
@click.option("--days", default=30, help="Lookahead window in days")
@click.option("--ticker", "-t", multiple=True, help="Filter to specific ticker(s)")
@click.option(
    "--backfill",
    is_flag=True,
    help="Backfill the calendar from SEC 8-K Item 2.02 filings (past dates + one estimated next date)",
)
def earnings_cmd(days, ticker, backfill):
    """Show upcoming earnings events from the watchlist."""
    if backfill:
        _run_backfill(list(ticker))
        return
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


def _run_backfill(tickers):
    from augur import earnings_calendar
    from augur.data_dir import get_data_dir
    from augur.earnings import _watchlist_tickers

    if not tickers:
        import yaml

        wl_path = get_data_dir() / "watchlist.yaml"
        data = {}
        if wl_path.exists():
            with open(wl_path) as f:
                data = yaml.safe_load(f) or {}
        tickers = _watchlist_tickers(data)
    if not tickers:
        click.echo("Watchlist is empty — add tickers with `augur watchlist add AAPL` or pass -t.")
        return

    path = get_data_dir() / "earnings_calendar.json"
    try:
        report = earnings_calendar.backfill_calendar(
            tickers, path, fetch=earnings_calendar.fetch_submissions
        )
    except RuntimeError as exc:
        click.echo(f"Backfill aborted: {exc}")
        return

    lines = ["═══ Earnings calendar backfill (SEC 8-K Item 2.02) ═══", ""]
    total = 0
    for t, r in report.items():
        if r["error"]:
            lines.append(f"  {t:<8} error: {r['error']}")
            continue
        added = r["added"]
        total += len(added)
        lines.append(f"  {t:<8} added {len(added)} ({r['estimated']} estimated)")
        for e in added:
            lines.append(f"             {e['event_date']}  ({e['confidence']})")
    lines.append("")
    lines.append(f"{total} events added → {path}")
    lines.append("Estimated dates come from filing cadence, not a company announcement.")
    click.echo("\n".join(lines))
