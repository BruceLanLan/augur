# -*- coding: utf-8 -*-
"""
Augur Lark/Feishu Bot - Event Subscription + Webhook

Usage:
    # Event mode (receive + send)
    export LARK_APP_ID=your_app_id
    export LARK_APP_SECRET=your_app_secret
    export LARK_VERIFICATION_TOKEN=your_token
    export LARK_ENCRYPT_KEY=your_key
    augur lark --mode event --port 9000

    # Webhook mode (send only)
    export LARK_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
    augur lark --mode webhook

Environment Variables:
    LARK_APP_ID              - App ID
    LARK_APP_SECRET          - App Secret
    LARK_VERIFICATION_TOKEN  - Verification Token
    LARK_ENCRYPT_KEY         - Encrypt Key
    LARK_WEBHOOK_URL         - Webhook URL
"""

import os
import re
import json
import hashlib
import time
import threading
from typing import Optional, Dict, Any, List

from augur.bots.utils import STOP_WORDS


# Signal emoji mapping
SIGNAL_EMOJI = {
    "bullish": "\U0001f7e2",
    "neutral": "\U0001f7e1",
    "bearish": "\U0001f534",
    "error": "\u26a0\ufe0f",
}

SIGNAL_CN = {
    "bullish": "\u770b\u591a",
    "neutral": "\u4e2d\u6027",
    "bearish": "\u770b\u7a7a",
    "error": "\u9519\u8bef",
}

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
}

# \u4eba\u540d\u6620\u5c04 (\u4e2d\u6587+\u82f1\u6587)
PERSONA_MENTIONS = {
    "\u5df4\u83f2\u7279": "buffett",
    "buffett": "buffett",
    "\u683c\u96f7\u5384\u59c6": "graham",
    "graham": "graham",
    "\u6797\u5947": "lynch",
    "lynch": "lynch",
    "\u8fbe\u5229\u6b27": "dalio",
    "dalio": "dalio",
    "\u8292\u683c": "munger",
    "munger": "munger",
    "\u7d22\u7f57\u65af": "soros",
    "soros": "soros",
    "\u9a6c\u514b\u65af": "marks",
    "marks": "marks",
    "\u4f0d\u5fb7": "cathie_wood",
    "cathie_wood": "cathie_wood",
    "\u8d39\u96ea": "fisher",
    "fisher": "fisher",
    "\u6bb5\u6c38\u5e73": "duan_yongping",
    "duan_yongping": "duan_yongping",
    "\u5f20\u78ca": "zhang_lei",
    "zhang_lei": "zhang_lei",
    "\u674e\u5f55": "li_lu",
    "li_lu": "li_lu",
    "\u4f46\u658c": "dan_bin",
    "dan_bin": "dan_bin",
    "\u5927\u5b87": "dayu",
    "dayu": "dayu",
    "\u8482\u5c14": "thiel",
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
        "pe": "pe", "pb": "pb", "ps": "ps",
        "roe": "roe", "roa": "roa",
        "gross_margins": "gross_margins", "gm": "gross_margins",
        "revenue_growth": "revenue_growth", "rg": "revenue_growth",
        "debt_ratio": "debt_ratio", "dr": "debt_ratio",
        "fcf": "fcf", "market_cap": "market_cap",
        "mc": "market_cap", "price": "price",
    }

    kwargs = {"ticker": ticker.upper()}
    for key, val in metrics.items():
        field_name = field_map.get(key, key)
        kwargs[field_name] = val

    return MarketContext(**kwargs)


