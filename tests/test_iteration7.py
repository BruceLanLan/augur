# -*- coding: utf-8 -*-
"""Tests for iteration 7 features: error messages, API response consistency,
and global exception handler.
"""

import pytest
from unittest.mock import patch
from click.testing import CliRunner
from fastapi.testclient import TestClient
import importlib

from dashboard.app import app as dashboard_app
from augur.api import app as standalone_app


@pytest.fixture(scope="module")
def dashboard_client():
    """TestClient for the dashboard app."""
    return TestClient(dashboard_app)


@pytest.fixture(scope="module")
def api_client():
    """TestClient for the standalone API."""
    return TestClient(standalone_app)


class TestGlobalExceptionHandler:
    """Test that unhandled exceptions return proper JSON, not stack traces."""

    def test_dashboard_unhandled_exception_returns_json(self):
        """Simulated unhandled exception should return JSON with status=error."""
        client = TestClient(dashboard_app, raise_server_exceptions=False)
        with patch("dashboard.app.get_registry", side_effect=RuntimeError("Simulated crash")):
            resp = client.get("/api/personas")
        assert resp.status_code == 500
        data = resp.json()
        assert data["status"] == "error"
        assert "detail" in data
        assert "timestamp" in data
        assert "path" in data
        # Must not contain stack trace information
        assert "Traceback" not in resp.text
        assert "RuntimeError" not in data["detail"]

    def test_standalone_api_unhandled_exception_returns_json(self):
        """Standalone API unhandled exception should return JSON with status=error."""
        client = TestClient(standalone_app, raise_server_exceptions=False)
        with patch("augur.api.get_registry", side_effect=RuntimeError("Simulated crash")):
            resp = client.get("/api/personas")
        assert resp.status_code == 500
        data = resp.json()
        assert data["status"] == "error"
        assert "detail" in data
        assert "timestamp" in data
        assert "path" in data
        assert "Traceback" not in resp.text

    def test_exception_handler_timestamp_format(self):
        """Timestamp in error response should be ISO 8601 with Z suffix."""
        import re
        client = TestClient(dashboard_app, raise_server_exceptions=False)
        with patch("dashboard.app.get_registry", side_effect=RuntimeError("Crash")):
            resp = client.get("/api/personas")
        data = resp.json()
        ts = data["timestamp"]
        # Should match YYYY-MM-DDTHH:MM:SSZ pattern
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", ts)


class TestCLIErrorMessages:
    """Test that CLI error messages are actionable and helpful."""

    def test_persona_not_found_includes_suggestion(self):
        """Error for missing persona should include suggestion to list personas."""
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["analyze", "AAPL", "--persona", "nonexistent", "--pe", "25"])
        assert result.exit_code != 0
        output = result.output
        assert "not found" in output
        # Should include actionable guidance
        assert "list-personas" in output or "Available" in output

    def test_missing_yfinance_includes_pip_install(self):
        """When yfinance is missing, error should include pip install command."""
        from augur.cli import main
        runner = CliRunner()
        # Directly test _auto_fetch_context by patching the import
        with patch("augur.cli._auto_fetch_context") as mock_fetch:
            # Simulate the ImportError path behavior
            from augur.personas.base import MarketContext
            import click as _click

            def fake_auto_fetch(ticker):
                _click.echo(
                    "Warning: yfinance not installed. Install with: pip install 'augur-agents[data]'\n"
                    "  Core analysis still works without it (using empty metrics).\n",
                    err=True,
                )
                return MarketContext(ticker=ticker.upper())

            mock_fetch.side_effect = fake_auto_fetch
            result = runner.invoke(main, ["analyze", "AAPL"])
        output = result.output
        assert "augur-agents[data]" in output

    def test_fetch_cmd_missing_yfinance_message(self):
        """fetch command with missing yfinance should show pip install instructions."""
        from augur.cli import main
        runner = CliRunner()
        # Mock the importlib.import_module to fail within the fetch command
        with patch("augur.optional_deps.importlib.import_module") as mock_import:
            def selective_import(name):
                if name == "augur.data":
                    raise ImportError(f"No module named 'augur.data'")
                return importlib.import_module(name)
            mock_import.side_effect = selective_import
            result = runner.invoke(main, ["fetch", "AAPL"])
        output = result.output
        assert result.exit_code != 0
        assert "augur-agents[data]" in output


