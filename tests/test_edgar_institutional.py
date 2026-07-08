# -*- coding: utf-8 -*-
"""Phase C, stage 2 (spec's 阶段3): SEC EDGAR 13F institutional-holdings
factor.

Offline, deterministic tests against synthetic 13F information-table XML
shaped exactly like real filings (structure, including the XML namespace
and multi-manager-sleeve duplication, confirmed against real Berkshire
Hathaway and Renaissance Technologies 13F-HR filings during
implementation -- see edgar_institutional.py module docstring).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from augur.consensus import edgar_institutional as ei
from augur.consensus.edgar_fundamentals import EdgarClient


def _info_table_xml(entries: list) -> str:
    """entries: list of (cusip, shares, other_manager) tuples."""
    rows = ""
    for cusip, shares, other_manager in entries:
        rows += f"""
  <infoTable>
    <nameOfIssuer>TEST CO</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>{cusip}</cusip>
    <value>1000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>{shares}</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>DFND</investmentDiscretion>
    <otherManager>{other_manager}</otherManager>
    <votingAuthority><Sole>{shares}</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>"""
    return f"""<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">{rows}
</informationTable>"""


def _submissions(filings: list) -> dict:
    """filings: list of (accession_number, filing_date, report_date) tuples,
    all form 13F-HR."""
    return {
        "filings": {
            "recent": {
                "form": ["13F-HR"] * len(filings),
                "accessionNumber": [f[0] for f in filings],
                "filingDate": [f[1] for f in filings],
                "reportDate": [f[2] for f in filings],
            }
        }
    }


def _patch_client(submissions: dict, index_by_accn: dict, xml_by_accn: dict, cik: int = 1067983):
    def _get_index(self, cik_arg, accn):
        return index_by_accn.get(accn)

    def _get_doc(self, cik_arg, accn, filename):
        return xml_by_accn.get((accn, filename))

    return patch.multiple(
        EdgarClient,
        get_submissions=lambda self, cik_arg: submissions,
        get_filing_index=_get_index,
        get_filing_document=_get_doc,
    )


TEST_CUSIP = "037833100"  # AAPL's real CUSIP, used as the test target


class TestFilenameDiscovery:
    """The core real-data-driven fix: holdings-table filenames aren't
    predictable, must be discovered per-filing via the index."""

    def test_finds_numeric_filename_excluding_primary_doc(self):
        """Exact filename set confirmed from real Berkshire 2026-05-15
        13F-HR filing directory."""
        names = ["accn-index.html", "accn.txt", "53405.xml", "primary_doc.xml"]
        with patch.object(EdgarClient, "get_filing_index", return_value=names):
            client = EdgarClient()
            result = ei._find_holdings_table_filename(client, 1067983, "accn")
        assert result == "53405.xml"

    def test_finds_legacy_named_filename(self):
        """Real 2017 Berkshire filing used form13fInfoTable.xml instead of
        a numeric name -- must not hardcode either convention."""
        names = ["accn-index.html", "accn.txt", "form13fInfoTable.xml", "primary_doc.xml"]
        with patch.object(EdgarClient, "get_filing_index", return_value=names):
            client = EdgarClient()
            result = ei._find_holdings_table_filename(client, 1067983, "accn")
        assert result == "form13fInfoTable.xml"

    def test_no_index_available_returns_none(self):
        with patch.object(EdgarClient, "get_filing_index", return_value=None):
            client = EdgarClient()
            result = ei._find_holdings_table_filename(client, 1067983, "accn")
        assert result is None


class TestMultiManagerSleeveAggregation:
    """The other core real-data-driven fix: one filer's total position is
    split across multiple infoTable entries, distinguished only by
    otherManager -- confirmed against real Berkshire data (3 separate
    Ally Financial entries in one filing)."""

    def test_sums_shares_across_multiple_sleeves_same_cusip(self):
        xml = _info_table_xml([
            (TEST_CUSIP, 1000000, "4"),
            (TEST_CUSIP, 500000, "2,4,11"),
            (TEST_CUSIP, 2000000, "4,5"),
        ])
        assert ei._shares_for_cusip(xml, TEST_CUSIP) == pytest.approx(3500000)

    def test_ignores_entries_for_other_cusips(self):
        xml = _info_table_xml([
            (TEST_CUSIP, 1000000, "4"),
            ("999999999", 5000000, "4"),  # a different company entirely
        ])
        assert ei._shares_for_cusip(xml, TEST_CUSIP) == pytest.approx(1000000)

    def test_cusip_not_present_returns_none_not_zero(self):
        """Distinguishes 'institution doesn't hold this' from 'holds
        exactly zero shares of an entry that does exist'."""
        xml = _info_table_xml([("999999999", 5000000, "4")])
        assert ei._shares_for_cusip(xml, TEST_CUSIP) is None

    def test_malformed_xml_returns_none(self):
        assert ei._shares_for_cusip("<not valid xml", TEST_CUSIP) is None


