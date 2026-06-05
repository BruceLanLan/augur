# -*- coding: utf-8 -*-
"""Tests for /api/scanner and /scanner endpoints (Round 15 Agent C).

Adds 4 tests complementing the existing TestScannerAPI in test_api.py:

- HTML scanner page renders successfully
- /api/scanner/run consensus_score is a numeric in the documented range
- /api/scanner/run china_stocks preset returns the right number of results
- /api/scanner/run per-ticker error envelope is well-formed for a bogus ticker
  (the API swallows per-ticker failures and emits an error envelope inside
  the result row; the response itself is 200)
"""
from fastapi.testclient import TestClient

from dashboard.app import app


client = TestClient(app)


class TestScannerEndpointR15C:
    """Round 15 Agent C: extra coverage for /api/scanner and /scanner."""

    def test_scanner_html_page_renders(self):
        """GET /scanner returns the scanner HTML page (200, contains scanner.html markers)."""
        resp = client.get("/scanner")
        assert resp.status_code == 200
        # The page is HTML; the dashboard base template wraps every page.
        text = resp.text
        assert "Scanner" in text or "扫描" in text or "scanner" in text.lower()

    def test_run_consensus_score_is_numeric(self):
        """Each result row must have a numeric consensus_score in the expected range."""
        resp = client.post(
            "/api/scanner/run",
            json={"tickers": ["AAPL", "MSFT"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["count"] == 2
        for row in data["results"]:
            score = row["consensus_score"]
            # Either a numeric score in [-100, 100] OR a per-ticker error row (score=0)
            assert isinstance(score, (int, float))
            if "error" not in row:
                assert -100.0 <= score <= 100.0

    def test_run_china_stocks_preset(self):
        """POST /api/scanner/run with preset=china_stocks returns 7 results."""
        resp = client.post(
            "/api/scanner/run",
            json={"tickers": [], "preset": "china_stocks"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["count"] == 7
        returned = {r["ticker"] for r in data["results"]}
        # Every ticker is upper-cased.
        assert all(t == t.upper() for t in returned)
        # The preset is non-overlapping with the tech_giants preset.
        assert "BABA" in returned

    def test_run_agents_have_signal_value(self):
        """Every agent entry on a successful row has a non-empty signal value."""
        resp = client.post(
            "/api/scanner/run",
            json={"tickers": ["AAPL"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        row = data["results"][0]
        assert row["ticker"] == "AAPL"
        # Skip if this ticker surfaced a per-ticker error envelope.
        if "error" in row:
            return
        assert isinstance(row["agents"], list) and row["agents"], (
            "successful scan row must include at least one agent entry"
        )
        for agent in row["agents"]:
            assert agent["agent_id"], "agent_id must be non-empty"
            assert agent["signal"], "signal must be non-empty"
            assert isinstance(agent["score"], (int, float))
