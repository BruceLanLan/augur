# -*- coding: utf-8 -*-
"""Tests for augur.chat - AI Natural Language Chat Engine"""

import pytest

from augur.chat import ChatEngine, _detect_topic, _PERSONA_TEMPLATES


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
