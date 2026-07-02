"""Regression tests for P1-2 and P1-4 from docs/AGENT_PEER_REVIEW_SYNTHESIS.md.

P1-2: persona manifest.json / Hermes yaml must track the live augur version
      and document the full MCP tool surface, not a stale snapshot.
P1-4: the committee page must apply the workspace's stored committee_preset
      on load instead of always defaulting to the hardcoded "all" lineup.
"""
import json
import re
from pathlib import Path

import yaml

from augur import __version__

ROOT = Path(__file__).parent.parent


def _persona_manifest_dirs():
    skills_dir = ROOT / "src" / "skills"
    return [d for d in skills_dir.iterdir() if d.is_dir() and (d / "manifest.json").exists()]


class TestPersonaManifestVersionSync:
    def test_all_manifests_match_live_version(self):
        stale = []
        for d in _persona_manifest_dirs():
            data = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
            if data.get("version") != __version__:
                stale.append((d.name, data.get("version")))
        assert not stale, f"manifest.json version drift vs augur.__version__={__version__}: {stale}"

    def test_all_skill_md_frontmatter_match_live_version(self):
        stale = []
        for d in _persona_manifest_dirs():
            skill_md = d / "SKILL.md"
            if not skill_md.exists():
                continue
            text = skill_md.read_text(encoding="utf-8")
            m = re.search(r"^version:\s*(\S+)", text, re.MULTILINE)
            if m and m.group(1) != __version__:
                stale.append((d.name, m.group(1)))
        assert not stale, f"SKILL.md version drift vs augur.__version__={__version__}: {stale}"


class TestHermesAgentVersionSync:
    def test_all_hermes_yaml_match_live_version(self):
        hermes_dir = ROOT / "hermes-agents"
        stale = []
        for f in hermes_dir.glob("*.yaml"):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            version = str(data.get("version", "")).strip('"')
            if version != __version__:
                stale.append((f.name, version))
        assert not stale, f"hermes-agents yaml version drift vs augur.__version__={__version__}: {stale}"


class TestCommitteePresetWiring:
    def test_committee_page_fetches_workspace_on_load(self):
        html = (ROOT / "src" / "dashboard" / "templates" / "committee.html").read_text(encoding="utf-8")
        assert "fetch('/api/workspace')" in html
        assert "ws.committee_preset" in html
        assert "loadPreset(preset)" in html
