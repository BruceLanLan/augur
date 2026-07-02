# -*- coding: utf-8 -*-
"""Dashboard CSS responsive/contrast audit (Round 15 Agent D).

Verifies three accessibility/responsive fixes landed in v8.2.0:

1. Light-mode ``--fg-3`` token meets WCAG AA 4.5:1 against the
   ``--bg-void`` (terminal canvas) and ``--bg-card`` backgrounds.
2. The ``@media (prefers-reduced-motion: reduce)`` block in
   ``ui-enhance.css`` now also covers the animations defined in
   ``augur.css`` (chevBounce, dotPulse) and ``layout.css`` (owlBob).
3. ``.hero-owl`` is hidden on the smallest breakpoint and shrunk
   below 1100px so it stops overlapping hero copy on narrow viewports.
"""
import re
from pathlib import Path

import pytest

CSS_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static" / "css"


def _read(name: str) -> str:
    p = CSS_DIR / name
    assert p.is_file(), f"Missing CSS file: {p}"
    return p.read_text(encoding="utf-8")


def _hex_to_rgb(hex_str: str):
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _luminance(rgb):
    def chan(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast_ratio(c1: str, c2: str) -> float:
    L1, L2 = _luminance(_hex_to_rgb(c1)), _luminance(_hex_to_rgb(c2))
    if L1 < L2:
        L1, L2 = L2, L1
    return (L1 + 0.05) / (L2 + 0.05)


def _extract_var(css_text: str, var_name: str, scope: str = r":root\.light,\s*html\.light") -> str:
    """Return the hex value assigned to ``var_name`` within the given scope block."""
    pattern = re.compile(
        scope + r"\s*\{([^}]+)\}", re.DOTALL,
    )
    match = pattern.search(css_text)
    assert match, f"Scope block not found: {scope!r}"
    block = match.group(1)
    var_pattern = re.compile(rf"--{re.escape(var_name)}\s*:\s*(#[0-9a-fA-F]{{3,8}})")
    m = var_pattern.search(block)
    assert m, f"Variable --{var_name} not found in scope {scope!r}"
    return m.group(1).lower()


# ---------------------------------------------------------------------------
# 1) Light-mode contrast
# ---------------------------------------------------------------------------

class TestLightModeFg3Contrast:
    """Light-mode ``--fg-3`` is used for muted/labels; must hit 4.5:1."""

    @pytest.fixture(scope="class")
    def light_block(self):
        return _read("colors_and_type.css")

    def test_fg3_against_bg_void_passes_wcag_aa(self, light_block):
        fg3 = _extract_var(light_block, "fg-3", r":root\.light,\s*html\.light")
        bg_void = _extract_var(light_block, "bg-void", r":root\.light,\s*html\.light")
        ratio = _contrast_ratio(fg3, bg_void)
        assert ratio >= 4.5, (
            f"Light --fg-3 ({fg3}) on --bg-void ({bg_void}) = {ratio:.2f}:1, "
            f"must be >= 4.5:1 (WCAG AA normal text)"
        )

    def test_fg3_against_bg_card_passes_wcag_aa(self, light_block):
        fg3 = _extract_var(light_block, "fg-3", r":root\.light,\s*html\.light")
        bg_card = _extract_var(light_block, "bg-card", r":root\.light,\s*html\.light")
        ratio = _contrast_ratio(fg3, bg_card)
        assert ratio >= 4.5, (
            f"Light --fg-3 ({fg3}) on --bg-card ({bg_card}) = {ratio:.2f}:1, "
            f"must be >= 4.5:1 (WCAG AA normal text)"
        )


# ---------------------------------------------------------------------------
# 2) prefers-reduced-motion coverage
# ---------------------------------------------------------------------------

class TestReducedMotionCoverage:
    """The reduced-motion media query must suppress all infinite animations."""

    @pytest.fixture(scope="class")
    def enhance_css(self):
        return _read("ui-enhance.css")

    def test_reduced_motion_block_present(self, enhance_css):
        assert "@media (prefers-reduced-motion: reduce)" in enhance_css, (
            "ui-enhance.css must declare a prefers-reduced-motion block"
        )

    @pytest.mark.parametrize(
        "selector",
        [".app-main", ".dot.live", ".dialogue .chevron", ".owl-spin"],
    )
    def test_reduced_motion_covers_selector(self, enhance_css, selector):
        # Find the reduce block (between @media and closing brace)
        m = re.search(
            r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.+?)\}\s*(?=@|\Z)",
            enhance_css, re.DOTALL,
        )
        assert m, "prefers-reduced-motion block missing closing brace"
        block = m.group(1)
        assert selector in block, (
            f"prefers-reduced-motion block must include {selector!r} "
            f"so the animation is suppressed for users who request it"
        )


# ---------------------------------------------------------------------------
# 3) hero-owl responsive behavior
# ---------------------------------------------------------------------------

class TestHeroOwlResponsive:
    """The hero owl decoration must not overlap hero text on narrow screens."""

    @pytest.fixture(scope="class")
    def layout_css(self):
        return _read("layout.css")

    def test_hero_owl_selector_exists(self, layout_css):
        assert ".hero-owl" in layout_css, "Expected .hero-owl selector in layout.css"

    def test_hero_owl_hidden_at_480px(self, layout_css):
        # Extract the @media (max-width: 480px) block
        m = re.search(
            r"@media\s*\(max-width:\s*480px\)\s*\{(.+?)\}\s*(?=@|\Z)",
            layout_css, re.DOTALL,
        )
        assert m, "Missing @media (max-width: 480px) block in layout.css"
        block = m.group(1)
        # must hide .hero-owl on the smallest breakpoint
        assert re.search(r"\.hero-owl\s*\{[^}]*display\s*:\s*none", block), (
            ".hero-owl must be hidden on viewports <= 480px to avoid overlapping hero text"
        )

    def test_hero_owl_resized_at_1100px(self, layout_css):
        m = re.search(
            r"@media\s*\(max-width:\s*1100px\)\s*\{(.+?)\}\s*(?=@|\Z)",
            layout_css, re.DOTALL,
        )
        assert m, "Missing @media (max-width: 1100px) block in layout.css"
        block = m.group(1)
        # must constrain .hero-owl at the medium breakpoint
        assert ".hero-owl" in block, (
            ".hero-owl should have a responsive rule at <=1100px to prevent overlap"
        )
        assert re.search(r"\.hero-owl\s*\{[^}]*(width|height|right)", block), (
            "Expected .hero-owl responsive sizing/positioning inside @media (max-width: 1100px)"
        )
