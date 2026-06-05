# -*- coding: utf-8 -*-
"""personas.html UX hardening (Round 13, Agent D).

Round 9 / 11 added accessibility checks for index.html. personas.html
previously shipped with three UX gaps that hurt screen-reader users and
keyboard-only operators:

1. Compare-results and ask-response live regions never declared
   ``aria-live`` / ``aria-busy``, so updates after a fetch landed
   silently and the user could not tell when loading finished.
2. The master-detail overlay was a plain ``<div>`` with no dialog role,
   no aria-modal, no labelledby, no Escape-key close, and no focus
   management.
3. The persona-card grid items were ``onclick``-only with no
   ``role="button"``, no ``tabindex``, and no ``onkeydown`` handler, so
   keyboard users could not open a master detail at all. The search
   input also lacked an accessible name.

These tests pin the new a11y contract in place.
"""
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "templates"
PERSONAS_HTML = TEMPLATES_DIR / "personas.html"


def _read() -> str:
    assert PERSONAS_HTML.is_file(), f"Missing template: {PERSONAS_HTML}"
    return PERSONAS_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def personas_soup():
    return BeautifulSoup(_read(), "html.parser")


@pytest.fixture(scope="module")
def personas_text():
    return _read()


class TestCompareResultsLiveRegion:
    """The compare-results region must declare aria-live + aria-busy so
    screen readers announce the result of runComparison(). The JS is
    expected to flip aria-busy between the request and the response."""

    def test_compare_results_has_aria_live(self, personas_soup):
        el = personas_soup.find(id="compare-results")
        assert el is not None, "#compare-results missing from personas.html"
        assert el.get("aria-live") in ("polite", "assertive"), (
            "#compare-results must declare aria-live so updates are announced"
        )

    def test_compare_results_has_aria_busy_default(self, personas_soup):
        el = personas_soup.find(id="compare-results")
        assert el is not None
        assert el.get("aria-busy") in ("true", "false"), (
            "#compare-results must expose aria-busy (initial value)"
        )

    def test_compare_results_has_accessible_name(self, personas_soup):
        el = personas_soup.find(id="compare-results")
        assert el is not None
        assert (el.get("aria-label") or el.get("aria-labelledby")), (
            "#compare-results needs an accessible name"
        )

    def test_run_comparison_toggles_aria_busy(self, personas_text):
        """runComparison must set aria-busy='true' before fetch and
        'false' in both the success and the catch branches."""
        # True on the way out
        assert re.search(
            r"resultsDiv\.setAttribute\(\s*'aria-busy'\s*,\s*'true'\s*\)",
            personas_text,
        ), "runComparison must mark compare-results busy before fetch"
        # False on the way back (must appear at least twice: then + catch)
        false_calls = re.findall(
            r"resultsDiv\.setAttribute\(\s*'aria-busy'\s*,\s*'false'\s*\)",
            personas_text,
        )
        assert len(false_calls) >= 2, (
            f"runComparison must clear aria-busy in BOTH the success and "
            f"the catch branches, found {len(false_calls)} call(s)"
        )


