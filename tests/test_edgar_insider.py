# -*- coding: utf-8 -*-
"""Phase C, Stage 2: SEC EDGAR Form 4 insider-trading factor.

Offline, deterministic tests against synthetic Form 4 XML shaped exactly
like real filings (structure confirmed against real recent AAPL Form 4s
during implementation, including the flat-text transactionCode element and
the M/F/G/S/P transaction-code distribution -- see edgar_insider.py module
docstring for the real-data investigation that motivated the P/S-only
filter).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from augur.consensus import edgar_insider as ei
from augur.consensus.edgar_fundamentals import EdgarClient


def _form4_xml(transactions: list, owner_cik: str = "0001780525") -> str:
    """Build a Form 4 XML string with the given non-derivative transactions.
    Each transaction dict: {code, date, shares, price}."""
    txn_xml = ""
    for t in transactions:
        txn_xml += f"""
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>{t['date']}</value></transactionDate>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>{t['code']}</transactionCode>
                <equitySwapInvolved>0</equitySwapInvolved>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>{t['shares']}</value></transactionShares>
                <transactionPricePerShare><value>{t['price']}</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>{'A' if t['code'] == 'P' else 'D'}</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
            <postTransactionAmounts>
                <sharesOwnedFollowingTransaction><value>100000</value></sharesOwnedFollowingTransaction>
            </postTransactionAmounts>
            <ownershipNature>
                <directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
            </ownershipNature>
        </nonDerivativeTransaction>"""

    return f"""<?xml version="1.0"?>
<ownershipDocument>
    <schemaVersion>X0609</schemaVersion>
    <documentType>4</documentType>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>Test Co</issuerName>
        <issuerTradingSymbol>TEST</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>{owner_cik}</rptOwnerCik>
            <rptOwnerName>Test Insider</rptOwnerName>
        </reportingOwnerId>
    </reportingOwner>
    <nonDerivativeTable>{txn_xml}
    </nonDerivativeTable>
