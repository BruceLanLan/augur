# -*- coding: utf-8 -*-
"""Pure-Python technical indicators (no third-party dependencies).

Inputs are plain lists of finite floats; callers are responsible for cleaning
the series (see ``augur.data._sanitize_price_series``).
"""

from typing import Dict, List, Sequence


def sma(values: Sequence[float], period: int) -> float:
    """Simple mean of the last ``period`` values (all values if fewer).

    Returns 0.0 for an empty series.
    """
    if not values:
        return 0.0
    window = list(values[-period:]) if period > 0 else list(values)
    return sum(window) / len(window)


def ema(values: Sequence[float], span: int) -> List[float]:
    """Exponential moving average seeded with the first value.

    ``multiplier = 2 / (span + 1)``. Returns a list the same length as ``values``.
    """
    if not values:
        return []
    multiplier = 2.0 / (span + 1)
    out = [float(values[0])]
    for v in values[1:]:
        out.append((v - out[-1]) * multiplier + out[-1])
    return out


def wilder_rsi(closes: Sequence[float], period: int = 14) -> float:
    """Wilder's RSI (Wilder 1978; matches TA-Lib ``RSI``) of the last close.

    The first average gain and loss are the simple means of the first
    ``period`` changes; every later change is folded in with Wilder's
    smoothing ``avg = (avg * (period - 1) + change) / period``.

    Conventions: fewer than ``period + 1`` closes -> 50.0; no movement at all
    (flat series) -> 50.0; gains but no losses -> 100.0; losses but no gains
    -> 0.0. Rounded to 2 decimals.
    """
    if period < 1 or len(closes) < period + 1:
        return 50.0

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    avg_gain = sum(d for d in deltas[:period] if d > 0) / period
    avg_loss = sum(-d for d in deltas[:period] if d < 0) / period
    for d in deltas[period:]:
        avg_gain = (avg_gain * (period - 1) + (d if d > 0 else 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + (-d if d < 0 else 0.0)) / period

    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 2)


def macd(closes: Sequence[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> Dict[str, float]:
    """MACD line, signal line and histogram at the last close.

    EMAs are seeded with the first close (unchanged from augur <= v13).
    Fewer than ``slow`` closes -> all zeros.
    """
    if len(closes) < slow:
        return {"macd": 0, "signal": 0, "histogram": 0}

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)

    macd_val = macd_line[-1]
    signal_val = signal_line[-1]
    return {
        "macd": round(macd_val, 4),
        "signal": round(signal_val, 4),
        "histogram": round(macd_val - signal_val, 4),
    }
