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
    """Both READMEs must display v8.2.1 in their Latest badge."""
    for rel in ("README.md", "README_EN.md"):
        text = _read(rel)
        # Badge URL form: badge/v8.2.1-Latest
        assert "badge/v8.2.1-Latest" in text, f"{rel} badge is not v8.2.1"
        assert "badge/v8.1.0-Latest" not in text, f"{rel} still has stale v8.1.0 badge"


def test_readme_changelog_marks_v8_2_1_current():
    """The top changelog entry marked (current) must be v8.2.1 (docs release), not v8.1.0."""
    for rel in ("README.md", "README_EN.md"):
        text = _read(rel)
        # The (current) marker should sit on a v8.2.0 line, not v8.1.0.
        current_block = re.search(r"<summary><strong>(v8\.\d+\.\d+)[^<]*\(current\)", text)
        assert current_block, f"{rel} has no (current) changelog entry"
        assert current_block.group(1) == "v8.2.1", (
            f"{rel} (current) entry is {current_block.group(1)}, expected v8.2.1"
        )


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


def test_pyproject_and_package_versions_agree_with_changelog():
    """pyproject + __init__.py must both declare 8.2.0, matching the changelog."""
    init_text = (ROOT / "src" / "augur" / "__init__.py").read_text(encoding="utf-8")
    assert '__version__ = "8.2.0"' in init_text, "src/augur/__init__.py version is not 8.2.0"

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    # Match either "version = "8.2.0"" or 'version = "8.2.0"'
    assert re.search(r'version\s*=\s*"8\.2\.0"', pyproject), \
        "pyproject.toml version is not 8.2.0"
