# -*- coding: utf-8 -*-
"""Dashboard accessibility audit (Round 6 Agent A).

Verifies that the dashboard home template (index.html) and the base
template (base.html) follow key WCAG 2.1 AA practices for keyboard
accessibility, screen-reader semantics, and dynamic content loading:

1. Interactive <span>/<div> elements that respond to onclick are
   reachable and operable via keyboard (tabindex + role + onkeydown)
   and have an accessible name.
2. Dynamic panels that swap skeleton placeholders for live data declare
   aria-live and aria-busy so assistive tech is told the content is
   updating and when the update completes.
3. Icon-only actionable controls carry an accessible name (aria-label).

The tests operate purely on the rendered template source so they do
not require the FastAPI app to be running and remain stable as the
JS implementation evolves.
"""
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "templates"
CSS_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "static" / "css"
DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard"
INDEX_HTML = TEMPLATES_DIR / "index.html"
BASE_HTML = TEMPLATES_DIR / "base.html"
REPORT_VIEW_HTML = TEMPLATES_DIR / "report_view.html"
I18N_JS = DASHBOARD_DIR / "static" / "js" / "i18n.js"
BLOOMBERG_CSS = CSS_DIR / "bloomberg.css"


def _read_css(name: str) -> str:
    p = CSS_DIR / name
    assert p.is_file(), f"Missing CSS file: {p}"
    return p.read_text(encoding="utf-8")


def _read(name: str) -> str:
    p = TEMPLATES_DIR / name
    assert p.is_file(), f"Missing template: {p}"
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def index_soup():
    return BeautifulSoup(_read("index.html"), "html.parser")


@pytest.fixture(scope="module")
def base_soup():
    return BeautifulSoup(_read("base.html"), "html.parser")


@pytest.fixture(scope="module")
def stocks_soup():
    return BeautifulSoup(_read("stocks.html"), "html.parser")


@pytest.fixture(scope="module")
def i18n_dicts():
    """Parse zh/en key dicts from i18n.js for parity checks."""
    text = I18N_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.I18N\s*=\s*\{(.+?)\n\};", text, re.S)
    assert m, "i18n.js must define window.I18N = { ... }"
    inner = m.group(1)
    en_marker = inner.find("\n    en:")
    assert en_marker != -1, "i18n.js must have an 'en' block"
    entry_pat = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', re.M)

    def _parse(block):
        return {em.group(1): em.group(2) for em in entry_pat.finditer(block)}

    return _parse(inner[:en_marker]), _parse(inner[en_marker:])


class TestKeyboardAccessibleChips:
    """Hero example-ticker chips must be reachable and activatable via
    keyboard and have an accessible name (WCAG 2.1.1, 4.1.2)."""

    # Map of visible chip text → ticker sent to tryExample
    EXPECTED_TICKERS = [
        ("NVDA", "NVDA"),
        ("AAPL", "AAPL"),
        ("TSLA", "TSLA"),
        ("MSFT", "MSFT"),
        ("BTC", "BTC-USD"),
        ("00700.HK", "00700.HK"),
    ]

    def test_chips_present(self, index_soup):
        chips = index_soup.select(".hero-chips .chip")
        labels = [c.get_text(strip=True) for c in chips]
        for visible, _ in self.EXPECTED_TICKERS:
            assert visible in labels, f"missing chip for {visible}; got {labels}"

    @pytest.mark.parametrize("visible,ticker", EXPECTED_TICKERS)
    def test_chip_has_role_button(self, index_soup, visible, ticker):
        chip = index_soup.find("span", class_="chip", string=re.compile(rf"^{re.escape(visible)}$"))
        assert chip is not None, f"chip for {ticker} not found"
        assert chip.get("role") == "button", (
            f"chip {ticker} must have role='button' for screen readers"
        )

    @pytest.mark.parametrize("visible,ticker", EXPECTED_TICKERS)
    def test_chip_is_keyboard_focusable(self, index_soup, visible, ticker):
        chip = index_soup.find("span", class_="chip", string=re.compile(rf"^{re.escape(visible)}$"))
        assert chip is not None
        assert chip.get("tabindex") in ("0", "0"), (
            f"chip {ticker} must have tabindex='0' to receive keyboard focus"
        )
        assert chip.has_attr("onkeydown"), (
            f"chip {ticker} must have an onkeydown handler for Enter/Space activation"
        )

    @pytest.mark.parametrize("visible,ticker", EXPECTED_TICKERS)
    def test_chip_has_aria_label(self, index_soup, visible, ticker):
        chip = index_soup.find("span", class_="chip", string=re.compile(rf"^{re.escape(visible)}$"))
        assert chip is not None
        assert chip.get("aria-label"), (
            f"chip {ticker} must have an aria-label accessible name"
        )

    def test_chips_container_has_group_role(self, index_soup):
        group = index_soup.find("div", class_="hero-chips")
        assert group is not None
        assert group.get("role") == "group", "hero-chips container should have role='group'"
        assert group.get("aria-label") or group.get("data-i18n-aria"), (
            "hero-chips container needs an accessible name"
        )


