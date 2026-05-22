# -*- coding: utf-8 -*-
"""
Augur 微信 Bot - 企业微信 + Webhook 双模式

Usage:
    # 企业微信模式 (接收+发送)
    export WECHAT_CORP_ID=your_corp_id
    export WECHAT_CORP_SECRET=your_corp_secret
    export WECHAT_AGENT_ID=your_agent_id
    export WECHAT_TOKEN=your_token
    export WECHAT_AES_KEY=your_aes_key
    augur wechat --mode wecom --port 8080

    # Webhook 模式 (仅发送, 配合 Cron)
    export WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
    augur wechat --mode webhook

Commands (in chat):
    分析 TICKER 或 analyze TICKER - 17位大师共识分析
    @巴菲特 TICKER 或 问 buffett TICKER - 向特定大师提问
    投资人列表 或 personas - 列出所有投资大师
    帮助 或 help - 显示帮助

Environment Variables:
    WECHAT_CORP_ID       - 企业ID
    WECHAT_CORP_SECRET   - 应用Secret
    WECHAT_AGENT_ID      - 应用AgentId
    WECHAT_TOKEN         - 回调Token
    WECHAT_AES_KEY       - 回调EncodingAESKey
    WECHAT_WEBHOOK_URL   - 群机器人Webhook地址
"""

import os
import re
import json
from typing import Optional, Dict, Any

# Signal emoji mapping (WeCom markdown支持)
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
}

# 人名映射 (中文+英文)
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
    """Extract ticker symbol from text."""
    match = re.search(r"\b([A-Z]{1,5})\b", text.upper())
    return match.group(1) if match else None


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


def format_wechat_message(ticker: str, consensus, results: dict) -> str:
    """Format analysis results for WeChat markdown.

    企业微信 markdown 支持: **bold**, `code`, > quote, [link](url)
    保持紧凑布局以适配手机屏幕宽度
    """
    signal_emoji = SIGNAL_EMOJI.get(consensus.signal.value, "")
    signal_cn = SIGNAL_CN.get(consensus.signal.value, consensus.signal.value)

    lines = [
        f"**\U0001f989 Augur \u5171\u8bc6\u5206\u6790 - {ticker.upper()}**",
        "",
        f"> \u4fe1\u53f7: {signal_emoji} **{signal_cn.upper()}**",
        f"> \u8bc4\u5206: **{consensus.score:.1f}/10**",
        f"> \u7f6e\u4fe1\u5ea6: **{consensus.confidence:.0%}**",
        "",
    ]

    # Agent 明细 (紧凑模式)
    agent_count = 0
    for agent_id, result in results.items():
        if result.signal.value == "error":
            continue
        emoji = AGENT_EMOJI.get(agent_id, "\U0001f464")
        signal_cn_agent = SIGNAL_CN.get(result.signal.value, result.signal.value)
        name = result.agent_name[:8]
        lines.append(f"{emoji} {name} | {signal_cn_agent} | {result.score:.1f}")
        agent_count += 1

    # 关键发现
    if consensus.key_findings:
        lines.append("")
        lines.append("**\u5173\u952e\u53d1\u73b0:**")
        for finding in consensus.key_findings[:3]:
            lines.append(f"\u2022 {finding}")

    # 风险
    if consensus.risks:
        lines.append("")
        lines.append("**\u26a0\ufe0f \u98ce\u9669:**")
        for risk in consensus.risks[:2]:
            lines.append(f"\u2022 {risk}")

    return "\n".join(lines)


def format_single_agent_wechat(ticker: str, result) -> str:
    """Format a single agent response for WeChat markdown."""
    signal_emoji = SIGNAL_EMOJI.get(result.signal.value, "")
    signal_cn = SIGNAL_CN.get(result.signal.value, result.signal.value)
    emoji = AGENT_EMOJI.get(result.agent_id, "\U0001f464")

    lines = [
        f"**{emoji} {result.agent_name} \u5206\u6790 - {ticker.upper()}**",
        "",
        f"> \u4fe1\u53f7: {signal_emoji} **{signal_cn.upper()}**",
        f"> \u8bc4\u5206: **{result.score:.1f}/10**",
        f"> \u7f6e\u4fe1\u5ea6: **{result.confidence:.0%}**",
        "",
        f"**\u63a8\u7406:**",
        result.reasoning[:300],
    ]

    if result.key_findings:
        lines.append("")
        lines.append("**\u5173\u952e\u53d1\u73b0:**")
        for finding in result.key_findings[:3]:
            lines.append(f"\u2022 {finding}")

    return "\n".join(lines)


