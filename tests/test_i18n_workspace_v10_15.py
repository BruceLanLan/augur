# -*- coding: utf-8 -*-
"""v10.15: workspace terminal settings i18n coverage across zh/en/ja/ko."""
import json
import re
from pathlib import Path

import pytest

JS_PATH = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "js" / "i18n.js"
I18N_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "i18n"
SETTINGS_HTML = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "templates" / "settings.html"

WORKSPACE_KEYS = [
    "settings-section-workspace-title",
    "settings-section-workspace-desc",
    "settings-workspace-preset-label",
    "settings-workspace-default-page",
    "settings-workspace-default-ticker",
    "settings-workspace-ticker-tape",
    "settings-workspace-sidebar-collapsed",
    "settings-workspace-hidden-nav",
    "settings-workspace-enabled-personas",
    "settings-workspace-enabled-personas-hint",
    "settings-workspace-personas-all",
    "settings-workspace-personas-clear",
    "settings-workspace-personas-required",
    "settings-workspace-save",
    "settings-workspace-saved",
    "settings-workspace-preset-applied",
    "settings-workspace-profile-label",
    "settings-workspace-profile-delete",
    "settings-workspace-profile-create",
    "settings-workspace-profile-switched",
    "settings-workspace-profile-name-required",
    "settings-workspace-profile-created",
    "settings-workspace-profile-cannot-delete",
    "settings-workspace-profile-delete-confirm",
    "settings-workspace-profile-deleted",
    "workspace-preset-analyst",
    "workspace-preset-trader",
    "workspace-preset-committee",
    "workspace-preset-minimal",
]

JSON_WORKSPACE_KEYS = [
    "section_title",
    "section_desc",
    "preset_label",
    "default_page",
    "default_ticker",
    "ticker_tape",
    "sidebar_collapsed",
    "hidden_nav",
    "enabled_personas",
    "enabled_personas_hint",
    "personas_all",
    "personas_clear",
    "personas_required",
    "save",
    "saved",
    "preset_applied",
    "preset_analyst",
    "preset_trader",
    "preset_committee",
    "preset_minimal",
    "profile_label",
    "profile_delete",
    "profile_create",
    "profile_switched",
    "profile_name_required",
    "profile_created",
    "profile_cannot_delete",
    "profile_delete_confirm",
    "profile_deleted",
]

LANG_MARKERS = ["zh:", "en:", "ja:", "ko:"]


def _parse_i18n_js():
    text = JS_PATH.read_text(encoding="utf-8")
    m = re.search(r"window\.I18N\s*=\s*\{(.+?)\n\};", text, re.S)
    assert m, "i18n.js must define window.I18N = { ... }"
    inner = m.group(1)
    entry_pat = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', re.M)

    def parse(block):
        return {em.group(1): em.group(2) for em in entry_pat.finditer(block)}

    blocks = {}
    for i, lang in enumerate(LANG_MARKERS):
        start = inner.find(f"\n    {lang}")
        assert start != -1, f"i18n.js must have a '{lang[:-1]}' block"
        end = len(inner)
        for later in LANG_MARKERS[i + 1:]:
            pos = inner.find(f"\n    {later}", start + 1)
            if pos != -1:
                end = pos
                break
        blocks[lang[:-1]] = parse(inner[start:end])
    return blocks


@pytest.fixture(scope="module")
def i18n_blocks():
    return _parse_i18n_js()


class TestWorkspaceI18nJs:
    @pytest.mark.parametrize("lang", ["zh", "en", "ja", "ko"])
    @pytest.mark.parametrize("key", WORKSPACE_KEYS)
    def test_workspace_key_defined(self, i18n_blocks, lang, key):
        block = i18n_blocks[lang]
        assert key in block, f"{key!r} missing from i18n.{lang}"
        assert block[key].strip(), f"{key!r} has empty value in i18n.{lang}"

    def test_settings_html_references_covered(self):
        html = SETTINGS_HTML.read_text(encoding="utf-8")
        skip_in_html = {
            "settings-workspace-saved",
            "settings-workspace-preset-applied",
            "settings-workspace-profile-switched",
            "settings-workspace-profile-name-required",
            "settings-workspace-profile-created",
            "settings-workspace-profile-cannot-delete",
            "settings-workspace-profile-delete-confirm",
            "settings-workspace-profile-deleted",
            "settings-workspace-personas-required",
        }
        for key in WORKSPACE_KEYS:
            if key in skip_in_html:
                continue
            assert f'data-i18n="{key}"' in html or f"_t('{key}'" in html, (
                f"{key!r} referenced in settings flow but not found in settings.html"
            )


class TestWorkspaceI18nJson:
    @pytest.mark.parametrize("lang", ["en", "zh"])
    @pytest.mark.parametrize("key", JSON_WORKSPACE_KEYS)
    def test_workspace_section_in_json(self, lang, key):
        data = json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))
        workspace = data.get("workspace")
        assert workspace is not None, f"{lang}.json must define a 'workspace' section"
        assert key in workspace, f"workspace.{key} missing from {lang}.json"
        assert str(workspace[key]).strip(), f"workspace.{key} empty in {lang}.json"