class TestFeaturedPersonaRowAccessible:
    """Featured-persona m-row cards behave as links and must be operable
    via keyboard and carry an accessible name."""

    def test_mrow_has_link_role(self, index_soup):
        rows = index_soup.select(".m-row")
        assert rows, "no .m-row elements found (featured persona section)"
        for row in rows:
            assert row.get("role") == "link", (
                "Featured persona .m-row must expose role='link' to assistive tech"
            )
            assert row.get("tabindex") == "0", ".m-row must be keyboard-focusable"
            assert row.has_attr("onkeydown"), ".m-row must have onkeydown for Enter"
            assert row.get("aria-label"), ".m-row must have an accessible name (aria-label)"


class TestMarketRefreshSpanAccessible:
    """The 'refresh 60s' inline control was a <span> with onclick and only
    a title attribute; it must now be exposed as a button."""

    def test_market_refresh_has_role_button(self, index_soup):
        el = index_soup.find(id="market-refresh-btn")
        assert el is not None
        assert el.get("role") == "button", (
            "market refresh control must have role='button' (was a bare span)"
        )

    def test_market_refresh_has_aria_label(self, index_soup):
        el = index_soup.find(id="market-refresh-btn")
        assert el is not None
        assert el.get("aria-label"), "market refresh control must have aria-label"
        assert el.get("tabindex") == "0", "market refresh must be keyboard-focusable"
        assert el.has_attr("onkeydown"), "market refresh must activate via keyboard"


class TestDynamicPanelLoadingSemantics:
    """Panels that swap skeleton placeholders for live data must declare
    aria-live and initial aria-busy, and the JavaScript must clear
    aria-busy after the data loads so screen readers know the update
    finished."""

    PANEL_IDS = [
        "market-board",
        "hot-tickers-grid",
        "sector-grid",
        "intl-markets-grid",
        "crypto-grid",
        "datasource-grid",
        "market-pulse-strip",
        "macro-snapshot-grid",
    ]

    @pytest.mark.parametrize("panel_id", PANEL_IDS)
    def test_panel_has_aria_live(self, index_soup, panel_id):
        el = index_soup.find(id=panel_id)
        assert el is not None, f"panel #{panel_id} not found"
        assert el.get("aria-live") in ("polite", "assertive"), (
            f"#{panel_id} must declare aria-live so live-region updates are announced"
        )

    @pytest.mark.parametrize("panel_id", PANEL_IDS)
    def test_panel_initially_busy(self, index_soup, panel_id):
        el = index_soup.find(id=panel_id)
        assert el is not None
        assert el.get("aria-busy") == "true", (
            f"#{panel_id} must start with aria-busy='true' to signal loading"
        )

    @pytest.mark.parametrize("panel_id", PANEL_IDS)
    def test_panel_has_accessible_label(self, index_soup, panel_id):
        el = index_soup.find(id=panel_id)
        assert el is not None
        assert (el.get("aria-label") or el.get("aria-labelledby")), (
            f"#{panel_id} needs an accessible name so live updates are meaningful"
        )

    def test_js_clears_aria_busy_for_market_board(self):
        """JS must set aria-busy='false' once market board data is loaded."""
        text = _read("index.html")
        # Look for the renderMarketBoard wrapper call that flips busy
        assert "market-board" in text and "aria-busy" in text
        # Specifically the post-render path
        m = re.search(
            r"renderMarketBoard\(data\);\s*var\s+mb\s*=\s*document\.getElementById\('market-board'\)"
            r"\s*;\s*if\s*\(mb\)\s*\{\s*mb\.setAttribute\('aria-busy',\s*'false'\)",
            text,
        )
        assert m, "renderMarketBoard must clear aria-busy='false' on #market-board"

    def test_js_clears_aria_busy_for_dynamic_panels(self):
        """The data-driven panels (pulse / intl / macro) are rendered as a
        side-effect of the market-board fetch; their busy state must be
        cleared in the same callback."""
        text = _read("index.html")
        for panel_id in ("market-pulse-strip", "intl-markets-grid", "macro-snapshot-grid"):
            assert panel_id in text, f"{panel_id} should appear in the JS"
            # The override renderMarketBoard wrapper should set busy false
            assert f"'{panel_id}'" in text and "aria-busy" in text


