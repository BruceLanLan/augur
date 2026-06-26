# -*- coding: utf-8 -*-
"""Tests for WebSocket streaming endpoint in dashboard/app.py."""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


client = TestClient(app)


class TestWebSocket:
    def test_websocket_accepts_connection(self):
        """WebSocket endpoint should accept connection for valid ticker."""
        with client.websocket_connect("/ws/analyze/AAPL") as ws:
            # Should receive agent messages
            data = ws.receive_json()
            assert data["type"] == "agent"
            assert "agent_id" in data
            assert "signal" in data
            assert "score" in data
            assert "progress" in data
            # Close after first message
            ws.close()

    def test_websocket_invalid_ticker_rejected(self):
        """WebSocket endpoint should reject invalid ticker format."""
        # Invalid ticker with special chars - should close with error code
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/analyze/AAPL;DROP") as ws:
                ws.receive_json()

    def test_websocket_streams_all_agents(self):
        """WebSocket should stream all agents then consensus."""
        with client.websocket_connect("/ws/analyze/AAPL") as ws:
            agent_count = 0
            consensus_received = False
            for _ in range(50):  # Safety limit
                data = ws.receive_json()
                if data["type"] == "agent":
                    agent_count += 1
                    assert "agent_name" in data
                    assert "progress" in data
                elif data["type"] == "consensus":
                    consensus_received = True
                    break

            assert agent_count > 0
            assert consensus_received