</ownershipDocument>"""


def _submissions(form4_filings: list) -> dict:
    """form4_filings: list of (accession_number, filing_date) tuples."""
    forms = ["4"] * len(form4_filings)
    accns = [f[0] for f in form4_filings]
    dates = [f[1] for f in form4_filings]
    return {
        "filings": {
            "recent": {
                "form": forms,
                "accessionNumber": accns,
                "filingDate": dates,
            }
        }
    }


def _patch_client(submissions: dict, xml_by_accn: dict, cik: int = 320193):
    """Patch EdgarClient to return synthetic submissions + filing XML,
    without touching the network."""
    def _get_doc(self, cik_arg, accn, filename):
        return xml_by_accn.get(accn)

    return patch.multiple(
        EdgarClient,
        get_cik=lambda self, ticker: cik,
        get_submissions=lambda self, cik_arg: submissions,
        get_filing_document=_get_doc,
    )


class TestOpenMarketCodeFiltering:
    """The core real-data-driven fix: only P/S transactions count."""

    def test_purchase_transaction_moves_signal_bullish(self):
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": _form4_xml([{"code": "P", "date": "2024-06-01", "shares": 10000, "price": 50.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result["insider_buying_signal"] > 5.0

    def test_sale_transaction_moves_signal_bearish(self):
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": _form4_xml([{"code": "S", "date": "2024-06-01", "shares": 10000, "price": 50.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result["insider_buying_signal"] < 5.0

    def test_rsu_vesting_m_code_excluded(self):
        """M (exercise/conversion) must not move the signal at all --
        confirmed against real AAPL data as the dominant, non-signal code."""
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": _form4_xml([{"code": "M", "date": "2024-06-01", "shares": 50000, "price": 50.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result["insider_buying_signal"] == 5.0

    def test_tax_withholding_f_code_excluded(self):
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": _form4_xml([{"code": "F", "date": "2024-06-01", "shares": 20000, "price": 50.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result["insider_buying_signal"] == 5.0

    def test_gift_g_code_excluded(self):
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": _form4_xml([{"code": "G", "date": "2024-06-01", "shares": 65000, "price": 0.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result["insider_buying_signal"] == 5.0

    def test_mixed_real_world_shaped_filing_only_counts_the_sale(self):
        """Mirrors a real AAPL filing structure: M (vesting) + F (tax
        withholding) + a genuine S in the same filing -- only S counts."""
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": _form4_xml([
            {"code": "M", "date": "2024-06-01", "shares": 30104, "price": 0.0},
            {"code": "F", "date": "2024-06-01", "shares": 16238, "price": 296.42},
            {"code": "S", "date": "2024-06-01", "shares": 50000, "price": 311.02},
        ])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=50_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        # Only the S transaction (50000 * 311.02) should factor in.
        expected_ratio = -(50000 * 311.02) / 50_000_000.0
        expected = ei._squash_to_signal(expected_ratio)
        assert result["insider_buying_signal"] == pytest.approx(round(expected, 3))


class TestTrailingWindowAndPointInTime:
    def test_filing_outside_90_day_window_excluded(self):
        subs = _submissions([("0001-1", "2024-01-01")])  # >90 days before as_of
        xml = {"0001-1": _form4_xml([{"code": "P", "date": "2024-01-01", "shares": 10000, "price": 50.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result["insider_buying_signal"] == 5.0

    def test_filing_after_as_of_date_excluded(self):
        """Point-in-time guard: a Form 4 filed AFTER the evaluation date
        must not be visible, even if its transaction_date is earlier."""
        subs = _submissions([("0001-1", "2024-06-20")])  # filed after as_of
        xml = {"0001-1": _form4_xml([{"code": "P", "date": "2024-06-01", "shares": 10000, "price": 50.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result["insider_buying_signal"] == 5.0

    def test_filing_exactly_on_as_of_date_included(self):
        subs = _submissions([("0001-1", "2024-06-15")])
        xml = {"0001-1": _form4_xml([{"code": "P", "date": "2024-06-15", "shares": 10000, "price": 50.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result["insider_buying_signal"] > 5.0


class TestClusterBuying:
    # Small enough relative to _SIGNAL_SCALE that the tanh squash stays in
    # its unsaturated region -- large test amounts (e.g. 10000sh @ $50 vs
    # $5M ADV = 10% ratio) push both the clustered and solo cases to the
    # 10.0 ceiling, making the amplification effect invisible to a
    # before/after assertion even though it's correctly applied internally.
    _SHARES = 500
    _PRICE = 50.0
    _ADV = 5_000_000.0

    def test_two_distinct_insiders_within_week_amplifies_signal(self):
        subs = _submissions([("0001-1", "2024-06-01"), ("0001-2", "2024-06-03")])
        xml = {
            "0001-1": _form4_xml([{"code": "P", "date": "2024-06-01", "shares": self._SHARES, "price": self._PRICE}], owner_cik="0001111111"),
            "0001-2": _form4_xml([{"code": "P", "date": "2024-06-03", "shares": self._SHARES, "price": self._PRICE}], owner_cik="0002222222"),
        }
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=self._ADV):
            clustered = ei.fetch_insider_buying_signal("TEST", "2024-06-15")

        # Same total dollar volume, single insider, no cluster -> lower signal
        subs_solo = _submissions([("0001-1", "2024-06-01")])
        xml_solo = {"0001-1": _form4_xml([
            {"code": "P", "date": "2024-06-01", "shares": self._SHARES * 2, "price": self._PRICE},
        ], owner_cik="0001111111")}
        with _patch_client(subs_solo, xml_solo), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=self._ADV):
            solo = ei.fetch_insider_buying_signal("TEST", "2024-06-15")

        assert clustered["insider_buying_signal"] > solo["insider_buying_signal"]

    def test_same_insider_twice_is_not_a_cluster(self):
        """Cluster amplification requires *distinct* insiders -- one person
        buying twice in a week is not a stronger signal by this metric."""
        subs = _submissions([("0001-1", "2024-06-01"), ("0001-2", "2024-06-03")])
        xml = {
            "0001-1": _form4_xml([{"code": "P", "date": "2024-06-01", "shares": self._SHARES, "price": self._PRICE}], owner_cik="0001111111"),
            "0001-2": _form4_xml([{"code": "P", "date": "2024-06-03", "shares": self._SHARES, "price": self._PRICE}], owner_cik="0001111111"),
        }
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=self._ADV):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")

        expected_ratio = (self._SHARES * self._PRICE * 2) / self._ADV
        expected = ei._squash_to_signal(expected_ratio)
        assert result["insider_buying_signal"] == pytest.approx(round(expected, 3))

    def test_purchases_more_than_a_week_apart_not_clustered(self):
        subs = _submissions([("0001-1", "2024-06-01"), ("0001-2", "2024-06-20")])
        xml = {
            "0001-1": _form4_xml([{"code": "P", "date": "2024-06-01", "shares": self._SHARES, "price": self._PRICE}], owner_cik="0001111111"),
            "0001-2": _form4_xml([{"code": "P", "date": "2024-06-20", "shares": self._SHARES, "price": self._PRICE}], owner_cik="0002222222"),
        }
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=self._ADV):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-25")

        expected_ratio = (self._SHARES * self._PRICE * 2) / self._ADV  # no amplification
        expected = ei._squash_to_signal(expected_ratio)
        assert result["insider_buying_signal"] == pytest.approx(round(expected, 3))


class TestNeverRaisesAndNeutralDefaults:
    def test_no_form4_filings_returns_neutral(self):
        subs = _submissions([])
        with _patch_client(subs, {}):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result == {"insider_buying_signal": 5.0}

    def test_unknown_cik_returns_neutral_not_exception(self):
        with patch.object(EdgarClient, "get_cik", return_value=None):
            result = ei.fetch_insider_buying_signal("0700.HK", "2024-06-15")
        assert result == {"insider_buying_signal": 5.0}

    def test_no_volume_data_returns_neutral(self):
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": _form4_xml([{"code": "P", "date": "2024-06-01", "shares": 10000, "price": 50.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=None):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result == {"insider_buying_signal": 5.0}

    def test_malformed_xml_does_not_raise(self):
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": "<not valid xml"}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=5_000_000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result == {"insider_buying_signal": 5.0}

    def test_submissions_fetch_failure_returns_neutral(self):
        with patch.object(EdgarClient, "get_cik", return_value=320193), \
             patch.object(EdgarClient, "get_submissions", return_value=None):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result == {"insider_buying_signal": 5.0}

    def test_unexpected_exception_returns_neutral(self):
        with patch.object(EdgarClient, "get_cik", side_effect=RuntimeError("boom")):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert result == {"insider_buying_signal": 5.0}

    def test_signal_bounded_to_0_10_even_for_extreme_ratio(self):
        subs = _submissions([("0001-1", "2024-06-01")])
        xml = {"0001-1": _form4_xml([{"code": "P", "date": "2024-06-01", "shares": 10_000_000, "price": 500.0}])}
        with _patch_client(subs, xml), \
             patch.object(ei, "_fetch_avg_daily_dollar_volume", return_value=1000.0):
            result = ei.fetch_insider_buying_signal("TEST", "2024-06-15")
        assert 0.0 <= result["insider_buying_signal"] <= 10.0

    def test_malformed_as_of_date_returns_neutral(self):
        """get_cik runs before date validation inside the try block, so
        this must still not touch the network -- mock it like every other
        test here rather than relying on incidental ordering."""
        with patch.object(EdgarClient, "get_cik", return_value=320193):
            result = ei.fetch_insider_buying_signal("TEST", "not-a-date")
        assert result == {"insider_buying_signal": 5.0}
