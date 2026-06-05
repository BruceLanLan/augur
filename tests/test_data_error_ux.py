# -*- coding: utf-8 -*-
"""Tests for augur.data user-visible error UX (round 7).

Background: data fetching had multiple silent-failure paths (empty data,
network error, malformed response, yfinance missing). This suite covers
the ``data_error`` field added to :func:`fetch_market_context`,
:func:`fetch_history`, :func:`fetch_market_overview`, :func:`fetch_hot_tickers`,
and :func:`fetch_market_context_batch` so callers can distinguish failure
modes rather than just observing ``data_source=='none'`` or an empty list.
"""

import importlib
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _clean_data_cache():
    """Reset the in-process data cache and provider chain between tests."""
    from augur import data as data_mod

    data_mod.clear_cache()
    data_mod._providers_cache = None
    yield
    data_mod.clear_cache()
    data_mod._providers_cache = None


def _stub_provider_chain(monkeypatch, providers):
    """Install a custom provider chain on augur.data."""
    from augur import data as data_mod

    monkeypatch.setattr(data_mod, "_providers_cache", list(providers))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_provider(name):
    """Provider that returns an empty dict for any ticker (silent failure)."""

    class _P(data_mod := importlib.import_module("augur.datasources.base").DataProvider):
        def fetch(self, ticker):  # type: ignore[override]
            return {}

    p = _P()
    p.name = name
    return p


def _raising_provider(name, exc=None):
    """Provider that raises on every fetch (simulates network error)."""
    from augur.datasources.base import DataProvider, DataProviderError

    class _P(DataProvider):
        def fetch(self, ticker):  # type: ignore[override]
            raise (exc or DataProviderError(f"{name} network error"))

    p = _P()
    p.name = name
    return p


def _ok_provider(name, fields=None):
    """Provider that returns a minimal valid MarketContext dict."""
    from augur.datasources.base import DataProvider

    class _P(DataProvider):
        def fetch(self, ticker):  # type: ignore[override]
            payload = {"data_source": name, "ticker": ticker.upper()}
            payload.update(fields or {"price": 100.0})
            return payload

    p = _P()
    p.name = name
    return p


# ---------------------------------------------------------------------------
# Silent failure #1: fetch_history returns [] for many distinct reasons
# ---------------------------------------------------------------------------


class TestFetchHistoryErrorUX:
    """fetch_history previously returned [] for: invalid ticker, missing
    yfinance, network error, empty history. All four are now distinguishable
    via the ``data_error`` attribute on the returned ``_ResultList``."""

    def test_invalid_ticker_attaches_error(self):
        from augur.data import fetch_history

        result = fetch_history("")
        assert isinstance(result, list)
        assert result == []
        assert result.data_error is not None
        assert "invalid ticker" in result.data_error

    def test_yfinance_missing_attaches_error(self):
        from augur.data import fetch_history

        with patch("augur.data._get_yfinance",
                   side_effect=ImportError("yfinance is required")):
            result = fetch_history("AAPL", force_refresh=True)
        assert result == []
        assert "yfinance_unavailable" in result.data_error
        assert "yfinance is required" in result.data_error

    def test_network_error_attaches_error(self):
        from augur.data import fetch_history

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = ConnectionError("upstream down")
        mock_yf.Ticker.return_value = mock_ticker

        with patch("augur.data._get_yfinance", return_value=mock_yf):
            result = fetch_history("AAPL", force_refresh=True)
        assert result == []
        assert "network_error" in result.data_error
        assert "upstream down" in result.data_error

    def test_empty_dataframe_attaches_error(self):
        """Empty DataFrame from yfinance is a distinct failure from network
        error; the message should make that clear."""
        from augur.data import fetch_history

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        empty_df = pd.DataFrame()  # empty, not None
        mock_ticker.history.return_value = empty_df
        mock_yf.Ticker.return_value = mock_ticker

        with patch("augur.data._get_yfinance", return_value=mock_yf):
            result = fetch_history("ZZZZZ", period="1y", force_refresh=True)
        assert result == []
        assert "no_data" in result.data_error
        assert "ZZZZZ" in result.data_error

    def test_successful_history_has_no_data_error(self):
        from augur.data import fetch_history

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        dates = pd.date_range(end="2024-01-30", periods=5, freq="B")
        prices = [100.0 + i for i in range(5)]
        hist_df = pd.DataFrame({
            "Open": prices,
            "High": [p + 1 for p in prices],
            "Low": [p - 1 for p in prices],
            "Close": prices,
            "Volume": [1_000_000] * 5,
        }, index=dates)
        mock_ticker.history.return_value = hist_df
        mock_yf.Ticker.return_value = mock_ticker

        with patch("augur.data._get_yfinance", return_value=mock_yf):
            result = fetch_history("AAPL", force_refresh=True)
        assert len(result) == 5
        assert getattr(result, "data_error", None) is None


