# -*- coding: utf-8 -*-
"""Test AgentRegistry loads all 18+ agents and basic analysis works."""

import pytest
from augur.registry import AgentRegistry, DecisionCoordinator
from augur.personas.base import MarketContext, SignalType


class TestAgentRegistry:
    def test_registry_loads_default_agents(self):
        registry = AgentRegistry()
        agents = registry.get_all()
        assert len(agents) >= 18, f"Expected >= 18 agents, got {len(agents)}"

    def test_registry_agent_ids(self):
        registry = AgentRegistry()
        agent_ids = [a.agent_id for a in registry.get_all()]
        expected = [
            "buffett", "graham", "lynch", "dalio", "munger",
            "soros", "marks", "cathie_wood", "fisher", "arps",
            "aschenbrenner", "dayu", "thiel",
            "duan_yongping", "zhang_lei", "li_lu", "dan_bin",
            "serenity",
        ]
        for eid in expected:
            assert eid in agent_ids, f"Missing agent: {eid}"

    def test_registry_get_agent(self):
        registry = AgentRegistry()
        buffett = registry.get("buffett")
        assert buffett is not None
        assert buffett.name == "Warren Buffett"

    def test_registry_get_nonexistent(self):
        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    def test_registry_register_unregister(self):
        from augur.personas.base import BaseAgent
        registry = AgentRegistry()
        initial_count = len(registry.get_all())

        # Can't easily create a BaseAgent without subclassing, so just test unregister
        assert registry.unregister("buffett") is True
        assert len(registry.get_all()) == initial_count - 1
        assert registry.get("buffett") is None

    def test_list_agents(self):
        registry = AgentRegistry()
        listing = registry.list_agents()
        assert len(listing) >= 17
        assert all("agent_id" in a for a in listing)
        assert all("name" in a for a in listing)


class TestDecisionCoordinator:
    def test_analyze_with_all(self):
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="AAPL", pe=32, gross_margins=0.46, roe=0.15)

        results = coordinator.analyze_with_all(ctx)
        assert len(results) >= 17

        for agent_id, result in results.items():
            assert result.agent_id == agent_id
            assert result.signal in [SignalType.BULLISH, SignalType.NEUTRAL, SignalType.BEARISH, SignalType.ERROR]

    def test_get_consensus(self):
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="AAPL", pe=32, gross_margins=0.46, roe=0.15)

        results = coordinator.analyze_with_all(ctx)
        consensus = coordinator.get_consensus(results, ticker="AAPL", context=ctx)

        assert consensus.agent_id == "consensus"
        assert consensus.signal in [SignalType.BULLISH, SignalType.NEUTRAL, SignalType.BEARISH]
        assert 0 <= consensus.score <= 10
        assert 0 <= consensus.confidence <= 1

    def test_run_debate(self):
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="TSLA", pe=80, gross_margins=0.25)

        results = coordinator.run_debate(ctx, rounds=2)
        assert len(results) >= 17


class TestConfig:
    def test_get_config(self):
        from augur.config import get_config, reset_config
        reset_config()
        config = get_config()
        assert isinstance(config, dict)
        # Should load from config/agents.yaml
        assert "defaults" in config or config == {}

    def test_set_config(self):
        from augur.config import get_config, set_config, reset_config
        reset_config()
        set_config("test_key", "test_value")
        config = get_config()
        assert config.get("test_key") == "test_value"

    def test_set_config_nested(self):
        from augur.config import set_config, get_config, reset_config
        reset_config()
        set_config("per_agent.buffett", "gpt-4o")
        config = get_config()
        assert config["per_agent"]["buffett"] == "gpt-4o"
