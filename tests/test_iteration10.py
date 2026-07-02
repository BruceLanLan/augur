# -*- coding: utf-8 -*-
"""Tests for Iteration 10: i18n coverage audit (Round 9 Agent D).

Covers 12 missing translations in dashboard/static/js/i18n.js that were
referenced by `data-i18n*` attributes in templates but never defined:

- 6 example-chip aria labels used in index.html
    a11y-chip-nvda, a11y-chip-aapl, a11y-chip-tsla, a11y-chip-msft,
    a11y-chip-btc, a11y-chip-hk
- 1 featured-persona aria label with {name} placeholder
    a11y-featured-persona
- 1 personas council description
    council-desc
- 4 signals page error panel + pending state
    signals-error-title, signals-error-msg, signals-error-retry,
    signals-add-pending

Also verifies general i18n.js invariants (key parity zh == en, no empty
values, every template-referenced key has a non-empty value in both
languages).
"""
import re
from pathlib import Path

import pytest


JS_PATH = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "js" / "i18n.js"
TPL_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "templates"

MISSING_KEYS = [
    "a11y-chip-nvda",
    "a11y-chip-aapl",
    "a11y-chip-tsla",
    "a11y-chip-msft",
    "a11y-chip-btc",
    "a11y-chip-hk",
    "a11y-featured-persona",
    "council-desc",
    "signals-error-title",
    "signals-error-msg",
    "signals-error-retry",
    "signals-add-pending",
]


# ---- Fixtures ----------------------------------------------------------------

def _parse_i18n():
    """Parse window.I18N = { zh: {...}, en: {...} } out of i18n.js.

    Avoids evaluating the full file (which references `localStorage`,
    `document`, etc.) by using a regex over the dictionary portion only.
    """
    text = JS_PATH.read_text(encoding="utf-8")
    m = re.search(r"window\.I18N\s*=\s*\{(.+?)\n\};", text, re.S)
    assert m, "i18n.js must define window.I18N = { ... }"
    inner = m.group(1)
    en_marker = inner.find("\n    en:")
    assert en_marker != -1, "i18n.js must have an 'en' block"
    ja_marker = inner.find("\n    ja:")
    en_end = ja_marker if ja_marker != -1 else len(inner)
    zh_block, en_block = inner[:en_marker], inner[en_marker:en_end]

    entry_pat = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', re.M)

    def parse(block):
        return {m.group(1): m.group(2) for m in entry_pat.finditer(block)}

    return parse(zh_block), parse(en_block)


@pytest.fixture(scope="module")
def i18n():
    return _parse_i18n()


# ---- Targeted tests for the 12 fixed keys -----------------------------------

class TestAddedI18nKeys:
    """Every key added in this round must be defined in BOTH languages."""

    @pytest.mark.parametrize("key", MISSING_KEYS)
    def test_key_defined_in_zh(self, i18n, key):
        zh, _ = i18n
        assert key in zh, f"{key!r} missing from i18n.zh"
        assert zh[key].strip(), f"{key!r} has empty value in i18n.zh"

    @pytest.mark.parametrize("key", MISSING_KEYS)
    def test_key_defined_in_en(self, i18n, key):
        _, en = i18n
        assert key in en, f"{key!r} missing from i18n.en"
        assert en[key].strip(), f"{key!r} has empty value in i18n.en"

    @pytest.mark.parametrize("key", MISSING_KEYS)
    def test_zh_contains_cjk(self, i18n, key):
        """The Chinese translation must actually contain CJK characters."""
        zh, _ = i18n
        assert re.search(r"[\u4e00-\u9fff]", zh[key]), (
            f"{key!r} zh value {zh[key]!r} has no CJK characters"
        )

    @pytest.mark.parametrize("key", MISSING_KEYS)
    def test_en_is_latin(self, i18n, key):
        """The English translation must be Latin-only (no CJK leaks)."""
        _, en = i18n
        assert not re.search(r"[\u4e00-\u9fff]", en[key]), (
            f"{key!r} en value {en[key]!r} unexpectedly contains CJK"
        )

    def test_aapl_chip_en_mentions_aapl(self, i18n):
        _, en = i18n
        assert "AAPL" in en["a11y-chip-aapl"]

    def test_btc_chip_en_mentions_btc(self, i18n):
        _, en = i18n
        assert "BTC" in en["a11y-chip-btc"]

    def test_hk_chip_en_mentions_hk(self, i18n):
        _, en = i18n
        assert "HK" in en["a11y-chip-hk"]

    def test_featured_persona_has_name_placeholder(self, i18n):
        zh, en = i18n
        assert "{name}" in zh["a11y-featured-persona"]
        assert "{name}" in en["a11y-featured-persona"]

    def test_signals_error_retry_matches_btn_retry(self, i18n):
        """signals-error-retry should reuse the same wording as btn-retry
        (consistency with the rest of the dashboard)."""
        zh, en = i18n
        assert zh["signals-error-retry"] == zh["btn-retry"], (
            "signals-error-retry should match btn-retry in zh"
        )
        assert en["signals-error-retry"] == en["btn-retry"], (
            "signals-error-retry should match btn-retry in en"
        )

    def test_signals_add_pending_has_ellipsis(self, i18n):
        zh, en = i18n
        assert "\u2026" in zh["signals-add-pending"]  # …
        assert "\u2026" in en["signals-add-pending"]


# ---- General invariants: no key drift between zh and en ----------------------

class TestI18nParity:
    """Every key defined in zh must also exist in en (and vice versa)."""

    def test_zh_en_key_parity(self, i18n):
        zh, en = i18n
        zh_only = set(zh) - set(en)
        en_only = set(en) - set(zh)
        assert not zh_only, f"keys defined in zh but not en: {sorted(zh_only)}"
        assert not en_only, f"keys defined in en but not zh: {sorted(en_only)}"

    def test_no_empty_values(self, i18n):
        zh, en = i18n
        empty_zh = [k for k, v in zh.items() if not v.strip()]
        empty_en = [k for k, v in en.items() if not v.strip()]
        assert not empty_zh, f"empty values in zh: {empty_zh}"
        assert not empty_en, f"empty values in en: {empty_en}"


# ---- Coverage test: every template data-i18n* key must be in the dict -------

class TestTemplateKeyCoverage:
    """For every key referenced by `data-i18n*` in any template, the
    key must be defined in BOTH zh and en (non-empty)."""

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

    def test_no_referenced_key_has_empty_value(self, i18n, referenced_keys):
        zh, en = i18n
        for k in referenced_keys:
            assert zh.get(k, "").strip(), f"empty zh value for referenced key {k!r}"
            assert en.get(k, "").strip(), f"empty en value for referenced key {k!r}"
