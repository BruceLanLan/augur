# -*- coding: utf-8 -*-
"""Loop 400 Agent 1 — layout/responsive polish regression tests."""
import re
from pathlib import Path

import pytest

CSS_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "css"


def _read(name: str) -> str:
    p = CSS_DIR / name
    assert p.is_file(), f"Missing CSS file: {p}"
    return p.read_text(encoding="utf-8")


def _media_block(css: str, max_width: str) -> str:
    m = re.search(
        rf"@media\s*\(max-width:\s*{max_width}px\)\s*\{{(.+?)\}}\s*(?=@|\Z)",
        css,
        re.DOTALL,
    )
    assert m, f"Missing @media (max-width: {max_width}px) in CSS"
    return m.group(1)


class TestMobileSidebarOffCanvas:
    @pytest.fixture(scope="class")
    def layout_css(self):
        return _read("layout.css")

    def test_sidebar_fixed_at_768(self, layout_css):
        block = _media_block(layout_css, "768")
        assert re.search(
            r"\.app-layout\s+\.(?:sidebar|sb)\s*,\s*\n\s*\.app-layout\s+\.(?:sb|sidebar)\s*\{[^}]*position\s*:\s*fixed",
            block,
            re.DOTALL,
        )


class TestGridShellNoDoubleGutter:
    @pytest.fixture(scope="class")
    def bloomberg_css(self):
        return _read("bloomberg.css")

    def test_app_layout_main_margin_reset(self, bloomberg_css):
        assert re.search(
            r"\.app-layout\s+\.app-main\s*\{[^}]*margin-left\s*:\s*0\s*!important",
            bloomberg_css,
        )


class TestMobileChromeStacking:
    @pytest.fixture(scope="class")
    def enhance_css(self):
        return _read("ui-enhance.css")

    def test_hamburger_below_ticker(self, enhance_css):
        block = _media_block(enhance_css, "768")
        assert re.search(
            r"\.hamburger-btn\s*\{[^}]*top\s*:\s*calc\([^)]*ticker-tape-height",
            block,
        )

    def test_toast_below_ticker(self, enhance_css):
        block = _media_block(enhance_css, "768")
        assert re.search(
            r"#toast-container\s*\{[^}]*top\s*:\s*calc\([^)]*ticker-tape-height",
            block,
        )


class TestHeroFormMobileStack:
    @pytest.fixture(scope="class")
    def layout_css(self):
        return _read("layout.css")

    def test_hero_input_column_at_600(self, layout_css):
        block = _media_block(layout_css, "600")
        assert re.search(
            r"\.hero-input\s*\{[^}]*flex-direction\s*:\s*column",
            block,
        )

    def test_hero_chips_wrap(self, layout_css):
        assert re.search(
            r"\.hero-chips\s*\{[^}]*flex-wrap\s*:\s*wrap",
            layout_css,
        )


class TestSafeAreaInsets:
    @pytest.fixture(scope="class")
    def bloomberg_css(self):
        return _read("bloomberg.css")

    def test_bottom_nav_safe_area(self, bloomberg_css):
        assert "safe-area-inset-bottom" in bloomberg_css

    def test_app_main_bottom_safe_area(self, bloomberg_css):
        assert re.search(
            r"\.app-main\s*\{[^}]*padding-bottom\s*:\s*calc\([^)]*safe-area-inset-bottom",
            bloomberg_css,
        )
