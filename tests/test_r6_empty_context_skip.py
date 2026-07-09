# -*- coding: utf-8 -*-
"""R6 groundwork (2026-07-09): predictions made against an empty
MarketContext (data_source="none" -- every data provider failed) must not
be persisted to the LearningEngine, since they aren't real
signal-conditioned judgments and would quietly pollute R6's future
calibration sample. Discovered while setting up a real watchlist cron
job: yfinance rate-limiting caused most tickers in a run to silently fall
back to an empty context, and those "predictions" were still being
recorded exactly like real ones.

Only the *learning* record is suppressed -- the analysis result itself
(and the >30-day outcome-resolution sweep, which is unrelated to today's
context quality) are unaffected.
"""

from unittest.mock import patch, MagicMock

from augur.consensus.engine import ConsensusEngine
from augur.personas.base import AgentResponse, MarketContext, SignalType


def _agent(agent_id: str, score: float = 6.0, signal: SignalType = SignalType.BULLISH) -> AgentResponse:
    return AgentResponse(
        agent_id=agent_id, agent_name=agent_id, signal=signal,
        score=score, confidence=0.6, reasoning="", key_findings=[], risks=[],
    )


def _make_results() -> dict:
    return {"a": _agent("a", 3.0), "b": _agent("b", 6.0), "c": _agent("c", 9.0)}


def _run_engine(ctx):
    engine = ConsensusEngine()
    with patch("augur.consensus.weighting.fetch_macro_features",
               return_value={"vix": 18.0, "trend": "bull", "regime": "BULL_LOW_VOL"}):
        return engine.compute(_make_results(), ticker="TEST", context=ctx)


class TestEmptyContextSkipsRecording:
    def test_empty_context_does_not_record_predictions(self):
        ctx = MarketContext(ticker="TEST")
        setattr(ctx, "data_source", "none")

        with patch("augur.registry._get_learning_engine") as mock_get_le, \
             patch("augur.registry._check_and_record_outcomes") as mock_check:
            mock_le = MagicMock()
            mock_get_le.return_value = mock_le
            _run_engine(ctx)

        mock_le.record_prediction.assert_not_called()

    def test_error_context_does_not_record_predictions(self):
        """data_source="error" (e.g. a too-long/malformed ticker rejected by
        input validation before any provider is even tried -- confirmed via
        a real `augur analyze NOTAREALTICKERXYZ` invocation) must be
        excluded the same way as data_source="none"."""
        ctx = MarketContext(ticker="TEST")
        setattr(ctx, "data_source", "error")

        with patch("augur.registry._get_learning_engine") as mock_get_le, \
             patch("augur.registry._check_and_record_outcomes"):
            mock_le = MagicMock()
            mock_get_le.return_value = mock_le
            _run_engine(ctx)

        mock_le.record_prediction.assert_not_called()

    def test_empty_context_still_runs_outcome_resolution_sweep(self):
        """Checking whether >30-day-old predictions for this ticker should
        resolve is unrelated to whether *today's* context is empty -- it
        must still run."""
        ctx = MarketContext(ticker="TEST")
        setattr(ctx, "data_source", "none")

        with patch("augur.registry._get_learning_engine") as mock_get_le, \
             patch("augur.registry._check_and_record_outcomes") as mock_check:
            mock_get_le.return_value = MagicMock()
            _run_engine(ctx)

        mock_check.assert_called_once()

    def test_real_context_still_records_predictions(self):
        """Backward compat: a normal, real data_source must not be affected."""
        ctx = MarketContext(ticker="TEST", price=150.0)
        setattr(ctx, "data_source", "yfinance")

        with patch("augur.registry._get_learning_engine") as mock_get_le, \
             patch("augur.registry._check_and_record_outcomes"):
            mock_le = MagicMock()
            mock_get_le.return_value = mock_le
            _run_engine(ctx)

        assert mock_le.record_prediction.call_count == 3  # one per agent

    def test_context_with_no_data_source_attribute_still_records(self):
        """A context that never went through fetch_market_context() (e.g.
        manually constructed with real user-supplied metrics) has no
        data_source attribute at all -- must not be treated as empty."""
        ctx = MarketContext(ticker="TEST", price=150.0, pe=25.0)

        with patch("augur.registry._get_learning_engine") as mock_get_le, \
             patch("augur.registry._check_and_record_outcomes"):
            mock_le = MagicMock()
            mock_get_le.return_value = mock_le
            _run_engine(ctx)

        assert mock_le.record_prediction.call_count == 3

    def test_none_context_still_records(self):
        """context=None (some callers don't pass one) must not be treated
        as empty -- there's no way to tell, so preserve prior behavior."""
        with patch("augur.registry._get_learning_engine") as mock_get_le, \
             patch("augur.registry._check_and_record_outcomes"):
            mock_le = MagicMock()
            mock_get_le.return_value = mock_le
            _run_engine(None)

        assert mock_le.record_prediction.call_count == 3


