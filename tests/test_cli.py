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
        result = runner.invoke(main, ["inject-soul", "--help"])
        assert result.exit_code == 0
        assert "--profile" in result.output
        assert "--persona" in result.output

    def test_inject_soul_runs(self, runner):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(main, [
                "inject-soul", "--profile", "test-profile",
                "--persona", "buffett", "--output-dir", tmpdir,
                "--format", "raw"
            ])
            assert result.exit_code == 0
            assert "Soul injected" in result.output

    def test_analyze_single_persona(self, runner):
        result = runner.invoke(main, ["analyze", "AAPL", "--persona", "buffett", "--pe", "32"])
        assert result.exit_code == 0
        assert "Warren Buffett" in result.output
        assert "Signal:" in result.output

    def test_analyze_all(self, runner):
        result = runner.invoke(main, ["analyze", "AAPL", "--pe", "25"])
        assert result.exit_code == 0
        assert "AAPL" in result.output
        assert "Masters Consensus" in result.output
        assert "Signal:" in result.output
        assert "Score:" in result.output

    def test_consensus_runs(self, runner):
        result = runner.invoke(main, ["consensus", "NVDA", "--pe", "60", "--gross-margins", "0.75"])
        assert result.exit_code == 0
        assert "Signal:" in result.output
        assert "Score:" in result.output

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        from augur import __version__
        assert __version__ in result.output

    def test_no_color_flag_strips_ansi_and_emoji(self, runner):
        """Verify --no-color produces output without ANSI escape codes or emojis."""
        import re
        result = runner.invoke(main, ["--no-color", "consensus", "AAPL", "--pe", "25"])
        assert result.exit_code == 0
        # No ANSI escape sequences
        ansi_pattern = re.compile(r"\033\[[0-9;]*m")
        assert not ansi_pattern.search(result.output), "ANSI codes found in --no-color output"

    def test_no_color_env_variable(self, runner):
        """Verify NO_COLOR env variable disables color and emojis."""
        import re
        result = runner.invoke(main, ["consensus", "AAPL", "--pe", "25"], env={"NO_COLOR": "1"})
        assert result.exit_code == 0
        ansi_pattern = re.compile(r"\033\[[0-9;]*m")
        assert not ansi_pattern.search(result.output), "ANSI codes found with NO_COLOR env"

    def test_consensus_json_valid(self, runner):
        """Verify --json output from consensus is parseable JSON."""
        import json
        result = runner.invoke(main, ["consensus", "AAPL", "--pe", "25", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "ticker" in data
        assert "consensus" in data
        assert "individual" in data
        assert data["ticker"] == "AAPL"

    def test_analyze_json_valid_single(self, runner):
        """Verify --json output from analyze (single persona) is parseable JSON."""
        import json
        result = runner.invoke(main, ["analyze", "AAPL", "--persona", "buffett", "--pe", "25", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "signal" in data
        assert "score" in data
        assert isinstance(data["score"], (int, float))

    def test_analyze_json_valid_all(self, runner):
        """Verify --json output from analyze (all agents) is parseable JSON."""
        import json
        result = runner.invoke(main, ["analyze", "AAPL", "--pe", "25", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)
        # Should contain agent keys
        assert len(data) > 0
