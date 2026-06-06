# -*- coding: utf-8 -*-
"""Test AgentRegistry loads all 18+ agents and basic analysis works."""

import math

import pytest
from augur.registry import AgentRegistry, DecisionCoordinator
from augur.personas.base import BaseAgent, MarketContext, SignalType


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

    def test_no_negative_scores_extreme_inputs(self):
        """No persona should produce negative scores even with extreme inputs."""
        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        # Extreme negative context: high debt, no growth, very high PE
        ctx = MarketContext(
            ticker="EXTREME",
            pe=500,
            pb=50,
            roe=-0.5,
            gross_margins=-0.1,
            revenue_growth=-0.8,
            debt_ratio=0.99,
            fcf=-10,
            market_cap=1,
            current_ratio=0.1,
            rsi=95,
        )
        results = coordinator.analyze_with_all(ctx)
        for agent_id, result in results.items():
            assert result.score >= 0, f"Agent {agent_id} produced negative score: {result.score}"

    def test_consensus_all_error_is_neutral(self):
        """When every agent returns ERROR, consensus must not default to bullish."""
        from augur.personas.base import AgentResponse

        coordinator = DecisionCoordinator(AgentRegistry())
        error_results = {
            "buffett": AgentResponse(
                agent_id="buffett", agent_name="Buffett",
                signal=SignalType.ERROR, confidence=0, score=0,
                reasoning="failed",
            ),
            "graham": AgentResponse(
                agent_id="graham", agent_name="Graham",
                signal=SignalType.ERROR, confidence=0, score=0,
                reasoning="failed",
            ),
        }
        consensus = coordinator.get_consensus(error_results, ticker="AAPL")
        assert consensus.signal == SignalType.NEUTRAL
        assert consensus.metadata.get("low_participation") is True

    def test_analyze_with_empty_registry(self):
        """Empty registry should not crash ThreadPoolExecutor."""
        registry = AgentRegistry()
        for agent in list(registry.get_all()):
            registry.unregister(agent.agent_id)
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="AAPL")
        assert coordinator.analyze_with_all(ctx) == {}


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


class TestRegistryRegistration:
    """Tests for persona registration, dedup, and hot-reload semantics."""

    def test_register_returns_true(self):
        """register() returns True and inserts a new agent."""
        registry = AgentRegistry()
        initial = len(registry.get_all())
        # Use a brand-new ad-hoc agent id
        class _Stub(BaseAgent):
            def analyze(self, context):
                from augur.personas.base import AgentResponse
                return AgentResponse(
                    agent_id=self.agent_id, agent_name=self.name,
                    signal=SignalType.NEUTRAL, confidence=0.5, score=5.0,
                    reasoning="stub",
                )
        stub = _Stub(
            agent_id="stub_new_1", name="Stub", identity="t", philosophy=[],
            scoring_weights={}, thresholds={},
        )
        assert registry.register(stub) is True
        assert len(registry.get_all()) == initial + 1
        assert registry.get("stub_new_1") is stub

    def test_register_overwrites_existing_id(self):
        """Re-registering same id REPLACES the previous agent (current contract)."""
        registry = AgentRegistry()
        original = registry.get("buffett")
        # Build a different agent that reuses the "buffett" id
        class _Stub(BaseAgent):
            def analyze(self, context):
                from augur.personas.base import AgentResponse
                return AgentResponse(
                    agent_id=self.agent_id, agent_name=self.name,
                    signal=SignalType.NEUTRAL, confidence=0.5, score=5.0,
                    reasoning="stub-replacement",
                )
        replacement = _Stub(
            agent_id="buffett", name="BuffettStub", identity="t",
            philosophy=[], scoring_weights={}, thresholds={},
        )
        registry.register(replacement)
        # Replacement should be active; previous Python agent gone
        assert registry.get("buffett") is replacement
        assert registry.get("buffett").name == "BuffettStub"
        assert registry.get("buffett") is not original

    def test_unregister_unknown_id_returns_false(self):
        """unregister() returns False for unknown ids (no exception)."""
        registry = AgentRegistry()
        assert registry.unregister("definitely_not_a_real_agent_xyz") is False

    def test_get_all_returns_independent_list(self):
        """get_all() should return a fresh list; mutating it must not affect registry."""
        registry = AgentRegistry()
        snapshot = registry.get_all()
        snapshot.clear()
        # Internal agents should still be present
        assert len(registry.get_all()) >= 18
        assert registry.get("buffett") is not None

    def test_list_agents_includes_yaml_custom(self):
        """If a YAML persona dir exists, the registry may have loaded custom personas."""
        registry = AgentRegistry()
        # da-yu.yaml and thiel.yaml ship in personas/custom/
        # Built-in 'dayu' is already registered; yaml re-load must not duplicate.
        ids = [a.agent_id for a in registry.get_all()]
        assert ids.count("dayu") == 1, "Duplicate 'dayu' after YAML load"
        # thiel.yaml would only land in registry if its agent_id differs from python 'thiel'
        # Just assert no obvious duplicates exist
        assert len(ids) == len(set(ids)), f"Duplicate ids in registry: {ids}"

    def test_reload_yaml_does_not_duplicate_builtin(self):
        """Calling _register_yaml_personas repeatedly must not duplicate or override built-ins."""
        registry = AgentRegistry()
        # Capture the original built-in 'dayu' Python agent
        original_dayu = registry.get("dayu")
        assert original_dayu is not None
        original_name = original_dayu.name

        # Hot-reload twice
        registry._register_yaml_personas()
        registry._register_yaml_personas()

        # Built-in must be preserved (da-yu.yaml has agent_id=dayu, so it must NOT overwrite)
        assert registry.get("dayu") is original_dayu
        assert registry.get("dayu").name == original_name
        ids = [a.agent_id for a in registry.get_all()]
        assert ids.count("dayu") == 1

    def test_global_registry_is_singleton(self):
        """get_registry() returns the same instance on repeated calls (singleton contract)."""
        import augur.registry as _reg_mod
        reg1 = _reg_mod.get_registry()
        reg2 = _reg_mod.get_registry()
        assert reg1 is reg2
        # The module-level global must now be set to that same instance
        assert _reg_mod._global_registry is reg1


class TestConsensusEdgeCases:
    """Loop 6 Agent: consensus tie-break and coverage sanitization."""

    def test_equal_bull_bear_weights_prefers_neutral(self):
        from augur.personas.base import AgentResponse

        coordinator = DecisionCoordinator(AgentRegistry())
        results = {
            "a": AgentResponse(
                "a", "A", SignalType.BULLISH, 0.8, 5.0, "x", coverage_confidence=1.0
            ),
            "b": AgentResponse(
                "b", "B", SignalType.BEARISH, 0.8, 5.0, "x", coverage_confidence=1.0
            ),
        }
        consensus = coordinator.get_consensus(results, ticker="")
        assert consensus.signal == SignalType.NEUTRAL

    def test_nan_coverage_confidence_does_not_poison_score(self):
        from augur.personas.base import AgentResponse

        coordinator = DecisionCoordinator(AgentRegistry())
        results = {
            "a": AgentResponse(
                "a", "A", SignalType.BULLISH, 0.8, 8.0, "x",
                coverage_confidence=float("nan"),
            ),
            "b": AgentResponse(
                "b", "B", SignalType.BEARISH, 0.8, 2.0, "x", coverage_confidence=1.0
            ),
        }
        consensus = coordinator.get_consensus(results, ticker="")
        assert math.isfinite(consensus.score)
        assert math.isfinite(consensus.confidence)
        assert 0.0 <= consensus.score <= 10.0
