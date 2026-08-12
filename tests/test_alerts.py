# -*- coding: utf-8 -*-
"""Tests for augur.alerts — Material Catalyst Alerts + Event Readiness Score."""

from datetime import datetime, timezone, timedelta

import pytest

from augur.alerts import (
    Alert,
    AlertEngine,
    ReadinessEvaluator,
    ReadinessScore,
    _generate_alert_id,
    _now_iso,
    _severity_for_filing,
    _severity_for_type,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_filing(**overrides):
    defaults = {
        "filing_type": "10-Q",
        "overall_assessment": "minor_changes",
        "material_change_count": 2,
        "run_id": "run_abc123",
    }
    defaults.update(overrides)
    return defaults


def _make_guidance_change(**overrides):
    defaults = {
        "metric": "revenue_guidance",
        "direction": "raised",
        "previous_range": (90_000, 95_000),
        "new_range": (95_000, 100_000),
    }
    defaults.update(overrides)
    return defaults


def _make_insider_cluster(**overrides):
    defaults = {
        "direction": "selling",
        "participant_count": 4,
        "total_value": 5_000_000,
        "period_days": 14,
    }
    defaults.update(overrides)
    return defaults


def _make_thesis_delta(**overrides):
    defaults = {
        "thesis_id": "th_AAPL_abc12345",
        "overall_assessment": "refuted",
        "falsification_triggered": ["services revenue growth below 5%"],
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# Alert dataclass
# ===========================================================================


class TestAlert:
    """Tests for the Alert dataclass."""

    def test_alert_creation_defaults(self):
        """Alert auto-generates created_at and alert_id when omitted."""
        a = Alert(
            ticker="AAPL",
            alert_type="filing_published",
            title="AAPL 10-K filed",
            description="Annual report published.",
            severity="high",
        )
        assert a.alert_id.startswith("al_")
        assert len(a.alert_id) == 11  # al_ + 8 hex chars
        assert a.created_at  # non-empty ISO timestamp
        assert not a.dismissed
        assert a.cooldown_until == ""

    def test_alert_id_is_deterministic(self):
        """Same ticker + type + title yields the same alert_id."""
        a1 = Alert(
            ticker="AAPL",
            alert_type="filing_published",
            title="AAPL 10-K filed",
            description="x",
        )
        a2 = Alert(
            ticker="AAPL",
            alert_type="filing_published",
            title="AAPL 10-K filed",
            description="y",
        )
        assert a1.alert_id == a2.alert_id

    def test_alert_id_differs_by_type(self):
        """Different alert_type yields different alert_id."""
        a1 = Alert(
            ticker="AAPL",
            alert_type="filing_published",
            title="Test",
            description="x",
        )
        a2 = Alert(
            ticker="AAPL",
            alert_type="guidance_change",
            title="Test",
            description="x",
        )
        assert a1.alert_id != a2.alert_id


# ===========================================================================
# AlertEngine — Filing alerts
# ===========================================================================


class TestFilingAlerts:
    """Tests for AlertEngine.check_filing_alerts."""

    def test_filing_published_alert_created(self):
        """A filing always produces at least one alert."""
        engine = AlertEngine()
        alerts = engine.check_filing_alerts("AAPL", _make_filing())
        assert len(alerts) == 1
        a = alerts[0]
        assert a.alert_type == "filing_published"
        assert a.ticker == "AAPL"
        assert "10-Q" in a.title

    def test_filing_significant_changes_is_critical(self):
        """Significant changes yield a critical severity alert."""
        engine = AlertEngine()
        alerts = engine.check_filing_alerts(
            "MSFT",
            _make_filing(
                overall_assessment="significant_changes",
                material_change_count=5,
            ),
        )
        assert alerts[0].severity == "critical"

    def test_filing_no_material_changes_is_low(self):
        """A filing with no material changes gets low severity."""
        engine = AlertEngine()
        alerts = engine.check_filing_alerts(
            "IBM",
            _make_filing(overall_assessment="no_material_changes", material_change_count=0),
        )
        assert alerts[0].severity == "low"


# ===========================================================================
# AlertEngine — Guidance alerts
# ===========================================================================


class TestGuidanceAlerts:
    """Tests for AlertEngine.check_guidance_alerts."""

    def test_raised_guidance_is_high(self):
        engine = AlertEngine()
        alerts = engine.check_guidance_alerts(
            "AAPL",
            [_make_guidance_change(direction="raised")],
        )
        assert len(alerts) == 1
        assert alerts[0].severity == "high"
        assert "raised" in alerts[0].title.lower()

    def test_lowered_guidance_is_critical(self):
        engine = AlertEngine()
        alerts = engine.check_guidance_alerts(
            "AAPL",
            [_make_guidance_change(direction="lowered")],
        )
        assert alerts[0].severity == "critical"
        assert "lowered" in alerts[0].title.lower()

    def test_withdrawn_guidance_is_critical(self):
        engine = AlertEngine()
        alerts = engine.check_guidance_alerts(
            "AAPL",
            [_make_guidance_change(
                direction="withdrawn",
                previous_range=(90_000, 95_000),
                new_range=None,
            )],
        )
        assert alerts[0].severity == "critical"
        assert "withdrew" in alerts[0].title.lower()


# ===========================================================================
# AlertEngine — Insider alerts
# ===========================================================================


class TestInsiderAlerts:
    """Tests for AlertEngine.check_insider_alerts."""

    def test_insider_cluster_produces_alert(self):
        engine = AlertEngine()
        alerts = engine.check_insider_alerts(
            "AAPL",
            [_make_insider_cluster()],
        )
        assert len(alerts) == 1
        assert alerts[0].alert_type == "insider_cluster"
        assert "4 insiders" in alerts[0].title

    def test_single_insider_ignored(self):
        """A cluster with only 1 participant is not a cluster — no alert."""
        engine = AlertEngine()
        alerts = engine.check_insider_alerts(
            "AAPL",
            [_make_insider_cluster(participant_count=1)],
        )
        assert len(alerts) == 0

    def test_buying_cluster_is_high_severity(self):
        engine = AlertEngine()
        alerts = engine.check_insider_alerts(
            "AAPL",
            [_make_insider_cluster(direction="buying", participant_count=3)],
        )
        assert alerts[0].severity == "high"


# ===========================================================================
# AlertEngine — Thesis alerts
# ===========================================================================


class TestThesisAlerts:
    """Tests for AlertEngine.check_thesis_alerts."""

    def test_refuted_thesis_is_critical(self):
        engine = AlertEngine()
        alerts = engine.check_thesis_alerts(
            "AAPL",
            [_make_thesis_delta(overall_assessment="refuted")],
        )
        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert "refuted" in alerts[0].title.lower()

    def test_weakened_thesis_is_high(self):
        engine = AlertEngine()
        alerts = engine.check_thesis_alerts(
            "AAPL",
            [_make_thesis_delta(overall_assessment="weakened")],
        )
        assert alerts[0].severity == "high"
        assert "weakened" in alerts[0].title.lower()

    def test_strengthened_thesis_is_low(self):
        engine = AlertEngine()
        alerts = engine.check_thesis_alerts(
            "AAPL",
            [_make_thesis_delta(overall_assessment="strengthened")],
        )
        assert alerts[0].severity == "low"

    def test_intact_thesis_produces_no_alert(self):
        engine = AlertEngine()
        alerts = engine.check_thesis_alerts(
            "AAPL",
            [_make_thesis_delta(overall_assessment="intact")],
        )
        assert len(alerts) == 0


# ===========================================================================
# AlertEngine — Lifecycle
# ===========================================================================


class TestAlertLifecycle:
    """Tests for deduplicate, get_active, dismiss."""

    def test_deduplicate_blocks_same_ticker_and_type(self):
        engine = AlertEngine()
        existing = Alert(
            ticker="AAPL",
            alert_type="filing_published",
            title="AAPL 10-Q filed",
            description="Old filing.",
            severity="medium",
        )
        engine._alerts.append(existing)

        candidates = engine.check_filing_alerts("AAPL", _make_filing())
        deduped = engine.deduplicate(candidates)
        assert len(deduped) == 0  # blocked by existing active alert

    def test_deduplicate_allows_different_type(self):
        engine = AlertEngine()
        existing = Alert(
            ticker="AAPL",
            alert_type="filing_published",
            title="AAPL 10-Q filed",
            description="Old.",
            severity="medium",
        )
        engine._alerts.append(existing)

        candidates = engine.check_guidance_alerts(
            "AAPL",
            [_make_guidance_change(direction="raised")],
        )
        deduped = engine.deduplicate(candidates)
        assert len(deduped) == 1

    def test_deduplicate_allows_dismissed(self):
        engine = AlertEngine()
        existing = Alert(
            ticker="AAPL",
            alert_type="filing_published",
            title="AAPL 10-Q filed",
            description="Old.",
            severity="medium",
            dismissed=True,
        )
        engine._alerts.append(existing)

        candidates = engine.check_filing_alerts("AAPL", _make_filing())
        deduped = engine.deduplicate(candidates)
        assert len(deduped) == 1  # dismissed doesn't block

    def test_get_active_filters_by_ticker(self):
        engine = AlertEngine()
        engine._alerts = [
            Alert(ticker="AAPL", alert_type="filing_published",
                  title="A", description="a", severity="low"),
            Alert(ticker="MSFT", alert_type="filing_published",
                  title="B", description="b", severity="low"),
            Alert(ticker="AAPL", alert_type="guidance_change",
                  title="C", description="c", severity="low", dismissed=True),
        ]
        active = engine.get_active("AAPL")
        assert len(active) == 1
        assert active[0].ticker == "AAPL"

    def test_get_active_returns_all_when_ticker_none(self):
        engine = AlertEngine()
        engine._alerts = [
            Alert(ticker="AAPL", alert_type="filing_published",
                  title="A", description="a", severity="low"),
            Alert(ticker="MSFT", alert_type="filing_published",
                  title="B", description="b", severity="low"),
        ]
        assert len(engine.get_active()) == 2

    def test_dismiss_marks_alert(self):
        engine = AlertEngine()
        a = Alert(ticker="AAPL", alert_type="filing_published",
                  title="Test", description="x", severity="low")
        engine._alerts.append(a)

        assert engine.dismiss(a.alert_id) is True
        assert a.dismissed is True
        assert engine.get_active("AAPL") == []

    def test_dismiss_unknown_id_returns_false(self):
        engine = AlertEngine()
        assert engine.dismiss("al_nonexistent") is False


# ===========================================================================
# Helpers
# ===========================================================================


class TestHelpers:
    """Tests for module-level helpers."""

    def test_generate_alert_id_format(self):
        aid = _generate_alert_id("AAPL", "filing_published", "AAPL 10-K filed")
        assert aid.startswith("al_")
        assert len(aid) == 11

    def test_now_iso_returns_string(self):
        ts = _now_iso()
        assert isinstance(ts, str)
        assert "T" in ts

    def test_severity_for_type_mappings(self):
        assert _severity_for_type("filing_published") == "high"
        assert _severity_for_type("guidance_change") == "high"
        assert _severity_for_type("insider_cluster") == "medium"
        assert _severity_for_type("ownership_delta") == "medium"
        assert _severity_for_type("thesis_triggered") == "critical"
        assert _severity_for_type("disagreement_widened") == "medium"
        assert _severity_for_type("unknown_type") == "low"

    def test_severity_for_filing(self):
        assert _severity_for_filing("significant_changes", 10) == "critical"
        assert _severity_for_filing("minor_changes", 3) == "high"
        assert _severity_for_filing("minor_changes", 1) == "medium"
        assert _severity_for_filing("no_material_changes", 0) == "low"


# ===========================================================================
# ReadinessScore
# ===========================================================================


class TestReadinessScore:
    """Tests for the ReadinessScore dataclass."""

    def test_recommendation_ready(self):
        rs = ReadinessScore(
            ticker="AAPL",
            event_id="ev_001",
            overall_score=85.0,
        )
        assert rs.recommendation == "ready"

    def test_recommendation_partial(self):
        rs = ReadinessScore(
            ticker="AAPL",
            event_id="ev_001",
            overall_score=55.0,
        )
        assert rs.recommendation == "partial"

    def test_recommendation_insufficient(self):
        rs = ReadinessScore(
            ticker="AAPL",
            event_id="ev_001",
            overall_score=25.0,
        )
        assert rs.recommendation == "insufficient"


# ===========================================================================
# ReadinessEvaluator
# ===========================================================================


class TestReadinessEvaluator:
    """Tests for the ReadinessEvaluator class."""

    def _full_data(self) -> dict:
        return {
            "market_cap": 3_000_000_000_000,
            "revenue": 383_000_000_000,
            "net_income": 97_000_000_000,
            "eps_diluted": 6.12,
            "pe_ratio": 28.5,
            "price": 175.0,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "free_cash_flow": 100_000_000_000,
            "debt_to_equity": 1.5,
            "roe": 0.45,
            "guidance": {"revenue": (90_000, 95_000)},
            "insider_transactions": [],
            "institutional_ownership": 0.62,
        }

    def test_evaluate_full_data_is_ready(self):
        evaluator = ReadinessEvaluator()
        evaluator.set_data_snapshot("AAPL", self._full_data())
        evaluator.set_last_analysis(
            "AAPL", datetime.now(timezone.utc).isoformat()
        )

        score = evaluator.evaluate("AAPL", {"event_id": "ev_001"})
        assert score.overall_score > 70
        assert score.recommendation == "ready"
        assert score.missing_items == []

    def test_evaluate_no_data_is_insufficient(self):
        evaluator = ReadinessEvaluator()
        score = evaluator.evaluate("AAPL", {"event_id": "ev_001"})
        assert score.overall_score < 40
        assert score.recommendation == "insufficient"
        assert len(score.missing_items) > 0

    def test_evaluate_partial_data_is_partial(self):
        evaluator = ReadinessEvaluator()
        evaluator.set_data_snapshot("AAPL", {
            "market_cap": 3_000_000_000_000,
            "price": 175.0,
        })
        evaluator.set_last_analysis(
            "AAPL", datetime.now(timezone.utc).isoformat()
        )
        score = evaluator.evaluate("AAPL", {"event_id": "ev_001"})
        assert 40 <= score.overall_score < 70
        assert score.recommendation == "partial"
        assert len(score.missing_items) > 0

    def test_evaluate_stale_analysis_lowers_score(self):
        evaluator = ReadinessEvaluator()
        evaluator.set_data_snapshot("AAPL", self._full_data())
        stale = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        evaluator.set_last_analysis("AAPL", stale)

        score = evaluator.evaluate("AAPL", {"event_id": "ev_001"})
        assert score.analysis_freshness == 0.0
        assert score.overall_score < 70

    def test_evaluate_evidence_completeness(self):
        evaluator = ReadinessEvaluator()
        evaluator.set_data_snapshot("AAPL", self._full_data())
        evaluator.set_last_analysis(
            "AAPL", datetime.now(timezone.utc).isoformat()
        )

        score = evaluator.evaluate("AAPL", {
            "event_id": "ev_001",
            "evidence_claims": [
                {"claim": "Revenue grew", "evidence": "10-Q filing"},
                {"claim": "Margins expanded", "source": "earnings call"},
                {"claim": "No evidence"},
            ],
        })
        assert score.evidence_completeness == pytest.approx(66.7, abs=0.1)
        assert score.overall_score < 100

    def test_missing_data_report_empty(self):
        evaluator = ReadinessEvaluator()
        evaluator.set_data_snapshot("AAPL", self._full_data())
        report = evaluator.missing_data_report("AAPL")
        assert report == ["All expected data fields are present"]

    def test_missing_data_report_with_gaps(self):
        evaluator = ReadinessEvaluator()
        evaluator.set_data_snapshot("AAPL", {"price": 175.0})
        report = evaluator.missing_data_report("AAPL")
        assert len(report) > 0
        assert any("Missing:" in item for item in report)

    def test_missing_data_report_no_snapshot(self):
        evaluator = ReadinessEvaluator()
        report = evaluator.missing_data_report("NONEXISTENT")
        assert len(report) == 1
        assert "No data snapshot" in report[0]