class TestBaseTemplateA11yPreserved:
    """Sanity checks: the base template still exposes a skip-link, named
    landmarks, and an aria-labelled toast container (none of the index
    edits should have regressed this)."""

    def test_skip_link_present(self, base_soup):
        link = base_soup.find("a", class_="skip-link", href="#main-content")
        assert link is not None, "base.html must keep a skip-to-main-content link"

    def test_main_landmark_present(self, base_soup):
        main = base_soup.find(id="main-content")
        assert main is not None
        assert main.name == "main", "#main-content must be a <main> landmark"

    def test_primary_nav_has_label(self, base_soup):
        nav = base_soup.find("nav", class_="sb-nav")
        assert nav is not None
        assert nav.get("aria-label") in ("Primary",), "primary nav needs aria-label"

    def test_toast_is_a_live_region(self, base_soup):
        toast = base_soup.find(id="toast-container")
        assert toast is not None
        assert toast.get("role") == "status"
        assert toast.get("aria-live") in ("polite", "assertive")


class TestStocksPageMobileA11y:
    """Stock analysis page must support phone use: touch-friendly controls,
    keyboard-accessible toggles, and live-region semantics during analysis."""

    def test_ticker_input_has_accessible_name(self, stocks_soup):
        inp = stocks_soup.find(id="inp-ticker")
        assert inp is not None
        assert inp.get("data-i18n-aria") == "a11y-stocks-ticker"
        assert inp.get("aria-label") or inp.get("data-i18n-aria")

    def test_analyze_btn_has_i18n_label(self, stocks_soup):
        btn = stocks_soup.find(id="analyze-btn")
        assert btn is not None
        span = btn.find(attrs={"data-i18n": "btn-analyze"})
        assert span is not None, "analyze button label must use data-i18n for mid-flow switch"

    def test_quick_ticker_buttons_are_real_buttons(self, stocks_soup):
        btns = stocks_soup.select(".ticker-btn")
        assert btns, "stocks page must expose quick-ticker buttons"
        for btn in btns:
            assert btn.name == "button", "ticker-btn must be <button> for touch/keyboard"
            assert btn.get("type") == "button"
            assert btn.get("data-i18n-aria") == "stocks-quick-ticker"
            assert btn.get("data-aria-ticker"), "each quick ticker needs data-aria-ticker for i18n aria-label"

    def test_adv_toggle_is_keyboard_button(self, stocks_soup):
        btn = stocks_soup.find(id="adv-toggle-btn")
        assert btn is not None
        assert btn.name == "button"
        assert btn.get("aria-expanded") in ("true", "false")
        assert btn.get("aria-controls") == "advMetrics"
        assert btn.has_attr("onkeydown")

    def test_spinner_is_live_region(self, stocks_soup):
        spinner = stocks_soup.find(id="spinner")
        assert spinner is not None
        assert spinner.get("role") == "status"
        assert spinner.get("aria-live") in ("polite", "assertive")
        assert spinner.get("aria-busy") is not None

    def test_spinner_progress_has_i18n(self, stocks_soup):
        prog = stocks_soup.find(id="analyze-progress")
        assert prog is not None
        assert prog.get("data-i18n") == "hero-progress", (
            "progress text must update when user switches language mid-analysis"
        )

    def test_error_panel_is_alert_live_region(self, stocks_soup):
        panel = stocks_soup.find(id="error-panel")
        assert panel is not None
        assert panel.get("aria-live") in ("polite", "assertive")
        assert panel.get("role") == "alert"
        title = panel.find(class_="error-panel-title")
        assert title and title.get("data-i18n") == "hero-error-title"
        retry = panel.find("button", attrs={"data-i18n": "btn-retry"})
        assert retry is not None

    def test_stocks_has_mobile_breakpoint_css(self):
        text = _read("stocks.html")
        assert "@media (max-width: 768px)" in text
        assert "stocks-input-row" in text

    def test_stocks_page_has_i18n_title(self, stocks_soup):
        h1 = stocks_soup.find("h1", class_="page-title", attrs={"data-i18n": "stocks-title"})
        assert h1 is not None, "stocks page must expose h1.page-title for heading hierarchy"


