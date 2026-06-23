# -*- coding: utf-8 -*-
"""Tests for v10.16: MCP workspace tools (P1-1).

Closes the "agent hosts can't read/apply terminal workspace state" gap from
docs/AGENT_PEER_REVIEW_SYNTHESIS.md — these are the testable helper functions
behind augur_workspace_get / augur_workspace_set / augur_workspace_profiles.
"""

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


class TestWorkspaceGetTool:
    def test_get_active_profile_default(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_get_tool

        out = _run_workspace_get_tool()
        assert "Profile: default (active)" in out
        assert "Layout preset:     analyst" in out

    def test_get_named_profile_without_switching(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_get_tool

        isolated_workspace.create_profile("research", copy_from="default")
        out = _run_workspace_get_tool(profile="research")
        assert "Profile: research" in out
        assert "(active)" not in out
        # active profile is unaffected
        assert isolated_workspace.get_workspace_state()["active_profile"] == "default"

    def test_get_unknown_profile_errors(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_get_tool

        out = _run_workspace_get_tool(profile="nope")
        assert out.startswith("Error:")
        assert "default" in out  # lists available profiles


class TestWorkspaceSetTool:
    def test_set_partial_field_preserves_rest(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_set_tool

        isolated_workspace.save_workspace({"layout_preset": "trader", "show_ticker_tape": False})
        out = _run_workspace_set_tool(default_ticker="NVDA")
        assert "Default ticker:    NVDA" in out
        # fields not passed must be untouched
        assert "Layout preset:     trader" in out
        assert "Show ticker tape:  False" in out

    def test_set_enabled_personas_comma_list(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_set_tool

        out = _run_workspace_set_tool(enabled_personas="buffett, munger ,graham")
        assert "Enabled personas:  buffett, munger, graham" in out
        assert isolated_workspace.get_workspace()["enabled_personas"] == ["buffett", "munger", "graham"]

    def test_set_enabled_personas_none_clears(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_set_tool

        _run_workspace_set_tool(enabled_personas="buffett,munger")
        out = _run_workspace_set_tool(enabled_personas="none")
        assert "Enabled personas:  (all)" in out
        assert isolated_workspace.get_workspace()["enabled_personas"] == []

    def test_set_on_named_profile_does_not_switch_active(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_set_tool

        isolated_workspace.create_profile("research", copy_from="default")
        _run_workspace_set_tool(profile="research", default_ticker="AAPL")
        assert isolated_workspace.get_workspace_state()["active_profile"] == "default"
        assert isolated_workspace.get_profile("research")["default_ticker"] == "AAPL"

    def test_set_unknown_profile_errors(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_set_tool

        out = _run_workspace_set_tool(profile="ghost", default_ticker="AAPL")
        assert out.startswith("Error:")

    def test_set_invalid_profile_name_errors(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_set_tool

        out = _run_workspace_set_tool(profile="Has Spaces!", default_ticker="AAPL")
        assert out.startswith("Error:")


class TestWorkspaceProfilesTool:
    def test_list_shows_active_marker(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_profiles_tool

        out = _run_workspace_profiles_tool(action="list")
        assert "active: default" in out
        assert "default *" in out

    def test_create_copies_from_source_without_activating(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_profiles_tool

        isolated_workspace.save_workspace({"layout_preset": "committee"})
        out = _run_workspace_profiles_tool(action="create", name="research", copy_from="default")
        assert "Created." in out
        assert "Layout preset:     committee" in out
        assert "(active)" not in out
        assert isolated_workspace.get_workspace_state()["active_profile"] == "default"

    def test_switch_then_delete_previous(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_profiles_tool

        _run_workspace_profiles_tool(action="create", name="research")
        out = _run_workspace_profiles_tool(action="switch", name="research")
        assert "Switched." in out
        assert "(active)" in out
        assert isolated_workspace.get_workspace_state()["active_profile"] == "research"

        out = _run_workspace_profiles_tool(action="delete", name="default")
        assert "Deleted profile 'default'" in out

    def test_cannot_delete_active_profile(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_profiles_tool

        out = _run_workspace_profiles_tool(action="delete", name="default")
        assert out.startswith("Error:")

    def test_unknown_action_errors(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_profiles_tool

        out = _run_workspace_profiles_tool(action="bogus", name="x")
        assert "Error" in out

    def test_missing_name_for_create_errors(self, isolated_workspace):
        from augur.mcp_server import _run_workspace_profiles_tool

        out = _run_workspace_profiles_tool(action="create", name="")
        assert out.startswith("Error:")


class TestMcpManifestSync:
    """Guard against the 'manifest/doc drift' failure mode called out in
    docs/AGENT_PEER_REVIEW_SYNTHESIS.md: .mcp.json's tool list silently
    falling behind the @mcp.tool()-decorated functions in mcp_server.py.
    Pure AST inspection — does not require the optional `mcp` package.
    """

    def _registered_tool_names(self):
        import ast
        import augur.mcp_server as mcp_server_mod

        src_path = Path(mcp_server_mod.__file__)
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "tool":
                        names.append(node.name)
        return names, src_path

    def test_mcp_json_tools_match_source(self):
        import json

        names, src_path = self._registered_tool_names()
        assert len(names) == 13

        repo_root = None
        for p in [src_path] + list(src_path.parents):
            if (p / ".mcp.json").exists():
                repo_root = p
                break
        assert repo_root is not None, ".mcp.json not found relative to mcp_server.py"

        manifest = json.loads((repo_root / ".mcp.json").read_text(encoding="utf-8"))
        manifest_tools = set(manifest["mcpServers"]["augur"]["tools"])
        assert manifest_tools == set(names)

    def test_workspace_tools_present(self):
        names, _ = self._registered_tool_names()
        for name in ("augur_workspace_get", "augur_workspace_set", "augur_workspace_profiles"):
            assert name in names
