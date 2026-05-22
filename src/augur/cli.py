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
"""

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="augur")
def main():
    """Augur - Multi-agent investment analysis system"""
    pass


@main.command("analyze")
@click.argument("ticker")
@click.option("--persona", "-p", default=None, help="Specific persona ID to use")
@click.option("--pe", type=float, default=0, help="PE ratio")
@click.option("--pb", type=float, default=0, help="PB ratio")
@click.option("--roe", type=float, default=0, help="Return on equity (decimal, e.g. 0.15)")
@click.option("--gross-margins", type=float, default=0, help="Gross margins (decimal, e.g. 0.45)")
@click.option("--revenue-growth", type=float, default=0, help="Revenue growth (decimal)")
@click.option("--debt-ratio", type=float, default=0, help="Debt ratio")
@click.option("--fcf", type=float, default=0, help="Free cash flow")
@click.option("--market-cap", type=float, default=0, help="Market cap")
@click.option("--price", type=float, default=0, help="Current price")
def analyze_cmd(ticker, persona, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price):
    """Analyze a ticker with one or all agents"""
    from augur.personas.base import MarketContext
    from augur.registry import AgentRegistry

    ctx = MarketContext(
        ticker=ticker.upper(),
        pe=pe,
        pb=pb,
        roe=roe,
        gross_margins=gross_margins,
        revenue_growth=revenue_growth,
        debt_ratio=debt_ratio,
        fcf=fcf,
        market_cap=market_cap,
        price=price,
    )

    registry = AgentRegistry()

    if persona:
        agent = registry.get(persona)
        if not agent:
            click.echo(f"Error: Persona '{persona}' not found.", err=True)
            click.echo(f"Available: {', '.join(a.agent_id for a in registry.get_all())}", err=True)
            raise SystemExit(1)
        result = agent.analyze(ctx)
        _print_result(result)
    else:
        click.echo(f"Analyzing {ticker.upper()} with all {len(registry.get_all())} agents...\n")
        for agent in registry.get_all():
            try:
                result = agent.analyze(ctx)
                click.echo(f"  {result.agent_name:20s} | {result.signal.value:8s} | {result.score:.1f}/10 | conf={result.confidence:.0%}")
            except Exception as e:
                click.echo(f"  {agent.name:20s} | ERROR    | {e}")


@main.command("consensus")
@click.argument("ticker")
@click.option("--pe", type=float, default=0, help="PE ratio")
@click.option("--pb", type=float, default=0, help="PB ratio")
@click.option("--roe", type=float, default=0, help="Return on equity (decimal)")
@click.option("--gross-margins", type=float, default=0, help="Gross margins (decimal)")
@click.option("--revenue-growth", type=float, default=0, help="Revenue growth (decimal)")
@click.option("--debt-ratio", type=float, default=0, help="Debt ratio")
@click.option("--fcf", type=float, default=0, help="Free cash flow")
@click.option("--market-cap", type=float, default=0, help="Market cap")
@click.option("--price", type=float, default=0, help="Current price")
def consensus_cmd(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price):
    """Get multi-agent consensus on a ticker"""
    from augur.personas.base import MarketContext
    from augur.registry import AgentRegistry, DecisionCoordinator

    ctx = MarketContext(
        ticker=ticker.upper(),
        pe=pe,
        pb=pb,
        roe=roe,
        gross_margins=gross_margins,
        revenue_growth=revenue_growth,
        debt_ratio=debt_ratio,
        fcf=fcf,
        market_cap=market_cap,
        price=price,
    )

    registry = AgentRegistry()
    coordinator = DecisionCoordinator(registry)

    click.echo(f"Computing consensus for {ticker.upper()}...\n")
    results = coordinator.analyze_with_all(ctx)
    consensus = coordinator.get_consensus(results, ticker=ticker.upper(), context=ctx)

    click.echo(f"Signal:     {consensus.signal.value}")
    click.echo(f"Score:      {consensus.score:.1f}/10")
    click.echo(f"Confidence: {consensus.confidence:.0%}")
    click.echo(f"Reasoning:  {consensus.reasoning}")

    if consensus.key_findings:
        click.echo(f"\nKey Findings:")
        for f in consensus.key_findings:
            click.echo(f"  - {f}")

    if consensus.risks:
        click.echo(f"\nRisks:")
        for r in consensus.risks:
            click.echo(f"  - {r}")

    # Show individual agent breakdown
    click.echo(f"\n--- Agent Breakdown ({len(results)} agents) ---")
    for agent_id, result in results.items():
        click.echo(f"  {result.agent_name:20s} | {result.signal.value:8s} | {result.score:.1f}/10")


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
        click.echo("Error: uvicorn and fastapi required. Run: pip install fastapi uvicorn", err=True)
        raise SystemExit(1)


@main.command("inject-soul")
def inject_soul_cmd():
    """Inject soul into personas (Phase 2)"""
    click.echo("Coming in Phase 2")


def _print_result(result):
    """Pretty print a single analysis result"""
    click.echo(f"Agent:      {result.agent_name}")
    click.echo(f"Signal:     {result.signal.value}")
    click.echo(f"Score:      {result.score:.1f}/10")
    click.echo(f"Confidence: {result.confidence:.0%}")

    if result.key_findings:
        click.echo(f"\nKey Findings:")
        for f in result.key_findings:
            click.echo(f"  - {f}")

    if result.risks:
        click.echo(f"\nRisks:")
        for r in result.risks:
            click.echo(f"  - {r}")


if __name__ == "__main__":
    main()
