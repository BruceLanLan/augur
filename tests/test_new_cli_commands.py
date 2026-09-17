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
    """ledger compares two saved runs (it used to print a placeholder for any input)."""

    @pytest.fixture
    def two_runs(self, monkeypatch, tmp_path):
        import augur.data as data_module
        from augur.datasources.base import DataProvider
        from augur.workflow import run_workflow

        values = {"pe": 20.0}

        class _Provider(DataProvider):
            name = "mock_ledger"

            def fetch(self, ticker):
                return {"data_source": "mock_ledger", "price": 100.0, "pe": values["pe"], "roe": 0.2,
                        "gross_margins": 0.4, "debt_ratio": 0.3}

        monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path / "augur_data"))
        monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")
        monkeypatch.setattr(data_module, "_get_providers", lambda: [_Provider()])
        data_module.clear_cache()
        first = run_workflow("TEST", steps="fetch,analyze,consensus")
        values["pe"] = 40.0
        data_module.clear_cache()  # fetch_market_context caches contexts for 3 minutes
        second = run_workflow("TEST", steps="fetch,analyze,consensus")
        return first["run_id"], second["run_id"]

    def test_ledger_defaults_to_two_latest_runs(self, runner, two_runs):
        from augur.cli_commands.ledger_cmd import ledger_cmd
        result = runner.invoke(ledger_cmd, ["TEST"])
        assert result.exit_code == 0, result.output
        assert f"{two_runs[0]}" in result.output and f"{two_runs[1]}" in result.output
        assert "pe: 20" in result.output and "40" in result.output

    def test_ledger_explicit_runs(self, runner, two_runs):
        from augur.cli_commands.ledger_cmd import ledger_cmd
        result = runner.invoke(ledger_cmd, ["TEST", two_runs[0], two_runs[1]])
        assert result.exit_code == 0, result.output

    def test_ledger_same_quarter_summary_names_run_dates(self, runner, two_runs):
        import re

        from augur.cli_commands.ledger_cmd import ledger_cmd
        result = runner.invoke(ledger_cmd, ["TEST"])
        assert result.exit_code == 0, result.output
        header = re.search(r"\((\d{4}-\d{2}-\d{2})\) → \S+ \((\d{4}-\d{2}-\d{2})\)", result.output)
        assert header, result.output
        assert re.search(rf"between runs on {header.group(1)} and {header.group(2)} \(both Q[1-4]_\d{{4}}\)",
                         result.output), result.output

    def test_ledger_without_runs_explains(self, runner, monkeypatch, tmp_path):
        from augur.cli_commands.ledger_cmd import ledger_cmd
        monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path / "empty"))
        result = runner.invoke(ledger_cmd, ["TEST", "Q3_2025", "Q4_2025"])
        assert result.exit_code == 1
        assert "no saved analysed run" in result.output


class TestInsiderCmd:
    def test_uses_library_fetch(self, runner, monkeypatch):
        import augur.ownership as ownership
        from augur.cli_commands.insider_cmd import insider_cmd
        from augur.ownership import InsiderTrade

        trades = [InsiderTrade("TEST", f"cik{i}", "", "2026-09-01", "buy", 100.0, 10.0, 1000.0) for i in range(3)]
        monkeypatch.setattr(ownership, "fetch_insider_trades", lambda ticker, as_of_date=None: trades)
        result = runner.invoke(insider_cmd, ["TEST"])
        assert result.exit_code == 0, result.output
        assert "cik2" in result.output


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
