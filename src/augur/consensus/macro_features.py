# -*- coding: utf-8 -*-
"""Macro feature fetcher for regime detection."""

from typing import Any, Dict, Optional


def fetch_macro_features(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Fetch VIX and simple trend proxy. Never raises."""
    result: Dict[str, Any] = {"vix": 20.0, "trend": "sideways", "regime": "SIDEWAYS"}
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
