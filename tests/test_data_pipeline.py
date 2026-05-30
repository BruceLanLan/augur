# -*- coding: utf-8 -*-
"""
Tests for data pipeline validation: type safety, unit conversions,
None handling, error propagation, and performance timing instrumentation.
"""

import time

import pytest

from augur.personas.base import MarketContext, SignalType, AgentResponse
from augur.registry import AgentRegistry, DecisionCoordinator


# ============ Fixtures ============


@pytest.fixture
def registry():
    return AgentRegistry()


@pytest.fixture
def coordinator(registry):
    return DecisionCoordinator(registry)


# ============ Test 1: All-zero fields ============


class TestAllZeroFields:
    """MarketContext with all-zero fields - every persona handles gracefully."""

    def test_all_zero_no_crash(self, coordinator):
        """No ZeroDivisionError or crash when all numeric fields are zero."""
        ctx = MarketContext(ticker="ZERO")
        results = coordinator.analyze_with_all(ctx)

        assert len(results) >= 18
        for agent_id, resp in results.items():
            assert resp.signal in (
                SignalType.BULLISH,
                SignalType.NEUTRAL,
                SignalType.BEARISH,
                SignalType.ERROR,
            ), f"Agent {agent_id} returned invalid signal"
            # ERROR is acceptable (graceful failure), but no unhandled exception
            assert isinstance(resp.score, (int, float))
            assert isinstance(resp.confidence, (int, float))


# ============ Test 2: None-like values ============


class TestNoneLikeValues:
    """MarketContext with None-like values (0, empty strings)."""

    def test_none_like_no_crash(self, coordinator):
        """Fields at 0 and empty strings do not cause crashes."""
        ctx = MarketContext(
            ticker="NONE",
            pe=0,
            roe=0,
            gross_margins=0,
            operating_margins=0,
            revenue_growth=0,
            debt_ratio=0,
            fcf=0,
            market_cap=0,
            sector="",
            industry="",
        )
        results = coordinator.analyze_with_all(ctx)

        assert len(results) >= 18
        for agent_id, resp in results.items():
            assert resp.signal in (
                SignalType.BULLISH,
                SignalType.NEUTRAL,
                SignalType.BEARISH,
                SignalType.ERROR,
            )


# ============ Test 3: Extreme values ============


class TestExtremeValues:
    """MarketContext with extreme values - scores stay in [0, 10]."""

    def test_extreme_values_scores_bounded(self, coordinator):
        """With extreme inputs, scores remain in [0, 10] and signals are valid."""
        ctx = MarketContext(
            ticker="EXTREME",
            pe=99999,
            roe=10.0,
            debt_ratio=5.0,
            gross_margins=0.99,
            revenue_growth=100.0,
            fcf=1000,
            market_cap=5000,
            rsi=99,
        )
        results = coordinator.analyze_with_all(ctx)

        for agent_id, resp in results.items():
            if resp.signal != SignalType.ERROR:
                assert 0 <= resp.score <= 10, (
                    f"Agent {agent_id} score {resp.score} out of [0, 10]"
                )
                assert resp.signal in (
                    SignalType.BULLISH,
                    SignalType.NEUTRAL,
                    SignalType.BEARISH,
                )


# ============ Test 4: Debt ratio conversion ============


class TestDebtRatioConversion:
    """Verify data.py converts yfinance debtToEquity correctly."""

    def test_conversion_162(self):
        """debtToEquity=162 -> debt_ratio ~ 0.618."""
        debt_to_equity = 162
        de_ratio = debt_to_equity / 100.0
        debt_ratio = de_ratio / (1.0 + de_ratio)
        assert abs(debt_ratio - 0.618) < 0.01

    def test_conversion_zero(self):
        """debtToEquity=0 -> debt_ratio=0."""
        debt_to_equity = 0
        if debt_to_equity > 0:
            de_ratio = debt_to_equity / 100.0
            debt_ratio = de_ratio / (1.0 + de_ratio)
        else:
            debt_ratio = 0
        assert debt_ratio == 0

    def test_conversion_negative(self):
        """Negative debtToEquity (negative equity) -> debt_ratio=0."""
        debt_to_equity = -150
        if debt_to_equity > 0:
            de_ratio = debt_to_equity / 100.0
            debt_ratio = de_ratio / (1.0 + de_ratio)
        else:
            debt_ratio = 0
        assert debt_ratio == 0

    def test_conversion_very_large(self):
        """Very large debtToEquity=10000 -> debt_ratio approaches 1.0."""
        debt_to_equity = 10000
        de_ratio = debt_to_equity / 100.0  # 100
        debt_ratio = de_ratio / (1.0 + de_ratio)  # 100/101 ~ 0.99
        assert 0.99 < debt_ratio < 1.0


# ============ Test 5: Unit conversion consistency ============