class TestCronEmptyContextTagging:
    """cron.py's own exception-fallback path (fetch_market_context itself
    raised, rather than gracefully returning data_source="none") must tag
    the fallback context the same way when there's truly no data at all."""

    def test_fallback_with_no_manual_overrides_tagged_empty(self):
        from augur.cron import run_watchlist_analysis

        config = {"watchlist": [{"ticker": "AAPL"}], "notifications": {"alert_threshold": 0}}
        mock_results = {"agent1": MagicMock(agent_name="Test", signal=MagicMock(value="bullish"), score=7.0)}
        captured_ctx = {}

        def fake_get_consensus(results, ticker="", context=None):
            captured_ctx["ctx"] = context
            c = MagicMock()
            c.signal = MagicMock(value="bullish")
            c.score = 7.0
            c.confidence = 0.75
            c.key_findings = []
            c.risks = []
            return c

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", side_effect=RuntimeError("network down")), \
             patch("augur.history.save_analysis"), \
             patch("augur.cron._send_notifications"), \
             patch("augur.registry.resolve_pending_outcomes", return_value={"resolved": 0, "failed": 0, "still_pending": 0}):
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.return_value = mock_results
            coord_inst.get_consensus.side_effect = fake_get_consensus

            run_watchlist_analysis()

        assert getattr(captured_ctx["ctx"], "data_source", None) == "none"

    def test_fallback_with_manual_overrides_not_tagged_empty(self):
        from augur.cron import run_watchlist_analysis

        config = {
            "watchlist": [{"ticker": "AAPL", "pe": 30.0, "roe": 0.5}],
            "notifications": {"alert_threshold": 0},
        }
        mock_results = {"agent1": MagicMock(agent_name="Test", signal=MagicMock(value="bullish"), score=7.0)}
        captured_ctx = {}

        def fake_get_consensus(results, ticker="", context=None):
            captured_ctx["ctx"] = context
            c = MagicMock()
            c.signal = MagicMock(value="bullish")
            c.score = 7.0
            c.confidence = 0.75
            c.key_findings = []
            c.risks = []
            return c

        with patch("augur.cron.load_watchlist", return_value=config), \
             patch("augur.registry.AgentRegistry"), \
             patch("augur.registry.DecisionCoordinator") as MockCoord, \
             patch("augur.data.fetch_market_context", side_effect=RuntimeError("network down")), \
             patch("augur.history.save_analysis"), \
             patch("augur.cron._send_notifications"), \
             patch("augur.registry.resolve_pending_outcomes", return_value={"resolved": 0, "failed": 0, "still_pending": 0}):
            coord_inst = MockCoord.return_value
            coord_inst.analyze_with_all.return_value = mock_results
            coord_inst.get_consensus.side_effect = fake_get_consensus

            run_watchlist_analysis()

        ctx = captured_ctx["ctx"]
        assert getattr(ctx, "data_source", None) != "none"
        assert ctx.pe == 30.0