# ---------------------------------------------------------------------------
# Silent failure #2: _build_context_from_providers aggregates per-provider errors
# ---------------------------------------------------------------------------


class TestMarketContextErrorUX:
    """When every provider in the chain fails, MarketContext gets a
    ``data_error`` that lists the per-provider reason. Success path leaves
    ``data_error`` unset."""

    def test_invalid_ticker_sets_data_error(self):
        from augur.data import fetch_market_context

        ctx = fetch_market_context("INVALID..TICKER")
        assert ctx.data_source == "error"
        assert getattr(ctx, "data_error", None) is not None
        assert "invalid ticker" in ctx.data_error

    def test_all_providers_empty_sets_aggregated_error(self, monkeypatch):
        from augur.data import fetch_market_context

        _stub_provider_chain(
            monkeypatch,
            [_empty_provider("yfinance"), _empty_provider("stooq")],
        )
        ctx = fetch_market_context("AAPL", force_refresh=True)
        assert ctx.data_source == "none"
        err = getattr(ctx, "data_error", "")
        assert "all providers failed" in err
        assert "yfinance" in err
        assert "stooq" in err

    def test_all_providers_raise_sets_aggregated_error(self, monkeypatch):
        from augur.datasources.base import DataProviderError
        from augur.data import fetch_market_context

        _stub_provider_chain(
            monkeypatch,
            [
                _raising_provider("yfinance", DataProviderError("boom")),
                _raising_provider("stooq", DataProviderError("kapow")),
            ],
        )
        ctx = fetch_market_context("AAPL", force_refresh=True)
        assert ctx.data_source == "none"
        err = getattr(ctx, "data_error", "")
        assert "boom" in err and "kapow" in err

    def test_successful_provider_has_no_data_error(self, monkeypatch):
        from augur.data import fetch_market_context

        _stub_provider_chain(monkeypatch, [_ok_provider("yfinance", {"price": 150.0})])
        ctx = fetch_market_context("AAPL", force_refresh=True)
        assert ctx.data_source == "yfinance"
        assert getattr(ctx, "data_error", None) is None

    def test_batch_invalid_ticker_sets_data_error(self, monkeypatch):
        from augur.data import fetch_market_context_batch

        _stub_provider_chain(monkeypatch, [_ok_provider("yfinance", {"price": 1.0})])
        result = fetch_market_context_batch(["AAPL", "BAD..TICKER"])
        assert result["AAPL"].data_source == "yfinance"
        assert result["BAD..TICKER"].data_source == "error"
        assert "invalid ticker" in result["BAD..TICKER"].data_error


# ---------------------------------------------------------------------------
# Silent failure #3: fetch_market_overview & fetch_hot_tickers now expose data_error
# ---------------------------------------------------------------------------


