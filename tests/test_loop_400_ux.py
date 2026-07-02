# -*- coding: utf-8 -*-
"""Loop 400 UX tests — backtest i18n, settings toasts, scanner edge cases."""
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "templates"
I18N_JS = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "js" / "i18n.js"


def _read(name: str) -> str:
    p = TEMPLATES_DIR / name
    assert p.is_file(), f"Missing template: {p}"
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def i18n_dicts():
    text = I18N_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.I18N\s*=\s*\{(.+?)\n\};", text, re.S)
    assert m, "i18n.js must define window.I18N"
    inner = m.group(1)
    en_marker = inner.find("\n    en:")
    assert en_marker != -1
    ja_marker = inner.find("\n    ja:")
    en_end = ja_marker if ja_marker != -1 else len(inner)
    entry_pat = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', re.M)

    def _parse(block):
        return {em.group(1): em.group(2) for em in entry_pat.finditer(block)}

    return _parse(inner[:en_marker]), _parse(inner[en_marker:en_end])


BACKTEST_I18N_KEYS = [
    "backtest-title",
    "backtest-desc",
    "backtest-ticker-label",
    "backtest-ticker-empty",
    "backtest-ticker-invalid",
    "backtest-run",
    "backtest-running",
    "backtest-loading",
    "backtest-error-timeout",
    "backtest-leaderboard-title",
    "backtest-col-hitrate",
    "backtest-timeline-title",
]

SETTINGS_TOAST_KEYS = [
    "settings-toast-preset-applied",
    "settings-toast-saved-all",
    "settings-toast-enter-api-key",
    "settings-toast-exported",
    "settings-toast-cron-saved",
    "settings-toast-token-saved",
    "settings-toast-auth-success",
    "settings-api-token-ph",
]

SCANNER_EDGE_KEYS = [
    "scanner-invalid-ticker",
    "scanner-timeout",
    "scanner-partial-errors",
    "scanner-error-row",
    "scanner-all-failed",
]


class TestBacktestI18n:
    @pytest.mark.parametrize("key", BACKTEST_I18N_KEYS)
    def test_backtest_keys_in_i18n(self, i18n_dicts, key):
        zh, en = i18n_dicts
        assert key in zh and key in en
        assert zh[key].strip() and en[key].strip()

    def test_backtest_page_has_data_i18n_title(self):
        soup = BeautifulSoup(_read("backtest.html"), "html.parser")
        assert soup.find(attrs={"data-i18n": "backtest-title"}) is not None

    def test_backtest_js_uses_t_helper(self):
        text = _read("backtest.html")
        assert "function _t(key, fb)" in text
        assert "_t('backtest-ticker-empty')" in text
        assert "backtest-running" in text
        assert "_t('backtest-error-timeout')" in text
        assert "_setRunBtnBusy" in text

    def test_backtest_js_no_hardcoded_validation_zh(self):
        text = _read("backtest.html")
        m = re.search(r"async function runBacktest\(\)\s*\{(.+?)\n\}", text, re.DOTALL)
        assert m
        body = m.group(1)
        assert "代码不能为空" not in body
        assert "回测中..." not in body


class TestSettingsToasts:
    @pytest.mark.parametrize("key", SETTINGS_TOAST_KEYS)
    def test_settings_toast_keys_in_i18n(self, i18n_dicts, key):
        zh, en = i18n_dicts
        assert key in zh and key in en

    def test_all_showtoast_use_t(self):
        text = _read("settings.html")
        calls = re.findall(r"showToast\(([^)]+)\)", text)
        assert calls
        for call in calls:
            assert "_t(" in call or "err.message" in call or "data.detail" in call

    def test_api_token_placeholder_i18n(self):
        assert "_t('settings-api-token-ph'" in _read("settings.html")


class TestScannerEdgeCases:
    @pytest.mark.parametrize("key", SCANNER_EDGE_KEYS)
    def test_scanner_edge_keys_in_i18n(self, i18n_dicts, key):
        zh, en = i18n_dicts
        assert key in zh and key in en

    def test_parse_tickers_dedupes(self):
        text = _read("scanner.html")
        assert "function parseTickers" in text
        assert "seen[t]" in text

    def test_load_preset_uses_chip_el_not_global_event(self):
        text = _read("scanner.html")
        assert "function loadPreset(name, chipEl)" in text
        assert "if (chipEl) chipEl.classList.add('active')" in text
        assert "event.target" not in text

    def test_run_button_disabled_over_limit(self):
        assert "runBtn.disabled = n === 0 || n > 20" in _read("scanner.html")

    def test_error_row_rendering(self):
        text = _read("scanner.html")
        assert "consensus_signal === 'error'" in text
        assert "scanner-all-failed" in text

    def test_abort_error_timeout_i18n(self):
        text = _read("scanner.html")
        assert "_t('scanner-timeout')" in text


class TestLoop400I18nParity:
    def test_backtest_keys_parity(self, i18n_dicts):
        zh, en = i18n_dicts
        for key in BACKTEST_I18N_KEYS:
            assert key in zh and key in en

    def test_scanner_edge_keys_parity(self, i18n_dicts):
        zh, en = i18n_dicts
        for key in SCANNER_EDGE_KEYS:
            assert zh[key] and en[key]