class WeComBot:
    """企业微信 Bot - 接收消息 + 主动推送

    使用 wechatpy 库实现企业微信回调消息处理和主动推送。
    """

    def __init__(self, corp_id: str, corp_secret: str, agent_id: str,
                 token: str, aes_key: str):
        """初始化企业微信 Bot.

        Args:
            corp_id: 企业ID
            corp_secret: 应用Secret
            agent_id: 应用AgentId
            token: 回调Token
            aes_key: 回调EncodingAESKey
        """
        try:
            from wechatpy.enterprise import WeChatClient
            from wechatpy.enterprise.crypto import WeChatCrypto
        except ImportError:
            raise ImportError(
                "wechatpy is not installed.\n"
                "Install with: pip install 'augur-agents[wechat]'\n"
                "  or: pip install wechatpy>=2.0.0 cryptography>=3.0"
            )

        self.corp_id = corp_id
        self.agent_id = agent_id
        self.client = WeChatClient(corp_id, corp_secret)
        self.crypto = WeChatCrypto(token, aes_key, corp_id)

    def handle_message(self, msg) -> Optional[str]:
        """Parse incoming message and route to appropriate handler.

        Args:
            msg: 企业微信消息对象 (wechatpy Message)

        Returns:
            Response text or None
        """
        content = msg.content if hasattr(msg, "content") else ""
        if not content:
            return None

        text = content.strip()

        # 帮助命令
        if text in ("帮助", "help", "?", "？"):
            return self._help_text()

        # 投资人列表
        if text in ("投资人列表", "personas", "列表"):
            return self._personas_text()

        # 分析命令: "分析 AAPL" 或 "analyze AAPL"
        analyze_match = re.match(r"(?:分析|analyze)\s+(\S+)(.*)", text, re.IGNORECASE)
        if analyze_match:
            ticker = analyze_match.group(1).upper()
            extra = analyze_match.group(2)
            metrics = _parse_metrics(extra)
            return self._run_consensus(ticker, metrics)

        # 特定大师: "@巴菲特 AAPL" 或 "问 buffett AAPL"
        ask_match = re.match(r"(?:@|问\s*)(\S+)\s+(\S+)(.*)", text)
        if ask_match:
            persona_name = ask_match.group(1)
            ticker_or_question = ask_match.group(2)
            extra = ask_match.group(3)
            persona_id = PERSONA_MENTIONS.get(persona_name)
            if persona_id:
                ticker = _extract_ticker(ticker_or_question + " " + extra) or ticker_or_question.upper()
                metrics = _parse_metrics(extra)
                return self._run_single_agent(persona_id, ticker, metrics)

        return None

    def send_analysis(self, user_id: str, ticker: str, results: dict, consensus):
        """Send analysis results to user via 企业微信.

        Args:
            user_id: 企业微信用户ID
            ticker: 股票代码
            results: Agent分析结果字典
            consensus: 共识结果
        """
        message = format_wechat_message(ticker, consensus, results)
        self.client.message.send_markdown(
            self.agent_id, user_id, message
        )

    def _run_consensus(self, ticker: str, metrics: Dict[str, float]) -> str:
        """Run consensus analysis and return formatted message."""
        try:
            from augur.registry import AgentRegistry, DecisionCoordinator

            market_ctx = _build_market_context(ticker, metrics)
            registry = AgentRegistry()
            coordinator = DecisionCoordinator(registry)

            results = coordinator.analyze_with_all(market_ctx)
            consensus = coordinator.get_consensus(results, ticker=ticker, context=market_ctx)

            return format_wechat_message(ticker, consensus, results)
        except Exception as e:
            return f"\u274c \u5206\u6790\u5931\u8d25: {e}"

    def _run_single_agent(self, persona_id: str, ticker: str,
                          metrics: Dict[str, float]) -> str:
        """Run single agent analysis and return formatted message."""
        try:
            from augur.registry import AgentRegistry

            registry = AgentRegistry()
            agent = registry.get(persona_id)

            if not agent:
                return f"\u274c \u672a\u627e\u5230\u6295\u8d44\u4eba: {persona_id}"

            market_ctx = _build_market_context(ticker, metrics)
            result = agent.analyze(market_ctx)
            return format_single_agent_wechat(ticker, result)
        except Exception as e:
            return f"\u274c \u5206\u6790\u5931\u8d25: {e}"

    def _help_text(self) -> str:
        """Generate help message."""
        return (
            "**\U0001f989 Augur - \u591a\u667a\u80fd\u4f53\u6295\u8d44\u5206\u6790**\n\n"
            "**\u53ef\u7528\u547d\u4ee4:**\n"
            "\u2022 `\u5206\u6790 TICKER` - 17\u4f4d\u5927\u5e08\u5171\u8bc6\u5206\u6790\n"
            "\u2022 `@\u5df4\u83f2\u7279 TICKER` - \u5411\u7279\u5b9a\u5927\u5e08\u63d0\u95ee\n"
            "\u2022 `\u95ee buffett TICKER` - \u540c\u4e0a\n"
            "\u2022 `\u6295\u8d44\u4eba\u5217\u8868` - \u5217\u51fa\u6240\u6709\u5927\u5e08\n"
            "\u2022 `\u5e2e\u52a9` - \u663e\u793a\u672c\u5e2e\u52a9\n\n"
            "**\u793a\u4f8b:**\n"
            "\u2022 `\u5206\u6790 AAPL pe=32 roe=0.55`\n"
            "\u2022 `@\u6bb5\u6c38\u5e73 NVDA`\n"
            "\u2022 `\u95ee \u5f20\u78ca PDD`"
        )

    def _personas_text(self) -> str:
        """Generate personas list message."""
        try:
            from augur.registry import AgentRegistry

            registry = AgentRegistry()
            agents = registry.get_all()

            lines = [f"**\U0001f989 \u53ef\u7528\u6295\u8d44\u5927\u5e08 ({len(agents)}\u4f4d)**\n"]
            for agent in agents:
                emoji = AGENT_EMOJI.get(agent.agent_id, "\U0001f464")
                lines.append(f"{emoji} `{agent.agent_id}` - {agent.name}")

            return "\n".join(lines)
        except Exception as e:
            return f"\u274c \u83b7\u53d6\u5217\u8868\u5931\u8d25: {e}"


