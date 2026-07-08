# -*- coding: utf-8 -*-
"""B1 step 3: EDGAR field-level overlay on fetch_market_context().

augur.data._overlay_edgar_fundamentals runs *after* the existing yfinance
-> stooq provider chain, replacing individual fundamentals fields with
EDGAR-sourced values when EDGAR successfully computed them, leaving
everything else (price, sector, rsi, ...) exactly as the provider chain
built it. Not a chain provider itself -- see the function's own docstring
for why "first success wins" chain semantics would be wrong here (EDGAR
only ever has fundamentals, never price/sector/technicals).

Note: tests/conftest.py's disable_edgar_overlay_by_default autouse fixture
stubs fetch_edgar_fundamentals to always return {"insufficient": True} for
every OTHER test in the suite (so a real ticker like "AAPL" doesn't trigger
a real network call). Every test below explicitly re-patches it to exercise
the real overlay behavior.
"""
from unittest.mock import patch

import pytest

from augur import data
from augur.consensus import edgar_fundamentals
from augur.personas.base import MarketContext


def _ctx(**kwargs) -> MarketContext:
    base = {"ticker": "AAPL", "price": 190.0, "pe": 0.0, "roe": 0.0}
    base.update(kwargs)
    return MarketContext(**base)


class TestOverlayAppliesEdgarFields:
    def test_nonzero_edgar_fields_override_existing_values(self):
        ctx = _ctx(pe=999.0, roe=0.01)  # pre-existing yfinance-sourced values
        edgar_result = {
            "pe": 25.5, "pb": 38.0, "roe": 1.5, "gross_margins": 0.47,
            "operating_margins": 0.32, "revenue_growth": 0.06,
            "earnings_growth": 0.19, "debt_ratio": 0.79, "market_cap": 2800000.0,
        }
        with patch.object(edgar_fundamentals, "fetch_edgar_fundamentals", return_value=edgar_result):
            data._overlay_edgar_fundamentals(ctx)

        assert ctx.pe == pytest.approx(25.5)
        assert ctx.roe == pytest.approx(1.5)
        assert ctx.market_cap == pytest.approx(2800000.0)
        assert getattr(ctx, "fundamentals_source", None) == "edgar"

    def test_zero_edgar_fields_leave_yfinance_value_untouched(self):
        """A field EDGAR couldn't compute (its own 0.0 sentinel) must not
        clobber whatever the yfinance/stooq chain already put there."""
        ctx = _ctx(pe=30.0, gross_margins=0.45)
        edgar_result = {
            "pe": 0.0,  # EDGAR couldn't compute this one
            "pb": 0.0, "roe": 1.5, "gross_margins": 0.0,
            "operating_margins": 0.0, "revenue_growth": 0.0,
            "earnings_growth": 0.0, "debt_ratio": 0.0, "market_cap": 0.0,
        }
        with patch.object(edgar_fundamentals, "fetch_edgar_fundamentals", return_value=edgar_result):
            data._overlay_edgar_fundamentals(ctx)

        assert ctx.pe == 30.0        # untouched -- EDGAR had 0.0
        assert ctx.gross_margins == 0.45  # untouched
        assert ctx.roe == pytest.approx(1.5)  # this one WAS overridden

    def test_insufficient_result_is_a_complete_noop(self):
        ctx = _ctx(pe=30.0, roe=0.15)
        with patch.object(edgar_fundamentals, "fetch_edgar_fundamentals", return_value={"insufficient": True}):
            data._overlay_edgar_fundamentals(ctx)

        assert ctx.pe == 30.0
        assert ctx.roe == 0.15
        assert not hasattr(ctx, "fundamentals_source")


class TestOverlaySkipConditions:
    def test_zero_price_skips_edgar_call_entirely(self):
        """No price -> EDGAR can't compute pe/pb/market_cap anyway; must
        not even attempt the (network) call."""
        ctx = _ctx(price=0.0)
        with patch.object(edgar_fundamentals, "fetch_edgar_fundamentals") as mock_fetch:
            data._overlay_edgar_fundamentals(ctx)
        mock_fetch.assert_not_called()

    def test_non_us_ticker_degrades_silently(self):
        """A ticker with no SEC CIK (e.g. a HK stock) must leave the
        context untouched, not raise -- fetch_edgar_fundamentals itself
        already returns insufficient for this case (its own CIK-lookup
        test coverage), this just confirms the overlay caller handles it
        the same way as any other insufficient result."""
        ctx = _ctx(ticker="0700.HK", pe=15.0)
        with patch.object(edgar_fundamentals, "fetch_edgar_fundamentals", return_value={"insufficient": True}):
            data._overlay_edgar_fundamentals(ctx)
        assert ctx.pe == 15.0

    def test_edgar_exception_does_not_propagate(self):
        """Any unexpected exception from the EDGAR path must degrade
        silently -- fetch_market_context's overall result must never be
        broken by an EDGAR-layer bug."""
        ctx = _ctx(pe=30.0)
        with patch.object(edgar_fundamentals, "fetch_edgar_fundamentals", side_effect=RuntimeError("boom")):
            data._overlay_edgar_fundamentals(ctx)  # must not raise
        assert ctx.pe == 30.0


class TestFetchMarketContextIntegration:
    """End-to-end through the real fetch_market_context() entrypoint, with
    the provider chain mocked (matching test_datasources.py's existing
    pattern) and EDGAR explicitly re-enabled for this test only."""

    def test_edgar_overlay_applied_after_provider_chain(self):
        from augur.datasources import YFinanceProvider

        class _FakeYfMock:
            pass

        info = {"symbol": "AAPL", "currentPrice": 190.0, "marketCap": 3_000_000_000_000, "sector": "Technology"}

        def _make_yf_mock(info_dict):
            from unittest.mock import MagicMock
            mock_ticker = MagicMock()
            mock_ticker.info = info_dict
            mock_ticker.history.return_value = MagicMock(empty=True)
            mock_yf = MagicMock()
            mock_yf.Ticker.return_value = mock_ticker
            return mock_yf

        yf_provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock(info))
        edgar_result = {
            "pe": 25.5, "pb": 0.0, "roe": 0.0, "gross_margins": 0.0,
            "operating_margins": 0.0, "revenue_growth": 0.0,
            "earnings_growth": 0.0, "debt_ratio": 0.0, "market_cap": 0.0,
        }

        with patch.object(data, "_get_providers", return_value=[yf_provider]), \
             patch.object(edgar_fundamentals, "fetch_edgar_fundamentals", return_value=edgar_result):
            ctx = data.fetch_market_context("AAPL", force_refresh=True)

        # Price/sector/data_source came from the yfinance chain, untouched.
        assert ctx.price == 190.0
        assert ctx.sector == "Technology"
        assert getattr(ctx, "data_source") == "yfinance"
        # pe was overridden by EDGAR; market_cap (EDGAR returned 0.0) kept
        # the yfinance-derived value.
        assert ctx.pe == pytest.approx(25.5)
        assert ctx.market_cap == pytest.approx(3000.0)
        assert getattr(ctx, "fundamentals_source", None) == "edgar"
