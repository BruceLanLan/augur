# -*- coding: utf-8 -*-
"""
augur.data - 实时股票数据获取

Provides MarketContext from live data via yfinance.
Supports: US stocks, HK stocks, A-shares (via suffix).

Usage:
    from augur.data import fetch_market_context, fetch_history

    ctx = fetch_market_context("AAPL")  # Returns MarketContext with real data
    history = fetch_history("AAPL", period="1y")  # Historical prices
"""

import logging
import re
import threading
import time
from typing import Dict, List, Optional, Any

from augur.personas.base import MarketContext

logger = logging.getLogger(__name__)


# ============ Cache ============

_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 180  # 3 minutes


def _cache_get(key: str) -> Optional[Any]:
    """Get cached value if not expired."""
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        if time.time() - entry["ts"] > _CACHE_TTL:
            del _cache[key]
            return None
        return entry["value"]


def _cache_set(key: str, value: Any) -> None:
    """Set cache entry."""
    with _cache_lock:
        _cache[key] = {"value": value, "ts": time.time()}


def clear_cache() -> None:
    """Clear all cached data entries."""
    with _cache_lock:
        _cache.clear()


def cache_info() -> Dict[str, Any]:
    """Return cache metadata: current size and TTL setting."""
    with _cache_lock:
        return {
            "size": len(_cache),
            "ttl_seconds": _CACHE_TTL,
        }


# ============ Ticker Validation ============

def _normalize_ticker(ticker: str) -> str:
    """Normalize and validate a ticker symbol.

    - Strips whitespace and uppercases
    - Validates: 1-15 chars, only alphanumeric, dots, hyphens
    - Raises ValueError if invalid
    """
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Ticker cannot be empty")
    if len(ticker) > 15:
        raise ValueError(f"Ticker too long (max 15 chars): {ticker}")
    if not re.match(r'^[A-Z0-9.\-]+$', ticker):
        raise ValueError(f"Invalid ticker format (only alphanumeric, dots, hyphens allowed): {ticker}")
    return ticker


# ============ yfinance Helpers ============

def _get_yfinance() -> Any:
    """Lazy import yfinance with graceful ImportError."""
    try:
        import yfinance as yf
        return yf
    except ImportError:
        raise ImportError(
            "yfinance is required for real-time data. "
            "Install with: pip install 'augur-agents[data]'"
        )


# ============ Public API ============

