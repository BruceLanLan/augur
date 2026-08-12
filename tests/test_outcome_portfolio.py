# -*- coding: utf-8 -*-
"""Tests for Outcome Tracker + Portfolio Risk modules."""
import pytest
from augur.outcome_tracker import OutcomeTracker, DecisionScore, OutcomeReport
from augur.portfolio_risk import PortfolioRiskAnalyzer, PortfolioRiskReport, PositionRisk


class TestOutcomeTracker:
    def test_record_and_report(self):
        ot = OutcomeTracker()
        ot.record(DecisionScore("d1", "buy", "correct", pnl_pct=8.5))
        ot.record(DecisionScore("d2", "sell", "incorrect", pnl_pct=-3.2))
        ot.record(DecisionScore("d3", "hold", "pending"))
        r = ot.report()
        assert r.total_decisions == 3
        assert r.resolved == 2
        assert r.pending == 1
        assert r.win_rate == 0.5

    def test_by_action_stats(self):
        ot = OutcomeTracker()
        ot.record(DecisionScore("d1", "buy", "correct"))
        ot.record(DecisionScore("d2", "buy", "incorrect"))
        r = ot.report()
        assert r.by_action["buy"]["correct"] == 1
        assert r.by_action["buy"]["incorrect"] == 1

    def test_empty_report(self):
        r = OutcomeTracker().report()
        assert r.total_decisions == 0
        assert r.win_rate == 0.0

    def test_avg_pnl(self):
        ot = OutcomeTracker()
        ot.record(DecisionScore("d1", "buy", "correct", pnl_pct=10.0))
        ot.record(DecisionScore("d2", "buy", "correct", pnl_pct=20.0))
        r = ot.report()
        assert r.avg_pnl_pct == pytest.approx(15.0)


class TestPortfolioRiskAnalyzer:
    def test_hhi_concentration(self):
        analyzer = PortfolioRiskAnalyzer()
        r = analyzer.analyze({"AAPL": 0.3, "MSFT": 0.25, "GOOG": 0.2, "AMZN": 0.15, "NVDA": 0.10})
        assert r.concentration_hhi > 0
        assert r.max_position_weight == 0.3
        assert 0 <= r.diversification_score <= 1

    def test_single_position_concentrated(self):
        r = PortfolioRiskAnalyzer().analyze({"AAPL": 1.0})
        assert r.max_position_weight == 1.0
        assert r.risk_summary == "concentrated — largest position exceeds 40%"

    def test_empty_portfolio(self):
        r = PortfolioRiskAnalyzer().analyze({})
        assert r.risk_summary == "empty portfolio"

    def test_weight_normalization(self):
        # Weights sum > 1 should be normalized
        r = PortfolioRiskAnalyzer().analyze({"AAPL": 0.5, "MSFT": 0.5})
        assert r.max_position_weight == 0.5
        assert len(r.positions) == 2
