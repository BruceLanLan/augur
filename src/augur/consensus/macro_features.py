# -*- coding: utf-8 -*-
"""Macro feature fetcher for regime detection."""

import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

_DEFAULT_MACRO: Dict[str, Any] = {
    "vix": 20.0,
    "trend": "sideways",
    "regime": "SIDEWAYS",
    "regime_raw": "SIDEWAYS",
}

# Cache is keyed by date_str ("live" key is None). Only the live entry is
# refreshed/expired on a TTL; historical (backtest) entries, if ever cached,
# would otherwise grow unbounded since a historical macro snapshot never
# goes stale. We don't cache historical lookups at all (see fetch_macro_features).
_CACHE: Optional[Tuple[float, Dict[str, Any]]] = None
_CACHE_TTL_SEC = 300.0
_CACHE_LOCK = threading.RLock()

# Hysteresis tuning: VIX uses an asymmetric (Schmitt-trigger) band instead of
# a hard >=25 cutoff, and a new raw regime must persist for CONFIRM_DAYS
# consecutive trading days before it is "accepted". This trades a small
# amount of detection lag for materially fewer spurious flips when VIX/SPY
# oscillate around a boundary.
VIX_ENTER_HIGH_VOL = 25.0
VIX_EXIT_HIGH_VOL = 23.0
CONFIRM_DAYS = 3
_TREND_SMA_WINDOW = 10


def _raw_regime(vix: float, trend: str, prev_high_vol: bool) -> Tuple[str, bool]:
    """Classify a single day from vix/trend, applying the vol hysteresis band.

    ``prev_high_vol`` is the previously accepted vol state; the band means
    a VIX reading between EXIT and ENTER thresholds keeps whatever vol state
    was already in effect rather than forcing a side.
    """
    if vix >= VIX_ENTER_HIGH_VOL:
        high_vol = True
    elif vix <= VIX_EXIT_HIGH_VOL:
        high_vol = False
    else:
        high_vol = prev_high_vol

    if trend == "bull":
        regime = "BULL_HIGH_VOL" if high_vol else "BULL_LOW_VOL"
    elif trend == "bear":
        regime = "BEAR_HIGH_VOL" if high_vol else "BEAR_LOW_VOL"
    else:
        regime = "SIDEWAYS"
    return regime, high_vol


def _trend_from_window(closes: Sequence[float], idx: int) -> str:
    """SPY trend proxy: last close vs trailing 10-day SMA, +/-2% deadband."""
    if idx + 1 < _TREND_SMA_WINDOW:
        return "sideways"
    window = closes[idx + 1 - _TREND_SMA_WINDOW : idx + 1]
    sma = sum(window) / len(window)
    last = closes[idx]
    if sma <= 0:
        return "sideways"
    if last > sma * 1.02:
        return "bull"
    if last < sma * 0.98:
        return "bear"
    return "sideways"


def classify_regime(
    vix_series: Sequence[float],
    spy_series: Sequence[float],
    end_idx: int,
    *,
    confirm_days: int = CONFIRM_DAYS,
) -> Dict[str, Any]:
    """Classify the regime as of ``end_idx`` using only data up to that index.

    Both series must be aligned (same trading-day index) and ``end_idx`` is
    inclusive. This is the single source of truth for regime classification:
    both the live path and the historical backtest path call this function,
    so live and backtest behavior are identical by construction.

    A "raw" per-day regime is computed first (current VIX/trend day only,
    via a Schmitt-trigger vol band), then a forward min-dwell scan accepts a
    new raw regime only once it has persisted for ``confirm_days`` consecutive
    days — this is the hysteresis. The scan starts from the beginning of the
    provided series, so the accepted regime at ``end_idx`` depends only on
    history up to and including ``end_idx`` (no look-ahead).
    """
    n = min(len(vix_series), len(spy_series))
    if n == 0 or end_idx < 0 or end_idx >= n:
        return dict(_DEFAULT_MACRO)

    accepted_regime = "SIDEWAYS"
    accepted_high_vol = False
    raw_regime = "SIDEWAYS"
    pending_regime: Optional[str] = None
    pending_count = 0

    for i in range(0, end_idx + 1):
        vix_i = float(vix_series[i])
        trend_i = _trend_from_window(spy_series, i)
        raw_regime, raw_high_vol = _raw_regime(vix_i, trend_i, accepted_high_vol)

        if raw_regime == accepted_regime:
            pending_regime = None
            pending_count = 0
            accepted_high_vol = raw_high_vol
            continue

        if raw_regime == pending_regime:
            pending_count += 1
        else:
            pending_regime = raw_regime
            pending_count = 1

        if pending_count >= max(1, confirm_days):
            accepted_regime = raw_regime
            accepted_high_vol = raw_high_vol
            pending_regime = None
            pending_count = 0

    return {
        "vix": float(vix_series[end_idx]),
        "trend": _trend_from_window(spy_series, end_idx),
        "regime": accepted_regime,
        "regime_raw": raw_regime,
    }