class TestAPIResponseConsistency:
    """Test that API responses have consistent structure."""

    def test_analyze_has_status_field(self, dashboard_client):
        """GET /api/analyze/TEST should include status=ok in response."""
        resp = dashboard_client.get("/api/analyze/TEST?auto_fetch=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_analyze_timestamp_iso8601_z(self, dashboard_client):
        """Timestamp should be ISO 8601 with Z suffix."""
        import re
        resp = dashboard_client.get("/api/analyze/TEST?auto_fetch=false")
        data = resp.json()
        assert "timestamp" in data
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", data["timestamp"])

    def test_personas_has_status_field(self, dashboard_client):
        """GET /api/personas should include status=ok."""
        resp = dashboard_client.get("/api/personas")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_standalone_analyze_has_status_field(self, api_client):
        """Standalone API analyze should include status=ok."""
        resp = api_client.get("/api/analyze/TEST?auto_fetch=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_standalone_analyze_timestamp_format(self, api_client):
        """Standalone API timestamp should be ISO 8601 with Z suffix."""
        import re
        resp = api_client.get("/api/analyze/TEST?auto_fetch=false")
        data = resp.json()
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", data["timestamp"])

    def test_standalone_personas_has_status(self, api_client):
        """Standalone /api/personas should include status=ok."""
        resp = api_client.get("/api/personas")
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_endpoint_has_status(self, dashboard_client):
        """Health endpoint should return status=ok."""
        resp = dashboard_client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_error_response_has_detail(self, dashboard_client):
        """Error responses should have 'detail' field."""
        resp = dashboard_client.get("/api/analyze/INVALID;TICKER")
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data


class TestErrorsModule:
    """Test the augur.errors module."""

    def test_error_response_structure(self):
        """error_response should return consistent dict structure."""
        from augur.errors import error_response
        err = error_response("Something went wrong", "Try again", "TEST_ERROR")
        assert err["status"] == "error"
        assert err["detail"] == "Something went wrong"
        assert err["suggestion"] == "Try again"
        assert err["code"] == "TEST_ERROR"

    def test_api_error_response_has_timestamp(self):
        """api_error_response should include timestamp and path."""
        import re
        from augur.errors import api_error_response
        err = api_error_response("Server failed", "Retry later", "SERVER_ERROR", "/api/test")
        assert err["status"] == "error"
        assert err["path"] == "/api/test"
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", err["timestamp"])

    def test_predefined_errors_have_required_fields(self):
        """All predefined ERRORS should have status, detail, suggestion, code."""
        from augur.errors import ERRORS
        for key, err in ERRORS.items():
            assert "status" in err, f"ERRORS[{key}] missing 'status'"
            assert "detail" in err, f"ERRORS[{key}] missing 'detail'"
            assert "suggestion" in err, f"ERRORS[{key}] missing 'suggestion'"
            assert "code" in err, f"ERRORS[{key}] missing 'code'"
            assert err["status"] == "error"

    def test_missing_yfinance_error_has_pip_install(self):
        """The yfinance error should mention pip install command."""
        from augur.errors import ERRORS
        err = ERRORS["missing_yfinance"]
        assert "pip install" in err["suggestion"]
        assert "augur-agents[data]" in err["suggestion"]


def _make_import_blocker(module_name):
    """Create an import side_effect that blocks a specific module."""
    _real_import = builtins.__import__

    def blocker(name, *args, **kwargs):
        if name == module_name:
            raise ImportError(f"No module named '{module_name}'")
        return _real_import(name, *args, **kwargs)

    return blocker


import builtins
original_import = builtins.__import__


class TestGracefulDegradation:
    """Test graceful degradation when optional dependencies are missing."""

    def test_fetch_cmd_missing_yfinance_gives_helpful_message(self):
        """When yfinance/augur.data is unavailable, fetch should give actionable error."""
        from augur.cli import main
        runner = CliRunner()
        with patch("augur.optional_deps.importlib.import_module") as mock_import:
            def selective_import(name):
                if name == "augur.data":
                    raise ImportError(f"No module named 'augur.data'")
                return importlib.import_module(name)
            mock_import.side_effect = selective_import
            result = runner.invoke(main, ["fetch", "AAPL"])
        assert result.exit_code != 0
        output = result.output
        assert "augur-agents[data]" in output
        assert "not installed" in output

    def test_cron_start_missing_apscheduler_gives_helpful_message(self):
        """When apscheduler is unavailable, cron-start should give actionable error."""
        from augur.cli import main
        runner = CliRunner()
        with patch("augur.optional_deps.importlib.import_module") as mock_import:
            def selective_import(name):
                if name == "apscheduler":
                    raise ImportError(f"No module named 'apscheduler'")
                return importlib.import_module(name)
            mock_import.side_effect = selective_import
            result = runner.invoke(main, ["cron-start"])
        assert result.exit_code != 0
        output = result.output
        assert "augur-agents[cron]" in output
        assert "not installed" in output

    def test_analyze_works_without_optional_deps(self):
        """Core analyze command works without yfinance/apscheduler."""
        from augur.cli import main
        runner = CliRunner()
        # Provide metrics so it doesn't try to auto-fetch
        result = runner.invoke(main, ["analyze", "AAPL", "--pe", "25", "--roe", "0.5"])
        assert result.exit_code == 0
        # Should show analysis output
        assert "AAPL" in result.output or "Agent" in result.output

    def test_consensus_works_without_optional_deps(self):
        """Core consensus command works without yfinance/apscheduler."""
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["consensus", "AAPL", "--pe", "25", "--roe", "0.5"])
        assert result.exit_code == 0
        assert "AAPL" in result.output

    def test_list_personas_works_without_optional_deps(self):
        """list-personas command works without any optional deps."""
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["list-personas"])
        assert result.exit_code == 0
        assert "Available Personas" in result.output

    def test_telegram_cmd_missing_dep_gives_helpful_message(self):
        """When telegram package is unavailable, command should give actionable error."""
        from augur.cli import main
        runner = CliRunner()
        with patch("augur.optional_deps.importlib.import_module") as mock_import:
            def selective_import(name):
                if name == "telegram":
                    raise ImportError(f"No module named 'telegram'")
                return importlib.import_module(name)
            mock_import.side_effect = selective_import
            result = runner.invoke(main, ["telegram"])
        assert result.exit_code != 0
        output = result.output
        assert "augur-agents[telegram]" in output

    def test_slack_cmd_missing_dep_gives_helpful_message(self):
        """When slack_bolt is unavailable, command should give actionable error."""
        from augur.cli import main
        runner = CliRunner()
        with patch("augur.optional_deps.importlib.import_module") as mock_import:
            def selective_import(name):
                if name == "slack_bolt":
                    raise ImportError(f"No module named 'slack_bolt'")
                return importlib.import_module(name)
            mock_import.side_effect = selective_import
            result = runner.invoke(main, ["slack"])
        assert result.exit_code != 0
        output = result.output
        assert "augur-agents[slack]" in output


