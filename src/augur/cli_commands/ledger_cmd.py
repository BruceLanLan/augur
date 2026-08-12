# -*- coding: utf-8 -*-
"""Change Ledger CLI — cross-quarter change comparison."""
from __future__ import annotations

import click

from augur.change_ledger import ChangeLedgerBuilder


@click.command("ledger")
@click.argument("ticker")
@click.argument("prev_quarter")
@click.argument("new_quarter")
def ledger_cmd(ticker, prev_quarter, new_quarter):
    """Show cross-quarter change ledger for a ticker."""
    # In production this loads RunBundles for the two quarters.
    # MVP: show the ledger structure with a placeholder note.
    prev = {"quarter": prev_quarter}
    new = {"quarter": new_quarter}
    ledger = ChangeLedgerBuilder.build(prev, new, ticker)
    lines = [f"═══ Change Ledger: {ticker.upper()} {prev_quarter}→{new_quarter} ═══", ""]
    if ledger.entries:
        for e in ledger.entries:
            lines.append(f"  [{e.category}] {e.before} → {e.after}")
    else:
        lines.append("  No changes detected between quarters.")
    lines.append("")
    lines.append(f"Summary: {ledger.summary}")
    click.echo("\n".join(lines))