def _macro_from_market(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Fetch macro features as of ``date_str`` (None = now); never raises.

    Pulls a trailing window of VIX/SPY daily closes ending at ``date_str``
    (or today, if None) and runs them through ``classify_regime`` so live
    classification uses the exact same hysteresis logic as the historical
    backtest path.
    """
    try:
        import yfinance as yf

        if date_str:
            end_dt = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
        else:
            end_dt = datetime.utcnow() + timedelta(days=1)
        # ~3 months of trailing data: enough to warm up the 10-day SMA and
        # the confirm_days dwell scan with comfortable margin.
        start_dt = end_dt - timedelta(days=95)
        # yfinance wants plain date strings here; passing datetime objects
        # through to the underlying scraper raises a TypeError internally.
        start_s, end_s = start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

        vix_hist = yf.Ticker("^VIX").history(start=start_s, end=end_s)
        spy_hist = yf.Ticker("SPY").history(start=start_s, end=end_s)

        if vix_hist is None or spy_hist is None or len(vix_hist) == 0 or len(spy_hist) == 0:
            return dict(_DEFAULT_MACRO)

        # VIX and SPY history come back tz-localized to different exchange
        # timezones (America/Chicago vs America/New_York), so the same
        # trading day has different absolute timestamps in each index.
        # Normalize both to plain (tz-naive) calendar dates before aligning,
        # otherwise the intersection below is silently empty.
        import pandas as pd

        vix_hist = vix_hist.copy()
        spy_hist = spy_hist.copy()
        vix_hist.index = pd.to_datetime(vix_hist.index.date)
        spy_hist.index = pd.to_datetime(spy_hist.index.date)

        # Align on shared trading days present in both series.
        common_idx = vix_hist.index.intersection(spy_hist.index)
        if len(common_idx) == 0:
            return dict(_DEFAULT_MACRO)
        common_idx = common_idx.sort_values()

        vix_closes: List[float] = vix_hist.loc[common_idx, "Close"].tolist()
        spy_closes: List[float] = spy_hist.loc[common_idx, "Close"].tolist()
        if not vix_closes or not spy_closes:
            return dict(_DEFAULT_MACRO)

        return classify_regime(vix_closes, spy_closes, end_idx=len(vix_closes) - 1)
    except Exception:
        return dict(_DEFAULT_MACRO)


def fetch_macro_features(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Fetch VIX/SPY-derived regime features as of ``date_str`` (None = now).

    Never raises. The live snapshot (``date_str=None``) is cached in-process
    for five minutes to avoid hammering yfinance on repeated ``get_consensus``
    calls. Historical lookups (``date_str`` set, e.g. for backtesting) are
    never cached, since a backtest can request many distinct dates and a
    historical snapshot would never expire anyway — caching it would just
    grow the cache unbounded for no benefit.
    Set ``AUGUR_SKIP_MACRO_FETCH=1`` to return defaults immediately (useful in CI).
    """
    if os.environ.get("AUGUR_SKIP_MACRO_FETCH", "").strip() in ("1", "true", "yes"):
        return dict(_DEFAULT_MACRO)

    if date_str is not None:
        return _macro_from_market(date_str)

    global _CACHE
    with _CACHE_LOCK:
        now = time.monotonic()
        if _CACHE is not None and (now - _CACHE[0]) < _CACHE_TTL_SEC:
            return dict(_CACHE[1])

        result = _macro_from_market(None)
        _CACHE = (now, result)
        return dict(result)


def clear_macro_cache() -> None:
    """Clear in-process macro cache (for tests)."""
    global _CACHE
    with _CACHE_LOCK:
        _CACHE = None
