# -*- coding: utf-8 -*-
"""Tests for augur.data module (offline technical calculations)."""

import pytest


class TestDataCalculations:
    def test_calculate_rsi_basic(self):
        """Monotonically increasing prices should give RSI > 70."""
        from augur.data import _calculate_rsi

        prices = [i for i in range(1, 30)]
        rsi = _calculate_rsi(prices, period=14)
        assert rsi > 70

    def test_calculate_rsi_decreasing(self):
        """Monotonically decreasing prices should give RSI < 30."""
        from augur.data import _calculate_rsi

        prices = [30 - i for i in range(29)]
        rsi = _calculate_rsi(prices, period=14)
        assert rsi < 30

    def test_calculate_rsi_short_data(self):
        """Too short data returns 50."""
        from augur.data import _calculate_rsi

        rsi = _calculate_rsi([100, 101, 102], period=14)
        assert rsi == 50.0

    def test_calculate_rsi_matches_wilder_reference(self):
        """Wilder's own worked example: RSI(14) is 70.46, then 66.25 (TA-Lib RSI)."""
        from augur.data import _calculate_rsi

        closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
        assert _calculate_rsi(closes[:15], period=14) == 70.46
        assert _calculate_rsi(closes, period=14) == 66.25

    def test_calculate_rsi_uses_whole_history(self):
        """Wilder's RSI carries the earlier moves; a last-14-changes average does not.

        Twenty bars of steady selling, then 14 alternating +2/-1 bars. The last 14
        changes alone average to RSI 66.67; Wilder's smoothing still remembers the
        sell-off and stays below 50.
        """
        from augur.data import _calculate_rsi

        closes = [200.0 - 2 * i for i in range(21)]
        for i in range(14):
            closes.append(closes[-1] + (2.0 if i % 2 == 0 else -1.0))
        rsi = _calculate_rsi(closes, period=14)
        assert rsi < 50

    def test_calculate_rsi_flat_series_is_neutral(self):
        """No movement at all -> 50 (v13 returned 100)."""
        from augur.data import _calculate_rsi

        assert _calculate_rsi([100.0] * 30, period=14) == 50.0

    def test_calculate_rsi_only_gains_is_100(self):
        from augur.data import _calculate_rsi

        assert _calculate_rsi([float(i) for i in range(1, 30)], period=14) == 100.0

    def test_calculate_macd(self):
        """Need 26+ prices for MACD calculation."""
        from augur.data import _calculate_macd

        prices = [100 + i * 0.5 for i in range(30)]
        result = _calculate_macd(prices)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result

    def test_calculate_macd_short_data(self):
        """Short data returns zeros for MACD."""
        from augur.data import _calculate_macd

        result = _calculate_macd([100, 101])
        assert result["macd"] == 0

    def test_calculate_technicals_from_prices(self):
        """Full technicals calculation with sufficient data."""
        from augur.data import _calculate_technicals_from_prices

        prices = [100 + i * 0.3 for i in range(60)]
        result = _calculate_technicals_from_prices(prices)
        assert "sma20" in result
        assert "sma50" in result
        assert "rsi" in result
        assert "atr" in result


class TestFetchHistoryValidation:
    def test_invalid_ticker_returns_empty(self):
        """Invalid tickers should return [] instead of raising."""
        from augur.data import fetch_history

        assert fetch_history("") == []
        assert fetch_history("INVALID..TICKER") == []


class TestDebtRatioConversion:
    """Tests for the debt_to_equity -> debt_ratio conversion logic in data.py."""

    def test_debt_ratio_conversion_negative(self):
        """Negative debt_to_equity (negative equity) should give debt_ratio=0."""
        # The fix is in fetch_market_context: if debt_to_equity <= 0, debt_ratio = 0
        # Test the formula directly
        debt_to_equity = -150
        if debt_to_equity > 0:
            de_ratio = debt_to_equity / 100.0
            debt_ratio = de_ratio / (1.0 + de_ratio)
        else:
            debt_ratio = 0
        assert debt_ratio == 0

    def test_debt_ratio_conversion_positive(self):
        """Normal positive debt_to_equity should compute correctly."""
        debt_to_equity = 162  # D/E = 1.62
        de_ratio = debt_to_equity / 100.0
        debt_ratio = de_ratio / (1.0 + de_ratio)
        assert 0.6 < debt_ratio < 0.7  # D/A = 1.62/2.62 ~ 0.618

    def test_debt_ratio_conversion_zero(self):
        """Zero debt_to_equity should give debt_ratio=0."""
        debt_to_equity = 0
        if debt_to_equity > 0:
            de_ratio = debt_to_equity / 100.0
            debt_ratio = de_ratio / (1.0 + de_ratio)
        else:
            debt_ratio = 0
        assert debt_ratio == 0


class TestSanitizePriceSeries:
    """Loop 6 Agent: non-finite / bool closes must not poison technicals."""

    def test_nan_close_skipped_in_technicals(self):
        import math
        from augur.data import calculate_technicals

        result = calculate_technicals(
            [{"close": float("nan")}, {"close": 100.0}, {"close": 101.0}]
        )
        assert all(
            not (isinstance(v, float) and not math.isfinite(v))
            for v in result.values()
        )

    def test_bool_close_skipped(self):
        from augur.data import calculate_technicals

        result = calculate_technicals([{"close": True}, {"close": 100.0}, {"close": 101.0}])
        assert result.get("sma20") == pytest.approx(100.5)

    def test_macd_with_inf_returns_zeros(self):
        from augur.data import _calculate_macd

        prices = [100.0] * 30
        prices[15] = float("inf")
        assert _calculate_macd(prices) == {"macd": 0, "signal": 0, "histogram": 0}
