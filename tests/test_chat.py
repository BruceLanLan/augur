# -*- coding: utf-8 -*-
"""Tests for augur.chat - AI Natural Language Chat Engine"""

import pytest

from augur.chat import ChatEngine, _detect_topic, _PERSONA_TEMPLATES, _MAX_HISTORY_ENTRIES


def test_chat_engine_init():
    """Test ChatEngine initialization."""
    engine = ChatEngine()
    assert engine.get_history() == []


def test_chat_engine_get_response_basic():
    """Test basic response generation."""
    engine = ChatEngine()
    result = engine.get_response("What should I invest in?")
    assert "agent_id" in result
    assert "agent_name" in result
    assert "response" in result
    assert "timestamp" in result
    assert len(result["response"]) > 50


def test_chat_engine_specific_agent():
    """Test response from a specific agent."""
    engine = ChatEngine()
    result = engine.get_response("Tell me about value investing", agent_id="buffett")
    assert result["agent_id"] == "buffett"
    assert result["agent_name"] == "Warren Buffett"
    assert len(result["response"]) > 0


def test_chat_engine_serenity_agent():
    """Test response from Serenity persona."""
    engine = ChatEngine()
    result = engine.get_response("What about semiconductor supply chains?", agent_id="serenity")
    assert result["agent_id"] == "serenity"
    assert result["agent_name"] == "Serenity"


def test_chat_engine_empty_message():
    """Test handling of empty messages."""
    engine = ChatEngine()
    result = engine.get_response("")
    assert result["agent_id"] == "system"
    assert "enter a message" in result["response"].lower()


def test_chat_engine_history():
    """Test chat history tracking."""
    engine = ChatEngine()
    engine.get_response("Hello", agent_id="buffett")
    history = engine.get_history()
    assert len(history) == 2  # user msg + assistant msg
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_chat_engine_clear_history():
    """Test clearing chat history."""
    engine = ChatEngine()
    engine.get_response("Test message")
    engine.clear_history()
    assert engine.get_history() == []


def test_chat_engine_available_agents():
    """Test getting available chat agents."""
    engine = ChatEngine()
    agents = engine.get_available_agents()
    assert len(agents) > 5
    agent_ids = [a["agent_id"] for a in agents]
    assert "buffett" in agent_ids
    assert "serenity" in agent_ids
    for agent in agents:
        assert "agent_id" in agent
        assert "name" in agent
        assert "style" in agent


def test_detect_topic_value():
    """Test topic detection for value-related messages."""
    assert _detect_topic("Is this stock undervalued?") == "value"
    assert _detect_topic("What is the PE ratio?") == "value"


def test_detect_topic_risk():
    """Test topic detection for risk-related messages."""
    assert _detect_topic("What are the risks?") == "risk"
    assert _detect_topic("How to hedge my portfolio?") == "risk"


def test_detect_topic_market():
    """Test topic detection for market-related messages."""
    assert _detect_topic("How is the market doing?") == "market"
    assert _detect_topic("What about the economy?") == "market"


def test_detect_topic_general():
    """Test topic detection defaults to general."""
    assert _detect_topic("Hello how are you") == "general"
    assert _detect_topic("What is your philosophy") == "general"


def test_persona_templates_coverage():
    """Test that key agents have templates defined."""
    assert "buffett" in _PERSONA_TEMPLATES
    assert "graham" in _PERSONA_TEMPLATES
    assert "serenity" in _PERSONA_TEMPLATES
    assert "cathie_wood" in _PERSONA_TEMPLATES
    for agent_id, template in _PERSONA_TEMPLATES.items():
        assert "greeting" in template
        assert "topics" in template
        assert "general" in template["topics"]


# ---------------------------------------------------------------------------
# Loop Round 7 — conversation buffer hardening
# ---------------------------------------------------------------------------


def test_history_max_size_caps_at_constant(monkeypatch):
    """History must not grow past _MAX_HISTORY_ENTRIES (oldest dropped)."""
    # Use a small constant for speed and to avoid 200+ calls
    small_cap = 10
    monkeypatch.setattr("augur.chat._MAX_HISTORY_ENTRIES", small_cap, raising=False)
    engine = ChatEngine()
    # Each get_response appends 2 entries (user + assistant) => 5 responses = 10 entries
    for i in range(small_cap + 3):  # 13 messages * 2 = 26 entries >> cap
        engine.get_response(f"msg {i}", agent_id="buffett")
    assert len(engine._history) == small_cap
    # The very first message we sent must have been evicted.
    assert not any(h.get("message") == "msg 0" for h in engine._history)
    # The most recent user message must still be present (FIFO cap, not LIFO).
    assert any(h.get("message") == f"msg {small_cap + 2}" for h in engine._history)


def test_history_chronological_ordering():
    """Entries must remain in insertion order across many turns."""
    engine = ChatEngine()
    for i in range(6):
        engine.get_response(f"turn {i}", agent_id="graham")
    # Extract just the user-message sequence, in order
    user_msgs = [h["message"] for h in engine._history if h.get("role") == "user"]
    assert user_msgs == [f"turn {i}" for i in range(6)]
    # Timestamps must be non-decreasing
    timestamps = [h["timestamp"] for h in engine._history]
    assert timestamps == sorted(timestamps)


