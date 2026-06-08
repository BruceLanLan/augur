# -*- coding: utf-8 -*-
"""Loop-400 a11y / i18n / mobile gap tests — 20-loop backlog from LOOP_200."""
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "templates"
DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard"
I18N_JS = DASHBOARD_DIR / "static" / "js" / "i18n.js"


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
    entry_pat = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', re.M)

    def _parse(block):
        return {em.group(1): em.group(2) for em in entry_pat.finditer(block)}

    return _parse(inner[:en_marker]), _parse(inner[en_marker:])


@pytest.fixture(scope="module")
def backtest_soup():
    return BeautifulSoup(_read("backtest.html"), "html.parser")


@pytest.fixture(scope="module")
def backtest_text():
    return _read("backtest.html")


@pytest.fixture(scope="module")
def base_soup():
    return BeautifulSoup(_read("base.html"), "html.parser")


@pytest.fixture(scope="module")
def stocks_text():
    return _read("stocks.html")


BACKTEST_I18N_KEYS = [
    "backtest-title", "backtest-desc", "backtest-ticker-label", "backtest-ticker-empty",
    "backtest-ticker-invalid", "backtest-capital-label", "backtest-capital-hint",
    "backtest-strategy-label", "backtest-strategy-equal", "backtest-strategy-kelly",
    "backtest-strategy-fixed", "backtest-days-label", "backtest-run", "backtest-running",
    "backtest-loading", "backtest-empty-title", "backtest-empty-desc",
    "backtest-error-title", "backtest-error-default", "backtest-error-failed",
    "backtest-error-timeout", "backtest-error-request",
    "a11y-backtest-loading", "a11y-backtest-metrics", "a11y-backtest-banner",
    "a11y-backtest-leaderboard", "a11y-backtest-timeline",
    "backtest-metric-annualized", "backtest-metric-drawdown", "backtest-metric-sharpe",
    "backtest-metric-winrate", "backtest-leaderboard-title", "backtest-col-hitrate",
    "backtest-lb-empty-title", "backtest-timeline-title", "backtest-col-date",
]


@pytest.mark.parametrize("key", BACKTEST_I18N_KEYS)
def test_backtest_key_in_both_langs(i18n_dicts, key):
    zh, en = i18n_dicts
    assert key in zh, f"{key} missing from zh"
    assert key in en, f"{key} missing from en"
    assert zh[key].strip() and en[key].strip()


class TestBacktestTemplateI18n:
    def test_title_has_data_i18n(self, backtest_soup):
        assert backtest_soup.find("h1", attrs={"data-i18n": "backtest-title"}) is not None

    def test_run_btn_label_i18n(self, backtest_soup):
        btn = backtest_soup.find(id="bt-run-btn")
        assert btn is not None
        assert btn.find(attrs={"data-i18n": "backtest-run"}) is not None

    def test_strategy_options_i18n(self, backtest_soup):
        assert len(backtest_soup.select("#bt-strategy option[data-i18n]")) == 3

    def test_metric_cards_bilingual(self, backtest_soup):
        for key in ("backtest-metric-annualized", "backtest-metric-drawdown",
                    "backtest-metric-sharpe", "backtest-metric-winrate"):
            assert backtest_soup.find(attrs={"data-i18n": key}) is not None
            assert backtest_soup.find(attrs={"data-i18n": key + "-sub"}) is not None

    def test_js_uses_t_helper(self, backtest_text):
        assert "function _t(key, fb)" in backtest_text
        assert "_t('backtest-ticker-empty')" in backtest_text
        assert "_t('backtest-error-timeout')" in backtest_text
        assert "_setRunBtnBusy" in backtest_text


class TestBacktestMobile:
    def test_mobile_breakpoint_css(self, backtest_text):
        assert "@media (max-width: 768px)" in backtest_text
        assert "min-height: 44px" in backtest_text
        assert "bt-form-row" in backtest_text

    def test_table_scroll_hints(self, backtest_soup):
        assert len(backtest_soup.find_all(attrs={"data-i18n": "table-scroll-hint"})) >= 2

    def test_table_captions_for_screen_readers(self, backtest_soup):
        assert len(backtest_soup.find_all("caption", class_="sr-only")) >= 2


class TestBacktestA11y:
    def test_loading_is_status_region(self, backtest_soup):
        el = backtest_soup.find(id="bt-loading")
        assert el.get("role") == "status"
        assert el.get("aria-live") == "polite"
        assert el.get("data-i18n-aria") == "a11y-backtest-loading"

    def test_error_is_alert(self, backtest_soup):
        el = backtest_soup.find(id="bt-error")
        assert el.get("role") == "alert"
        assert el.get("aria-live") == "assertive"

    def test_days_group_has_aria(self, backtest_soup):
        grp = backtest_soup.find(id="bt-days-group")
        assert grp.get("role") == "group"
        assert grp.get("data-i18n-aria") == "a11y-backtest-days-group"

    def test_capital_hint_is_alert(self, backtest_soup):
        assert backtest_soup.find(id="bt-capital-hint").get("role") == "alert"


