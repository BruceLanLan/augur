# -*- coding: utf-8 -*-
"""Portfolio / Compare / History / Debate UX tests — Loop 400 Agent 5.

Integration scenarios and missing-feature regression for the four
analysis-adjacent dashboard pages. Covers cross-page links, share URLs,
watchlist import, i18n hardcoded strings, a11y semantics, and loading/error UX.
"""
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


def _soup(name: str) -> BeautifulSoup:
    return BeautifulSoup(_read(name), "html.parser")


# ============================================================
# Portfolio — watchlist import & form UX
# ============================================================
class TestPortfolioWatchlistIntegration:
    def test_import_from_watchlist_function(self):
        text = _read("portfolio.html")
        assert "function importFromWatchlist()" in text
        assert "augur-watchlist" in text
        assert "portfolio-import-done" in text

    def test_url_import_watchlist_on_load(self):
        text = _read("portfolio.html")
        assert "params.get('import') === 'watchlist'" in text

    def test_empty_state_links_watchlist_with_to_param(self):
        soup = _soup("portfolio.html")
        link = soup.find("a", href="/watchlist?to=portfolio")
        assert link is not None

    def test_import_button_in_add_form(self, ):
        soup = _soup("portfolio.html")
        btn = soup.find("button", id="pf-import-btn")
        assert btn is not None
        assert btn.get("data-i18n") == "portfolio-import-btn"

    def test_enter_key_submits_holding(self):
        text = _read("portfolio.html")
        assert "e.key === 'Enter'" in text
        assert "addHolding()" in text


class TestPortfolioAnalyzeA11y:
    def test_analyze_btn_has_aria_busy(self):
        soup = _soup("portfolio.html")
        btn = soup.find("button", id="pf-analyze-btn")
        assert btn is not None
        assert btn.get("aria-busy") == "false"

    def test_remove_holding_uses_i18n_key(self):
        text = _read("portfolio.html")
        assert "portfolio-remove-holding" in text

    def test_date_label_i18n(self):
        soup = _soup("portfolio.html")
        label = soup.find("label", attrs={"for": "pf-date"})
        assert label is not None
        assert label.get("data-i18n") == "portfolio-date-label"


# ============================================================
# Compare — share URL & form validation
# ============================================================
class TestCompareShareUrlIntegration:
    def test_apply_compare_query_params(self):
        text = _read("compare.html")
        assert "function applyCompareQueryParams()" in text
        assert "params.get('ticker')" in text
        assert "params.get('agents')" in text

    def test_share_link_format(self):
        text = _read("compare.html")
        assert "/compare?ticker=" in text
        assert "agents=" in text

    def test_compare_url_loaded_toast(self):
        text = _read("compare.html")
        assert "compare-url-loaded" in text

    def test_validate_uses_compare_btn_id(self):
        text = _read("compare.html")
        assert "getElementById('compare-btn')" in text
        assert "querySelector('.btn-primary')" not in text

    def test_enter_key_runs_compare(self):
        text = _read("compare.html")
        m = re.search(r"compare-ticker.*?keydown", text, re.DOTALL)
        assert m
        assert "runCompare()" in text


class TestCompareErrorAndExport:
    def test_api_error_handling_checks_ok(self):
        text = _read("compare.html")
        assert "if (!r.ok)" in text
        assert "compare-api-error" in text

    def test_export_md_uses_i18n(self):
        text = _read("compare.html")
        assert "compare-md-signal" in text
        assert "compare-md-score" in text
        assert "compare-md-analysis" in text

    def test_spinner_has_live_region(self):
        soup = _soup("compare.html")
        spinner = soup.find(id="compare-spinner")
        assert spinner.get("role") == "status"
        assert spinner.get("aria-live") == "polite"


