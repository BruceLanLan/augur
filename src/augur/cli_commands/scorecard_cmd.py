# -*- coding: utf-8 -*-
"""Post-earnings scorecard CLI — score pre-event questions against a post-event run."""
from __future__ import annotations

import click


def _clip(text: str, n: int = 200) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _unavailable(ticker: str, reason: str) -> None:
    click.echo(f"Scorecard {ticker} unavailable: {reason}")


@click.command("scorecard")
@click.argument("ticker")
@click.option("--pre", "pre_id", default=None, help="Pre-event run id or quarter label (default: second-latest run)")
@click.option("--post", "post_id", default=None, help="Post-event run id or quarter label (default: latest run)")
def scorecard_cmd(ticker, pre_id, post_id):
    """Post-earnings scorecard: did the pre-event run answer the research questions right?

    Scores the ticker's research questions (open and answered) by comparing
    what the pre-event run said with what the post-event run says. Offline:
    reads saved runs and the question queue only.

    \b
    Examples:
      augur scorecard AAPL
      augur scorecard AAPL --pre run_AAPL_... --post run_AAPL_...
    """
    from augur.cli_commands.ledger_cmd import _resolve
    from augur.questions import QuestionQueue
    from augur.run_tracker import list_run_ids, load_run_bundle_dict
    from augur.scorecard import ScorecardBuilder

    t = ticker.upper()
    runs = list_run_ids(t)
    pre = _resolve(pre_id, t, runs) if pre_id else (runs[1] if len(runs) > 1 else None)
    post = _resolve(post_id, t, runs) if post_id else (runs[0] if runs else None)
    if pre is None or post is None:
        wanted = ", ".join(r for r in (pre_id, post_id) if r) or "the two latest runs"
        _unavailable(t, f"need a pre-event and a post-event saved run (found {len(runs)} runs; "
                        f"looked for {wanted}) — next step: run `augur workflow {t}` before and after the event")
        return
    if pre == post:
        _unavailable(t, f"pre and post resolve to the same run {pre} — next step: pass two different runs")
        return

    queue = QuestionQueue.persistent()
    questions = [q.question for status in ("open", "answered") for q in queue.list(t, status=status)]
    if not questions:
        _unavailable(t, "no research questions recorded for this ticker, so there is nothing to score "
                        "— next step: add questions (dashboard POST /api/questions/add) before the event")
        return

    try:
        pre_run, post_run = load_run_bundle_dict(pre), load_run_bundle_dict(post)
    except (OSError, ValueError) as exc:
        _unavailable(t, f"saved run unreadable ({exc}) — next step: re-run `augur workflow {t}`")
        return
    pre_run.setdefault("ticker", t)
    card = ScorecardBuilder().build(pre_run, post_run, questions)
    if not any(it.pre_event_answer or it.actual_outcome for it in card.items):
        _unavailable(t, f"neither run {pre} nor {post} carries an answer to any of the "
                        f"{len(questions)} recorded questions — next step: run a skill or workflow that "
                        f"answers them (e.g. `augur skill run earnings-prep {t}`)")
        return

    lines = [f"═══ Post-Earnings Scorecard: {t} ═══", f"  {pre} (pre) → {post} (post)", ""]
    for it in card.items:
        lines.append(f"  [{it.verdict}] {it.question}")
        lines.append(f"      pre: {_clip(it.pre_event_answer) or '—'}")
        lines.append(f"      actual: {_clip(it.actual_outcome) or '—'}")
        if it.evidence_refs:
            lines.append(f"      evidence: {', '.join(it.evidence_refs[:5])}")
    lines += ["", f"Summary: {card.summary}"]
    click.echo("\n".join(lines))
