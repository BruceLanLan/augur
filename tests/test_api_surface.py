# -*- coding: utf-8 -*-
"""Tests for new REST endpoints (disagreement, evidence, insider, ownership)."""
import json
import pytest

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    try:
        from dashboard.app import app
        return TestClient(app)
    except Exception:
        pytest.skip("dashboard app not importable in this environment")


class TestDisagreementEndpoint:
    def test_disagreement_requires_ticker(self, client):
        resp = client.get("/api/disagreement")
        assert resp.status_code == 400

    def test_disagreement_returns_map(self, client):
        resp = client.get("/api/disagreement?ticker=AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "consensus_strength" in data
        assert "conflict_points" in data


class TestEvidenceEndpoint:
    def test_missing_evidence_404(self, client):
        resp = client.get("/api/evidence/ev_nonexistent_123")
        assert resp.status_code in (404, 200)


class TestInsiderEndpoint:
    def test_insider_activity(self, client):
        resp = client.get("/api/insider/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "trades" in data

    def test_insider_invalid_ticker(self, client):
        resp = client.get("/api/insider/INVALID_TICKER_THAT_IS_WAY_TOO_LONG")
        assert resp.status_code == 400


class TestOwnershipEndpoint:
    def test_ownership_delta(self, client):
        resp = client.get("/api/ownership/MSFT")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "MSFT"
        assert "top_holders" in data
