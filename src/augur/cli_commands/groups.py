# -*- coding: utf-8 -*-
"""v14 "one command tree": grouped forms of the flat top-level commands.

The grouped subcommands are the *same* ``click.Command`` objects as the flat
ones, so behaviour, options, stdout and exit codes are identical. The flat
names stay registered as thin copies that print a one-line deprecation note to
**stderr** (never stdout, which scripts and tests parse) before running.

    augur watchlist add|show|watch      <- watchlist-add, watchlist-show, watch
    augur cron run|start                <- cron-run, cron-start
    augur report run|from-run           <- report (live), research-report (saved run)
    augur eval ic                       <- ic-report
    augur records citations|comments|audit|decisions|ledger|verify-pack
    augur skill compat|profiles         <- compat, skills

``augur report TICKER`` keeps working unchanged: ``report`` is a group that
forwards any first token that is not a subcommand name to ``report run``.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict, List, Tuple

import click

from augur.cli_commands.analysis import report_cmd
from augur.cli_commands.backtest import ic_report_cmd
from augur.cli_commands.compat_cmd import compat_cmd
from augur.cli_commands.eval_cmd import eval_cmd
from augur.cli_commands.export_cmd import verify_pack_cmd
from augur.cli_commands.ledger_cmd import ledger_cmd
from augur.cli_commands.meta import skills_cmd, update_cmd
from augur.cli_commands.monitor import watch_cmd
from augur.cli_commands.records_cmd import audit_cmd, citations_cmd, comments_cmd, decisions_cmd
from augur.cli_commands.research_report_cmd import research_report_cmd
from augur.cli_commands.skill_cmd import skill_cmd
from augur.cli_commands.watchlist import (
    cron_run_cmd, cron_start_cmd, watchlist_add_cmd, watchlist_show_cmd,
)


class ReportGroup(click.Group):
    """``augur report`` group that still accepts ``augur report TICKER ...``.

    If the first token is not a subcommand name (and not ``--help``), the
    arguments are forwarded to ``report run``, i.e. the pre-v14 behaviour.
    """

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        if args and args[0] not in self.commands and args[0] not in ctx.help_option_names:
            args = ["run", *args]
        return super().parse_args(ctx, args)

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        super().format_options(ctx, formatter)
        run = self.commands.get("run")
        if run is None:
            return
        rows = [r for p in run.get_params(ctx) if (r := p.get_help_record(ctx)) and "--help" not in r[0]]
        if rows:
            with formatter.section("Options for `augur report TICKER` / `augur report run TICKER`"):
                formatter.write_dl(rows)


@click.group("watchlist")
def watchlist_group():
    """Manage and monitor the watchlist (add / show / watch)."""


@click.group("cron")
def cron_group():
    """Scheduled watchlist analysis (run once / start daemon)."""


@click.group("report", cls=ReportGroup, no_args_is_help=True)
def report_group():
    """Reports: live deep report, or a report from a saved run.

    \b
    augur report TICKER [OPTIONS]        same as `augur report run TICKER`
    augur report run AAPL -o aapl.md     live analysis -> deep report
    augur report from-run AAPL           report from the latest saved run
                                         (was `augur research-report`)
    """


@click.group("records")
def records_group():
    """Research records: citations, comments, audit log, decisions, ledger, packs."""


# (group, subcommand name, command, old flat name or None if not deprecated)
_TREE: List[Tuple[click.Group, str, click.Command, str]] = [
    (watchlist_group, "add", watchlist_add_cmd, "watchlist-add"),
    (watchlist_group, "show", watchlist_show_cmd, "watchlist-show"),
    (watchlist_group, "watch", watch_cmd, "watch"),
    (cron_group, "run", cron_run_cmd, "cron-run"),
    (cron_group, "start", cron_start_cmd, "cron-start"),
    (report_group, "run", report_cmd, ""),
    (report_group, "from-run", research_report_cmd, "research-report"),
    (eval_cmd, "ic", ic_report_cmd, "ic-report"),
    (records_group, "citations", citations_cmd, "citations"),
    (records_group, "comments", comments_cmd, "comments"),
    (records_group, "audit", audit_cmd, "audit"),
    (records_group, "decisions", decisions_cmd, "decisions"),
    (records_group, "ledger", ledger_cmd, "ledger"),
    (records_group, "verify-pack", verify_pack_cmd, "verify-pack"),
    (skill_cmd, "compat", compat_cmd, "compat"),
    (skill_cmd, "profiles", skills_cmd, "skills"),
]

_alias_classes: Dict[type, type] = {}


def _alias_class(base: type) -> type:
    """Subclass of ``base`` whose parse_args prints the deprecation note first."""
    if base not in _alias_classes:

        def parse_args(self, ctx, args):
            if not ctx.resilient_parsing and getattr(self, "_v14_note", None):
                click.echo(self._v14_note, err=True)
            return base.parse_args(self, ctx, args)

        _alias_classes[base] = type(f"Deprecated{base.__name__}", (base,), {"parse_args": parse_args})
    return _alias_classes[base]


def deprecated_alias(cmd: click.Command, old: str, new: str) -> click.Command:
    """Shallow copy of ``cmd`` that prints a one-line note to stderr when used."""
    alias = copy.copy(cmd)
    alias.__class__ = _alias_class(type(cmd))
    alias._v14_note = f"note: `augur {old}` is now `augur {new}`; the old name keeps working until the next major release"
    # Listed once, under its group, in `augur --help`.
    alias.hidden = True
    return alias


def _is_git_checkout() -> bool:
    # cli_commands/groups.py -> cli_commands -> augur -> src -> repo root
    return (Path(__file__).resolve().parents[3] / ".git").exists()


def register_groups(main: click.Group) -> None:
    """Add the grouped tree to ``main`` and turn flat names into noted aliases."""
    for group, sub, cmd, old in _TREE:
        group.add_command(cmd, name=sub)
        if old:
            new = f"{group.name} {sub}"
            main.add_command(deprecated_alias(cmd, old, new), name=old)
    for group in (watchlist_group, cron_group, report_group, records_group):
        main.add_command(group)
    # `augur update` does `git pull` in the source checkout; under a pip
    # install there is none, so keep it callable (it explains itself) but hidden.
    if not _is_git_checkout():
        update_cmd.hidden = True
