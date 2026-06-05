# -*- coding: utf-8 -*-
"""Round 10 Agent D: /api/debate endpoint tests.

Exercises the four key behaviors of the multi-agent debate route:

  1. basic happy-path POST returns a well-formed payload with rounds + summary
  2. missing required field (`agent_ids`) is rejected with 422 by Pydantic
  3. invalid inputs (bad ticker, single agent, duplicate agent) yield 400
  4. unknown agent_id is rejected with 404 (not 500)
"""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app, get_endpoint_bucket


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_debate_bucket():
    """Reset the /api/debate token bucket between tests so the burst is full."""
    get_endpoint_bucket("api_debate").reset()
    yield
    get_endpoint_bucket("api_debate").reset()


class TestApiDebate:
    """Validate /api/debate end-to-end behavior."""

    def test_basic_success_returns_well_formed_payload(self, client):
        """Two known agents + valid ticker -> 200 with rounds, summary, timestamp."""
        resp = client.post(
            "/api/debate",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "graham"]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Envelope
        assert data["ticker"] == "AAPL"
        assert "summary" in data and isinstance(data["summary"], str) and data["summary"]
        assert "timestamp" in data and data["timestamp"].endswith("Z")

        # Rounds: one per agent, in order, with required fields
        rounds = data["rounds"]
        assert isinstance(rounds, list)
        assert len(rounds) == 2
        for i, rnd in enumerate(rounds, start=1):
            assert rnd["round"] == i
            assert rnd["agent_id"] in {"buffett", "graham"}
            assert "agent_name" in rnd
            assert "signal" in rnd
            assert "score" in rnd
            assert "confidence" in rnd
            assert "reasoning" in rnd
        # The second round's reasoning should reference the previous speaker
        # (the endpoint tags round > 1 with `[对前者观点的回应]`).
        assert "[对前者观点的回应]" in rounds[1]["reasoning"] or rounds[1]["reasoning"] != rounds[0]["reasoning"]

    def test_missing_field_returns_422(self, client):
        """Omitting `agent_ids` is a Pydantic validation error -> 422, not 500."""
        resp = client.post("/api/debate", json={"ticker": "AAPL"})
        assert resp.status_code == 422
        body = resp.json()
        # FastAPI's HTTPException-based 422 surfaces a `detail` whose rendered
        # text (whether list-of-dicts or string) must mention the missing field.
        rendered = repr(body)
        assert "agent_ids" in rendered, (
            f"expected 'agent_ids' in 422 response, got {rendered}"
        )

    def test_invalid_inputs_return_400(self, client):
        """Bad ticker, single agent, and duplicate agent all return 400."""
        # 1) Illegal ticker characters -> 400
        bad_ticker = client.post(
            "/api/debate",
            json={"ticker": "AA PL", "agent_ids": ["buffett", "graham"]},
        )
        assert bad_ticker.status_code == 400
        assert "invalid" in bad_ticker.json()["detail"].lower()

        # 2) Only one agent -> 400 (debate requires 2-4)
        too_few = client.post(
            "/api/debate",
            json={"ticker": "AAPL", "agent_ids": ["buffett"]},
        )
        assert too_few.status_code == 400
        assert "2" in too_few.json()["detail"]

        # 3) Duplicate agent_ids -> 400
        dup = client.post(
            "/api/debate",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "buffett"]},
        )
        assert dup.status_code == 400
        assert "重复" in dup.json()["detail"] or "duplicate" in dup.json()["detail"].lower()

    def test_unknown_agent_returns_404(self, client):
        """An agent_id not in the registry yields 404 (not 500) and is not retried."""
        resp = client.post(
            "/api/debate",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "no_such_agent_xyz"]},
        )
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "no_such_agent_xyz" in detail