class WebhookBot:
    """微信群机器人 Webhook - 仅推送

    使用企业微信群机器人 Webhook 接口，支持发送 markdown 消息到群组。
    适合配合 Cron 定时推送分析结果。
    """

    def __init__(self, webhook_url: str):
        """初始化 Webhook Bot.

        Args:
            webhook_url: 企业微信群机器人 Webhook 地址
        """
        self.webhook_url = webhook_url

    def send_markdown(self, content: str):
        """Send markdown message to group via webhook.

        Args:
            content: Markdown 格式的消息内容
        """
        import urllib.request

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("errcode") != 0:
                    print(f"WeChat webhook error: {result.get('errmsg', 'unknown')}")
        except Exception as e:
            print(f"Failed to send WeChat webhook: {e}")

    def send_text(self, content: str, mentioned_list: Optional[list] = None):
        """Send plain text message to group via webhook.

        Args:
            content: 文本消息内容
            mentioned_list: 需要@的用户列表 (user_id), "@all" 表示所有人
        """
        import urllib.request

        payload: Dict[str, Any] = {
            "msgtype": "text",
            "text": {
                "content": content,
            }
        }
        if mentioned_list:
            payload["text"]["mentioned_list"] = mentioned_list

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("errcode") != 0:
                    print(f"WeChat webhook error: {result.get('errmsg', 'unknown')}")
        except Exception as e:
            print(f"Failed to send WeChat webhook: {e}")

    def send_consensus(self, ticker: str, consensus, agent_results: dict):
        """Format and send consensus report via webhook.

        Args:
            ticker: 股票代码
            consensus: 共识结果
            agent_results: Agent分析结果字典
        """
        message = format_wechat_message(ticker, consensus, agent_results)
        self.send_markdown(message)