# ============================================================
# History — loading, i18n, cross-page detail links
# ============================================================
class TestHistoryLoadingAndEmpty:
    def test_skeleton_before_table(self):
        soup = _soup("history.html")
        assert soup.find(id="history-skeleton") is not None
        table = soup.find("table", id="history-table")
        assert table is not None
        assert "display:none" in (table.get("style") or "")

    def test_empty_state_has_compare_link(self):
        soup = _soup("history.html")
        empty = soup.find(id="empty-state")
        link = empty.find("a", href="/compare")
        assert link is not None

    def test_error_panel_with_retry(self):
        soup = _soup("history.html")
        err = soup.find(id="history-error")
        assert err is not None
        assert err.get("role") == "alert"
        assert soup.find(attrs={"data-i18n": "history-error-retry"}) is not None


class TestHistoryI18nAndLocale:
    def test_no_hardcoded_delete_confirm(self):
        text = _read("history.html")
        assert "确认删除此记录" not in text
        assert "history-delete-confirm" in text

    def test_no_hardcoded_clear_confirm(self):
        text = _read("history.html")
        assert "确认清除所有历史" not in text
        assert "history-clear-confirm" in text

    def test_locale_aware_date_formatting(self):
        text = _read("history.html")
        assert "function formatHistoryDate" in text
        assert "getCurrentLang" in text
        assert "'zh-CN'" not in text or "_historyLocale()" in text

    def test_page_indicator_uses_t(self):
        text = _read("history.html")
        assert "history-page-indicator" in text


class TestHistoryCrossPageDetail:
    def test_detail_links_to_stocks_compare_debate(self):
        text = _read("history.html")
        assert "/stocks?ticker=" in text
        assert "report=1" in text
        assert "/compare?ticker=" in text
        assert "/debate?ticker=" in text
        assert "history-view-report" in text
        assert "history-debate-link" in text


# ============================================================
# Debate — URL params, a11y, error handling
# ============================================================
class TestDebateIntegration:
    def test_apply_debate_query_params(self):
        text = _read("debate.html")
        assert "function applyDebateQueryParams()" in text

    def test_empty_state_links_compare(self):
        soup = _soup("debate.html")
        link = soup.find("a", href="/compare")
        assert link is not None

    def test_spinner_aria_busy(self):
        soup = _soup("debate.html")
        spinner = soup.find(id="debate-spinner")
        assert spinner.get("aria-busy") == "true"

    def test_debate_api_error_handling(self):
        text = _read("debate.html")
        assert "debate-api-error" in text
        assert "if (!r.ok)" in text

    def test_enter_key_starts_debate(self):
        text = _read("debate.html")
        assert "startDebate()" in text


class TestDebateAgentCounter:
    def test_agent_counter_element(self):
        soup = _soup("debate.html")
        counter = soup.find(id="debate-select-count")
        assert counter is not None
        assert "agent-counter" in (counter.get("class") or [])

    def test_debate_card_class_in_css_or_thread(self):
        text = _read("debate.html")
        assert "debate-card" in text


# ============================================================
# i18n parity for new keys (zh + en)
# ============================================================
class TestPcohI18nParity:
    NEW_KEYS = [
        "history-load-failed",
        "history-delete-confirm",
        "history-deleted",
        "history-clear-confirm",
        "history-cleared",
        "history-delete-btn",
        "history-detail-agents",
        "history-view-report",
        "history-debate-link",
        "history-error-title",
        "history-error-retry",
        "portfolio-date-label",
        "portfolio-remove-holding",
        "portfolio-import-done",
        "portfolio-import-empty",
        "portfolio-import-btn",
        "compare-url-loaded",
        "compare-api-error",
        "compare-md-signal",
        "debate-api-error",
        "debate-url-loaded",
    ]

    @pytest.fixture(scope="module")
    def i18n_text(self):
        return I18N_JS.read_text(encoding="utf-8")

    @pytest.mark.parametrize("key", NEW_KEYS)
    def test_key_in_zh_and_en(self, i18n_text, key):
        zh_block = i18n_text.split("en:")[0]
        en_block = i18n_text.split("en:", 1)[1]
        assert f'"{key}":' in zh_block, f"missing zh key {key}"
        assert f'"{key}":' in en_block, f"missing en key {key}"
