# -*- coding: utf-8 -*-
"""Tests for scripts/smoke_test_datasources.py -- the real-network smoke
test run weekly by .github/workflows/data-source-smoke.yml.

Only the CLI/severity logic is covered here (mocked) -- the actual network
calls (check_edgar/check_yfinance's bodies) are exercised manually/by CI
against the real internet, not in the offline test suite.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "smoke_test_datasources.py"
_spec = importlib.util.spec_from_file_location("smoke_test_datasources", _SCRIPT_PATH)
smoke = importlib.util.module_from_spec(_spec)
sys.modules["smoke_test_datasources"] = smoke
_spec.loader.exec_module(smoke)


class TestSeverityAsymmetry:
    """EDGAR failure must fail the job; yfinance failure must not -- SEC
    rarely blocks CI IPs, Yahoo Finance frequently does, for reasons
    unrelated to a real regression."""

    def test_edgar_failure_returns_nonzero(self):
        with patch.object(smoke, "check_edgar", return_value=False):
            with patch("sys.argv", ["smoke_test_datasources.py", "--edgar"]):
                assert smoke.main() == 1

    def test_edgar_success_returns_zero(self):
        with patch.object(smoke, "check_edgar", return_value=True):
            with patch("sys.argv", ["smoke_test_datasources.py", "--edgar"]):
                assert smoke.main() == 0

    def test_yfinance_failure_alone_returns_zero(self):
        with patch.object(smoke, "check_yfinance", return_value=False):
            with patch("sys.argv", ["smoke_test_datasources.py", "--yfinance"]):
                assert smoke.main() == 0

    def test_yfinance_success_returns_zero(self):
        with patch.object(smoke, "check_yfinance", return_value=True):
            with patch("sys.argv", ["smoke_test_datasources.py", "--yfinance"]):
                assert smoke.main() == 0

    def test_all_mode_edgar_failure_dominates_yfinance_success(self):
        with patch.object(smoke, "check_edgar", return_value=False), patch.object(
            smoke, "check_yfinance", return_value=True
        ):
            with patch("sys.argv", ["smoke_test_datasources.py", "--all"]):
                assert smoke.main() == 1

    def test_all_mode_both_fail_returns_nonzero(self):
        with patch.object(smoke, "check_edgar", return_value=False), patch.object(
            smoke, "check_yfinance", return_value=False
        ):
            with patch("sys.argv", ["smoke_test_datasources.py", "--all"]):
                assert smoke.main() == 1

    def test_all_mode_both_succeed_returns_zero(self):
        with patch.object(smoke, "check_edgar", return_value=True), patch.object(
            smoke, "check_yfinance", return_value=True
        ):
            with patch("sys.argv", ["smoke_test_datasources.py", "--all"]):
                assert smoke.main() == 0


class TestArgumentDefaults:
    def test_no_flags_runs_edgar_only(self):
        """Bare invocation (no --edgar/--yfinance/--all) must still run the
        load-bearing EDGAR check, not silently no-op."""
        with patch.object(smoke, "check_edgar", return_value=True) as mock_edgar, patch.object(
            smoke, "check_yfinance"
        ) as mock_yfinance:
            with patch("sys.argv", ["smoke_test_datasources.py"]):
                rc = smoke.main()
        assert rc == 0
        mock_edgar.assert_called_once()
        mock_yfinance.assert_not_called()

    def test_edgar_flag_does_not_run_yfinance(self):
        with patch.object(smoke, "check_edgar", return_value=True), patch.object(
            smoke, "check_yfinance"
        ) as mock_yfinance:
            with patch("sys.argv", ["smoke_test_datasources.py", "--edgar"]):
                smoke.main()
        mock_yfinance.assert_not_called()

    def test_yfinance_flag_does_not_run_edgar(self):
        with patch.object(smoke, "check_edgar") as mock_edgar, patch.object(
            smoke, "check_yfinance", return_value=True
        ):
            with patch("sys.argv", ["smoke_test_datasources.py", "--yfinance"]):
                smoke.main()
        mock_edgar.assert_not_called()


class TestWarningOnYfinanceFailure:
    def test_prints_github_actions_warning_annotation(self, capsys):
        with patch.object(smoke, "check_yfinance", return_value=False):
            with patch("sys.argv", ["smoke_test_datasources.py", "--yfinance"]):
                smoke.main()
        captured = capsys.readouterr()
        assert "::warning::" in captured.out

    def test_no_warning_when_yfinance_succeeds(self, capsys):
        with patch.object(smoke, "check_yfinance", return_value=True):
            with patch("sys.argv", ["smoke_test_datasources.py", "--yfinance"]):
                smoke.main()
        captured = capsys.readouterr()
        assert "::warning::" not in captured.out
