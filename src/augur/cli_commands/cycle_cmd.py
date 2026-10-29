# -*- coding: utf-8 -*-
"""Earnings cycle CLI — run the watchlist through the research cycle from saved state."""
from __future__ import annotations

from typing import List, Optional

import click

_NEXT_STEP = {
    "fundamentals_snapshot": "run `augur workflow {t}`",
    "recent_filings": "run `augur workflow {t}` with SEC EDGAR reachable (latest run has no SEC evidence)",
    "prior_guidance": "record prior guidance for {t} (GuidanceTracker)",
}


def _watchlist_tickers() -> List[str]:
    import yaml

    from augur.data_dir import get_data_dir
    from augur.earnings import _watchlist_tickers as parse

    path = get_data_dir() / "watchlist.yaml"
    if not path.exists():
        return []
    try:
        return parse(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except (OSError, yaml.YAMLError):
        return []


def _ledger_summary(ticker: str) -> str:
    from augur.change_ledger import ChangeLedgerBuilder
    from augur.cli_commands.ledger_cmd import _analysed_runs, _snapshot

    try:
        runs = _analysed_runs(ticker)
        if len(runs) < 2:
            return (f"unavailable: need two saved runs with persona analysis (found {len(runs)}) "
                    f"— next step: run `augur workflow {ticker}` again later")
        ledger = ChangeLedgerBuilder.build(_snapshot(runs[1], ticker), _snapshot(runs[0], ticker), ticker)
        return f"{runs[1]} → {runs[0]}: {ledger.summary}"
    except Exception as exc:  # a broken run should not stop the whole cycle
        return f"unavailable: {exc}"


def _thesis_summary(ticker: str) -> str:
    from augur.cli_commands.thesis_delta_cmd import thesis_delta_summary

    try:
        return thesis_delta_summary(ticker)
    except Exception as exc:
        return f"unavailable: {exc}"


def _next_step(ticker: str, missing: List[str], run_id: Optional[str]) -> str:
    if not missing:
        return f"ready — review `augur dossier {ticker}` before the call; after it, `augur scorecard {ticker}`"
    return "; ".join(_NEXT_STEP.get(m, f"provide {m}").format(t=ticker) for m in missing)


@click.command("cycle")
@click.option("--days", default=30, show_default=True, type=int, help="Look-ahead window for earnings events")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "markdown"]), show_default=True)
def cycle_cmd(days, fmt):
    """Run the watchlist through the earnings research cycle (offline).

    For each watchlist ticker with an earnings event in the next N days:
    dossier readiness, the dossier, the change ledger and the thesis delta.
    Reads saved state only (watchlist, earnings calendar, runs, theses) and
    never fetches data.

    \b
    Examples:
      augur cycle
      augur cycle --days 14 --format markdown
    """
    from augur.cli_commands.dossier_cmd import run_earnings_dossier
    from augur.earnings import EarningsEventService

    svc = EarningsEventService()
    events = svc.identify_events_for_watchlist(lookahead_days=days)
    statuses = svc.check_dossier_readiness(events)
    md = fmt == "markdown"

    def head(text: str, level: int = 2) -> str:
        return f"{'#' * level} {text}" if md else (f"═══ {text} ═══" if level == 1 else f"── {text} ──")

    out: List[str] = [head(f"Earnings Cycle — next {days} days", 1), ""]
    tickers = _watchlist_tickers()
    if not tickers:
        out.append("Watchlist is empty — next step: `augur watchlist-add TICKER`.")
    with_event = {s.ticker for s in statuses}
    no_event = [t for t in tickers if t not in with_event]

    for s in statuses:
        t = s.ticker
        ev = s.event
        out.append(head(f"{t} · {ev.event_date} ({ev.confidence}{', ' + ev.fiscal_period if ev.fiscal_period else ''})"))
        state = "ready" if s.ready else "not ready"
        out.append(f"Readiness: {state}" + (f" — missing: {', '.join(s.missing_items)}" if s.missing_items else ""))
        out.append(f"Latest run: {s.run_id or 'none'}")
        out.append("")
        try:
            out.append(run_earnings_dossier(t, output_format=fmt))
        except Exception as exc:
            out.append(f"Dossier unavailable: {exc}")
        out.append("")
        out.append(f"Ledger: {_ledger_summary(t)}")
        thesis = _thesis_summary(t)
        out.append("Thesis delta: " + (thesis if "\n" not in thesis else "\n  " + thesis.replace("\n", "\n  ")))
        out.append("")

    ready = sum(1 for s in statuses if s.ready)
    out.append(head("Summary"))
    out.append(f"ready {ready}/{len(statuses)} earnings events within {days} days")
    if no_event:
        out.append(f"No calendar event within {days} days: {', '.join(no_event)}")
    if statuses:
        out.append("")
        out.append("Next steps:")
        for s in statuses:
            out.append(f"{'-' if md else ' '} {s.ticker}: {_next_step(s.ticker, s.missing_items, s.run_id)}")
    click.echo("\n".join(out))
