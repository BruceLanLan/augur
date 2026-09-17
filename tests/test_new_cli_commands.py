# -*- coding: utf-8 -*-
"""Tests for new CLI commands (batch, valuation, compat, dossier, ledger, earnings, research-report)."""
import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


class TestBatchCmd:
    def test_no_tickers(self, runner):
        from augur.cli_commands.batch_cmd import batch_cmd
        result = runner.invoke(batch_cmd, [])
        assert result.exit_code != 0  # requires argument

    def test_invalid_ticker_graceful(self, runner):
        from augur.cli_commands.batch_cmd import batch_cmd
        result = runner.invoke(batch_cmd, ["BADTICKERXYZ"])
        # Should not crash — network failure handled gracefully
        assert result.exit_code == 0
        assert "Batch Analysis" in result.output


class TestValuationCmd:
    def test_valuation(self, runner):
        from augur.cli_commands.valuation_cmd import valuation_cmd
        result = runner.invoke(valuation_cmd, [
            "TEST", "--fcf", "100e9", "--shares", "15.5e9", "--net-debt", "50e9",
        ])
        assert result.exit_code == 0
        assert "DCF Valuation" in result.output
        assert "Fair Value" in result.output


class TestCompatCmd:
    def test_compat(self, runner):
        from augur.cli_commands.compat_cmd import compat_cmd
        result = runner.invoke(compat_cmd, [])
        assert result.exit_code == 0
        assert "Compatibility Report" in result.output


class TestDossierCmd:
    def test_dossier(self, runner):
        from augur.cli_commands.dossier_cmd import dossier_cmd
        result = runner.invoke(dossier_cmd, ["TEST"])
        assert result.exit_code == 0
        assert "Pre-Earnings Dossier" in result.output

    def test_dossier_markdown(self, runner):
        from augur.cli_commands.dossier_cmd import dossier_cmd
        result = runner.invoke(dossier_cmd, ["TEST", "--format", "markdown"])
        assert result.exit_code == 0


class TestLedgerCmd:
    def test_ledger(self, runner):
        from augur.cli_commands.ledger_cmd import ledger_cmd
        result = runner.invoke(ledger_cmd, ["TEST", "Q3_2025", "Q4_2025"])
        assert result.exit_code == 0
        assert "Change Ledger" in result.output


class TestEarningsCmd:
    def test_earnings(self, runner):
        from augur.cli_commands.earnings_cmd import earnings_cmd
        result = runner.invoke(earnings_cmd, ["--ticker", "NONEXISTENT"])
        assert result.exit_code == 0


class TestResearchReportCmd:
    """research-report reads a saved run (it used to print an empty shell)."""

    @pytest.fixture
    def seeded_run(self, monkeypatch, tmp_path):
        import augur.data as data_module
        from augur.datasources.base import DataProvider
        from augur.workflow import run_workflow

        class _Provider(DataProvider):
            name = "mock_report"

            def fetch(self, ticker):
                return {"data_source": "mock_report", "price": 100.0, "pe": 18.0, "roe": 0.2}

        monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path / "augur_data"))
        monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")
        monkeypatch.setattr(data_module, "_get_providers", lambda: [_Provider()])
        return run_workflow("TEST", steps="fetch,analyze,consensus")

    def test_research_report(self, runner, seeded_run):
        from augur.cli_commands.research_report_cmd import research_report_cmd
        result = runner.invoke(research_report_cmd, ["TEST"])
        assert result.exit_code == 0, result.output
        assert "Research Report" in result.output
        assert seeded_run["run_id"] in result.output

    def test_research_report_json(self, runner, seeded_run):
        from augur.cli_commands.research_report_cmd import research_report_cmd
        result = runner.invoke(research_report_cmd, ["TEST", "--format", "json"])
        assert result.exit_code == 0, result.output
        assert '"ticker"' in result.output
        assert seeded_run["run_id"] in result.output
