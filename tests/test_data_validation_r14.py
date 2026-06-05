# -*- coding: utf-8 -*-
"""Round 14: tests for augur.data input-validation gaps.

Covers three regressions fixed in this round:

1. ``_normalize_ticker`` / ``fetch_market_context`` crashed with
   ``AttributeError`` when called with a non-string ticker (``None``,
   ``int``, etc.). They now raise / attach a ``data_error`` instead.

2. ``fetch_market_context_batch`` silently iterated over a bare string
   (one MarketContext per character) and raised ``TypeError`` on
   ``None``. It now rejects non-list inputs with a single ``INVALID``
   entry carrying a ``data_error`` describing the misuse.

3. ``search_ticker`` raised uncaught ``ImportError`` when yfinance was
   missing and returned ``[]`` for invalid queries with no
   ``data_error``. It now validates the query, mirrors the rest of the
   module's error UX, and returns a ``_ResultList`` with ``data_error``
   on every failure path.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clean_data_cache():
    from augur import data as data_mod

    data_mod.clear_cache()
    data_mod._providers_cache = None
    yield
    data_mod.clear_cache()
    data_mod._providers_cache = None


# ---------------------------------------------------------------------------
# Gap #1: _normalize_ticker / fetch_market_context reject non-string tickers
# ---------------------------------------------------------------------------


class TestNormalizeTickerTypeValidation:
    """`_normalize_ticker` must reject non-str inputs with ValueError,
    not crash with AttributeError from `ticker.strip()`."""

    def test_normalize_ticker_rejects_none(self):
        from augur.data import _normalize_ticker

        with pytest.raises(ValueError, match="must be a string"):
            _normalize_ticker(None)

    def test_normalize_ticker_rejects_int(self):
        from augur.data import _normalize_ticker

        with pytest.raises(ValueError, match="must be a string"):
            _normalize_ticker(123)

    def test_normalize_ticker_rejects_list(self):
        from augur.data import _normalize_ticker

        with pytest.raises(ValueError, match="must be a string"):
            _normalize_ticker(["AAPL"])

    def test_fetch_market_context_with_none_returns_error_context(self):
        from augur.data import fetch_market_context

        ctx = fetch_market_context(None)
        assert ctx.ticker == "INVALID"
        assert getattr(ctx, "data_source", None) == "error"
        assert "invalid ticker" in ctx.data_error
        assert "NoneType" in ctx.data_error

    def test_fetch_market_context_with_int_returns_error_context(self):
        from augur.data import fetch_market_context

        ctx = fetch_market_context(123)
        assert ctx.ticker == "INVALID"
        assert getattr(ctx, "data_source", None) == "error"
        assert "invalid ticker" in ctx.data_error
        assert "int" in ctx.data_error


# ---------------------------------------------------------------------------
# Gap #2: fetch_market_context_batch validates the tickers argument
# ---------------------------------------------------------------------------


class TestBatchTickerTypeValidation:
    """`fetch_market_context_batch` must not crash on non-list inputs and
    must not silently return per-character contexts when given a bare
    string."""

    def test_batch_with_none_returns_single_invalid_entry(self):
        from augur.data import fetch_market_context_batch

        result = fetch_market_context_batch(None)
        assert list(result.keys()) == ["INVALID"]
        ctx = result["INVALID"]
        assert ctx.data_source == "error"
        assert "expected list" in ctx.data_error
        assert "NoneType" in ctx.data_error

    def test_batch_with_string_returns_single_invalid_entry(self):
        """Regression: previously this iterated over each character and
        returned one context per letter of the ticker string."""
        from augur.data import fetch_market_context_batch

        result = fetch_market_context_batch("AAPL")
        assert list(result.keys()) == ["INVALID"]
        ctx = result["INVALID"]
        assert ctx.data_source == "error"
        assert "expected list" in ctx.data_error
        assert "str" in ctx.data_error

    def test_batch_with_tuple_is_accepted(self):
        from augur.data import fetch_market_context_batch

        # Tuples are acceptable iterables; the function should treat them
        # like lists. With no providers installed the per-ticker fetch will
        # gracefully fall through to the empty-context path.
        result = fetch_market_context_batch(("AAPL",))
        assert "AAPL" in result
        assert result["AAPL"].data_source in ("yfinance", "stooq", "none", "error")

    def test_batch_mixed_valid_and_nonstring_entries(self):
        from augur.data import fetch_market_context_batch

        # 123 is non-string and should be reported as invalid; "AAPL" is fine
        result = fetch_market_context_batch(["AAPL", 123, None])
        # Non-string entries are stringified for the result key so callers
        # can still look them up by their original repr
        assert "123" in result
        assert result["123"].data_source == "error"
        assert "invalid ticker" in result["123"].data_error
        assert "None" in result
        assert result["None"].data_source == "error"
        assert "AAPL" in result


# ---------------------------------------------------------------------------
# Gap #3: search_ticker validates the query and surfaces failure modes
# ---------------------------------------------------------------------------


class TestSearchTickerValidation:
    """`search_ticker` must (a) reject non-str/empty/invalid queries
    with `data_error`, (b) handle yfinance import errors gracefully,
    and (c) attach `data_source` on the success path."""

    def test_search_ticker_rejects_none(self):
        from augur.data import search_ticker

        result = search_ticker(None)
        assert isinstance(result, list)
        assert result == []
        assert result.data_error is not None
        assert "invalid query" in result.data_error
        assert "NoneType" in result.data_error
        assert result.data_source == "error"

    def test_search_ticker_rejects_empty_string(self):
        from augur.data import search_ticker

        result = search_ticker("")
        assert isinstance(result, list)
        assert result == []
        assert "invalid query" in result.data_error
        assert "cannot be empty" in result.data_error

    def test_search_ticker_rejects_invalid_format(self):
        from augur.data import search_ticker

        result = search_ticker("BAD..TICKER")
        assert isinstance(result, list)
        assert result == []
        assert "invalid query" in result.data_error
        assert "consecutive dots" in result.data_error

    def test_search_ticker_yfinance_missing_attaches_error(self):
        from augur.data import search_ticker

        with patch("augur.data._get_yfinance",
                   side_effect=ImportError("yfinance is required")):
            result = search_ticker("AAPL")
        assert isinstance(result, list)
        assert result == []
        assert "yfinance_unavailable" in result.data_error
        assert result.data_source == "error"

    def test_search_ticker_network_error_attaches_error(self):
        from augur.data import search_ticker

        mock_yf = MagicMock()
        mock_t = MagicMock()
        mock_t.info = None
        type(mock_t).info = property(lambda self: (_ for _ in ()).throw(ConnectionError("upstream down")))
        # Use side_effect to raise on .info access
        mock_t = MagicMock()
        mock_t.info = {}
        mock_yf.Ticker.return_value = mock_t
        # Make the .info getter raise
        def _raise():
            raise ConnectionError("upstream down")
        type(mock_t).info = property(lambda self: _raise())

        with patch("augur.data._get_yfinance", return_value=mock_yf):
            result = search_ticker("AAPL")
        assert isinstance(result, list)
        assert "network_error" in result.data_error
        assert "upstream down" in result.data_error
        assert result.data_source == "error"

    def test_search_ticker_returns_list_subclass_on_success(self):
        """On the success path the result must still be a `_ResultList`
        (so callers can rely on `data_source` being set)."""
        from augur.data import search_ticker, _ResultList

        mock_yf = MagicMock()
        mock_t = MagicMock()
        mock_t.info = {
            "symbol": "AAPL",
            "longName": "Apple Inc.",
            "exchange": "NMS",
            "quoteType": "EQUITY",
        }
        mock_yf.Ticker.return_value = mock_t

        with patch("augur.data._get_yfinance", return_value=mock_yf):
            result = search_ticker("AAPL")
        assert isinstance(result, _ResultList)
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result.data_source == "yfinance"
        assert getattr(result, "data_error", None) is None
