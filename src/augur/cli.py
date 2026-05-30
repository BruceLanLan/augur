# -*- coding: utf-8 -*-
"""
augur.cli - Click-based command line interface

Commands:
  augur analyze TICKER [--persona ID] [--pe X] [--roe X] ...
  augur consensus TICKER [--pe X] [--roe X] ...
  augur list-personas
  augur mcp-server
  augur api [--port 8900]
  augur inject-soul
  augur telegram          - Start Telegram bot
  augur slack             - Start Slack bot
  augur wechat            - Start WeChat/WeCom bot
  augur lark              - Start Lark/Feishu bot
  augur cron-run          - Run watchlist analysis once
  augur cron-start        - Start scheduler daemon
  augur watchlist-add     - Add ticker to watchlist
  augur watchlist-show    - Show current watchlist
"""

import click

from augur import __version__


@click.group()
@click.version_option(version=__version__, prog_name="augur")
@click.option("--no-color", is_flag=True, default=False, help="Disable color output and emojis")
@click.pass_context
def main(ctx, no_color):
    """Augur - Multi-agent investment analysis system"""
    import os
    ctx.ensure_object(dict)
    # Respect --no-color flag or NO_COLOR env variable
    if no_color or os.environ.get("NO_COLOR", "") != "":
        _prev_no_color = os.environ.get("NO_COLOR")
        os.environ["NO_COLOR"] = "1"
        ctx.obj["no_color"] = True

        # Restore original env state when CLI context closes
        def _restore_env():
            if _prev_no_color is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = _prev_no_color

        ctx.call_on_close(_restore_env)
    else:
        ctx.obj["no_color"] = False


