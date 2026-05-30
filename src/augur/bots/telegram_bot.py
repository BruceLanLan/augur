# -*- coding: utf-8 -*-
"""
augur.bots.telegram_bot - Telegram Bot for Augur multi-agent analysis

Commands:
  /analyze TICKER [pe=X roe=X ...] - Run full consensus analysis
  /ask PERSONA_ID question - Ask a specific investor persona
  /consensus TICKER - 18-agent consensus report
  /personas - List all available personas
  /help - Show help

Also responds to natural language messages with @persona mentions.

Environment variables:
  TELEGRAM_TOKEN - Bot token from BotFather
  AUGUR_DEFAULT_MODEL - Optional, override default model
"""

import os
import re
import asyncio
from typing import Optional, Dict

from augur.bots.utils import STOP_WORDS

# Signal emoji mapping
SIGNAL_EMOJI = {
    "bullish": "\U0001f7e2",   # green circle
    "neutral": "\U0001f7e1",   # yellow circle
    "bearish": "\U0001f534",   # red circle
    "error": "\u26a0\ufe0f",   # warning
}

SIGNAL_CN = {
    "bullish": "看多",
    "neutral": "中性",
    "bearish": "看空",
    "error": "错误",
}

# Agent emoji mapping
AGENT_EMOJI = {
    "buffett": "\U0001f3e6",
    "graham": "\U0001f4d0",
    "lynch": "\U0001f680",
    "dalio": "\U0001f310",
    "munger": "\U0001f9e0",
    "soros": "\U0001f504",
    "marks": "\U0001f4c9",
    "cathie_wood": "\U0001f4a1",
    "fisher": "\U0001f52c",
    "arps": "\U0001f947",
    "aschenbrenner": "\U0001f916",
    "dayu": "\u20bf",
    "thiel": "\U0001f3e2",
    "duan_yongping": "\U0001f3af",
    "zhang_lei": "\U0001f30f",
    "li_lu": "\U0001f3d4\ufe0f",
    "dan_bin": "\U0001fad6",
    "serenity": "\U0001f52d",  # telescope
}

# Persona name mapping for @mention detection
PERSONA_MENTIONS = {
    "巴菲特": "buffett",
    "buffett": "buffett",
    "格雷厄姆": "graham",
    "graham": "graham",
    "林奇": "lynch",
    "lynch": "lynch",
    "达利欧": "dalio",
    "dalio": "dalio",
    "芒格": "munger",
    "munger": "munger",
    "索罗斯": "soros",
    "soros": "soros",
    "马克斯": "marks",
    "marks": "marks",
    "伍德": "cathie_wood",
    "cathie_wood": "cathie_wood",
    "费雪": "fisher",
    "fisher": "fisher",
    "段永平": "duan_yongping",
    "duan_yongping": "duan_yongping",
    "张磊": "zhang_lei",
    "zhang_lei": "zhang_lei",
    "李录": "li_lu",
    "li_lu": "li_lu",
    "但斌": "dan_bin",
    "dan_bin": "dan_bin",
    "大宇": "dayu",
    "dayu": "dayu",
    "蒂尔": "thiel",
    "thiel": "thiel",
    "aschenbrenner": "aschenbrenner",
    "serenity": "serenity",
    "arps": "arps",
}


def _parse_metrics(args: list) -> Dict[str, float]:
    """Parse key=value metric pairs from command arguments."""
    metrics = {}
    for arg in args:
        if "=" in arg:
            key, val = arg.split("=", 1)
            try:
                metrics[key.strip().lower()] = float(val.strip())
            except ValueError:
                pass
    return metrics


def _extract_ticker(text: str) -> Optional[str]:
    """Extract ticker symbol from text, filtering out common stop words."""
    candidates = re.findall(r'\b([A-Z]{2,5})\b', text.upper())
    for candidate in candidates:
        if candidate not in STOP_WORDS:
            return candidate
    return None


def _build_market_context(ticker: str, metrics: Dict[str, float]):
    """Build MarketContext from ticker and parsed metrics.

    If no metrics provided, auto-fetches from yfinance.
    """
    from augur.personas.base import MarketContext

    # Auto-fetch when no metrics given
    if not metrics:
        try:
            from augur.data import fetch_market_context
            return fetch_market_context(ticker)
        except Exception:
            pass  # fallback to empty context

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
        "sector": "sector",
        "industry": "industry",
    }

    kwargs = {"ticker": ticker.upper()}
    for key, val in metrics.items():
        field_name = field_map.get(key, key)
        kwargs[field_name] = val

    return MarketContext(**kwargs)


