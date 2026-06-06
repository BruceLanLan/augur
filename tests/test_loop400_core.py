# -*- coding: utf-8 -*-
"""Loop-400: thread safety, persona signal consistency, data edge cases."""

from __future__ import annotations

import concurrent.futures
import math
import textwrap
from unittest.mock import patch

import pytest

from augur.personas.base import AgentResponse, BaseAgent, MarketContext, SignalType
from augur.registry import AgentRegistry, DecisionCoordinator, get_coordinator, get_registry


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestRegistryThreadSafety:
    def test_concurrent_register_and_get(self):
        registry = AgentRegistry()
        errors: list[str] = []

        class _Stub(BaseAgent):
            def __init__(self, agent_id: str):
                super().__init__(
                    agent_id=agent_id,
                    name=agent_id,
                    identity="stub",
                    philosophy=[],
                    scoring_weights={},
                    thresholds={},
                )

            def analyze(self, context):
                return AgentResponse(
                    agent_id=self.agent_id,
                    agent_name=self.name,
                    signal=SignalType.NEUTRAL,
                    confidence=0.5,
                    score=5.0,
                    reasoning="ok",
                )

        def worker(i: int):
            try:
                aid = f"loop400_stub_{i}"
                registry.register(_Stub(aid))
                assert registry.get(aid) is not None
                assert len(registry.get_all()) >= 18
                registry.list_agents()
            except Exception as exc:
                errors.append(str(exc))

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futures = [pool.submit(worker, i) for i in range(40)]
            concurrent.futures.wait(futures)

        assert errors == []

    def test_singleton_init_is_thread_safe(self):
        import augur.registry as reg_mod

        reg_mod._global_registry = None
        reg_mod._global_coordinator = None
        seen: list[AgentRegistry] = []
        errors: list[str] = []

        def worker():
            try:
                seen.append(get_registry())
                get_coordinator()
            except Exception as exc:
                errors.append(str(exc))

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(worker) for _ in range(30)]
            concurrent.futures.wait(futures)

        assert errors == []
        assert len({id(r) for r in seen}) == 1


class TestLearningThreadSafety:
    def test_concurrent_record_prediction(self, tmp_path):
        from augur.learning import LearningEngine

        engine = LearningEngine(weights_path=tmp_path / "weights.json")

        def worker(i: int):
            engine.record_prediction("AAPL", f"agent_{i % 5}", "bullish", 7.0, 0.7)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker, i) for i in range(80)]
            concurrent.futures.wait(futures)

        assert engine.prediction_count == 80


class TestSentimentThreadSafety:
    def test_concurrent_cache_access(self):
        from augur.sentiment import SentimentAnalyzer

        analyzer = SentimentAnalyzer()
        errors: list[str] = []

        with patch("augur.sentiment._fetch_stocktwits", return_value=(0.2, 10)):
            with patch("augur.sentiment._fetch_reddit", return_value=None):
                def worker():
                    try:
                        r = analyzer.get_sentiment("AAPL")
                        assert r.ticker == "AAPL"
                        analyzer.clear_cache()
                    except Exception as exc:
                        errors.append(str(exc))

                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    futures = [pool.submit(worker) for _ in range(24)]
                    concurrent.futures.wait(futures)

        assert errors == []


# ---------------------------------------------------------------------------
# Persona signal consistency
# ---------------------------------------------------------------------------


