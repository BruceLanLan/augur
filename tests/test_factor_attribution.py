# -*- coding: utf-8 -*-
"""Tests for augur.backtest.compute_factor_cross_sectional_ic (B2 from
docs/FUTURE_DIRECTIONS_BRAINSTORM_2026-07.md).

Uses fake duck-typed agents (agent_id + analyze()) rather than the real 18
personas or real fetch_ticker_replay_records() network calls -- this
function's job is the cross-sectional grouping / rank-IC / split-half
aggregation, which is pure computation over already-built records; the
real-persona, real-network integration is exercised manually via
scripts/factor_attribution.py per this project's established convention for
this class of research script (see fetch_ticker_replay_records,
compute_cross_sectional_regime_ic -- neither has pytest coverage either,
for the same reason).
"""

from augur.backtest import (
    _REPLAY_RECORD_FIELDS,
    _record_to_market_context,
    _signed_agent_scores,
    compute_factor_cross_sectional_ic,
)
from augur.personas.base import AgentResponse, SignalType


class TestReplayRecordFieldsShared:
    """_signed_agent_scores and _record_to_market_context used to each hardcode
    their own copy of this field list -- exactly the kind of drift that caused
    the insider_ownership/institutional_ownership gap documented in
    docs/FACTOR_ATTRIBUTION_FINDINGS_2026-07.md. Both now read from one
    module-level constant; this guards against a future edit reintroducing
    two copies that silently diverge."""

    def test_record_to_market_context_uses_the_shared_field_list(self):
        record = {f: 42.0 for f in _REPLAY_RECORD_FIELDS}
        record["date"] = "2026-01-01"
        ctx = _record_to_market_context("AAPL", record)
        for field in _REPLAY_RECORD_FIELDS:
            assert getattr(ctx, field) == 42.0

    def test_signed_agent_scores_uses_the_shared_field_list(self):
        seen_ctx = {}

        class _CapturingAgent:
            agent_id = "capture"

            def analyze(self, ctx):
                seen_ctx["ctx"] = ctx
                return AgentResponse(
                    agent_id="capture", agent_name="capture", signal=SignalType.NEUTRAL,
                    confidence=0.5, score=5.0, reasoning="",
                )

        record = {f: 7.0 for f in _REPLAY_RECORD_FIELDS}
        _signed_agent_scores("AAPL", record, [_CapturingAgent()])
        for field in _REPLAY_RECORD_FIELDS:
            assert getattr(seen_ctx["ctx"], field) == 7.0

    def test_a_field_not_in_the_shared_list_is_not_populated(self):
        record = {"insider_ownership": 99.0, "date": "2026-01-01"}
        ctx = _record_to_market_context("AAPL", record)
        assert ctx.insider_ownership == 0  # MarketContext default, not 99.0


class _FakeAgent:
    """Duck-typed agent: only needs .agent_id and .analyze(ctx) -> AgentResponse,
    the exact interface compute_factor_cross_sectional_ic actually uses."""

    def __init__(self, agent_id, factor_fn=None, raises=False):
        self.agent_id = agent_id
        self._factor_fn = factor_fn or (lambda ctx: {})
        self._raises = raises

    def analyze(self, ctx):
        if self._raises:
            raise RuntimeError("boom")
        return AgentResponse(
            agent_id=self.agent_id,
            agent_name=self.agent_id,
            signal=SignalType.NEUTRAL,
            confidence=0.5,
            score=5.0,
            reasoning="",
            metadata={"factors": self._factor_fn(ctx)},
        )


def _records_for(ticker, dates, pe_by_date, return_by_date):
    return [
        {"date": d, "pe": pe_by_date[d], "actual_return_20d": return_by_date[d]}
        for d in dates
    ]


