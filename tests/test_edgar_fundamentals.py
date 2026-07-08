# -*- coding: utf-8 -*-
"""B1: SEC EDGAR point-in-time fundamentals provider.

Offline, deterministic tests against synthetic ``companyfacts``-shaped JSON
-- no network. Migrated from tests/test_pit_fundamentals.py (P2-4), keeping
every behavioral guarantee that still applies to the new data source (look-
ahead guard, pe/pb/roe/margin arithmetic, YoY growth using two as-of
periods, never-raises), plus new coverage for landmines specific to real
EDGAR XBRL data found during implementation (see edgar_fundamentals.py
module docstring):

  - the same fiscal-year-end period re-appearing in multiple later filings
    as a restated comparative, each with a different (later) filed date --
    the correct "available from" date is the *earliest* filed date, not
    whichever filing happens to be scanned first
  - a company switching XBRL tags mid-history for the same concept (e.g.
    Apple: Revenues -> RevenueFromContractWithCustomerExcludingAssessedTax)
    -- records must be merged across every tag in the family, not "first
    tag with data wins for the whole company"
  - EdgarClient itself: CIK lookup, disk caching (ticker map + companyfacts),
    cache-hit avoiding redundant HTTP calls, the rate limiter
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from augur.consensus import edgar_fundamentals as ef

# Captured at import time, before any fixture (including conftest.py's
# disable_edgar_overlay_by_default) has had a chance to monkeypatch the
# module-level name -- this file's tests exercise fetch_edgar_fundamentals
# itself, so they need the real implementation back regardless of what
# other test files' isolation fixtures do to it.
_REAL_FETCH_EDGAR_FUNDAMENTALS = ef.fetch_edgar_fundamentals


@pytest.fixture(autouse=True)
def _restore_real_fetch_edgar_fundamentals(disable_edgar_overlay_by_default, monkeypatch):
    """Undo conftest.py's global stub for this file only.

    disable_edgar_overlay_by_default (conftest.py) replaces
    edgar_fundamentals.fetch_edgar_fundamentals with an always-insufficient
    stub so tests elsewhere that call the real fetch_market_context() don't
    make a real network call for a ticker like "AAPL". This file's tests
    are testing fetch_edgar_fundamentals directly, so that stub must not
    apply here. Depending on disable_edgar_overlay_by_default by name forces
    pytest to run it first, guaranteeing this fixture's restoration wins.
    """
    monkeypatch.setattr(ef, "fetch_edgar_fundamentals", _REAL_FETCH_EDGAR_FUNDAMENTALS)


@pytest.fixture(autouse=True)
def _reset_client():
    ef.reset_edgar_client()
    yield
    ef.reset_edgar_client()


@pytest.fixture
def tmp_cache_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _rec(end, val, filed, form="10-K", fp="FY", start=None, accn="0000000000-00-000000"):
    r = {"end": end, "val": val, "filed": filed, "form": form, "fp": fp, "accn": accn, "fy": 2024}
    if start:
        r["start"] = start
    return r


def _facts(concept_records: dict, namespace: str = "us-gaap") -> dict:
    """Build a companyfacts-shaped dict. concept_records maps concept tag
    name -> list of record dicts (all placed under a single 'USD' unit,
    matching every concept this module reads)."""
    ns = {tag: {"units": {"USD": records}} for tag, records in concept_records.items()}
    return {"cik": 1, "entityName": "TEST CO", "facts": {namespace: ns}}


def _patch_client_facts(facts: dict):
    """Patch EdgarClient.get_company_facts to return synthetic facts and
    get_cik to succeed, without touching the network."""
    return patch.multiple(
        ef.EdgarClient,
        get_cik=lambda self, ticker: 1,
        get_company_facts=lambda self, ticker: facts,
    )


# ---------------------------------------------------------------------------
# Look-ahead guard (real filed dates, not a guessed lag)
# ---------------------------------------------------------------------------

class TestLookAheadGuard:
    def test_period_not_yet_filed_is_insufficient(self):
        facts = _facts({
            "NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15")],
        })
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-01-01", price=10.0)
        assert result == {"insufficient": True}

    def test_period_available_exactly_on_filed_date(self):
        """filed == as_of_date must be treated as available (the guard is
        <=, not <)."""
        facts = _facts({
            "NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15")],
            "EarningsPerShareDiluted": [_rec("2022-12-31", 2.0, filed="2023-02-15", start="2022-01-01")],
        })
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-02-15", price=10.0)
        assert result.get("insufficient") is not True
        assert result["pe"] == pytest.approx(5.0)  # 10 / 2.0

    def test_period_one_day_before_filed_date_is_insufficient(self):
        facts = _facts({
            "NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15")],
        })
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-02-14", price=10.0)
        assert result == {"insufficient": True}

    def test_no_facts_at_all_is_insufficient(self):
        with _patch_client_facts(_facts({})):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-06-01", price=10.0)
        assert result == {"insufficient": True}

    def test_unknown_cik_is_insufficient(self):
        """A ticker with no SEC CIK (non-US ticker, or a filer that doesn't
        submit XBRL 10-Ks) must degrade cleanly, not raise."""
        with patch.object(ef.EdgarClient, "get_company_facts", return_value=None):
            result = ef.fetch_edgar_fundamentals("0700.HK", "2023-06-01", price=10.0)
        assert result == {"insufficient": True}


# ---------------------------------------------------------------------------
# Fundamentals arithmetic
# ---------------------------------------------------------------------------

class TestFundamentalsArithmetic:
    def _two_period_facts(self):
        return _facts({
            "NetIncomeLoss": [
                _rec("2021-12-31", 80.0, filed="2022-02-15"),
                _rec("2022-12-31", 100.0, filed="2023-02-15"),
            ],
            "RevenueFromContractWithCustomerExcludingAssessedTax": [
                _rec("2021-12-31", 800.0, filed="2022-02-15"),
                _rec("2022-12-31", 1000.0, filed="2023-02-15"),
            ],
            "StockholdersEquity": [
                _rec("2021-12-31", 400.0, filed="2022-02-15"),
                _rec("2022-12-31", 500.0, filed="2023-02-15"),
            ],
            "Assets": [
                _rec("2021-12-31", 700.0, filed="2022-02-15"),
                _rec("2022-12-31", 800.0, filed="2023-02-15"),
            ],
            "Liabilities": [
                _rec("2021-12-31", 280.0, filed="2022-02-15"),
                _rec("2022-12-31", 350.0, filed="2023-02-15"),
            ],
            "GrossProfit": [
                _rec("2021-12-31", 400.0, filed="2022-02-15"),
                _rec("2022-12-31", 500.0, filed="2023-02-15"),
            ],
            "OperatingIncomeLoss": [
                _rec("2021-12-31", 160.0, filed="2022-02-15"),
                _rec("2022-12-31", 200.0, filed="2023-02-15"),
            ],
            "EarningsPerShareDiluted": [
                _rec("2021-12-31", 1.6, filed="2022-02-15", start="2021-01-01"),
                _rec("2022-12-31", 2.0, filed="2023-02-15", start="2022-01-01"),
            ],
            "CommonStockSharesOutstanding": [
                _rec("2021-12-31", 50.0, filed="2022-02-15"),
                _rec("2022-12-31", 50.0, filed="2023-02-15"),
            ],
        })

    def test_pe_pb_roe_computed_from_most_recent_available_period(self):
        facts = self._two_period_facts()
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-04-01", price=20.0)

        assert result["pe"] == pytest.approx(10.0)        # 20 / 2.0
        assert result["pb"] == pytest.approx(2.0)          # 20 / (500/50=10)
        assert result["roe"] == pytest.approx(0.2)         # 100 / 500
        assert result["gross_margins"] == pytest.approx(0.5)       # 500/1000
        assert result["operating_margins"] == pytest.approx(0.2)   # 200/1000
        assert result["debt_ratio"] == pytest.approx(0.4375)       # 350/800 (Liabilities/Assets)
        assert result["market_cap"] == pytest.approx(1000.0)       # 20 * 50

    def test_yoy_growth_uses_two_as_of_available_periods_only(self):
        facts = self._two_period_facts()
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-04-01", price=20.0)

        assert result["revenue_growth"] == pytest.approx(0.25)   # 1000/800 - 1
        assert result["earnings_growth"] == pytest.approx(0.25)  # 100/80 - 1

    def test_yoy_growth_is_zero_when_only_one_period_available(self):
        facts = self._two_period_facts()
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2022-03-01", price=20.0)  # only FY2021 filed

        assert result["revenue_growth"] == 0.0
        assert result["earnings_growth"] == 0.0

    def test_eps_falls_back_to_net_income_over_shares_outstanding(self):
        """No EarningsPerShareDiluted tag at all -> derive from
        net_income / shares_outstanding."""
        facts = _facts({
            "NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15")],
            "CommonStockSharesOutstanding": [_rec("2022-12-31", 50.0, filed="2023-02-15")],
        })
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-06-01", price=20.0)
        # eps = 100/50 = 2.0 -> pe = 20/2 = 10
        assert result["pe"] == pytest.approx(10.0)


class TestQuarterlyWithinAnnualFilingExcluded:
    """Regression test for a real bug found during manual end-to-end
    verification against NVDA's real EDGAR data: form="10-K", fp="FY" alone
    does not reliably mean "the annual duration record" for revenue/income
    concepts. NVDA's FY2015 10-K (filed 2015-03-12) tags a supplementary
    Q4-only figure (start=2014-10-27, end=2015-01-25, ~90 days) with the
    exact same form/fp as the true full-year figure (start=2014-01-27,
    end=2015-01-25, ~363 days) -- both share the same period *end* date.
    Before the fix, this made the ~90-day Q4 record's end date look like a
    second distinct "available period" for YoY comparison purposes,
    producing a nonsense +282% "growth" figure (comparing the full year
    against a single quarter). The duration filter must exclude it.
    """

    def test_short_duration_record_with_same_end_date_is_excluded(self):
        facts = _facts({
            "NetIncomeLoss": [
                # True annual record: ~363 days.
                _rec("2015-01-25", 4681507000.0, filed="2015-03-12", start="2014-01-27"),
                # Supplementary Q4-only record tagged with the SAME
                # form/fp, same end date, but only ~90 days -- must be
                # excluded from annual period selection entirely.
                _rec("2015-01-25", 1250514000.0, filed="2015-03-12", start="2014-10-27"),
                # A real prior annual period for the YoY comparison to
                # land on correctly once the bogus quarterly is excluded.
                _rec("2014-01-26", 4130000000.0, filed="2014-03-13", start="2013-01-28"),
            ],
        })
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2015-06-01", price=10.0)

        # Must compare the two real annual figures, not the annual vs. the
        # smuggled-in quarterly one -- growth is real (~13%), not +282%.
        assert result["earnings_growth"] == pytest.approx(
            (4681507000.0 / 4130000000.0) - 1.0, abs=1e-6
        )
        assert result["earnings_growth"] < 1.0  # sanity bound: not a multi-hundred-percent artifact

    def test_instant_facts_unaffected_by_duration_filter(self):
        """Balance-sheet (instant) concepts have no start date at all --
        the duration filter must not accidentally exclude them."""
        facts = _facts({
            "NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15", start="2022-01-01")],
            "StockholdersEquity": [_rec("2022-12-31", 500.0, filed="2023-02-15")],  # no start
        })
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-06-01", price=10.0)
        assert result["roe"] == pytest.approx(0.2)  # 100/500 -- proves equity value was found


# ---------------------------------------------------------------------------
# EDGAR-specific landmines found against real data during implementation
# ---------------------------------------------------------------------------

class TestRestatementDuplicateHandling:
    """The same fiscal-year-end period is routinely re-reported as a prior-
    year comparative in one or two later annual filings — confirmed against
    real EDGAR data for AAPL (FY2022 first filed 2022-10-28, then
    re-reported in the FY2023 10-K filed 2023-11-03 and the FY2024 10-K
    filed 2024-11-01, all with the identical value). The correct available-
    from date is the *earliest* filed date across all of them."""

    def test_earliest_filed_date_wins_for_restated_period(self):
        facts = _facts({
            "NetIncomeLoss": [
                _rec("2022-12-31", 100.0, filed="2023-02-15"),  # first filing
                _rec("2022-12-31", 100.0, filed="2024-02-15"),  # restated in next year's 10-K
                _rec("2022-12-31", 100.0, filed="2025-02-15"),  # restated again
            ],
        })
        # as_of one day before the *earliest* filed date -> insufficient
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-02-14", price=10.0)
        assert result == {"insufficient": True}

        # as_of on the earliest filed date -> available, even though later
        # restatements of the same period exist with later filed dates
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-02-15", price=10.0)
        assert result.get("insufficient") is not True


class TestTagFamilyMerging:
    """A company can switch XBRL tags for the same concept mid-history
    (confirmed against real AAPL data: Revenues -> RevenueFromContractWith
    CustomerExcludingAssessedTax around FY2019). Periods reported under
    *either* tag must both be visible, not just whichever tag happens to be
    checked first."""

    def test_periods_merged_across_old_and_new_revenue_tags(self):
        facts = _facts({
            "NetIncomeLoss": [
                _rec("2018-12-31", 80.0, filed="2019-02-15"),
                _rec("2022-12-31", 100.0, filed="2023-02-15"),
            ],
            # Old period reported under the deprecated tag...
            "Revenues": [
                _rec("2018-12-31", 800.0, filed="2019-02-15"),
            ],
            # ...new period reported under the tag the company switched to.
            "RevenueFromContractWithCustomerExcludingAssessedTax": [
                _rec("2022-12-31", 1000.0, filed="2023-02-15"),
            ],
        })
        # Old period, old tag -> must resolve, not silently miss because
        # the new tag was checked and had nothing for this date.
        with _patch_client_facts(facts):
            old = ef.fetch_edgar_fundamentals("TEST", "2019-06-01", price=10.0)
        assert old.get("insufficient") is not True
        assert old["revenue_growth"] == 0.0  # only one period available -> fine

        # New period, new tag -> must also resolve.
        with _patch_client_facts(facts):
            new = ef.fetch_edgar_fundamentals("TEST", "2023-06-01", price=10.0)
        assert new.get("insufficient") is not True
        assert new["gross_margins"] == 0.0  # no GrossProfit tag supplied, stays 0 not raised


# ---------------------------------------------------------------------------
# Never raises
# ---------------------------------------------------------------------------

class TestNeverRaises:
    def test_malformed_as_of_date_returns_insufficient_not_exception(self):
        result = ef.fetch_edgar_fundamentals("TEST", "not-a-date", price=10.0)
        assert result == {"insufficient": True}

    def test_unexpected_exception_in_fetch_is_swallowed(self):
        with patch.object(ef.EdgarClient, "get_company_facts", side_effect=RuntimeError("boom")):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-06-01", price=10.0)
        assert result == {"insufficient": True}

    def test_non_positive_price_is_insufficient(self):
        facts = _facts({"NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15")]})
        with _patch_client_facts(facts):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-06-01", price=0.0)
        assert result == {"insufficient": True}

    def test_missing_price_falls_back_to_fetch_history(self):
        facts = _facts({"NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15")]})
        fake_history = [{"date": "2023-05-01", "close": 15.0}, {"date": "2023-06-01", "close": 20.0}]
        with _patch_client_facts(facts), patch("augur.data.fetch_history", return_value=fake_history):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-06-01", price=None)
        assert result.get("insufficient") is not True

    def test_fetch_history_failure_with_no_price_is_insufficient(self):
        facts = _facts({"NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15")]})
        with _patch_client_facts(facts), patch("augur.data.fetch_history", side_effect=RuntimeError("network down")):
            result = ef.fetch_edgar_fundamentals("TEST", "2023-06-01", price=None)
        assert result == {"insufficient": True}


# ---------------------------------------------------------------------------
# EdgarClient: CIK lookup, disk caching, rate limiting
# ---------------------------------------------------------------------------

class TestEdgarClientCikLookup:
    def test_get_cik_returns_known_ticker(self, tmp_cache_dir):
        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        raw_map = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        with patch.object(client, "_http_get_json", return_value=raw_map):
            cik = client.get_cik("AAPL")
        assert cik == 320193

    def test_get_cik_unknown_ticker_returns_none(self, tmp_cache_dir):
        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        raw_map = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        with patch.object(client, "_http_get_json", return_value=raw_map):
            cik = client.get_cik("0700.HK")
        assert cik is None

    def test_get_cik_case_insensitive(self, tmp_cache_dir):
        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        raw_map = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        with patch.object(client, "_http_get_json", return_value=raw_map):
            assert client.get_cik("aapl") == 320193

    def test_ticker_map_http_failure_returns_empty_not_raises(self, tmp_cache_dir):
        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        with patch.object(client, "_http_get_json", return_value=None):
            cik = client.get_cik("AAPL")
        assert cik is None


class TestEdgarClientCaching:
    def test_ticker_map_persisted_to_disk(self, tmp_cache_dir):
        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        raw_map = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        with patch.object(client, "_http_get_json", return_value=raw_map) as mock_get:
            client.get_cik("AAPL")
        assert (tmp_cache_dir / "company_tickers.json").exists()
        assert mock_get.call_count == 1

    def test_second_client_instance_uses_disk_cache_not_http(self, tmp_cache_dir):
        """A fresh EdgarClient (new process simulation) must read the warm
        disk cache instead of re-fetching."""
        client1 = ef.EdgarClient(cache_dir=tmp_cache_dir)
        raw_map = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        with patch.object(client1, "_http_get_json", return_value=raw_map):
            client1.get_cik("AAPL")

        client2 = ef.EdgarClient(cache_dir=tmp_cache_dir)
        with patch.object(client2, "_http_get_json") as mock_get2:
            cik = client2.get_cik("AAPL")
        assert cik == 320193
        mock_get2.assert_not_called()

    def test_stale_ticker_map_cache_is_refetched(self, tmp_cache_dir):
        cache_path = tmp_cache_dir / "company_tickers.json"
        tmp_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"0": {"cik_str": 1, "ticker": "OLD", "title": "Old Co"}}), encoding="utf-8")
        # Backdate the file beyond the TTL.
        stale_time = time.time() - ef._TICKER_MAP_TTL_SECONDS - 3600
        import os
        os.utime(cache_path, (stale_time, stale_time))

        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        fresh_map = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        with patch.object(client, "_http_get_json", return_value=fresh_map) as mock_get:
            cik = client.get_cik("AAPL")
        assert cik == 320193
        mock_get.assert_called_once()

    def test_companyfacts_cached_avoids_redundant_http(self, tmp_cache_dir):
        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        facts = _facts({"NetIncomeLoss": [_rec("2022-12-31", 100.0, filed="2023-02-15")]})
        with patch.object(client, "get_cik", return_value=320193), \
             patch.object(client, "_http_get_json", return_value=facts) as mock_get:
            client.get_company_facts("AAPL")
            client.get_company_facts("AAPL")
        assert mock_get.call_count == 1

    def test_companyfacts_http_failure_with_no_cache_returns_none(self, tmp_cache_dir):
        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        with patch.object(client, "get_cik", return_value=320193), \
             patch.object(client, "_http_get_json", return_value=None):
            result = client.get_company_facts("AAPL")
        assert result is None

    def test_companyfacts_unknown_ticker_returns_none_without_http(self, tmp_cache_dir):
        client = ef.EdgarClient(cache_dir=tmp_cache_dir)
        with patch.object(client, "get_cik", return_value=None), \
             patch.object(client, "_http_get_json") as mock_get:
            result = client.get_company_facts("0700.HK")
        assert result is None
        mock_get.assert_not_called()


class TestEdgarClientRateLimiter:
    def test_token_bucket_allows_burst_up_to_rate(self):
        bucket = ef._TokenBucket(rate=10.0)
        start = time.monotonic()
        for _ in range(10):
            bucket.acquire()
        elapsed = time.monotonic() - start
        # 10 tokens available immediately (bucket starts full) -> should be fast.
        assert elapsed < 0.5

    def test_token_bucket_throttles_beyond_rate(self):
        bucket = ef._TokenBucket(rate=10.0)
        for _ in range(10):
            bucket.acquire()
        start = time.monotonic()
        bucket.acquire()  # 11th request within the same second must wait
        elapsed = time.monotonic() - start
        assert elapsed > 0.05


class TestContactEmailResolution:
    def test_uses_env_var_when_set(self, monkeypatch):
        monkeypatch.setenv("AUGUR_EDGAR_CONTACT_EMAIL", "real@example.com")
        assert ef.EdgarClient._resolve_contact_email() == "real@example.com"

    def test_falls_back_to_placeholder_when_unset(self, monkeypatch):
        monkeypatch.delenv("AUGUR_EDGAR_CONTACT_EMAIL", raising=False)
        assert ef.EdgarClient._resolve_contact_email() == ef._DEFAULT_CONTACT_EMAIL
