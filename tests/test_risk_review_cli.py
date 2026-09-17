# -*- coding: utf-8 -*-
"""`augur risk-review` — Item 1A across the two latest 10-Ks (risk_review had no entry point).

The HTML fixtures mimic real 10-K structure found on AAPL filings: a table of
contents and an Item 1 cross-reference both mention "Item 1A", risk factors
are a heading paragraph plus body paragraphs, inline <sup>® markup must not
split sentences, and running page footers differ by year.
"""
from click.testing import CliRunner

import augur.risk_review as rr


def _tenk(year, risks):
    body = "".join(
        f"<p><b>{heading}</b></p><p>{text}</p><p>Acme Inc. | {year} Form 10-K | {i + 7}</p>"
        for i, (heading, text) in enumerate(risks)
    )
    return (
        "<html><body>"
        "<p>Item 1A. Risk Factors 7</p><p>Item 1B. Unresolved Staff Comments 20</p>"
        "<p>Item 1. Business</p><p>Acme makes Widgets<sup>®</sup>. See Item 1A. for risks. "
        + "Long business description. " * 200 + "</p>"
        "<p>Item 1A. Risk Factors</p><p>Macroeconomic and Industry Risks</p>"
        + body
        + "<p>Item 1B. Unresolved Staff Comments</p><p>None.</p></body></html>"
    )


PREV = [
    ("The Company faces intense competition", "Competitors may reduce prices and the Company may lose market share."),
    ("The Company's retail stores are subject to numerous risks", "Retail operations may not be profitable in some locations."),
]
NEW = [
    ("The Company faces intense competition", "Competitors may reduce prices and the Company may lose market share."),
    ("New export controls on semiconductors could disrupt supply", "Regulatory restrictions will likely increase costs and delay shipments."),
]


class _FakeEdgar:
    def get_cik(self, ticker):
        return 1234

    def get_submissions(self, cik):
        return {"filings": {"recent": {
            "form": ["10-Q", "10-K", "8-K", "10-K"],
            "accessionNumber": ["q", "new-acc", "k8", "prev-acc"],
            "primaryDocument": ["q.htm", "new.htm", "k8.htm", "prev.htm"],
            "filingDate": ["2026-08-01", "2025-10-31", "2025-06-01", "2024-11-01"],
        }}}

    def get_filing_document(self, cik, accession, document):
        return {"new.htm": _tenk(2025, NEW), "prev.htm": _tenk(2024, PREV)}[document]


def test_section_extraction_skips_toc_and_cross_references():
    text = rr._filing_html_to_text(_tenk(2025, NEW))
    section = rr.group_risk_paragraphs(rr.extract_risk_factor_section(text))

    assert "Long business description" not in section
    assert "Form 10-K" not in section, "page footers must be stripped"
    assert "Macroeconomic and Industry Risks" not in section.split("\n\n")[0], "sub-headings are not risks"
    assert section.count("\n\n") == 1, section  # exactly two risk factors
    assert "Widgets" not in section


def test_fetch_uses_the_two_latest_10k_filings():
    src = rr.fetch_10k_risk_sections("ACME", client=_FakeEdgar())
    assert (src["new_accession"], src["prev_accession"]) == ("new-acc", "prev-acc")
    assert "export controls" in src["new_text"] and "retail stores" in src["prev_text"]


def test_cli_reports_new_and_removed_risks(monkeypatch):
    from augur.cli import main

    monkeypatch.setattr(rr, "fetch_10k_risk_sections", lambda t: rr.__dict__["_orig_fetch"](t, client=_FakeEdgar()))
    result = CliRunner().invoke(main, ["risk-review", "ACME"])

    assert result.exit_code == 0, result.output
    assert "10-K new-acc (filed 2025-10-31)" in result.output
    assert "vs 10-K prev-acc (filed 2024-11-01)" in result.output
    new_block = result.output.split("── New")[1].split("──")[1]
    assert "export controls" in new_block
    removed_block = result.output.split("── Removed")[1]
    assert "retail stores" in removed_block


def test_cli_explains_missing_cik(monkeypatch):
    from augur.cli import main

    def _no_cik(ticker):
        raise LookupError("0700.HK has no SEC CIK (non-US listing or not an XBRL filer)")

    monkeypatch.setattr(rr, "fetch_10k_risk_sections", _no_cik)
    result = CliRunner().invoke(main, ["risk-review", "0700.HK"])
    assert result.exit_code == 1
    assert "no SEC CIK" in result.output


rr.__dict__.setdefault("_orig_fetch", rr.fetch_10k_risk_sections)
