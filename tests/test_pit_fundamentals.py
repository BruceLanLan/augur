# -*- coding: utf-8 -*-
"""P2-4: point-in-time fundamentals provider (``augur.consensus.pit_fundamentals``).

Offline, deterministic tests against synthetic ``financials``/``balance_sheet``
DataFrames -- no network. Covers:
  - the look-ahead guard (90-day filing lag),
  - the boundary date exactly at the lag,
  - pe/pb/roe/margin arithmetic,
  - YoY growth using two as-of-available periods,
  - the "insufficient" (not zero-filled) result when no period qualifies,
  - yfinance's NaN-padded oldest-retained column being correctly excluded
    from "available" rather than producing a false all-zero result,
  - the retry-then-cache behavior when the first fetch transiently returns
    an empty DataFrame.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from augur.consensus import pit_fundamentals as pf


@pytest.fixture(autouse=True)
def _clear_cache():
    pf.clear_pit_cache()
    yield
    pf.clear_pit_cache()


def _make_financials(periods_and_rows: dict) -> pd.DataFrame:
    """Build a ``financials``-shaped DataFrame: rows are line items, columns
    are period-end Timestamps. ``periods_and_rows`` maps period_end (str) ->
    {row_name: value}."""
    columns = [pd.Timestamp(p) for p in periods_and_rows]
    all_rows = sorted({row for rows in periods_and_rows.values() for row in rows})
    data = {}
    for p, rows in periods_and_rows.items():
        col = pd.Timestamp(p)
        data[col] = [rows.get(row, float("nan")) for row in all_rows]
    df = pd.DataFrame(data, index=all_rows)
    return df


def _mock_ticker(financials: pd.DataFrame, balance_sheet: pd.DataFrame):
    mock_tk = MagicMock()
    mock_tk.financials = financials
    mock_tk.balance_sheet = balance_sheet
    return mock_tk


class TestLookAheadGuard:
    def test_period_not_yet_available_is_insufficient(self):
        """A period ending 2022-12-31 is not as-of available on 2023-01-01 --
        the 90-day filing lag means it isn't "filed" until ~2023-03-31."""
        financials = _make_financials({
            "2022-12-31": {"Net Income": 100.0, "Total Revenue": 1000.0,
                            "Diluted EPS": 2.0, "Diluted Average Shares": 50.0},
        })
        balance_sheet = _make_financials({
            "2022-12-31": {"Stockholders Equity": 500.0, "Ordinary Shares Number": 50.0,
                            "Total Debt": 100.0, "Total Assets": 800.0},
        })
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", "2023-01-01", price=10.0)
        assert result == {"insufficient": True}

    def test_period_available_exactly_at_90_day_boundary(self):
        """period_end + 90 days == as_of_date must be treated as available
        (the guard is ``<=``, not ``<``)."""
        period_end = pd.Timestamp("2022-12-31")
        as_of = (period_end + pd.Timedelta(days=90)).strftime("%Y-%m-%d")
        financials = _make_financials({
            "2022-12-31": {"Net Income": 100.0, "Total Revenue": 1000.0,
                            "Diluted EPS": 2.0, "Diluted Average Shares": 50.0},
        })
        balance_sheet = _make_financials({
            "2022-12-31": {"Stockholders Equity": 500.0, "Ordinary Shares Number": 50.0,
                            "Total Debt": 100.0, "Total Assets": 800.0},
        })
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", as_of, price=10.0)
        assert result.get("insufficient") is not True
        assert result["pe"] == pytest.approx(5.0)  # price 10 / eps 2

    def test_period_one_day_before_90_day_boundary_is_insufficient(self):
        period_end = pd.Timestamp("2022-12-31")
        as_of = (period_end + pd.Timedelta(days=89)).strftime("%Y-%m-%d")
        financials = _make_financials({
            "2022-12-31": {"Net Income": 100.0, "Total Revenue": 1000.0,
                            "Diluted EPS": 2.0, "Diluted Average Shares": 50.0},
        })
        balance_sheet = _make_financials({
            "2022-12-31": {"Stockholders Equity": 500.0, "Ordinary Shares Number": 50.0},
        })
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", as_of, price=10.0)
        assert result == {"insufficient": True}

    def test_no_statements_at_all_is_insufficient(self):
        with patch("yfinance.Ticker", return_value=_mock_ticker(pd.DataFrame(), pd.DataFrame())):
            result = pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=10.0)
        assert result == {"insufficient": True}


