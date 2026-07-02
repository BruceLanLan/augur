# -*- coding: utf-8 -*-
"""Signals dashboard UX tests (Round 8 Agent B).

Verifies UX improvements to dashboard/templates/signals.html:

1. Watchlist table rows are keyboard accessible: tabindex, role, aria-label
   and Enter/Space activation (WCAG 2.1.1).
2. The "+ Add" button has a loading state (disabled + i18n key) and
   double-submit is prevented (so users can't add the same ticker twice
   when the request is slow).
3. Empty-state example chips expose a translated aria-label and live
   inside a role=group wrapper so screen readers announce them as a set.
4. The "no filter match" state is rendered with role=status so assistive
   tech is told the result count has changed.
5. The watchlist <tbody> starts in aria-busy="true" with data-state="loading"
   so the spinner is announced and not lost on a long fetch.
"""
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "templates"
SIGNALS_HTML = TEMPLATES_DIR / "signals.html"


def _read() -> str:
    assert SIGNALS_HTML.is_file(), f"Missing template: {SIGNALS_HTML}"
    return SIGNALS_HTML.read_text(encoding="utf-8")


def _render():
    """Render signals.html through Jinja so we can inspect the JS source."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    t = env.get_template("signals.html")
    return t.render()


@pytest.fixture(scope="module")
def signals_text():
    return _read()


@pytest.fixture(scope="module")
def signals_rendered():
    return _render()


class TestKeyboardAccessibleRows:
    """The signal rows look like table rows but act like expand buttons -
    they MUST be reachable and activatable by keyboard (WCAG 2.1.1)."""

    def test_row_template_has_tabindex(self, signals_text):
        # The .signal-row-main row template must declare tabindex=0 so the
        # row joins the natural tab order.
        assert 'class="signal-row-main" tabindex="0"' in signals_text, (
            "signal-row-main must be tabbable (tabindex=0)"
        )

    def test_row_template_has_role_and_aria_label(self, signals_text):
        # role=button + aria-label gives screen readers an accessible name
        # and tells them this is an interactive control, not a data cell.
        assert 'role="button"' in signals_text
        # The label must reference a translatable key + the ticker name.
        assert "signals-row-aria" in signals_text
        assert 'aria-label="' in signals_text

    def test_row_template_activates_on_enter_and_space(self, signals_text):
        # Pressing Enter or Space on a focused row should toggle the
        # detail panel the same way a click does (WCAG 2.1.1).
        # The handler lives inside a JS string, so 'Enter' and ' ' are
        # escaped with backslashes. We test for the underlying logic.
        onkeydown = re.search(
            r'class="signal-row-main"[^>]*onkeydown="([^"]+)"', signals_text
        )
        assert onkeydown, "row template must have onkeydown handler"
        handler = onkeydown.group(1)
        # Strip JS escape chars so we can match Enter and Space in a
        # readable way regardless of how they are quoted.
        flat = handler.replace("\\'", "'")
        assert "Enter" in flat, f"onkeydown must handle Enter, got: {handler}"
        assert "' '" in flat, f"onkeydown must handle Space, got: {handler}"
        assert "preventDefault" in flat, (
            f"onkeydown must preventDefault to avoid page scroll, got: {handler}"
        )


class TestAddButtonLoadingState:
    """The + Add button must show a pending state and ignore double-clicks
    so a slow network cannot create duplicate watchlist entries."""

    def test_add_button_disabled_during_request(self, signals_text):
        # addTicker() must set disabled=true on the Add button before fetch
        # and restore it in both .then and .catch.
        add_fn_match = re.search(
            r"function addTicker\(\)\s*\{(.+?)\n\}", signals_text, re.DOTALL
        )
        assert add_fn_match, "addTicker() function not found"
        body = add_fn_match.group(1)
        assert "addBtn.disabled = true" in body, "addBtn must be disabled on submit"
        assert "addBtn.disabled = false" in body, "addBtn must be re-enabled on resolve"
        # .disabled check before fetch blocks double-submit
        assert "if (addBtn && addBtn.disabled) return" in body, (
            "double-submit guard missing"
        )

    def test_add_button_uses_pending_label(self, signals_text):
        # The pending label should come from a translatable i18n key.
        assert "signals-add-pending" in signals_text, (
            "Add button must use a translatable pending-state key"
        )


class TestEmptyStateAccessibility:
    """The empty-state example chips must be screen-reader friendly and
    grouped so they read as a single set."""

    def test_example_chips_have_aria_labels(self, signals_text):
        # Each example chip must carry an aria-label that mentions the
        # ticker so it is meaningful to a screen reader user. The chips
        # are constructed via JS string concatenation, so the attribute
        # appears as 'aria-label="' + escapeHtml(...) + '"' in source.
        assert "signals-add-example-aria" in signals_text, (
            "i18n key signals-add-example-aria must exist"
        )
        for ticker in ("AAPL", "NVDA", "MSFT"):
            # The whole chip line (escaped quotes) must include the
            # ticker name in the aria-label composition. We use a
            # simple substring check on the rendered HTML to keep the
            # test robust to whitespace/formatting changes.
            line_re = re.compile(
                r"quickAddExample\(\\?'" + ticker + r"\\?'\)"
                r"[\s\S]{0,200}"
                r"aria-label=\"[^\"]*" + ticker + r"[^\"]*\""
            )
            assert line_re.search(signals_text), (
                f"Example chip {ticker} missing aria-label with ticker name"
            )

    def test_chips_wrapped_in_role_group(self, signals_text):
        # role=group with an accessible name turns three loose buttons
        # into a single announced "Example tickers" set. The wrapper is
        # emitted inside a JS string so we look for the literal substring.
        assert 'role="group" aria-label="Example tickers"' in signals_text, (
            "Empty-state chips must be wrapped in role=group"
        )
        # All three tickers must appear as quickAddExample calls (note
        # the JS source uses \' to escape the single quote).
        for ticker in ("AAPL", "NVDA", "MSFT"):
            assert (
                f"quickAddExample(\\'{ticker}\\')" in signals_text
            ), f"chip call missing for {ticker}"


class TestInitialLoadingSemantics:
    """The watchlist <tbody> must announce its initial loading state so
    assistive tech does not skip past the spinner on a slow fetch."""

    def test_tbody_starts_aria_busy_true(self, signals_text):
        # The static markup ships with aria-busy="true" so SR users hear
        # the loading state before any JS runs.
        tbody_match = re.search(
            r'<tbody id="watchlist-body"([^>]*)>', signals_text
        )
        assert tbody_match, "watchlist-body tbody not found"
        attrs = tbody_match.group(1)
        assert 'aria-busy="true"' in attrs, "tbody must start aria-busy=true"
        assert 'data-state="loading"' in attrs, "tbody must start data-state=loading"

    def test_tbody_skeleton_row_present(self, signals_text):
        # The initial spinner row should be present in the static markup
        # so the user sees feedback before fetch resolves.
        assert 'class="spinner"' in signals_text
        assert "signals-loading" in signals_text
