# -*- coding: utf-8 -*-
"""augur.cli_commands.backtest - backtest / ic-report"""

import click


@click.command("backtest")
@click.argument("ticker", required=False, default="AAPL")
@click.option("--days", type=int, default=30, help="Number of days to backtest")
@click.option("--demo", is_flag=True, help="Use generated sample data (offline, deterministic, never real)")
@click.option("--live", is_flag=True, help="[default behavior] Use real historical data from yfinance — kept for backward compatibility with existing scripts")
def backtest_cmd(ticker, days, demo, live):
    """Run historical backtest on a ticker.

    Real historical data (yfinance) is now the default — no --live flag
    needed. Pass --demo for offline/no-network synthetic data; it is never
    silently substituted if a live fetch fails, since a fake "backtest
    result" that looks real is worse than a clear error.

    \b
    Examples:
      augur backtest AAPL --days 30          # Real data (default)
      augur backtest NVDA --days 60 --demo   # Offline synthetic data
    """
    if live and demo:
        click.echo("Error: --live and --demo are mutually exclusive.", err=True)
        raise SystemExit(1)

    from augur.backtest import Backtester

    click.echo(f"Running backtest for {ticker.upper()} ({days} days)...\n")

    if demo:
        from augur.backtest import generate_sample_data
        historical_data, forward_returns = generate_sample_data(ticker, days)
        backtester = Backtester()
        result = backtester.run_backtest(ticker, historical_data, forward_returns, data_source="demo")
        click.echo(result.summary)
        click.echo(f"\nTotal records: {len(result.records)}")
        click.echo(f"Consensus IC (20d): {result.consensus_ic:.4f}")
        click.echo(f"\n[数据来源: 演示数据 (--demo，非真实历史，不计入 leaderboard)]")
        return

    # Default (and --live, now a no-op alias): real data. No silent fallback
    # to demo on failure — a wrong-looking-real number is worse than an
    # honest error (docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md debt 2).
    from augur.optional_deps import is_available
    if not is_available("augur.data"):
        click.echo(
            "Error: Package 'augur.data' is required for real-time market data fetching but is not installed.\n"
            "  Install with: pip install 'augur-agents[data]'\n"
            "  Or pass --demo to use offline synthetic data instead.",
            err=True,
        )
        raise SystemExit(1)

    try:
        backtester = Backtester()
        result = backtester.run_live_backtest(ticker, days=days)
    except ImportError as e:
        click.echo(
            f"Error: {e}\n"
            f"  Install with: pip install 'augur-agents[data]'\n"
            f"  Or pass --demo to use offline synthetic data instead.",
            err=True,
        )
        raise SystemExit(1)
    except Exception as e:
        click.echo(
            f"Error fetching live data for {ticker.upper()}: {e}\n"
            f"  Suggestion: Check network connection or try a different ticker.\n"
            f"  Or pass --demo to use offline synthetic data instead.",
            err=True,
        )
        raise SystemExit(1)

    click.echo(result.summary)
    click.echo(f"\nTotal records: {len(result.records)}")
    click.echo(f"Consensus IC (20d): {result.consensus_ic:.4f}")
    click.echo(f"\n[数据来源: yfinance 实时历史数据]")


@click.command("ic-report")
@click.option("--agent", "-a", default=None, help="Filter by agent ID")
def ic_report_cmd(agent):
    """Show Agent IC leaderboard"""
    from augur.backtest import Backtester

    backtester = Backtester()

    if agent:
        ics = backtester.get_ic_report(agent_id=agent)
    else:
        ics = backtester.get_leaderboard()

    if not ics:
        click.echo(
            "No live backtest records found (demo-mode records don't count — "
            "see docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md debt 2).\n"
            "Run 'augur backtest TICKER' first."
        )
        return

    click.echo(f"{'Rank':<5} {'Agent':<22} {'IC 5d':<10} {'IC 20d':<10} {'IC 60d':<10} {'Hit Rate':<10} {'Predictions'}")
    click.echo("-" * 85)

    for i, ic in enumerate(ics, 1):
        click.echo(
            f"{i:<5} {ic.agent_id:<22} {ic.ic_5d:<10.4f} {ic.ic_20d:<10.4f} "
            f"{ic.ic_60d:<10.4f} {ic.hit_rate:<10.1%} {ic.total_predictions}"
        )