class TestFundamentalsArithmetic:
    def _two_period_statements(self):
        financials = _make_financials({
            "2021-12-31": {"Net Income": 80.0, "Total Revenue": 800.0,
                            "Diluted EPS": 1.6, "Diluted Average Shares": 50.0,
                            "Gross Profit": 400.0, "Operating Income": 160.0},
            "2022-12-31": {"Net Income": 100.0, "Total Revenue": 1000.0,
                            "Diluted EPS": 2.0, "Diluted Average Shares": 50.0,
                            "Gross Profit": 500.0, "Operating Income": 200.0},
        })
        balance_sheet = _make_financials({
            "2021-12-31": {"Stockholders Equity": 400.0, "Ordinary Shares Number": 50.0,
                            "Total Debt": 80.0, "Total Assets": 700.0},
            "2022-12-31": {"Stockholders Equity": 500.0, "Ordinary Shares Number": 50.0,
                            "Total Debt": 100.0, "Total Assets": 800.0},
        })
        return financials, balance_sheet

    def test_pe_pb_roe_computed_from_most_recent_available_period(self):
        financials, balance_sheet = self._two_period_statements()
        as_of = "2023-04-01"  # both periods as-of available; 2022-12-31 is most recent
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", as_of, price=20.0)

        assert result["pe"] == pytest.approx(10.0)        # 20 / 2.0
        assert result["pb"] == pytest.approx(2.0)          # 20 / (500/50=10)
        assert result["roe"] == pytest.approx(0.2)         # 100 / 500
        assert result["gross_margins"] == pytest.approx(0.5)       # 500/1000
        assert result["operating_margins"] == pytest.approx(0.2)   # 200/1000
        assert result["debt_ratio"] == pytest.approx(0.125)        # 100/800
        assert result["market_cap"] == pytest.approx(1000.0)       # 20 * 50

    def test_yoy_growth_uses_two_as_of_available_periods_only(self):
        financials, balance_sheet = self._two_period_statements()
        as_of = "2023-04-01"
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", as_of, price=20.0)

        # revenue: 1000 / 800 - 1 = 0.25 ; earnings: 100 / 80 - 1 = 0.25
        assert result["revenue_growth"] == pytest.approx(0.25)
        assert result["earnings_growth"] == pytest.approx(0.25)

    def test_yoy_growth_is_zero_when_only_one_period_available(self):
        financials, balance_sheet = self._two_period_statements()
        as_of = "2022-04-01"  # only 2021-12-31 is as-of available
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", as_of, price=20.0)

        assert result["revenue_growth"] == 0.0
        assert result["earnings_growth"] == 0.0

    def test_eps_falls_back_to_net_income_over_diluted_shares(self):
        financials = _make_financials({
            "2022-12-31": {"Net Income": 100.0, "Total Revenue": 1000.0,
                            "Diluted Average Shares": 50.0},  # no "Diluted EPS" row
        })
        balance_sheet = _make_financials({
            "2022-12-31": {"Stockholders Equity": 500.0, "Ordinary Shares Number": 50.0},
        })
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=20.0)
        # eps = 100/50 = 2.0 -> pe = 20/2 = 10
        assert result["pe"] == pytest.approx(10.0)


class TestNaNPaddedOldestColumnGuard:
    """Regression test for the bug found during P2-4 OOS validation: yfinance
    pads its oldest retained annual column with NaN once it ages out of full
    retention. Before the fix, ``_available_periods`` treated that column as
    "available" purely because the column label passed the date guard, and
    every downstream field silently fell through to its 0.0 default --
    producing a *successful-looking* all-zero result instead of correctly
    flagging the day as insufficient. This is the null-by-construction
    failure mode the whole module exists to prevent.
    """

    def test_nan_only_column_is_not_treated_as_available(self):
        financials = _make_financials({
            "2022-01-31": {},  # every row NaN for this period -- the padded column
        })
        balance_sheet = _make_financials({
            "2022-01-31": {},
        })
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=10.0)
        # Must be insufficient, NOT a "successful" all-zero result.
        assert result == {"insufficient": True}

    def test_nan_only_oldest_column_excluded_but_real_newer_column_used(self):
        financials = _make_financials({
            "2022-01-31": {},  # NaN-padded, must be excluded
            "2023-01-31": {"Net Income": 50.0, "Total Revenue": 500.0,
                            "Diluted EPS": 1.0, "Diluted Average Shares": 50.0},
        })
        balance_sheet = _make_financials({
            "2022-01-31": {},
            "2023-01-31": {"Stockholders Equity": 250.0, "Ordinary Shares Number": 50.0},
        })
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=10.0)
        assert result.get("insufficient") is not True
        assert result["pe"] == pytest.approx(10.0)  # 10 / 1.0
        # Only one real period is as-of available -> growth fields are 0.0,
        # not computed against the NaN-padded column.
        assert result["revenue_growth"] == 0.0
        assert result["earnings_growth"] == 0.0


