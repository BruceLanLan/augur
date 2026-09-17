# -*- coding: utf-8 -*-
"""Research report CLI — aggregated v11 research report."""
from __future__ import annotations

import dataclasses

import click

from augur.research_report import ResearchReportBuilder


@click.command("research-report")
@click.argument("ticker")
@click.option("--run-id", "-r", default=None,
              help="RunBundle to report on. Defaults to the most recent run for TICKER.")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
def research_report_cmd(ticker, run_id, fmt):
    """Generate a research report from a saved analysis run.

    \b
    Examples:
      augur workflow AAPL && augur research-report AAPL
      augur research-report AAPL --format json
    """
    from augur.disagreement import build_disagreement_from_bundle
    from augur.run_tracker import extract_persona_results, latest_run_id, load_run_bundle_dict

    ticker = ticker.upper()
    run_id = run_id or latest_run_id(ticker, require_persona_analysis=True)
    if not run_id:
        click.echo(f"Error: no saved runs for {ticker}. Run `augur workflow {ticker}` first.", err=True)
        raise SystemExit(1)
    try:
        bundle = load_run_bundle_dict(run_id)
    except FileNotFoundError:
        click.echo(f"Error: run {run_id} not found.", err=True)
        raise SystemExit(1)

    persona_outputs, consensus = extract_persona_results(bundle)
    steps = {sr.get("step_name"): sr for sr in bundle.get("step_results", [])}
    if isinstance(consensus.get("score"), (int, float)):
        consensus["score"] = f"{consensus['score']:.2f} / 10"
    if isinstance(consensus.get("confidence"), (int, float)):
        consensus["confidence"] = f"{consensus['confidence']:.0%}"
    if persona_outputs:
        signals = [p.get("signal") for p in persona_outputs.values()]
        consensus["vote"] = (
            f"bullish {signals.count('bullish')} / neutral {signals.count('neutral')} / "
            f"bearish {signals.count('bearish')}"
        )

    disagreement = {}
    if persona_outputs:
        disagreement = dataclasses.asdict(build_disagreement_from_bundle(bundle, ticker, run_id))

    coverage = bundle.get("coverage") or {}
    provenance = {
        "run_id": run_id,
        "run_created_at": bundle.get("created_at", ""),
        "code_version": (bundle.get("metadata") or {}).get("code_version", ""),
        "steps": ", ".join(f"{name}={sr.get('status')}" for name, sr in steps.items()),
        "evidence_coverage": coverage.get("coverage_ratio", "n/a"),
    }
    cost = (bundle.get("metadata") or {}).get("cost")
    if cost:
        provenance["latency_ms"] = f"{cost.get('total_latency', 0):.0f} total (" + ", ".join(
            f"{sc['step_name']} {sc['latency_ms']:.0f}" for sc in cost.get("step_costs", [])
        ) + ")"

    report = ResearchReportBuilder().build(
        ticker, run_id=run_id, consensus=consensus,
        disagreement=disagreement, provenance=provenance,
    )
    if fmt == "json":
        click.echo(report.to_json())
    else:
        click.echo(report.to_markdown())
