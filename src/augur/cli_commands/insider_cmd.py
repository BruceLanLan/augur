# -*- coding: utf-8 -*-
"""augur.cli_commands.insider_cmd — ``augur insider`` command.

Displays a 90-day insider trading summary with cluster detection.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import click

from augur.cli_format import format_table
from augur.ownership import InsiderAnalyzer, InsiderCluster, InsiderTrade


def _fetch_insider_trades(ticker: str) -> list[InsiderTrade]:
    """Fetch open-market insider trades for *ticker* from EDGAR (trailing 90 days).

    Returns an empty list on any fetch/parse failure — the CLI prints a
    notice rather than crashing.
    """
    try:
        from augur.consensus.edgar_insider import _fetch_form4_transactions
    except ImportError:
        return []

    # Use today as the as-of date for the CLI
    as_of_date = datetime.now().strftime("%Y-%m-%d")
    raw_trades = _fetch_form4_transactions(ticker.upper(), as_of_date)

    trades: list[InsiderTrade] = []
    for t in raw_trades:
        shares = t.get("shares", 0) or 0
        price = t.get("price", 0) or 0
        code = t.get("code", "")
        trade_type = "buy" if code == "P" else "sell"
        trades.append(InsiderTrade(
            ticker=ticker.upper(),
            person=t.get("reporting_owner_cik", "Unknown"),
            role="",
            transaction_date=t.get("transaction_date", ""),
            type=trade_type,
            shares=float(shares),
            price=float(price),
            value=float(shares) * float(price),
        ))
    return trades


def _format_trades_table(trades: list[InsiderTrade]) -> str:
    """Render a list of InsiderTrade objects as a formatted table."""
    if not trades:
        return "  (no trades in the trailing 90-day window)"

    headers = ["Date", "Person (CIK)", "Type", "Shares", "Price", "Value"]
    rows = []
    for t in trades:
        type_label = "BUY " if t.type == "buy" else "SELL"
        rows.append([
            t.transaction_date,
            t.person,
            type_label,
            f"{t.shares:,.0f}",
            f"${t.price:,.2f}",
            f"${t.value:,.0f}",
        ])
    return format_table(headers, rows)


def _format_cluster_summary(cluster: InsiderCluster) -> str:
    """Render an InsiderCluster as a one-line summary."""
    assessment_labels = {
        "cluster_buying": "🟢 CLUSTER BUYING",
        "cluster_selling": "🔴 CLUSTER SELLING",
        "mixed": "🟡 MIXED",
        "no_activity": "⚪ NO ACTIVITY",
    }
    label = assessment_labels.get(cluster.assessment, cluster.assessment)
    net_sign = "+" if cluster.net_value >= 0 else ""
    return (
        f"  Assessment:  {label}\n"
        f"  Total Buys:  {cluster.total_buys}\n"
        f"  Total Sells: {cluster.total_sells}\n"
        f"  Net Value:   {net_sign}${cluster.net_value:,.0f}\n"
        f"  Participants: {', '.join(cluster.participants) if cluster.participants else '(none)'}"
    )


@click.command("insider")
@click.argument("ticker")
@click.option(
    "--days", "-d",
    default=90,
    type=int,
    help="Lookback window in days (default: 90).",
)
def insider_cmd(ticker: str, days: int) -> None:
    """Show recent insider trading activity and cluster detection.

    \b
    Fetches open-market (P/S) Form 4 transactions from SEC EDGAR for the
    trailing 90 days, runs cluster detection, and prints a summary table.

    \b
    Examples:
      augur insider AAPL
      augur insider NVDA --days 60
    """
    ticker = ticker.upper()

    click.echo(f"\nInsider Trading Summary: {ticker}")
    click.echo(f"  Period: last {days} days")
    click.echo(f"  Source: SEC EDGAR Form 4 (open-market P/S only)\n")

    # Fetch trades
    trades = _fetch_insider_trades(ticker)

    if not trades:
        click.echo("  No open-market insider transactions found in this window.")
        click.echo("  (This may mean no insiders traded, or EDGAR data is unavailable.)\n")
        return

    # Run cluster detection
    analyzer = InsiderAnalyzer()
    cluster = analyzer.detect_clusters(trades, window_days=days)

    # Print cluster summary
    click.echo(_format_cluster_summary(cluster))
    click.echo("")

    # Print trade details table
    click.echo("Transaction Details:")
    click.echo(_format_trades_table(trades))
    click.echo("")
