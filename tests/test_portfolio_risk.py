# -*- coding: utf-8 -*-
"""Tests for Feature D: Portfolio Risk Decomposition (POST /api/portfolio/risk)."""

import pytest
from unittest.mock import patch


class TestPortfolioRiskValidation:
    """Input validation edge cases."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        return TestClient(app)

    def test_empty_holdings_rejected(self, client):
        resp = client.post("/api/portfolio/risk", json={"holdings": []})
        assert resp.status_code == 400

    def test_too_many_holdings_rejected(self, client):
        holdings = [{"ticker": f"T{i}", "qty": 1, "current_price": 10.0} for i in range(21)]
        resp = client.post("/api/portfolio/risk", json={"holdings": holdings})
        assert resp.status_code == 400

    def test_invalid_ticker_rejected(self, client):
        resp = client.post("/api/portfolio/risk", json={
            "holdings": [{"ticker": "bad;ticker", "qty": 1, "current_price": 10.0}]
        })
        assert resp.status_code == 400

    def test_zero_qty_rejected(self, client):
        resp = client.post("/api/portfolio/risk", json={
            "holdings": [{"ticker": "AAPL", "qty": 0, "current_price": 10.0}]
        })
        assert resp.status_code == 400

    def test_zero_total_value_rejected(self, client):
        """All holdings have current_price=0 (no market value) -> 400."""
        resp = client.post("/api/portfolio/risk", json={
            "holdings": [{"ticker": "AAPL", "qty": 10, "current_price": 0}]
        })
        assert resp.status_code == 400

    def test_negative_qty_rejected(self, client):
        """Negative qty is rejected the same way as zero (not just <=0 vs ==0)."""
        resp = client.post("/api/portfolio/risk", json={
            "holdings": [{"ticker": "AAPL", "qty": -5, "current_price": 10.0}]
        })
        assert resp.status_code == 400

    def test_negative_current_price_rejected(self, client):
        """A negative current_price is financially nonsensical and must be rejected
        (previously unvalidated — could flip total_value negative and produce
        garbage weights instead of a clean 400)."""
        resp = client.post("/api/portfolio/risk", json={
            "holdings": [{"ticker": "AAPL", "qty": 10, "current_price": -50.0}]
        })
        assert resp.status_code == 400

    def test_exactly_20_holdings_accepted(self, client):
        """20 holdings is the boundary — must be accepted (only 21+ is rejected)."""
        holdings = [{"ticker": f"T{i}", "qty": 1, "current_price": 10.0} for i in range(20)]
        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", side_effect=Exception("no network")):
            resp = client.post("/api/portfolio/risk", json={"holdings": holdings})
        assert resp.status_code == 200
        assert len(resp.json()["holdings"]) == 20


class TestPortfolioRiskComputation:
    """Structural correctness of the risk decomposition math."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        return TestClient(app)

    def _mock_ctx(self, ticker, beta=1.0, sector="Technology"):
        from augur.personas.base import MarketContext
        return MarketContext(ticker=ticker, price=100.0, beta_1y=beta, sector=sector)

    def test_single_holding_full_weight_and_risk(self, client):
        """One holding: weight=100%, risk_contribution=100%, effective_n=1."""
        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", return_value=self._mock_ctx("AAPL", beta=1.3)):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [{"ticker": "AAPL", "qty": 10, "current_price": 150.0}]
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value"] == pytest.approx(1500.0)
        assert len(data["holdings"]) == 1
        h = data["holdings"][0]
        assert h["weight_pct"] == pytest.approx(100.0)
        assert h["risk_contribution_pct"] == pytest.approx(100.0)
        assert h["beta"] == pytest.approx(1.3, abs=0.01)
        assert data["portfolio"]["beta"] == pytest.approx(1.3, abs=0.01)
        assert data["portfolio"]["diversification"]["effective_n_weight"] == pytest.approx(1.0)
        assert data["portfolio"]["diversification"]["effective_n_risk"] == pytest.approx(1.0)

    def test_risk_contributions_sum_to_100(self, client):
        """Multi-holding: risk_contribution_pct across all holdings sums to ~100%."""
        contexts = {
            "AAPL": self._mock_ctx("AAPL", beta=1.2, sector="Technology"),
            "KO": self._mock_ctx("KO", beta=0.6, sector="Consumer Defensive"),
            "JPM": self._mock_ctx("JPM", beta=1.1, sector="Financial Services"),
        }

        def fake_ctx(ticker, **kw):
            return contexts[ticker]

        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", side_effect=fake_ctx):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [
                    {"ticker": "AAPL", "qty": 10, "current_price": 150.0},
                    {"ticker": "KO", "qty": 20, "current_price": 60.0},
                    {"ticker": "JPM", "qty": 5, "current_price": 200.0},
                ]
            })

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["holdings"]) == 3

        total_risk_contrib = sum(h["risk_contribution_pct"] for h in data["holdings"])
        assert total_risk_contrib == pytest.approx(100.0, abs=0.5)

        total_weight = sum(h["weight_pct"] for h in data["holdings"])
        assert total_weight == pytest.approx(100.0, abs=0.5)

        # Weighted-average beta bounds check
        assert 0.5 <= data["portfolio"]["beta"] <= 1.3

        # effective_n must be between 1 and n=3
        div = data["portfolio"]["diversification"]
        assert 1.0 <= div["effective_n_weight"] <= 3.0
        assert 1.0 <= div["effective_n_risk"] <= 3.0

        assert data["portfolio"]["volatility_annual_pct"] >= 0

    def test_duplicate_ticker_lots_aggregated(self, client):
        """Two lots of the same ticker are merged into one position."""
        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", return_value=self._mock_ctx("AAPL")):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [
                    {"ticker": "AAPL", "qty": 5, "current_price": 150.0},
                    {"ticker": "aapl", "qty": 5, "current_price": 150.0},  # lowercase, same ticker
                ]
            })

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["holdings"]) == 1
        assert data["holdings"][0]["ticker"] == "AAPL"
        assert data["total_value"] == pytest.approx(1500.0)  # 10 shares * 150

    def test_sector_concentration_groups_same_sector(self, client):
        """Two tech holdings should combine into one 'Technology' sector bucket."""
        contexts = {
            "AAPL": self._mock_ctx("AAPL", sector="Technology"),
            "MSFT": self._mock_ctx("MSFT", sector="Technology"),
        }

        def fake_ctx(ticker, **kw):
            return contexts[ticker]

        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", side_effect=fake_ctx):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [
                    {"ticker": "AAPL", "qty": 10, "current_price": 100.0},
                    {"ticker": "MSFT", "qty": 10, "current_price": 100.0},
                ]
            })

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sector_concentration"]) == 1
        assert data["sector_concentration"][0]["sector"] == "Technology"
        assert data["sector_concentration"][0]["weight_pct"] == pytest.approx(100.0, abs=0.1)

    def test_market_context_failure_falls_back_gracefully(self, client):
        """If fetch_market_context raises, beta defaults to 1.0 and sector to 'Unknown'."""
        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", side_effect=RuntimeError("no data")):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [{"ticker": "AAPL", "qty": 10, "current_price": 150.0}]
            })

        assert resp.status_code == 200
        data = resp.json()
        h = data["holdings"][0]
        assert h["beta"] == pytest.approx(1.0)
        assert h["sector"] == "Unknown"

    def test_data_source_mock_when_history_unavailable(self, client):
        """When fetch_history fails, data_source falls back to 'mock' but response is still valid."""
        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", return_value=self._mock_ctx("AAPL")):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [{"ticker": "AAPL", "qty": 10, "current_price": 150.0}]
            })

        assert resp.status_code == 200
        assert resp.json()["data_source"] == "mock"

    def test_live_data_source_when_history_available(self, client):
        """When fetch_history returns real-looking data for all tickers, data_source='live'."""
        fake_hist = [{"close": 100.0 + i * 0.5} for i in range(30)]

        with patch("augur.data.fetch_history", return_value=fake_hist), \
             patch("augur.data.fetch_market_context", return_value=self._mock_ctx("AAPL")):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [{"ticker": "AAPL", "qty": 10, "current_price": 150.0}]
            })

        assert resp.status_code == 200
        assert resp.json()["data_source"] == "live"

    def test_second_lot_zero_price_does_not_overwrite_first(self, client):
        """Aggregation keeps the last *non-zero* price seen — a later lot with
        current_price=0 (e.g. client didn't have a fresh quote for that entry)
        must not blank out an already-known price."""
        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", return_value=self._mock_ctx("AAPL")):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [
                    {"ticker": "AAPL", "qty": 5, "current_price": 150.0},
                    {"ticker": "AAPL", "qty": 5, "current_price": 0},
                ]
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value"] == pytest.approx(1500.0)  # 10 shares * 150, not 750

    def test_both_lots_zero_price_gives_zero_value_error(self, client):
        """If every lot of a ticker has current_price=0, aggregated value is 0
        -> overall zero-total-value rejection still fires (no silent 0-value ticker)."""
        resp = client.post("/api/portfolio/risk", json={
            "holdings": [
                {"ticker": "AAPL", "qty": 5, "current_price": 0},
                {"ticker": "AAPL", "qty": 5, "current_price": 0},
            ]
        })
        assert resp.status_code == 400

    def test_holdings_sorted_by_weight_descending(self, client):
        """Response holdings are sorted largest-weight-first, not insertion order."""
        contexts = {
            "SMALL": self._mock_ctx("SMALL", sector="Technology"),
            "BIG": self._mock_ctx("BIG", sector="Technology"),
        }

        def fake_ctx(ticker, **kw):
            return contexts[ticker]

        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", side_effect=fake_ctx):
            resp = client.post("/api/portfolio/risk", json={
                # SMALL submitted first but is the smaller position
                "holdings": [
                    {"ticker": "SMALL", "qty": 1, "current_price": 10.0},
                    {"ticker": "BIG", "qty": 100, "current_price": 100.0},
                ]
            })

        assert resp.status_code == 200
        tickers_in_order = [h["ticker"] for h in resp.json()["holdings"]]
        assert tickers_in_order == ["BIG", "SMALL"]

    def test_sector_concentration_sorted_by_weight_descending(self, client):
        """sector_concentration list is sorted largest-sector-first."""
        contexts = {
            "SMALLCAP": self._mock_ctx("SMALLCAP", sector="Energy"),
            "BIGCAP": self._mock_ctx("BIGCAP", sector="Technology"),
        }

        def fake_ctx(ticker, **kw):
            return contexts[ticker]

        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", side_effect=fake_ctx):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [
                    {"ticker": "SMALLCAP", "qty": 1, "current_price": 10.0},
                    {"ticker": "BIGCAP", "qty": 100, "current_price": 100.0},
                ]
            })

        assert resp.status_code == 200
        sectors_in_order = [s["sector"] for s in resp.json()["sector_concentration"]]
        assert sectors_in_order == ["Technology", "Energy"]

    def test_zero_beta_falls_back_to_one(self, client):
        """A MarketContext.beta_1y of exactly 0.0 is treated as 'no data' and
        substituted with the neutral default 1.0 (falsy-0 fallback in the
        route) — locking down current behavior since a real zero-beta asset
        would be silently overwritten the same way."""
        with patch("augur.data.fetch_history", side_effect=Exception("no network")), \
             patch("augur.data.fetch_market_context", return_value=self._mock_ctx("AAPL", beta=0.0)):
            resp = client.post("/api/portfolio/risk", json={
                "holdings": [{"ticker": "AAPL", "qty": 10, "current_price": 150.0}]
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["holdings"][0]["beta"] == pytest.approx(1.0)
        assert data["portfolio"]["beta"] == pytest.approx(1.0)
