# -*- coding: utf-8 -*-
"""augur.cli_commands.analysis - analyze / consensus / report / list-personas"""

import click

from augur.cli_helpers import _auto_fetch_context, _print_result


@click.command("analyze")
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
            separator = "━" * 46  # heavy horizontal line

            num_agents = len(results)
            click.echo(separator)
            click.echo(f"  {ticker.upper()} — {num_agents} Masters Consensus")
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
                finding_emojis = ["\U0001f6e1️", "⚡", "\U0001f680", "\U0001f4a1", "\U0001f4ca"]
                for i, finding in enumerate(consensus.key_findings):
                    emoji = finding_emojis[i % len(finding_emojis)]
                    click.echo(f"    • {emoji} {clean_output(finding)}")

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


@click.command("consensus")
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


@click.command("report")
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


@click.command("list-personas")
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
