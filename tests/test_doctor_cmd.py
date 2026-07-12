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