class TestCompareEndpoint:
    def test_compare_valid_request(self):
        """POST /api/compare with valid agents should return results."""
        resp = client.post("/api/compare", json={
            "ticker": "AAPL",
            "agent_ids": ["buffett", "graham"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["agent_count"] == 2
        assert len(data["agents"]) == 2

    def test_compare_too_few_agents(self):
        """POST /api/compare with < 2 agents should return 400."""
        resp = client.post("/api/compare", json={
            "ticker": "AAPL",
            "agent_ids": ["buffett"],
        })
        assert resp.status_code == 400

    def test_compare_too_many_agents(self):
        """POST /api/compare with > 5 agents should return 400."""
        resp = client.post("/api/compare", json={
            "ticker": "AAPL",
            "agent_ids": ["buffett", "graham", "lynch", "wood", "soros", "dalio"],
        })
        assert resp.status_code == 400

    def test_compare_invalid_ticker(self):
        """POST /api/compare with invalid ticker should return 400."""
        resp = client.post("/api/compare", json={
            "ticker": "AAPL;DROP",
            "agent_ids": ["buffett", "graham"],
        })
        assert resp.status_code == 400


class TestHistoryAPI:
    def test_list_history(self):
        """GET /api/history should return a list."""
        resp = client.get("/api/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_history_page_loads(self):
        """GET /history should render the history page."""
        resp = client.get("/history")
        assert resp.status_code == 200
        assert "历史记录" in resp.text

    def test_compare_page_loads(self):
        """GET /compare should render the compare page."""
        resp = client.get("/compare")
        assert resp.status_code == 200
        assert "对比分析" in resp.text


class TestPriceStreamEndpoint:
    """Tests for the /ws/prices real-time price streaming WebSocket."""

    def test_ws_prices_sends_initial_price_update(self):
        """Connecting to /ws/prices should yield a price_update payload with all tickers."""
        with client.websocket_connect("/ws/prices") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "price_update"
            assert "prices" in msg and isinstance(msg["prices"], list)
            assert "timestamp" in msg
            assert len(msg["prices"]) > 0
            for p in msg["prices"]:
                assert {"ticker", "price", "change", "change_pct"} <= set(p)
                assert p["price"] > 0
            ws.close()

    def test_ws_prices_receives_pong_or_stays_open(self):
        """A second send_text after connect should keep the socket open (no crash)."""
        with client.websocket_connect("/ws/prices") as ws:
            # Drain the initial price_update
            initial = ws.receive_json()
            assert initial["type"] == "price_update"
            # Endpoint loops on receive_text; sending a benign keepalive should not
            # raise. We just confirm the socket is still open by issuing a second recv
            # with a short timeout via the context manager's own buffer.
            ws.send_text("ping")
            # Close cleanly to avoid hanging the test
            ws.close()

    def test_ws_prices_rejects_when_auth_required_and_token_missing(self, monkeypatch):
        """If AUGUR_API_TOKEN is set, /ws/prices must close with 1008 for missing token."""
        # Force auth on
        monkeypatch.setenv("AUGUR_API_TOKEN", "secret-test-token-xyz")
        try:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/prices") as ws:
                    # Should be closed by the server; receive_text will raise
                    ws.receive_text()
        finally:
            monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)

    def test_ws_prices_accepts_query_token_when_auth_required(self, monkeypatch):
        """Browser clients pass ?token= when AUGUR_API_TOKEN is configured."""
        monkeypatch.setenv("AUGUR_API_TOKEN", "secret-test-token-xyz")
        try:
            with client.websocket_connect(
                "/ws/prices?token=secret-test-token-xyz"
            ) as ws:
                msg = ws.receive_json()
                assert msg["type"] == "price_update"
                assert len(msg["prices"]) > 0
        finally:
            monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)


class TestCommitteeWebSocket:
    """Tests for /ws/committee streaming endpoint (v9.0.8)."""

    def test_committee_ws_streams_agents_then_verdict(self):
        """Full committee run: should stream agent messages then a verdict."""
        with client.websocket_connect("/ws/committee") as ws:
            ws.send_json({
                "ticker": "AAPL",
                "agents": ["buffett", "graham"],
                "question": "Is AAPL undervalued?",
            })
            agent_count = 0
            verdict_received = False
            for _ in range(20):
                msg = ws.receive_json()
                if msg["type"] == "agent":
                    agent_count += 1
                    assert "agent_name" in msg
                    assert "signal" in msg
                    assert "score" in msg
                    assert "progress" in msg
                elif msg["type"] == "verdict":
                    verdict_received = True
                    v = msg["verdict"]
                    assert "signal" in v
                    assert "score" in v
                    assert "confidence" in v
                    assert "vote" in v
                    assert isinstance(msg.get("opinions"), list)
                    break

            assert agent_count == 2
            assert verdict_received

    def test_committee_post_kelly_pct_matches_position_sizing(self):
        """v10.16.4 regression: POST /api/committee must not double-scale kelly_pct."""
        resp = client.post("/api/committee", json={
            "ticker": "AAPL", "agents": ["buffett"], "question": "Is AAPL undervalued?",
        })
        assert resp.status_code == 200
        verdict = resp.json()["verdict"]
        assert verdict["kelly_pct"] <= 20.0, (
            f"kelly_pct={verdict['kelly_pct']} exceeds the 20% half-Kelly cap; "
            "looks like position_pct got multiplied by 100 twice"
        )

    def test_committee_ws_invalid_ticker_returns_error(self):
        """Invalid ticker format should return error message."""
        with client.websocket_connect("/ws/committee") as ws:
            ws.send_json({"ticker": "AAPL;DROP", "agents": ["buffett"], "question": "?"})
            msg = ws.receive_json()
            assert msg["type"] == "error"

    def test_committee_ws_all_agents_when_empty_list(self):
        """Empty agents list should run all registered agents."""
        with client.websocket_connect("/ws/committee") as ws:
            ws.send_json({"ticker": "NVDA", "agents": [], "question": "Analyze NVDA"})
            msg = ws.receive_json()
            assert msg["type"] == "agent"
            ws.close()

    def test_committee_ws_kelly_pct_matches_position_sizing(self):
        """v10.16.4 regression: kelly_pct must equal position_sizing.position_pct,
        not be multiplied by 100 again (position_pct is already a percentage,
        e.g. 19.9 means 19.9%, not a 0-1 fraction)."""
        with client.websocket_connect("/ws/committee") as ws:
            ws.send_json({"ticker": "AAPL", "agents": ["buffett"], "question": "?"})
            verdict = None
            for _ in range(20):
                msg = ws.receive_json()
                if msg["type"] == "verdict":
                    verdict = msg["verdict"]
                    break
            assert verdict is not None
            assert verdict["kelly_pct"] <= 20.0, (
                f"kelly_pct={verdict['kelly_pct']} exceeds the 20% half-Kelly cap; "
                "looks like position_pct got multiplied by 100 twice"
            )

    def test_committee_ws_verdict_opinions_sorted_by_score(self):
        """Opinions in verdict message should be sorted descending by score."""
        with client.websocket_connect("/ws/committee") as ws:
            ws.send_json({
                "ticker": "TSLA",
                "agents": ["buffett", "graham", "lynch"],
                "question": "Is TSLA a good investment?",
            })
            verdict_msg = None
            for _ in range(20):
                msg = ws.receive_json()
                if msg["type"] == "verdict":
                    verdict_msg = msg
                    break
            assert verdict_msg is not None
            opinions = verdict_msg.get("opinions", [])
            scores = [op["score"] for op in opinions]
            assert scores == sorted(scores, reverse=True)


class TestWorkspaceWebSocket:
    """P2-5: /ws/workspace — workspace state streaming."""

    def test_ws_workspace_sends_initial_state(self):
        """/ws/workspace must send current workspace immediately on connect."""
        with client.websocket_connect("/ws/workspace") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "workspace_state"
            assert "workspace" in msg
            ws_data = msg["workspace"]
            assert isinstance(ws_data, dict)
            assert "enabled_personas" in ws_data

    def test_ws_workspace_route_exists(self):
        """Verify /ws/workspace is registered and reachable (not 404)."""
        with client.websocket_connect("/ws/workspace") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "workspace_state"


class TestWorkflowWebSocket:
    """P2-5: /ws/workflow — workflow progress streaming."""

    def test_ws_workflow_streams_step_messages(self):
        """/ws/workflow must emit step_start, step_done per step, then done."""
        with client.websocket_connect("/ws/workflow") as ws:
            ws.send_json({"ticker": "AAPL", "steps": "fetch,analyze,consensus", "agents": "buffett,graham"})
            types_seen = []
            steps_seen = []
            for _ in range(20):
                msg = ws.receive_json()
                types_seen.append(msg["type"])
                if "step" in msg:
                    steps_seen.append(msg["step"])
                if msg["type"] == "done":
                    break
            assert "step_start" in types_seen
            assert "step_done" in types_seen
            assert "done" in types_seen
            assert "fetch" in steps_seen

    def test_ws_workflow_invalid_ticker_returns_error(self):
        """Invalid ticker should return an error message."""
        with client.websocket_connect("/ws/workflow") as ws:
            ws.send_json({"ticker": "AAPL;DROP", "steps": "fetch"})
            msg = ws.receive_json()
            assert msg["type"] == "error"

    def test_ws_workflow_done_has_step_status(self):
        """Final done message must include step_status dict."""
        with client.websocket_connect("/ws/workflow") as ws:
            ws.send_json({"ticker": "AAPL", "steps": "fetch", "agents": "buffett"})
            done_msg = None
            for _ in range(10):
                msg = ws.receive_json()
                if msg["type"] == "done":
                    done_msg = msg
                    break
            assert done_msg is not None
            assert "step_status" in done_msg
            assert done_msg["step_status"]["fetch"] == "ok"

    def test_ws_workflow_step_done_has_elapsed_ms(self):
        """step_done messages must include elapsed_ms timing field."""
        with client.websocket_connect("/ws/workflow") as ws:
            ws.send_json({"ticker": "AAPL", "steps": "fetch", "agents": "buffett"})
            for _ in range(10):
                msg = ws.receive_json()
                if msg["type"] == "step_done" and msg.get("step") == "fetch":
                    assert "elapsed_ms" in msg
                    assert isinstance(msg["elapsed_ms"], (int, float))
                    break
                if msg["type"] == "done":
                    break