class TestStatementCacheRetry:
    """Regression test for the second bug found during P2-4 OOS validation:
    yfinance has been observed to transiently return an empty DataFrame for
    a ticker that has real, retrievable data on a later call within the same
    process. The old caching logic accepted and permanently cached whatever
    the *first* call returned, including a transiently-empty bad response.
    """

    def test_empty_first_fetch_retries_and_uses_later_nonempty_result(self):
        real_financials = _make_financials({
            "2022-12-31": {"Net Income": 100.0, "Total Revenue": 1000.0,
                            "Diluted EPS": 2.0, "Diluted Average Shares": 50.0},
        })
        real_balance_sheet = _make_financials({
            "2022-12-31": {"Stockholders Equity": 500.0, "Ordinary Shares Number": 50.0},
        })

        call_count = {"n": 0}

        def _ticker_factory(_symbol):
            call_count["n"] += 1
            mock_tk = MagicMock()
            if call_count["n"] == 1:
                # First attempt: transiently empty, as observed with real yfinance.
                mock_tk.financials = pd.DataFrame()
                mock_tk.balance_sheet = pd.DataFrame()
            else:
                mock_tk.financials = real_financials
                mock_tk.balance_sheet = real_balance_sheet
            return mock_tk

        with patch("yfinance.Ticker", side_effect=_ticker_factory):
            result = pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=20.0)

        assert call_count["n"] >= 2, "must retry after an empty first fetch"
        assert result.get("insufficient") is not True
        assert result["pe"] == pytest.approx(10.0)

    def test_persistently_empty_fetch_is_cached_as_insufficient_after_retries(self):
        def _ticker_factory(_symbol):
            mock_tk = MagicMock()
            mock_tk.financials = pd.DataFrame()
            mock_tk.balance_sheet = pd.DataFrame()
            return mock_tk

        with patch("yfinance.Ticker", side_effect=_ticker_factory) as mock_ctor:
            result = pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=20.0)
            calls_after_first = mock_ctor.call_count
            # A second call for the same ticker must use the cache, not
            # trigger a fresh round of retries.
            pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=20.0)
            assert mock_ctor.call_count == calls_after_first

        assert result == {"insufficient": True}

    def test_successful_fetch_is_cached_and_not_retried_on_subsequent_calls(self):
        real_financials = _make_financials({
            "2022-12-31": {"Net Income": 100.0, "Total Revenue": 1000.0,
                            "Diluted EPS": 2.0, "Diluted Average Shares": 50.0},
        })
        real_balance_sheet = _make_financials({
            "2022-12-31": {"Stockholders Equity": 500.0, "Ordinary Shares Number": 50.0},
        })

        with patch("yfinance.Ticker", return_value=_mock_ticker(real_financials, real_balance_sheet)) as mock_ctor:
            pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=20.0)
            first_call_count = mock_ctor.call_count
            pf.fetch_pit_fundamentals("TEST", "2023-07-01", price=21.0)
            # Statements are cached per-ticker -- a second as-of date for the
            # same ticker must not re-fetch.
            assert mock_ctor.call_count == first_call_count


class TestNeverRaises:
    def test_malformed_as_of_date_returns_insufficient_not_exception(self):
        result = pf.fetch_pit_fundamentals("TEST", "not-a-date", price=10.0)
        assert result == {"insufficient": True}

    def test_unexpected_exception_in_fetch_is_swallowed(self):
        with patch("yfinance.Ticker", side_effect=RuntimeError("boom")):
            result = pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=10.0)
        assert result == {"insufficient": True}

    def test_non_positive_price_is_insufficient(self):
        financials = _make_financials({
            "2022-12-31": {"Net Income": 100.0, "Total Revenue": 1000.0,
                            "Diluted EPS": 2.0, "Diluted Average Shares": 50.0},
        })
        balance_sheet = _make_financials({
            "2022-12-31": {"Stockholders Equity": 500.0, "Ordinary Shares Number": 50.0},
        })
        with patch("yfinance.Ticker", return_value=_mock_ticker(financials, balance_sheet)):
            result = pf.fetch_pit_fundamentals("TEST", "2023-06-01", price=0.0)
        assert result == {"insufficient": True}
