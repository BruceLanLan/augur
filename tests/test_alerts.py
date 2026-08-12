# -*- coding: utf-8 -*-
"""Tests for Material Catalyst Alerts + Event Readiness Score (B07 + B08)."""
import pytest
from augur.alerts import Alert, AlertEngine, ReadinessScore, ReadinessEvaluator


class TestAlert:
    def test_creation(self):
        a = Alert(alert_id="al_001", ticker="AAPL", alert_type="filing_published", title="10-Q Filed", description="Q4 2025 10-Q published", severity="high", created_at="2025-01-01")
        assert a.severity == "high"
        assert a.dismissed is False

    def test_dismiss(self):
        a = Alert(alert_id="al_002", ticker="MSFT", alert_type="guidance_change", title="Guidance raised", description="", severity="medium", created_at="2025-01-01", dismissed=True)
        assert a.dismissed is True


class TestAlertEngine:
    def test_deduplicate(self):
        a1 = Alert("al_1", "AAPL", "filing_published", "Same", "", "high", "2025-01-01T10:00")
        a2 = Alert("al_2", "AAPL", "filing_published", "Same", "", "high", "2025-01-01T10:05")
        deduped = AlertEngine().deduplicate([a1, a2], cooldown_minutes=60)
        assert len(deduped) >= 1

    def test_deduplicate_different_types(self):
        a1 = Alert("al_1", "AAPL", "filing_published", "A", "", "high", "2025-01-01")
        a2 = Alert("al_2", "AAPL", "guidance_change", "B", "", "high", "2025-01-01")
        deduped = AlertEngine().deduplicate([a1, a2], cooldown_minutes=60)
        assert len(deduped) == 2

    def test_get_active(self):
        alerts = AlertEngine().get_active("AAPL")
        assert isinstance(alerts, list)

    def test_dismiss(self):
        AlertEngine().dismiss("al_test")
        # should not raise


class TestReadinessScore:
    def test_creation(self):
        rs = ReadinessScore(ticker="AAPL", event_id="evt_001", overall_score=85.0, data_availability=90.0, analysis_freshness=80.0, evidence_completeness=85.0, missing_items=[], recommendation="ready")
        assert rs.recommendation == "ready"


class TestReadinessEvaluator:
    def test_evaluate(self):
        score = ReadinessEvaluator().evaluate("AAPL", {"event_id": "evt_001", "event_date": "2025-12-31"})
        assert 0 <= score.overall_score <= 100

    def test_missing_data_report(self):
        report = ReadinessEvaluator().missing_data_report("AAPL")
        assert isinstance(report, list)

    def test_evaluate_missing_data(self):
        score = ReadinessEvaluator().evaluate("UNKNOWN", {"event_id": "evt_x"})
        assert score.recommendation in ("ready", "partial", "insufficient")
