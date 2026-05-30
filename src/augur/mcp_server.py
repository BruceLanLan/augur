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

import re
from typing import Optional


def _build_context(ticker: str, pe: float = 0, pb: float = 0, roe: float = 0,
                   gross_margins: float = 0, revenue_growth: float = 0,
                   debt_ratio: float = 0, fcf: float = 0, market_cap: float = 0,
                   price: float = 0, institutional_ownership: float = 0,
                   insider_ownership: float = 0, rsi: float = 50,
                   volatility_20d: float = 0, short_interest: float = 0,
                   volume: float = 0, sector: str = "", industry: str = "",
                   auto_fetch: bool = True):
    """Build a MarketContext from parameters, with optional auto-fetch from yfinance."""
    from augur.personas.base import MarketContext

    # Auto-fetch if no core metrics provided
    has_metrics = any([pe, pb, roe, gross_margins, revenue_growth, market_cap, price])
    if not has_metrics and auto_fetch:
        try:
            from augur.data import fetch_market_context
            return fetch_market_context(ticker)
        except Exception:
            pass

    return MarketContext(
        ticker=ticker.upper(),
        pe=pe, pb=pb, roe=roe,
        gross_margins=gross_margins,
        revenue_growth=revenue_growth,
        debt_ratio=debt_ratio,
        fcf=fcf,
        market_cap=market_cap,
        price=price,
        institutional_ownership=institutional_ownership,
        insider_ownership=insider_ownership,
        rsi=rsi,
        volatility_20d=volatility_20d,
        short_interest=short_interest,
        volume=volume,
        sector=sector,
        industry=industry,
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
                      fcf: float = 0, market_cap: float = 0, price: float = 0,
                      institutional_ownership: float = 0, insider_ownership: float = 0,
                      rsi: float = 50, sector: str = "", industry: str = "") -> str:
        """Analyze a ticker with one or all agents. Auto-fetches live data if no metrics given.

        Args:
            ticker: Stock ticker symbol (e.g. AAPL, NVDA, 0700.HK)
            persona: Optional specific persona ID (e.g. buffett, graham). If None, uses all agents.
            pe: PE ratio
            pb: PB ratio
            roe: Return on equity (decimal, e.g. 0.15 for 15%)
            gross_margins: Gross margins (decimal, e.g. 0.45 for 45%)
            revenue_growth: Revenue growth rate (decimal)
            debt_ratio: Debt ratio as fraction of total assets (decimal, e.g. 0.35 for 35%)
            fcf: Free cash flow in billions USD
            market_cap: Market cap in billions USD
            price: Current stock price
            institutional_ownership: Institutional ownership percentage (0-100)
            insider_ownership: Insider ownership percentage (0-100)
            rsi: RSI indicator (default 50 = neutral)
            sector: Sector name (e.g. Technology)
            industry: Industry name
        """
        from augur.registry import AgentRegistry

        if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
            return "Error: Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens."

        ctx = _build_context(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio,
                             fcf, market_cap, price, institutional_ownership, insider_ownership,
                             rsi, sector=sector, industry=industry)
        registry = AgentRegistry()

        if persona:
            agent = registry.get(persona)
            if not agent:
                return f"Error: Persona '{persona}' not found. Available: {', '.join(a.agent_id for a in registry.get_all())}"
            result = agent.analyze(ctx)
            lines = [
                f"Agent: {result.agent_name}",
                f"Signal: {result.signal.value.upper()}",
                f"Score: {result.score:.1f}/10",
                f"Confidence: {result.confidence:.0%}",
            ]
            if result.key_findings:
                lines.append("Key Findings:")
                for f in result.key_findings[:4]:
                    lines.append(f"  - {f}")
            if result.risks:
                lines.append("Risks:")
                for r in result.risks[:3]:
                    lines.append(f"  - {r}")
            lines.append(f"\nReasoning:\n{result.reasoning}")
            return "\n".join(lines)
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
                        price: float = 0, institutional_ownership: float = 0,
                        insider_ownership: float = 0, rsi: float = 50,
                        sector: str = "", industry: str = "") -> str:
        """Get multi-agent consensus on a ticker. Auto-fetches live data if no metrics given.

        Args:
            ticker: Stock ticker symbol
            pe: PE ratio
            pb: PB ratio
            roe: Return on equity (decimal)
            gross_margins: Gross margins (decimal)
            revenue_growth: Revenue growth rate (decimal)
            debt_ratio: Debt ratio as fraction (decimal, e.g. 0.35)
            fcf: Free cash flow in billions USD
            market_cap: Market cap in billions USD
            price: Current stock price
            institutional_ownership: Institutional ownership % (0-100)
            insider_ownership: Insider ownership % (0-100)
            rsi: RSI indicator (default 50)
            sector: Sector name
            industry: Industry name
        """
        from augur.registry import AgentRegistry, DecisionCoordinator

        if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
            return "Error: Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens."

        ctx = _build_context(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio,
                             fcf, market_cap, price, institutional_ownership, insider_ownership,
                             rsi, sector=sector, industry=industry)
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)

        results = coordinator.analyze_with_all(ctx)
        consensus = coordinator.get_consensus(results, ticker=ticker.upper(), context=ctx)

        pos = consensus.metadata.get("position_sizing", {})
        kelly = pos.get("position_pct", None)
        lines = [
            f"Consensus for {ticker.upper()}:",
            f"  Signal: {consensus.signal.value.upper()}",
            f"  Score: {consensus.score:.1f}/10",
            f"  Confidence: {consensus.confidence:.0%}",
        ]
        if kelly is not None:
            lines.append(f"  Kelly Position: {kelly:.1f}%")
        lines.append(f"  Reasoning: {consensus.reasoning}")
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
        if not yaml_content or not yaml_content.strip():
            return "Error: YAML content cannot be empty"
        if len(yaml_content) > 10240:
            return "Error: YAML content too large (max 10KB)"

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
                     price: float = 0, sector: str = "", industry: str = "") -> str:
        """Run a multi-round debate among agents on a ticker. Auto-fetches live data if no metrics given.

        Args:
            ticker: Stock ticker symbol
            rounds: Number of debate rounds (default 2)
            pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price: Financial metrics
            sector: Sector name
            industry: Industry name
        """
        from augur.registry import AgentRegistry, DecisionCoordinator

        if not re.match(r'^[A-Za-z0-9.\-]{1,15}$', ticker):
            return "Error: Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens."
        rounds = max(1, min(5, rounds))

        ctx = _build_context(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio,
                             fcf, market_cap, price, sector=sector, industry=industry)
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

    @mcp.tool()
    def augur_fetch(ticker: str) -> str:
        """Fetch real-time market data for a ticker without running analysis.

        Args:
            ticker: Stock ticker symbol (e.g. AAPL, NVDA, 0700.HK)

        Returns:
            Key market metrics: price, PE, gross margin, ROE, debt ratio, market cap, etc.
        """
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            lines = [
                f"Market data for {ctx.ticker} (via yfinance):",
                f"  Price:        ${ctx.price:.2f}",
                f"  PE:           {ctx.pe:.1f}",
                f"  PB:           {ctx.pb:.2f}",
                f"  Market Cap:   ${ctx.market_cap:.0f}B",
                f"  ROE:          {ctx.roe:.1%}",
                f"  Gross Margin: {ctx.gross_margins:.1%}",
                f"  Op. Margin:   {ctx.operating_margins:.1%}",
                f"  Rev Growth:   {ctx.revenue_growth:.1%}",
                f"  Debt Ratio:   {ctx.debt_ratio:.1%}",
                f"  FCF:          ${ctx.fcf:.1f}B",
                f"  RSI:          {ctx.rsi:.0f}",
                f"  Beta:         {ctx.beta_1y:.2f}",
                f"  Sector:       {ctx.sector}",
                f"  Industry:     {ctx.industry}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching data for {ticker}: {e}\nMake sure yfinance is installed: pip install 'augur-agents[data]'"

    return mcp


def run_server():
    """Run the MCP server in stdio mode."""
    mcp = create_server()
    mcp.run(transport="stdio")


# Alias for backward-compatibility with augur-mcp entry point
main = run_server


if __name__ == "__main__":
    run_server()
