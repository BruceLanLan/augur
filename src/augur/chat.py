# -*- coding: utf-8 -*-
"""
augur.chat - AI Natural Language Chat Engine

Provides chat interactions with each agent persona using template-based
responses. No external LLM API required - generates formatted responses
using persona-specific prompt templates.

Architecture:
    - ChatEngine: Stateful engine that maintains conversation history
    - Template system: Per-persona greeting, prefix, and topic-based responses
    - Topic detection: keyword-based classification (value, risk, market, general)

Supported Personas:
    buffett, graham, lynch, dalio, munger, soros, marks, cathie_wood,
    serenity, thiel, duan_yongping (11 personas with unique speaking styles)

Features:
    - Persona-specific voice and vocabulary
    - Topic-aware responses (value investing, risk, market outlook, general)
    - Conversation history accumulation across calls
    - Available agents listing for UI integration

Integration:
    - Module-level singleton in dashboard/app.py (_get_chat_engine())
    - CLI command: `augur chat <ticker> [--persona buffett]`
    - REST API: POST /api/chat with message and optional agent_id

Usage:
    engine = ChatEngine()
    resp = engine.get_response("What about AAPL?", agent_id="buffett")
    history = engine.get_history()
"""

import random
import time
from typing import Dict, List, Any, Optional


