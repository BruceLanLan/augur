# -*- coding: utf-8 -*-
"""Earnings dossier CLI — pre-event research dossier generation (B02)."""
from __future__ import annotations

def run_earnings_dossier(ticker: str, event_id: str = "", as_of: str = "", output_format: str = "text") -> str:
    """Generate a pre-earnings research dossier for a ticker.

    Combines: prior guidance, key KPI changes, persona disagreement,
    and unanswered questions into a structured dossier.
    """
    t = ticker.upper()
    sections: list = []
    sections.append(f"═══ Pre-Earnings Dossier: {t} ═══")

    # Prior guidance
    try:
        from augur.guidance_tracker import GuidanceTracker
        g = GuidanceTracker()
        history = g.get_history(t, "revenue")
        if history:
            latest = history[-1]
            sections.append("── Prior Guidance ──")
            sections.append(f"  Revenue: {latest.low} - {latest.high} ({latest.fiscal_period})")
    except Exception:
        pass

    # Earnings event readiness
    try:
        from augur.earnings import get_earnings_service
        svc = get_earnings_service()
        events = svc.detect_events([t], lookahead_days=30)
        if events:
            ev = events[0]
            sections.append("── Event ──")
            sections.append(f"  Date: {ev.event_date} ({ev.confidence})")
            statuses = svc.check_dossier_readiness([ev])
            if statuses and statuses[0].missing_items:
                sections.append(f"  Missing: {', '.join(statuses[0].missing_items)}")
            else:
                sections.append("  Readiness: ready")
    except Exception:
        pass

    # Persona disagreement
    sections.append("── Disagreement ──")
    try:
        from augur.disagreement import DisagreementMapBuilder
        from augur.run_tracker import latest_run_id, load_run_bundle_dict

        run_id = latest_run_id(ticker)
        persona_outputs = {}
        if run_id:
            steps = {sr.get("step_name"): sr for sr in load_run_bundle_dict(run_id).get("step_results", [])}
            persona_outputs = (steps.get("analyze") or {}).get("result") or {}
        if persona_outputs:
            dm = DisagreementMapBuilder(ticker, run_id).build(persona_outputs)
            sections.append(f"  From run {run_id}: consensus strength {dm.consensus_strength}")
            for cp in dm.conflict_points[:3]:
                sections.append(
                    f"  • {cp.claim} — bulls: {len(cp.bullish_personas)}, bears: {len(cp.bearish_personas)}"
                )
        else:
            sections.append(f"  No saved run yet — run `augur workflow {ticker.upper()}` first.")
    except Exception as e:  # keep the dossier usable even if a run is unreadable
        sections.append(f"  (disagreement unavailable: {e})")

    # Open questions
    try:
        from augur.questions import QuestionQueue
        q = QuestionQueue()
        questions = q.list(t, status="open")
        if questions:
            sections.append("── Open Questions ──")
            for question in questions[:5]:
                sections.append(f"  ? {question.question}")
    except Exception:
        pass

    dossier = "\n".join(sections)

    if output_format == "markdown":
        return "\n\n".join(f"## {s}" if s.startswith("──") else s for s in sections)
    return dossier


import click


@click.command("dossier")
@click.argument("ticker")
@click.option("--event-id", default="", help="Earnings event ID")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "markdown"]))
def dossier_cmd(ticker, event_id, fmt):
    """Generate a pre-earnings research dossier."""
    click.echo(run_earnings_dossier(ticker, event_id=event_id, output_format=fmt))
