from pathlib import Path
# -*- coding: utf-8 -*-
"""Tests for Provider Health Dashboard (G08)."""
import pytest
from augur.provider_health import (
    ProviderHealth, ProviderHealthDashboard, ProviderHealthTracker,
)


class TestProviderHealth:
    def test_creation(self):
        ph = ProviderHealth(provider_name="yfinance", status="healthy")
        assert ph.provider_name == "yfinance"
        assert ph.status == "healthy"


class TestProviderHealthDashboard:
    def test_counts(self):
        providers = [
            ProviderHealth(provider_name="a", status="healthy"),
            ProviderHealth(provider_name="b", status="healthy"),
            ProviderHealth(provider_name="c", status="degraded"),
            ProviderHealth(provider_name="d", status="down"),
        ]
        dash = ProviderHealthDashboard(providers=providers)
        assert dash.healthy_count == 2
        assert dash.degraded_count == 1
        assert dash.down_count == 1

    def test_empty(self):
        dash = ProviderHealthDashboard(providers=[])
        assert dash.healthy_count == 0


class TestProviderHealthTracker:
    def test_record_success(self):
        import tempfile; t = ProviderHealthTracker(storage_path=Path(tempfile.mktemp(suffix='.json')))
        t.record_success("yfinance", 100.0, tickers=5)
        ph = t.get_health("yfinance")
        assert ph is not None
        assert ph.status == "healthy"
        assert ph.total_successes == 1

    def test_record_failure(self):
        import tempfile; t = ProviderHealthTracker(storage_path=Path(tempfile.mktemp(suffix='.json')))
        t.record_failure("bad_source", "timeout")
        ph = t.get_health("bad_source")
        assert ph is not None
        assert ph.status == "down"
        assert ph.last_error == "timeout"

    def test_record_success_then_failure(self):
        import tempfile; t = ProviderHealthTracker(storage_path=Path(tempfile.mktemp(suffix='.json')))
        t.record_success("test", 50.0)
        t.record_failure("test", "error")
        ph = t.get_health("test")
        assert ph.total_checks == 2
        assert ph.total_successes == 1

    def test_get_dashboard(self):
        import tempfile; t = ProviderHealthTracker(storage_path=Path(tempfile.mktemp(suffix='.json')))
        t.record_success("a", 10.0)
        t.record_failure("b", "down")
        dash = t.get_dashboard()
        assert len(dash.providers) == 2
        assert dash.healthy_count >= 1

    def test_get_issues(self):
        import tempfile; t = ProviderHealthTracker(storage_path=Path(tempfile.mktemp(suffix='.json')))
        t.record_success("healthy", 10.0)
        t.record_failure("bad", "error")
        issues = t.get_issues()
        assert len(issues) == 1
        assert issues[0].provider_name == "bad"

    def test_multiple_successes_avg_latency(self):
        import tempfile; t = ProviderHealthTracker(storage_path=Path(tempfile.mktemp(suffix='.json')))
        t.record_success("test", 100.0)
        t.record_success("test", 200.0)
        ph = t.get_health("test")
        assert ph.avg_latency_ms == pytest.approx(150.0, rel=0.1)
