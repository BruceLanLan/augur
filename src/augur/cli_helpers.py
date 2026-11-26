# -*- coding: utf-8 -*-
"""
augur.cli_helpers - Shared helpers used across multiple augur.cli_commands modules

Split out of cli.py (R7) so each command module can import these without
depending on cli.py itself.
"""

import click


def _auto_fetch_context(ticker: str):
    """Auto-fetch MarketContext from yfinance, with graceful fallback."""
    from augur.personas.base import MarketContext
    from augur.optional_deps import is_available

    if not is_available("augur.data"):
        click.echo(
            "Warning: yfinance not installed. Install with: pip install 'augur-agents[data]'\n"
            "  Core analysis still works without it (using empty metrics).\n",
            err=True,
        )
        return MarketContext(ticker=ticker.upper())

    try:
        from augur.data import fetch_market_context
        # Progress goes to stderr so `--json` stdout stays pure JSON.
        click.echo(f"Auto-fetching live data for {ticker.upper()}...\n", err=True)
        ctx = fetch_market_context(ticker)
        click.echo(f"  {fetch_summary_line(ctx)}", err=True)
        click.echo(f"  [{describe_data_source(ctx)}]\n", err=True)
        return ctx
    except Exception as e:
        click.echo(
            f"Warning: Failed to fetch data for {ticker.upper()}: {e}\n"
            f"  Suggestion: Check your network connection or try again later.\n"
            f"  Falling back to empty metrics.\n",
            err=True,
        )
        return MarketContext(ticker=ticker.upper())


def fetch_summary_line(ctx) -> str:
    """One-line summary printed after an auto-fetch (fund-aware)."""
    from augur.etf import is_fund

    ccy = trading_currency(ctx)
    price = f"Price: {ctx.price:.2f}" + (f" {ccy}" if ccy else "")
    if is_fund(ctx):
        etf = getattr(ctx, "etf", None) or {}
        aum = etf.get("aum_usd_bn")
        aum_s = f"${aum:,.1f}B" if isinstance(aum, (int, float)) and aum > 0 else "unknown"
        return f"{price} | ETF | AUM: {aum_s}"
    return f"{price} | PE: {ctx.pe:.1f} | ROE: {ctx.roe:.2%} | GM: {ctx.gross_margins:.2%}"


def trading_currency(ctx) -> str:
    """Trading currency code of the quote (price is always in this currency)."""
    return str(getattr(ctx, "currency", "") or "").upper()


def amount_currency(ctx, kind: str = "market") -> str:
    """Currency of a billions-denominated amount on ``ctx``.

    The data layer converts amounts to USD when it knows the FX rate
    (``fx_rate_usd > 0``). When the rate is unknown it leaves them unconverted:
    market-side amounts (market cap, EV) in the trading currency, statement
    amounts (FCF, revenue, cash, debt) in the financial-statement currency.
    """
    fx = getattr(ctx, "fx_rate_usd", 0) or 0
    ccy = trading_currency(ctx)
    try:
        fx = float(fx)
    except (TypeError, ValueError):
        fx = 0.0
    if fx > 0 or ccy in ("", "USD"):
        return "USD"
    if kind == "financial":
        return str(getattr(ctx, "financial_currency", "") or ccy).upper()
    return ccy


def format_amount_bn(value, ccy: str, decimals: int = 1) -> str:
    """Billions amount: ``$12.3B`` for USD, ``12.3B HKD`` otherwise."""
    if ccy == "USD":
        return f"${value:,.{decimals}f}B"
    return f"{value:,.{decimals}f}B {ccy}"


def _print_result(result):
    """Pretty print a single analysis result"""
    from augur.cli_format import signal_icon, clean_output

    icon = signal_icon(result.signal.value)
    if (result.metadata or {}).get("not_applicable"):
        click.echo(f"Agent:      {result.agent_name}")
        click.echo("Signal:     N/A (not applicable to funds)")
        click.echo(f"Reason:     {clean_output(result.reasoning)}")
        return
    click.echo(f"Agent:      {result.agent_name}")
    click.echo(f"Signal:     {icon} {result.signal.value}")
    click.echo(f"Score:      {result.score:.1f}/10")
    click.echo(f"Confidence: {result.confidence:.0%}")

    if result.key_findings:
        click.echo("\nKey Findings:")
        for f in result.key_findings:
            click.echo(f"  - {clean_output(f)}")

    if result.risks:
        click.echo("\nRisks:")
        for r in result.risks:
            click.echo(f"  - {clean_output(r)}")


def describe_data_source(ctx) -> str:
    """Human-readable data source line for a fetched MarketContext.

    The CLI used to print "yfinance" whatever provider (or none) actually
    served the data. English, like the rest of the CLI frame.
    """
    source = getattr(ctx, "data_source", None) or "unknown"
    label = {"none": "none available (metrics empty)", "error": "fetch failed"}.get(source, f"{source} (live)")
    if getattr(ctx, "fundamentals_source", None) == "edgar":
        label += " + SEC EDGAR fundamentals"
    return f"Data source: {label}"
