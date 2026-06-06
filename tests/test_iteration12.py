# -*- coding: utf-8 -*-
"""Tests for Iteration 12: Round 10 i18n coverage expansion.

Adds 6 new translations to dashboard/static/js/i18n.js for keys that are
referenced by signals.html via ``_t('key')`` and inline ``aria-label``
attributes that should be language-aware:

- 2 example chip / row aria-labels that were missing from i18n.js even
  though they were already being requested at runtime:
    signals-add-example-aria, signals-row-aria
- 4 new aria-labels for the signals filter & form controls that had
  hard-coded English text in the template:
    signals-filter-type-aria, signals-filter-sort-aria,
    signals-add-pe-aria, signals-add-roe-aria

Also re-runs the iteration 10 parity / coverage invariants.
"""
import re
from pathlib import Path

import pytest


JS_PATH = Path(__file__).resolve().parents[1] / "dashboard" / "static" / "js" / "i18n.js"
TPL_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "templates"

NEW_KEYS = [
    "signals-add-example-aria",
    "signals-row-aria",
    "signals-filter-type-aria",
    "signals-filter-sort-aria",
    "signals-add-pe-aria",
    "signals-add-roe-aria",
]


def _parse_i18n():
    text = JS_PATH.read_text(encoding="utf-8")
    m = re.search(r"window\.I18N\s*=\s*\{(.+?)\n\};", text, re.S)
    assert m, "i18n.js must define window.I18N = { ... }"
    inner = m.group(1)
    en_marker = inner.find("\n    en:")
    assert en_marker != -1, "i18n.js must have an 'en' block"
    zh_block, en_block = inner[:en_marker], inner[en_marker:]

    entry_pat = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', re.M)

    def parse(block):
        return {m.group(1): m.group(2) for m in entry_pat.finditer(block)}

    return parse(zh_block), parse(en_block)


@pytest.fixture(scope="module")
def i18n():
    return _parse_i18n()


class TestRound10Keys:
    """The 6 new keys must be defined in both languages with proper scripts."""

    @pytest.mark.parametrize("key", NEW_KEYS)
    def test_key_defined_in_zh(self, i18n, key):
        zh, _ = i18n
        assert key in zh, f"{key!r} missing from i18n.zh"
        assert zh[key].strip(), f"{key!r} has empty value in i18n.zh"

    @pytest.mark.parametrize("key", NEW_KEYS)
    def test_key_defined_in_en(self, i18n, key):
        _, en = i18n
        assert key in en, f"{key!r} missing from i18n.en"
        assert en[key].strip(), f"{key!r} has empty value in i18n.en"

    @pytest.mark.parametrize("key", NEW_KEYS)
    def test_zh_contains_cjk(self, i18n, key):
        zh, _ = i18n
        assert re.search(r"[\u4e00-\u9fff]", zh[key]), (
            f"{key!r} zh value {zh[key]!r} has no CJK characters"
        )

    @pytest.mark.parametrize("key", NEW_KEYS)
    def test_en_is_latin(self, i18n, key):
        _, en = i18n
        assert not re.search(r"[\u4e00-\u9fff]", en[key]), (
            f"{key!r} en value {en[key]!r} unexpectedly contains CJK"
        )

    def test_zh_en_key_parity(self, i18n):
        """Adding new keys must not break parity between zh and en dicts."""
        zh, en = i18n
        zh_only = set(zh) - set(en)
        en_only = set(en) - set(zh)
        assert not zh_only, f"keys defined in zh but not en: {sorted(zh_only)}"
        assert not en_only, f"keys defined in en but not zh: {sorted(en_only)}"

    def test_quick_add_en_short(self, i18n):
        """signals-add-example-aria is concatenated with the ticker ('AAPL' etc.),
        so the en value should be terse enough to read naturally."""
        _, en = i18n
        assert len(en["signals-add-example-aria"]) <= 20

    def test_filter_type_en_mentions_signal(self, i18n):
        _, en = i18n
        assert "signal" in en["signals-filter-type-aria"].lower()

    def test_pe_key_mentions_pe(self, i18n):
        zh, en = i18n
        # zh has "PE" in the value already, en is "PE ratio"
        assert "PE" in en["signals-add-pe-aria"]
        assert "PE" in zh["signals-add-pe-aria"] or "市盈率" in zh["signals-add-pe-aria"]

    def test_roe_key_mentions_roe(self, i18n):
        zh, en = i18n
        assert "ROE" in en["signals-add-roe-aria"]
        assert "ROE" in zh["signals-add-roe-aria"] or "净资产" in zh["signals-add-roe-aria"]


# ---- Re-run coverage invariant for templates --------------------------------

class TestTemplateKeyCoverageRound10:
    @pytest.fixture(scope="class")
    def referenced_keys(self):
        pat = re.compile(r'data-i18n(?:-aria|-title)?="([^"]+)"')
        keys = set()
        for p in TPL_DIR.glob("*.html"):
            for k in pat.findall(p.read_text(encoding="utf-8")):
                if "{{" not in k:  # skip Jinja template expressions
                    keys.add(k)
        return keys

    def test_every_referenced_key_defined(self, i18n, referenced_keys):
        zh, en = i18n
        missing = referenced_keys - set(zh)
        assert not missing, f"template keys missing in zh: {sorted(missing)}"
        missing = referenced_keys - set(en)
        assert not missing, f"template keys missing in en: {sorted(missing)}"

    def test_no_empty_values(self, i18n):
        zh, en = i18n
        empty_zh = [k for k, v in zh.items() if not v.strip()]
        empty_en = [k for k, v in en.items() if not v.strip()]
        assert not empty_zh, f"empty values in zh: {empty_zh}"
        assert not empty_en, f"empty values in en: {empty_en}"
