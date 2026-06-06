# -*- coding: utf-8 -*-
"""Backtest dashboard UX tests (Round 8 Agent C).

Validates UX/a11y fixes applied to dashboard/templates/backtest.html:

  1. Day-toggle buttons (.bt-days-btn) are exposed as a real
     role="group" with an accessible name and each carries
     aria-pressed so screen readers announce the current selection.
  2. The result panels (bt-banner, bt-metrics, bt-leaderboard,
     bt-timeline) are wired as aria-live regions with accessible
     names, and the loading panel keeps aria-busy in sync with the
     actual loading state.
  3. The ticker input has a visible validation hint target, the
     run button toggles aria-busy while loading, and the runBacktest
     function refuses to submit an empty / malformed ticker — i.e.
     the form is no longer a dead one-size-fits-all silent fall-
     through to 'AAPL'.
  4. The Ticker input supports Enter-to-submit (no <form> wrapper
     was added, but the keydown handler on the input delegates to
     runBacktest).
"""

import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "templates"
BACKTEST_HTML = TEMPLATES_DIR / "backtest.html"


def _read_template() -> str:
    assert BACKTEST_HTML.is_file(), f"Missing template: {BACKTEST_HTML}"
    return BACKTEST_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def backtest_text() -> str:
    return _read_template()


@pytest.fixture(scope="module")
def backtest_soup() -> BeautifulSoup:
    return BeautifulSoup(_read_template(), "html.parser")


# ============================================================
# Issue 1: Day-toggle button group has ARIA semantics
# ============================================================
class TestDayToggleGroupA11y:
    EXPECTED_DAYS = [30, 60, 90, 180, 365]

    def test_days_buttons_have_aria_pressed(self, backtest_soup):
        """Each day button must expose aria-pressed for screen readers."""
        buttons = backtest_soup.select(".bt-days-btn")
        assert len(buttons) == len(self.EXPECTED_DAYS), (
            f"expected {len(self.EXPECTED_DAYS)} day buttons, got {len(buttons)}"
        )
        for btn in buttons:
            val = btn.get("aria-pressed")
            assert val in ("true", "false"), (
                f"day button {btn.get('data-days')} must have aria-pressed set, got {val!r}"
            )

    def test_default_30d_button_is_pressed(self, backtest_soup):
        """The default-selected (30d) button must start with aria-pressed='true'."""
        btn = backtest_soup.find("button", attrs={"data-days": "30"})
        assert btn is not None, "30d button missing"
        assert btn.get("aria-pressed") == "true", (
            "the default day button (30d) must be announced as pressed"
        )

    def test_other_day_buttons_start_unpressed(self, backtest_soup):
        for d in (60, 90, 180, 365):
            btn = backtest_soup.find("button", attrs={"data-days": str(d)})
            assert btn is not None, f"{d}d button missing"
            assert btn.get("aria-pressed") == "false", (
                f"{d}d button must start as aria-pressed='false'"
            )

    def test_days_buttons_have_type_button(self, backtest_soup):
        """Without type='button' the buttons default to type='submit' inside a form,
        which would cause a hard reload when activated. We use type='button'."""
        for btn in backtest_soup.select(".bt-days-btn"):
            assert btn.get("type") == "button", (
                f"day button {btn.get('data-days')} must have explicit type='button'"
            )

    def test_days_group_has_role_and_label(self, backtest_soup):
        group = backtest_soup.find(id="bt-days-group")
        assert group is not None, "bt-days-group container missing"
        assert group.get("role") == "group", "day toggle container must be role='group'"
        assert group.get("aria-label"), "day toggle group needs an accessible name"

    def test_setdays_js_updates_aria_pressed(self, backtest_text):
        """The JS that toggles the active day must also flip aria-pressed."""
        # The setDays function must call setAttribute('aria-pressed', ...)
        assert re.search(
            r"btn\.setAttribute\(\s*['\"]aria-pressed['\"]\s*,\s*pressed\s*\?\s*['\"]true['\"]\s*:\s*['\"]false['\"]\s*\)",
            backtest_text,
        ), "setDays() must update aria-pressed on the day buttons"


