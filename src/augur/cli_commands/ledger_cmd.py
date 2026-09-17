# -*- coding: utf-8 -*-
"""Change Ledger CLI — what changed between two saved analysis runs."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import click

from augur.change_ledger import ChangeLedgerBuilder

_QUARTER = re.compile(r"^Q([1-4])[_\-\s]?(\d{4})$", re.IGNORECASE)


def _snapshot(run_id: str, ticker: str) -> Dict[str, Any]:
    """Ledger snapshot of a RunBundle: evidence metrics, persona risks, disagreement."""
    import dataclasses

    from augur.disagreement import build_disagreement_from_bundle
    from augur.run_tracker import extract_persona_results, load_run_bundle_dict

    bundle = load_run_bundle_dict(run_id)
    metrics: Dict[str, float] = {}
    for step in bundle.get("step_results", []):
        result = step.get("result")
        if isinstance(result, dict):
            for item in result.get("evidence_items") or []:
                if isinstance(item, dict) and not item.get("missing") and isinstance(item.get("value"), (int, float)):
                    metrics.setdefault(item["metric"], float(item["value"]))
    personas, _consensus = extract_persona_results(bundle)
    risks = sorted({r for p in personas.values() for r in (p.get("risks") or [])})
    return {
        "run_id": run_id,
        "date": str(bundle.get("created_at", ""))[:10],
        "metrics": metrics,
        "risks": risks,
        "disagreement": dataclasses.asdict(build_disagreement_from_bundle(bundle, ticker, run_id)),
    }


def _analysed_runs(ticker: str) -> List[str]:
    from augur.run_tracker import bundle_has_persona_analysis, list_run_ids, load_run_bundle_dict

    return [r for r in list_run_ids(ticker) if bundle_has_persona_analysis(load_run_bundle_dict(r))]


def _resolve(ref: Optional[str], ticker: str, runs: List[str]) -> Optional[str]:
    """A run id, or a quarter label (newest analysed run created in that quarter)."""
    if ref is None:
        return None
    m = _QUARTER.match(ref)
    if not m:
        return ref if ref in runs else None
    quarter, year = int(m.group(1)), m.group(2)
    months = {f"{year}-{mm:02d}" for mm in range(3 * quarter - 2, 3 * quarter + 1)}
    for run_id in runs:  # newest first
        stamp = re.search(r"_(\d{4})(\d{2})\d{2}T", run_id)
        if stamp and f"{stamp.group(1)}-{stamp.group(2)}" in months:
            return run_id
    return None


@click.command("ledger")
@click.argument("ticker")
@click.argument("previous", required=False)
@click.argument("new", required=False)
def ledger_cmd(ticker, previous, new):
    """What changed between two saved runs: metrics, persona risks, disagreement.

    \b
    Examples:
      augur ledger AAPL                          # two most recent analysed runs
      augur ledger AAPL run_AAPL_... run_AAPL_... # specific runs
      augur ledger AAPL Q2_2026 Q3_2026          # newest run in each quarter
    """
    ticker = ticker.upper()
    runs = _analysed_runs(ticker)
    if previous is None and new is None:
        if len(runs) < 2:
            click.echo(f"Error: need two saved runs with persona analysis for {ticker} "
                       f"(found {len(runs)}). Run `augur workflow {ticker}` again later.", err=True)
            raise SystemExit(1)
        new_id, prev_id = runs[0], runs[1]
    else:
        prev_id, new_id = _resolve(previous, ticker, runs), _resolve(new, ticker or "", runs)
        missing = [ref for ref, rid in ((previous, prev_id), (new, new_id)) if ref is not None and rid is None]
        if new is None:
            missing.append("<new run>")
        if missing:
            click.echo(f"Error: no saved analysed run for {ticker} matching: {', '.join(missing)}", err=True)
            raise SystemExit(1)

    prev_snap, new_snap = _snapshot(prev_id, ticker), _snapshot(new_id, ticker)
    ledger = ChangeLedgerBuilder.build(prev_snap, new_snap, ticker)
    lines = [f"═══ Change Ledger: {ticker} ═══",
             f"  {prev_id} ({prev_snap['date']}) → {new_id} ({new_snap['date']})", ""]
    if ledger.entries:
        for e in ledger.entries:
            flag = " ⚠" if getattr(e, "material", False) else ""
            lines.append(f"  [{e.category}] {e.before} → {e.after}{flag}")
    else:
        lines.append("  No changes detected between the two runs.")
    lines.append("")
    lines.append(f"Summary: {ledger.summary}")
    click.echo("\n".join(lines))
