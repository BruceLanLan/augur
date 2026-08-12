# -*- coding: utf-8 -*-
"""Tests for augur:// MCP resource helpers (no `mcp` package required).

Covers the testable module-level helper behind the ``augur://decisions/{id}``
resource so the read path is verified without importing FastMCP.
"""

import json

from augur.thesis import Decision, DecisionLog


def _record_decision(decision_id="dec_AAPL_buy_20240101"):
    """Persist a Decision through the canonical DecisionLog store."""
    DecisionLog().record(Decision(
        decision_id=decision_id,
        ticker="AAPL",
        action="buy",
        reasoning="Strong moat at a fair price.",
        evidence_run_ids=["run_AAPL_20240101_00000000_abcd1234"],
        thesis_ids=["th_AAPL_abcd1234"],
        created_at="2024-01-01T00:00:00Z",
    ))
    return decision_id


class TestDecisionResource:
    def test_returns_decision_json(self):
        from augur.mcp_server import _run_decision_resource

        did = _record_decision()
        data = json.loads(_run_decision_resource(did))

        assert data["decision_id"] == did
        assert data["ticker"] == "AAPL"
        assert data["action"] == "buy"
        assert data["reasoning"] == "Strong moat at a fair price."

    def test_not_found_returns_error_envelope(self):
        from augur.mcp_server import _run_decision_resource

        data = json.loads(_run_decision_resource("dec_NOPE_hold_20240101"))

        assert data["error"] == "decision not found"
        assert data["decision_id"] == "dec_NOPE_hold_20240101"
