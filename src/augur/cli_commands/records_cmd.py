# -*- coding: utf-8 -*-
"""Research-record CLI: citation corrections, review comments, audit log, decision outcomes."""
from __future__ import annotations

import click


def _echo_table(rows, headers):
    if not rows:
        return
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    click.echo("  ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
    click.echo("  ".join("-" * w for w in widths))
    for r in rows:
        click.echo("  ".join(str(c).ljust(w) for c, w in zip(r, widths)))


# ---------------------------------------------------------------------------
# augur citations
# ---------------------------------------------------------------------------

@click.group("citations")
def citations_cmd():
    """Report and triage wrong citations (accepted ones become regression cases)."""


@citations_cmd.command("report")
@click.argument("ticker")
@click.option("--claim-id", required=True, help="Claim whose citation is wrong.")
@click.option("--issue", "issue_type", required=True,
              type=click.Choice(["wrong_source", "fabricated", "misattributed", "outdated"]))
@click.option("--wrong", "incorrect_refs", multiple=True, help="Evidence id cited incorrectly (repeatable).")
@click.option("--correct", "correct_refs", multiple=True, help="Evidence id that should be cited (repeatable).")
@click.option("--note", default="", help="Free-text description.")
def citations_report_cmd(ticker, claim_id, issue_type, incorrect_refs, correct_refs, note):
    """Report a citation error on a claim."""
    from augur.citation_queue import CitationCorrectionQueue
    from augur.team_audit import record_action

    cc = CitationCorrectionQueue().report(
        claim_id=claim_id, ticker=ticker, issue_type=issue_type,
        incorrect_refs=list(incorrect_refs), correct_refs=list(correct_refs), description=note,
    )
    record_action("citation_report", {"correction_id": cc.correction_id, "ticker": cc.ticker})
    click.echo(f"Reported {cc.correction_id} ({cc.issue_type}) on {cc.claim_id} — status: {cc.status}")


@citations_cmd.command("list")
@click.option("--status", type=click.Choice(["open", "accepted", "rejected", "fixed", "all"]), default="open")
def citations_list_cmd(status):
    """List citation corrections."""
    from augur.citation_queue import CitationCorrectionQueue

    queue = CitationCorrectionQueue()
    items = queue.get_corpus().corrections
    if status != "all":
        items = [c for c in items if c.status == status]
    if not items:
        click.echo(f"No {status if status != 'all' else ''} citation corrections.".replace("  ", " "))
        return
    _echo_table(
        [(c.correction_id, c.ticker, c.claim_id, c.issue_type, c.status, c.created_at[:10]) for c in items],
        ["ID", "TICKER", "CLAIM", "ISSUE", "STATUS", "REPORTED"],
    )


def _transition(action: str, correction_id: str, reason: str = ""):
    from augur.citation_queue import CitationCorrectionQueue
    from augur.team_audit import record_action

    queue = CitationCorrectionQueue()
    if action == "accept":
        cc = queue.accept(correction_id)
    elif action == "reject":
        cc = queue.reject(correction_id, reason)
    else:
        cc = queue.mark_fixed(correction_id)
    if cc is None:
        click.echo(f"Error: no citation correction {correction_id}", err=True)
        raise SystemExit(1)
    record_action(f"citation_{action}", {"correction_id": correction_id})
    click.echo(f"{correction_id} → {cc.status}")


@citations_cmd.command("accept")
@click.argument("correction_id")
def citations_accept_cmd(correction_id):
    """Accept a reported correction (adds it to the regression corpus)."""
    _transition("accept", correction_id)


@citations_cmd.command("reject")
@click.argument("correction_id")
@click.option("--reason", default="")
def citations_reject_cmd(correction_id, reason):
    """Reject a reported correction."""
    _transition("reject", correction_id, reason)


@citations_cmd.command("fixed")
@click.argument("correction_id")
def citations_fixed_cmd(correction_id):
    """Mark an accepted correction as fixed."""
    _transition("fixed", correction_id)


# ---------------------------------------------------------------------------
# augur comments
# ---------------------------------------------------------------------------

@click.group("comments")
def comments_cmd():
    """Review comments on runs, theses, decisions, claims and evidence."""


@comments_cmd.command("add")
@click.argument("target_type", type=click.Choice(["run", "thesis", "decision", "claim", "evidence"]))
@click.argument("target_id")
@click.argument("text")
@click.option("--author", default="local")
def comments_add_cmd(target_type, target_id, text, author):
    """Add a comment, e.g. `augur comments add run run_AAPL_... "check FCF source"`."""
    from augur.review_comment import ReviewSystem
    from augur.team_audit import record_action

    comment = ReviewSystem.persistent().add_comment(target_type, target_id, author, text)
    record_action("comment_add", {"comment_id": comment.comment_id, "target": f"{target_type}:{target_id}"})
    click.echo(f"Added comment {comment.comment_id} on {target_type} {target_id}")


@comments_cmd.command("list")
@click.option("--target", default="", help="Filter as TYPE:ID, e.g. run:run_AAPL_...")
@click.option("--all", "show_all", is_flag=True, help="Include resolved comments.")
def comments_list_cmd(target, show_all):
    """List comments (unresolved by default)."""
    from augur.review_comment import ReviewSystem

    rs = ReviewSystem.persistent()
    resolved = None if show_all else False
    if target:
        if ":" not in target:
            click.echo("Error: --target must look like TYPE:ID", err=True)
            raise SystemExit(1)
        ttype, tid = target.split(":", 1)
        items = rs.list_by_target(ttype, tid, resolved=resolved)
    else:
        items = rs.list_all(resolved=resolved)
    if not items:
        click.echo("No comments.")
        return
    for c in items:
        state = "resolved" if c.resolved else "open"
        click.echo(f"[{c.comment_id[:8]}] {c.target_type}:{c.target_id} ({state}, {c.author}, {c.created_at[:10]})")
        click.echo(f"    {c.text}")


@comments_cmd.command("resolve")
@click.argument("comment_id")
def comments_resolve_cmd(comment_id):
    """Resolve a comment (full id or unique prefix)."""
    from augur.review_comment import ReviewSystem
    from augur.team_audit import record_action

    rs = ReviewSystem.persistent()
    matches = [c.comment_id for c in rs.list_all() if c.comment_id.startswith(comment_id)]
    if len(matches) != 1:
        click.echo(f"Error: {'no' if not matches else 'ambiguous'} comment id {comment_id}", err=True)
        raise SystemExit(1)
    if not rs.resolve(matches[0]):
        click.echo(f"{matches[0]} is already resolved.")
        return
    record_action("comment_resolve", {"comment_id": matches[0]})
    click.echo(f"Resolved {matches[0]}")


# ---------------------------------------------------------------------------
# augur audit
# ---------------------------------------------------------------------------

@click.command("audit")
@click.option("--limit", default=20, show_default=True)
@click.option("--action", default="", help="Only this action, e.g. decision_record.")
@click.option("--user", default="", help="Only this user.")
def audit_cmd(limit, action, user):
    """Show the audit log of research-record changes."""
    from augur.team_audit import AuditLog

    log = AuditLog()
    if action:
        entries = list(reversed(log.list_by_action(action)))[:limit]
    elif user:
        entries = list(reversed(log.list_by_user(user)))[:limit]
    else:
        entries = log.recent(limit)
    if user and action:
        entries = [e for e in entries if e.user == user]
    if not entries:
        click.echo("Audit log is empty.")
        return
    for e in entries:
        details = ", ".join(f"{k}={v}" for k, v in (e.details or {}).items())
        click.echo(f"{e.timestamp[:19]}  {e.user:<10} {e.action:<18} {details}")


# ---------------------------------------------------------------------------
# augur decisions
# ---------------------------------------------------------------------------

@click.group("decisions")
def decisions_cmd():
    """Record decision outcomes and score decision quality over time."""


@decisions_cmd.command("list")
@click.option("--ticker", default="")
def decisions_list_cmd(ticker):
    """List recorded decisions and their outcomes."""
    from augur.thesis import DecisionLog

    log = DecisionLog()
    items = log.list_by_ticker(ticker) if ticker else log.list_all()
    if not items:
        click.echo("No decisions recorded yet (record them from the Thesis page or the API).")
        return
    _echo_table(
        [(d.decision_id, d.ticker, d.action, d.outcome or "pending",
          "" if d.pnl_pct is None else f"{d.pnl_pct:+.1f}%", d.created_at[:10]) for d in items],
        ["ID", "TICKER", "ACTION", "OUTCOME", "PNL", "CREATED"],
    )


@decisions_cmd.command("resolve")
@click.argument("decision_id")
@click.argument("outcome", type=click.Choice(["correct", "incorrect", "neutral"]))
@click.option("--pnl", "pnl_pct", type=float, default=None, help="Realised return in percent, e.g. 12.5")
def decisions_resolve_cmd(decision_id, outcome, pnl_pct):
    """Record how a decision turned out."""
    from augur.team_audit import record_action
    from augur.thesis import DecisionLog

    decision = DecisionLog().resolve(decision_id, outcome, pnl_pct)
    if decision is None:
        click.echo(f"Error: no decision {decision_id}", err=True)
        raise SystemExit(1)
    record_action("decision_resolve", {"decision_id": decision_id, "outcome": outcome, "pnl_pct": pnl_pct})
    click.echo(f"{decision_id} → {outcome}" + ("" if pnl_pct is None else f" ({pnl_pct:+.1f}%)"))


@decisions_cmd.command("report")
@click.option("--ticker", default="")
def decisions_report_cmd(ticker):
    """Win rate and average return of resolved decisions."""
    from augur.outcome_tracker import DecisionScore, OutcomeTracker
    from augur.thesis import DecisionLog

    log = DecisionLog()
    items = log.list_by_ticker(ticker) if ticker else log.list_all()
    tracker = OutcomeTracker()
    for d in items:
        tracker.record(DecisionScore(
            decision_id=d.decision_id, action=d.action,
            outcome=d.outcome or "pending", pnl_pct=d.pnl_pct or 0.0,
        ))
    report = tracker.report()
    click.echo(f"Decisions: {report.total_decisions}  resolved: {report.resolved}  pending: {report.pending}")
    if report.resolved == 0:
        click.echo("No resolved decisions yet — use `augur decisions resolve ID correct|incorrect|neutral`.")
        return
    click.echo(f"Win rate: {report.win_rate:.0%}   average PnL: {report.avg_pnl_pct:+.2f}%")
    for action, counts in sorted(report.by_action.items()):
        click.echo(f"  {action:<5} correct {counts['correct']}  incorrect {counts['incorrect']}  neutral {counts['neutral']}")