META_I18N_KEYS = [
    "meta-og-title", "meta-og-desc", "meta-twitter-title", "meta-twitter-desc",
]


@pytest.mark.parametrize("key", META_I18N_KEYS)
def test_meta_key_in_both_langs(i18n_dicts, key):
    zh, en = i18n_dicts
    assert key in zh and key in en


class TestBaseMetaI18n:
    def test_og_tags_have_data_i18n_meta(self, base_soup):
        for prop in ("og:title", "og:description"):
            assert base_soup.find("meta", attrs={"property": prop, "data-i18n-meta": True})

    def test_twitter_tags_have_data_i18n_meta(self, base_soup):
        for name in ("twitter:title", "twitter:description"):
            assert base_soup.find("meta", attrs={"name": name, "data-i18n-meta": True})

    def test_apply_language_updates_meta(self):
        js = I18N_JS.read_text(encoding="utf-8")
        assert "data-i18n-meta" in js
        assert "setAttribute('content'" in js

    def test_og_image_switches_by_lang(self):
        js = I18N_JS.read_text(encoding="utf-8")
        assert "data-i18n-lang-img" in js
        assert "hero-banner-en.svg" in js


TICKER_I18N_KEYS = [
    "ticker-loading", "a11y-ticker-tape", "a11y-ticker-pause",
    "a11y-ticker-resume", "ticker-pause-title",
]


@pytest.mark.parametrize("key", TICKER_I18N_KEYS)
def test_ticker_key_in_both_langs(i18n_dicts, key):
    zh, en = i18n_dicts
    assert key in zh and key in en


class TestTickerTapeA11y:
    def test_tape_wrap_has_i18n_aria(self, base_soup):
        assert base_soup.find(id="ticker-tape-wrap").get("data-i18n-aria") == "a11y-ticker-tape"

    def test_pause_btn_is_button_with_i18n(self, base_soup):
        btn = base_soup.find(id="ticker-tape-pause")
        assert btn.name == "button"
        assert btn.get("type") == "button"
        assert btn.get("data-i18n-aria") == "a11y-ticker-pause"

    def test_loading_span_has_i18n(self, base_soup):
        assert base_soup.find(class_="ticker-tape-loading").get("data-i18n") == "ticker-loading"

    def test_pause_js_uses_t_helper(self):
        text = _read("base.html")
        assert "window.t(resumeKey)" in text or "window.t(pauseKey)" in text


STYLE_KEYS = [
    "style-value-investing", "style-deep-value", "style-growth", "style-disruptive",
    "style-macro", "style-all-weather", "style-contrarian", "style-growth-value",
    "style-activist", "style-integrity-value", "style-value-growth", "style-long-term",
    "style-trend", "style-monopoly", "style-ai-supercycle", "style-technical",
    "style-quant-neutral",
]


@pytest.mark.parametrize("key", STYLE_KEYS)
def test_persona_style_key_in_both_langs(i18n_dicts, key):
    zh, en = i18n_dicts
    assert key in zh and key in en


class TestStocksPersonaStyleI18n:
    def test_agent_style_map_uses_i18n_keys(self, stocks_text):
        assert "buffett: 'style-value-investing'" in stocks_text
        block = stocks_text.split("AGENT_STYLE_MAP")[1].split("};")[0]
        assert "价值投资'" not in block

    def test_build_score_cards_uses_t(self, stocks_text):
        assert "window.t(styleKey)" in stocks_text


STOCKS_HISTORY_KEYS = [
    "stocks-history-title", "stocks-history-desc", "stocks-history-col-date",
    "stocks-history-col-score", "stocks-history-col-signal", "stocks-history-col-price",
    "stocks-history-empty",
]


@pytest.mark.parametrize("key", STOCKS_HISTORY_KEYS)
def test_stocks_history_key_in_both_langs(i18n_dicts, key):
    zh, en = i18n_dicts
    assert key in zh and key in en


class TestStocksHistoryPanel:
    def test_history_panel_has_i18n(self, stocks_text):
        assert 'data-i18n="stocks-history-title"' in stocks_text
        assert 'data-i18n="stocks-history-empty"' in stocks_text

    def test_history_table_has_scroll_hint(self, stocks_text):
        idx = stocks_text.find("history-comparison")
        assert "table-scroll-hint" in stocks_text[idx:idx + 2000]

    def test_history_panel_is_live_region(self, stocks_text):
        assert 'aria-live="polite"' in stocks_text


def test_zh_en_key_parity_within_5(i18n_dicts):
    zh, en = i18n_dicts
    only_zh = set(zh) - set(en)
    only_en = set(en) - set(zh)
    assert len(only_zh) <= 5, f"zh-only keys: {sorted(only_zh)[:10]}"
    assert len(only_en) <= 5, f"en-only keys: {sorted(only_en)[:10]}"
