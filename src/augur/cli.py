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
  augur workflow TICKER     - Multi-step agentic pipeline
"""

import click

from augur import __version__


@click.group()
@click.version_option(version=__version__, prog_name="augur")
@click.option("--no-color", is_flag=True, default=False, help="Disable color output and emojis")
@click.pass_context
def main(ctx, no_color):
    """Augur - Multi-agent investment analysis system.

    \b
    18 virtual investor personas analyze stocks from different perspectives
    and form consensus recommendations with Kelly position sizing.

    \b
    Quick start:
      augur analyze AAPL          # Full analysis with all 18 agents
      augur consensus NVDA        # Consensus recommendation
      augur list-personas         # Show all personas
      augur fetch TSLA            # Fetch real-time data
      augur workflow AAPL --steps fetch,analyze,consensus,committee
    """
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
    """Analyze a ticker with one or all agents (auto-fetches data if no metrics specified).

    \b
    Examples:
      augur analyze AAPL                     # Auto-fetch & analyze
      augur analyze NVDA --pe 60 --roe 0.45  # Manual metrics
      augur analyze TSLA --persona buffett   # Single persona
      augur analyze MSFT --json              # JSON output
    """
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
            from augur.registry import DecisionCoordinator
            from augur.cli_format import signal_icon, clean_output

            coordinator = DecisionCoordinator(registry)
            try:
                results = coordinator.analyze_with_all(ctx)
                consensus = coordinator.get_consensus(results, ticker=ticker.upper(), context=ctx)
            except Exception as e:
                click.echo(f"Analysis failed: {e}", err=True)
                raise SystemExit(1)

            # Build the README-style consensus summary box
            separator = "\u2501" * 46  # heavy horizontal line

            num_agents = len(results)
            click.echo(separator)
            click.echo(f"  {ticker.upper()} \u2014 {num_agents} Masters Consensus")
            click.echo(separator)

            icon = signal_icon(consensus.signal.value)
            click.echo(f"  Signal:     {icon} {consensus.signal.value.upper()}")
            click.echo(f"  Score:      {consensus.score:.1f} / 10")
            click.echo(f"  Confidence: {consensus.confidence:.0%}")

            pos = consensus.metadata.get("position_sizing", {})
            if pos:
                click.echo(f"  Kelly Size: {pos.get('position_pct', 0):.1f}%")

            # Key Findings
            if consensus.key_findings:
                click.echo("")
                click.echo("  Key Findings:")
                # Use emoji bullets matching README style
                finding_emojis = ["\U0001f6e1\ufe0f", "\u26a1", "\U0001f680", "\U0001f4a1", "\U0001f4ca"]
                for i, finding in enumerate(consensus.key_findings):
                    emoji = finding_emojis[i % len(finding_emojis)]
                    click.echo(f"    \u2022 {emoji} {clean_output(finding)}")

            # Signal distribution breakdown
            click.echo("")
            from augur.personas.base import SignalType
            bullish_agents = [aid for aid, r in results.items() if r.signal == SignalType.BULLISH]
            neutral_agents = [aid for aid, r in results.items() if r.signal == SignalType.NEUTRAL]
            bearish_agents = [aid for aid, r in results.items() if r.signal == SignalType.BEARISH]

            if bullish_agents:
                names = ", ".join(bullish_agents[:5])
                suffix = f"..." if len(bullish_agents) > 5 else ""
                click.echo(f"  BULLISH ({len(bullish_agents)}): {names}{suffix}")
            if neutral_agents:
                names = ", ".join(neutral_agents[:5])
                suffix = f"..." if len(neutral_agents) > 5 else ""
                click.echo(f"  NEUTRAL  ({len(neutral_agents)}): {names}{suffix}")
            if bearish_agents:
                names = ", ".join(bearish_agents[:5])
                suffix = f"..." if len(bearish_agents) > 5 else ""
                click.echo(f"  BEARISH ({len(bearish_agents)}): {names}{suffix}")

            click.echo(separator)


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
    """Get multi-agent consensus on a ticker (auto-fetches data if no metrics specified).

    \b
    Examples:
      augur consensus AAPL                        # Auto-fetch consensus
      augur consensus NVDA --pe 60 --roe 0.45     # Manual metrics
      augur consensus TSLA --json                 # JSON output
    """
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


@main.command("report")
@click.argument("ticker")
@click.option("--output", "-o", default=None, help="Save report to file")
@click.option("--pe", type=float, default=None, help="PE ratio")
@click.option("--pb", type=float, default=None, help="PB ratio")
@click.option("--roe", type=float, default=None, help="Return on equity (decimal)")
@click.option("--gross-margins", type=float, default=None, help="Gross margins (decimal)")
@click.option("--revenue-growth", type=float, default=None, help="Revenue growth (decimal)")
@click.option("--debt-ratio", type=float, default=None, help="Debt/assets ratio (decimal)")
@click.option("--fcf", type=float, default=None, help="Free cash flow (billions USD)")
@click.option("--market-cap", type=float, default=None, help="Market cap (billions USD)")
@click.option("--price", type=float, default=None, help="Current stock price")
@click.option("--sector", default="", help="Sector name")
@click.option("--industry", default="", help="Industry name")
def report_cmd(ticker, output, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price, sector, industry):
    """Generate a deep analysis report for a ticker.

    \b
    Examples:
      augur report AAPL                     # Auto-fetch & generate report
      augur report NVDA --pe 60 --roe 0.45  # Manual metrics
      augur report TSLA -o tsla_report.md   # Save to file
    """
    from augur.personas.base import MarketContext
    from augur.registry import AgentRegistry, DecisionCoordinator
    from augur.report import generate_report

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

    click.echo(f"Generating deep report for {ticker.upper()}...\n")
    results = coordinator.analyze_with_all(ctx)
    consensus = coordinator.get_consensus(results, ticker=ticker.upper(), context=ctx)

    report = generate_report(ticker.upper(), ctx, results, consensus)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)
        click.echo(f"报告已保存至: {output}")
    else:
        click.echo(report)


@main.command("list-personas")
def list_personas_cmd():
    """List all available personas.

    \b
    Examples:
      augur list-personas
    """
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
    """Add a ticker to the watchlist.

    \b
    Examples:
      augur watchlist-add AAPL --pe 30 --roe 0.55
      augur watchlist-add NVDA --sector Technology
      augur watchlist-add BTC-USD
    """
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


@main.command("fetch")
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


@main.command("workflow")
@click.argument("ticker")
@click.option(
    "--steps",
    default="",
    help=(
        "Comma-separated steps: fetch, analyze, consensus, committee, debate, sentiment. "
        "Default: follows your active terminal layout preset (analyst=fetch,analyze,consensus; "
        "trader/minimal=fetch,consensus; committee=fetch,analyze,consensus,committee)."
    ),
)
@click.option("--agents", "-a", default="", help="Comma-separated agent IDs (default: all personas)")
@click.option("--question", "-q", default="", help="Question for the committee step")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
def workflow_cmd(ticker, steps, agents, question, as_json):
    """Run a multi-step agentic analysis pipeline.

    \b
    Examples:
      augur workflow AAPL
      augur workflow NVDA --steps fetch,analyze,consensus,committee
      augur workflow TSLA --agents buffett,munger,dalio --steps fetch,analyze,committee
      augur workflow AAPL --json
    """
    from augur.workflow import run_workflow, VALID_STEPS

    if not as_json:
        steps_label = steps or "workspace default"
        click.echo(f"Running workflow for {ticker.upper()} ({steps_label})...\n")

    try:
        result = run_workflow(ticker, steps=steps, agents=agents, question=question)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo(f"  Valid steps: {', '.join(VALID_STEPS)}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Workflow failed: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        import json as _json
        payload = {k: v for k, v in result.items() if k != "summary"}
        click.echo(_json.dumps(payload, ensure_ascii=False, indent=2))
        return

    click.echo(result.get("summary", ""))


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


# ============ v8: Chat & Sentiment commands ============

@main.command("chat")
@click.argument("ticker")
@click.option("--persona", "-p", default=None, help="Persona to chat as (e.g. buffett, serenity)")
def chat_cmd(ticker, persona):
    """Get a quick persona response about a ticker"""
    from augur.chat import ChatEngine
    engine = ChatEngine()
    message = f"What do you think about {ticker.upper()}?"
    resp = engine.get_response(message, agent_id=persona)
    click.echo(f"\n{resp['agent_name']} on {ticker.upper()}:\n")
    click.echo(resp["response"])
    click.echo(f"\n[Topic: {resp.get('topic', 'general')}]")


@main.command("sentiment")
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


@main.command("serve")
@click.option("--port", default=8000, show_default=True, help="Dashboard port")
@click.option("--host", default="0.0.0.0", show_default=True, help="Bind host")
@click.option("--open", "open_browser", is_flag=True, default=False, help="Open browser on start")
def serve_cmd(port, host, open_browser):
    """Start the Augur web dashboard.

    \b
    Examples:
      augur serve                       # Start on default port 8000
      augur serve --port 8080           # Custom port
      augur serve --open                # Open browser automatically
    """
    import sys
    import os

    # Resolve dashboard app path relative to this file.
    # dashboard/ lives alongside augur/ under src/ (parents[1]) so this
    # resolves correctly both in a dev checkout and a real pip install —
    # unlike the old repo-root-relative path, which only worked because
    # dev/test runs happen to have the repo root on sys.path incidentally.
    from pathlib import Path as _Path
    dashboard_dir = _Path(__file__).resolve().parents[1] / "dashboard"
    if str(dashboard_dir) not in sys.path:
        sys.path.insert(0, str(dashboard_dir.parent))

    try:
        import uvicorn
    except ImportError:
        click.echo(
            "Error: uvicorn is not installed.\n"
            "  Install with: pip install uvicorn\n"
            "  Or run manually: python3 -m dashboard.app",
            err=True,
        )
        raise SystemExit(1)

    try:
        from dashboard.app import app as dashboard_app
    except ImportError as e:
        click.echo(
            f"Error: Could not import dashboard app: {e}\n"
            "  Run manually: python3 -m dashboard.app",
            err=True,
        )
        raise SystemExit(1)

    click.echo(f"\U0001f989 Augur Dashboard starting at http://localhost:{port}")

    if open_browser:
        import threading
        import webbrowser

        def _open():
            webbrowser.open(f"http://localhost:{port}")

        threading.Timer(1.0, _open).start()

    uvicorn.run(dashboard_app, host=host, port=port)


@main.command("watch")
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


@main.command("portfolio")
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


@main.command("skills")
@click.option("--school", default=None, help="Filter by school (value/growth/macro/china)")
@click.option("--lang", default=None, help="Filter by language (en/zh)")
def skills_cmd(school, lang):
    """List available Augur skill profiles.

    \b
    Examples:
      augur skills                        # Show all skills
      augur skills --school value         # Value investing skills only
      augur skills --lang zh              # Chinese-language skills only
      augur skills --school growth --lang en
    """
    import re as _re
    import yaml as _yaml
    from pathlib import Path as _Path

    skills_dir = _Path(__file__).resolve().parents[1] / "skills"

    if not skills_dir.exists():
        click.echo(
            "Skills directory not found.\n"
            "  Hint: Run generate_skills.py or check your augur installation.",
            err=True,
        )
        raise SystemExit(1)

    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        click.echo("No SKILL.md files found in skills/.")
        return

    rows = []
    for path in skill_files:
        try:
            content = path.read_text(encoding="utf-8")
            # Extract YAML frontmatter between --- delimiters
            m = _re.match(r"^---\n(.*?)\n---", content, _re.DOTALL)
            if not m:
                continue
            data = _yaml.safe_load(m.group(1)) or {}
            augur_meta = data.get("metadata", {}).get("augur", {})
            skill_school = augur_meta.get("school", "")
            skill_lang = augur_meta.get("language", "")
            skill_name = data.get("name", path.parent.name)
            skill_desc = data.get("description", "")

            if school and skill_school.lower() != school.lower():
                continue
            if lang and skill_lang.lower() != lang.lower():
                continue

            rows.append((skill_name, skill_desc, skill_lang, skill_school))
        except Exception:
            continue

    if not rows:
        click.echo("No skills match the given filters.")
        return

    # Print formatted table
    click.echo(f"\nAugur Skills ({len(rows)} found)\n")
    header = f"{'Name':<30s} {'Language':<10s} {'School':<10s} {'Description'}"
    click.echo(header)
    click.echo("-" * 90)
    for name, desc, skill_lang_val, skill_school_val in rows:
        # Truncate description for table fit
        short_desc = desc[:45] + "..." if len(desc) > 45 else desc
        click.echo(f"{name:<30s} {skill_lang_val:<10s} {skill_school_val:<10s} {short_desc}")


@main.command("committee")
@click.argument("ticker")
@click.option("--question", "-q", default="", help="Specific question for the committee")
@click.option("--agents", "-a", default="", help="Comma-separated agent IDs (default: all 18)")
@click.option("--preset", type=click.Choice(["value", "china", "macro", "growth", "all"]),
              default=None, help="Use a preset committee")
@click.option("--pe", type=float, default=None)
@click.option("--roe", type=float, default=None)
@click.option("--debt-ratio", type=float, default=None)
@click.option("--market-cap", type=float, default=None)
@click.option("--sector", default="", help="Sector name")
def committee_cmd(ticker, question, agents, preset, pe, roe, debt_ratio, market_cap, sector):
    """Convene an investment committee on a ticker.

    \b
    Examples:
      augur committee AAPL -q "Is the moat widening or narrowing?"
      augur committee NVDA --agents buffett,munger,dalio
      augur committee 0700.HK --preset china
      augur committee TSLA --preset growth -q "Is this a 10x from here?"
    """
    from augur.agents import AgentRegistry, DecisionCoordinator
    from augur.scanner.fetch import fetch_market_data

    PRESETS = {
        "value":  ["buffett", "graham", "munger", "fisher"],
        "china":  ["duan_yongping", "zhang_lei", "li_lu", "dan_bin"],
        "macro":  ["dalio", "soros", "marks", "arps"],
        "growth": ["cathie_wood", "thiel", "aschenbrenner", "lynch"],
        "all":    [],
    }

    ticker = ticker.upper()
    if not question:
        question = f"Should we invest in {ticker} at the current valuation?"

    # Resolve agent list
    agent_ids = []
    if preset:
        agent_ids = PRESETS.get(preset, [])
        click.echo(f"🏛️  Committee preset: {preset} ({len(agent_ids) or 18} masters)")
    elif agents:
        agent_ids = [a.strip() for a in agents.split(",") if a.strip()]
        click.echo(f"🏛️  Committee: {', '.join(agent_ids)}")
    else:
        click.echo("🏛️  Full committee: all 18 masters")

    # Auto-fetch market data
    click.echo(f"   Fetching data for {ticker}…")
    try:
        data = fetch_market_data(ticker)
        pe = pe or data.get("pe_ratio") or 0
        roe = roe or data.get("roe") or 0
        debt_ratio = debt_ratio or data.get("debt_ratio") or 0
        market_cap = market_cap or data.get("market_cap") or 0
        price = data.get("price") or 0
        sector = sector or data.get("sector") or ""
        if price:
            click.echo(f"   {ticker}: ${price:.2f} | PE={pe:.1f} | ROE={roe:.0%} | Sector={sector}")
    except Exception:
        price = 0

    # Build context
    from augur.scanner.context import MarketContext
    ctx = MarketContext(
        ticker=ticker, price=price or 0,
        pe_ratio=pe or 0, pb_ratio=0, roe=roe or 0,
        gross_margins=0, revenue_growth=0,
        debt_ratio=debt_ratio or 0, fcf=0,
        market_cap=market_cap or 0, sector=sector,
    )

    registry = AgentRegistry()
    coordinator = DecisionCoordinator(registry)

    if agent_ids:
        all_agents = {a.agent_id: a for a in registry.get_all()}
        selected = {aid: all_agents[aid] for aid in agent_ids if aid in all_agents}
        if not selected:
            click.echo(f"⚠  No valid agents in: {', '.join(agent_ids)}", err=True)
            raise SystemExit(1)
        responses = {aid: agent.analyze(ctx) for aid, agent in selected.items()}
    else:
        responses = coordinator.analyze_with_all(ctx)

    consensus = coordinator.get_consensus(responses, ticker=ticker, context=ctx)

    bullish = [(aid, r) for aid, r in responses.items() if r.signal.value == "bullish"]
    bearish = [(aid, r) for aid, r in responses.items() if r.signal.value == "bearish"]
    neutral = [(aid, r) for aid, r in responses.items() if r.signal.value == "neutral"]

    click.echo(f"\n{'═'*58}")
    click.echo(f"  Investment Committee: {ticker}")
    click.echo(f"  Q: {question}")
    click.echo(f"{'═'*58}")
    click.echo("  Independent Opinions")
    click.echo(f"  {'─'*54}")
    for aid, r in sorted(responses.items(), key=lambda x: -x[1].score):
        stance = r.signal.value.upper()
        color = "green" if stance == "BULLISH" else ("red" if stance == "BEARISH" else "yellow")
        line = f"  {r.agent_name:24s} │ {stance:8s} │ {r.score:.1f}/10"
        click.echo(line)
        if r.key_findings:
            click.echo(f"    → {r.key_findings[0]}")

    click.echo(f"\n  Dissents")
    click.echo(f"  {'─'*54}")
    if bearish:
        for aid, r in bearish:
            risk = r.risks[0] if r.risks else "No moat / valuation concern"
            click.echo(f"  ⚠  {r.agent_name}: {risk}")
    else:
        click.echo("  No bearish dissents.")

    kelly = consensus.metadata.get("position_sizing", {}).get("position_pct", 0)
    sig_color = "green" if consensus.signal.value == "bullish" else (
        "red" if consensus.signal.value == "bearish" else "yellow")
    click.echo(f"\n  Verdict")
    click.echo(f"  {'─'*54}")
    click.echo(f"  Signal:      {consensus.signal.value.upper()}")
    click.echo(f"  Score:       {consensus.score:.1f}/10")
    click.echo(f"  Confidence:  {consensus.confidence:.0%}")
    if kelly:
        click.echo(f"  Kelly Size:  {kelly:.0%}")
    click.echo(f"  Vote:        Bullish {len(bullish)} / Neutral {len(neutral)} / Bearish {len(bearish)}")
    click.echo(f"{'═'*58}\n")


@main.command("update")
def update_cmd():
    """Update Augur to the latest version from the repository.

    \b
    Examples:
      augur update          # Pull latest changes and reinstall
    """
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]

    click.echo(f"🦉 Augur {__version__} → checking for updates…")

    # Verify this is a git repo
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        click.echo(
            "⚠  This installation is not a git clone.\n"
            "   To update: git clone https://github.com/BruceLanLan/augur.git",
            err=True,
        )
        raise SystemExit(1)

    # Check for uncommitted changes that would block pull
    status = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if status.returncode != 0:
        click.echo(f"⚠  git status failed: {status.stderr.strip()}", err=True)
        raise SystemExit(1)

    if status.stdout.strip():
        click.echo(
            "⚠  Working tree has uncommitted changes — aborting to avoid conflicts.\n"
            "   Stash or commit your changes first: git stash",
            err=True,
        )
        raise SystemExit(1)

    # Pull
    click.echo("   Pulling latest changes…")
    pull = subprocess.run(
        ["git", "-C", str(repo_root), "pull", "--ff-only"],
        capture_output=True, text=True,
    )
    if pull.returncode != 0:
        click.echo(f"⚠  git pull failed:\n{pull.stderr.strip()}", err=True)
        raise SystemExit(1)

    if "Already up to date" in pull.stdout:
        click.echo(f"✅ Already up to date ({__version__}).")
        return

    click.echo(pull.stdout.strip())

    # Reinstall
    click.echo("   Reinstalling package…")
    pip = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    if pip.returncode != 0:
        click.echo(f"⚠  pip install failed:\n{pip.stderr.strip()}", err=True)
        raise SystemExit(1)

    # Re-import to get new version
    try:
        import importlib
        import augur as _augur_mod
        importlib.reload(_augur_mod)
        new_version = _augur_mod.__version__
    except Exception:
        new_version = "unknown"

    click.echo(f"✅ Updated to {new_version}.")


if __name__ == "__main__":
    main()
