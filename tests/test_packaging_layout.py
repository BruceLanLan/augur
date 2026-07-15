# -*- coding: utf-8 -*-
"""Regression guard for the v10.2.0 packaging fix.

dashboard/ and skills/ used to live at the repo root, outside src/, which
[tool.setuptools.packages.find] never packages. A real `python -m build`
confirmed the resulting wheel contained zero dashboard/* files — `pip
install augur-agents; augur serve` hard-failed with an ImportError. See
CHANGELOG.md [10.2.0] for the full incident writeup.

These tests exercise the actual setuptools discovery mechanism (cheap, no
network, no full wheel build) so this specific failure mode can't silently
come back — e.g. if someone moves dashboard/ or skills/ back to the repo
root, or the package-data globs get deleted from pyproject.toml.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDashboardAndSkillsAreUnderSrc:
    """The literal directory layout setuptools.packages.find relies on."""

    def test_dashboard_lives_under_src(self):
        assert (REPO_ROOT / "src" / "dashboard" / "app.py").is_file()
        assert (REPO_ROOT / "src" / "dashboard" / "__init__.py").is_file()

    def test_skills_lives_under_src(self):
        assert (REPO_ROOT / "src" / "skills" / "__init__.py").is_file()
        assert (REPO_ROOT / "src" / "skills" / "augur-buffett" / "SKILL.md").is_file()

    def test_no_stale_dashboard_or_skills_at_repo_root(self):
        """Guards against a future accidental copy/move back to the root
        (e.g. a merge conflict resolution) creating a second, unpackaged copy."""
        assert not (REPO_ROOT / "dashboard").exists()
        assert not (REPO_ROOT / "skills").exists()


class TestSetuptoolsDiscoversThem:
    """Exercises the real discovery mechanism the wheel build uses."""

    def test_find_packages_discovers_dashboard_and_skills(self):
        from setuptools import find_packages
        pkgs = find_packages(where=str(REPO_ROOT / "src"))
        assert "dashboard" in pkgs
        assert "dashboard.routes" in pkgs
        assert "skills" in pkgs
        assert "augur" in pkgs


class TestPackageDataConfig:
    """pyproject.toml must declare package-data for the non-.py assets that
    live inside dashboard/ (templates/static/i18n) and skills/ (md/json) —
    packages.find alone only picks up .py files.

    Parsed with plain text + regex rather than a TOML library, matching this
    repo's existing convention (see test_docs_audit_r13a.py) — the test
    suite targets Python 3.9, which predates stdlib tomllib.
    """

    @pytest.fixture(scope="class")
    def pyproject_text(self):
        return (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    def test_dashboard_package_data_declared(self, pyproject_text):
        m = re.search(r'^dashboard\s*=\s*\[([^\]]*)\]', pyproject_text, re.M)
        assert m, "no `dashboard = [...]` line under [tool.setuptools.package-data]"
        globs = m.group(1)
        assert "templates" in globs
        assert "static" in globs
        assert "i18n" in globs

    def test_skills_package_data_declared(self, pyproject_text):
        m = re.search(r'^skills\s*=\s*\[([^\]]*)\]', pyproject_text, re.M)
        assert m, "no `skills = [...]` line under [tool.setuptools.package-data]"
        globs = m.group(1)
        assert ".md" in globs
        assert ".json" in globs

    def test_packages_find_where_includes_src(self, pyproject_text):
        m = re.search(r'^\[tool\.setuptools\.packages\.find\]\s*\nwhere\s*=\s*\[([^\]]*)\]', pyproject_text, re.M)
        assert m, "no [tool.setuptools.packages.find] where= line"
        assert '"src"' in m.group(1)


class TestCliPathResolutionMatchesLayout:
    """`augur serve`/`augur skills` path resolution must point at
    src/dashboard and src/skills relative to wherever the resolving file
    actually lives, not a repo-root-relative assumption that only worked by
    incidental cwd-on-sys.path behavior in a dev checkout.

    R7 (v10.7.0) split cli.py into augur.cli_commands.*; the resolution code
    now lives in cli_commands/server.py and cli_commands/meta.py, one
    directory level deeper than the original src/augur/cli.py, so the
    correct parents[] depth shifted from 1 to 2 accordingly.
    """

    def test_cli_resolves_dashboard_relative_to_src(self):
        server_source = (REPO_ROOT / "src" / "augur" / "cli_commands" / "server.py").read_text(encoding="utf-8")
        assert 'parents[2] / "dashboard"' in server_source
        assert 'parents[1] / "dashboard"' not in server_source
        assert 'parents[3] / "dashboard"' not in server_source

    def test_cli_resolves_skills_relative_to_src(self):
        meta_source = (REPO_ROOT / "src" / "augur" / "cli_commands" / "meta.py").read_text(encoding="utf-8")
        assert 'parents[2] / "skills"' in meta_source
        assert 'parents[1] / "skills"' not in meta_source
        assert 'parents[3] / "skills"' not in meta_source


class TestDashboardImagesMountResolvesToRepoRoot:
    """R7's dashboard/ -> src/dashboard/ move (d8af2a0) shifted app.py one
    directory level deeper without updating IMAGES_DIR's ".parent.parent",
    which silently 404'd every persona avatar dashboard-wide (the mount's
    own `if IMAGES_DIR.exists()` guard means this never raised -- found via
    a real Playwright run during v10.15.0 release prep, not caught by any
    existing test since nothing exercised actual image loading in a
    browser). docs/images isn't in package-data (not shipped in the wheel),
    so this only matters in a dev checkout -- but it must resolve correctly
    there, where the files really do exist.
    """

    def test_images_dir_resolves_to_real_repo_root_docs_images(self):
        app_source = (REPO_ROOT / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
        assert 'IMAGES_DIR = Path(__file__).parent.parent.parent / "docs" / "images"' in app_source

        # The literal computation app.py performs, mirrored here rather than
        # importing dashboard.app (which has heavy import-time side effects)
        # -- must land on the real docs/images that actually has avatar PNGs.
        app_py_path = REPO_ROOT / "src" / "dashboard" / "app.py"
        images_dir = app_py_path.parent.parent.parent / "docs" / "images"
        assert images_dir == REPO_ROOT / "docs" / "images"
        assert images_dir.exists()
        assert (images_dir / "avatars" / "buffett.png").exists()
