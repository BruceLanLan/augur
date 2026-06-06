# -*- coding: utf-8 -*-
"""Home dashboard (index.html) UX tests — Agent 3/10 loop-200-review.

First-time investor POV: run AAPL analysis without confusion.
Covers hero analyze flow, onboarding, market panels, loading/errors.
"""
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "templates"
INDEX_HTML = TEMPLATES_DIR / "index.html"
BASE_HTML = TEMPLATES_DIR / "base.html"


def _read(name: str) -> str:
    p = TEMPLATES_DIR / name
    assert p.is_file(), f"Missing template: {p}"
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def index_text():
    return _read("index.html")


@pytest.fixture(scope="module")
def index_soup():
    return BeautifulSoup(_read("index.html"), "html.parser")


class TestHeroSectionIdentity:
    """Hero must be scroll-targetable after tryExample (was broken selector)."""

    def test_hero_has_section_class_and_id(self, index_soup):
        hero = index_soup.find("section", id="hero-section")
        assert hero is not None
        classes = hero.get("class") or []
        assert "hero-section" in classes

    def test_try_example_scrolls_to_hero_section(self, index_text):
        assert "getElementById('hero-section')" in index_text or (
            "querySelector('.hero-section, .hero')" in index_text
        )


class TestOnboardingFirstRun:
    """Onboarding guides first-time users toward AAPL one-click demo."""

    def test_onboard_banner_has_region_role(self, index_soup):
        banner = index_soup.find(id="onboard-banner")
        assert banner is not None
        assert banner.get("role") == "region"

    def test_onboard_has_try_aapl_cta(self, index_soup):
        cta = index_soup.find("button", class_="onboard-cta")
        assert cta is not None
        assert "tryExample('AAPL')" in (cta.get("onclick") or "")

    def test_try_example_dismisses_onboard(self, index_text):
        m = re.search(r"function tryExample\(t\)\s*\{(.+?)\n\}", index_text, re.DOTALL)
        assert m, "tryExample() not found"
        assert "dismissOnboard()" in m.group(1)


class TestHeroExamplesHint:
    """Example chips must explain no manual financial inputs needed."""

    def test_examples_hint_present(self, index_soup):
        hint = index_soup.find(attrs={"data-i18n": "hero-examples-hint"})
        assert hint is not None

    def test_aapl_chip_recommended(self, index_soup):
        chip = index_soup.find("span", class_="chip-recommended", string="AAPL")
        assert chip is not None
        assert chip.get("role") == "button"


class TestHeroAnalyzeLoadingSemantics:
    """Loading state must be announced and button must not double-submit."""

    def test_spinner_is_live_region(self, index_soup):
        spinner = index_soup.find(id="hero-spinner")
        assert spinner is not None
        assert spinner.get("role") == "status"
        assert spinner.get("aria-live") == "polite"
        assert spinner.get("aria-busy") == "true"

    def test_analyze_btn_sets_aria_busy(self, index_text):
        assert "setAttribute('aria-busy', 'true')" in index_text
        assert "removeAttribute('aria-busy')" in index_text

    def test_hero_go_busy_guard(self, index_text):
        assert "_heroGoBusy" in index_text
        assert "if (_heroGoBusy) return" in index_text


class TestHeroResultAndErrorSemantics:
    """Result and error panels must be screen-reader friendly."""

    def test_result_is_live_region(self, index_soup):
        result = index_soup.find(id="hero-result")
        assert result is not None
        assert result.get("role") == "region"
        assert result.get("aria-live") == "polite"

    def test_result_has_data_warning_slot(self, index_soup):
        assert index_soup.find(id="hr-data-warning") is not None

    def test_error_is_alert(self, index_soup):
        err = index_soup.find(id="hero-error")
        assert err is not None
        assert err.get("role") == "alert"
        assert err.get("aria-live") == "assertive"

    def test_ticker_hint_is_alert(self, index_soup):
        hint = index_soup.find(id="hero-ticker-hint")
        assert hint is not None
        assert hint.get("role") == "alert"

    def test_hero_surfaces_data_error(self, index_text):
        assert "data.data_error" in index_text
        assert "_showHeroDataWarning" in index_text

    def test_hero_scrolls_to_result_or_error(self, index_text):
        assert "_scrollHeroPanel" in index_text
        assert "_scrollHeroPanel('hero-result')" in index_text
        assert "_scrollHeroPanel('hero-error')" in index_text


class TestMarketPanelDataErrorSurfacing:
    """Market panels must surface backend data_error hints."""

    def test_market_board_shows_data_error(self, index_text):
        assert "data.data_error" in index_text
        assert "renderMarketBoard" in index_text

    def test_hot_tickers_shows_data_error(self, index_text):
        m = re.search(r"function renderHotTickers\(data\)\s*\{(.+?)\n\}", index_text, re.DOTALL)
        assert m
        assert "data.data_error" in m.group(1)


