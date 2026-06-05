# -*- coding: utf-8 -*-
"""Tests for input validation on dashboard routes that previously lacked it.

Covers five endpoints in dashboard/app.py that previously passed path
parameters / query strings straight to handlers without sanitization:
- GET  /api/fetch/{ticker}
- GET  /api/search?q=...
- GET  /api/config/persona/{agent_id}
- DEL  /api/rules/{rule_id}
- GET  /api/history/{history_id}
- DEL  /api/history/{history_id}
"""

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


client = TestClient(app)


class TestFetchTickerValidation:
    """/api/fetch/{ticker} must reject malformed tickers with HTTP 400."""

    def test_fetch_valid_ticker_shape(self):
        # Alphanumeric tickers are accepted at the validation layer.
        # We only assert the *validation* outcome: 200 OR a non-validation error
        # (e.g. 500/501 from yfinance). The point is: NOT 400.
        resp = client.get("/api/fetch/AAPL")
        assert resp.status_code != 400 or resp.status_code == 200

    def test_fetch_invalid_ticker_with_space(self):
        resp = client.get("/api/fetch/AA PL")
        assert resp.status_code == 400
        assert "Invalid ticker" in resp.json()["detail"]

    def test_fetch_invalid_ticker_with_semicolon(self):
        resp = client.get("/api/fetch/AAPL;DROP")
        assert resp.status_code == 400

    def test_fetch_invalid_ticker_too_long(self):
        resp = client.get("/api/fetch/" + "A" * 16)
        assert resp.status_code == 400


class TestSearchQueryValidation:
    """/api/search?q=... must cap length and reject control characters."""

    def test_search_empty_returns_empty(self):
        resp = client.get("/api/search?q=")
        assert resp.status_code == 200
        assert resp.json() == {"results": []}

    def test_search_rejects_huge_query(self):
        resp = client.get("/api/search?q=" + "A" * 200)
        assert resp.status_code == 400
        assert "too long" in resp.json()["detail"]

    def test_search_rejects_control_chars(self):
        # Newline (0x0A) is a control char; should be rejected.
        resp = client.get("/api/search?q=foo%0Abar")
        assert resp.status_code == 400


class TestConfigPersonaAgentIDValidation:
    """/api/config/persona/{agent_id} must reject non-slug agent ids."""

    def test_get_persona_config_valid(self):
        resp = client.get("/api/config/persona/buffett")
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == "buffett"

    def test_get_persona_config_uppercase_rejected(self):
        # agent_id is case-sensitive and must be lowercase to match the
        # canonical registry naming convention.
        resp = client.get("/api/config/persona/BUFFETT")
        assert resp.status_code == 400

    def test_get_persona_config_special_char_rejected(self):
        resp = client.get("/api/config/persona/buffett%3Bdrop")
        assert resp.status_code == 400


class TestRuleIDValidation:
    """DELETE /api/rules/{rule_id} must validate rule_id format."""

    def test_delete_rule_invalid_special_char(self):
        resp = client.delete("/api/rules/rule%3Bdrop")
        assert resp.status_code == 400
        assert "rule_id" in resp.json()["detail"]

    def test_delete_rule_invalid_space(self):
        resp = client.delete("/api/rules/foo bar")
        assert resp.status_code == 400


class TestHistoryIDValidation:
    """GET/DELETE /api/history/{history_id} must validate history_id format."""

    def test_get_history_invalid_special_char(self):
        resp = client.get("/api/history/hist%3Bdrop")
        assert resp.status_code == 400

    def test_get_history_invalid_space(self):
        resp = client.get("/api/history/foo bar")
        assert resp.status_code == 400

    def test_delete_history_invalid_special_char(self):
        resp = client.delete("/api/history/hist%3Bdrop")
        assert resp.status_code == 400

    def test_delete_history_invalid_space(self):
        resp = client.delete("/api/history/foo bar")
        assert resp.status_code == 400