class TestMasterDetailOverlayDialog:
    """The overlay modal must be a real dialog: role, aria-modal,
    labelledby, an aria-label on the close button, and an Escape-key
    handler that calls closeMasterDetail."""

    def test_overlay_is_a_dialog(self, personas_soup):
        el = personas_soup.find(id="master-detail-overlay")
        assert el is not None
        assert el.get("role") == "dialog", (
            "#master-detail-overlay must expose role='dialog'"
        )
        assert el.get("aria-modal") == "true", (
            "#master-detail-overlay must be marked aria-modal='true'"
        )

    def test_overlay_has_labelledby_target(self, personas_soup):
        el = personas_soup.find(id="master-detail-overlay")
        assert el is not None
        labelled_by = el.get("aria-labelledby")
        assert labelled_by, "#master-detail-overlay must have aria-labelledby"
        # The referenced element must exist and have content
        target = personas_soup.find(id=labelled_by)
        assert target is not None, f"aria-labelledby target #{labelled_by} not found"
        assert target.get_text(strip=True), (
            f"aria-labelledby target #{labelled_by} must contain text"
        )

    def test_close_button_has_aria_label(self, personas_soup):
        btn = personas_soup.find("button", class_="detail-x")
        assert btn is not None, "Modal close button (.detail-x) missing"
        assert btn.get("aria-label"), "Modal close button needs aria-label"

    def test_escape_key_handler_registered(self, personas_text):
        """A document-level keydown listener must close the modal on Escape."""
        # The handler is registered as a named function reference; verify
        # both the registration and the handler body mention Escape.
        assert re.search(
            r"document\.addEventListener\(\s*['\"]keydown['\"]\s*,\s*_escHandler\s*\)",
            personas_text,
        ), "No document-level keydown listener named _escHandler"
        # Pull out the _escHandler function body and confirm it checks Escape
        m = re.search(
            r"var\s+_escHandler\s*=\s*function[^{]*\{(.*?)\n\};",
            personas_text,
            re.S,
        )
        assert m, "_escHandler function body not found"
        body = m.group(1)
        assert re.search(r"Escape|keyCode\s*===\s*27", body, re.I), (
            "_escHandler must check for Escape / keyCode 27"
        )

    def test_close_master_detail_restores_focus(self, personas_text):
        """closeMasterDetail should return focus to the element that
        opened the modal so keyboard users do not lose context."""
        m = re.search(
            r"function\s+closeMasterDetail\s*\([^)]*\)\s*\{(.*?)\n\}",
            personas_text,
            re.S,
        )
        assert m, "closeMasterDetail function not found"
        body = m.group(1)
        # The implementation stores the previously-focused element on a
        # module-level var and refocuses it on close. Accept either a
        # direct activeElement reference or the named cache variable.
        assert (
            "activeElement" in body or "_lastFocusedBeforeModal" in body
        ), "closeMasterDetail should remember and restore the opener's focus"
        assert ".focus(" in body, "closeMasterDetail should call .focus() on restore"


class TestPersonaCardKeyboardActivation:
    """Each persona-card must be a real button for assistive tech:
    role=button, tabindex=0, an onkeydown handler, and an aria-label."""

    @pytest.fixture(scope="class")
    def first_card(self, personas_soup):
        card = personas_soup.find("div", class_="persona-card")
        assert card is not None, "No .persona-card rendered in personas.html"
        return card

    def test_card_has_role_button(self, first_card):
        assert first_card.get("role") == "button", (
            ".persona-card must expose role='button'"
        )

    def test_card_is_keyboard_focusable(self, first_card):
        assert first_card.get("tabindex") == "0", (
            ".persona-card must have tabindex='0' to receive keyboard focus"
        )

    def test_card_has_onkeydown(self, first_card):
        assert first_card.has_attr("onkeydown"), (
            ".persona-card must have an onkeydown handler for Enter/Space"
        )

    def test_card_has_aria_label(self, first_card):
        assert first_card.get("aria-label"), (
            ".persona-card must have an aria-label accessible name"
        )

    def test_keydown_handler_activates_open(self, personas_text):
        """The onkeydown inline handler must call openMasterDetail for
        either Enter or Space, mirroring the onclick behavior."""
        m = re.search(
            r"onkeydown=[\"']if\(event\.key==='Enter'\|" r"\|event\.key===' '\)\{",
            personas_text,
        )
        assert m, (
            "persona-card onkeydown must check for Enter or Space and "
            "preventDefault to avoid page scroll on Space"
        )
        # And call openMasterDetail
        assert "openMasterDetail" in personas_text

    def test_search_input_has_accessible_name(self, personas_soup):
        inp = personas_soup.find(id="persona-search")
        assert inp is not None
        assert (inp.get("aria-label") or inp.get("aria-labelledby")), (
            "#persona-search needs an accessible name for screen readers"
        )