# ============================================================
# Issue 2: Loading & result panels expose ARIA live regions
# ============================================================
class TestBacktestPanelLiveRegions:
    PANEL_IDS = [
        "bt-banner",
        "bt-metrics",
        "bt-leaderboard",
        "bt-timeline",
    ]

    @pytest.mark.parametrize("panel_id", PANEL_IDS)
    def test_panel_has_aria_live(self, backtest_soup, panel_id):
        el = backtest_soup.find(id=panel_id)
        assert el is not None, f"panel #{panel_id} not found"
        assert el.get("aria-live") in ("polite", "assertive"), (
            f"#{panel_id} must declare aria-live so live-region updates are announced"
        )

    @pytest.mark.parametrize("panel_id", PANEL_IDS)
    def test_panel_has_accessible_label(self, backtest_soup, panel_id):
        el = backtest_soup.find(id=panel_id)
        assert el is not None
        assert el.get("aria-label"), (
            f"#{panel_id} needs an aria-label so live updates are meaningful"
        )

    def test_loading_panel_aria_busy_default_false(self, backtest_soup):
        """The loading panel must NOT be aria-busy='true' on initial render,
        otherwise screen readers would announce the loader forever."""
        el = backtest_soup.find(id="bt-loading")
        assert el is not None
        assert el.get("aria-busy") == "false", (
            "#bt-loading must default to aria-busy='false' on initial render"
        )

    def test_runbacktest_toggles_aria_busy_on_loading(self, backtest_text):
        """runBacktest() must set aria-busy='true' when starting and
        reset it to 'false' in the finally block."""
        # Find the finally block
        m = re.search(
            r"finally\s*\{[^}]*loadingEl\.setAttribute\(\s*['\"]aria-busy['\"]\s*,\s*['\"]false['\"]\s*\)",
            backtest_text,
            re.DOTALL,
        )
        assert m, "runBacktest() finally block must reset aria-busy to 'false' on #bt-loading"

        m2 = re.search(
            r"loadingEl\.setAttribute\(\s*['\"]aria-busy['\"]\s*,\s*['\"]true['\"]\s*\)",
            backtest_text,
        )
        assert m2, "runBacktest() must set aria-busy='true' on #bt-loading when starting"

    def test_run_btn_toggles_aria_busy(self, backtest_text):
        """The run button itself must toggle aria-busy so screen readers
        announce the long-running operation."""
        assert "_setRunBtnBusy" in backtest_text, "run button busy state via _setRunBtnBusy"
        assert re.search(
            r"btn\.setAttribute\(\s*['\"]aria-busy['\"]\s*,\s*busy\s*\?\s*['\"]true['\"]\s*:\s*['\"]false['\"]\s*\)",
            backtest_text,
        ), "_setRunBtnBusy must toggle aria-busy on the run button"


# ============================================================
# Issue 3: Form is no longer dead — ticker validation + Enter
# ============================================================
class TestTickerFormValidation:
    def test_ticker_input_has_hint_target(self, backtest_soup):
        """There must be a visible-validation hint target wired to the ticker input."""
        ticker_input = backtest_soup.find(id="bt-ticker")
        assert ticker_input is not None
        assert ticker_input.get("aria-describedby") == "bt-ticker-hint", (
            "ticker input must be wired to a hint element via aria-describedby"
        )
        hint = backtest_soup.find(id="bt-ticker-hint")
        assert hint is not None, "ticker hint element (#bt-ticker-hint) missing"
        assert hint.get("role") == "alert", (
            "ticker hint must use role='alert' so screen readers announce it"
        )

    def test_ticker_input_has_maxlength(self, backtest_soup):
        ticker_input = backtest_soup.find(id="bt-ticker")
        assert ticker_input is not None
        assert ticker_input.get("maxlength") is not None, (
            "ticker input must have a maxlength to prevent absurd inputs"
        )

    def test_ticker_input_supports_enter_to_submit(self, backtest_text):
        """Pressing Enter in the ticker field must trigger runBacktest()."""
        # Inline onkeydown handler on the ticker input
        m = re.search(
            r"id=[\"']bt-ticker[\"'][^>]*onkeydown=[\"'][^\"]*Enter[^\"]*runBacktest\(\)",
            backtest_text,
        )
        assert m, "ticker input must have an Enter-to-run onkeydown handler"

    def test_runbacktest_rejects_empty_ticker(self, backtest_text):
        """runBacktest() must early-return on empty ticker instead of silently
        defaulting to AAPL — the 'dead form' symptom."""
        # Look for an early-return on empty ticker inside runBacktest
        # and the absence of the old `|| 'AAPL'` fallback.
        assert "if (!ticker)" in backtest_text, (
            "runBacktest() must explicitly check for empty ticker"
        )
        # The buggy pattern from before must be gone
        assert ".trim().toUpperCase() || 'AAPL'" not in backtest_text, (
            "old 'silently fall back to AAPL' logic must be removed"
        )

    def test_runbacktest_rejects_malformed_ticker(self, backtest_text):
        """runBacktest() must validate ticker format (regex of allowed chars)."""
        m = re.search(
            r"/\^\[A-Z0-9\.\\-\]\{1,10\}\$/",
            backtest_text,
        )
        assert m, "runBacktest() must validate ticker against a strict character set"