# Persona response templates: each agent has a distinct speaking style
_PERSONA_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "buffett": {
        "greeting": "Well, let me think about this the way I think about any investment...",
        "style": "folksy, uses analogies from baseball and daily life",
        "prefix": "As I've always said at our annual meetings,",
        "topics": {
            "value": "The key is finding wonderful businesses at fair prices. Look for durable competitive advantages - what I call 'moats'.",
            "risk": "Risk comes from not knowing what you're doing. If you understand the business, the margin of safety will protect you.",
            "market": "Mr. Market is your servant, not your guide. When others are fearful, be greedy. When others are greedy, be fearful.",
            "general": "Rule No. 1: Never lose money. Rule No. 2: Never forget Rule No. 1. Think of stocks as pieces of businesses, not as trading chips.",
        },
    },
    "graham": {
        "greeting": "From a security analysis perspective, let us examine this methodically...",
        "style": "academic, quantitative, emphasizes safety margins",
        "prefix": "The intelligent investor recognizes that",
        "topics": {
            "value": "An investment operation is one which, upon thorough analysis, promises safety of principal and an adequate return. Look for PE below 15 and PB below 1.5.",
            "risk": "The margin of safety is always dependent on the price paid. No matter how wonderful a business, paying too much transforms it into a speculation.",
            "market": "The market is a voting machine in the short run, a weighing machine in the long run. Focus on intrinsic value, not market sentiment.",
            "general": "Buy when most people are pessimistic, and sell when most people are optimistic. The individual investor should act consistently as an investor and not as a speculator.",
        },
    },
    "lynch": {
        "greeting": "Hey, this reminds me of something I noticed at the mall last weekend...",
        "style": "casual, observational, finds opportunities in everyday life",
        "prefix": "In my experience managing Magellan,",
        "topics": {
            "value": "Go for a business that any idiot can run - because sooner or later, one will. Look for companies with strong earnings growth and reasonable PEG ratios.",
            "risk": "Know what you own, and know why you own it. If you cannot explain to a 10-year-old why you own a stock, you should not own it.",
            "market": "The stock market is not a casino. Behind every stock is a company. Your edge is in your everyday observations.",
            "general": "Invest in what you know. The best stock ideas come from the shopping mall, the workplace, or the dinner table. Be patient - big winners can take years to play out.",
        },
    },
    "dalio": {
        "greeting": "Let me approach this through the lens of principles and macro cycles...",
        "style": "systematic, principles-based, macro-focused",
        "prefix": "Based on my study of economic cycles and history,",
        "topics": {
            "value": "Diversification is the holy grail of investing. Build an all-weather portfolio that performs across different economic environments.",
            "risk": "The biggest risk is not the risk you can see, but the one you cannot see. Stress-test your portfolio against historical scenarios.",
            "market": "We are in a long-term debt cycle. Understand where we are in the cycle and position accordingly. Cash is rarely king for long periods.",
            "general": "Pain plus reflection equals progress. Build a machine of principles that can operate independently. Radical transparency leads to better outcomes.",
        },
    },
    "munger": {
        "greeting": "Well, I'd say that's a perfectly obvious question if you think about it from first principles...",
        "style": "blunt, uses mental models, references Charlie Almanack",
        "prefix": "It's obvious when you apply basic mental models -",
        "topics": {
            "value": "All intelligent investing is value investing. Acquire more than you are paying for. The big money is in the waiting.",
            "risk": "Invert, always invert. Instead of asking how to succeed, ask what would guarantee failure, then avoid those things.",
            "market": "The market is a pari-mutuel system. You have to bet against the crowd when the odds are in your favor. Avoid the folly of the crowd.",
            "general": "Spend each day trying to be a little wiser than you were when you woke up. Mental models from multiple disciplines are your toolkit.",
        },
    },
    "soros": {
        "greeting": "The situation is never as simple as the consensus believes...",
        "style": "contrarian, reflexivity theory, macro trader",
        "prefix": "Through the lens of reflexivity and market feedback loops,",
        "topics": {
            "value": "Markets are always wrong in the sense that they present a biased view of reality. Reflexivity creates self-reinforcing cycles.",
            "risk": "It's not whether you're right or wrong that's important, but how much money you make when you're right and how much you lose when wrong.",
            "market": "Financial markets test hypotheses. When you identify a divergence between perception and reality, that's your opportunity.",
            "general": "The worse a situation becomes, the less it takes to turn it around, and the bigger the upside. Find the inflection point.",
        },
    },
    "marks": {
        "greeting": "I think the most important thing here is to understand where we are in the cycle...",
        "style": "thoughtful, cycle-aware, risk-focused memos",
        "prefix": "As I wrote in my latest memo to Oaktree clients,",
        "topics": {
            "value": "The most profitable investment actions are by definition contrarian. You buy at the point of maximum pessimism.",
            "risk": "Risk means more things can happen than will happen. Understanding the range of outcomes is more important than predicting the single most likely one.",
            "market": "The pendulum of investor psychology swings between euphoria and depression. Knowing where we are in the cycle is essential.",
            "general": "Being too far ahead of your time is indistinguishable from being wrong. Second-level thinking separates great investors from average ones.",
        },
    },
    "cathie_wood": {
        "greeting": "This is exactly the kind of disruptive innovation opportunity we're focused on...",
        "style": "forward-looking, innovation-focused, high conviction",
        "prefix": "Our research at ARK shows that",
        "topics": {
            "value": "We invest in technologies that are on the right side of change. The convergence of AI, robotics, genomics, and blockchain will create trillions in value.",
            "risk": "The real risk is not investing in innovation. Companies that fail to adapt will be disrupted. The market underestimates exponential growth curves.",
            "market": "We are in the early innings of a technology revolution. Current valuations for disruptive innovators reflect a fraction of their long-term potential.",
            "general": "We take a 5-year time horizon. Short-term volatility is noise. Focus on Wright's Law and the declining cost curves of transformative technologies.",
        },
    },
    "serenity": {
        "greeting": "Let me reverse-engineer this from the physical layer up...",
        "style": "deep-tech supply chain analysis, choke-point theory, semiconductor hardware focus",
        "prefix": "Through supply chain reverse engineering,",
        "topics": {
            "value": "The real alpha is in identifying irreplaceable chokepoints - small-cap monopolies in critical supply chains that the entire AI infrastructure depends on.",
            "risk": "Liquidity traps in micro-cap stocks are real. When the exit is narrow and everyone runs for the door at once, the stampede is brutal.",
            "market": "Wall Street has institutional blind spots. They cannot cover sub-$1B companies in Sweden or Taiwan. That research vacuum is your edge.",
            "general": "Think bottom-up, not top-down. Start with the GPU, trace every physical component backward until you find what cannot be substituted. That is your Strait of Hormuz.",
        },
    },
    "thiel": {
        "greeting": "The contrarian question you should ask is: what do I believe that nobody else agrees with?",
        "style": "contrarian, zero-to-one thinking, monopoly theory",
        "prefix": "From a zero-to-one perspective,",
        "topics": {
            "value": "Competition is for losers. Invest in companies that create monopolies through technological secrets that others cannot replicate.",
            "risk": "Definite optimism requires planning. The biggest risk is incrementalism - thinking small when the opportunity demands bold action.",
            "market": "The most valuable companies of the future are being built today by people who believe in definite, not indefinite, futures.",
            "general": "Every great company solves a unique problem. Ask: what valuable company is nobody building? That is where the 10x opportunity lies.",
        },
    },
    "duan_yongping": {
        "greeting": "Let me think about this from the perspective of 'ben fen' (doing the right thing)...",
        "style": "focused on business quality, extreme concentration, Chinese value philosophy",
        "prefix": "My philosophy of 'ben fen' tells me that",
        "topics": {
            "value": "Only invest in businesses you truly understand. Extreme concentration in your best ideas. Quality of business matters more than price.",
            "risk": "Stop doing wrong things. That is more important than finding the right things to do. If you do not understand it, do not buy it.",
            "market": "The market gives you opportunities precisely because most people are emotional. Be rational. Be patient. Your circle of competence is your edge.",
            "general": "I do not do short-term trading. I buy great businesses and hold them. OPPO and vivo succeeded because of focus and doing the right thing consistently.",
        },
    },
}

