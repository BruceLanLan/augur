# -*- coding: utf-8 -*-
"""
augur.data - 实时股票数据获取

Provides MarketContext from live data via a multi-source provider chain.
Supports: US stocks, HK stocks, A-shares (via suffix).

数据源链 (多数据源 fallback, 消除单点故障):
    1. yfinance  - 主数据源（基本面 + 行情 + 技术指标）
    2. stooq     - 备用行情数据源（免费 CSV，yfinance 失败时降级）
    全部失败时返回带 ``data_source="none"`` 标记的空 MarketContext。

Usage:
    from augur.data import fetch_market_context, fetch_history

    ctx = fetch_market_context("AAPL")  # Returns MarketContext with real data
    history = fetch_history("AAPL", period="1y")  # Historical prices

向后兼容: ``fetch_market_context(ticker, force_refresh=False)`` 签名与行为不变，
仅内部改为走 provider 链。
"""

import logging
import re
import threading
import time
from dataclasses import fields as _dataclass_fields
from typing import Any, Dict, List, Optional

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


def cache_stats() -> Dict[str, Any]:
    """Return detailed cache statistics including per-key age and expiration info."""
    now = time.time()
    with _cache_lock:
        expired_count = 0
        for key, entry in _cache.items():
            age = now - entry["ts"]
            if age > _CACHE_TTL:
                expired_count += 1
        return {
            "size": len(_cache),
            "ttl_seconds": _CACHE_TTL,
            "expired_count": expired_count,
            "active_count": len(_cache) - expired_count,
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


# ============ Provider Chain ============

_providers_lock = threading.Lock()
_providers_cache: Optional[List[Any]] = None


def _get_providers() -> List[Any]:
    """返回（并缓存）默认 provider 链：yfinance 优先，stooq 兜底。

    provider 无状态（yfinance loader 在调用时按属性解析），可安全复用。
    测试可通过 patch 本函数注入 mock provider 链。
    """
    global _providers_cache
    with _providers_lock:
        if _providers_cache is None:
            from augur.datasources import default_providers
            _providers_cache = default_providers()
        return _providers_cache


def _market_context_field_names() -> set:
    """MarketContext 的合法字段名集合，用于过滤 provider 返回的字典。"""
    return {f.name for f in _dataclass_fields(MarketContext)}


def _build_context_from_providers(ticker: str) -> MarketContext:
    """按 provider 链顺序尝试获取数据并构建 MarketContext。

    - 第一个成功返回非空字典的 provider 胜出。
    - 全部失败时返回仅含 ticker 的空 context，并标记 ``data_source="none"``。
    - 返回的 context 上附带动态属性 ``data_source`` 标记来源（不修改 MarketContext 定义）。
    """
    valid_fields = _market_context_field_names()
    upper = ticker.upper()

    for provider in _get_providers():
        name = getattr(provider, "name", provider.__class__.__name__)
        try:
            raw = provider.fetch(ticker)
        except Exception as exc:
            logger.warning("data provider '%s' failed for %s: %s", name, ticker, exc)
            continue
        if not raw:
            logger.warning("data provider '%s' returned empty data for %s", name, ticker)
            continue

        source = raw.pop("data_source", name)
        # 仅保留 MarketContext 合法字段，避免未知键导致 TypeError
        kwargs = {k: v for k, v in raw.items() if k in valid_fields and k != "ticker"}
        ctx = MarketContext(ticker=upper, **kwargs)
        setattr(ctx, "data_source", source)
        return ctx

    # 所有数据源均失败：返回空 context，但带来源标记，便于下游识别“无数据”状态
    logger.warning("all data providers failed for %s; returning empty context", ticker)
    ctx = MarketContext(ticker=upper)
    setattr(ctx, "data_source", "none")
    return ctx


# ============ Public API ============

def fetch_market_context(ticker: str, force_refresh: bool = False) -> MarketContext:
    """
    Fetch real-time data for a ticker and return a populated MarketContext.

    内部走 provider 链（yfinance -> stooq -> 空 context），对调用方完全透明。
    返回的 MarketContext 带有动态属性 ``data_source``，标记实际命中的数据源
    （"yfinance" / "stooq" / "none"）。

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

    ctx = _build_context_from_providers(ticker)
    _cache_set(cache_key, ctx)
    return ctx


def fetch_history(ticker: str, period: str = "1y", force_refresh: bool = False) -> List[Dict]:
    """
    Fetch historical price data.

    Args:
        ticker: Stock symbol (e.g. AAPL, 0700.HK, 600519.SS)
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
        force_refresh: If True, bypass the cache and fetch fresh data

    Returns:
        List of {date, open, high, low, close, volume, change_pct}
    """
    from augur.datasources.base import safe_num

    ticker = _normalize_ticker(ticker)
    cache_key = f"hist:{ticker}:{period}"
    if not force_refresh:
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
        # safe_num 防止 yfinance 偶发的 NaN 行污染历史序列
        close = safe_num(row.get("Close", 0))
        change_pct = 0.0
        if prev_close and prev_close > 0:
            change_pct = (close - prev_close) / prev_close
        prev_close = close

        results.append({
            "date": date_idx.strftime("%Y-%m-%d"),
            "open": round(safe_num(row.get("Open", 0)), 4),
            "high": round(safe_num(row.get("High", 0)), 4),
            "low": round(safe_num(row.get("Low", 0)), 4),
            "close": round(close, 4),
            "volume": int(safe_num(row.get("Volume", 0))),
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


def fetch_market_overview(force_refresh: bool = False) -> Dict[str, Any]:
    """获取市场总览快照：主要指数、波动率、加密、商品的最新价与涨跌幅。

    供首页 Dashboard 的「市场总览」板块使用，呈现宏观市场环境（Bloomberg 风格）。
    使用 yfinance 的 fast_info / history 批量拉取，单条失败不影响其余条目。

    Returns:
        {
          "as_of": ISO 时间戳,
          "items": [{key, symbol, name, group, price, change, change_pct, currency}, ...],
          "source": "yfinance" | "partial" | "none",
        }
    """
    cache_key = "market_overview"
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    # (key, yfinance symbol, 展示名, 分组)
    instruments = [
        ("sp500", "^GSPC", "S&P 500", "指数"),
        ("nasdaq", "^IXIC", "纳斯达克", "指数"),
        ("dow", "^DJI", "道琼斯", "指数"),
        ("vix", "^VIX", "VIX 恐慌指数", "波动率"),
        ("us10y", "^TNX", "美债10年", "利率"),
        ("hsi", "^HSI", "恒生指数", "指数"),
        ("csi300", "000300.SS", "沪深300", "指数"),
        ("gold", "GC=F", "黄金", "商品"),
        ("oil", "CL=F", "原油 WTI", "商品"),
        ("btc", "BTC-USD", "比特币", "加密"),
        ("eth", "ETH-USD", "以太坊", "加密"),
        ("dxy", "DX-Y.NYB", "美元指数", "汇率"),
    ]

    items: List[Dict[str, Any]] = []
    ok_count = 0
    try:
        yf = _get_yfinance()
    except Exception:
        result = {"as_of": _now_iso(), "items": [], "source": "none"}
        _cache_set(cache_key, result)
        return result

    for key, symbol, name, group in instruments:
        price = 0.0
        prev = 0.0
        currency = "USD"
        try:
            tk = yf.Ticker(symbol)
            # fast_info 比 .info 轻量且更快
            fi = getattr(tk, "fast_info", None)
            if fi is not None:
                price = _safe_float(getattr(fi, "last_price", 0)) or _safe_float(
                    fi.get("lastPrice") if hasattr(fi, "get") else 0
                )
                prev = _safe_float(getattr(fi, "previous_close", 0)) or _safe_float(
                    fi.get("previousClose") if hasattr(fi, "get") else 0
                )
                currency = (getattr(fi, "currency", None) or "USD")
            # 回退：用 2 日历史
            if price <= 0 or prev <= 0:
                hist = tk.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = [c for c in hist["Close"].tolist() if c and c == c]
                    if closes:
                        price = price or float(closes[-1])
                        prev = prev or (float(closes[-2]) if len(closes) >= 2 else float(closes[-1]))
        except Exception as exc:
            logger.debug("market overview fetch failed for %s: %s", symbol, exc)

        change = (price - prev) if (price and prev) else 0.0
        change_pct = (change / prev) if prev else 0.0
        if price > 0:
            ok_count += 1
        items.append({
            "key": key,
            "symbol": symbol,
            "name": name,
            "group": group,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 4),
            "currency": currency,
        })

    source = "yfinance" if ok_count == len(instruments) else ("partial" if ok_count else "none")
    result = {"as_of": _now_iso(), "items": items, "source": source}
    # 市场总览缓存时间略短（60s）以保证一定的实时性
    with _cache_lock:
        _cache[cache_key] = {"value": result, "ts": time.time() - (_CACHE_TTL - 60)}
    return result


def _safe_float(value: Any) -> float:
    """轻量级安全 float 转换（用于市场总览）。"""
    try:
        f = float(value)
        if f != f or f in (float("inf"), float("-inf")):
            return 0.0
        return f
    except (TypeError, ValueError):
        return 0.0


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_hot_tickers(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """获取热门标的实时行情（供首页 Hot Tickers 面板使用）。

    包含主要科技股及加密货币，返回每个标的的 symbol, name, price, change_pct, market_cap。
    缓存 90 秒。yfinance 不可用时优雅降级为空列表。

    Returns:
        [{symbol, name, price, change_pct, market_cap}, ...]
    """
    cache_key = "hot_tickers"
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    # 热门标的列表及中文名映射
    HOT_SYMBOLS = [
        ("AAPL", "苹果"),
        ("NVDA", "英伟达"),
        ("TSLA", "特斯拉"),
        ("MSFT", "微软"),
        ("GOOGL", "谷歌"),
        ("AMZN", "亚马逊"),
        ("BTC-USD", "比特币"),
        ("ETH-USD", "以太坊"),
        ("META", "Meta"),
        ("AMD", "AMD"),
    ]

    try:
        yf = _get_yfinance()
    except Exception:
        result: List[Dict[str, Any]] = []
        _cache_set(cache_key, result)
        return result

    items: List[Dict[str, Any]] = []
    for symbol, name_cn in HOT_SYMBOLS:
        price = 0.0
        prev = 0.0
        market_cap = 0.0
        try:
            tk = yf.Ticker(symbol)
            fi = getattr(tk, "fast_info", None)
            if fi is not None:
                price = _safe_float(getattr(fi, "last_price", 0)) or _safe_float(
                    fi.get("lastPrice") if hasattr(fi, "get") else 0
                )
                prev = _safe_float(getattr(fi, "previous_close", 0)) or _safe_float(
                    fi.get("previousClose") if hasattr(fi, "get") else 0
                )
                market_cap = _safe_float(getattr(fi, "market_cap", 0)) or _safe_float(
                    fi.get("marketCap") if hasattr(fi, "get") else 0
                )
            # 回退：用历史数据
            if price <= 0 or prev <= 0:
                hist = tk.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = [c for c in hist["Close"].tolist() if c and c == c]
                    if closes:
                        price = price or float(closes[-1])
                        prev = prev or (float(closes[-2]) if len(closes) >= 2 else float(closes[-1]))
        except Exception as exc:
            logger.debug("hot ticker fetch failed for %s: %s", symbol, exc)

        change_pct = ((price - prev) / prev) if prev else 0.0
        items.append({
            "symbol": symbol,
            "name": name_cn,
            "price": round(price, 2),
            "change_pct": round(change_pct, 4),
            "market_cap": round(market_cap, 0),
        })

    # 使用 90 秒 TTL 缓存
    with _cache_lock:
        _cache[cache_key] = {"value": items, "ts": time.time() - (_CACHE_TTL - 90)}
    return items


def search_ticker(query: str) -> List[Dict]:
    """
    Search for tickers by name/symbol.

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