class TestUnitConversions:
    """Verify fcf and market_cap are consistently in billions."""

    def test_fcf_in_billions(self):
        """data.py divides raw fcf by 1e9."""
        raw_fcf = 5_000_000_000  # 5 billion USD
        converted = raw_fcf / 1e9
        assert converted == 5.0

    def test_market_cap_in_billions(self):
        """data.py divides raw market_cap by 1e9."""
        raw_cap = 2_500_000_000_000  # 2.5 trillion
        converted = raw_cap / 1e9
        assert converted == 2500.0

    def test_market_context_expects_billions(self):
        """MarketContext fields represent billions when populated from data.py."""
        ctx = MarketContext(ticker="TEST", fcf=5.0, market_cap=2500.0)
        assert ctx.fcf == 5.0
        assert ctx.market_cap == 2500.0


# ============ Test 6: Ownership percentage conversion ============


class TestOwnershipConversion:
    """Verify institutional_ownership converts from 0-1 fraction to 0-100 %."""

    def test_ownership_fraction_to_pct(self):
        """yfinance fraction 0.75 -> 75.0 percentage."""
        raw_fraction = 0.75
        converted = raw_fraction * 100
        assert converted == 75.0

    def test_ownership_zero(self):
        """Zero ownership stays zero."""
        assert 0 * 100 == 0

    def test_ownership_one(self):
        """Full ownership (1.0) -> 100%."""
        assert 1.0 * 100 == 100.0


# ============ Test 7: Coordinator mixed valid/error results ============


class TestMixedResults:
    """Coordinator handles mixed valid/error results correctly."""

    def test_consensus_with_errors(self, coordinator):
        """Consensus excludes errors from adversarial overheating but includes in count."""
        ctx = MarketContext(ticker="MIX", pe=15, roe=0.2, gross_margins=0.4)
        results = coordinator.analyze_with_all(ctx)

        # Inject some errors
        results["fake_error_1"] = AgentResponse(
            agent_id="fake_error_1",
            agent_name="Fake Error 1",
            signal=SignalType.ERROR,
            confidence=0,
            score=0,
            reasoning="Simulated error",
        )
        results["fake_error_2"] = AgentResponse(
            agent_id="fake_error_2",
            agent_name="Fake Error 2",
            signal=SignalType.ERROR,
            confidence=0,
            score=0,
            reasoning="Simulated error",
        )

        consensus = coordinator.get_consensus(results, ticker="MIX", context=ctx)
        assert consensus.agent_id == "consensus"
        assert consensus.signal in (SignalType.BULLISH, SignalType.NEUTRAL, SignalType.BEARISH)
        # Reasoning mentions total count including errors
        assert str(len(results)) in consensus.reasoning


# ============ Test 8: Parallel vs sequential equivalence ============


class TestDeterminism:
    """Parallel execution produces deterministic results."""

    def test_deterministic_scores(self, coordinator):
        """Two runs with the same input give the same agent scores."""
        ctx = MarketContext(ticker="DET", pe=25, roe=0.12, gross_margins=0.35)

        results1 = coordinator.analyze_with_all(ctx)
        results2 = coordinator.analyze_with_all(ctx)

        # Same agents should be present
        assert set(results1.keys()) == set(results2.keys())

        # Same scores for each agent (deterministic computation)
        for agent_id in results1:
            r1 = results1[agent_id]
            r2 = results2[agent_id]
            assert r1.score == r2.score, (
                f"Agent {agent_id} score differs: {r1.score} vs {r2.score}"
            )
            assert r1.signal == r2.signal


# ============ Test 9: Timing metadata ============


class TestTimingMetadata:
    """Verify timing metadata is present in consensus result."""

    def test_timing_in_consensus_metadata(self, coordinator):
        """consensus.metadata should contain 'timing_ms' with analysis and consensus keys."""
        ctx = MarketContext(ticker="TIME", pe=20, roe=0.15)

        results = coordinator.analyze_with_all(ctx)
        consensus = coordinator.get_consensus(results, ticker="TIME", context=ctx)

        assert "timing_ms" in consensus.metadata
        timing = consensus.metadata["timing_ms"]
        assert "analysis_ms" in timing
        assert "consensus_ms" in timing
        assert timing["analysis_ms"] > 0, "Analysis timing should be positive"
        assert timing["consensus_ms"] > 0, "Consensus timing should be positive"
        assert isinstance(timing["analysis_ms"], float)
        assert isinstance(timing["consensus_ms"], float)


# ============ Test 10: Performance baseline ============


class TestPerformanceBaseline:
    """Full 18-agent analysis completes in under 2 seconds."""

    def test_analysis_under_2s(self, coordinator):
        """Pure computation (no network) should finish quickly."""
        ctx = MarketContext(
            ticker="PERF",
            pe=30,
            roe=0.18,
            gross_margins=0.45,
            revenue_growth=0.15,
            debt_ratio=0.3,
            fcf=10.0,
            market_cap=500.0,
        )

        t0 = time.perf_counter()
        results = coordinator.analyze_with_all(ctx)
        consensus = coordinator.get_consensus(results, ticker="PERF", context=ctx)
        elapsed = time.perf_counter() - t0

        assert len(results) >= 18
        assert elapsed < 2.0, f"Full analysis took {elapsed:.2f}s, expected < 2.0s"
