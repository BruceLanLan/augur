# -*- coding: utf-8 -*-
"""augur.cli_commands.workflow - workflow / chat / committee"""

import click


@click.command("workflow")
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


@click.command("chat")
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


@click.command("committee")
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
