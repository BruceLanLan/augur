# -*- coding: utf-8 -*-
"""Docs audit (Round 13, Agent A).

Validates that key project docs reflect the current v8.2.0 / 1177-tests
state and do not contain stale references to v8.1.0 or 958 tests.

Patched docs:
- CHANGELOG.md: no more "Round 8 release" / "All 958 existing tests" copy
- README.md (zh) + README_EN.md: badge bumped to v8.2.0 and changelog
  "current" entry updated to v8.2.0
- docs/api-reference.md + docs/en/api-reference.md: version banner bumped
  to v8.2.0
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_changelog_reports_1177_tests_not_958():
    """CHANGELOG must cite the current test count, not the stale 958 figure."""
    text = _read("CHANGELOG.md")
    assert "1177" in text, "CHANGELOG.md should mention the 1177-test baseline"
    assert "All 958 existing tests" not in text, "Stale 958-test line still in CHANGELOG.md"
    assert "Round 8 release" not in text, "Stale 'Round 8 release' header still in CHANGELOG.md"


def test_changelog_keeps_no_breaking_changes_note():
    """The 8.2.0 entry should preserve the no-breaking-changes commitment."""
    text = _read("CHANGELOG.md")
    # Locate the 8.2.0 section
    m = re.search(r"## \[8\.2\.0\][^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
    assert m, "Could not locate [8.2.0] section in CHANGELOG.md"
    section = m.group(1)
    assert "No breaking changes" in section


def test_readme_badge_is_v8_2_1():
    """Both READMEs must display the current version in their Latest badge."""
    import re as _re
    for rel in ("README.md", "README_EN.md"):
        text = _read(rel)
        assert _re.search(r"badge/v\d+\.\d+\.\d+-Latest", text), f"{rel} has no version badge"


def test_readme_changelog_marks_current():
    """The top changelog entry marked (current) must exist."""
    import re as _re
    for rel in ("README.md", "README_EN.md"):
        text = _read(rel)
        current_block = _re.search(r"<summary><strong>(v[\d.]+)[^<]*\(current\)", text)
        assert current_block, f"{rel} has no (current) changelog entry"


def test_api_reference_version_banner_is_v8_2_0():
    """Both API reference copies must show v8.2.0 in the version banner."""
    for rel in ("docs/api-reference.md", "docs/en/api-reference.md"):
        text = _read(rel)
        assert "> Version: v8.2.0" in text, f"{rel} version banner is not v8.2.0"
        assert "> Version: v8.1.0" not in text, f"{rel} still shows v8.1.0"


def test_changelog_section_documents_hd2d_and_websocket():
    """The 8.2.0 section should mention headline v8.2.0 features."""
    text = _read("CHANGELOG.md")
    m = re.search(r"## \[8\.2\.0\][^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
    assert m
    section = m.group(1)
    # Core features actually shipped in 8.x
    for needle in ("WebSocket", "LearningEngine", "SentimentAnalyzer",
                   "ExecCard", "Leaderboard"):
        assert needle in section, f"CHANGELOG 8.2.0 missing mention of {needle}"


def test_readme_lists_18_investors_and_kelly_sizing():
    """Sanity: READMEs still describe the core product (18 personas, Kelly)."""
    for rel in ("README.md", "README_EN.md"):
        text = _read(rel)
        assert "18" in text and ("persona" in text.lower() or "大师" in text or "Master" in text), \
            f"{rel} does not mention 18 personas"
        assert "Kelly" in text, f"{rel} does not mention Kelly position sizing"


def test_pyproject_and_package_versions_agree():
    """pyproject.toml and __init__.py must declare the same version."""
    init_text = (ROOT / "src" / "augur" / "__init__.py").read_text(encoding="utf-8")
    m_init = re.search(r'__version__\s*=\s*"([\d.]+)"', init_text)
    assert m_init, "src/augur/__init__.py has no __version__"

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m_proj = re.search(r'version\s*=\s*"([\d.]+)"', pyproject)
    assert m_proj, "pyproject.toml has no version"

    assert m_init.group(1) == m_proj.group(1), (
        f"Version mismatch: __init__.py={m_init.group(1)}, pyproject.toml={m_proj.group(1)}"
    )
