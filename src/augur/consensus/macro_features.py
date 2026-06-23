# -*- coding: utf-8 -*-
"""Macro feature fetcher for regime detection."""

import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

_DEFAULT_MACRO: Dict[str, Any] = {
    "vix": 20.0,
    "trend": "sideways",
    "regime": "SIDEWAYS",
}

_CACHE: Optional[Tuple[float, Dict[str, Any]]] = None
_CACHE_TTL_SEC = 300.0
_CACHE_LOCK = threading.RLock()


def _macro_from_market(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Fetch live macro features; never raises."""
    result: Dict[str, Any] = dict(_DEFAULT_MACRO)
    try:
        import yfinance as yf
        vix_ticker = yf.Ticker("^VIX")
        hist = vix_ticker.history(period="5d")
        if hist is not None and len(hist) > 0:
            result["vix"] = float(hist["Close"].iloc[-1])

        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="1mo")
        if spy_hist is not None and len(spy_hist) >= 10:
            closes = spy_hist["Close"]
            sma = closes.rolling(10).mean().iloc[-1]
            last = closes.iloc[-1]
            if last > sma * 1.02:
                result["trend"] = "bull"
            elif last < sma * 0.98:
                result["trend"] = "bear"
    except Exception:
        pass

    vix = result["vix"]
    trend = result["trend"]
    high_vol = vix >= 25
    if trend == "bull":
        result["regime"] = "BULL_HIGH_VOL" if high_vol else "BULL_LOW_VOL"
    elif trend == "bear":
        result["regime"] = "BEAR_HIGH_VOL" if high_vol else "BEAR_LOW_VOL"
    else:
        result["regime"] = "SIDEWAYS"
    return result


def fetch_macro_features(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Fetch VIX and simple trend proxy. Never raises.

    Results are cached in-process for five minutes to avoid hammering
    yfinance on repeated ``get_consensus`` calls. Set ``AUGUR_SKIP_MACRO_FETCH=1``
    to return defaults immediately (useful in CI).
    """
    if os.environ.get("AUGUR_SKIP_MACRO_FETCH", "").strip() in ("1", "true", "yes"):
        return dict(_DEFAULT_MACRO)

    global _CACHE
    with _CACHE_LOCK:
        now = time.monotonic()
        if _CACHE is not None and (now - _CACHE[0]) < _CACHE_TTL_SEC:
            return dict(_CACHE[1])

        result = _macro_from_market(date_str)
        _CACHE = (now, result)
        return dict(result)


def clear_macro_cache() -> None:
    """Clear in-process macro cache (for tests)."""
    global _CACHE
    with _CACHE_LOCK:
        _CACHE = None
