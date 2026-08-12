# -*- coding: utf-8 -*-
"""Valuation CLI — DCF fair value vs market price comparison."""
from __future__ import annotations

def run_valuation(ticker: str, fcf: float = 0, growth: float = 0.08, wacc: float = 0.10,
                  shares: float = 0, net_debt: float = 0) -> str:
    """Compute DCF fair value and compare to current market price."""
    from augur.valuation import compute_dcf, DCFInputs

    # Auto-fetch market data if not provided
    if fcf <= 0 or shares <= 0:
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            fcf = fcf or (ctx.fcf if ctx.fcf > 0 else ctx.revenue * 0.15)
            shares = shares or getattr(ctx, "shares_outstanding", 0) or 1e9
            market_price = ctx.price
        except Exception:
            market_price = 0.0
    else:
        market_price = 0.0

    if fcf <= 0 or shares <= 0:
        return f"Error: insufficient data for {ticker} valuation"

    result = compute_dcf(DCFInputs(
        free_cash_flow=fcf, growth_rate_stage1=growth,
        stage1_years=5, growth_rate_terminal=0.025,
        wacc=wacc, shares_outstanding=shares, net_debt=net_debt,
    ))

    lines = [f"═══ DCF Valuation: {ticker.upper()} ═══", ""]
    lines.append(f"  Free Cash Flow:      ${fcf/1e9:.1f}B")
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

    return "\n".join(lines)
