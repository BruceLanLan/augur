# -*- coding: utf-8 -*-
"""
augur.mcp_server - MCP Server for Augur (stdio mode)

Provides 10 tools (stdio; no HTTP auth — runs locally beside the analyst):
  - augur_analyze
  - augur_consensus
  - augur_committee
  - augur_debate
  - augur_fetch
  - augur_sentiment
  - augur_list_personas
  - augur_configure
  - augur_create_persona
  - augur_workflow

MCP tools do not use AUGUR_API_TOKEN (that applies to the Dashboard/REST API only).
Live market data requires optional deps (`pip install 'augur-agents[data]'`) and,
for premium sources, env keys such as FINNHUB_API_KEY / ALPHAVANTAGE_API_KEY.
Without them, augur_fetch / auto-fetch falls back to yfinance or returns a clear error.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Ticker validation pattern: 1-15 alphanumeric chars, dots, or hyphens
_TICKER_PATTERN = re.compile(r'^[A-Za-z0-9.\-]{1,15}$')
_PERSONA_ID_PATTERN = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')
_MODEL_NAME_PATTERN = re.compile(r'^[A-Za-z0-9._\-+:/]{1,128}$')


def _validate_ticker(ticker: str) -> Optional[str]:
    """Validate ticker format. Returns error message string if invalid, None if valid."""
    if not ticker or not _TICKER_PATTERN.match(ticker):
        return "Error: Invalid ticker format. Use 1-15 alphanumeric characters, dots, or hyphens."
    return None


def _validate_persona_id(persona_id: str) -> Optional[str]:
    """Validate persona_id for configure/create tools."""
    if not isinstance(persona_id, str) or not persona_id:
        return "Error: persona_id must be a non-empty string"
    if not _PERSONA_ID_PATTERN.match(persona_id):
        return (
            "Error: Invalid persona_id format. "
            "Use 1-64 alphanumeric characters, underscores, or hyphens."
        )
    return None


def _validate_model_name(model: str) -> Optional[str]:
    """Validate model name for configure tool."""
    if not isinstance(model, str) or not model:
        return "Error: model must be a non-empty string"
    if len(model) > 128:
        return "Error: model name too long (max 128 characters)"
    if not _MODEL_NAME_PATTERN.match(model):
        return (
            "Error: Invalid model format. "
            "Use alphanumeric characters, dots, hyphens, underscores, colons, or slashes."
        )
    return None


def _run_workflow_tool(
    ticker: str,
    steps: str = "fetch,analyze,consensus",
    agents: str = "",
    question: str = "",
) -> str:
    """Execute augur_workflow MCP tool logic (testable without FastMCP)."""
    err = _validate_ticker(ticker)
    if err:
        return err
    try:
        from augur.workflow import run_workflow, VALID_STEPS
        result = run_workflow(ticker, steps=steps, agents=agents, question=question)
        summary = result.get("summary", "")
        ran = ", ".join(result.get("steps", []))
        header = f"Workflow complete ({ran}) for {ticker.upper()}\n\n"
        return header + summary if summary else header + str(result)
    except ValueError as e:
        return f"Error: {e}\nValid steps: {', '.join(VALID_STEPS)}"
    except Exception as e:
        return f"Workflow failed for {ticker}: {e}"


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

    mcp = FastMCP(
        "augur",
        instructions=(
            "Multi-agent investment analysis with 18 investor personas. "
            "Seven tools: analyze, consensus, list_personas, configure, create_persona, debate, fetch. "
            "Omit financial metrics to auto-fetch via yfinance; install augur-agents[data] if fetch fails."
        ),
    )

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

        err = _validate_ticker(ticker)
        if err:
            return err

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

        err = _validate_ticker(ticker)
        if err:
            return err

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
        from augur.registry import AgentRegistry

        # Validate persona_id: must be a non-empty string of safe identifier chars
        # (alphanumeric, underscore, hyphen). This prevents the value from being
        # injected into a dot-notation config key path (set_config splits on "."),
        # which could overwrite arbitrary nested config keys or produce surprising
        # nesting when the value contains a ".".
        if not isinstance(persona_id, str) or not persona_id:
            return "Error: persona_id must be a non-empty string"
        err = _validate_persona_id(persona_id)
        if err:
            return err

        # Validate the persona actually exists in the registry
        registry = AgentRegistry()
        if not registry.get(persona_id):
            return f"Error: Persona '{persona_id}' not found. Available: {', '.join(a.agent_id for a in registry.get_all())}"

        err = _validate_model_name(model)
        if err:
            return err

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

        err = _validate_ticker(ticker)
        if err:
            return err
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
    def augur_committee(
        ticker: str,
        question: str,
        agents: str = "",
        pe: float = 0,
        pb: float = 0,
        roe: float = 0,
        gross_margins: float = 0,
        revenue_growth: float = 0,
        debt_ratio: float = 0,
        fcf: float = 0,
        market_cap: float = 0,
        price: float = 0,
        sector: str = "",
    ) -> str:
        """Convene an investment committee: multiple masters analyze independently then yield a verdict.

        More structured than debate — each master speaks first without seeing others' opinions,
        then dissents are recorded, and a weighted verdict is produced.

        Args:
            ticker: Stock ticker symbol (e.g. AAPL, NVDA, 0700.HK)
            question: The specific question for the committee (e.g. "Is the moat real at this valuation?")
            agents: Comma-separated agent IDs to include (empty = all 18, e.g. "buffett,munger,dalio")
            pe, pb, roe, gross_margins, revenue_growth, debt_ratio, fcf, market_cap, price, sector:
                Optional financial metrics (auto-fetched via yfinance if omitted)

        Returns:
            Structured committee report: independent opinions, dissents, and weighted verdict
        """
        ctx = _build_context(ticker, pe, pb, roe, gross_margins, revenue_growth, debt_ratio,
                             fcf, market_cap, price, sector=sector)

        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)

        # Resolve agent list
        selected_agents = None
        if agents.strip():
            selected_ids = [a.strip() for a in agents.split(",") if a.strip()]
            all_agents = {a.agent_id: a for a in registry.get_all()}
            selected_agents = {aid: all_agents[aid] for aid in selected_ids if aid in all_agents}
            if not selected_agents:
                return f"No valid agents found in: {agents}. Use augur_list_personas to see available IDs."

        # Run independent analysis (no cross-contamination)
        if selected_agents:
            responses = {aid: agent.analyze(ctx) for aid, agent in selected_agents.items()}
        else:
            responses = coordinator.analyze_with_all(ctx)

        consensus = coordinator.get_consensus(responses, ticker=ticker.upper(), context=ctx)

        # Build committee report
        bullish = [(aid, r) for aid, r in responses.items() if r.signal.value == "bullish"]
        bearish = [(aid, r) for aid, r in responses.items() if r.signal.value == "bearish"]
        neutral = [(aid, r) for aid, r in responses.items() if r.signal.value == "neutral"]

        lines = [
            f"═══ Investment Committee: {ticker.upper()} ═══",
            f"Question: {question}",
            f"Attendees: {len(responses)} masters",
            "",
            "─── Independent Opinions ───",
        ]
        for aid, r in sorted(responses.items(), key=lambda x: -x[1].score):
            stance = r.signal.value.upper()
            lines.append(f"  {r.agent_name:22s} │ {stance:8s} │ {r.score:.1f}/10")
            if r.key_findings:
                lines.append(f"    → {r.key_findings[0]}")

        lines += [
            "",
            "─── Dissents & Concerns ───",
        ]
        if bearish:
            lines.append(f"  BEARISH ({len(bearish)}): " + ", ".join(r.agent_name for _, r in bearish))
        if len(bullish) > 0 and len(bearish) > 0:
            for aid, r in bearish:
                if r.risks:
                    lines.append(f"    ⚠ {r.agent_name}: {r.risks[0]}")
        if not bearish:
            lines.append("  No bearish dissents.")

        kelly = consensus.metadata.get("position_sizing", {}).get("position_pct", 0)
        lines += [
            "",
            "─── Committee Verdict ───",
            f"  Signal:     {consensus.signal.value.upper()}",
            f"  Score:      {consensus.score:.1f}/10",
            f"  Confidence: {consensus.confidence:.0%}",
            f"  Kelly Size: {kelly:.0%}" if kelly else "  Kelly Size: N/A (signal not bullish)",
            f"  Vote:       Bullish {len(bullish)} / Neutral {len(neutral)} / Bearish {len(bearish)}",
        ]
        return "\n".join(lines)

    @mcp.tool()
    def augur_sentiment(ticker: str) -> str:
        """Fetch social sentiment analysis for a ticker (StockTwits + news signals).

        Args:
            ticker: Stock ticker symbol (e.g. AAPL, NVDA, BTC-USD)

        Returns:
            Sentiment score (-1.0 very bearish to +1.0 very bullish), volume, trending status.
        """
        err = _validate_ticker(ticker)
        if err:
            return err
        try:
            from augur.sentiment import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            result = analyzer.get_sentiment(ticker.upper())
            score_label = (
                "Very Bullish" if result.overall_score > 0.5 else
                "Bullish" if result.overall_score > 0.1 else
                "Neutral" if result.overall_score > -0.1 else
                "Bearish" if result.overall_score > -0.5 else
                "Very Bearish"
            )
            lines = [
                f"Social Sentiment for {result.ticker}:",
                f"  Score:    {result.overall_score:+.2f}  ({score_label})",
                f"  Volume:   {result.volume} messages",
                f"  Trending: {'Yes' if result.trending else 'No'}",
                f"  Source:   {result.data_source}",
            ]
            if result.sources:
                lines.append("  By source:")
                for src, score in result.sources.items():
                    lines.append(f"    {src}: {score:+.2f}")
            return "\n".join(lines)
        except Exception as e:
            return f"Sentiment unavailable for {ticker}: {e}"

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

    @mcp.tool()
    def augur_workflow(
        ticker: str,
        steps: str = "fetch,analyze,consensus",
        agents: str = "",
        question: str = "",
    ) -> str:
        """Run a multi-step agentic analysis workflow.

        Args:
            ticker: Stock ticker symbol (e.g. AAPL, NVDA)
            steps: Comma-separated steps: fetch, analyze, consensus, committee, debate, sentiment
            agents: Optional comma-separated agent IDs (empty = all personas)
            question: Optional question for committee step

        Returns:
            Structured workflow report with fetch data, consensus, committee verdict, sentiment
        """
        return _run_workflow_tool(ticker, steps=steps, agents=agents, question=question)

    return mcp


def run_server():
    """Run the MCP server in stdio mode."""
    mcp = create_server()
    mcp.run(transport="stdio")


# Alias for backward-compatibility with augur-mcp entry point
main = run_server


if __name__ == "__main__":
    run_server()
