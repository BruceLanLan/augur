# -*- coding: utf-8 -*-
"""augur.cli_commands.export_cmd — export RunBundle to Markdown / JSON / PDF / Evidence Pack"""

from __future__ import annotations

from pathlib import Path

import click


@click.command("export")
@click.argument("ticker")
@click.option(
    "--run-id", "-r",
    default=None,
    help=(
        "Run ID to export (e.g. run_AAPL_20250101T120000_abc12345). "
        "Defaults to the most recent run for TICKER."
    ),
)
@click.option(
    "--format", "-f",
    "fmt",
    type=click.Choice(["md", "json", "pdf", "evidence-pack"], case_sensitive=False),
    default="md",
    help="Export format: md, json, pdf, or evidence-pack.",
)
@click.option(
    "--output", "-o",
    default=None,
    help=(
        "Output file path. Defaults to "
        "'{run_id}_report.{ext}' in the current directory."
    ),
)
@click.option(
    "--template", "-t",
    default="default",
    help="Jinja2 template string or 'default' for the built-in template (Markdown only).",
)
def export_cmd(
    ticker: str,
    run_id: str | None,
    fmt: str,
    output: str | None,
    template: str,
) -> None:
    """Export a completed analysis run.

    \b
    Examples:
      augur export AAPL                      # latest run, Markdown
      augur export AAPL --run-id run_AAPL_xxx --format md
      augur export AAPL --run-id run_AAPL_xxx --format pdf -o report.pdf
      augur export AAPL --run-id run_AAPL_xxx --format evidence-pack
    """
    from augur.export import ReportExporter

    if run_id is None:
        from augur.run_tracker import latest_run_id

        run_id = latest_run_id(ticker)
        if run_id is None:
            click.echo(
                f"Error: no saved runs for {ticker.upper()}. "
                f"Run `augur workflow {ticker.upper()}` first.",
                err=True,
            )
            raise SystemExit(1)

    # Determine output path
    ext_map = {
        "md": ".md",
        "json": ".json",
        "pdf": ".pdf",
        "evidence-pack": ".zip",
    }
    if output is None:
        output = f"{run_id}_report{ext_map.get(fmt, '.md')}"

    output_path = Path(output)

    try:
        exporter = ReportExporter()
        result_path = exporter.export_from_run_id(
            run_id=run_id,
            output_path=output_path,
            fmt=fmt,
            template=template,
        )
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"✓ Exported {fmt} to {result_path}")
    click.echo(f"  Ticker: {ticker.upper()}")
    click.echo(f"  Run ID: {run_id}")



@click.command("verify-pack")
@click.argument("pack", type=click.Path(exists=True, dir_okay=False))
def verify_pack_cmd(pack: str) -> None:
    """Verify an evidence pack's file digests and evidence coverage.

    \b
    Example:
      augur export AAPL --format evidence-pack -o aapl.zip
      augur verify-pack aapl.zip
    """
    import zipfile

    from augur.export import verify_evidence_pack

    try:
        result = verify_evidence_pack(Path(pack))
    except (ValueError, zipfile.BadZipFile) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if not result["has_digests"]:
        click.echo("Error: this pack predates per-file digests; re-export it to verify.", err=True)
        raise SystemExit(1)
    click.echo(f"Run ID: {result['run_id']}")
    click.echo(f"Files checked: {result['checked']}")
    for name in result["mismatched"]:
        click.echo(f"  ✗ digest mismatch: {name}")
    for ev_id in result["missing_evidence"]:
        click.echo(f"  ✗ evidence file missing: {ev_id}")
    if not result["ok"]:
        click.echo("FAILED: pack contents do not match its manifest.")
        raise SystemExit(1)
    click.echo("OK: every file matches the manifest digest.")