def test_history_persistence_across_calls():
    """Cleared history stays empty; non-cleared history survives multiple reads."""
    engine = ChatEngine()
    engine.get_response("hello", agent_id="buffett")
    engine.get_response("world", agent_id="lynch")
    # Two calls, two turns => 4 entries
    assert len(engine.get_history()) == 4
    # Read it again — must be the same snapshot, not re-consumed
    snap1 = engine.get_history()
    snap2 = engine.get_history()
    assert snap1 == snap2
    # clear_history wipes everything and is idempotent
    engine.clear_history()
    assert engine.get_history() == []
    engine.clear_history()
    assert engine.get_history() == []


def test_history_limit_truncates_to_tail():
    """get_history(limit=N) must return the most recent N entries only."""
    engine = ChatEngine()
    for i in range(8):
        engine.get_response(f"q {i}", agent_id="munger")
    # 8 turns * 2 entries = 16 total
    assert len(engine._history) == 16
    last3 = engine.get_history(limit=3)
    assert len(last3) == 3
    # The last 3 entries are: assistant of q7, then ... actually
    # final assistant of q7 is last; tail should end on q7's assistant.
    assert last3[-1]["message"].startswith("Well, I'd say") or last3[-1]["role"] == "assistant"
    # And must be strictly the trailing slice, not arbitrary positions
    assert last3 == engine._history[-3:]


def test_llm_path_used_when_available(monkeypatch):
    """When llm_persona_reply returns text, result['source'] == 'llm' and
    the per-agent conversation buffer is appended with user+assistant turns."""
    engine = ChatEngine()

    # Force the LLM code path: available + system prompt builds + reply succeeds
    monkeypatch.setattr("augur.llm_client.is_llm_available", lambda: True)
    monkeypatch.setattr(
        "augur.chat.ChatEngine._build_chat_system_prompt",
        lambda self, aid: f"SYS for {aid}",
    )
    monkeypatch.setattr(
        "augur.llm_client.llm_persona_reply",
        lambda sys_p, hist, msg, name: f"<<{name} says hi to '{msg}'>>",
    )

    result = engine.get_response("should I buy AAPL?", agent_id="buffett")
    assert result["source"] == "llm"
    assert result["response"] == "<<Warren Buffett says hi to 'should I buy AAPL?'>>"
    # Per-agent conversation buffer is populated and bounded
    convo = engine._conversations.get("buffett", [])
    assert len(convo) == 2
    assert convo[0] == {"role": "user", "content": "should I buy AAPL?"}
    assert convo[1]["role"] == "assistant"
    assert "Warren Buffett" in convo[1]["content"]


def test_llm_path_fallback_to_template(monkeypatch):
    """If LLM is unavailable, source must be 'template' and a non-empty
    persona response is still produced (graceful degradation)."""
    engine = ChatEngine()
    monkeypatch.setattr("augur.llm_client.is_llm_available", lambda: False)
    result = engine.get_response("is this undervalued?", agent_id="graham")
    assert result["source"] == "template"
    assert result["agent_id"] == "graham"
    # Template path always produces a non-trivial reply
    assert len(result["response"]) > 20
    # History still records both turns even on fallback
    assert len(engine._history) == 2
    assert engine._history[0]["role"] == "user"
    assert engine._history[1]["role"] == "assistant"


def test_per_agent_conversation_buffer_isolated(monkeypatch):
    """Two different agents must keep independent conversation buffers; each
    is independently bounded to the last 24 messages (12 turns)."""
    monkeypatch.setattr("augur.llm_client.is_llm_available", lambda: True)
    monkeypatch.setattr(
        "augur.chat.ChatEngine._build_chat_system_prompt",
        lambda self, aid: f"SYS/{aid}",
    )

    def _echo(sys_p, hist, msg, name):
        # Echo user message with a deterministic assistant reply
        return f"reply-for-{name}: {msg}"

    monkeypatch.setattr("augur.llm_client.llm_persona_reply", _echo)

    engine = ChatEngine()
    engine.get_response("u1", agent_id="buffett")
    engine.get_response("u2", agent_id="buffett")
    engine.get_response("x1", agent_id="lynch")

    # buffett has 2 user + 2 assistant = 4 entries; lynch has 1+1 = 2
    assert len(engine._conversations["buffett"]) == 4
    assert len(engine._conversations["lynch"]) == 2
    # Buffet's buffer must not contain lynch's user message
    buf_msgs = [t["content"] for t in engine._conversations["buffett"]]
    assert "x1" not in buf_msgs
    assert "u1" in buf_msgs and "u2" in buf_msgs
    # Now overflow buffett past the 24-msg cap (12 turns)
    for i in range(15):
        engine.get_response(f"b{i}", agent_id="buffett")
    assert len(engine._conversations["buffett"]) <= 24
    # And lynch's buffer is untouched
    assert len(engine._conversations["lynch"]) == 2