@main.command("analyze")
@click.argument("ticker")
@click.option("--persona", "-p", default=None, help="Specific persona ID to use")
@click.option("--pe", type=float, default=None, help="PE ratio")
@click.option("--pb", type=float, default=None, help="PB ratio")
@click.option("--roe", type=float, default=None, help="Return on equity (decimal, e.g. 0.55 for 55%)")
@click.option("--gross-margins", type=float, default=None, help="Gross margins (decimal, e.g. 0.46 for 46%)")
@click.option("--revenue-growth", type=float, default=None, help="Revenue growth (decimal)")
@click.option("--debt-ratio", type=float, default=None, help="Debt/assets ratio (decimal, e.g. 0.35 for 35%)")
@click.option("--fcf", type=float, default=None, help="Free cash flow (billions USD)")
@click.option("--market-cap", type=float, default=None, help="Market cap (billions USD)")
@click.option("--price", type=float, default=None, help="Current stock price")
@click.option("--sector", default="", help="Sector name (e.g. Technology)")
@click.option("--industry", default="", help="Industry name (e.g. Semiconductor)")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
def analyze_cmd(ticker, persona, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price, sector, industry, as_json):
    """Analyze a ticker with one or all agents (auto-fetches data if no metrics specified)"""
    from augur.personas.base import MarketContext
    from augur.registry import AgentRegistry

    # Check if user provided any metrics
    user_metrics = {k: v for k, v in {
        "pe": pe, "pb": pb, "roe": roe, "gross_margins": gross_margins,
        "revenue_growth": revenue_growth, "debt_ratio": debt_ratio,
        "fcf": fcf, "market_cap": market_cap, "price": price,
    }.items() if v is not None}

    if not user_metrics:
        # Auto-fetch from yfinance
        ctx = _auto_fetch_context(ticker)
    else:
        ctx = MarketContext(
            ticker=ticker.upper(),
            pe=pe or 0,
            pb=pb or 0,
            roe=roe or 0,
            gross_margins=gross_margins or 0,
            revenue_growth=revenue_growth or 0,
            debt_ratio=debt_ratio or 0,
            fcf=fcf or 0,
            market_cap=market_cap or 0,
            price=price or 0,
            sector=sector or "",
            industry=industry or "",
        )

    registry = AgentRegistry()

    if persona:
        agent = registry.get(persona)
        if not agent:
            click.echo(f"Error: Persona '{persona}' not found.", err=True)
            click.echo(f"  Suggestion: Run 'augur list-personas' to see available IDs.", err=True)
            click.echo(f"  Available: {', '.join(a.agent_id for a in registry.get_all())}", err=True)
            raise SystemExit(1)
        result = agent.analyze(ctx)
        if as_json:
            import json as _json
            click.echo(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            _print_result(result)
    else:
        if as_json:
            import json as _json
            all_results = {}
            for agent in registry.get_all():
                try:
                    all_results[agent.agent_id] = agent.analyze(ctx).to_dict()
                except Exception as e:
                    all_results[agent.agent_id] = {"error": str(e)}
            click.echo(_json.dumps(all_results, ensure_ascii=False, indent=2))
        else:
            from augur.cli_format import format_table, signal_icon, color_text
            click.echo(f"Analyzing {ticker.upper()} with all {len(registry.get_all())} agents...\n")
            headers = ["Agent", "Signal", "Score", "Confidence"]
            rows = []
            for agent in registry.get_all():
                try:
                    result = agent.analyze(ctx)
                    icon = signal_icon(result.signal.value)
                    rows.append([
                        result.agent_name,
                        f"{icon} {result.signal.value}",
                        f"{result.score:.1f}/10",
                        f"{result.confidence:.0%}",
                    ])
                except Exception as e:
                    rows.append([agent.name, "ERROR", "-", str(e)])
            click.echo(format_table(headers, rows))


@main.command("consensus")
@click.argument("ticker")
@click.option("--pe", type=float, default=None, help="PE ratio")
@click.option("--pb", type=float, default=None, help="PB ratio")
@click.option("--roe", type=float, default=None, help="Return on equity (decimal)")
@click.option("--gross-margins", type=float, default=None, help="Gross margins (decimal)")
@click.option("--revenue-growth", type=float, default=None, help="Revenue growth (decimal)")
@click.option("--debt-ratio", type=float, default=None, help="Debt/assets ratio (decimal)")
@click.option("--fcf", type=float, default=None, help="Free cash flow (billions USD)")
@click.option("--market-cap", type=float, default=None, help="Market cap (billions USD)")
@click.option("--price", type=float, default=None, help="Current stock price")
@click.option("--sector", default="", help="Sector name (e.g. Technology)")
@click.option("--industry", default="", help="Industry name")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
def consensus_cmd(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price, sector, industry, as_json):
    """Get multi-agent consensus on a ticker (auto-fetches data if no metrics specified)"""
    from augur.personas.base import MarketContext
    from augur.registry import AgentRegistry, DecisionCoordinator

    # Check if user provided any metrics
    user_metrics = {k: v for k, v in {
        "pe": pe, "pb": pb, "roe": roe, "gross_margins": gross_margins,
        "revenue_growth": revenue_growth, "debt_ratio": debt_ratio,
        "fcf": fcf, "market_cap": market_cap, "price": price,
    }.items() if v is not None}

    if not user_metrics:
        # Auto-fetch from yfinance
        ctx = _auto_fetch_context(ticker)
    else:
        ctx = MarketContext(
            ticker=ticker.upper(),
            pe=pe or 0,
            pb=pb or 0,
            roe=roe or 0,
            gross_margins=gross_margins or 0,
            revenue_growth=revenue_growth or 0,
            debt_ratio=debt_ratio or 0,
            fcf=fcf or 0,
            market_cap=market_cap or 0,
            price=price or 0,
            sector=sector or "",
            industry=industry or "",
        )

    registry = AgentRegistry()
    coordinator = DecisionCoordinator(registry)

    if not as_json:
        click.echo(f"Computing consensus for {ticker.upper()}...\n")
    results = coordinator.analyze_with_all(ctx)
    consensus = coordinator.get_consensus(results, ticker=ticker.upper(), context=ctx)

    if as_json:
        import json as _json
        payload = {
            "ticker": ticker.upper(),
            "consensus": consensus.to_dict(),
            "individual": {aid: r.to_dict() for aid, r in results.items()},
        }
        click.echo(_json.dumps(payload, ensure_ascii=False, indent=2))
        return

    from augur.cli_format import format_box, format_table, signal_icon, color_text, clean_output

    # Summary box
    icon = signal_icon(consensus.signal.value)
    box_lines = [
        f"Signal:     {icon} {consensus.signal.value.upper()}",
        f"Score:      {consensus.score:.1f}/10",
        f"Confidence: {consensus.confidence:.0%}",
    ]
    pos = consensus.metadata.get("position_sizing", {})
    if pos:
        box_lines.append(f"Kelly Size: {pos.get('position_pct', 0):.1f}%")
    box_lines.append(f"Reasoning:  {clean_output(consensus.reasoning)}")
    click.echo(format_box(box_lines, title=f"{ticker.upper()} Consensus"))

    if consensus.key_findings:
        click.echo(f"\nKey Findings:")
        for f in consensus.key_findings:
            click.echo(f"  - {clean_output(f)}")

    if consensus.risks:
        click.echo(f"\nRisks:")
        for r in consensus.risks:
            click.echo(f"  - {clean_output(r)}")

    # Show individual agent breakdown as aligned table
    click.echo(f"\n--- Agent Breakdown ({len(results)} agents) ---")
    headers = ["Agent", "Signal", "Score"]
    rows = []
    for agent_id, result in results.items():
        rows.append([
            result.agent_name,
            f"{signal_icon(result.signal.value)} {result.signal.value}",
            f"{result.score:.1f}/10",
        ])
    click.echo(format_table(headers, rows))


@main.command("list-personas")
def list_personas_cmd():
    """List all available personas"""
    from augur.registry import AgentRegistry

    registry = AgentRegistry()
    agents = registry.get_all()

    click.echo(f"Available Personas ({len(agents)} total):\n")
    click.echo(f"{'ID':<20s} {'Name':<25s} {'Philosophy'}")
    click.echo("-" * 70)
    for agent in agents:
        philosophy = ", ".join(agent.philosophy[:2]) if agent.philosophy else ""
        click.echo(f"{agent.agent_id:<20s} {agent.name:<25s} {philosophy}")


@main.command("mcp-server")
def mcp_server_cmd():
    """Start the MCP server (stdio mode)"""
    from augur.mcp_server import run_server
    run_server()


@main.command("api")
@click.option("--port", type=int, default=8900, help="Port to run on")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
def api_cmd(port, host):
    """Start the REST API server"""
    try:
        import uvicorn
        from augur.api import app
        click.echo(f"Starting Augur API on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
    except ImportError:
        click.echo(
            "Error: uvicorn and fastapi are not installed.\n"
            "  Install with: pip install 'augur-agents[api]' (or: pip install fastapi uvicorn)\n"
            "  CLI commands (analyze, consensus) still work without the API server.",
            err=True,
        )
        raise SystemExit(1)


@main.command("inject-soul")
@click.option("--profile", "-p", required=True, help="Profile name to create")
@click.option("--persona", required=True, help="Persona ID to inject (e.g. buffett, duan_yongping)")
@click.option("--output-dir", "-o", default=None, help="Output directory (default: current dir)")
@click.option("--format", "-f", "fmt", type=click.Choice(["hermes", "claude", "raw"]), default="hermes", help="Output format")
def inject_soul_cmd(profile, persona, output_dir, fmt):
    """Inject persona soul into a profile config file"""
    from augur.soul import inject_soul

    try:
        result_path = inject_soul(profile, persona, format=fmt, output_dir=output_dir)
        click.echo(f"Soul injected: {result_path}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command("telegram")
def telegram_cmd():
    """Start the Telegram bot"""
    from augur.optional_deps import require_optional
    try:
        require_optional("telegram", "Telegram bot integration", "pip install 'augur-agents[telegram]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.bots.telegram_bot import run_telegram_bot
    run_telegram_bot()


@main.command("slack")
@click.option("--mode", type=click.Choice(["socket", "http"]), default="socket",
              help="Mode: socket (dev) or http (production)")
@click.option("--port", type=int, default=3000, help="Port for HTTP mode")
def slack_cmd(mode, port):
    """Start the Slack bot"""
    from augur.optional_deps import require_optional
    try:
        require_optional("slack_bolt", "Slack bot integration", "pip install 'augur-agents[slack]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.bots.slack_bot import run_slack_bot
    run_slack_bot(mode=mode, port=port)


@main.command("wechat")
@click.option("--mode", type=click.Choice(["personal", "wecom", "webhook"]), default="personal",
              help="Mode: personal (GeWeChat), wecom (enterprise), or webhook (push only)")
@click.option("--port", type=int, default=8066, help="Port for callback server")
def wechat_cmd(mode, port):
    """Start the WeChat bot (personal/wecom/webhook)"""
    from augur.optional_deps import require_optional
    try:
        require_optional("augur.bots.wechat_bot", "WeChat bot integration", "pip install 'augur-agents[wechat]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.bots.wechat_bot import run_wechat_bot
    run_wechat_bot(mode=mode, port=port)


@main.command("lark")
@click.option("--mode", type=click.Choice(["event", "webhook"]), default="event",
              help="Mode: event (subscription) or webhook (push only)")
@click.option("--port", type=int, default=9000, help="Port for event server")
def lark_cmd(mode, port):
    """Start the Lark/Feishu bot"""
    from augur.optional_deps import require_optional
    try:
        require_optional("augur.bots.lark_bot", "Lark/Feishu bot integration", "pip install 'augur-agents[lark]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.bots.lark_bot import run_lark_bot
    run_lark_bot(mode=mode, port_num=port)


@main.command("cron-run")
def cron_run_cmd():
    """Run watchlist analysis once (manual trigger)"""
    from augur.cron import run_watchlist_analysis

    click.echo("Running watchlist analysis...\n")
    results = run_watchlist_analysis()

    if not results:
        click.echo("No results. Is your watchlist empty?")
        click.echo("Add tickers with: augur watchlist-add TICKER --pe X --roe X")
        return

    click.echo(f"\nCompleted: {len(results)} tickers analyzed.")


@main.command("cron-start")
def cron_start_cmd():
    """Start the scheduler daemon"""
    from augur.optional_deps import require_optional
    try:
        require_optional("apscheduler", "scheduled watchlist analysis (cron daemon)", "pip install 'augur-agents[cron]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.cron import start_scheduler
    start_scheduler()


@main.command("watchlist-add")
@click.argument("ticker")
@click.option("--pe", type=float, default=None, help="PE ratio")
@click.option("--pb", type=float, default=None, help="PB ratio")
@click.option("--roe", type=float, default=None, help="Return on equity (decimal)")
@click.option("--gross-margins", type=float, default=None, help="Gross margins (decimal)")
@click.option("--revenue-growth", type=float, default=None, help="Revenue growth (decimal)")
@click.option("--debt-ratio", type=float, default=None, help="Debt ratio")
@click.option("--fcf", type=float, default=None, help="Free cash flow")
@click.option("--market-cap", type=float, default=None, help="Market cap")
@click.option("--price", type=float, default=None, help="Current price")
@click.option("--sector", default=None, help="Sector name (e.g. Technology)")
@click.option("--industry", default=None, help="Industry name (e.g. Semiconductor)")
def watchlist_add_cmd(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price, sector, industry):
    """Add a ticker to the watchlist"""
    from augur.cron import add_to_watchlist, WATCHLIST_PATH

    metrics = {}
    if pe is not None:
        metrics["pe"] = pe
    if pb is not None:
        metrics["pb"] = pb
    if roe is not None:
        metrics["roe"] = roe
    if gross_margins is not None:
        metrics["gross_margins"] = gross_margins
    if revenue_growth is not None:
        metrics["revenue_growth"] = revenue_growth
    if debt_ratio is not None:
        metrics["debt_ratio"] = debt_ratio
    if fcf is not None:
        metrics["fcf"] = fcf
    if market_cap is not None:
        metrics["market_cap"] = market_cap
    if price is not None:
        metrics["price"] = price
    if sector is not None:
        metrics["sector"] = sector
    if industry is not None:
        metrics["industry"] = industry

    config = add_to_watchlist(ticker, metrics)
    watchlist = config.get("watchlist", [])

    click.echo(f"Added {ticker.upper()} to watchlist.")
    if metrics:
        click.echo(f"  Metrics: {metrics}")
    click.echo(f"  Total watchlist: {len(watchlist)} tickers")
    click.echo(f"  Config: {WATCHLIST_PATH}")


@main.command("watchlist-show")
def watchlist_show_cmd():
    """Show the current watchlist"""
    from augur.cron import load_watchlist, WATCHLIST_PATH

    config = load_watchlist()
    watchlist = config.get("watchlist", [])
    schedule = config.get("schedule", {})

    if not watchlist:
        click.echo("Watchlist is empty.")
        click.echo("Add tickers with: augur watchlist-add TICKER --pe X --roe X")
        return

    click.echo(f"Augur Watchlist ({len(watchlist)} tickers)")
    click.echo(f"Config: {WATCHLIST_PATH}")
    click.echo(f"Schedule: {schedule.get('cron', 'not set')} ({schedule.get('timezone', 'UTC')})")
    click.echo("")
    click.echo(f"{'Ticker':<10s} {'PE':<8s} {'ROE':<8s} {'GM':<8s} {'Price':<10s}")
    click.echo("-" * 50)

    for item in watchlist:
        ticker = item.get("ticker", "?")
        pe = f"{item['pe']:.1f}" if "pe" in item else "-"
        roe = f"{item['roe']:.2f}" if "roe" in item else "-"
        gm = f"{item['gross_margins']:.2f}" if "gross_margins" in item else "-"
        price = f"{item['price']:.2f}" if "price" in item else "-"
        click.echo(f"{ticker:<10s} {pe:<8s} {roe:<8s} {gm:<8s} {price:<10s}")


@main.command("backtest")
@click.argument("ticker", required=False, default="AAPL")
@click.option("--days", type=int, default=30, help="Number of days to backtest")
@click.option("--demo", is_flag=True, help="Use generated sample data")
@click.option("--live", is_flag=True, help="Use real historical data from yfinance")
def backtest_cmd(ticker, days, demo, live):
    """Run historical backtest on a ticker"""
    from augur.backtest import Backtester, generate_sample_data

    click.echo(f"Running backtest for {ticker.upper()} ({days} days)...\n")

    if live:
        # Use real data from yfinance
        from augur.optional_deps import is_available
        if not is_available("augur.data"):
            click.echo(
                "Error: Package 'augur.data' is required for real-time market data fetching but is not installed.\n"
                "  Install with: pip install 'augur-agents[data]'\n"
                "  Core commands (analyze, consensus, list-personas) still work without it.\n"
                "  Falling back to sample data...\n",
                err=True,
            )
        else:
            try:
                backtester = Backtester()
                result = backtester.run_live_backtest(ticker, days=days)
                click.echo(result.summary)
                click.echo(f"\nTotal records: {len(result.records)}")
                click.echo(f"Consensus IC (20d): {result.consensus_ic:.4f}")
                click.echo(f"\n[数据来源: yfinance 实时历史数据]")
                return
            except ImportError as e:
                click.echo(
                    f"Error: {e}\n"
                    f"  Install with: pip install 'augur-agents[data]'\n"
                    f"  Falling back to sample data...\n",
                    err=True,
                )
            except Exception as e:
                click.echo(
                    f"Error fetching live data: {e}\n"
                    f"  Suggestion: Check network connection or try a different ticker.\n"
                    f"  Falling back to sample data...\n",
                    err=True,
                )

    historical_data, forward_returns = generate_sample_data(ticker, days)

    backtester = Backtester()
    result = backtester.run_backtest(ticker, historical_data, forward_returns)

    click.echo(result.summary)
    click.echo(f"\nTotal records: {len(result.records)}")
    click.echo(f"Consensus IC (20d): {result.consensus_ic:.4f}")


@main.command("ic-report")
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
        click.echo("No backtest records found. Run 'augur backtest TICKER --demo' first.")
        return

    click.echo(f"{'Rank':<5} {'Agent':<22} {'IC 5d':<10} {'IC 20d':<10} {'IC 60d':<10} {'Hit Rate':<10} {'Predictions'}")
    click.echo("-" * 85)

    for i, ic in enumerate(ics, 1):
        click.echo(
            f"{i:<5} {ic.agent_id:<22} {ic.ic_5d:<10.4f} {ic.ic_20d:<10.4f} "
            f"{ic.ic_60d:<10.4f} {ic.hit_rate:<10.1%} {ic.total_predictions}"
        )


@main.command("fetch")
@click.argument("ticker")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def fetch_cmd(ticker, as_json):
    """Fetch real-time market data for a ticker (via yfinance)"""
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
        click.echo(f"Auto-fetching data for {ticker.upper()} from yfinance...\n")
        ctx = fetch_market_context(ticker)
        click.echo(f"  Price: {ctx.price:.2f} | PE: {ctx.pe:.1f} | ROE: {ctx.roe:.2%} | GM: {ctx.gross_margins:.2%}")
        click.echo(f"  [数据来源: yfinance 实时]\n")
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
        click.echo(f"\nKey Findings:")
        for f in result.key_findings:
            click.echo(f"  - {clean_output(f)}")

    if result.risks:
        click.echo(f"\nRisks:")
        for r in result.risks:
            click.echo(f"  - {clean_output(r)}")


if __name__ == "__main__":
    main()
