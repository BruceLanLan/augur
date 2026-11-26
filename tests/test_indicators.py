# -*- coding: utf-8 -*-
"""Tests for augur.indicators (pure-Python indicator math)."""

import pytest

from augur import indicators


def _legacy_macd(closes):
    """augur <= v13 MACD, copied verbatim to pin that the math only moved."""
    def ema(data, span):
        multiplier = 2.0 / (span + 1)
        result = [data[0]]
        for i in range(1, len(data)):
            result.append((data[i] - result[-1]) * multiplier + result[-1])
        return result

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal_line = ema(macd_line, 9)
    m, s = macd_line[-1], signal_line[-1]
    return {"macd": round(m, 4), "signal": round(s, 4), "histogram": round(m - s, 4)}


class TestWilderRsi:
    def test_wilder_reference(self):
        closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
        assert indicators.wilder_rsi(closes[:15]) == 70.46
        assert indicators.wilder_rsi(closes) == 66.25

    def test_conventions(self):
        assert indicators.wilder_rsi([1.0, 2.0]) == 50.0          # too short
        assert indicators.wilder_rsi([5.0] * 40) == 50.0          # flat
        assert indicators.wilder_rsi([float(i) for i in range(1, 40)]) == 100.0
        assert indicators.wilder_rsi([float(40 - i) for i in range(39)]) == 0.0

    def test_bounded(self):
        import math
        import random
        r = random.Random(3)
        s = [100.0]
        for _ in range(200):
            s.append(s[-1] * math.exp(r.gauss(0, 0.02)))
        v = indicators.wilder_rsi(s)
        assert 0.0 <= v <= 100.0


class TestMovedMath:
    def test_macd_identical_to_v13(self):
        import math
        import random
        r = random.Random(7)
        s = [100.0]
        for _ in range(80):
            s.append(s[-1] * math.exp(r.gauss(0.001, 0.02)))
        for n in (26, 40, 63, 81):
            assert indicators.macd(s[:n]) == _legacy_macd(s[:n])

    def test_macd_short(self):
        assert indicators.macd([1.0] * 25) == {"macd": 0, "signal": 0, "histogram": 0}

    def test_sma(self):
        assert indicators.sma([1.0, 2.0, 3.0, 4.0], 2) == pytest.approx(3.5)
        assert indicators.sma([1.0, 2.0, 3.0], 20) == pytest.approx(2.0)
        assert indicators.sma([], 5) == 0.0

    def test_ema_seeded_with_first_value(self):
        out = indicators.ema([10.0, 20.0], 3)
        assert out == [10.0, 15.0]


def _bars(n=30, seed=3):
    """Deterministic OHLC-ish bars: closes plus highs/lows bracketing them."""
    import math
    import random
    r = random.Random(seed)
    closes, highs, lows = [], [], []
    c = 100.0
    for _ in range(n):
        c *= math.exp(r.gauss(0, 0.015))
        closes.append(c)
        highs.append(c * (1 + abs(r.gauss(0, 0.01))))
        lows.append(c * (1 - abs(r.gauss(0, 0.01))))
    return closes, highs, lows


class TestTrueRangeAtr:
    def test_true_range_uses_previous_close_on_gaps(self):
        # gap up: range 11.5-12.5 but previous close 10 -> TR = 12.5 - 10
        assert indicators.true_ranges([10.0, 12.0], [10.0, 12.5], [10.0, 11.5]) == [2.5]
        # inside bar: plain high - low
        assert indicators.true_ranges([10.0, 10.2], [10.0, 10.5], [10.0, 9.8]) == [
            pytest.approx(0.7)]

    def test_missing_high_low_bar_degrades_to_close_move(self):
        trs = indicators.true_ranges([10.0, 11.0, 10.5], [10.0, None, 0.0], [10.0, None, 0.0])
        assert trs == [pytest.approx(1.0), pytest.approx(0.5)]
        # high < low is invalid too
        assert indicators.true_ranges([10.0, 11.0], [10.0, 9.0], [10.0, 12.0]) == [
            pytest.approx(1.0)]

    def test_wilder_seed_and_smoothing(self):
        # 14 bars of TR=1 seed ATR=1; a 15th TR of 15 -> (1*13 + 15) / 14 = 2
        closes = [100.0] * 16
        highs = [100.5] * 15 + [115.0]
        lows = [99.5] * 15 + [100.0]
        assert indicators.wilder_atr(closes[:15], highs[:15], lows[:15]) == pytest.approx(1.0)
        assert indicators.wilder_atr(closes, highs, lows) == pytest.approx(2.0)

    def test_matches_independent_reference(self):
        closes, highs, lows = _bars(63)
        trs = [max(highs[i], closes[i - 1]) - min(lows[i], closes[i - 1])
               for i in range(1, 63)]
        ref = sum(trs[:14]) / 14
        for tr in trs[14:]:
            ref = ref + (tr - ref) / 14
        assert indicators.wilder_atr(closes, highs, lows) == pytest.approx(ref)

    def test_too_short(self):
        closes, highs, lows = _bars(14)
        assert indicators.wilder_atr(closes, highs, lows) == 0.0
        assert indicators.close_to_close_atr(closes) == 0.0

    def test_true_atr_not_below_close_to_close_wilder(self):
        closes, highs, lows = _bars(63)
        assert indicators.wilder_atr(closes, highs, lows) >= indicators.wilder_atr(closes)

    def test_close_to_close_atr_is_v14_formula(self):
        closes, _, _ = _bars(40)
        moves = [abs(closes[i] - closes[i - 1]) for i in range(1, 40)]
        assert indicators.close_to_close_atr(closes) == pytest.approx(sum(moves[-14:]) / 14)