# Default template for agents without specific templates
_DEFAULT_TEMPLATE = {
    "greeting": "Based on my analysis and investment philosophy...",
    "style": "professional, analytical",
    "prefix": "From my perspective,",
    "topics": {
        "value": "Focus on fundamentals: earnings quality, balance sheet strength, and sustainable competitive advantages.",
        "risk": "Diversification and position sizing are your primary risk management tools. Never put all eggs in one basket.",
        "market": "Markets are cyclical. Understanding where we are in the cycle helps frame the risk/reward of any position.",
        "general": "Discipline and patience are the investor's greatest allies. Have a process and stick to it through market noise.",
    },
}


def _detect_topic(message: str) -> str:
    """Detect the topic category from the user's message."""
    msg_lower = message.lower()
    value_keywords = ["value", "cheap", "undervalued", "pe", "pb", "margin", "price", "buy", "worth"]
    risk_keywords = ["risk", "danger", "loss", "crash", "bear", "hedge", "protect", "volatility"]
    market_keywords = ["market", "economy", "cycle", "bull", "trend", "macro", "fed", "interest"]

    if any(kw in msg_lower for kw in value_keywords):
        return "value"
    elif any(kw in msg_lower for kw in risk_keywords):
        return "risk"
    elif any(kw in msg_lower for kw in market_keywords):
        return "market"
    return "general"


_MAX_HISTORY_ENTRIES = 200


