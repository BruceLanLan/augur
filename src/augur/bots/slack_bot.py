# -*- coding: utf-8 -*-
"""
Augur Slack Bot - Multi-agent investment analysis bot for Slack

Usage:
    # Socket Mode (recommended for development)
    export SLACK_BOT_TOKEN=xoxb-...
    export SLACK_APP_TOKEN=xapp-...
    augur slack

    # HTTP Mode (production, behind a URL)
    export SLACK_BOT_TOKEN=xoxb-...
    export SLACK_SIGNING_SECRET=...
    augur slack --mode http --port 3000

Slash Commands:
    /augur-analyze TICKER [pe=X roe=X ...] - Run consensus analysis
    /augur TICKER [pe=X roe=X ...]         - Shortcut for /augur-analyze
    /augur-ask PERSONA_ID question         - Ask a specific investor
    /augur-personas                        - List all available personas
    /augur-help                            - Show help

App Mentions:
    @augur analyze AAPL pe=32 roe=0.55
    @augur @buffett analyze AAPL

Direct Messages:
    Natural language analysis requests

Environment Variables:
    SLACK_BOT_TOKEN      - Bot User OAuth Token (xoxb-...)
    SLACK_APP_TOKEN      - App-Level Token for Socket Mode (xapp-...)
    SLACK_SIGNING_SECRET - Signing secret (for HTTP mode)
"""

import os
import re
from typing import Optional, Dict, List, Any


# Signal emoji mapping (Slack style)
SIGNAL_EMOJI = {
    "bullish": ":chart_with_upwards_trend:",
    "neutral": ":white_circle:",
    "bearish": ":chart_with_downwards_trend:",
    "error": ":warning:",
}

SIGNAL_CN = {
    "bullish": "BULLISH",
    "neutral": "NEUTRAL",
    "bearish": "BEARISH",
    "error": "ERROR",
}

# Agent emoji mapping
AGENT_EMOJI = {
    "buffett": ":bank:",
    "graham": ":triangular_ruler:",
    "lynch": ":rocket:",
    "dalio": ":globe_with_meridians:",
    "munger": ":brain:",
    "soros": ":arrows_counterclockwise:",
    "marks": ":chart_with_downwards_trend:",
    "cathie_wood": ":bulb:",
    "fisher": ":mag:",
    "arps": ":trophy:",
    "aschenbrenner": ":robot_face:",
    "dayu": ":moneybag:",
    "thiel": ":office:",
    "duan_yongping": ":dart:",
    "zhang_lei": ":earth_asia:",
    "li_lu": ":mountain:",
    "dan_bin": ":tea:",
}

# Persona name mapping for @mention detection
PERSONA_MENTIONS = {
    "buffett": "buffett",
    "graham": "graham",
    "lynch": "lynch",
    "dalio": "dalio",
    "munger": "munger",
    "soros": "soros",
    "marks": "marks",
    "cathie_wood": "cathie_wood",
    "fisher": "fisher",
    "duan_yongping": "duan_yongping",
    "zhang_lei": "zhang_lei",
    "li_lu": "li_lu",
    "dan_bin": "dan_bin",
    "dayu": "dayu",
    "thiel": "thiel",
    "aschenbrenner": "aschenbrenner",
    "arps": "arps",
}


def _parse_metrics(text: str) -> Dict[str, float]:
    """Parse key=value metric pairs from text."""
    metrics = {}
    for match in re.finditer(r"(\w+)=([\d.]+)", text):
        key = match.group(1).strip().lower()
        try:
            metrics[key] = float(match.group(2))
        except ValueError:
            pass
    return metrics


def _extract_ticker(text: str) -> Optional[str]:
    """Extract ticker symbol from text, filtering out common stop words."""
    from augur.bots.utils import extract_ticker
    return extract_ticker(text)


def _build_market_context(ticker: str, metrics: Dict[str, float]):
    """Build MarketContext from ticker and parsed metrics."""
    from augur.personas.base import MarketContext

    field_map = {
        "pe": "pe",
        "pb": "pb",
        "ps": "ps",
        "roe": "roe",
        "roa": "roa",
        "gross_margins": "gross_margins",
        "gm": "gross_margins",
        "revenue_growth": "revenue_growth",
        "rg": "revenue_growth",
        "debt_ratio": "debt_ratio",
        "dr": "debt_ratio",
        "fcf": "fcf",
        "market_cap": "market_cap",
        "mc": "market_cap",
        "price": "price",
    }

    kwargs = {"ticker": ticker.upper()}
    for key, val in metrics.items():
        field_name = field_map.get(key, key)
        kwargs[field_name] = val

    return MarketContext(**kwargs)


