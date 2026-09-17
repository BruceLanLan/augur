# -*- coding: utf-8 -*-
"""Risk-factor review CLI — compare Item 1A across the two latest 10-K filings."""
from __future__ import annotations

import click


@click.command("risk-review")
@click.argument("ticker")
@click.option("--limit", default=8, show_default=True, help="Items to show per section.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
def risk_review_cmd(ticker, limit, as_json):
    """New, escalated and removed risk factors between the two latest 10-Ks.

    Reads Item 1A from SEC EDGAR (set AUGUR_EDGAR_CONTACT_EMAIL). Matching and
    classification are rule-based, not an LLM: a reworded risk factor can show
    up as one "new" plus one "removed" item.
    """
    import dataclasses
    import json

    from augur.risk_review import RiskReviewer, fetch_10k_risk_sections

    try:
        src = fetch_10k_risk_sections(ticker)
    except LookupError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    report = RiskReviewer(ticker).review(
        src["new_text"], src["prev_text"], filing_accession=src["new_accession"],
    )
    if as_json:
        payload = dataclasses.asdict(report)
        payload["compared_with"] = {"accession": src["prev_accession"], "filed": src["prev_filed"]}
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    click.echo(f"═══ Risk Factor Review: {ticker.upper()} ═══")
    click.echo(f"  10-K {src['new_accession']} (filed {src['new_filed']})")
    if src["prev_accession"]:
        click.echo(f"  vs 10-K {src['prev_accession']} (filed {src['prev_filed']})")
    else:
        click.echo("  (only one 10-K on file — nothing to compare against)")
    click.echo(f"  {report.summary}")
    for title, items in (("New", report.new_risks), ("Escalated wording", report.escalated_risks),
                         ("Removed", report.removed_risks), ("Critical", report.critical_risks)):
        if not items:
            continue
        click.echo(f"\n── {title} ({len(items)}) ──")
        for item in items[:limit]:
            click.echo(f"  [{item.severity}/{item.category}] {_shorten(item.description, 160)}")


def _shorten(text: str, limit: int) -> str:
    """Collapse whitespace and cut at a word boundary with an ellipsis."""
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    cut = flat[:limit].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"
