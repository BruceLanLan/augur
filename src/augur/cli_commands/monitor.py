# -*- coding: utf-8 -*-
"""augur.cli_commands.monitor - watch / portfolio"""

import click

from augur.cli_helpers import _auto_fetch_context


@click.command("watch")
@click.argument("tickers", nargs=-1, required=True)
@click.option("--interval", default=60, show_default=True, help="Refresh interval in seconds")
@click.option("--persona", default=None, help="Use specific persona (default: consensus)")
@click.option("--alert-above", default=None, type=float, help="Alert when score above threshold")
@click.option("--alert-below", default=None, type=float, help="Alert when score below threshold")
def watch_cmd(tickers, interval, persona, alert_above, alert_below):
    """Watch tickers and refresh analysis at a set interval.

    \b
    Examples:
      augur watch AAPL NVDA TSLA            # Watch 3 tickers, refresh every 60s
      augur watch AAPL --interval 30        # Refresh every 30s
      augur watch NVDA --persona buffett    # Use Buffett persona
      augur watch AAPL --alert-above 7.5   # Alert when score > 7.5
    """
    import time

    from augur.registry import AgentRegistry, DecisionCoordinator

    registry = AgentRegistry()

    if persona:
        agent = registry.get(persona)
        if not agent:
            click.echo(f"Error: Persona '{persona}' not found.", err=True)
            click.echo(f"  Available: {', '.join(a.agent_id for a in registry.get_all())}", err=True)
            raise SystemExit(1)
    else:
        agent = None

    click.echo(f"Watching {len(tickers)} ticker(s) — refresh every {interval}s. Press Ctrl+C to stop.\n")

    try:
        while True:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            click.echo(f"[{timestamp}]")

            for ticker in tickers:
                try:
                    ctx = _auto_fetch_context(ticker)

                    if agent:
                        result = agent.analyze(ctx)
                        score = result.score
                        signal = result.signal.value.upper()
                    else:
                        coordinator = DecisionCoordinator(registry)
                        results = coordinator.analyze_with_all(ctx)
                        consensus = coordinator.get_consensus(results, ticker=ticker.upper(), context=ctx)
                        score = consensus.score
                        signal = consensus.signal.value.upper()

                    change_pct = ctx.change_pct
                    if change_pct >= 0:
                        change_str = f"↑ +{change_pct:.2%}"
                    else:
                        change_str = f"↓ {change_pct:.2%}"

                    line = f"  {ticker.upper():<8s} {signal:<10s} {score:.1f}/10  {change_str}"

                    alerts = []
                    if alert_above is not None and score > alert_above:
                        alerts.append(f"ALERT: score {score:.1f} > {alert_above}")
                    if alert_below is not None and score < alert_below:
                        alerts.append(f"ALERT: score {score:.1f} < {alert_below}")

                    if alerts:
                        line += "  *** " + " | ".join(alerts) + " ***"

                    click.echo(line)

                except Exception as e:
                    click.echo(f"  {ticker.upper():<8s} ERROR: {e}")

            click.echo("")
            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\nStopped.")