def format_lark_card(ticker: str, consensus, results: dict) -> Dict[str, Any]:
    """Format as Lark Interactive Card.

    Lark cards support: header, divider, columns, fields, buttons.
    """
    signal_emoji = SIGNAL_EMOJI.get(consensus.signal.value, "")
    signal_cn = SIGNAL_CN.get(consensus.signal.value, consensus.signal.value)

    # Header template color based on signal
    template = "green" if consensus.signal.value == "bullish" else (
        "red" if consensus.signal.value == "bearish" else "yellow"
    )

    # Build agent detail text
    agent_lines = []
    for agent_id, result in results.items():
        if result.signal.value == "error":
            continue
        emoji = AGENT_EMOJI.get(agent_id, "\U0001f464")
        scn = SIGNAL_CN.get(result.signal.value, result.signal.value)
        name = result.agent_name[:8]
        agent_lines.append(f"{emoji} {name} | {scn} | {result.score:.1f}/10")

    agent_text = "\n".join(agent_lines) if agent_lines else "\u65e0\u6570\u636e"

    elements: List[Dict[str, Any]] = [
        {
            "tag": "div",
            "fields": [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**\u4fe1\u53f7:** {signal_emoji} {signal_cn}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**\u8bc4\u5206:** {consensus.score:.1f}/10"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**\u7f6e\u4fe1\u5ea6:** {consensus.confidence:.0%}"}},
            ],
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**Agent \u660e\u7ec6:**\n{agent_text}"},
        },
    ]

    # Key findings
    if consensus.key_findings:
        findings = "\n".join(f"\u2022 {f}" for f in consensus.key_findings[:4])
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**\u5173\u952e\u53d1\u73b0:**\n{findings}"},
        })

    # Risks
    if consensus.risks:
        risks = "\n".join(f"\u2022 {r}" for r in consensus.risks[:3])
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**\u26a0\ufe0f \u98ce\u9669:**\n{risks}"},
        })

    # Footer
    elements.append({
        "tag": "note",
        "elements": [
            {"tag": "plain_text", "content": f"\U0001f989 Augur Multi-Agent | {len(results)} agents"},
        ],
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"\U0001f989 Augur \u5171\u8bc6\u5206\u6790 - {ticker.upper()}"},
            "template": template,
        },
        "elements": elements,
    }

    return card


def format_lark_rich_text(ticker: str, consensus, results: dict) -> Dict[str, Any]:
    """Format as Lark rich text (post) message for webhook."""
    signal_emoji = SIGNAL_EMOJI.get(consensus.signal.value, "")
    signal_cn = SIGNAL_CN.get(consensus.signal.value, consensus.signal.value)

    content: List[List[Dict[str, Any]]] = [
        [{"tag": "text", "text": f"\u4fe1\u53f7: {signal_emoji} {signal_cn}  |  \u8bc4\u5206: {consensus.score:.1f}/10  |  \u7f6e\u4fe1\u5ea6: {consensus.confidence:.0%}"}],
        [{"tag": "text", "text": ""}],
    ]

    for agent_id, result in results.items():
        if result.signal.value == "error":
            continue
        emoji = AGENT_EMOJI.get(agent_id, "\U0001f464")
        scn = SIGNAL_CN.get(result.signal.value, result.signal.value)
        name = result.agent_name[:10]
        content.append([{"tag": "text", "text": f"{emoji} {name} | {scn} | {result.score:.1f}/10"}])

    if consensus.key_findings:
        content.append([{"tag": "text", "text": ""}])
        content.append([{"tag": "text", "text": "\u5173\u952e\u53d1\u73b0:"}])
        for f in consensus.key_findings[:3]:
            content.append([{"tag": "text", "text": f"\u2022 {f}"}])

    return {
        "zh_cn": {
            "title": f"\U0001f989 Augur \u5171\u8bc6\u5206\u6790 - {ticker.upper()}",
            "content": content,
        }
    }


