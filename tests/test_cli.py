# -*- coding: utf-8 -*-
"""Test CLI commands are registered and --help works."""

import pytest
from click.testing import CliRunner
from augur.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestCLI:
    def test_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Multi-agent investment analysis" in result.output

    def test_analyze_help(self, runner):
        result = runner.invoke(main, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "TICKER" in result.output
        assert "--persona" in result.output
        assert "--pe" in result.output

    def test_consensus_help(self, runner):
        result = runner.invoke(main, ["consensus", "--help"])
        assert result.exit_code == 0
        assert "TICKER" in result.output

    def test_list_personas_help(self, runner):
        result = runner.invoke(main, ["list-personas", "--help"])
        assert result.exit_code == 0

    def test_list_personas_runs(self, runner):
        result = runner.invoke(main, ["list-personas"])
        assert result.exit_code == 0
        assert "buffett" in result.output
        assert "graham" in result.output

    def test_mcp_server_help(self, runner):
        result = runner.invoke(main, ["mcp-server", "--help"])
        assert result.exit_code == 0

    def test_api_help(self, runner):
        result = runner.invoke(main, ["api", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output

    def test_inject_soul(self, runner):
        result = runner.invoke(main, ["inject-soul"])
        assert result.exit_code == 0
        assert "Phase 2" in result.output

    def test_analyze_single_persona(self, runner):
        result = runner.invoke(main, ["analyze", "AAPL", "--persona", "buffett", "--pe", "32"])
        assert result.exit_code == 0
        assert "Warren Buffett" in result.output
        assert "Signal:" in result.output

    def test_analyze_all(self, runner):
        result = runner.invoke(main, ["analyze", "AAPL", "--pe", "25"])
        assert result.exit_code == 0
        assert "Analyzing AAPL" in result.output

    def test_consensus_runs(self, runner):
        result = runner.invoke(main, ["consensus", "NVDA", "--pe", "60", "--gross-margins", "0.75"])
        assert result.exit_code == 0
        assert "Signal:" in result.output
        assert "Score:" in result.output

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