@click.command("portfolio")
@click.argument("tickers", nargs=-1, required=False)
@click.option("--weights", default=None, help="Manual weight overrides as JSON or 'AAPL:0.5,NVDA:0.3'")
@click.option("--days", type=int, default=None, help="Lookback days for fetch context (reserved)")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format")
def portfolio_cmd(tickers, weights, days, fmt):
    """Portfolio allocation suggestion using Kelly fractions.

    \b
    Examples:
      augur portfolio AAPL NVDA TSLA         # Analyze 3 tickers
      augur portfolio                         # Use watchlist
      augur portfolio AAPL NVDA --format json # JSON output
    """
    import json as _json
    from augur.registry import AgentRegistry, DecisionCoordinator

    DEFAULT_CAPITAL = 100_000

    # Resolve tickers: argument list or watchlist
    ticker_list = list(tickers)
    if not ticker_list:
        from augur.cron import load_watchlist
        config = load_watchlist()
        watchlist = config.get("watchlist", [])
        ticker_list = [item.get("ticker", "") for item in watchlist if item.get("ticker")]
        if not ticker_list:
            click.echo("No tickers provided and watchlist is empty.", err=True)
            click.echo("  Add tickers: augur watchlist-add TICKER", err=True)
            raise SystemExit(1)
        if fmt == "text":
            click.echo(f"Using watchlist: {', '.join(ticker_list)}\n")

    registry = AgentRegistry()
    coordinator = DecisionCoordinator(registry)

    rows = []  # list of dicts with ticker, signal, score, kelly_pct
    errors = []

    for ticker in ticker_list:
        t = ticker.upper()
        if fmt == "text":
            click.echo(f"Analyzing {t}...")
        try:
            ctx = _auto_fetch_context(t)
            results = coordinator.analyze_with_all(ctx)
            consensus = coordinator.get_consensus(results, ticker=t, context=ctx)

            pos = consensus.metadata.get("position_sizing", {})
            kelly_pct = pos.get("position_pct", 0.0) if pos else 0.0

            # For NEUTRAL/BEARISH use 0% allocation
            from augur.personas.base import SignalType
            if consensus.signal != SignalType.BULLISH:
                kelly_pct = 0.0

            rows.append({
                "ticker": t,
                "signal": consensus.signal.value.upper(),
                "score": round(consensus.score, 1),
                "kelly_pct": round(kelly_pct, 1),
            })
        except Exception as e:
            errors.append((t, str(e)))
            if fmt == "text":
                click.echo(f"  Warning: {t} failed: {e}", err=True)

    if not rows and not errors:
        click.echo("No results.", err=True)
        raise SystemExit(1)

    # Compute allocations — cap total at 100%
    total_invested_pct = sum(r["kelly_pct"] for r in rows)
    if total_invested_pct > 100.0:
        # Normalize proportionally
        factor = 100.0 / total_invested_pct
        for r in rows:
            r["kelly_pct"] = round(r["kelly_pct"] * factor, 1)
        total_invested_pct = 100.0

    cash_pct = round(100.0 - total_invested_pct, 1)

    if fmt == "json":
        payload = {
            "tickers": rows,
            "cash_pct": cash_pct,
            "total_invested_pct": round(total_invested_pct, 1),
            "capital": DEFAULT_CAPITAL,
            "errors": [{"ticker": t, "error": e} for t, e in errors],
        }
        click.echo(_json.dumps(payload, ensure_ascii=False, indent=2))
        return

    # Text output — portfolio table
    separator = "─" * 62
    click.echo("")
    click.echo("PORTFOLIO ANALYSIS")
    click.echo(separator)
    click.echo(f"{'Ticker':<10s} {'Signal':<10s} {'Score':<8s} {'Kelly%':<10s} {'Suggested Alloc'}")
    click.echo(separator)

    for r in rows:
        alloc_pct = r["kelly_pct"]
        alloc_dollars = int(alloc_pct / 100 * DEFAULT_CAPITAL)
        ticker_str = r["ticker"]
        signal_str = r["signal"]
        score_str = f"{r['score']:.1f}"
        kelly_str = f"{alloc_pct:.1f}%"
        if alloc_pct > 0:
            alloc_str = f"{alloc_pct:.1f}% (${alloc_dollars:,})"
        else:
            alloc_str = "0.0%"
        click.echo(f"{ticker_str:<10s} {signal_str:<10s} {score_str:<8s} {kelly_str:<10s} {alloc_str}")

    # Cash row
    cash_dollars = int(cash_pct / 100 * DEFAULT_CAPITAL)
    cash_alloc_str = f"{cash_pct:.1f}% (${cash_dollars:,})"
    click.echo(f"{'CASH':<10s} {'':<10s} {'':<8s} {'':<10s} {cash_alloc_str}")
    click.echo(separator)
    click.echo(f"Total invested: {total_invested_pct:.1f}% | Cash: {cash_pct:.1f}%")