class LarkEventBot:
    """\u98de\u4e66\u4e8b\u4ef6\u8ba2\u9605 Bot - \u63a5\u6536\u6d88\u606f + \u4e3b\u52a8\u63a8\u9001"""

    def __init__(self, app_id: str, app_secret: str,
                 verification_token: str, encrypt_key: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self._tenant_access_token = None
        self._token_expires = 0
        self._token_lock = threading.Lock()

    def _get_tenant_access_token(self) -> str:
        """Get or refresh tenant access token (thread-safe)."""
        import urllib.request

        with self._token_lock:
            if self._tenant_access_token and time.time() < self._token_expires:
                return self._tenant_access_token

            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            payload = json.dumps({
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            }).encode("utf-8")

            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            self._tenant_access_token = data.get("tenant_access_token", "")
            self._token_expires = time.time() + data.get("expire", 7200) - 300
            return self._tenant_access_token

    def verify_event(self, body: dict) -> Optional[Dict[str, Any]]:
        """Verify event callback and handle challenge."""
        if "challenge" in body:
            token = body.get("token", "")
            if token == self.verification_token:
                return {"challenge": body["challenge"]}
            return None
        return None

    def handle_message(self, event: dict) -> Optional[str]:
        """Handle incoming message event."""
        event_body = event.get("event", {})
        message = event_body.get("message", {})
        msg_type = message.get("message_type", "")

        if msg_type != "text":
            return None

        content_str = message.get("content", "{}")
        try:
            content_data = json.loads(content_str)
        except json.JSONDecodeError:
            return None

        text = content_data.get("text", "").strip()
        if not text:
            return None

        # Remove @bot mention
        text = re.sub(r"@_user_\d+", "", text).strip()

        # Help
        if text in ("\u5e2e\u52a9", "help", "?", "\uff1f"):
            return self._help_text()

        # Personas
        if text in ("\u6295\u8d44\u4eba\u5217\u8868", "personas", "\u5217\u8868"):
            return self._personas_text()

        # Analyze
        analyze_match = re.match(r"(?:\u5206\u6790|analyze)\s+(\S+)(.*)", text, re.IGNORECASE)
        if analyze_match:
            ticker = analyze_match.group(1).upper()
            extra = analyze_match.group(2)
            metrics = _parse_metrics(extra)
            return self._run_consensus(ticker, metrics)

        # Ask persona
        ask_match = re.match(r"(?:@|\u95ee\s*)(\S+)\s+(\S+)(.*)", text)
        if ask_match:
            persona_name = ask_match.group(1)
            ticker_or_q = ask_match.group(2)
            extra = ask_match.group(3)
            persona_id = PERSONA_MENTIONS.get(persona_name)
            if persona_id:
                ticker = _extract_ticker(ticker_or_q + " " + extra) or ticker_or_q.upper()
                metrics = _parse_metrics(extra)
                return self._run_single_agent(persona_id, ticker, metrics)

        return None

    def send_card(self, chat_id: str, card_content: Dict[str, Any]):
        """Send interactive card message to chat."""
        import urllib.request

        token = self._get_tenant_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"

        payload = json.dumps({
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content),
        }).encode("utf-8")

        req = urllib.request.Request(
            url + "?receive_id_type=chat_id",
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != 0:
                    print(f"Lark send error: {data.get('msg', 'unknown')}")
        except Exception as e:
            print(f"Failed to send Lark card: {e}")

    def send_text(self, chat_id: str, text: str):
        """Send plain text message to chat."""
        import urllib.request

        token = self._get_tenant_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"

        payload = json.dumps({
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }).encode("utf-8")

        req = urllib.request.Request(
            url + "?receive_id_type=chat_id",
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != 0:
                    print(f"Lark send error: {data.get('msg', 'unknown')}")
        except Exception as e:
            print(f"Failed to send Lark text: {e}")

    def _run_consensus(self, ticker: str, metrics: Dict[str, float]) -> str:
        """Run consensus analysis."""
        try:
            from augur.registry import AgentRegistry, DecisionCoordinator

            market_ctx = _build_market_context(ticker, metrics)
            registry = AgentRegistry()
            coordinator = DecisionCoordinator(registry)

            results = coordinator.analyze_with_all(market_ctx)
            consensus = coordinator.get_consensus(results, ticker=ticker, context=market_ctx)

            signal_cn = SIGNAL_CN.get(consensus.signal.value, consensus.signal.value)
            lines = [
                f"\U0001f989 Augur \u5171\u8bc6 - {ticker}",
                f"\u4fe1\u53f7: {signal_cn} | \u8bc4\u5206: {consensus.score:.1f}/10 | \u7f6e\u4fe1\u5ea6: {consensus.confidence:.0%}",
                "",
            ]
            for aid, r in results.items():
                if r.signal.value == "error":
                    continue
                scn = SIGNAL_CN.get(r.signal.value, r.signal.value)
                lines.append(f"  {r.agent_name[:10]} | {scn} | {r.score:.1f}")

            return "\n".join(lines)
        except Exception as e:
            return f"\u274c \u5206\u6790\u5931\u8d25: {e}"

    def _run_single_agent(self, persona_id: str, ticker: str,
                          metrics: Dict[str, float]) -> str:
        """Run single agent analysis."""
        try:
            from augur.registry import AgentRegistry

            registry = AgentRegistry()
            agent = registry.get(persona_id)
            if not agent:
                return f"\u274c \u672a\u627e\u5230\u6295\u8d44\u4eba: {persona_id}"

            market_ctx = _build_market_context(ticker, metrics)
            result = agent.analyze(market_ctx)

            signal_cn = SIGNAL_CN.get(result.signal.value, result.signal.value)
            lines = [
                f"{result.agent_name} \u5206\u6790 - {ticker}",
                f"\u4fe1\u53f7: {signal_cn} | \u8bc4\u5206: {result.score:.1f}/10",
                "",
                result.reasoning[:300],
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"\u274c \u5206\u6790\u5931\u8d25: {e}"

    def _help_text(self) -> str:
        return (
            "\U0001f989 Augur - \u591a\u667a\u80fd\u4f53\u6295\u8d44\u5206\u6790\n\n"
            "\u53ef\u7528\u547d\u4ee4:\n"
            "\u2022 \u5206\u6790 TICKER - 17\u4f4d\u5927\u5e08\u5171\u8bc6\u5206\u6790\n"
            "\u2022 @\u5df4\u83f2\u7279 TICKER - \u5411\u7279\u5b9a\u5927\u5e08\u63d0\u95ee\n"
            "\u2022 \u95ee buffett TICKER - \u540c\u4e0a\n"
            "\u2022 \u6295\u8d44\u4eba\u5217\u8868 - \u5217\u51fa\u6240\u6709\u5927\u5e08\n"
            "\u2022 \u5e2e\u52a9 - \u663e\u793a\u672c\u5e2e\u52a9\n\n"
            "\u793a\u4f8b: \u5206\u6790 AAPL pe=32 roe=0.55"
        )

    def _personas_text(self) -> str:
        try:
            from augur.registry import AgentRegistry

            registry = AgentRegistry()
            agents = registry.get_all()

            lines = [f"\U0001f989 \u53ef\u7528\u6295\u8d44\u5927\u5e08 ({len(agents)}\u4f4d)\n"]
            for agent in agents:
                emoji = AGENT_EMOJI.get(agent.agent_id, "\U0001f464")
                lines.append(f"{emoji} {agent.agent_id} - {agent.name}")
            return "\n".join(lines)
        except Exception as e:
            return f"\u274c \u83b7\u53d6\u5217\u8868\u5931\u8d25: {e}"


class LarkWebhookBot:
    """\u98de\u4e66\u7fa4\u673a\u5668\u4eba Webhook - \u4ec5\u63a8\u9001"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_rich_text(self, content: Dict[str, Any]):
        """Send rich text (post) message."""
        import urllib.request

        payload = json.dumps({
            "msg_type": "post",
            "content": {"post": content},
        }).encode("utf-8")

        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != 0:
                    print(f"Lark webhook error: {data.get('msg', 'unknown')}")
        except Exception as e:
            print(f"Failed to send Lark webhook: {e}")

    def send_card(self, card_content: Dict[str, Any]):
        """Send interactive card via webhook."""
        import urllib.request

        payload = json.dumps({
            "msg_type": "interactive",
            "card": card_content,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != 0:
                    print(f"Lark webhook error: {data.get('msg', 'unknown')}")
        except Exception as e:
            print(f"Failed to send Lark card: {e}")

    def send_text(self, text: str):
        """Send plain text message via webhook."""
        import urllib.request

        payload = json.dumps({
            "msg_type": "text",
            "content": {"text": text},
        }).encode("utf-8")

        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != 0:
                    print(f"Lark webhook error: {data.get('msg', 'unknown')}")
        except Exception as e:
            print(f"Failed to send Lark text: {e}")

    def send_consensus(self, ticker: str, consensus, agent_results: dict):
        """Format and send consensus report via webhook card."""
        card = format_lark_card(ticker, consensus, agent_results)
        self.send_card(card)


def run_event_server(port_num: int = 9000):
    """Start Lark event subscription server."""
    app_id = os.environ.get("LARK_APP_ID")
    app_secret = os.environ.get("LARK_APP_SECRET")
    verification_token = os.environ.get("LARK_VERIFICATION_TOKEN")
    encrypt_key = os.environ.get("LARK_ENCRYPT_KEY", "")

    if not all([app_id, app_secret, verification_token]):
        print("Error: Lark environment variables not set.")
        print("")
        print("Required:")
        print("  export LARK_APP_ID='your_app_id'")
        print("  export LARK_APP_SECRET='your_app_secret'")
        print("  export LARK_VERIFICATION_TOKEN='your_token'")
        print("  export LARK_ENCRYPT_KEY='your_key'  (optional)")
        print("")
        print("See: https://open.feishu.cn/document/")
        raise SystemExit(1)

    bot = LarkEventBot(app_id, app_secret, verification_token, encrypt_key)

    from http.server import HTTPServer, BaseHTTPRequestHandler

    class LarkHandler(BaseHTTPRequestHandler):
        """HTTP handler for Lark event callbacks."""

        def do_POST(self):
            """Handle incoming Lark events."""
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return

            # URL verification challenge
            challenge_resp = bot.verify_event(data)
            if challenge_resp:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(challenge_resp).encode("utf-8"))
                return

            # Handle message event
            event_type = data.get("header", {}).get("event_type", "")
            if event_type == "im.message.receive_v1":
                reply_text = bot.handle_message(data)
                if reply_text:
                    chat_id = data.get("event", {}).get("message", {}).get("chat_id", "")
                    if chat_id:
                        bot.send_text(chat_id, reply_text)

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format, *args):
            pass

    print(f"\U0001f989 Augur Lark Bot starting on port {port_num}...")
    print(f"   App ID: {app_id[:8]}...")
    print("")
    print("Configure in Lark Developer Console:")
    print("  Subscribe to: im.message.receive_v1")
    print("")
    print("Press Ctrl+C to stop.")

    server = HTTPServer(("0.0.0.0", port_num), LarkHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nLark Bot stopped.")
        server.shutdown()


def run_webhook_mode():
    """Run in webhook-only mode (for cron push)."""
    webhook_url = os.environ.get("LARK_WEBHOOK_URL")
    if not webhook_url:
        print("Error: LARK_WEBHOOK_URL environment variable is not set.")
        print("")
        print("To get a webhook URL:")
        print("  1. Open Lark/Feishu group chat")
        print("  2. Click settings > Bots > Add Bot > Custom Bot")
        print("  3. Copy the Webhook URL")
        print("  4. Set: export LARK_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'")
        raise SystemExit(1)

    bot = LarkWebhookBot(webhook_url)

    from augur.cron import run_watchlist_analysis

    print("\U0001f989 Augur Lark Webhook mode - running watchlist analysis...")
    results = run_watchlist_analysis()

    if not results:
        print("No results. Watchlist is empty.")
        return

    for analysis in results:
        ticker = analysis["ticker"]
        consensus = analysis["consensus"]
        agent_results = analysis["results"]

        bot.send_consensus(ticker, consensus, agent_results)
        print(f"  Sent: {ticker} ({consensus.signal.value})")

    print(f"\nDone. Sent {len(results)} reports to Lark group.")


def run_lark_bot(mode: str = "event", port_num: int = 9000):
    """Start the Lark/Feishu bot.

    Args:
        mode: 'event' for event subscription or 'webhook' for webhook-only
        port_num: Server listening number (default: 9000)
    """
    if mode == "webhook":
        run_webhook_mode()
    else:
        run_event_server(port_num=port_num)