def run_wecom_server(port: int = 8080):
    """Start WeCom callback server.

    启动企业微信回调服务器，监听消息事件并自动回复分析结果。

    Args:
        port: HTTP 端口号
    """
    corp_id = os.environ.get("WECHAT_CORP_ID")
    corp_secret = os.environ.get("WECHAT_CORP_SECRET")
    agent_id = os.environ.get("WECHAT_AGENT_ID")
    token = os.environ.get("WECHAT_TOKEN")
    aes_key = os.environ.get("WECHAT_AES_KEY")

    if not all([corp_id, corp_secret, agent_id, token, aes_key]):
        print("Error: WeCom environment variables not set.")
        print("")
        print("Required:")
        print("  export WECHAT_CORP_ID='your_corp_id'")
        print("  export WECHAT_CORP_SECRET='your_corp_secret'")
        print("  export WECHAT_AGENT_ID='your_agent_id'")
        print("  export WECHAT_TOKEN='your_token'")
        print("  export WECHAT_AES_KEY='your_aes_key'")
        print("")
        print("See: https://developer.work.weixin.qq.com/document/")
        raise SystemExit(1)

    try:
        from wechatpy.enterprise import WeChatClient  # noqa: F401
        from wechatpy.enterprise.crypto import WeChatCrypto  # noqa: F401
    except ImportError:
        print("Error: wechatpy is not installed.")
        print("Install it with: pip install 'augur-agents[wechat]'")
        print("  or: pip install wechatpy>=2.0.0 cryptography>=3.0")
        raise SystemExit(1)

    bot = WeComBot(corp_id, corp_secret, agent_id, token, aes_key)

    # 使用 Flask 风格的简单 HTTP server 处理回调
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    import xml.etree.ElementTree as ET

    class WeComHandler(BaseHTTPRequestHandler):
        """HTTP handler for WeCom callback verification and messages."""

        def do_GET(self):
            """Handle WeCom URL verification (验证回调URL)."""
            query = parse_qs(urlparse(self.path).query)
            msg_signature = query.get("msg_signature", [""])[0]
            timestamp = query.get("timestamp", [""])[0]
            nonce = query.get("nonce", [""])[0]
            echostr = query.get("echostr", [""])[0]

            try:
                echo = bot.crypto.check_signature(
                    msg_signature, timestamp, nonce, echostr
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(echo.encode("utf-8"))
            except Exception as e:
                self.send_response(403)
                self.end_headers()
                print(f"Verification failed: {e}")

        def do_POST(self):
            """Handle incoming WeCom messages."""
            query = parse_qs(urlparse(self.path).query)
            msg_signature = query.get("msg_signature", [""])[0]
            timestamp = query.get("timestamp", [""])[0]
            nonce = query.get("nonce", [""])[0]

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                decrypted_xml = bot.crypto.decrypt_message(
                    body, msg_signature, timestamp, nonce
                )
                # 解析XML消息
                root = ET.fromstring(decrypted_xml)
                msg_type = root.find("MsgType").text
                from_user = root.find("FromUserName").text

                if msg_type == "text":
                    content = root.find("Content").text or ""

                    # 创建简单消息对象
                    class SimpleMsg:
                        pass

                    msg = SimpleMsg()
                    msg.content = content

                    reply = bot.handle_message(msg)
                    if reply:
                        # 发送回复 (通过主动推送API)
                        bot.client.message.send_markdown(
                            bot.agent_id, from_user, reply
                        )

                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"success")

            except Exception as e:
                print(f"Message handling error: {e}")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"success")

        def log_message(self, format, *args):
            """Suppress default logging."""
            pass

    print(f"\U0001f989 Augur WeCom Bot starting on port {port}...")
    print(f"   Corp ID: {corp_id[:8]}...")
    print(f"   Agent ID: {agent_id}")
    print(f"   Callback URL: http://YOUR_SERVER:{port}/")
    print("")
    print("Configure callback URL in WeCom admin console:")
    print(f"  URL: http://YOUR_DOMAIN:{port}/")
    print(f"  Token: (your WECHAT_TOKEN)")
    print(f"  EncodingAESKey: (your WECHAT_AES_KEY)")
    print("")
    print("Press Ctrl+C to stop.")

    server = HTTPServer(("0.0.0.0", port), WeComHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeCom Bot stopped.")
        server.shutdown()


def run_webhook_mode():
    """Run in webhook-only mode (for cron push).

    从 watchlist 读取配置并通过 webhook 推送分析结果到企业微信群。
    """
    webhook_url = os.environ.get("WECHAT_WEBHOOK_URL")
    if not webhook_url:
        print("Error: WECHAT_WEBHOOK_URL environment variable is not set.")
        print("")
        print("To get a webhook URL:")
        print("  1. Open WeCom group chat")
        print("  2. Click group settings > Group Robots > Add Robot")
        print("  3. Copy the Webhook URL")
        print("  4. Set it: export WECHAT_WEBHOOK_URL='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx'")
        raise SystemExit(1)

    bot = WebhookBot(webhook_url)

    # 运行 watchlist 分析并推送
    from augur.cron import run_watchlist_analysis

    print("\U0001f989 Augur WeChat Webhook mode - running watchlist analysis...")
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

    print(f"\nDone. Sent {len(results)} reports to WeChat group.")


def run_wechat_bot(mode: str = "wecom", port: int = 8080):
    """Start the WeChat bot.

    Args:
        mode: 'wecom' for full enterprise mode, 'webhook' for webhook-only push
        port: Port for WeCom callback server (default: 8080)
    """
    if mode == "webhook":
        run_webhook_mode()
    else:
        run_wecom_server(port=port)
