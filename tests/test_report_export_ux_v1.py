# -*- coding: utf-8 -*-
"""Report / PDF / export UX tests — loop-400-review.

Builds on loop-200 report contrast fixes: export helpers, print/PDF,
theme-aware HTML, i18n toasts, remaining parchment contrast edge cases.
"""
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "templates"
STATIC_JS = Path(__file__).resolve().parents[1] / "dashboard" / "static" / "js" / "i18n.js"
CSS_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "static" / "css"


def _read(name: str) -> str:
    p = TEMPLATES_DIR / name
    assert p.is_file(), f"Missing template: {p}"
    return p.read_text(encoding="utf-8")


def _read_css(name: str) -> str:
    p = CSS_DIR / name
    assert p.is_file(), f"Missing css: {p}"
    return p.read_text(encoding="utf-8")


REPORT_I18N_KEYS = [
    "report-export-html",
    "report-print-pdf",
    "report-view-analysis",
    "report-voting-board",
    "report-full-markdown",
    "report-exec-summary",
    "report-consensus",
    "report-bullish",
    "report-bearish",
    "report-neutral-label",
    "report-agents-voted",
    "report-score-distribution",
    "report-generated",
    "report-voting-empty",
    "report-toast-no-report",
    "report-toast-md-downloaded",
    "report-toast-html-downloaded",
    "report-toast-copied",
    "report-toast-copy-failed",
    "report-toast-print-prep",
]


@pytest.fixture(scope="module")
def report_html():
    return _read("report_view.html")


@pytest.fixture(scope="module")
def report_soup():
    return BeautifulSoup(_read("report_view.html"), "html.parser")


@pytest.fixture(scope="module")
def base_html():
    return _read("base.html")


class TestReportExportHelpers:
    """Shared export utilities live in base.html for report + stocks pages."""

    def test_base_exports_build_report_html_export(self, base_html):
        assert "function buildReportHTMLExport(" in base_html
        assert "isLightTheme()" in base_html

    def test_base_exports_prepare_report_print(self, base_html):
        assert "function prepareReportPrint(" in base_html
        assert "expandAllReportSections" in base_html

    def test_base_exports_report_theme_color(self, base_html):
        assert "function reportThemeColor(" in base_html


class TestReportViewExportBar:
    """Dedicated report page must expose MD / HTML / PDF / copy actions."""

    def test_download_bar_has_md_html_pdf_copy(self, report_soup):
        bar = report_soup.find(id="rp-download-bar")
        assert bar is not None
        onclick = " ".join(
            (btn.get("onclick") or "") for btn in bar.find_all("button")
        )
        assert "downloadReportMD()" in onclick
        assert "downloadReportHTML()" in onclick
        assert "downloadReportPDF()" in onclick
        assert "copyReportText()" in onclick

    def test_pdf_button_has_i18n(self, report_soup):
        btn = report_soup.find("button", attrs={"onclick": "downloadReportPDF()"})
        assert btn is not None
        assert btn.get("data-i18n") == "report-print-pdf"

    def test_view_analysis_link_i18n(self, report_soup):
        link = report_soup.find(id="rp-view-stocks-link")
        assert link is not None
        assert link.get("data-i18n") == "report-view-analysis"

    def test_export_uses_shared_html_builder(self, report_html):
        assert "buildReportHTMLExport(rpTicker, renderedBody)" in report_html
        assert "prepareReportPrint()" in report_html
        assert "showToast('No report available'" not in report_html

    def test_dynamic_labels_use_t_helper(self, report_html):
        assert "_t('report-exec-summary')" in report_html
        assert "_t('report-consensus')" in report_html
        assert "_t('report-score-distribution')" in report_html


class TestReportI18nKeys:
    """New report export keys must exist in zh and en with parity."""

    @pytest.fixture(scope="class")
    def i18n_blocks(self):
        text = STATIC_JS.read_text(encoding="utf-8")
        m = re.search(r"window\.I18N\s*=\s*\{(.+?)\n\};", text, re.S)
        assert m
        inner = m.group(1)
        en_marker = inner.find("\n    en:")
        ja_marker = inner.find("\n    ja:")
        en_end = ja_marker if ja_marker != -1 else len(inner)
        zh_block = inner[:en_marker]
        en_block = inner[en_marker:en_end]
        def keys(block):
            return set(re.findall(r'"([a-z0-9_-]+)"\s*:', block))
        return keys(zh_block), keys(en_block)

    def test_report_keys_in_zh_and_en(self, i18n_blocks):
        zh, en = i18n_blocks
        for key in REPORT_I18N_KEYS:
            assert key in zh, f"Missing zh key: {key}"
            assert key in en, f"Missing en key: {key}"


class TestReportPrintContrast:
    """Print CSS must flatten parchment panels to readable black-on-white."""

    def test_report_view_print_flattens_parchment(self, report_html):
        print_block = report_html.split("@media print")[1]
        assert "report-md-panel" in print_block or ".md-report" in print_block
        assert "#fff" in print_block
        assert "#222" in print_block

    def test_bloomberg_print_flattens_scroll_md_report(self):
        css = _read_css("bloomberg.css")
        print_idx = css.rfind("/* --- Print Styles for Report --- */")
        assert print_idx != -1
        block = css[print_idx:print_idx + 2500]
        assert ".scroll" in block
        assert "#report-content.md-report" in block
        assert "color: #222" in block

    def test_score_gauge_track_uses_css_var(self, report_html):
        assert "var(--report-chart-track" in report_html
        assert "background: rgba(255,255,255,0.06)" not in report_html


class TestStocksReportExportParity:
    """Inline stocks report toolbar should reuse shared export helpers."""

    def test_stocks_html_export_uses_builder(self):
        html = _read("stocks.html")
        assert "buildReportHTMLExport(ticker, renderedBody)" in html
        assert "prepareReportPrint()" in html

    def test_stocks_gauge_uses_theme_color(self):
        html = _read("stocks.html")
        gauge = html.split("function createScoreGauge")[1].split("function ")[0]
        assert "reportThemeColor" in gauge
        assert 'fill="rgba(255,255,255,0.5)"' not in gauge