def fetch_market_context(ticker: str, force_refresh: bool = False) -> MarketContext:
    """
    Fetch real-time data for a ticker and return a populated MarketContext.

    Supports:
    - US stocks: AAPL, NVDA, TSLA
    - HK stocks: 0700.HK, 9988.HK
    - A-shares: 600519.SS, 000858.SZ

    Args:
        ticker: Stock symbol
        force_refresh: If True, bypass the cache and fetch fresh data

    Fills: price, pe, pb, ps, roe, gross_margins, operating_margins,
           revenue_growth, earnings_growth, debt_ratio, fcf, market_cap,
           current_ratio, sector, industry, rsi, sma50, etc.
    """
    ticker = _normalize_ticker(ticker)
    cache_key = f"ctx:{ticker}"
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    yf = _get_yfinance()
    stock = yf.Ticker(ticker)

    try:
        info = stock.info or {}
    except Exception:
        info = {}

    # If info is empty or missing 'symbol', we have no valid data from yfinance.
    # Return a minimal MarketContext with just the ticker and zero defaults.
    if not info or "symbol" not in info:
        ctx = MarketContext(ticker=ticker.upper())
        _cache_set(cache_key, ctx)
        return ctx

    # Map yfinance info to MarketContext fields
    price = info.get("currentPrice") or info.get("regularMarketPrice", 0) or 0
    pe = info.get("trailingPE", 0) or 0
    pb = info.get("priceToBook", 0) or 0
    ps = info.get("priceToSalesTrailing12Months", 0) or 0
    roe = info.get("returnOnEquity", 0) or 0
    gross_margins = info.get("grossMargins", 0) or 0
    operating_margins = info.get("operatingMargins", 0) or 0
    revenue_growth = info.get("revenueGrowth", 0) or 0
    earnings_growth = info.get("earningsGrowth", 0) or 0
    debt_to_equity = info.get("debtToEquity", 0) or 0
    # yfinance debtToEquity is D/E percentage (e.g. 162 means D/E = 1.62)
    # Convert to debt ratio (D/A = D/E / (1 + D/E))
    # Guard: negative or zero debt_to_equity (negative shareholder equity) is invalid
    # for this formula; de_ratio of -1.0 would cause ZeroDivisionError.
    if debt_to_equity > 0:
        de_ratio = debt_to_equity / 100.0  # D/E as decimal
        debt_ratio = de_ratio / (1.0 + de_ratio)   # D/A = D/E / (1 + D/E)
    else:
        debt_ratio = 0
    fcf = (info.get("freeCashflow", 0) or 0) / 1e9         # raw USD → billions
    market_cap = (info.get("marketCap", 0) or 0) / 1e9    # raw USD → billions
    revenue = (info.get("totalRevenue", 0) or 0) / 1e9    # raw USD → billions
    current_ratio = info.get("currentRatio", 0) or 0
    quick_ratio = info.get("quickRatio", 0) or 0
    sector = info.get("sector", "") or ""
    industry = info.get("industry", "") or ""

    # Ownership data (yfinance returns as fraction 0-1, convert to percentage 0-100)
    institutional_ownership = (info.get("heldPercentInstitutions", 0) or 0) * 100
    insider_ownership = (info.get("heldPercentInsiders", 0) or 0) * 100

    # Short interest as fraction of float (0-1), e.g. 0.05 = 5% short
    short_interest = info.get("shortPercentOfFloat", 0) or 0

    # Beta
    beta_1y = info.get("beta", 1.0) or 1.0

    # 52-week high/low distance
    fifty_two_high = info.get("fiftyTwoWeekHigh", 0) or 0
    fifty_two_low = info.get("fiftyTwoWeekLow", 0) or 0
    price_vs_52w_high = ((price / fifty_two_high) - 1) * 100 if fifty_two_high and price else 0
    price_vs_52w_low = ((price / fifty_two_low) - 1) * 100 if fifty_two_low and price else 0

    # Calculate technical indicators from price history
    technicals = {}
    try:
        hist = stock.history(period="3mo")
        if hist is not None and not hist.empty:
            closes = hist["Close"].tolist()
            technicals = _calculate_technicals_from_prices(closes)
    except Exception:
        pass

    rsi = technicals.get("rsi", 50)
    macd = technicals.get("macd", 0)
    macd_signal = technicals.get("macd_signal", 0)
    macd_histogram = technicals.get("macd_histogram", 0)
    sma20 = technicals.get("sma20", 0)
    sma50 = technicals.get("sma50", 0)
    atr = technicals.get("atr", 0)
    volatility_20d = technicals.get("volatility_20d", 0)

    ctx = MarketContext(
        ticker=ticker.upper(),
        price=price,
        pe=pe,
        pb=pb,
        ps=ps,
        roe=roe,
        gross_margins=gross_margins,
        operating_margins=operating_margins,
        revenue_growth=revenue_growth,
        earnings_growth=earnings_growth,
        debt_ratio=debt_ratio,
        fcf=fcf,
        market_cap=market_cap,
        current_ratio=current_ratio,
        sector=sector,
        industry=industry,
        revenue=revenue,
        quick_ratio=quick_ratio,
        institutional_ownership=institutional_ownership,
        insider_ownership=insider_ownership,
        short_interest=short_interest,
        beta_1y=beta_1y,
        price_vs_52w_high=price_vs_52w_high,
        price_vs_52w_low=price_vs_52w_low,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        sma20=sma20,
        sma50=sma50,
        atr=atr,
        volatility_20d=volatility_20d,
    )

    _cache_set(cache_key, ctx)
    return ctx


def fetch_history(ticker: str, period: str = "1y") -> List[Dict]:
    """
    Fetch historical price data.

    Args:
        ticker: Stock symbol (e.g. AAPL, 0700.HK, 600519.SS)
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)

    Returns:
        List of {date, open, high, low, close, volume, change_pct}
    """
    ticker = _normalize_ticker(ticker)
    cache_key = f"hist:{ticker}:{period}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    yf = _get_yfinance()
    stock = yf.Ticker(ticker)

    try:
        hist = stock.history(period=period)
    except Exception:
        return []

    if hist is None or hist.empty:
        return []

    results = []
    prev_close = None
    for date_idx, row in hist.iterrows():
        close = float(row.get("Close", 0))
        change_pct = 0.0
        if prev_close and prev_close > 0:
            change_pct = (close - prev_close) / prev_close
        prev_close = close

        results.append({
            "date": date_idx.strftime("%Y-%m-%d"),
            "open": round(float(row.get("Open", 0)), 4),
            "high": round(float(row.get("High", 0)), 4),
            "low": round(float(row.get("Low", 0)), 4),
            "close": round(close, 4),
            "volume": int(row.get("Volume", 0)),
            "change_pct": round(change_pct, 6),
        })

    _cache_set(cache_key, results)
    return results


