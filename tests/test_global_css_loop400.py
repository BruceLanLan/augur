# -*- coding: utf-8 -*-
"""Loop-400 global CSS alignment — page chrome, reading rhythm, redundant UI removal."""
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "templates"
LAYOUT_CSS = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "css" / "layout.css"

TOOL_PAGES = [
    "signals.html",
    "history.html",
    "debate.html",
    "compare.html",
    "performance.html",
    "scanner.html",
    "backtest.html",
    "watchlist.html",
    "portfolio.html",
    "stocks.html",
]


def _read(name: str) -> str:
    p = TEMPLATES_DIR / name
    assert p.is_file(), f"Missing template: {p}"
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def layout_css():
    return LAYOUT_CSS.read_text(encoding="utf-8")


class TestLayoutCssPageChrome:
    def test_layout_defines_page_title(self, layout_css):
        assert ".page-title" in layout_css
        assert ".page-lead" in layout_css or ".page-desc" in layout_css

    def test_layout_defines_section_title_compact(self, layout_css):
        assert ".section-title.compact" in layout_css
        assert ".section-title.spaced" in layout_css

    def test_layout_defines_reading_width(self, layout_css):
        assert "--prose-max" in layout_css

    def test_layout_defines_auth_panel(self, layout_css):
        assert ".auth-panel" in layout_css


class TestToolPagesUsePageChrome:
    @pytest.mark.parametrize("page", TOOL_PAGES)
    def test_no_inline_orange_h1_style(self, page):
        text = _read(page)
        assert 'h1 style="color:var(--accent-orange)' not in text

    @pytest.mark.parametrize("page", TOOL_PAGES)
    def test_has_page_title_class(self, page):
        soup = BeautifulSoup(_read(page), "html.parser")
        assert soup.find("h1", class_="page-title") is not None

    @pytest.mark.parametrize("page", TOOL_PAGES)
    def test_has_page_lead(self, page):
        soup = BeautifulSoup(_read(page), "html.parser")
        assert soup.find(class_="page-lead") is not None


class TestIndexSectionTitleCompact:
    def test_index_uses_compact_not_inline_border_reset(self):
        text = _read("index.html")
        assert "border-bottom:none; padding-bottom:0" not in text
        assert 'class="section-title compact"' in text


class TestAuthPagesUseAuthPanel:
    def test_login_uses_auth_panel(self):
        soup = BeautifulSoup(_read("login.html"), "html.parser")
        assert soup.find(class_="auth-panel") is not None

    def test_register_uses_auth_panel(self):
        soup = BeautifulSoup(_read("register.html"), "html.parser")
        assert soup.find(class_="auth-panel") is not None


class TestNoDuplicateMainLandmark:
    def test_optimizer_does_not_nest_main_role(self):
        assert 'role="main"' not in _read("optimizer.html")
