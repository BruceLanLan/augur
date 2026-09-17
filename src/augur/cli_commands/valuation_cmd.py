# -*- coding: utf-8 -*-
"""Valuation CLI — DCF fair value vs market price comparison."""
from __future__ import annotations

def run_valuation(ticker: str, fcf: float = 0, growth: float = 0.08, wacc: float = 0.10,
                  shares: float = 0, net_debt: float | None = None) -> str:
    """Compute DCF fair value and compare to current market price.

    Explicit ``fcf``/``shares``/``net_debt`` are in plain USD / share counts.
    Anything left unset is filled from the live MarketContext, whose
    ``fcf``/``market_cap``/``total_cash``/``total_debt`` are in *billions* of
    USD. Missing inputs are reported as an error rather than guessed.
    """
    from augur.valuation import compute_dcf, DCFInputs

    market_price = 0.0
    sources: list[str] = []
    if fcf <= 0 or shares <= 0 or net_debt is None:
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
        except Exception as e:  # network/provider failure
            ctx = None
            sources.append(f"auto-fetch failed: {e}")
        if ctx is not None:
            market_price = float(getattr(ctx, "price", 0) or 0)
            if fcf <= 0 and (getattr(ctx, "fcf", 0) or 0) > 0:
                fcf = ctx.fcf * 1e9
                sources.append("FCF")
            market_cap = float(getattr(ctx, "market_cap", 0) or 0)
            if shares <= 0 and market_cap > 0 and market_price > 0:
                shares = market_cap * 1e9 / market_price
                sources.append("shares (market cap / price)")
            if net_debt is None:
                debt = float(getattr(ctx, "total_debt", 0) or 0)
                cash = float(getattr(ctx, "total_cash", 0) or 0)
                if debt or cash:
                    net_debt = (debt - cash) * 1e9
                    sources.append("net debt (debt - cash)")

    missing = []
    if fcf <= 0:
        missing.append("free cash flow (pass --fcf, in USD)")
    if shares <= 0:
        missing.append("shares outstanding (pass --shares)")
    if missing:
        return f"Error: insufficient data for {ticker.upper()} valuation: " + "; ".join(missing)
    if net_debt is None:
        net_debt = 0.0

    result = compute_dcf(DCFInputs(
        free_cash_flow=fcf, growth_rate_stage1=growth,
        stage1_years=5, growth_rate_terminal=0.025,
        wacc=wacc, shares_outstanding=shares, net_debt=net_debt,
    ))

    lines = [f"═══ DCF Valuation: {ticker.upper()} ═══", ""]
    lines.append(f"  Free Cash Flow:      ${fcf/1e9:.1f}B")
    lines.append(f"  Shares Outstanding:  {shares/1e9:.2f}B")
    lines.append(f"  Net Debt:            ${net_debt/1e9:.1f}B")
    lines.append(f"  Stage 1 Growth:      {growth:.1%}")
    lines.append(f"  WACC:                {wacc:.1%}")
    lines.append(f"  Fair Value/Share:    ${result.fair_value_per_share:.2f}")
    lines.append(f"  Enterprise Value:    ${result.enterprise_value/1e9:.1f}B")
    lines.append(f"  Equity Value:        ${result.equity_value/1e9:.1f}B")
    lines.append("")

    if market_price > 0:
        upside = (result.fair_value_per_share / market_price - 1) * 100
        lines.append(f"  Market Price:        ${market_price:.2f}")
        lines.append(f"  Upside/Downside:     {upside:+.1f}%")
        lines.append("")
        if upside > 20:
            lines.append("  Verdict: undervalued — potential margin of safety")
        elif upside < -20:
            lines.append("  Verdict: overvalued relative to DCF")
        else:
            lines.append("  Verdict: fairly valued within ±20% band")
        lines.append("")
    if sources:
        lines.append(f"  Auto-filled: {', '.join(sources)}")
    lines.append("  Model: 2-stage DCF, 5y stage 1, 2.5% terminal growth. Not investment advice.")

    return "\n".join(lines)


import click


@click.command("valuation")
@click.argument("ticker")
@click.option("--fcf", type=float, default=0.0, help="Free cash flow in USD, e.g. 100e9 (auto-fetched if 0)")
@click.option("--growth", type=float, default=0.08, help="Stage-1 growth rate")
@click.option("--wacc", type=float, default=0.10, help="Discount rate")
@click.option("--shares", type=float, default=0.0, help="Shares outstanding (derived from market cap / price if 0)")
@click.option("--net-debt", type=float, default=None, help="Net debt in USD (auto: total debt - cash)")
def valuation_cmd(ticker, fcf, growth, wacc, shares, net_debt):
    """DCF valuation with fair-value vs market comparison."""
    out = run_valuation(ticker, fcf=fcf, growth=growth, wacc=wacc, shares=shares, net_debt=net_debt)
    click.echo(out)
    if out.startswith("Error:"):
        raise SystemExit(1)