def format_consensus_blocks(ticker: str, consensus, results: dict) -> List[Dict[str, Any]]:
    """Format consensus results as Slack Block Kit blocks."""
    signal_emoji = SIGNAL_EMOJI.get(consensus.signal.value, ":question:")
    signal_text = SIGNAL_CN.get(consensus.signal.value, consensus.signal.value.upper())

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"\U0001f989 Augur \u5171\u8bc6\u5206\u6790 \u2014 {ticker.upper()}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*\u4fe1\u53f7:* {signal_emoji} {signal_text}"},
                {"type": "mrkdwn", "text": f"*\u8bc4\u5206:* {consensus.score:.1f}/10"},
                {"type": "mrkdwn", "text": f"*\u7f6e\u4fe1\u5ea6:* {consensus.confidence:.0%}"},
            ],
        },
        {"type": "divider"},
    ]

    # Agent breakdown
    agent_lines = []
    for agent_id, result in results.items():
        if result.signal.value == "error":
            continue
        emoji = AGENT_EMOJI.get(agent_id, ":bust_in_silhouette:")
        signal_cn = SIGNAL_CN.get(result.signal.value, result.signal.value)
        name = result.agent_name[:12]
        agent_lines.append(f"{emoji} `{name:<12s}` | {signal_cn} | {result.score:.1f}/10")

    if agent_lines:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Agent \u660e\u7ec6:*\n" + "\n".join(agent_lines),
            },
        })

    # Key findings
    if consensus.key_findings:
        findings_text = "*\u5173\u952e\u53d1\u73b0:*\n"
        for finding in consensus.key_findings[:5]:
            findings_text += f"\u2022 {finding}\n"
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": findings_text},
        })

    # Risks
    if consensus.risks:
        risks_text = "*:warning: \u98ce\u9669:*\n"
        for risk in consensus.risks[:3]:
            risks_text += f"\u2022 {risk}\n"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": risks_text},
        })

    # Footer context
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"\U0001f989 Augur Multi-Agent Analysis | {len(results)} agents",
            }
        ],
    })

    return blocks


def format_single_agent_blocks(ticker: str, result) -> List[Dict[str, Any]]:
    """Format a single agent response as Slack Block Kit blocks."""
    signal_emoji = SIGNAL_EMOJI.get(result.signal.value, ":question:")
    signal_text = SIGNAL_CN.get(result.signal.value, result.signal.value.upper())
    emoji = AGENT_EMOJI.get(result.agent_id, ":bust_in_silhouette:")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{result.agent_name} \u5206\u6790 \u2014 {ticker.upper()}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*\u4fe1\u53f7:* {signal_emoji} {signal_text}"},
                {"type": "mrkdwn", "text": f"*\u8bc4\u5206:* {result.score:.1f}/10"},
                {"type": "mrkdwn", "text": f"*\u7f6e\u4fe1\u5ea6:* {result.confidence:.0%}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*\u63a8\u7406:*\n{result.reasoning[:800]}",
            },
        },
    ]

    if result.key_findings:
        findings_text = "*\u5173\u952e\u53d1\u73b0:*\n"
        for finding in result.key_findings[:5]:
            findings_text += f"\u2022 {finding}\n"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": findings_text},
        })

    if result.risks:
        risks_text = "*:warning: \u98ce\u9669:*\n"
        for risk in result.risks[:3]:
            risks_text += f"\u2022 {risk}\n"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": risks_text},
        })

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"{emoji} {result.agent_name} | \U0001f989 Augur",
            }
        ],
    })

    return blocks


def format_personas_blocks() -> List[Dict[str, Any]]:
    """Format personas list as Slack Block Kit blocks."""
    from augur.registry import AgentRegistry

    registry = AgentRegistry()
    agents = registry.get_all()

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"\U0001f989 Augur \u6295\u8d44\u5927\u5e08 ({len(agents)}\u4f4d)",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    persona_lines = []
    for agent in agents:
        emoji = AGENT_EMOJI.get(agent.agent_id, ":bust_in_silhouette:")
        philosophy = ", ".join(agent.philosophy[:2]) if agent.philosophy else ""
        persona_lines.append(f"{emoji} `{agent.agent_id}` - *{agent.name}*")
        if philosophy:
            persona_lines.append(f"    _{philosophy}_")

    # Split into chunks to avoid block text limits
    chunk_size = 12
    for i in range(0, len(persona_lines), chunk_size):
        chunk = persona_lines[i:i + chunk_size]
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(chunk)},
        })

    return blocks