class TestCommoditiesMoversAccessibility:
    """Secondary panels need live-region semantics."""

    def test_commodities_row_aria_live(self, index_soup):
        row = index_soup.find(id="commodities-rates-row")
        assert row is not None
        assert row.get("aria-live") == "polite"
        assert row.get("aria-busy") == "true"

    def test_movers_row_aria_live(self, index_soup):
        row = index_soup.find(id="movers-row")
        assert row is not None
        assert row.get("aria-live") == "polite"

    def test_commodities_retry_on_error(self, index_text):
        assert "loadCommodities()" in index_text
        assert "_setCommodRatesBusy" in index_text


class TestLeaderboardEmptyState:
    """Empty leaderboard should offer AAPL quick-start."""

    def test_leaderboard_empty_has_aapl_chip(self, index_soup):
        lb = index_soup.find(id="leaderboard-list")
        assert lb is not None
        chip = lb.find("span", class_="chip-recommended", string="AAPL")
        assert chip is not None


class TestCtrlEnterHeroSubmit:
    """Ctrl+Enter on home page must trigger hero analyze."""

    def test_base_ctrl_enter_clicks_hero_btn(self):
        text = _read("base.html")
        assert "hero-analyze-btn" in text
        assert "heroBtn.click()" in text


class TestMacroI18n:
    """Macro snapshot and fear/greed panels must use _t() keys, not hardcoded copy."""

    def test_macro_commentary_helper(self, index_text):
        assert "_macroCommentary" in index_text
        assert "macro-' + key + '-up" in index_text

    def test_fear_greed_uses_i18n_labels(self, index_text):
        assert "_fgLabel" in index_text
        assert "fg-extreme-greed" in index_text

    def test_macro_grid_has_i18n_aria(self, index_soup):
        grid = index_soup.find(id="macro-snapshot-grid")
        assert grid is not None
        assert grid.get("data-i18n-aria") == "a11y-macro-snapshot"

    def test_fear_greed_has_i18n_aria(self, index_soup):
        card = index_soup.find(id="fear-greed-card")
        assert card is not None
        assert card.get("data-i18n-aria") == "a11y-fear-greed"

    def test_refresh_hook_on_lang_switch(self, index_text):
        assert "_refreshIndexDynamicI18n" in index_text


class TestPersonaChips:
    """Featured persona quick chips guide first-time users to persona + AAPL demo."""

    def test_persona_chips_present(self, index_soup):
        chips = index_soup.select(".persona-chips .persona-chip")
        assert len(chips) >= 3

    def test_persona_chips_call_try_persona(self, index_soup):
        for chip in index_soup.select(".persona-chips .persona-chip"):
            assert "tryPersona(" in (chip.get("onclick") or "")

    def test_view_all_personas_i18n(self, index_soup):
        link = index_soup.find("a", href="/personas")
        assert link is not None
        assert link.get("data-i18n") == "btn-view-all-personas"

    def test_featured_style_has_i18n(self, index_text):
        assert 'data-i18n="persona-style-' in index_text

    def test_featured_rows_prefill_aapl(self, index_soup):
        row = index_soup.select(".m-row")[0]
        assert "ticker=AAPL" in (row.get("onclick") or "")


class TestIndexPerfDeferrals:
    """Below-fold panels and sparklines must defer to keep first paint fast."""

    def test_deferred_panel_loading(self, index_text):
        assert "_deferIndexLoad" in index_text
        assert "loadCryptoOverview" in index_text

    def test_sparkline_concurrency_limit(self, index_text):
        assert "_SPARKLINE_MAX" in index_text
        assert "_drainSparklineQueue" in index_text


class TestFirstTimeLeaderboardEmpty:
    """Dynamic leaderboard empty state must keep AAPL quick-start chip."""

    def test_render_leaderboard_empty_has_aapl_chip(self, index_text):
        m = re.search(r"function renderLeaderboard\(\)\s*\{(.+?)\n\}", index_text, re.DOTALL)
        assert m, "renderLeaderboard() not found"
        body = m.group(1)
        assert "chip-recommended" in body
        assert "tryExample('AAPL')" in body or 'tryExample(\\\'AAPL\\\')' in body

    def test_try_persona_dismisses_onboard(self, index_text):
        m = re.search(r"function tryPersona\(personaId\)\s*\{(.+?)\n\}", index_text, re.DOTALL)
        assert m
        assert "dismissOnboard()" in m.group(1)
        assert "ticker=AAPL" in m.group(1)