class TestBasicCrossSectionalIC:
    def test_perfectly_correlated_factor_gets_ic_near_one(self):
        # 5 tickers/day, factor value == pe, and pe perfectly rank-orders
        # with the return on every day -> IC should be ~1.0.
        agent = _FakeAgent("quant", factor_fn=lambda ctx: {"value_factor": ctx.pe})
        dates = ["2026-01-01", "2026-01-02"]
        records_by_ticker = {}
        for i, ticker in enumerate(["A", "B", "C", "D", "E"]):
            pe_by_date = {d: float(i) for d in dates}
            ret_by_date = {d: float(i) * 0.01 for d in dates}
            records_by_ticker[ticker] = _records_for(ticker, dates, pe_by_date, ret_by_date)

        result = compute_factor_cross_sectional_ic(records_by_ticker, [agent], min_tickers_per_day=5)
        key = "quant.value_factor"
        assert key in result["per_factor"]
        assert result["per_factor"][key]["ic_mean"] > 0.9
        assert result["per_factor"][key]["n_days"] == 2

    def test_inverted_factor_gets_negative_ic(self):
        agent = _FakeAgent("quant", factor_fn=lambda ctx: {"value_factor": ctx.pe})
        dates = ["2026-01-01"]
        records_by_ticker = {}
        for i, ticker in enumerate(["A", "B", "C", "D", "E"]):
            # Higher pe -> lower return (inverted relationship)
            pe_by_date = {dates[0]: float(i)}
            ret_by_date = {dates[0]: -float(i) * 0.01}
            records_by_ticker[ticker] = _records_for(ticker, dates, pe_by_date, ret_by_date)

        result = compute_factor_cross_sectional_ic(records_by_ticker, [agent], min_tickers_per_day=5)
        assert result["per_factor"]["quant.value_factor"]["ic_mean"] < -0.9


class TestThinDayFiltering:
    def test_days_below_min_tickers_are_skipped_and_counted(self):
        agent = _FakeAgent("quant", factor_fn=lambda ctx: {"f": ctx.pe})
        records_by_ticker = {
            "A": [{"date": "2026-01-01", "pe": 1.0, "actual_return_20d": 0.01}],
            "B": [{"date": "2026-01-01", "pe": 2.0, "actual_return_20d": 0.02}],
        }
        result = compute_factor_cross_sectional_ic(records_by_ticker, [agent], min_tickers_per_day=5)
        assert result["n_days_total"] == 0
        assert result["n_days_skipped_thin"] == 1
        assert result["per_factor"] == {}


class TestNamespacing:
    def test_same_factor_name_across_agents_kept_separate(self):
        agent_a = _FakeAgent("agent_a", factor_fn=lambda ctx: {"quality": ctx.pe})
        agent_b = _FakeAgent("agent_b", factor_fn=lambda ctx: {"quality": -ctx.pe})
        dates = ["2026-01-01"]
        records_by_ticker = {}
        for i, ticker in enumerate(["A", "B", "C", "D", "E"]):
            records_by_ticker[ticker] = [
                {"date": dates[0], "pe": float(i), "actual_return_20d": float(i) * 0.01}
            ]

        result = compute_factor_cross_sectional_ic(
            records_by_ticker, [agent_a, agent_b], min_tickers_per_day=5
        )
        assert "agent_a.quality" in result["per_factor"]
        assert "agent_b.quality" in result["per_factor"]
        # Opposite-signed formulas on the same underlying data -> opposite IC signs
        assert result["per_factor"]["agent_a.quality"]["ic_mean"] > 0
        assert result["per_factor"]["agent_b.quality"]["ic_mean"] < 0


class TestNonNumericFactorsFiltered:
    def test_string_and_bool_factor_values_are_skipped(self):
        agent = _FakeAgent(
            "quant",
            factor_fn=lambda ctx: {"numeric": ctx.pe, "label": "high", "flag": True},
        )
        dates = ["2026-01-01"]
        records_by_ticker = {}
        for i, ticker in enumerate(["A", "B", "C", "D", "E"]):
            records_by_ticker[ticker] = [
                {"date": dates[0], "pe": float(i), "actual_return_20d": float(i) * 0.01}
            ]
        result = compute_factor_cross_sectional_ic(records_by_ticker, [agent], min_tickers_per_day=5)
        assert "quant.numeric" in result["per_factor"]
        assert "quant.label" not in result["per_factor"]
        assert "quant.flag" not in result["per_factor"]