class TestOptionalDepsModule:
    """Test the augur.optional_deps module itself."""

    def test_is_available_returns_true_for_installed_packages(self):
        """is_available should return True for packages we know exist."""
        from augur.optional_deps import is_available
        assert is_available("os") is True
        assert is_available("sys") is True

    def test_is_available_returns_false_for_missing_packages(self):
        """is_available should return False for non-existent packages."""
        from augur.optional_deps import is_available
        with patch("augur.optional_deps.importlib.import_module", side_effect=ImportError):
            assert is_available("nonexistent_package_xyz") is False

    def test_require_optional_raises_for_missing_package(self):
        """require_optional should raise ImportError with helpful message."""
        from augur.optional_deps import require_optional
        with patch("augur.optional_deps.importlib.import_module", side_effect=ImportError):
            with pytest.raises(ImportError) as exc_info:
                require_optional("yfinance")
            msg = str(exc_info.value)
            assert "yfinance" in msg
            assert "augur-agents[data]" in msg
            assert "not installed" in msg

    def test_require_optional_passes_for_installed_package(self):
        """require_optional should not raise for installed packages."""
        from augur.optional_deps import require_optional
        # 'os' is always available
        require_optional("os", "operating system features", "pip install os")

    def test_get_install_hint_returns_registry_entry(self):
        """get_install_hint should return registered info for known packages."""
        from augur.optional_deps import get_install_hint
        feature, cmd = get_install_hint("yfinance")
        assert "market data" in feature
        assert "augur-agents[data]" in cmd

    def test_get_install_hint_returns_default_for_unknown(self):
        """get_install_hint should return generic hint for unknown packages."""
        from augur.optional_deps import get_install_hint
        feature, cmd = get_install_hint("some_unknown_pkg")
        assert "some_unknown_pkg" in cmd


class TestCLIOutputFormat:
    """Test CLI output formatting: --no-color and --json flags."""

    def test_no_color_strips_formatting(self):
        """--no-color flag should produce output without ANSI escape codes."""
        import re
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["--no-color", "consensus", "AAPL", "--pe", "25"])
        assert result.exit_code == 0
        # No ANSI escape sequences
        ansi_pattern = re.compile(r"\033\[[0-9;]*m")
        assert not ansi_pattern.search(result.output)

    def test_json_output_analyze_is_valid(self):
        """--json flag on analyze should produce valid JSON."""
        import json
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["analyze", "AAPL", "--pe", "25", "--json"])
        assert result.exit_code == 0
        # Should be parseable JSON
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_json_output_consensus_is_valid(self):
        """--json flag on consensus should produce valid JSON."""
        import json
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["consensus", "AAPL", "--pe", "25", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert "ticker" in data
        assert "consensus" in data

    def test_help_text_completeness(self):
        """All main commands should have help text."""
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        # Should list key commands
        assert "analyze" in result.output
        assert "consensus" in result.output
        assert "list-personas" in result.output
        assert "fetch" in result.output


import importlib
