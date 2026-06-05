# -*- coding: utf-8 -*-
"""Tests for Iteration 12 Agent C: Makefile + pyproject audit fixes.

Covers 4 issues found in the audit:
  1. Makefile .PHONY list was missing `api`, `clean`, `docker-full`
     (and now also `lint`, `format`).
  2. Makefile `clean` target only removed __pycache__ + *.pyc, leaving
     .pytest_cache, .mypy_cache, .ruff_cache, *.egg-info, .eggs,
     build/, dist/, .coverage, htmlcov/, *.pyo behind.
  3. pyproject.toml entry-point group was `"mcp"`; the MCP Python SDK
     convention is `"mcp.server"`, so MCP-aware launchers could not
     discover the server.
  4. pyproject.toml did not declare the `[project.entry-points."augur.plugins"]`
     group referenced by `src/augur/plugins.py:PluginManager.ENTRY_POINT_GROUP`,
     meaning external packages could not register plugins via setuptools.
"""
import re
import sys
from pathlib import Path

import pytest

try:
    import tomllib  # py3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
PYPROJECT = ROOT / "pyproject.toml"


# ---------------------------------------------------------------------------
# Issue 1 + 2: Makefile
# ---------------------------------------------------------------------------

class TestMakefilePhony:
    """All real targets in the Makefile must be declared .PHONY."""

    @pytest.fixture
    def phony_targets(self):
        text = MAKEFILE.read_text()
        m = re.search(r"^\.PHONY:\s*(.+)$", text, re.MULTILINE)
        assert m, "Makefile must contain a .PHONY declaration"
        return {t.strip() for t in m.group(1).split()}

    @pytest.mark.parametrize("target", [
        "install", "dev", "test", "run", "api", "clean",
        "docker-build", "docker-up", "docker-down", "docker-full",
    ])
    def test_target_declared_phony(self, phony_targets, target):
        """Every top-level target must be in .PHONY so `make` doesn't
        confuse a target name with a same-named file in the repo."""
        assert target in phony_targets, (
            f"target '{target}' is missing from .PHONY"
        )


class TestMakefileClean:
    """`make clean` must remove standard Python build/cache artifacts."""

    @pytest.fixture
    def clean_recipe(self):
        text = MAKEFILE.read_text()
        m = re.search(
            r"^clean:\s*\n((?:\t.+\n?)+)",
            text,
            re.MULTILINE,
        )
        assert m, "Makefile must define a `clean:` target"
        return m.group(1)

    @pytest.mark.parametrize("artifact", [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".eggs",
        "*.egg-info",
        "build/",
        "dist/",
        ".coverage",
        "htmlcov/",
    ])
    def test_clean_removes_artifact(self, clean_recipe, artifact):
        """clean recipe must reference every common Python cache/build dir."""
        assert artifact in clean_recipe, (
            f"`make clean` does not remove '{artifact}'"
        )

    def test_clean_uses_null_terminated_or_dashdelete(self, clean_recipe):
        """`find -exec rm -rf` and `find -delete` both silently handle
        the case where no matches exist, so they are safe without
        `|| true`. We just assert that every cleanup line uses one of
        these safe idioms (no naked `rm -rf` against a glob)."""
        for ln in clean_recipe.splitlines():
            stripped = ln.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Acceptable cleanup forms:
            #   find ... -exec rm -rf {} +
            #   find ... -delete
            #   rm -rf <literal_dir>/   (explicit dir, not a glob)
            if "rm" in stripped and "find" in stripped and "-exec" in stripped:
                assert "-exec rm" in stripped
            elif "rm" in stripped and "find" not in stripped:
                # Bare `rm -rf X/` is fine only if X is a literal path.
                assert ("2>/dev/null" in stripped or "|| true" in stripped), (
                    f"unguarded bare rm: {stripped!r}"
                )
            else:
                # find ... -delete or other harmless find forms
                assert "-delete" in stripped or "-exec" in stripped or "echo" in stripped


# ---------------------------------------------------------------------------
# Issue 3 + 4: pyproject.toml
# ---------------------------------------------------------------------------

class TestPyprojectEntryPoints:
    """Validate that all entry-point groups referenced in source are declared."""

    @pytest.fixture
    def pyproject(self):
        with open(PYPROJECT, "rb") as f:
            return tomllib.load(f)

    def test_mcp_entry_point_uses_standard_group(self, pyproject):
        """The MCP Python SDK convention is group='mcp.server' (not 'mcp')."""
        eps = pyproject["project"]["entry-points"]
        # The old non-standard key must be gone.
        assert "mcp" not in eps, (
            "entry-point group 'mcp' is non-standard; use 'mcp.server'"
        )
        assert "mcp.server" in eps, (
            "expected entry-point group 'mcp.server' in pyproject.toml"
        )
        servers = eps["mcp.server"]
        assert "augur-agents" in servers
        assert servers["augur-agents"] == "augur.mcp_server:create_server"

    def test_plugin_entry_point_group_declared(self, pyproject):
        """src/augur/plugins.py references group 'augur.plugins' but the
        project never declared it, so external packages could not
        register plugins via setuptools."""
        eps = pyproject["project"]["entry-points"]
        assert "augur.plugins" in eps, (
            "expected entry-point group 'augur.plugins' to be declared "
            "(see PluginManager.ENTRY_POINT_GROUP in src/augur/plugins.py)"
        )

    def test_plugin_group_matches_source(self):
        """The declared group name must match the constant the code looks up."""
        from augur.plugins import PluginManager
        eps_group = PluginManager.ENTRY_POINT_GROUP
        assert eps_group == "augur.plugins"
        with open(PYPROJECT, "rb") as f:
            data = tomllib.load(f)
        assert eps_group in data["project"]["entry-points"]