class TestTechnicalsAtrPath:
    def test_without_high_low_keeps_legacy_atr(self):
        from augur.data import _calculate_technicals_from_prices
        closes, _, _ = _bars(63)
        out = _calculate_technicals_from_prices(closes)
        assert out["atr"] == round(indicators.close_to_close_atr(closes), 4)

    def test_with_high_low_uses_true_atr(self):
        from augur.data import _calculate_technicals_from_prices
        closes, highs, lows = _bars(63)
        out = _calculate_technicals_from_prices(closes, highs, lows)
        assert out["atr"] == round(indicators.wilder_atr(closes, highs, lows), 4)
        assert out["atr"] > round(indicators.close_to_close_atr(closes), 4)

    def test_all_zero_high_low_falls_back_to_legacy(self):
        # fetch_history writes 0 for a missing High/Low cell
        from augur.data import _calculate_technicals_from_prices
        closes, _, _ = _bars(63)
        out = _calculate_technicals_from_prices(closes, [0.0] * 63, [0.0] * 63)
        assert out["atr"] == round(indicators.close_to_close_atr(closes), 4)

    def test_misaligned_high_low_ignored(self):
        from augur.data import _calculate_technicals_from_prices
        closes, highs, lows = _bars(63)
        out = _calculate_technicals_from_prices(closes, highs[:-1], lows[:-1])
        assert out["atr"] == round(indicators.close_to_close_atr(closes), 4)

    def test_bad_close_row_dropped_with_its_high_low(self):
        from augur.data import calculate_technicals
        closes, highs, lows = _bars(63)
        rows = [{"close": c, "high": h, "low": lo} for c, h, lo in zip(closes, highs, lows)]
        # a NaN close row (with a wild high) must disappear entirely, not shift H/L
        rows.insert(30, {"close": float("nan"), "high": 1e6, "low": 1.0})
        out = calculate_technicals(rows)
        assert out["atr"] == round(indicators.wilder_atr(closes, highs, lows), 4)

    def test_provider_passes_high_low(self):
        import pandas as pd
        from unittest.mock import MagicMock
        from augur.datasources.yfinance_provider import YFinanceProvider
        closes, highs, lows = _bars(63)
        hist = pd.DataFrame({"Close": closes, "High": highs, "Low": lows})
        ticker = MagicMock()
        ticker.info = {"symbol": "AAPL", "currentPrice": closes[-1], "quoteType": "EQUITY"}
        ticker.history.return_value = hist
        yf = MagicMock()
        yf.Ticker.return_value = ticker
        fields = YFinanceProvider(yf_loader=lambda: yf).fetch("AAPL")
        assert fields["atr"] == round(indicators.wilder_atr(closes, highs, lows), 4)

    def test_provider_without_high_low_columns_keeps_technicals(self):
        import pandas as pd
        from unittest.mock import MagicMock
        from augur.datasources.yfinance_provider import YFinanceProvider
        closes, _, _ = _bars(63)
        ticker = MagicMock()
        ticker.info = {"symbol": "AAPL", "currentPrice": closes[-1], "quoteType": "EQUITY"}
        ticker.history.return_value = pd.DataFrame({"Close": closes})
        yf = MagicMock()
        yf.Ticker.return_value = ticker
        fields = YFinanceProvider(yf_loader=lambda: yf).fetch("AAPL")
        assert fields["atr"] == round(indicators.close_to_close_atr(closes), 4)
        assert fields["sma20"] > 0