def format_consensus_message(ticker: str, consensus, results: dict) -> str:
    """Format consensus results as a Telegram message with emoji."""
    signal_emoji = SIGNAL_EMOJI.get(consensus.signal.value, "")
    signal_cn = SIGNAL_CN.get(consensus.signal.value, consensus.signal.value)

    lines = [
        f"\U0001f989 Augur \u5171\u8bc6\u5206\u6790 \u2014 {ticker.upper()}",
        "",
        f"\U0001f4ca \u4fe1\u53f7: {signal_emoji} {signal_cn.upper()}",
        f"\u2b50 \u8bc4\u5206: {consensus.score:.1f}/10",
        f"\U0001f3af \u7f6e\u4fe1\u5ea6: {consensus.confidence:.0%}",
        "",
        "\u2501\u2501\u2501 Agent \u660e\u7ec6 \u2501\u2501\u2501",
    ]

    for agent_id, result in results.items():
        if result.signal.value == "error":
            continue
        emoji = AGENT_EMOJI.get(agent_id, "\U0001f464")
        signal_cn_agent = SIGNAL_CN.get(result.signal.value, result.signal.value)
        name = result.agent_name[:12]
        lines.append(
            f"{emoji} {name:<12s} | {signal_cn_agent} | {result.score:.1f}/10"
        )

    if consensus.key_findings:
        lines.append("")
        lines.append("\U0001f4cb \u5173\u952e\u53d1\u73b0:")
        for finding in consensus.key_findings[:5]:
            lines.append(f"\u2022 {finding}")

    if consensus.risks:
        lines.append("")
        lines.append("\u26a0\ufe0f \u98ce\u9669:")
        for risk in consensus.risks[:3]:
            lines.append(f"\u2022 {risk}")

    return "\n".join(lines)


def format_single_agent_message(ticker: str, result) -> str:
    """Format a single agent response as a Telegram message."""
    signal_emoji = SIGNAL_EMOJI.get(result.signal.value, "")
    signal_cn = SIGNAL_CN.get(result.signal.value, result.signal.value)
    emoji = AGENT_EMOJI.get(result.agent_id, "\U0001f464")

    lines = [
        f"{emoji} {result.agent_name} \u5206\u6790 \u2014 {ticker.upper()}",
        "",
        f"\U0001f4ca \u4fe1\u53f7: {signal_emoji} {signal_cn.upper()}",
        f"\u2b50 \u8bc4\u5206: {result.score:.1f}/10",
        f"\U0001f3af \u7f6e\u4fe1\u5ea6: {result.confidence:.0%}",
        "",
        f"\U0001f4dd \u63a8\u7406:",
        result.reasoning[:500],
    ]

    if result.key_findings:
        lines.append("")
        lines.append("\U0001f4cb \u5173\u952e\u53d1\u73b0:")
        for finding in result.key_findings[:5]:
            lines.append(f"\u2022 {finding}")

    if result.risks:
        lines.append("")
        lines.append("\u26a0\ufe0f \u98ce\u9669:")
        for risk in result.risks[:3]:
            lines.append(f"\u2022 {risk}")

    return "\n".join(lines)