class TestAgentFailureIsolation:
    def test_one_agent_raising_does_not_break_others(self):
        good = _FakeAgent("good", factor_fn=lambda ctx: {"f": ctx.pe})
        bad = _FakeAgent("bad", raises=True)
        dates = ["2026-01-01"]
        records_by_ticker = {}
        for i, ticker in enumerate(["A", "B", "C", "D", "E"]):
            records_by_ticker[ticker] = [
                {"date": dates[0], "pe": float(i), "actual_return_20d": float(i) * 0.01}
            ]
        result = compute_factor_cross_sectional_ic(records_by_ticker, [good, bad], min_tickers_per_day=5)
        assert "good.f" in result["per_factor"]
        assert not any(k.startswith("bad.") for k in result["per_factor"])


class TestSplitHalfStability:
    def _build(self, agent, per_day_pe, per_day_ret, min_tickers=5):
        records_by_ticker = {}
        tickers = ["A", "B", "C", "D", "E"]
        for i, ticker in enumerate(tickers):
            records_by_ticker[ticker] = [
                {"date": d, "pe": per_day_pe[d][i], "actual_return_20d": per_day_ret[d][i]}
                for d in per_day_pe
            ]
        return compute_factor_cross_sectional_ic(records_by_ticker, [agent], min_tickers_per_day=min_tickers)

    def test_consistent_sign_both_halves_is_stable(self):
        agent = _FakeAgent("quant", factor_fn=lambda ctx: {"f": ctx.pe})
        dates = [f"2026-01-{d:02d}" for d in range(1, 9)]  # 8 days -> 4/4 split
        per_day_pe = {d: [0.0, 1.0, 2.0, 3.0, 4.0] for d in dates}
        # Same positive relationship (pe rank == return rank) on every day
        per_day_ret = {d: [0.0, 0.01, 0.02, 0.03, 0.04] for d in dates}
        result = self._build(agent, per_day_pe, per_day_ret)
        stats = result["per_factor"]["quant.f"]
        assert stats["split_half_stable"] is True
        assert stats["first_half_ic"] > 0
        assert stats["second_half_ic"] > 0

    def test_sign_flip_between_halves_is_unstable(self):
        agent = _FakeAgent("quant", factor_fn=lambda ctx: {"f": ctx.pe})
        first_half_dates = [f"2026-01-{d:02d}" for d in range(1, 5)]
        second_half_dates = [f"2026-01-{d:02d}" for d in range(5, 9)]
        per_day_pe = {}
        per_day_ret = {}
        for d in first_half_dates:
            per_day_pe[d] = [0.0, 1.0, 2.0, 3.0, 4.0]
            per_day_ret[d] = [0.0, 0.01, 0.02, 0.03, 0.04]  # positive relationship
        for d in second_half_dates:
            per_day_pe[d] = [0.0, 1.0, 2.0, 3.0, 4.0]
            per_day_ret[d] = [0.04, 0.03, 0.02, 0.01, 0.0]  # inverted relationship
        result = self._build(agent, per_day_pe, per_day_ret)
        stats = result["per_factor"]["quant.f"]
        assert stats["split_half_stable"] is False
        assert stats["first_half_ic"] > 0
        assert stats["second_half_ic"] < 0

    def test_below_threshold_ic_in_either_half_is_unstable(self):
        agent = _FakeAgent("quant", factor_fn=lambda ctx: {"f": ctx.pe})
        dates = [f"2026-01-{d:02d}" for d in range(1, 9)]
        per_day_pe = {d: [0.0, 1.0, 2.0, 3.0, 4.0] for d in dates}
        # No relationship between pe and return at all -> IC ~ 0 in both halves
        per_day_ret = {d: [0.0, 0.0, 0.0, 0.0, 0.0] for d in dates}
        result = self._build(agent, per_day_pe, per_day_ret)
        stats = result["per_factor"]["quant.f"]
        assert stats["split_half_stable"] is False

    def test_fewer_than_three_days_in_a_half_is_unstable(self):
        agent = _FakeAgent("quant", factor_fn=lambda ctx: {"f": ctx.pe})
        dates = [f"2026-01-{d:02d}" for d in range(1, 4)]  # 3 days -> 1/2 split
        per_day_pe = {d: [0.0, 1.0, 2.0, 3.0, 4.0] for d in dates}
        per_day_ret = {d: [0.0, 0.01, 0.02, 0.03, 0.04] for d in dates}
        result = self._build(agent, per_day_pe, per_day_ret)
        stats = result["per_factor"]["quant.f"]
        assert stats["split_half_stable"] is False
