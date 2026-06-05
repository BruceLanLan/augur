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

    def test_analyze_missing_ticker_argument(self, runner):
        """Verify analyze without ticker argument fails with proper Click usage error."""
        result = runner.invoke(main, ["analyze"])
        assert result.exit_code == 2  # Click usage error
        assert "Missing argument" in result.output
        assert "TICKER" in result.output

    def test_consensus_missing_ticker_argument(self, runner):
        """Verify consensus without ticker argument fails with proper Click usage error."""
        result = runner.invoke(main, ["consensus"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output
        assert "TICKER" in result.output

    def test_inject_soul_format_flag_accepts_valid_choices(self, runner, tmp_path):
        """Verify --format flag accepts the three documented choices (hermes, claude, raw)."""
        for fmt in ["hermes", "claude", "raw"]:
            result = runner.invoke(main, [
                "inject-soul",
                "--profile", f"test-{fmt}",
                "--persona", "buffett",
                "--output-dir", str(tmp_path),
                "--format", fmt,
            ])
            assert result.exit_code == 0, f"format={fmt} failed: {result.output}"
            assert "Soul injected" in result.output

    def test_inject_soul_format_flag_rejects_invalid_choice(self, runner):
        """Verify --format flag rejects values outside the click.Choice set."""
        result = runner.invoke(main, [
            "inject-soul",
            "--profile", "bad",
            "--persona", "buffett",
            "--format", "bogus",
        ])
        assert result.exit_code == 2
        assert "Invalid value" in result.output
        assert "--format" in result.output

    def test_no_color_disables_emojis(self, runner):
        """Verify --no-color strips emoji glyphs (not just ANSI) from consensus output."""
        # Reference: known emoji codepoints used by cli_format
        emoji_chars = ["\U0001f7e2", "\U0001f7e1", "\U0001f534", "\u26a1", "\U0001f680"]
        for emoji in emoji_chars:
            result = runner.invoke(main, ["--no-color", "consensus", "AAPL", "--pe", "25"])
            assert result.exit_code == 0
            assert emoji not in result.output, (
                f"emoji {emoji!r} present in --no-color output"
            )

    def test_unknown_command_rejected(self, runner):
        """Verify unknown subcommands are rejected with a Click error."""
        result = runner.invoke(main, ["definitely-not-a-real-command"])
        assert result.exit_code == 2
        assert "No such command" in result.output
        assert "definitely-not-a-real-command" in result.output

    def test_watchlist_add_invalid_pe_rejected(self, runner):
        """Verify --pe flag with non-numeric input is rejected by Click's float type."""
        result = runner.invoke(main, ["watchlist-add", "FAKE", "--pe", "not-a-number"])
        assert result.exit_code == 2
        assert "Invalid value" in result.output
        assert "--pe" in result.output