class TestQuarterOverQuarterChange:
    def test_new_position_reads_as_full_increase(self):
        subs = _submissions([
            ("accn-2", "2026-05-15", "2026-03-31"),
            ("accn-1", "2026-02-15", "2025-12-31"),
        ])
        index = {"accn-2": ["primary_doc.xml", "holdings.xml"], "accn-1": ["primary_doc.xml", "holdings.xml"]}
        xml = {
            ("accn-2", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 1000000, "1")]),
            ("accn-1", "holdings.xml"): _info_table_xml([]),  # didn't hold it last quarter
        }
        with _patch_client(subs, index, xml):
            client = EdgarClient()
            change = ei._institution_share_change(client, 1067983, TEST_CUSIP, "2026-06-01")
        assert change == 1.0

    def test_full_exit_reads_as_full_decrease(self):
        subs = _submissions([
            ("accn-2", "2026-05-15", "2026-03-31"),
            ("accn-1", "2026-02-15", "2025-12-31"),
        ])
        index = {"accn-2": ["primary_doc.xml", "holdings.xml"], "accn-1": ["primary_doc.xml", "holdings.xml"]}
        xml = {
            ("accn-2", "holdings.xml"): _info_table_xml([]),
            ("accn-1", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 1000000, "1")]),
        }
        with _patch_client(subs, index, xml):
            client = EdgarClient()
            change = ei._institution_share_change(client, 1067983, TEST_CUSIP, "2026-06-01")
        assert change == -1.0

    def test_partial_increase_computed_correctly(self):
        subs = _submissions([
            ("accn-2", "2026-05-15", "2026-03-31"),
            ("accn-1", "2026-02-15", "2025-12-31"),
        ])
        index = {"accn-2": ["primary_doc.xml", "holdings.xml"], "accn-1": ["primary_doc.xml", "holdings.xml"]}
        xml = {
            ("accn-2", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 1200000, "1")]),
            ("accn-1", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 1000000, "1")]),
        }
        with _patch_client(subs, index, xml):
            client = EdgarClient()
            change = ei._institution_share_change(client, 1067983, TEST_CUSIP, "2026-06-01")
        assert change == pytest.approx(0.2)

    def test_never_held_returns_none(self):
        subs = _submissions([
            ("accn-2", "2026-05-15", "2026-03-31"),
            ("accn-1", "2026-02-15", "2025-12-31"),
        ])
        index = {"accn-2": ["primary_doc.xml", "holdings.xml"], "accn-1": ["primary_doc.xml", "holdings.xml"]}
        xml = {
            ("accn-2", "holdings.xml"): _info_table_xml([("999999999", 500, "1")]),
            ("accn-1", "holdings.xml"): _info_table_xml([("999999999", 500, "1")]),
        }
        with _patch_client(subs, index, xml):
            client = EdgarClient()
            change = ei._institution_share_change(client, 1067983, TEST_CUSIP, "2026-06-01")
        assert change is None

    def test_fewer_than_two_as_of_available_filings_returns_none(self):
        subs = _submissions([("accn-1", "2026-02-15", "2025-12-31")])
        with _patch_client(subs, {}, {}):
            client = EdgarClient()
            change = ei._institution_share_change(client, 1067983, TEST_CUSIP, "2026-06-01")
        assert change is None

    def test_point_in_time_excludes_filings_after_as_of_date(self):
        """A filing filed AFTER as_of_date must not count toward the
        'most recent 2 filings' selection."""
        subs = _submissions([
            ("accn-future", "2026-08-15", "2026-06-30"),  # filed after as_of
            ("accn-2", "2026-05-15", "2026-03-31"),
            ("accn-1", "2026-02-15", "2025-12-31"),
        ])
        index = {"accn-2": ["primary_doc.xml", "holdings.xml"], "accn-1": ["primary_doc.xml", "holdings.xml"],
                 "accn-future": ["primary_doc.xml", "holdings.xml"]}
        xml = {
            ("accn-2", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 1200000, "1")]),
            ("accn-1", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 1000000, "1")]),
            ("accn-future", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 99999999, "1")]),
        }
        with _patch_client(subs, index, xml):
            client = EdgarClient()
            change = ei._institution_share_change(client, 1067983, TEST_CUSIP, "2026-06-01")
        # Must use accn-2 vs accn-1, not accn-future
        assert change == pytest.approx(0.2)


