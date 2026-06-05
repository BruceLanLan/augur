# -*- coding: utf-8 -*-
"""Round 9 Agent C: dashboard error-handling hardening tests.

Verifies that routes that previously returned 500 on common errors now
return well-formed 4xx/5xx responses with helpful detail messages,
or degrade gracefully.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ============ api_get_watchlist ============

class TestGetWatchlistErrorHandling:
    """api_get_watchlist must never 500 on missing/corrupt watchlist.yaml."""

    def test_missing_watchlist_returns_empty_not_500(self, client, monkeypatch):
        """FileNotFoundError -> graceful empty list (200)."""
        from augur import cron

        def _raise_fnf():
            raise FileNotFoundError("watchlist.yaml not found")

        monkeypatch.setattr(cron, "load_watchlist", _raise_fnf)
        # The route imports it lazily; patch the symbol on the module too
        with patch("augur.cron.load_watchlist", side_effect=FileNotFoundError("missing")):
            resp = client.get("/api/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert data["watchlist"] == []
        assert data["schedule"] == {}

    def test_corrupt_watchlist_returns_200_with_error_flag(self, client):
        """YAMLError / arbitrary Exception -> 200 with error field, not 500."""
        with patch("augur.cron.load_watchlist", side_effect=Exception("bad yaml")):
            resp = client.get("/api/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert data["watchlist"] == []
        assert data["error"] == "watchlist_unavailable"
        assert "bad yaml" in data["message"]


# ============ api_add_to_watchlist ============

class TestAddWatchlistErrorHandling:
    """api_add_to_watchlist must not 500 on storage failures."""

    def test_permission_error_returns_403(self, client):
        with patch("augur.cron.add_to_watchlist", side_effect=PermissionError("readonly")):
            resp = client.post("/api/watchlist/add", json={"ticker": "AAPL"})
        assert resp.status_code == 403
        assert "无写入权限" in resp.json()["detail"]

    def test_oserror_returns_500_with_detail(self, client):
        with patch("augur.cron.add_to_watchlist", side_effect=OSError("disk full")):
            resp = client.post("/api/watchlist/add", json={"ticker": "AAPL"})
        assert resp.status_code == 500
        assert "disk full" in resp.json()["detail"]

    def test_unexpected_exception_returns_500(self, client):
        with patch("augur.cron.add_to_watchlist", side_effect=RuntimeError("boom")):
            resp = client.post("/api/watchlist/add", json={"ticker": "AAPL"})
        assert resp.status_code == 500
        assert "添加自选股失败" in resp.json()["detail"]


# ============ api_list_history ============

class TestListHistoryErrorHandling:
    """api_list_history must degrade gracefully on storage failures."""

    def test_paginated_history_storage_failure_returns_200_empty(self, client):
        with patch("augur.history.list_history", side_effect=Exception("db locked")):
            resp = client.get("/api/history?page=1&per_page=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["error"] == "history_unavailable"

    def test_simple_history_storage_failure_returns_200_empty(self, client):
        with patch("augur.history.list_history", side_effect=Exception("io error")):
            resp = client.get("/api/history?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["records"] == []
        assert data["count"] == 0
        assert data["error"] == "history_unavailable"


# ============ api_clear_history ============

class TestClearHistoryErrorHandling:
    """api_clear_history must return 500 (not unhandled exception) on storage failure."""

    def test_storage_failure_returns_500_with_detail(self, client):
        with patch("augur.history.clear_history", side_effect=Exception("db corrupted")):
            resp = client.delete("/api/history")
        assert resp.status_code == 500
        assert "db corrupted" in resp.json()["detail"]


# ============ api_chat ============

class TestChatErrorHandling:
    """api_chat must return 4xx/5xx (not crash) on engine failures."""

    def test_empty_message_returns_400(self, client):
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 400
        assert "不能为空" in resp.json()["detail"]

    def test_whitespace_message_returns_400(self, client):
        resp = client.post("/api/chat", json={"message": "   "})
        assert resp.status_code == 400

    def test_engine_valueerror_returns_400(self, client):
        with patch("dashboard.app._get_chat_engine") as mock_engine:
            mock_engine.return_value.get_response.side_effect = ValueError("bad input")
            resp = client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 400
        assert "Invalid chat request" in resp.json()["detail"]

    def test_engine_runtime_returns_500(self, client):
        with patch("dashboard.app._get_chat_engine") as mock_engine:
            mock_engine.return_value.get_response.side_effect = RuntimeError("upstream down")
            resp = client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 500
        assert "聊天服务暂时不可用" in resp.json()["detail"]

    def test_engine_keyerror_returns_404(self, client):
        with patch("dashboard.app._get_chat_engine") as mock_engine:
            mock_engine.return_value.get_response.side_effect = KeyError("ghost_agent")
            resp = client.post("/api/chat", json={"message": "hi", "agent_id": "ghost"})
        assert resp.status_code == 404
        assert "ghost" in resp.json()["detail"]


# ============ api_i18n ============

class TestI18nErrorHandling:
    """api_i18n must return 500 with helpful detail on corrupt/unreadable files."""

    def test_corrupt_json_returns_500_with_detail(self, client, tmp_path, monkeypatch):
        # Create a corrupt en.json in a temp i18n dir and patch Path parent resolution
        bad_file = tmp_path / "en.json"
        bad_file.write_text("{ this is not json", encoding="utf-8")
        # The route uses Path(__file__).parent / "i18n" so we patch the read_text call
        from pathlib import Path as P

        original_read = P.read_text

        def fake_read(self, *args, **kwargs):
            if str(self).endswith("en.json") and tmp_path.name not in str(self):
                return "{ this is not json"
            return original_read(self, *args, **kwargs)

        # Simpler: patch json.loads to raise for the i18n route
        with patch("dashboard.app.json.loads", side_effect=json.JSONDecodeError("bad", "x", 0)):
            resp = client.get("/api/i18n/en")
        assert resp.status_code == 500
        assert "翻译文件格式错误" in resp.json()["detail"]

    def test_valid_i18n_still_works(self, client):
        """Regression: the happy path must still return 200 with valid JSON."""
        resp = client.get("/api/i18n/zh")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert len(data) > 0
