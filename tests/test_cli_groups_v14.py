# -*- coding: utf-8 -*-
"""v14 grouped command tree: grouped paths resolve, flat names keep working
and print the deprecation note on stderr only."""
from __future__ import annotations

import pytest
from click.testing import CliRunner

from augur.cli import main

GROUPED = [
    ["watchlist", "add"], ["watchlist", "show"], ["watchlist", "watch"],
    ["cron", "run"], ["cron", "start"],
    ["report", "run"], ["report", "from-run"],
    ["eval", "ic"], ["eval", "personas"], ["eval", "factors"],
    ["records", "citations"], ["records", "comments"], ["records", "audit"],
    ["records", "decisions"], ["records", "ledger"], ["records", "verify-pack"],
    ["skill", "compat"], ["skill", "profiles"], ["skill", "list"],
]

FLAT = {
    "watchlist-add": "watchlist add",
    "watchlist-show": "watchlist show",
    "watch": "watchlist watch",
    "cron-run": "cron run",
    "cron-start": "cron start",
    "research-report": "report from-run",
    "ic-report": "eval ic",
    "citations": "records citations",
    "comments": "records comments",
    "audit": "records audit",
    "decisions": "records decisions",
    "ledger": "records ledger",
    "verify-pack": "records verify-pack",
    "compat": "skill compat",
    "skills": "skill profiles",
}


def _runner() -> CliRunner:
    # click >= 8.2 always keeps stderr separate; older click needs mix_stderr=False.
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


@pytest.mark.parametrize("path", GROUPED, ids=" ".join)
def test_grouped_path_resolves(path):
    result = _runner().invoke(main, [*path, "--help"])
    assert result.exit_code == 0, result.output
    assert f"{' '.join(path)} [OPTIONS]" in result.stdout
    assert "note:" not in result.stderr


@pytest.mark.parametrize("old,new", sorted(FLAT.items()))
def test_flat_name_still_works_with_note_on_stderr(old, new):
    result = _runner().invoke(main, [old, "--help"])
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.stdout
    assert "note:" not in result.stdout
    assert f"note: `augur {old}` is now `augur {new}`" in result.stderr
    assert result.stderr.count("\n") == 1


def test_report_help_documents_ticker_form():
    result = _runner().invoke(main, ["report", "--help"])
    assert result.exit_code == 0
    assert "augur report TICKER" in result.stdout
    assert "from-run" in result.stdout and "run" in result.stdout


def test_report_ticker_forwards_to_run(monkeypatch):
    import augur.cli_commands.analysis as analysis

    seen = {}

    def fake_callback(ticker, output, **kwargs):
        seen["ticker"] = ticker
        seen["output"] = output

    monkeypatch.setattr(analysis.report_cmd, "callback", fake_callback)
    result = _runner().invoke(main, ["report", "AAPL", "-o", "x.md"])
    assert result.exit_code == 0, result.output
    assert seen == {"ticker": "AAPL", "output": "x.md"}
    assert result.stderr == ""

    seen.clear()
    result = _runner().invoke(main, ["report", "-o", "y.md", "NVDA"])
    assert result.exit_code == 0, result.output
    assert seen == {"ticker": "NVDA", "output": "y.md"}


def test_top_level_help_lists_groups():
    result = _runner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for name in ("watchlist", "cron", "report", "records", "eval", "skill"):
        assert f"\n  {name} " in result.stdout


def test_grouped_and_flat_share_command_objects():
    from augur.cli_commands.watchlist import watchlist_add_cmd

    assert main.commands["watchlist"].commands["add"] is watchlist_add_cmd
    assert main.commands["watchlist-add"] is not watchlist_add_cmd
    assert main.commands["watchlist-add"].callback is watchlist_add_cmd.callback
