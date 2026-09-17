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
        click.echo(f"Auto-fetching live data for {ticker.upper()}...\n")
        ctx = fetch_market_context(ticker)
        click.echo(f"  Price: {ctx.price:.2f} | PE: {ctx.pe:.1f} | ROE: {ctx.roe:.2%} | GM: {ctx.gross_margins:.2%}")
        click.echo(f"  [{describe_data_source(ctx)}]\n")
        return ctx
    except Exception as e:
        click.echo(
            f"Warning: Failed to fetch data for {ticker.upper()}: {e}\n"
            f"  Suggestion: Check your network connection or try again later.\n"
            f"  Falling back to empty metrics.\n",
            err=True,
        )
        return MarketContext(ticker=ticker.upper())


def _print_result(result):
    """Pretty print a single analysis result"""
    from augur.cli_format import signal_icon, clean_output

    icon = signal_icon(result.signal.value)
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

    The CLI used to print "数据来源: yfinance 实时" whatever provider (or none)
    actually served the data.
    """
    source = getattr(ctx, "data_source", None) or "unknown"
    label = {"none": "无可用数据源（指标为空）", "error": "获取失败"}.get(source, f"{source} 实时")
    if getattr(ctx, "fundamentals_source", None) == "edgar":
        label += " + SEC EDGAR 基本面"
    return f"数据来源: {label}"
