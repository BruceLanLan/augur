# -*- coding: utf-8 -*-
"""CLI entry points for citation corrections, review comments, audit log and decision outcomes.

These modules (citation_queue, review_comment, team_audit, outcome_tracker)
had tests but no user entry point before 2026-09-17.
"""
from click.testing import CliRunner


def _run(*args):
    from augur.cli import main

    return CliRunner().invoke(main, list(args))


def test_citation_report_list_accept_roundtrip():
    r = _run("citations", "report", "AAPL", "--claim-id", "claim_rec_cli_1",
             "--issue", "wrong_source", "--wrong", "ev_bad", "--correct", "ev_good")
    assert r.exit_code == 0, r.output
    cid = r.output.split()[1]
    assert cid.startswith("cc_")
    assert cid in _run("citations", "list").output
    assert _run("citations", "accept", cid).exit_code == 0
    assert cid in _run("citations", "list", "--status", "accepted").output
    assert _run("citations", "accept", "cc_missing").exit_code == 1


def test_comments_persist_across_processes_and_resolve():
    r = _run("comments", "add", "run", "run_REC_1", "check the FCF source", "--author", "reviewer")
    assert r.exit_code == 0, r.output
    comment_id = r.output.split()[2]

    # A fresh ReviewSystem (new process equivalent) must still see it.
    listed = _run("comments", "list", "--target", "run:run_REC_1")
    assert "check the FCF source" in listed.output

    assert _run("comments", "resolve", comment_id[:10]).exit_code == 0
    assert "check the FCF source" not in _run("comments", "list", "--target", "run:run_REC_1").output
    assert "resolved" in _run("comments", "list", "--target", "run:run_REC_1", "--all").output


def test_audit_log_records_cli_actions():
    _run("comments", "add", "thesis", "th_REC_AUDIT", "audited comment")
    out = _run("audit", "--action", "comment_add").output
    assert "comment_add" in out and "thesis:th_REC_AUDIT" in out


def test_decisions_resolve_and_report():
    from augur.thesis import Decision, DecisionLog

    log = DecisionLog()
    win = log.record(Decision(decision_id="", ticker="RECQ", action="buy", reasoning="r",
                              evidence_run_ids=[], thesis_ids=[], created_at=""))
    loss = log.record(Decision(decision_id="", ticker="RECQ", action="sell", reasoning="r",
                               evidence_run_ids=[], thesis_ids=[], created_at=""))
    assert win and loss and win != loss, "blank ids must be generated, not collide"

    assert _run("decisions", "resolve", win, "correct", "--pnl", "12.5").exit_code == 0
    assert _run("decisions", "resolve", loss, "incorrect", "--pnl", "-4").exit_code == 0

    report = _run("decisions", "report", "--ticker", "RECQ")
    assert report.exit_code == 0, report.output
    assert "Win rate: 50%" in report.output
    assert "+4.25%" in report.output
    assert "RECQ" in _run("decisions", "list", "--ticker", "RECQ").output


def test_dashboard_decision_api_no_longer_overwrites_previous_decision():
    from fastapi.testclient import TestClient

    from dashboard.app import app

    client = TestClient(app)
    ids = {
        client.post("/api/decisions/record", json={"ticker": "RECAPI", "action": a, "reasoning": "x"}).json()["decision_id"]
        for a in ("buy", "hold")
    }
    assert "" not in ids and len(ids) == 2