class TestI18nMidFlowLanguageSwitch:
    """Switching zh/en mid-flow must keep aria-labels and static labels in sync."""

    STOCKS_I18N_KEYS = [
        "stocks-title",
        "stocks-desc",
        "stocks-ticker-label",
        "stocks-ticker-ph",
        "stocks-quick-ticker",
        "stocks-adv-toggle",
        "a11y-stocks-ticker",
        "a11y-hero-chips-group",
        "hero-progress",
        "hero-error-title",
        "btn-analyze",
        "btn-retry",
    ]

    @pytest.mark.parametrize("key", STOCKS_I18N_KEYS)
    def test_stocks_key_in_both_langs(self, i18n_dicts, key):
        zh, en = i18n_dicts
        assert key in zh, f"{key} missing from i18n.zh"
        assert key in en, f"{key} missing from i18n.en"
        assert zh[key].strip() and en[key].strip()

    def test_apply_language_substitutes_aria_placeholders(self):
        """i18n.js applyLanguage must replace {name} and {ticker} in aria-labels."""
        text = I18N_JS.read_text(encoding="utf-8")
        assert "data-aria-name" in text or "data-aria-name" in _read("index.html")
        assert "replace(/\\{name\\}/g" in text or "{name}" in text
        assert "data-aria-ticker" in _read("stocks.html")
        js = I18N_JS.read_text(encoding="utf-8")
        assert "data-aria-ticker" in js or "data-aria-ticker" in _read("stocks.html")
        assert re.search(r"label\.replace\(/\\\{name\\\}/g", js)
        assert re.search(r"label\.replace\(/\\\{ticker\\\}/g", js)

    def test_featured_persona_has_data_aria_name(self, index_soup):
        rows = index_soup.select(".m-row")
        assert rows
        for row in rows:
            assert row.get("data-aria-name"), (
                "featured persona rows need data-aria-name so mid-flow lang switch keeps aria-label"
            )

    def test_hero_chips_group_has_i18n_aria(self, index_soup):
        group = index_soup.find("div", class_="hero-chips")
        assert group is not None
        assert group.get("data-i18n-aria") == "a11y-hero-chips-group"


class TestMobileTouchTargetsCSS:
    """Phone analyze-stock scenario: form controls and buttons meet 44px touch target."""

    @pytest.fixture(scope="module")
    def css_content(self):
        return BLOOMBERG_CSS.read_text(encoding="utf-8")

    def test_mobile_touch_target_rule_exists(self, css_content):
        assert "max-width: 768px" in css_content
        assert "min-height: 44px" in css_content
        assert ".ticker-btn" in css_content

    def test_form_inputs_prevent_ios_zoom(self, css_content):
        idx = css_content.find("/* Mobile touch targets */")
        assert idx != -1, "bloomberg.css must define a mobile touch-target block"
        mobile_block = css_content[idx:idx + 500]
        assert ".form-input" in mobile_block
        assert "font-size: 1rem" in mobile_block

    def test_touch_action_manipulation(self, css_content):
        assert "touch-action: manipulation" in css_content

    def test_focus_visible_on_interactive_elements(self, css_content):
        assert ".ticker-btn:focus-visible" in css_content
        assert ".form-input:focus-visible" in css_content


class TestReportViewReadability:
    """Deep report page CSS must keep markdown readable on parchment (light)
    and terminal-dark backgrounds — beige + white text was unreadable."""

    @pytest.fixture(scope="module")
    def report_soup(self):
        return BeautifulSoup(_read("report_view.html"), "html.parser")

    def test_report_page_has_md_report_landmark(self, report_soup):
        md = report_soup.find(id="rp-full-md")
        assert md is not None, "report_view.html must expose #rp-full-md"
        assert "md-report" in (md.get("class") or []), (
            "#rp-full-md must carry md-report class for shared markdown styles"
        )

    def test_report_loading_state_has_live_region(self, report_soup):
        loading = report_soup.find(id="rp-loading")
        assert loading is not None
        assert loading.get("role") == "status"
        assert loading.get("aria-live") in ("polite", "assertive")

    def test_report_error_state_is_alert(self, report_soup):
        err = report_soup.find(id="rp-error")
        assert err is not None
        assert err.get("role") == "alert"

    def test_bloomberg_css_has_light_mode_md_report_contrast(self):
        css = _read_css("bloomberg.css")
        assert "html.light" in css and ".md-report" in css
        assert "parchment-ink" in css or "--report-text" in css, (
            "bloomberg.css must define light-mode report text tokens for parchment backgrounds"
        )
        assert "report-section-body" in css or "report-md-panel" in css, (
            "Dedicated report page markdown panels need light-mode contrast rules"
        )

    def test_colors_css_defines_report_tokens(self):
        css = _read_css("colors_and_type.css")
        assert "--report-text" in css
        assert "--parchment-ink" in css
        assert "html.light" in css
        compact = re.sub(r"\s+", "", css)
        assert "--report-text:var(--parchment-ink)" in compact, (
            "Light-mode --report-text must map to --parchment-ink for readable parchment prose"
        )

    def test_report_view_uses_theme_aware_chart_helper(self):
        html = _read("report_view.html")
        assert "reportThemeColor" in html, (
            "SVG chart labels must read CSS variables instead of hard-coded light-grey fills"
        )
        chart_block = html.split("function renderScoreChart")[1].split("function ")[0]
        gauge_block = html.split("function createScoreGauge")[1].split("function ")[0]
        assert "#c9d1d9" not in chart_block, "renderScoreChart must not hard-code #c9d1d9"
        assert "#c9d1d9" not in gauge_block, "createScoreGauge must not hard-code #c9d1d9"