class TestMarketOverviewAndHotTickersErrorUX:
    """``fetch_market_overview`` and ``fetch_hot_tickers`` previously swallowed
    yfinance import errors and per-instrument network errors. They now set a
    ``data_error`` field so the dashboard can surface a helpful message."""

    def test_market_overview_yfinance_missing_attaches_error(self):
        from augur.data import fetch_market_overview

        with patch("augur.data._get_yfinance",
                   side_effect=ImportError("yfinance missing")):
            result = fetch_market_overview(force_refresh=True)
        assert result["source"] == "none"
        assert result["items"] == []
        assert "yfinance_unavailable" in result["data_error"]

    def test_market_overview_partial_failure_attaches_error(self):
        """When some instruments fail, the result must indicate that."""
        from augur.data import fetch_market_overview

        mock_yf = MagicMock()
        # 2 of the 15 instruments will raise -> partial
        call_count = {"n": 0}

        def _ticker_factory(symbol):
            mock_t = MagicMock()
            call_count["n"] += 1
            if call_count["n"] % 5 == 0:
                mock_t.fast_info = None
                mock_t.history.side_effect = ConnectionError("net")
            else:
                mock_fi = MagicMock()
                mock_fi.last_price = 100.0
                mock_fi.previous_close = 99.0
                mock_fi.currency = "USD"
                mock_t.fast_info = mock_fi
            return mock_t

        mock_yf.Ticker.side_effect = _ticker_factory

        with patch("augur.data._get_yfinance", return_value=mock_yf):
            result = fetch_market_overview(force_refresh=True)
        assert result["source"] == "partial"
        assert "data_error" in result
        assert "instruments failed" in result["data_error"]
        assert "partial data" in result["data_error"]

    def test_hot_tickers_yfinance_missing_attaches_error(self):
        from augur.data import fetch_hot_tickers

        with patch("augur.data._get_yfinance",
                   side_effect=ImportError("yfinance missing")):
            result = fetch_hot_tickers(force_refresh=True)
        assert isinstance(result, list)  # backward compat
        assert result == []
        assert result.data_error is not None
        assert "yfinance_unavailable" in result.data_error
        assert result.data_source == "error"

    def test_hot_tickers_partial_failure_attaches_error(self):
        from augur.data import fetch_hot_tickers

        mock_yf = MagicMock()
        # First ticker raises; rest succeed
        def _factory(symbol):
            mock_t = MagicMock()
            if symbol == "AAPL":
                mock_t.fast_info = None
                mock_t.history.side_effect = ConnectionError("net")
            else:
                mock_fi = MagicMock()
                mock_fi.last_price = 200.0
                mock_fi.previous_close = 198.0
                mock_fi.market_cap = 1e12
                mock_fi.currency = "USD"
                mock_t.fast_info = mock_fi
            return mock_t

        mock_yf.Ticker.side_effect = _factory

        with patch("augur.data._get_yfinance", return_value=mock_yf):
            result = fetch_hot_tickers(force_refresh=True)
        assert isinstance(result, list)
        assert len(result) == 10  # all 10 slots
        assert getattr(result, "data_error", None) is not None
        assert "AAPL" in result.data_error
        assert "1/10" in result.data_error

    def test_hot_tickers_full_success_has_no_data_error(self):
        from augur.data import fetch_hot_tickers

        mock_yf = MagicMock()
        mock_t = MagicMock()
        mock_fi = MagicMock()
        mock_fi.last_price = 100.0
        mock_fi.previous_close = 99.0
        mock_fi.market_cap = 5e11
        mock_fi.currency = "USD"
        mock_t.fast_info = mock_fi
        mock_yf.Ticker.return_value = mock_t

        with patch("augur.data._get_yfinance", return_value=mock_yf):
            result = fetch_hot_tickers(force_refresh=True)
        assert isinstance(result, list)
        assert len(result) == 10
        assert getattr(result, "data_error", None) is None
        assert getattr(result, "data_source", None) == "yfinance"

    def test_result_list_is_a_list_subclass(self):
        """Backward-compat: _ResultList must behave like a list for callers
        that don't know about the data_error attribute."""
        from augur.data import _ResultList

        rl = _ResultList()
        rl.append({"a": 1})
        assert isinstance(rl, list)
        assert len(rl) == 1
        assert rl[0] == {"a": 1}
        assert rl.data_error is None
