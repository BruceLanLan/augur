# -*- coding: utf-8 -*-
"""Thesis delta CLI — check active theses against the two latest saved runs."""
from __future__ import annotations

from typing import List, Optional, Tuple

import click


def _active_theses(ticker: str) -> list:
    from augur.thesis import ThesisJournal

    return [t for t in ThesisJournal().list_by_ticker(ticker) if t.status == "active"]


def build_thesis_delta(
    ticker: str, previous: Optional[str] = None, new: Optional[str] = None,
) -> Tuple[Optional[str], List[Tuple[object, object]]]:
    """(unavailable reason or None, [(thesis, delta), ...]) for ``ticker``.

    Reads saved state only: the thesis journal and persisted RunBundles.
    """
    from augur.cli_commands.ledger_cmd import _resolve
    from augur.run_tracker import list_run_ids, load_run_bundle_dict
    from augur.thesis import compute_thesis_delta

    t = ticker.upper()
    theses = _active_theses(t)
    if not theses:
        return (f"no active thesis for {t} — next step: record one "
                f"in the dashboard (`augur serve`, POST /api/thesis/create)"), []
    runs = list_run_ids(t)
    if previous is None and new is None:
        if len(runs) < 2:
            return (f"need two saved runs for {t} (found {len(runs)}) — next step: "
                    f"run `augur workflow {t}` again after the next data update"), []
        new_id, prev_id = runs[0], runs[1]
    else:
        prev_id = _resolve(previous, t, runs) if previous else (runs[1] if len(runs) > 1 else None)
        new_id = _resolve(new, t, runs) if new else (runs[0] if runs else None)
        if prev_id is None or new_id is None:
            return (f"no saved run for {t} matching {previous or '<previous>'} / {new or '<new>'} "
                    f"— next step: omit the run ids to compare the two latest runs"), []
    try:
        prev_bundle, new_bundle = load_run_bundle_dict(prev_id), load_run_bundle_dict(new_id)
    except (OSError, ValueError) as exc:
        return f"saved run unreadable ({exc}) — next step: re-run `augur workflow {t}`", []
    return None, [(th, compute_thesis_delta(th, prev_bundle, new_bundle)) for th in theses]


def thesis_delta_summary(ticker: str) -> str:
    """One line per active thesis, or an explicit unavailable line."""
    reason, results = build_thesis_delta(ticker)
    if reason:
        return f"unavailable: {reason}"
    return "\n".join(
        f"{th.thesis_id}: {d.overall_assessment} "
        f"({len(d.fact_changes)} fact / {len(d.valuation_changes)} valuation / "
        f"{len(d.language_changes)} language changes, "
        f"{len(d.falsification_triggered)} falsification triggered)"
        for th, d in results
    )


@click.command("thesis-delta")
@click.argument("ticker")
@click.option("--prev", "previous", default=None, help="Previous run id or quarter label (e.g. Q2_2026)")
@click.option("--new", "new", default=None, help="New run id or quarter label")
def thesis_delta_cmd(ticker, previous, new):
    """Review active theses against the two latest saved runs (offline).

    \b
    Examples:
      augur thesis-delta AAPL
      augur thesis-delta AAPL --prev run_AAPL_... --new run_AAPL_...
    """
    from augur.thesis import format_thesis_delta_report

    reason, results = build_thesis_delta(ticker, previous, new)
    if reason:
        click.echo(f"Thesis delta {ticker.upper()} unavailable: {reason}")
        return
    click.echo("\n\n".join(format_thesis_delta_report(th, d) for th, d in results))
