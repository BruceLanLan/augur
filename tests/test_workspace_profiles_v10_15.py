# -*- coding: utf-8 -*-
"""Tests for v10.15: multi-profile workspace, landing redirect, export/import."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def isolated_workspace(tmp_path):
    """Use a temp workspace.yaml and reset module cache."""
    import augur.workspace as ws_mod

    path = tmp_path / "workspace.yaml"
    with patch.object(ws_mod, "_workspace_path", return_value=path):
        ws_mod.reset_workspace_cache()
        yield ws_mod
        ws_mod.reset_workspace_cache()


class TestWorkspaceProfiles:
    def test_default_profile_on_fresh_install(self, isolated_workspace):
        ws_mod = isolated_workspace
        state = ws_mod.get_workspace_state()
        assert state["active_profile"] == "default"
        assert "default" in state["profiles"]
        assert ws_mod.get_workspace()["layout_preset"] == "analyst"

    def test_create_and_list_profiles(self, isolated_workspace):
        ws_mod = isolated_workspace
        ws_mod.create_profile("day-trading", copy_from="default")
        ws_mod.create_profile("research")

        profiles = ws_mod.list_profiles()
        names = {p["name"] for p in profiles}
        assert names == {"day-trading", "default", "research"}
        assert sum(1 for p in profiles if p["active"]) == 1

    def test_switch_active_profile(self, isolated_workspace):
        ws_mod = isolated_workspace
        ws_mod.save_workspace({"layout_preset": "trader", "default_page": "/stocks"})
        ws_mod.create_profile("day-trading")
        ws_mod.set_active_profile("day-trading")

        assert ws_mod.get_workspace_state()["active_profile"] == "day-trading"
        active_ws = ws_mod.get_workspace()
        assert active_ws["layout_preset"] == "analyst"

        ws_mod.set_active_profile("default")
        assert ws_mod.get_workspace()["layout_preset"] == "trader"

    def test_delete_profile(self, isolated_workspace):
        ws_mod = isolated_workspace
        ws_mod.create_profile("research")
        ws_mod.set_active_profile("default")
        ws_mod.delete_profile("research")

        names = {p["name"] for p in ws_mod.list_profiles()}
        assert names == {"default"}

    def test_cannot_delete_active_or_last_profile(self, isolated_workspace):
        ws_mod = isolated_workspace
        with pytest.raises(ValueError, match="last profile"):
            ws_mod.delete_profile("default")

        ws_mod.create_profile("research")
        with pytest.raises(ValueError, match="active profile"):
            ws_mod.delete_profile("default")

    def test_migrate_legacy_flat_format(self, isolated_workspace, tmp_path):
        ws_mod = isolated_workspace
        path = tmp_path / "workspace.yaml"
        path.write_text(
            "layout_preset: minimal\ndefault_page: /stocks\ndefault_ticker: AAPL\n",
            encoding="utf-8",
        )
        ws_mod.reset_workspace_cache()
        loaded = ws_mod.get_workspace()
        assert loaded["layout_preset"] == "minimal"
        assert loaded["default_ticker"] == "AAPL"
        state = ws_mod.get_workspace_state()
        assert "default" in state["profiles"]


class TestLandingRedirect:
    def test_default_ticker_takes_priority(self, isolated_workspace):
        from augur.workspace import resolve_landing_url

        url = resolve_landing_url({
            "default_ticker": "aapl",
            "default_page": "/committee",
        })
        assert url == "/stocks?ticker=AAPL"

    def test_default_page_when_no_ticker(self, isolated_workspace):
        from augur.workspace import resolve_landing_url

        url = resolve_landing_url({"default_page": "/stocks", "default_ticker": ""})
        assert url == "/stocks"

    def test_no_redirect_when_dashboard(self, isolated_workspace):
        from augur.workspace import resolve_landing_url

        assert resolve_landing_url({"default_page": "/", "default_ticker": ""}) is None
        assert resolve_landing_url({"default_page": "/"}, path="/stocks") is None


class TestIndexLandingRedirect:
    def test_index_redirects_for_trader_profile(self, isolated_workspace, tmp_path):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        import augur.workspace as ws_mod

        path = tmp_path / "landing-workspace.yaml"
        with patch.object(ws_mod, "_workspace_path", return_value=path):
            ws_mod.reset_workspace_cache()
            ws_mod.save_workspace({"default_page": "/stocks", "default_ticker": ""})
            client = TestClient(app)
            resp = client.get("/", follow_redirects=False)
            assert resp.status_code == 302
            assert resp.headers["location"] == "/stocks"

    def test_index_renders_when_default_dashboard(self, isolated_workspace, tmp_path):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        import augur.workspace as ws_mod

        path = tmp_path / "landing-workspace2.yaml"
        with patch.object(ws_mod, "_workspace_path", return_value=path):
            ws_mod.reset_workspace_cache()
            client = TestClient(app)
            resp = client.get("/", follow_redirects=False)
            assert resp.status_code == 200


class TestWorkspaceExportImport:
    def test_export_import_roundtrip(self, isolated_workspace):
        ws_mod = isolated_workspace
        ws_mod.save_workspace({
            "layout_preset": "trader",
            "default_page": "/stocks",
            "default_ticker": "SPY",
        })
        ws_mod.create_profile("research")
        ws_mod.save_profile("research", {
            "layout_preset": "analyst",
            "default_page": "/",
            "default_ticker": "",
        })

        bundle = ws_mod.export_workspace_bundle()
        assert bundle["active_profile"] == "default"
        assert "research" in bundle["profiles"]
        assert bundle["profiles"]["default"]["default_ticker"] == "SPY"

        ws_mod.reset_workspace_cache()
        ws_mod.import_workspace_bundle(bundle, merge=False)
        reloaded = ws_mod.export_workspace_bundle()
        assert reloaded["profiles"]["default"]["default_ticker"] == "SPY"
        assert "research" in reloaded["profiles"]

    def test_config_export_merge_pattern(self, isolated_workspace):
        """Simulate /api/config/export embedding workspace bundle."""
        ws_mod = isolated_workspace
        ws_mod.create_profile("day-trading")
        ws_mod.set_active_profile("day-trading")
        ws_mod.save_workspace({"layout_preset": "trader", "default_ticker": "QQQ"})

        config_export = {
            "defaults": {"model": "gpt-4"},
            ws_mod.WORKSPACE_EXPORT_KEY: ws_mod.export_workspace_bundle(),
        }
        assert ws_mod.WORKSPACE_EXPORT_KEY in config_export

        ws_mod.reset_workspace_cache()
        ws_mod.import_workspace_bundle(config_export[ws_mod.WORKSPACE_EXPORT_KEY], merge=False)
        assert ws_mod.get_workspace_state()["active_profile"] == "day-trading"
        assert ws_mod.get_workspace()["default_ticker"] == "QQQ"


class TestWorkspaceProfilesAPI:
    def test_profile_endpoints(self, isolated_workspace, tmp_path):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        import augur.workspace as ws_mod

        path = tmp_path / "api-workspace.yaml"
        with patch.object(ws_mod, "_workspace_path", return_value=path):
            ws_mod.reset_workspace_cache()
            client = TestClient(app)

            r = client.get("/api/workspace")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "ok"
            assert "active_profile" in data
            assert "profiles" in data

            r2 = client.post("/api/workspace/profiles", json={"name": "day-trading"})
            assert r2.status_code == 200
            assert r2.json()["profile"] == "day-trading"

            r2b = client.get("/api/workspace/profiles/day-trading")
            assert r2b.status_code == 200
            assert r2b.json()["profile"] == "day-trading"
            assert r2b.json()["active"] is False
            assert r2b.json()["workspace"]["layout_preset"] == "analyst"

            r2c = client.get("/api/workspace/profiles/no-such-profile")
            assert r2c.status_code == 404

            r3 = client.put("/api/workspace/active", json={"profile": "day-trading"})
            assert r3.status_code == 200
            assert r3.json()["active_profile"] == "day-trading"

            r4 = client.put("/api/workspace", json={
                "layout_preset": "trader",
                "default_ticker": "NVDA",
            })
            assert r4.status_code == 200
            assert r4.json()["workspace"]["default_ticker"] == "NVDA"

            r5 = client.get("/api/workspace/export")
            assert r5.status_code == 200
            exported = r5.json()["workspace"]
            assert "day-trading" in exported["profiles"]

            ws_mod.reset_workspace_cache()
            r6 = client.post("/api/workspace/import", json={"workspace": exported, "merge": False})
            assert r6.status_code == 200
            assert r6.json()["workspace"]["profiles"]["day-trading"]["default_ticker"] == "NVDA"

            client.put("/api/workspace/active", json={"profile": "default"})
            r7 = client.delete("/api/workspace/profiles/day-trading")
            assert r7.status_code == 200

    def test_invalid_profile_name_rejected(self, isolated_workspace, tmp_path):
        from fastapi.testclient import TestClient
        from dashboard.app import app
        import augur.workspace as ws_mod

        path = tmp_path / "api-workspace2.yaml"
        with patch.object(ws_mod, "_workspace_path", return_value=path):
            ws_mod.reset_workspace_cache()
            client = TestClient(app)
            r = client.post("/api/workspace/profiles", json={"name": "Bad Name!"})
            assert r.status_code == 400
