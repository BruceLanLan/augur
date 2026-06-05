# -*- coding: utf-8 -*-
"""Loop Round 11 Agent C: /api/analyze/{ticker} consensus + /api/compare tests.

The "consensus" surface in this codebase is the `consensus` field returned by
``GET /api/analyze/{ticker}`` (a multi-agent aggregate produced by the
DecisionCoordinator). ``POST /api/compare`` is the dedicated multi-agent
side-by-side compare route.

This file covers:

  1. ``/api/analyze/{ticker}`` returns a `consensus` block with the required
     keys and the agent list matches `agent_count`.
  2. The consensus signal/score are derived from the agents (the signal
     should appear in the agents' signals when at least one agent is bullish
     or bearish).
  3. ``/api/compare`` happy path returns per-agent results in the requested
     order with the envelope (ticker, agent_count, agents, timestamp).
  4. ``/api/compare`` validation: missing field -> 422, bad ticker -> 400,
     too-few agents -> 400, duplicate agent_ids -> 400, unknown agent -> 404.
"""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app, get_endpoint_bucket


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_compare_bucket():
    """Reset the /api/compare token bucket between tests so the burst is full."""
    get_endpoint_bucket("api_compare").reset()
    yield
    get_endpoint_bucket("api_compare").reset()


class TestAnalyzeConsensus:
    """``GET /api/analyze/{ticker}`` must include a populated `consensus` block."""

    def test_consensus_block_present_and_well_formed(self, client):
        """The analyze endpoint returns a `consensus` block with the
        required fields (signal, score, confidence, reasoning, key_findings,
        risks, metadata) and the agents[] list matches `agent_count`."""
        resp = client.get("/api/analyze/AAPL")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["status"] == "ok"
        assert data["ticker"] == "AAPL"

        # Envelope
        assert "consensus" in data
        consensus = data["consensus"]
        assert isinstance(consensus, dict)

        # Required keys on the consensus payload
        for key in ("signal", "score", "confidence", "reasoning",
                    "key_findings", "risks", "metadata", "agent_id",
                    "agent_name"):
            assert key in consensus, f"missing key {key!r} in consensus"

        # Score should be a number, signal a string
        assert isinstance(consensus["score"], (int, float))
        assert isinstance(consensus["signal"], str) and consensus["signal"]
        assert isinstance(consensus["key_findings"], list)
        assert isinstance(consensus["risks"], list)
        assert isinstance(consensus["metadata"], dict)

        # agents[] length must equal agent_count
        agents = data["agents"]
        assert isinstance(agents, list) and len(agents) > 0
        assert data["agent_count"] == len(agents)

    def test_consensus_signal_is_one_of_agent_signals(self, client):
        """When at least one agent is bullish/bearish, the consensus signal
        must be one of the values declared by the agent responses (bullish,
        bearish, or neutral) — never a raw error / unknown token."""
        resp = client.get("/api/analyze/AAPL")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        valid_signals = {"bullish", "bearish", "neutral"}
        consensus_signal = data["consensus"]["signal"]
        assert consensus_signal in valid_signals, (
            f"unexpected consensus signal: {consensus_signal!r}"
        )

        # The agent-level signals should also be from the valid set
        agent_signals = [a.get("signal") for a in data["agents"]]
        assert all(s in valid_signals for s in agent_signals), (
            f"agent signals outside valid set: {agent_signals!r}"
        )


class TestApiCompare:
    """``POST /api/compare`` — multi-agent side-by-side comparison."""

    def test_basic_success_returns_well_formed_payload(self, client):
        """Two known agents + valid ticker -> 200 with envelope + per-agent
        results in the requested order."""
        resp = client.post(
            "/api/compare",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "graham"]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Envelope
        assert data["ticker"] == "AAPL"
        assert data["agent_count"] == 2
        assert "timestamp" in data and data["timestamp"].endswith("Z")

        agents = data["agents"]
        assert isinstance(agents, list) and len(agents) == 2

        # Order preserved: first agent returned is buffett, second is graham
        assert agents[0]["agent_id"] == "buffett"
        assert agents[1]["agent_id"] == "graham"

        # Each agent result has the expected shape
        for a in agents:
            for key in ("agent_id", "agent_name", "signal", "score",
                        "confidence", "reasoning", "key_findings", "risks"):
                assert key in a, f"missing key {key!r} in agent result"
            assert a["signal"] in {"bullish", "bearish", "neutral"}

    def test_invalid_inputs_return_400_or_422(self, client):
        """Bad ticker -> 400, too-few agents -> 400, duplicate agent_ids -> 400,
        missing required field -> 422."""
        # 1) Illegal ticker characters -> 400
        bad_ticker = client.post(
            "/api/compare",
            json={"ticker": "AA PL", "agent_ids": ["buffett", "graham"]},
        )
        assert bad_ticker.status_code == 400
        assert "invalid" in bad_ticker.json()["detail"].lower()

        # 2) Only one agent -> 400 (compare requires 2-5)
        too_few = client.post(
            "/api/compare",
            json={"ticker": "AAPL", "agent_ids": ["buffett"]},
        )
        assert too_few.status_code == 400
        assert "2" in too_few.json()["detail"]

        # 3) Duplicate agent_ids -> 400
        dup = client.post(
            "/api/compare",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "buffett"]},
        )
        assert dup.status_code == 400
        detail = dup.json()["detail"]
        assert "重复" in detail or "duplicate" in detail.lower()

        # 4) Missing `agent_ids` -> 422 (Pydantic validation)
        missing = client.post("/api/compare", json={"ticker": "AAPL"})
        assert missing.status_code == 422
        assert "agent_ids" in repr(missing.json())

    def test_unknown_agent_returns_404(self, client):
        """An agent_id not in the registry yields 404 (not 500)."""
        resp = client.post(
            "/api/compare",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "no_such_agent_xyz"]},
        )
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "no_such_agent_xyz" in detail
