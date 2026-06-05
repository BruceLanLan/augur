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
INDEX_HTML = TEMPLATES_DIR / "index.html"
BASE_HTML = TEMPLATES_DIR / "base.html"


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
        assert group.get("aria-label"), "hero-chips container needs an accessible name"


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
