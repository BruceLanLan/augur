# -*- coding: utf-8 -*-
"""`augur committee` must run.

Found by running the README examples from a fresh install (2026-09-17): the
command crashed with "No module named 'augur.agents'". It still imported
augur.agents / augur.scanner.fetch / augur.scanner.context, which were
removed in the v10.15 scanner cleanup, and no test invoked the command.
"""
import pytest
from click.testing import CliRunner

from augur.datasources.base import DataProvider


class _Provider(DataProvider):
    name = "mock_committee"

    def fetch(self, ticker):
        return {"data_source": "mock_committee", "price": 150.0, "pe": 20.0,
                "roe": 0.25, "gross_margins": 0.45, "market_cap": 900.0, "fcf": 40.0}


@pytest.fixture
def offline(monkeypatch):
    import augur.data as data_module

    monkeypatch.setattr(data_module, "_get_providers", lambda: [_Provider()])
    monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")


def _invoke(*args):
    from augur.cli import main

    return CliRunner().invoke(main, ["committee", *args])


def test_full_committee_runs_and_reports_verdict(offline):
    result = _invoke("AAPL", "-q", "Is the moat widening?")

    assert result.exit_code == 0, result.output
    assert "Investment Committee: AAPL" in result.output
    assert "Q: Is the moat widening?" in result.output
    assert "Verdict" in result.output
    assert "Vote:" in result.output


def test_preset_limits_the_committee(offline):
    result = _invoke("AAPL", "--preset", "value")

    assert result.exit_code == 0, result.output
    assert "Warren Buffett" in result.output
    assert "Cathie Wood" not in result.output


def test_unknown_agents_fail_cleanly(offline):
    result = _invoke("AAPL", "--agents", "nobody,no_one")

    assert result.exit_code == 1
    assert "No valid agents" in result.output