def calculate_technicals(prices: List[Dict]) -> Dict[str, Any]:
    """
    Calculate technical indicators from price history.

    Args:
        prices: List of dicts with at least 'close' field.

    Returns:
        Dict with: rsi, macd, macd_signal, sma20, sma50, atr, volatility_20d, etc.
    """
    closes = [p["close"] for p in prices if "close" in p]
    if not closes:
        return {}
    return _calculate_technicals_from_prices(closes)


def search_ticker(query: str) -> List[Dict]:
    """
    Search for tickers by name/symbol.

    Args:
        query: Search query (e.g. "apple", "AAPL")

    Returns:
        List of {symbol, name, exchange, type}
    """
    yf = _get_yfinance()

    try:
        # yfinance search is limited; use Ticker info as fallback
        # Try direct ticker lookup first
        stock = yf.Ticker(query.upper())
        info = stock.info or {}
        if info.get("symbol"):
            return [{
                "symbol": info.get("symbol", query.upper()),
                "name": info.get("longName") or info.get("shortName", ""),
                "exchange": info.get("exchange", ""),
                "type": info.get("quoteType", "EQUITY"),
            }]
    except Exception:
        pass

    return []


# ============ Internal Helpers ============

def _calculate_technicals_from_prices(closes: List[float]) -> Dict[str, Any]:
    """Calculate technical indicators from a list of closing prices."""
    result = {}

    n = len(closes)
    if n < 2:
        return result

    # SMA 20
    if n >= 20:
        result["sma20"] = round(sum(closes[-20:]) / 20, 4)
    else:
        result["sma20"] = round(sum(closes) / n, 4)

    # SMA 50
    if n >= 50:
        result["sma50"] = round(sum(closes[-50:]) / 50, 4)
    else:
        result["sma50"] = round(sum(closes) / n, 4)

    # RSI (14-period)
    result["rsi"] = _calculate_rsi(closes, period=14)

    # MACD (12/26/9)
    macd_vals = _calculate_macd(closes)
    result["macd"] = macd_vals.get("macd", 0)
    result["macd_signal"] = macd_vals.get("signal", 0)
    result["macd_histogram"] = macd_vals.get("histogram", 0)

    # ATR (14-period, approximated from close-to-close)
    if n >= 15:
        true_ranges = [abs(closes[i] - closes[i - 1]) for i in range(1, n)]
        atr_window = true_ranges[-14:]
        result["atr"] = round(sum(atr_window) / len(atr_window), 4)
    else:
        result["atr"] = 0

    # 20-day volatility (annualized)
    if n >= 21:
        returns = [(closes[i] / closes[i - 1] - 1) for i in range(max(1, n - 20), n)]
        if returns:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
            result["volatility_20d"] = round((variance ** 0.5) * (252 ** 0.5), 4)
        else:
            result["volatility_20d"] = 0
    else:
        result["volatility_20d"] = 0

    return result


def _calculate_rsi(closes: List[float], period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index)."""
    if len(closes) < period + 1:
        return 50.0

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Use last `period` deltas for initial calculation, then smooth
    gains = []
    losses = []
    for d in deltas[-period:]:
        if d > 0:
            gains.append(d)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(d))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # All gains, no losses -> RSI=100; if avg_gain were 0 (all losses), rs=0 -> RSI=0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


def _calculate_macd(closes: List[float]) -> Dict[str, float]:
    """Calculate MACD (12/26/9)."""
    if len(closes) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0}

    # EMA helper
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

    macd_val = macd_line[-1]
    signal_val = signal_line[-1]
    histogram = macd_val - signal_val

    return {
        "macd": round(macd_val, 4),
        "signal": round(signal_val, 4),
        "histogram": round(histogram, 4),
    }