def run_telegram_bot(token: Optional[str] = None):
    """Start the Telegram bot.

    Args:
        token: Telegram bot token. If not provided, reads from TELEGRAM_TOKEN env var.
    """
    token = token or os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("Error: TELEGRAM_TOKEN environment variable is not set.")
        print("")
        print("To get a token:")
        print("  1. Open Telegram and search for @BotFather")
        print("  2. Send /newbot and follow the instructions")
        print("  3. Copy the token and set it:")
        print("     export TELEGRAM_TOKEN='your-token-here'")
        print("")
        print("Then run: augur telegram")
        raise SystemExit(1)

    try:
        from telegram import Update
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            filters,
            ContextTypes,
        )
    except ImportError:
        print("Error: python-telegram-bot is not installed.")
        print("Install it with: pip install 'augur-agents[telegram]'")
        print("  or: pip install python-telegram-bot>=20.0")
        raise SystemExit(1)

    # --- Handler functions ---

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "\U0001f989 *Augur - \u591a\u667a\u80fd\u4f53\u6295\u8d44\u5206\u6790\u7cfb\u7edf*\n\n"
            "\U0001f4cb *\u53ef\u7528\u547d\u4ee4:*\n"
            "`/analyze TICKER [pe=X roe=X ...]` - \u5171\u8bc6\u5206\u6790\n"
            "`/consensus TICKER` - 18-Agent \u5171\u8bc6\u62a5\u544a\n"
            "`/ask PERSONA question` - \u5411\u7279\u5b9a\u6295\u8d44\u5927\u5e08\u63d0\u95ee\n"
            "`/personas` - \u5217\u51fa\u6240\u6709\u6295\u8d44\u5927\u5e08\n"
            "`/help` - \u663e\u793a\u5e2e\u52a9\n\n"
            "\U0001f4ac *\u81ea\u7136\u8bed\u8a00:*\n"
            "\u76f4\u63a5\u53d1\u9001\u5305\u542b @\u4eba\u540d \u7684\u6d88\u606f\uff0c\u4f8b\u5982:\n"
            "`@\u5df4\u83f2\u7279 \u5206\u6790AAPL`\n"
            "`@\u6bb5\u6c38\u5e73 NVDA\u503c\u5f97\u4e70\u5417\uff1f`\n\n"
            "\U0001f4ca *\u6307\u6807\u53c2\u6570:*\n"
            "`pe` / `pb` / `roe` / `gm`(\u6bdb\u5229\u7387) / `rg`(\u8425\u6536\u589e\u901f) / "
            "`dr`(\u8d1f\u503a\u7387) / `fcf` / `price`"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def personas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /personas command."""
        from augur.registry import AgentRegistry

        registry = AgentRegistry()
        agents = registry.get_all()

        lines = [f"\U0001f989 *\u53ef\u7528\u6295\u8d44\u5927\u5e08 ({len(agents)}\u4f4d)*\n"]
        for agent in agents:
            emoji = AGENT_EMOJI.get(agent.agent_id, "\U0001f464")
            philosophy = ", ".join(agent.philosophy[:2]) if agent.philosophy else ""
            lines.append(f"{emoji} `{agent.agent_id}` - {agent.name}")
            if philosophy:
                lines.append(f"   _{philosophy}_")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze TICKER [pe=X roe=X ...] command."""
        if not context.args:
            await update.message.reply_text(
                "\u7528\u6cd5: `/analyze TICKER [pe=X roe=X ...]`\n"
                "\u4f8b: `/analyze AAPL pe=32 roe=0.55`",
                parse_mode="Markdown",
            )
            return

        ticker = context.args[0].upper()
        metrics = _parse_metrics(context.args[1:])

        await update.message.reply_text(
            f"\U0001f504 \u6b63\u5728\u5206\u6790 {ticker}\uff0c\u8bf717\u4f4d\u5927\u5e08\u5206\u6790\u4e2d..."
        )

        try:
            from augur.registry import AgentRegistry, DecisionCoordinator

            market_ctx = _build_market_context(ticker, metrics)
            registry = AgentRegistry()
            coordinator = DecisionCoordinator(registry)

            results = coordinator.analyze_with_all(market_ctx)
            consensus = coordinator.get_consensus(results, ticker=ticker, context=market_ctx)

            message = format_consensus_message(ticker, consensus, results)
            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(f"\u274c \u5206\u6790\u5931\u8d25: {e}")

    async def consensus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /consensus TICKER command (alias for /analyze)."""
        await analyze_command(update, context)

    async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ask PERSONA_ID question command."""
        if len(context.args) < 2:
            await update.message.reply_text(
                "\u7528\u6cd5: `/ask PERSONA_ID \u95ee\u9898`\n"
                "\u4f8b: `/ask buffett \u5206\u6790AAPL`\n"
                "\u4f8b: `/ask duan_yongping NVDA\u503c\u5f97\u4e70\u5417`",
                parse_mode="Markdown",
            )
            return

        persona_id = context.args[0].lower()
        question = " ".join(context.args[1:])

        # Try to extract ticker from question
        ticker = _extract_ticker(question) or "UNKNOWN"

        # Parse any metrics from question
        metrics = _parse_metrics(context.args[1:])

        from augur.registry import AgentRegistry

        registry = AgentRegistry()
        agent = registry.get(persona_id)

        if not agent:
            # Check PERSONA_MENTIONS mapping
            persona_id = PERSONA_MENTIONS.get(persona_id, persona_id)
            agent = registry.get(persona_id)

        if not agent:
            available = ", ".join(f"`{a.agent_id}`" for a in registry.get_all()[:10])
            await update.message.reply_text(
                f"\u274c \u672a\u627e\u5230\u6295\u8d44\u4eba: `{context.args[0]}`\n\n"
                f"\u53ef\u7528: {available} ...\n"
                f"\u8f93\u5165 /personas \u67e5\u770b\u5168\u90e8",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            f"\U0001f504 \u6b63\u5728\u8be2\u95ee {agent.name}..."
        )

        try:
            market_ctx = _build_market_context(ticker, metrics)
            result = agent.analyze(market_ctx)
            message = format_single_agent_message(ticker, result)
            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(f"\u274c \u5206\u6790\u5931\u8d25: {e}")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages with @persona mentions."""
        text = update.message.text or ""

        # Detect @persona mention pattern
        mention_match = re.search(r"@(\S+)", text)
        if not mention_match:
            return

        mention = mention_match.group(1).lower()
        persona_id = PERSONA_MENTIONS.get(mention)

        if not persona_id:
            return

        # Extract the rest as question
        question = re.sub(r"@\S+", "", text).strip()
        ticker = _extract_ticker(question) or "UNKNOWN"

        metrics = _parse_metrics(question.split())

        try:
            from augur.registry import AgentRegistry

            registry = AgentRegistry()
            agent = registry.get(persona_id)

            if not agent:
                return

            await update.message.reply_text(
                f"\U0001f504 \u6b63\u5728\u8be2\u95ee {agent.name}..."
            )

            market_ctx = _build_market_context(ticker, metrics)
            result = agent.analyze(market_ctx)
            message = format_single_agent_message(ticker, result)
            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(f"\u274c \u5206\u6790\u5931\u8d25: {e}")

    # --- Build application ---
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("personas", personas_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("consensus", consensus_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("\U0001f989 Augur Telegram Bot started!")
    print("Send /help to the bot to see available commands.")
    app.run_polling()