class TestFetchInstitutionalFlowSignal:
    def test_unknown_ticker_returns_neutral(self):
        result = ei.fetch_institutional_flow_signal("NOTINTABLE", "2026-06-01")
        assert result == {"institutional_flow_signal": 5.0}

    def test_malformed_date_returns_neutral(self):
        result = ei.fetch_institutional_flow_signal("AAPL", "not-a-date")
        assert result == {"institutional_flow_signal": 5.0}

    def test_net_buying_across_institutions_moves_signal_bullish(self):
        subs = _submissions([
            ("accn-2", "2026-05-15", "2026-03-31"),
            ("accn-1", "2026-02-15", "2025-12-31"),
        ])
        index = {"accn-2": ["primary_doc.xml", "holdings.xml"], "accn-1": ["primary_doc.xml", "holdings.xml"]}
        xml = {
            ("accn-2", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 2000000, "1")]),
            ("accn-1", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 1000000, "1")]),
        }
        with _patch_client(subs, index, xml):
            result = ei.fetch_institutional_flow_signal("AAPL", "2026-06-01")
        assert result["institutional_flow_signal"] > 5.0

    def test_net_selling_across_institutions_moves_signal_bearish(self):
        subs = _submissions([
            ("accn-2", "2026-05-15", "2026-03-31"),
            ("accn-1", "2026-02-15", "2025-12-31"),
        ])
        index = {"accn-2": ["primary_doc.xml", "holdings.xml"], "accn-1": ["primary_doc.xml", "holdings.xml"]}
        xml = {
            ("accn-2", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 500000, "1")]),
            ("accn-1", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 1000000, "1")]),
        }
        with _patch_client(subs, index, xml):
            result = ei.fetch_institutional_flow_signal("AAPL", "2026-06-01")
        assert result["institutional_flow_signal"] < 5.0

    def test_signal_bounded_to_0_10(self):
        subs = _submissions([
            ("accn-2", "2026-05-15", "2026-03-31"),
            ("accn-1", "2026-02-15", "2025-12-31"),
        ])
        index = {"accn-2": ["primary_doc.xml", "holdings.xml"], "accn-1": ["primary_doc.xml", "holdings.xml"]}
        xml = {
            ("accn-2", "holdings.xml"): _info_table_xml([(TEST_CUSIP, 100_000_000, "1")]),
            ("accn-1", "holdings.xml"): _info_table_xml([]),
        }
        with _patch_client(subs, index, xml):
            result = ei.fetch_institutional_flow_signal("AAPL", "2026-06-01")
        assert 0.0 <= result["institutional_flow_signal"] <= 10.0

    def test_no_institution_has_data_returns_neutral(self):
        subs = _submissions([("accn-1", "2026-02-15", "2025-12-31")])  # only 1 filing, no pair
        with _patch_client(subs, {}, {}):
            result = ei.fetch_institutional_flow_signal("AAPL", "2026-06-01")
        assert result == {"institutional_flow_signal": 5.0}

    def test_never_raises_on_unexpected_exception(self):
        with patch.object(EdgarClient, "get_submissions", side_effect=RuntimeError("boom")):
            result = ei.fetch_institutional_flow_signal("AAPL", "2026-06-01")
        assert result == {"institutional_flow_signal": 5.0}

    def test_all_tracked_institutions_are_real_verified_ciks(self):
        """Regression guard: every CIK in the curated list must be a
        plausible SEC CIK (positive int) -- catches an obvious typo, not a
        substitute for the manual verification done during implementation."""
        for name, cik in ei._TRACKED_INSTITUTIONS.items():
            assert isinstance(cik, int) and cik > 0, f"{name} has an invalid CIK: {cik}"

    def test_ticker_cusip_table_has_no_duplicate_cusips(self):
        """Two different tickers must never map to the same CUSIP -- would
        silently conflate two distinct companies' institutional flow."""
        cusips = list(ei._TICKER_TO_CUSIP.values())
        assert len(cusips) == len(set(cusips))
