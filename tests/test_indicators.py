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
