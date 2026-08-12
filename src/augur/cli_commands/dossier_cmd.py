# -*- coding: utf-8 -*-
"""Earnings dossier CLI — pre-event research dossier generation (B02)."""
from __future__ import annotations
from typing import Optional

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
    try:
        from augur.disagreement import DisagreementMapBuilder
        # Placeholder — would use latest RunBundle persona outputs
        sections.append("── Disagreement ──")
        sections.append("  (run analysis for full disagreement map)")
    except Exception:
        pass

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

from augur.cli_commands.dossier_cmd import run_earnings_dossier


@click.command("dossier")
@click.argument("ticker")
@click.option("--event-id", default="", help="Earnings event ID")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "markdown"]))
def dossier_cmd(ticker, event_id, fmt):
    """Generate a pre-earnings research dossier."""
    click.echo(run_earnings_dossier(ticker, event_id=event_id, output_format=fmt))