class ChatEngine:
    """
    AI Natural Language Chat Engine.

    Generates persona-specific responses using template strings.
    Each agent responds in character based on their investment philosophy.
    """

    def __init__(self):
        """Initialize the ChatEngine."""
        self._history: List[Dict[str, Any]] = []
        # Per-agent rolling conversation for multi-turn LLM context:
        # {agent_id: [{"role": "user"|"assistant", "content": str}, ...]}
        self._conversations: Dict[str, List[Dict[str, str]]] = {}

    def _append_history(self, entry: Dict[str, Any]) -> None:
        self._history.append(entry)
        if len(self._history) > _MAX_HISTORY_ENTRIES:
            self._history = self._history[-_MAX_HISTORY_ENTRIES:]

    def _build_chat_system_prompt(self, agent_id: str) -> Optional[str]:
        """
        Build a CHAT-oriented system prompt from the persona's identity and
        philosophy. We deliberately do NOT reuse agent.get_system_prompt() —
        that prompt instructs structured "## Signal / ## Score" analysis output,
        which is wrong for conversational chat. Building from identity+philosophy
        works uniformly for all 18 personas (not just the ~8 that override it).
        """
        try:
            from augur.registry import get_registry
            agent = get_registry().get(agent_id)
            if not agent:
                return None
            name = getattr(agent, "name", agent_id)
            identity = (getattr(agent, "identity", "") or "").strip()
            philosophy = getattr(agent, "philosophy", []) or []
            phil_str = "、".join(str(p) for p in philosophy) if philosophy else ""

            parts = [f"你是投资大师「{name}」。"]
            if identity:
                parts.append(f"\n你的身份与背景：\n{identity}")
            if phil_str:
                parts.append(f"\n你的核心投资哲学：{phil_str}")
            parts.append(
                "\n请始终保持这个投资人的视角、语气和分析框架来对话。"
                "用第一人称回答，像本人一样表达观点。"
            )
            return "".join(parts)
        except Exception:
            return None

    def _llm_reply(self, agent_id: str, agent_name: str, message: str) -> Optional[str]:
        """Try to generate a reply via Claude. Returns None to signal fallback."""
        try:
            from augur.llm_client import is_llm_available, llm_persona_reply
            if not is_llm_available():
                return None
            system_prompt = self._build_chat_system_prompt(agent_id)
            if not system_prompt:
                return None
            convo = self._conversations.get(agent_id, [])
            reply = llm_persona_reply(system_prompt, convo, message, agent_name)
            if reply:
                # Persist this turn into the per-agent rolling conversation
                convo = convo + [
                    {"role": "user", "content": message.strip()},
                    {"role": "assistant", "content": reply},
                ]
                # Keep the last ~12 turns (24 messages) to bound context
                self._conversations[agent_id] = convo[-24:]
            return reply
        except Exception:
            return None

    def get_response(self, message: str, agent_id: str = None) -> Dict[str, Any]:
        """
        Generate a response from the specified agent persona.

        Args:
            message: The user's message.
            agent_id: The agent to respond as. If None, uses a random agent.

        Returns:
            Dict with agent_id, agent_name, response text, and metadata.
        """
        if not message or not message.strip():
            return {
                "agent_id": "system",
                "agent_name": "System",
                "response": "Please enter a message to get investment insights.",
                "timestamp": time.time(),
            }

        # Select agent template
        if agent_id and agent_id in _PERSONA_TEMPLATES:
            template = _PERSONA_TEMPLATES[agent_id]
        elif agent_id:
            template = _DEFAULT_TEMPLATE
        else:
            agent_id = random.choice(list(_PERSONA_TEMPLATES.keys()))
            template = _PERSONA_TEMPLATES[agent_id]

        topic = _detect_topic(message)
        agent_name = self._get_agent_name(agent_id)

        # Try the LLM backend first (real Claude reply in persona voice).
        # Falls back to templates when no API key / SDK / on error.
        source = "template"
        response_text = self._llm_reply(agent_id, agent_name, message)
        if response_text:
            source = "llm"
        else:
            # Template fallback
            topic_response = template["topics"].get(topic, template["topics"]["general"])
            greeting = template["greeting"]
            prefix = template["prefix"]
            response_text = f"{greeting}\n\n{prefix} {topic_response}"
            if "$" in message or any(c.isupper() and len(c) >= 2 for c in message.split()):
                response_text += f"\n\nRegarding your specific question about '{message.strip()[:50]}' - I would recommend doing thorough due diligence on the fundamentals before making any decision."

        result = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "response": response_text,
            "topic": topic,
            "source": source,
            "timestamp": time.time(),
        }

        # Store in history
        self._append_history({
            "role": "user",
            "message": message,
            "timestamp": time.time(),
        })
        self._append_history({
            "role": "assistant",
            "agent_id": agent_id,
            "message": response_text,
            "timestamp": time.time(),
        })

        return result

    def get_available_agents(self) -> List[Dict[str, str]]:
        """Get list of available chat agents."""
        agents = []
        for agent_id, template in _PERSONA_TEMPLATES.items():
            agents.append({
                "agent_id": agent_id,
                "name": self._get_agent_name(agent_id),
                "style": template.get("style", ""),
            })
        return agents

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history."""
        return self._history[-limit:]

    def clear_history(self):
        """Clear chat history."""
        self._history = []

    def _get_agent_name(self, agent_id: str) -> str:
        """Get display name for an agent."""
        name_map = {
            "buffett": "Warren Buffett",
            "graham": "Benjamin Graham",
            "lynch": "Peter Lynch",
            "dalio": "Ray Dalio",
            "munger": "Charlie Munger",
            "soros": "George Soros",
            "marks": "Howard Marks",
            "cathie_wood": "Cathie Wood",
            "serenity": "Serenity",
            "thiel": "Peter Thiel",
            "duan_yongping": "Duan Yongping",
            "fisher": "Philip Fisher",
            "arps": "Martin Arps",
            "aschenbrenner": "Leopold Aschenbrenner",
            "dayu": "Dayu",
            "zhang_lei": "Zhang Lei",
            "li_lu": "Li Lu",
            "dan_bin": "Dan Bin",
        }
        return name_map.get(agent_id, agent_id.replace("_", " ").title())
