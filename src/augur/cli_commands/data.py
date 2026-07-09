# -*- coding: utf-8 -*-
"""augur.cli_commands.data - fetch / sentiment"""

import click


@click.command("fetch")
@click.argument("ticker")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def fetch_cmd(ticker, as_json):
    """Fetch real-time market data for a ticker (via yfinance).

    \b
    Examples:
      augur fetch AAPL           # Formatted output
      augur fetch NVDA --json    # JSON output
      augur fetch 0700.HK        # Hong Kong stock
    """
    from augur.optional_deps import require_optional
    try:
        require_optional("augur.data", "real-time market data fetching", "pip install 'augur-agents[data]'")
        from augur.data import fetch_market_context
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"Fetching data for {ticker.upper()}...\n")

    try:
        ctx = fetch_market_context(ticker)
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Error fetching data: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        import json
        click.echo(json.dumps(ctx.to_dict(), indent=2, ensure_ascii=False))
    else:
        click.echo(f"{'Ticker':<18s} {ctx.ticker}")
        click.echo(f"{'Price':<18s} {ctx.price:.2f}")
        click.echo(f"{'Market Cap':<18s} ${ctx.market_cap:,.1f}B")
        click.echo(f"{'PE':<18s} {ctx.pe:.2f}")
        click.echo(f"{'PB':<18s} {ctx.pb:.2f}")
        click.echo(f"{'PS':<18s} {ctx.ps:.2f}")
        click.echo(f"{'ROE':<18s} {ctx.roe:.2%}")
        click.echo(f"{'Gross Margins':<18s} {ctx.gross_margins:.2%}")
        click.echo(f"{'Operating Margins':<18s} {ctx.operating_margins:.2%}")
        click.echo(f"{'Revenue Growth':<18s} {ctx.revenue_growth:.2%}")
        click.echo(f"{'Earnings Growth':<18s} {ctx.earnings_growth:.2%}")
        click.echo(f"{'Debt Ratio':<18s} {ctx.debt_ratio:.2f}")
        click.echo(f"{'FCF':<18s} ${ctx.fcf:,.2f}B")
        click.echo(f"{'Current Ratio':<18s} {ctx.current_ratio:.2f}")
        click.echo(f"{'Sector':<18s} {ctx.sector}")
        click.echo(f"{'Industry':<18s} {ctx.industry}")
        click.echo(f"{'RSI':<18s} {ctx.rsi:.1f}")
        click.echo(f"{'MACD':<18s} {ctx.macd:.4f}")
        click.echo(f"{'SMA20':<18s} {ctx.sma20:.2f}")
        click.echo(f"{'SMA50':<18s} {ctx.sma50:.2f}")
        click.echo(f"\n[数据来源: yfinance 实时]")


@click.command("sentiment")
@click.argument("ticker")
def sentiment_cmd(ticker):
    """Print social sentiment scores for a ticker"""
    from augur.sentiment import SentimentAnalyzer
    sa = SentimentAnalyzer()
    result = sa.get_sentiment(ticker.upper())
    click.echo(f"\nSentiment Analysis: {result.ticker}\n")
    click.echo(f"{'Overall Score':<20s} {result.overall_score:+.4f}  (source: {result.data_source})")
    click.echo(f"{'StockTwits (62.5%)':<20s} {result.sources.get('stocktwits_score', 0):+.4f}")
    click.echo(f"{'Reddit (37.5%)':<20s} {result.sources.get('reddit_score', 0):+.4f}")
    click.echo(f"{'X (Twitter)':<20s} excluded (R4: no free real-data source, see CHANGELOG)")
    click.echo(f"{'Volume':<20s} {result.volume:,}")
    click.echo(f"{'Trending':<20s} {'Yes' if result.trending else 'No'}")
    click.echo(f"{'Consensus Factor':<20s} {sa.get_sentiment_factor(ticker.upper()):+.4f}")
    if result.data_source == "mock":
        click.echo("\n[Note: StockTwits/Reddit unavailable this call -- scores are hash-mock fallback]")


@click.command("guidance")
@click.argument("ticker")
@click.option("--as-of", "as_of_date", default=None, help="As-of date (YYYY-MM-DD), default: latest filing")
def guidance_cmd(ticker, as_of_date):
    """Extract management outlook from the latest 10-K/10-Q MD&A via LLM (EDGAR Phase 4, opt-in).

    \b
    Disabled by default -- this makes a paid LLM API call. Enable with:
      export AUGUR_EDGAR_GUIDANCE_EXTRACTION=1
      export OPENAI_API_KEY=...          # or OPENAI_BASE_URL for a compatible endpoint

    \b
    Examples:
      augur guidance AAPL
      augur guidance NVDA --as-of 2025-06-01
    """
    from augur.consensus.edgar_guidance import fetch_management_guidance

    result = fetch_management_guidance(ticker, as_of_date=as_of_date)

    if not result.get("available"):
        click.echo(f"Not available: {result.get('reason', 'unknown')}", err=True)
        raise SystemExit(1)

    click.echo(f"\nManagement Guidance: {ticker.upper()}")
    click.echo(f"{'Filing':<20s} {result['form']} filed {result['filing_date']} (accession {result['accession_number']})")
    click.echo(f"{'Cache hit':<20s} {result['cache_hit']}")
    click.echo(f"{'Outlook sentiment':<20s} {result['outlook_sentiment']}")
    click.echo(f"{'Outlook summary':<20s} {result['outlook_summary']}")
    if result["guidance_numbers"]:
        click.echo("Guidance numbers:")
        for g in result["guidance_numbers"]:
            click.echo(f"  - {g}")
    else:
        click.echo(f"{'Guidance numbers':<20s} (none stated)")
    if result["risk_notes"]:
        click.echo(f"{'Risk notes':<20s} {result['risk_notes']}")