def format_help_blocks() -> List[Dict[str, Any]]:
    """Format help message as Slack Block Kit blocks."""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "\U0001f989 Augur - \u591a\u667a\u80fd\u4f53\u6295\u8d44\u5206\u6790\u7cfb\u7edf",
                "emoji": True,
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Slash Commands:*\n"
                    "\u2022 `/augur-analyze TICKER [pe=X roe=X ...]` - 17\u4f4d\u5927\u5e08\u5171\u8bc6\u5206\u6790\n"
                    "\u2022 `/augur TICKER [pe=X roe=X ...]` - \u5feb\u6377\u5171\u8bc6\u5206\u6790\n"
                    "\u2022 `/augur-ask PERSONA question` - \u5411\u7279\u5b9a\u6295\u8d44\u5927\u5e08\u63d0\u95ee\n"
                    "\u2022 `/augur-personas` - \u5217\u51fa\u6240\u6709\u6295\u8d44\u5927\u5e08\n"
                    "\u2022 `/augur-help` - \u663e\u793a\u5e2e\u52a9\n"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*App Mentions:*\n"
                    "\u2022 `@augur analyze AAPL pe=32 roe=0.55`\n"
                    "\u2022 `@augur @buffett analyze AAPL`\n\n"
                    "*Direct Messages:*\n"
                    "\u2022 \u53d1\u9001\u5305\u542b\u80a1\u7968\u4ee3\u7801\u7684\u6d88\u606f\u5373\u53ef\u89e6\u53d1\u5206\u6790\n"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*\u6307\u6807\u53c2\u6570:*\n"
                    "`pe` / `pb` / `roe` / `gm`(\u6bdb\u5229\u7387) / `rg`(\u8425\u6536\u589e\u901f) / "
                    "`dr`(\u8d1f\u503a\u7387) / `fcf` / `price` / `market_cap`"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "\U0001f989 Augur | 18 Investor Persona Agents",
                }
            ],
        },
    ]


def format_consensus_text(ticker: str, consensus, results: dict) -> str:
    """Format consensus as plain text fallback for notifications."""
    signal_emoji = SIGNAL_EMOJI.get(consensus.signal.value, "")
    signal_text = SIGNAL_CN.get(consensus.signal.value, consensus.signal.value.upper())

    lines = [
        f"\U0001f989 Augur \u5171\u8bc6\u5206\u6790 - {ticker.upper()}",
        f"\u4fe1\u53f7: {signal_emoji} {signal_text}",
        f"\u8bc4\u5206: {consensus.score:.1f}/10",
        f"\u7f6e\u4fe1\u5ea6: {consensus.confidence:.0%}",
        "",
    ]

    for agent_id, result in results.items():
        if result.signal.value == "error":
            continue
        name = result.agent_name[:12]
        signal_cn = SIGNAL_CN.get(result.signal.value, result.signal.value)
        lines.append(f"  {name:<12s} | {signal_cn} | {result.score:.1f}/10")

    return "\n".join(lines)


