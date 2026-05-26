# -*- coding: utf-8 -*-
"""
augur.mcp_server - MCP Server for Augur (stdio mode)

Provides 6 tools:
  - augur_analyze
  - augur_consensus
  - augur_list_personas
  - augur_configure
  - augur_create_persona
  - augur_debate
"""

from typing import Optional


def _build_context(ticker: str, pe: float = 0, pb: float = 0, roe: float = 0,
                   gross_margins: float = 0, revenue_growth: float = 0,
                   debt_ratio: float = 0, fcf: float = 0, market_cap: float = 0,
                   price: float = 0):
    """Build a MarketContext from parameters."""
    from augur.personas.base import MarketContext
    return MarketContext(
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


def create_server():
    """Create and configure the MCP server."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "The 'mcp' package is required for the MCP server. "
            "Install it with: pip install 'mcp>=1.0.0' (requires Python 3.10+)"
        )

    mcp = FastMCP("augur", instructions="Multi-agent investment analysis system with 18 investor persona agents")

    @mcp.tool()
    def augur_analyze(ticker: str, persona: Optional[str] = None, pe: float = 0,
                      pb: float = 0, roe: float = 0, gross_margins: float = 0,
                      revenue_growth: float = 0, debt_ratio: float = 0,
                      fcf: float = 0, market_cap: float = 0, price: float = 0) -> str:
        """Analyze a ticker with one or all agents.

        Args:
            ticker: Stock ticker symbol (e.g. AAPL, NVDA)
            persona: Optional specific persona ID (e.g. buffett, graham). If None, uses all agents.
            pe: PE ratio
            pb: PB ratio
            roe: Return on equity (decimal, e.g. 0.15 for 15%)
            gross_margins: Gross margins (decimal, e.g. 0.45 for 45%)
            revenue_growth: Revenue growth rate (decimal)
            debt_ratio: Debt ratio
            fcf: Free cash flow
            market_cap: Market capitalization
            price: Current stock price
        """
        from augur.registry import AgentRegistry

        ctx = _build_context(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price)
        registry = AgentRegistry()

        if persona:
            agent = registry.get(persona)
            if not agent:
                return f"Error: Persona '{persona}' not found. Available: {', '.join(a.agent_id for a in registry.get_all())}"
            result = agent.analyze(ctx)
            return f"Agent: {result.agent_name}\nSignal: {result.signal.value}\nScore: {result.score:.1f}/10\nConfidence: {result.confidence:.0%}\nReasoning: {result.reasoning}"
        else:
            lines = [f"Analysis of {ticker.upper()} with {len(registry.get_all())} agents:\n"]
            for agent in registry.get_all():
                try:
                    result = agent.analyze(ctx)
                    lines.append(f"  {result.agent_name:20s} | {result.signal.value:8s} | {result.score:.1f}/10")
                except Exception as e:
                    lines.append(f"  {agent.name:20s} | ERROR    | {e}")
            return "\n".join(lines)

    @mcp.tool()
    def augur_consensus(ticker: str, pe: float = 0, pb: float = 0, roe: float = 0,
                        gross_margins: float = 0, revenue_growth: float = 0,
                        debt_ratio: float = 0, fcf: float = 0, market_cap: float = 0,
                        price: float = 0) -> str:
        """Get multi-agent consensus on a ticker.

        Args:
            ticker: Stock ticker symbol
            pe: PE ratio
            pb: PB ratio
            roe: Return on equity (decimal)
            gross_margins: Gross margins (decimal)
            revenue_growth: Revenue growth rate (decimal)
            debt_ratio: Debt ratio
            fcf: Free cash flow
            market_cap: Market capitalization
            price: Current stock price
        """
        from augur.registry import AgentRegistry, DecisionCoordinator

        ctx = _build_context(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price)
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)

        results = coordinator.analyze_with_all(ctx)
        consensus = coordinator.get_consensus(results, ticker=ticker.upper(), context=ctx)

        lines = [
            f"Consensus for {ticker.upper()}:",
            f"  Signal: {consensus.signal.value}",
            f"  Score: {consensus.score:.1f}/10",
            f"  Confidence: {consensus.confidence:.0%}",
            f"  Reasoning: {consensus.reasoning}",
        ]
        if consensus.key_findings:
            lines.append("  Key Findings:")
            for f in consensus.key_findings:
                lines.append(f"    - {f}")
        if consensus.risks:
            lines.append("  Risks:")
            for r in consensus.risks:
                lines.append(f"    - {r}")
        return "\n".join(lines)

    @mcp.tool()
    def augur_list_personas() -> str:
        """List all available investor personas."""
        from augur.registry import AgentRegistry

        registry = AgentRegistry()
        agents = registry.get_all()

        lines = [f"Available Personas ({len(agents)} total):\n"]
        for agent in agents:
            philosophy = ", ".join(agent.philosophy[:2]) if agent.philosophy else ""
            lines.append(f"  {agent.agent_id:<20s} {agent.name:<25s} {philosophy}")
        return "\n".join(lines)

    @mcp.tool()
    def augur_configure(persona_id: str, model: str) -> str:
        """Configure model for a specific persona.

        Args:
            persona_id: The persona ID to configure (e.g. buffett, graham)
            model: The model to use (e.g. claude-sonnet-4-6, deepseek-v4)
        """
        from augur.config import get_config, set_config, save_config

        set_config(f"per_agent.{persona_id}", model)
        path = save_config()
        return f"Configured {persona_id} to use model '{model}'. Saved to {path}"

    @mcp.tool()
    def augur_create_persona(yaml_content: str) -> str:
        """Create a new persona from YAML content.

        Args:
            yaml_content: YAML content defining the persona (must include agent_id, name, scoring_weights)
        """
        import tempfile
        from pathlib import Path
        from augur.persona_loader import load_persona_yaml
        from augur.registry import get_registry

        # Write to temp file and load
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            agent = load_persona_yaml(tmp_path)
            get_registry().register(agent)
            return f"Created and registered persona: {agent.agent_id} ({agent.name})"
        except Exception as e:
            return f"Error creating persona: {e}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @mcp.tool()
    def augur_debate(ticker: str, rounds: int = 2, pe: float = 0, pb: float = 0,
                     roe: float = 0, gross_margins: float = 0, revenue_growth: float = 0,
                     debt_ratio: float = 0, fcf: float = 0, market_cap: float = 0,
                     price: float = 0) -> str:
        """Run a multi-round debate among agents on a ticker.

        Args:
            ticker: Stock ticker symbol
            rounds: Number of debate rounds (default 2)
            pe: PE ratio
            pb: PB ratio
            roe: Return on equity (decimal)
            gross_margins: Gross margins (decimal)
            revenue_growth: Revenue growth rate (decimal)
            debt_ratio: Debt ratio
            fcf: Free cash flow
            market_cap: Market capitalization
            price: Current stock price
        """
        from augur.registry import AgentRegistry, DecisionCoordinator

        ctx = _build_context(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price)
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)

        results = coordinator.run_debate(ctx, rounds=rounds)
        consensus = coordinator.get_consensus(results, ticker=ticker.upper(), context=ctx)

        lines = [
            f"Debate Results for {ticker.upper()} ({rounds} rounds, {len(results)} agents):",
            f"  Consensus Signal: {consensus.signal.value}",
            f"  Score: {consensus.score:.1f}/10",
            f"  Confidence: {consensus.confidence:.0%}",
            "",
            "Agent Positions After Debate:",
        ]
        for agent_id, result in results.items():
            lines.append(f"  {result.agent_name:20s} | {result.signal.value:8s} | {result.score:.1f}/10")
        return "\n".join(lines)

    return mcp


def run_server():
    """Run the MCP server in stdio mode."""
    mcp = create_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
