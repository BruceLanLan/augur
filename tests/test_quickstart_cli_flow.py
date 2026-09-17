# -*- coding: utf-8 -*-
"""The README quickstart must work as written: workflow, then export.

Found by running the quickstart from a fresh wheel install (2026-09-17):
``augur export AAPL --format md`` exited with "Missing option '--run-id'",
and ``augur workflow`` never told the user which run id it had produced.
"""
import pytest
from click.testing import CliRunner

from augur.datasources.base import DataProvider


class _Provider(DataProvider):
    name = "mock_quickstart"

    def fetch(self, ticker):
        return {"data_source": "mock_quickstart", "price": 150.0, "pe": 20.0, "roe": 0.18}


@pytest.fixture
def offline_provider(monkeypatch, tmp_path):
    import augur.data as data_module

    # The hermetic data root is shared across the session; "latest run for a
    # ticker" needs a root this test owns.
    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path / "augur_data"))

    monkeypatch.setattr(data_module, "_get_providers", lambda: [_Provider()])
    # Consensus otherwise pulls live VIX/SPY history for regime detection.
    monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")


def _cli():
    from augur.cli import main

    return main


def test_workflow_prints_run_id_and_export_hint(offline_provider):
    result = CliRunner().invoke(_cli(), ["workflow", "AAPL"])

    assert result.exit_code == 0, result.output
    assert "Run ID: run_" in result.output
    assert "augur export AAPL" in result.output


def test_export_without_run_id_uses_latest_run_for_ticker(offline_provider, tmp_path):
    from augur.workflow import run_workflow

    run_workflow("MSFT", steps="fetch,analyze,consensus")
    latest = run_workflow("AAPL", steps="fetch,analyze,consensus")

    out = tmp_path / "report.md"
    result = CliRunner().invoke(_cli(), ["export", "AAPL", "--format", "md", "-o", str(out)])

    assert result.exit_code == 0, result.output
    assert f"Run ID: {latest['run_id']}" in result.output
    assert out.exists() and out.stat().st_size > 0


def test_export_without_any_run_explains_next_step(offline_provider):
    result = CliRunner().invoke(_cli(), ["export", "NVDA"])

    assert result.exit_code == 1
    assert "augur workflow NVDA" in result.output


def test_research_report_uses_latest_run(offline_provider):
    """`augur research-report` used to call ResearchReportBuilder().build(ticker)
    with no inputs, so it always printed only a title."""
    from augur.workflow import run_workflow

    latest = run_workflow("AAPL", steps="fetch,analyze,consensus")
    result = CliRunner().invoke(_cli(), ["research-report", "AAPL"])

    assert result.exit_code == 0, result.output
    assert "## Consensus" in result.output
    assert "## Disagreement Map" in result.output
    assert "## Provenance" in result.output
    assert latest["run_id"] in result.output


def test_research_report_without_any_run_explains_next_step(offline_provider):
    result = CliRunner().invoke(_cli(), ["research-report", "NVDA"])

    assert result.exit_code == 1
    assert "augur workflow NVDA" in result.output


def test_evidence_pack_honours_output_path(offline_provider, tmp_path):
    from augur.workflow import run_workflow

    run_workflow("AAPL", steps="fetch,analyze,consensus")
    target = tmp_path / "out" / "pack.zip"
    result = CliRunner().invoke(_cli(), ["export", "AAPL", "--format", "evidence-pack", "-o", str(target)])

    assert result.exit_code == 0, result.output
    assert target.exists()


def test_dossier_shows_disagreement_from_latest_run(offline_provider):
    from augur.workflow import run_workflow

    latest = run_workflow("AAPL", steps="fetch,analyze,consensus")
    result = CliRunner().invoke(_cli(), ["dossier", "AAPL"])

    assert result.exit_code == 0, result.output
    assert f"From run {latest['run_id']}" in result.output