class TestYamlPersonaSignalConsistency:
    def test_bool_scoring_weight_rejected(self, tmp_path):
        from augur.persona_loader import load_persona_yaml

        spec = tmp_path / "bool_weight.yaml"
        spec.write_text(
            textwrap.dedent(
                """\
                agent_id: bool_weight
                name: Bool Weight
                scoring_weights:
                  momentum: true
                """
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="scoring_weights"):
            load_persona_yaml(spec)

    def test_bool_thresholds_use_defaults(self, tmp_path):
        from augur.persona_loader import load_persona_yaml

        spec = tmp_path / "bool_thresh.yaml"
        spec.write_text(
            textwrap.dedent(
                """\
                agent_id: bool_thresh
                name: Bool Thresh
                scoring_weights:
                  momentum: 1.0
                thresholds:
                  bullish_threshold: true
                  bearish_threshold: false
                factors:
                  momentum:
                    base: 8
                    rules: []
                """
            ),
            encoding="utf-8",
        )
        agent = load_persona_yaml(spec)
        assert agent.thresholds["bullish_threshold"] == 7.0
        assert agent.thresholds["bearish_threshold"] == 4.0

        ctx = MarketContext(ticker="TEST", price=10)
        resp = agent.analyze(ctx)
        assert resp.signal == SignalType.BULLISH
        assert resp.score == pytest.approx(8.0)

    def test_normalized_weights_match_python_persona_signal(self, tmp_path):
        from augur.persona_loader import load_persona_yaml

        spec = tmp_path / "weights.yaml"
        spec.write_text(
            textwrap.dedent(
                """\
                agent_id: weight_norm
                name: Weight Norm
                scoring_weights:
                  a: 0.25
                  b: 0.25
                factors:
                  a:
                    base: 10
                    rules: []
                  b:
                    base: 0
                    rules: []
                thresholds:
                  bullish_threshold: 6.0
                  bearish_threshold: 4.0
                """
            ),
            encoding="utf-8",
        )
        agent = load_persona_yaml(spec)
        resp = agent.analyze(MarketContext(ticker="TEST"))
        assert resp.score == pytest.approx(5.0)
        assert resp.signal == SignalType.NEUTRAL


class TestConsensusSignalConsistency:
    def test_three_way_tie_resolves_neutral(self):
        coordinator = DecisionCoordinator(AgentRegistry())
        results = {
            "a": AgentResponse("a", "A", SignalType.BULLISH, 0.8, 7.0, "x"),
            "b": AgentResponse("b", "B", SignalType.BEARISH, 0.8, 3.0, "x"),
            "c": AgentResponse("c", "C", SignalType.NEUTRAL, 0.8, 5.0, "x"),
        }
        consensus = coordinator.get_consensus(results, ticker="")
        assert consensus.signal == SignalType.NEUTRAL


# ---------------------------------------------------------------------------
# Data edge cases
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_data_state():
    from augur import data as data_mod

    data_mod.clear_cache()
    data_mod.reset_providers_cache()
    yield
    data_mod.clear_cache()
    data_mod.reset_providers_cache()


class TestDataEdgeCases:
    def test_safe_num_rejects_bool(self):
        from augur.datasources.base import safe_num

        assert safe_num(True) == 0.0
        assert safe_num(False) == 0.0
        assert safe_num(True, default=9.0) == 9.0

    def test_sanitize_price_series_drops_bool_and_nan(self):
        from augur.data import _sanitize_price_series

        assert _sanitize_price_series([100, True, float("nan"), 101, -5, "x"]) == [100.0, 101.0]

    def test_batch_none_tickers_rejected(self):
        from augur.data import fetch_market_context_batch

        out = fetch_market_context_batch(None)
        assert "INVALID" in out
        assert "None" in out["INVALID"].data_error

    def test_batch_empty_list_returns_empty_dict(self):
        from augur.data import fetch_market_context_batch

        assert fetch_market_context_batch([]) == {}

    def test_reset_providers_cache(self):
        from augur import data as data_mod

        data_mod._providers_cache = ["stub"]
        data_mod.reset_providers_cache()
        assert data_mod._providers_cache is None

    def test_calculate_technicals_ignores_bool_closes(self):
        from augur.data import calculate_technicals

        prices = [{"close": 100 + i} for i in range(30)]
        prices[5]["close"] = True
        result = calculate_technicals(prices)
        assert math.isfinite(result.get("rsi", 50))
        assert 0 <= result["rsi"] <= 100
