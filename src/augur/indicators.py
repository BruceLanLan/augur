# -*- coding: utf-8 -*-
"""Pure-Python technical indicators (no third-party dependencies).

Inputs are plain lists of finite floats; callers are responsible for cleaning
the series (see ``augur.data._sanitize_price_series``).
"""

import math
from typing import Dict, List, Optional, Sequence


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

    Seeding convention (unchanged from augur <= v13, kept deliberately):
    both price EMAs are seeded with the *first close* (pandas
    ``ewm(adjust=False)`` style), and the signal EMA is seeded with the first
    MACD value and runs over the whole MACD line, including the bars before
    EMA26 has warmed up. TA-Lib instead seeds each EMA with an SMA of its
    first ``span`` values and starts the signal line only once EMA26 exists.
    On production's ~63-bar window the two conventions differ slightly in
    level; the v14 audit measured the ``macd > signal`` cross flipping on
    4 of 638 random windows, so the existing convention is documented rather
    than changed (changing it would move every persona that reads MACD).
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


def _valid_hl(high: Optional[float], low: Optional[float]) -> bool:
    if high is None or low is None:
        return False
    if isinstance(high, bool) or isinstance(low, bool):
        return False
    try:
        h, lo = float(high), float(low)
    except (TypeError, ValueError):
        return False
    return math.isfinite(h) and math.isfinite(lo) and h > 0 and lo > 0 and h >= lo


def true_ranges(closes: Sequence[float],
                highs: Optional[Sequence[Optional[float]]] = None,
                lows: Optional[Sequence[Optional[float]]] = None) -> List[float]:
    """Wilder's True Range for bars 1..n-1 (bar 0 has no previous close).

    ``TR_i = max(H_i, C_{i-1}) - min(L_i, C_{i-1})``. A bar whose high/low is
    missing or invalid (non-finite, <= 0, high < low) is treated as
    ``H = L = C_i``, which degrades that bar to ``|C_i - C_{i-1}|`` -- the
    lower bound of its true range. Without highs/lows every bar degrades
    that way. ``highs``/``lows`` must be aligned with ``closes``.
    """
    n = len(closes)
    have_hl = highs is not None and lows is not None and len(highs) == n and len(lows) == n
    out: List[float] = []
    for i in range(1, n):
        prev = closes[i - 1]
        if have_hl and _valid_hl(highs[i], lows[i]):
            h, lo = float(highs[i]), float(lows[i])
        else:
            h = lo = closes[i]
        out.append(max(h, prev) - min(lo, prev))
    return out


def wilder_atr(closes: Sequence[float],
               highs: Optional[Sequence[Optional[float]]] = None,
               lows: Optional[Sequence[Optional[float]]] = None,
               period: int = 14) -> float:
    """Wilder's Average True Range (matches TA-Lib ``ATR``) at the last bar.

    The first ATR is the simple mean of the first ``period`` true ranges;
    later ones use ``atr = (atr * (period - 1) + TR) / period``. Fewer than
    ``period + 1`` bars -> 0.0. See :func:`true_ranges` for missing H/L.
    """
    trs = true_ranges(closes, highs, lows)
    if period < 1 or len(trs) < period:
        return 0.0
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def close_to_close_atr(closes: Sequence[float], period: int = 14) -> float:
    """Legacy (augur <= v14.0) ATR approximation: simple mean of the last
    ``period`` absolute close-to-close changes. Used only when no high/low
    data is available; on real daily bars it reads ~0.54x a true ATR
    (true/approx median 1.86; see
    docs/research/ATR_RECALIBRATION_2026-11.md). Fewer than ``period + 1``
    closes -> 0.0.
    """
    if period < 1 or len(closes) < period + 1:
        return 0.0
    moves = [abs(closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    window = moves[-period:]
    return sum(window) / len(window)


def has_high_low(highs: Optional[Sequence[Optional[float]]],
                 lows: Optional[Sequence[Optional[float]]]) -> bool:
    """True when at least one bar has a usable high/low pair."""
    if highs is None or lows is None or len(highs) != len(lows):
        return False
    return any(_valid_hl(h, lo) for h, lo in zip(highs, lows))
