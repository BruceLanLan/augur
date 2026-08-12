# -*- coding: utf-8 -*-
"""Tests for ``augur filing-delta`` CLI command."""

import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from augur.cli import main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def new_filing_json():
    return {
        "filing_date": "2025-11-01",
        "filing_type": "10-Q",
        "metrics": {
            "revenue": 94930.0,
            "net_income": 22956.0,
            "eps_diluted": 1.47,
            "total_assets": 352755.0,
        },
        "sections": {
            "Risk Factors": "Updated risk disclosure text...",
        },
        "guidance": {
            "revenue_guidance": [92000, 96000],
        },
    }


@pytest.fixture
def prev_filing_json():
    return {
        "filing_date": "2025-08-01",
        "filing_type": "10-Q",
        "metrics": {
            "revenue": 89498.0,
            "net_income": 21448.0,
            "eps_diluted": 1.38,
            "total_assets": 345000.0,
        },
        "sections": {
            "Risk Factors": "Original risk disclosure text...",
        },
        "guidance": {
            "revenue_guidance": [89000, 95000],
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFilingDeltaCLI:
    """Tests for the ``augur filing-delta`` CLI command."""

    def test_help(self, runner):
        """``filing-delta --help`` prints usage."""
        result = runner.invoke(main, ["filing-delta", "--help"])
        assert result.exit_code == 0
        assert "TICKER" in result.output
        assert "--new" in result.output
        assert "--prev" in result.output
        assert "--format" in result.output

    def test_registered_in_main_help(self, runner):
        """``main --help`` lists the filing-delta command."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "filing-delta" in result.output

    def test_markdown_output(self, runner, new_filing_json, prev_filing_json):
        """Default format produces a Markdown table report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = Path(tmpdir) / "new.json"
            prev_path = Path(tmpdir) / "prev.json"
            new_path.write_text(json.dumps(new_filing_json))
            prev_path.write_text(json.dumps(prev_filing_json))

            result = runner.invoke(main, [
                "filing-delta", "AAPL",
                "--new", str(new_path),
                "--prev", str(prev_path),
            ])
            assert result.exit_code == 0
            assert "# Filing Delta Report: AAPL" in result.output
            assert "## Numeric Changes" in result.output
            assert "revenue" in result.output
            assert "Overall Assessment" in result.output

    def test_json_output(self, runner, new_filing_json, prev_filing_json):
        """``--format json`` produces valid JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = Path(tmpdir) / "new.json"
            prev_path = Path(tmpdir) / "prev.json"
            new_path.write_text(json.dumps(new_filing_json))
            prev_path.write_text(json.dumps(prev_filing_json))

            result = runner.invoke(main, [
                "filing-delta", "AAPL",
                "--new", str(new_path),
                "--prev", str(prev_path),
                "--format", "json",
            ])
            assert result.exit_code == 0

            # Should be parseable JSON
            data = json.loads(result.output)
            assert data["ticker"] == "AAPL"
            assert data["filing_type"] == "10-Q"
            assert len(data["numeric_changes"]) > 0
            assert "overall_assessment" in data

    def test_missing_new_file(self, runner, prev_filing_json):
        """Error when --new file does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_path = Path(tmpdir) / "prev.json"
            prev_path.write_text(json.dumps(prev_filing_json))

            result = runner.invoke(main, [
                "filing-delta", "AAPL",
                "--new", str(Path(tmpdir) / "nonexistent.json"),
                "--prev", str(prev_path),
            ])
            assert result.exit_code == 1
            assert "Error" in result.output

    def test_missing_prev_file(self, runner, new_filing_json):
        """Error when --prev file does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = Path(tmpdir) / "new.json"
            new_path.write_text(json.dumps(new_filing_json))

            result = runner.invoke(main, [
                "filing-delta", "AAPL",
                "--new", str(new_path),
                "--prev", str(Path(tmpdir) / "nonexistent.json"),
            ])
            assert result.exit_code == 1
            assert "Error" in result.output

    def test_invalid_json_file(self, runner):
        """Error when a JSON file contains invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = Path(tmpdir) / "bad.json"
            bad_path.write_text("this is not json {{{")

            result = runner.invoke(main, [
                "filing-delta", "AAPL",
                "--new", str(bad_path),
                "--prev", str(bad_path),
            ])
            assert result.exit_code == 1
            assert "Error" in result.output

    def test_guidance_changes_in_output(self, runner, new_filing_json, prev_filing_json):
        """Markdown output includes guidance changes section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = Path(tmpdir) / "new.json"
            prev_path = Path(tmpdir) / "prev.json"
            new_path.write_text(json.dumps(new_filing_json))
            prev_path.write_text(json.dumps(prev_filing_json))

            result = runner.invoke(main, [
                "filing-delta", "AAPL",
                "--new", str(new_path),
                "--prev", str(prev_path),
            ])
            assert result.exit_code == 0
            assert "## Guidance Changes" in result.output
            assert "revenue_guidance" in result.output
            assert "raised" in result.output
