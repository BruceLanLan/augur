# -*- coding: utf-8 -*-
"""augur.cli_commands.filing_delta_cmd — ``augur filing-delta`` command."""

from __future__ import annotations

import json

import click

from augur.filing_delta import FilingDeltaCLI


@click.command("filing-delta")
@click.argument("ticker")
@click.option(
    "--new", "-n",
    "new_path",
    required=True,
    help="Path to the newer filing JSON evidence file.",
)
@click.option(
    "--prev", "-p",
    "prev_path",
    required=True,
    help="Path to the previous filing JSON evidence file.",
)
@click.option(
    "--format", "-f",
    "fmt",
    type=click.Choice(["md", "json"], case_sensitive=False),
    default="md",
    help="Output format: md (Markdown table) or json.",
)
@click.option(
    "--run-id",
    default=None,
    help="Optional RunBundle ID for provenance.",
)
def filing_delta_cmd(
    ticker: str,
    new_path: str,
    prev_path: str,
    fmt: str,
    run_id: str | None,
) -> None:
    """Compare two SEC filing snapshots and report material deltas.

    \b
    Reads two JSON evidence files (e.g. from ``augur export --format json``)
    and produces a structured comparison showing numeric changes, text changes,
    and guidance changes in Markdown-table or JSON format.

    \b
    Examples:
      augur filing-delta AAPL --new filing_new.json --prev filing_prev.json
      augur filing-delta NVDA --new q3.json --prev q2.json --format json
    """
    # Load filing data from JSON files
    try:
        with open(new_path, "r", encoding="utf-8") as f:
            new_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        click.echo(f"Error reading --new file '{new_path}': {e}", err=True)
        raise SystemExit(1)

    try:
        with open(prev_path, "r", encoding="utf-8") as f:
            prev_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        click.echo(f"Error reading --prev file '{prev_path}': {e}", err=True)
        raise SystemExit(1)

    # Build and format the report
    try:
        report = FilingDeltaCLI.run(
            ticker=ticker,
            new_data=new_data,
            prev_data=prev_data,
            run_id=run_id,
        )
    except Exception as e:
        click.echo(f"Error building delta report: {e}", err=True)
        raise SystemExit(1)

    output = FilingDeltaCLI.format_output(report, fmt=fmt)
    click.echo(output)
