# -*- coding: utf-8 -*-
"""Tests for augur.data module (offline technical calculations)."""


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