def run_slack_bot(mode: str = "socket", port: int = 3000):
    """Start the Slack bot.

    Args:
        mode: 'socket' for Socket Mode (dev) or 'http' for HTTP mode (production)
        port: Port for HTTP mode (default: 3000)
    """
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        print("Error: SLACK_BOT_TOKEN environment variable is not set.")
        print("")
        print("To get a token:")
        print("  1. Go to https://api.slack.com/apps and create an app")
        print("  2. Under 'OAuth & Permissions', add scopes:")
        print("     chat:write, app_mentions:read, commands, im:read, im:write")
        print("  3. Install to workspace and copy Bot User OAuth Token")
        print("  4. Set it: export SLACK_BOT_TOKEN='xoxb-...'")
        print("")
        if mode == "socket":
            print("For Socket Mode, also set:")
            print("  export SLACK_APP_TOKEN='xapp-...'")
        else:
            print("For HTTP Mode, also set:")
            print("  export SLACK_SIGNING_SECRET='your-signing-secret'")
        print("")
        print("Then run: augur slack")
        raise SystemExit(1)

    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        print("Error: slack-bolt is not installed.")
        print("Install it with: pip install 'augur-agents[slack]'")
        print("  or: pip install slack-bolt>=1.18.0")
        raise SystemExit(1)

    # Initialize app based on mode
    if mode == "http":
        signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
        if not signing_secret:
            print("Error: SLACK_SIGNING_SECRET is required for HTTP mode.")
            print("Set it: export SLACK_SIGNING_SECRET='your-signing-secret'")
            raise SystemExit(1)
        app = App(token=bot_token, signing_secret=signing_secret)
    else:
        app_token = os.environ.get("SLACK_APP_TOKEN")
        if not app_token:
            print("Error: SLACK_APP_TOKEN is required for Socket Mode.")
            print("")
            print("To get an App-Level Token:")
            print("  1. Go to your app settings on api.slack.com")
            print("  2. Under 'Basic Information' > 'App-Level Tokens'")
            print("  3. Generate a token with 'connections:write' scope")
            print("  4. Set it: export SLACK_APP_TOKEN='xapp-...'")
            raise SystemExit(1)
        app = App(token=bot_token)

    # --- Slash command: /augur-analyze or /augur ---

    @app.command("/augur-analyze")
    @app.command("/augur")
    def handle_analyze_command(ack, command, respond):
        """Handle /augur-analyze TICKER [pe=X roe=X ...] command."""
        ack()

        text = command.get("text", "").strip()
        if not text:
            respond(
                text="Usage: `/augur-analyze TICKER [pe=X roe=X ...]`\n"
                "Example: `/augur-analyze AAPL pe=32 roe=0.55`"
            )
            return

        parts = text.split()
        ticker = parts[0].upper()
        metrics = _parse_metrics(text)

        respond(text=f":hourglass_flowing_sand: Analyzing {ticker} with 18 agents...")

        try:
            from augur.registry import AgentRegistry, DecisionCoordinator

            market_ctx = _build_market_context(ticker, metrics)
            registry = AgentRegistry()
            coordinator = DecisionCoordinator(registry)

            results = coordinator.analyze_with_all(market_ctx)
            consensus = coordinator.get_consensus(results, ticker=ticker, context=market_ctx)

            blocks = format_consensus_blocks(ticker, consensus, results)
            respond(blocks=blocks, text=f"Augur analysis for {ticker}")
        except Exception as e:
            respond(text=f":x: Analysis failed: {e}")

    # --- Slash command: /augur-ask ---

    @app.command("/augur-ask")
    def handle_ask_command(ack, command, respond):
        """Handle /augur-ask PERSONA_ID question command."""
        ack()

        text = command.get("text", "").strip()
        if not text or " " not in text:
            respond(
                text="Usage: `/augur-ask PERSONA_ID question`\n"
                "Example: `/augur-ask buffett analyze AAPL pe=32`\n"
                "Example: `/augur-ask duan_yongping NVDA worth buying?`"
            )
            return

        parts = text.split(None, 1)
        persona_id = parts[0].lower()
        question = parts[1] if len(parts) > 1 else ""

        ticker = _extract_ticker(question) or "UNKNOWN"
        metrics = _parse_metrics(question)

        from augur.registry import AgentRegistry

        registry = AgentRegistry()
        agent = registry.get(persona_id)

        if not agent:
            persona_id = PERSONA_MENTIONS.get(persona_id, persona_id)
            agent = registry.get(persona_id)

        if not agent:
            available = ", ".join(f"`{a.agent_id}`" for a in registry.get_all()[:10])
            respond(
                text=f":x: Persona not found: `{parts[0]}`\n\n"
                f"Available: {available} ...\n"
                f"Use `/augur-personas` to see all."
            )
            return

        respond(text=f":hourglass_flowing_sand: Asking {agent.name}...")

        try:
            market_ctx = _build_market_context(ticker, metrics)
            result = agent.analyze(market_ctx)
            blocks = format_single_agent_blocks(ticker, result)
            respond(blocks=blocks, text=f"{agent.name} analysis for {ticker}")
        except Exception as e:
            respond(text=f":x: Analysis failed: {e}")

    # --- Slash command: /augur-personas ---

    @app.command("/augur-personas")
    def handle_personas_command(ack, respond):
        """Handle /augur-personas command."""
        ack()
        blocks = format_personas_blocks()
        respond(blocks=blocks, text="Augur Personas")

    # --- Slash command: /augur-help ---

    @app.command("/augur-help")
    def handle_help_command(ack, respond):
        """Handle /augur-help command."""
        ack()
        blocks = format_help_blocks()
        respond(blocks=blocks, text="Augur Help")

    # --- App mention handler ---

    @app.event("app_mention")
    def handle_app_mention(event, say):
        """Handle @augur mentions in channels."""
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event.get("ts")

        # Remove the bot mention itself
        clean_text = re.sub(r"<@\w+>", "", text).strip()

        # Check for @persona mention within message
        persona_match = re.search(r"@(\w+)", clean_text)
        persona_id = None
        if persona_match:
            mention = persona_match.group(1).lower()
            persona_id = PERSONA_MENTIONS.get(mention)
            clean_text = re.sub(r"@\w+", "", clean_text).strip()

        ticker = _extract_ticker(clean_text)
        metrics = _parse_metrics(clean_text)

        if not ticker:
            say(
                blocks=format_help_blocks(),
                text="Augur Help",
                thread_ts=thread_ts,
            )
            return

        if persona_id:
            # Single agent analysis
            from augur.registry import AgentRegistry

            registry = AgentRegistry()
            agent = registry.get(persona_id)

            if not agent:
                say(
                    text=f":x: Persona not found: `{persona_match.group(1)}`",
                    thread_ts=thread_ts,
                )
                return

            say(
                text=f":hourglass_flowing_sand: Asking {agent.name} about {ticker}...",
                thread_ts=thread_ts,
            )

            try:
                market_ctx = _build_market_context(ticker, metrics)
                result = agent.analyze(market_ctx)
                blocks = format_single_agent_blocks(ticker, result)
                say(blocks=blocks, text=f"{agent.name} analysis", thread_ts=thread_ts)
            except Exception as e:
                say(text=f":x: Analysis failed: {e}", thread_ts=thread_ts)
        else:
            # Full consensus analysis
            say(
                text=f":hourglass_flowing_sand: Analyzing {ticker} with 18 agents...",
                thread_ts=thread_ts,
            )

            try:
                from augur.registry import AgentRegistry, DecisionCoordinator

                market_ctx = _build_market_context(ticker, metrics)
                registry = AgentRegistry()
                coordinator = DecisionCoordinator(registry)

                results = coordinator.analyze_with_all(market_ctx)
                consensus = coordinator.get_consensus(results, ticker=ticker, context=market_ctx)

                blocks = format_consensus_blocks(ticker, consensus, results)
                say(blocks=blocks, text=f"Augur analysis for {ticker}", thread_ts=thread_ts)
            except Exception as e:
                say(text=f":x: Analysis failed: {e}", thread_ts=thread_ts)

    # --- Direct message handler ---

    @app.event("message")
    def handle_dm(event, say):
        """Handle direct messages to the bot."""
        # Only handle DMs (channel type 'im')
        channel_type = event.get("channel_type", "")
        if channel_type != "im":
            return

        # Ignore bot messages
        if event.get("bot_id") or event.get("subtype"):
            return

        text = event.get("text", "").strip()
        if not text:
            return

        ticker = _extract_ticker(text)
        metrics = _parse_metrics(text)

        # Check for persona mention
        persona_match = re.search(r"@(\w+)", text)
        persona_id = None
        if persona_match:
            mention = persona_match.group(1).lower()
            persona_id = PERSONA_MENTIONS.get(mention)

        if not ticker:
            say(blocks=format_help_blocks(), text="Augur Help")
            return

        if persona_id:
            from augur.registry import AgentRegistry

            registry = AgentRegistry()
            agent = registry.get(persona_id)

            if agent:
                say(text=f":hourglass_flowing_sand: Asking {agent.name} about {ticker}...")
                try:
                    market_ctx = _build_market_context(ticker, metrics)
                    result = agent.analyze(market_ctx)
                    blocks = format_single_agent_blocks(ticker, result)
                    say(blocks=blocks, text=f"{agent.name} analysis")
                except Exception as e:
                    say(text=f":x: Analysis failed: {e}")
                return

        # Default: full consensus
        say(text=f":hourglass_flowing_sand: Analyzing {ticker} with 18 agents...")

        try:
            from augur.registry import AgentRegistry, DecisionCoordinator

            market_ctx = _build_market_context(ticker, metrics)
            registry = AgentRegistry()
            coordinator = DecisionCoordinator(registry)

            results = coordinator.analyze_with_all(market_ctx)
            consensus = coordinator.get_consensus(results, ticker=ticker, context=market_ctx)

            blocks = format_consensus_blocks(ticker, consensus, results)
            say(blocks=blocks, text=f"Augur analysis for {ticker}")
        except Exception as e:
            say(text=f":x: Analysis failed: {e}")

    # --- Start the app ---

    print(f"\U0001f989 Augur Slack Bot starting ({mode} mode)...")

    if mode == "socket":
        handler = SocketModeHandler(app, app_token)
        print("\U0001f989 Augur Slack Bot started! (Socket Mode)")
        print("The bot is now listening for commands and mentions.")
        handler.start()
    else:
        print(f"\U0001f989 Augur Slack Bot started! (HTTP Mode on port {port})")
        print("Make sure your Slack app's Request URL points to this server.")
        app.start(port=port)
