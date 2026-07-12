# -*- coding: utf-8 -*-
"""Tests for `augur doctor` -- local environment diagnostic command.

Covers the SSL/TLS toolchain check (motivated by a real incident: a venv
built from macOS CommandLineTools' python3.9 links Apple's LibreSSL, which
breaks yfinance's curl_cffi backend with SSLError), API key visibility,
data-source connectivity probing, and learning-engine data accumulation
reporting.
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from augur.cli import main
from augur.datasources.base import DataProvider, DataProviderError


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def isolated_provider_stats(tmp_path):
    """Every test gets its own provider_stats.json -- never touch the real
    ~/.augur/provider_stats.json on the machine running the suite."""
    stats_path = tmp_path / "provider_stats.json"
    with patch("augur.provider_stats._default_path", return_value=stats_path):
        yield stats_path


class _FakeProvider(DataProvider):
    def __init__(self, name, should_fail=False):
        self.name = name
        self._should_fail = should_fail

    def fetch(self, ticker):
        if self._should_fail:
            raise DataProviderError(f"{self.name} request failed for {ticker}: boom")
        return {"data_source": self.name}


class TestOfflineMode:
    def test_offline_skips_network_calls(self, runner):
        with patch(
            "augur.datasources.default_providers",
            return_value=[_FakeProvider("yfinance"), _FakeProvider("stooq")],
        ):
            with patch.object(_FakeProvider, "fetch", side_effect=AssertionError("should not be called")):
                result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "skipped (--offline)" in result.output
        assert "yfinance" in result.output
        assert "stooq" in result.output

    def test_offline_still_reports_ssl_and_keys(self, runner):
        result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "Python environment" in result.output
        assert "SSL backend" in result.output
        assert "API key configuration" in result.output
        assert "Learning engine" in result.output


class TestSSLDetection:
    def test_libressl_triggers_warning(self, runner):
        with patch("ssl.OPENSSL_VERSION", "LibreSSL 2.8.3"):
            result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "LibreSSL detected" in result.output
        assert "curl_cffi" in result.output

    def test_real_openssl_reports_ok(self, runner):
        with patch("ssl.OPENSSL_VERSION", "OpenSSL 3.6.3 9 Jun 2026"):
            result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "looks fine for yfinance/curl_cffi" in result.output
        assert "LibreSSL detected" not in result.output


class TestApiKeyReporting:
    def test_configured_key_shown_as_configured(self, runner, monkeypatch):
        monkeypatch.setenv("FINNHUB_API_KEY", "test-key-123")
        result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        lines = [l for l in result.output.splitlines() if "FINNHUB_API_KEY" in l]
        assert lines and "configured" in lines[0] and "not set" not in lines[0]

    def test_missing_key_shown_as_not_set(self, runner, monkeypatch):
        monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
        result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        lines = [l for l in result.output.splitlines() if "ALPHAVANTAGE_API_KEY" in l]
        assert lines and "not set" in lines[0]


class TestDataSourceConnectivity:
    def test_reachable_provider_marked_ok(self, runner):
        with patch(
            "augur.datasources.default_providers",
            return_value=[_FakeProvider("yfinance", should_fail=False)],
        ):
            result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "yfinance" in result.output
        assert "reachable" in result.output

    def test_failing_provider_marked_failed_with_reason(self, runner):
        with patch(
            "augur.datasources.default_providers",
            return_value=[_FakeProvider("stooq", should_fail=True)],
        ):
            result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "FAILED" in result.output
        assert "stooq request failed" in result.output

    def test_provider_chain_load_failure_reported_not_raised(self, runner):
        with patch("augur.datasources.default_providers", side_effect=RuntimeError("boom")):
            result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "Could not load data source chain" in result.output


class TestProviderStatsHistory:
    """Repeated `augur doctor` runs build up a short local trend, so a dead
    endpoint (like stooq's real 2026-07-09 404 breakage) shows up as a
    reachability history instead of requiring someone to notice by hand."""

    def test_first_run_includes_its_own_result_in_history(self, runner):
        with patch(
            "augur.datasources.default_providers",
            return_value=[_FakeProvider("yfinance", should_fail=False)],
        ):
            result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Last 7 days" in result.output
        assert "1/1 reachable" in result.output

    def test_offline_only_run_shows_no_history_yet(self, runner):
        with patch(
            "augur.datasources.default_providers",
            return_value=[_FakeProvider("yfinance", should_fail=False)],
        ):
            result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "Last 7 days" not in result.output

    def test_second_run_shows_accumulated_history(self, runner):
        with patch(
            "augur.datasources.default_providers",
            return_value=[_FakeProvider("stooq", should_fail=True)],
        ):
            first = runner.invoke(main, ["doctor"])
            second = runner.invoke(main, ["doctor"])
        assert first.exit_code == 0
        assert second.exit_code == 0
        assert "Last 7 days" in second.output
        assert "stooq" in second.output
        assert "0/2 reachable" in second.output

    def test_offline_run_does_not_record_but_still_shows_prior_history(self, runner):
        with patch(
            "augur.datasources.default_providers",
            return_value=[_FakeProvider("yfinance", should_fail=False)],
        ):
            runner.invoke(main, ["doctor"])
            offline_result = runner.invoke(main, ["doctor", "--offline"])
        assert offline_result.exit_code == 0
        assert "Last 7 days" in offline_result.output
        assert "1/1 reachable" in offline_result.output

    def test_history_survives_stats_write_failure(self, runner):
        with patch("augur.provider_stats._default_path", side_effect=OSError("disk full")):
            with patch(
                "augur.datasources.default_providers",
                return_value=[_FakeProvider("yfinance", should_fail=False)],
            ):
                result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "reachable" in result.output


class TestLearningEngineReporting:
    def test_shows_pending_and_resolved_counts(self, runner):
        fake_engine = type(
            "FakeEngine",
            (),
            {
                "prediction_count": 72,
                "pending_count": 70,
                "last_resolution": {"timestamp": 1783645213.65, "resolved": 2, "failed": 0},
            },
        )()
        with patch("augur.registry._get_learning_engine", return_value=fake_engine):
            result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "72 total" in result.output
        assert "2 resolved" in result.output
        assert "70 pending" in result.output

    def test_never_run_when_no_resolution_history(self, runner):
        fake_engine = type(
            "FakeEngine",
            (),
            {"prediction_count": 0, "pending_count": 0, "last_resolution": None},
        )()
        with patch("augur.registry._get_learning_engine", return_value=fake_engine):
            result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "never run" in result.output

    def test_learning_engine_failure_reported_not_raised(self, runner):
        with patch("augur.registry._get_learning_engine", side_effect=RuntimeError("boom")):
            result = runner.invoke(main, ["doctor", "--offline"])
        assert result.exit_code == 0
        assert "Could not read learning engine state" in result.output
