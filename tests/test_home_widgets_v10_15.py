# -*- coding: utf-8 -*-
"""v10.15: Bloomberg-style customizable home dashboard widgets."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

import dashboard.app as app_mod
from dashboard.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def isolated_home_widgets(tmp_path):
    widgets_path = tmp_path / "home_widgets.yaml"
    with patch.object(app_mod, "_home_widgets_path", return_value=widgets_path):
        app_mod._HOME_WIDGETS_CACHE = None
        yield widgets_path
        app_mod._HOME_WIDGETS_CACHE = None


class TestHomeWidgetsAPI:
    def test_get_returns_defaults(self, client, isolated_home_widgets):
        with patch("augur.cron.load_watchlist", return_value={"watchlist": []}):
            resp = client.get("/api/home/widgets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "widgets" in data
        assert data["pinned_tickers"]
        assert "market-board" in data["valid_panels"]
        assert isinstance(data["quotes"], list)

    def test_put_pinned_and_collapsed_persist(self, client, isolated_home_widgets):
        payload = {
            "pinned_tickers": ["AAPL", "NVDA", "msft"],
            "collapsed_panels": ["crypto", "sector-perf", "invalid-panel"],
        }
        resp = client.put("/api/home/widgets", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["widgets"]["pinned_tickers"] == ["AAPL", "NVDA", "MSFT"]
        assert data["widgets"]["collapsed_panels"] == ["crypto", "sector-perf"]
        assert data["pinned_tickers"] == ["AAPL", "NVDA", "MSFT"]

        resp2 = client.get("/api/home/widgets")
        saved = resp2.json()["widgets"]
        assert saved["pinned_tickers"] == ["AAPL", "NVDA", "MSFT"]
        assert saved["collapsed_panels"] == ["crypto", "sector-perf"]

    def test_pinned_fallback_to_watchlist(self, client, isolated_home_widgets):
        watchlist = {
            "watchlist": [
                {"ticker": "TSLA"},
                {"ticker": "META"},
            ]
        }
        with patch("augur.cron.load_watchlist", return_value=watchlist):
            resp = client.get("/api/home/widgets")
        assert resp.json()["pinned_tickers"] == ["TSLA", "META"]

    def test_save_rejects_invalid_tickers(self, client, isolated_home_widgets):
        resp = client.put(
            "/api/home/widgets",
            json={"pinned_tickers": ["GOOD", "bad ticker!", ""]},
        )
        assert resp.status_code == 200
        assert resp.json()["widgets"]["pinned_tickers"] == ["GOOD"]


class TestHomeWidgetsHelpers:
    def test_get_save_roundtrip(self, isolated_home_widgets):
        saved = app_mod.save_home_widgets({
            "pinned_tickers": ["AAPL"],
            "collapsed_panels": ["market-pulse"],
        })
        assert saved["pinned_tickers"] == ["AAPL"]
        app_mod._HOME_WIDGETS_CACHE = None
        loaded = app_mod.get_home_widgets()
        assert loaded["collapsed_panels"] == ["market-pulse"]


class TestHomeDashboardHTML:
    @pytest.fixture(scope="class")
    def index_soup(self):
        path = Path(__file__).resolve().parents[1] / "dashboard" / "templates" / "index.html"
        return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    @pytest.fixture(scope="class")
    def index_text(self, index_soup):
        return str(index_soup)

    def test_pinned_watchlist_strip_present(self, index_soup):
        assert index_soup.find(id="home-watchlist-strip") is not None
        assert index_soup.find(id="home-watchlist-wrap") is not None

    def test_customize_bar_present(self, index_soup):
        btn = index_soup.find(id="home-customize-btn")
        assert btn is not None
        assert "toggleHomeCustomize" in (btn.get("onclick") or "")

    def test_collapsible_market_panels(self, index_soup):
        panels = index_soup.select(".home-panel[data-panel-id]")
        panel_ids = {p.get("data-panel-id") for p in panels}
        assert "market-board" in panel_ids
        assert "hot-tickers" in panel_ids
        assert "sector-perf" in panel_ids
        assert "fear-macro" in panel_ids

    def test_panel_toggle_hooks(self, index_text):
        assert "toggleHomePanel(" in index_text
        assert "applyHomePanelState" in index_text
        assert "loadHomeWidgets" in index_text

    def test_workspace_default_ticker_applied(self, index_text):
        assert "loadHomeWorkspace" in index_text
        assert "/api/workspace" in index_text
        assert "default_ticker" in index_text
        assert "hero-ticker" in index_text

    def test_home_widgets_api_used(self, index_text):
        assert "/api/home/widgets" in index_text
        assert "saveHomeWidgets" in index_text
        assert "renderPinnedWatchlistStrip" in index_text
