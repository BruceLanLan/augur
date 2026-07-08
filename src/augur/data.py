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
import math
import re
import threading
import time
from dataclasses import fields as _dataclass_fields
from datetime import datetime
from typing import Any, Dict, List, Optional

from augur.personas.base import MarketContext

logger = logging.getLogger(__name__)


# ============ Error UX helpers ============
#
# 数据获取链路中存在多类“静默失败”路径（yfinance 不可用、网络异常、数据源返回空 dict、
# 未知 ticker 等），原先调用方只能靠 ``data_source=="none"`` 推断，无法区分失败原因。
# 下面提供一个轻量级 list 子类 ``_ResultList``，允许在 list 上挂载 ``data_error`` 字段，
# 完全向后兼容（``isinstance(x, list)`` 仍为 True）。

class _ResultList(list):
    """list 子类，可挂载 ``data_error`` 字段。

    用于 ``fetch_history`` / ``fetch_hot_tickers`` 等返回 list 的接口，
    在出现数据获取失败时附带用户可读的错误信息。
    ``data_error`` 默认为 ``None``（成功时）。
    """

    data_error: Optional[str] = None
    data_source: Optional[str] = None


def _attach_error(result: Any, message: str, source: Optional[str] = None) -> Any:
    """给返回值（list / dict / MarketContext）附加 ``data_error``，并返回。

    - list: 转 ``_ResultList`` 并挂 ``data_error``（同时支持 ``data_source``）
    - dict: 写入 ``data_error`` 键
    - MarketContext: 通过 ``setattr`` 挂动态属性
    - 其他: 透传，不附加
    """
    if isinstance(result, list) and not isinstance(result, _ResultList):
        result = _ResultList(result)
    if isinstance(result, _ResultList):
        result.data_error = message
        if source is not None:
            result.data_source = source
    elif isinstance(result, dict):
        result.setdefault("data_error", message)
        if source is not None:
            result.setdefault("data_source", source)
    else:
        try:
            setattr(result, "data_error", message)
            if source is not None:
                setattr(result, "data_source", source)
        except Exception:  # pragma: no cover - defensive
            pass
    return result


# ============ Cache ============
# Simple in-memory cache with TTL and LRU eviction.
# Max 100 entries; when exceeded, the oldest 20+ entries (by timestamp) are
# evicted down to 80 to provide headroom and avoid evicting on every insert.

_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 180  # 3 minutes
_CACHE_MAX_SIZE = 100
_CACHE_EVICT_TARGET = 80


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
    """Set cache entry with LRU eviction.

    Enforces a maximum of _CACHE_MAX_SIZE (100) entries. When the limit is
    exceeded, evicts the oldest entries by timestamp down to _CACHE_EVICT_TARGET
    (80) to provide headroom and avoid evicting on every insert.
    """
    with _cache_lock:
        _cache[key] = {"value": value, "ts": time.time()}
        if len(_cache) > _CACHE_MAX_SIZE:
            # Sort entries by timestamp ascending, evict oldest
            sorted_keys = sorted(_cache.keys(), key=lambda k: _cache[k]["ts"])
            evict_count = len(_cache) - _CACHE_EVICT_TARGET
            for k in sorted_keys[:evict_count]:
                del _cache[k]


def clear_cache() -> None:
    """Clear all cached data entries."""
    with _cache_lock:
        _cache.clear()


def reset_providers_cache() -> None:
    """Reset the lazy provider chain cache (for tests and hot-reload)."""
    global _providers_cache
    with _providers_lock:
        _providers_cache = None


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

    - Accepts str only; non-str inputs (None, int, list, etc.) are rejected
      with ValueError instead of an uncaught ``AttributeError`` from
      ``str.strip``.
    - Strips whitespace and uppercases
    - Validates: 1-15 chars, only alphanumeric, dots, hyphens
    - Raises ValueError if invalid
    """
    if not isinstance(ticker, str):
        raise ValueError(
            f"Ticker must be a string, got {type(ticker).__name__}: {ticker!r}"
        )
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Ticker cannot be empty")
    if len(ticker) > 15:
        raise ValueError(f"Ticker too long (max 15 chars): {ticker}")
    if '..' in ticker:
        raise ValueError(f"Invalid ticker format (consecutive dots not allowed): {ticker}")
    if not re.match(r'^[A-Z0-9.\-]+$', ticker):
        raise ValueError(f"Invalid ticker format (only alphanumeric, dots, hyphens allowed): {ticker}")
    # Reject leading/trailing punctuation: ".AAPL", "AAPL.", "-AAPL", "AAPL-"
    # are syntactically allowed by the regex but never valid ticker symbols.
    if ticker[0] in '.-' or ticker[-1] in '.-':
        raise ValueError(
            f"Invalid ticker format (must not start or end with '.' or '-'): {ticker}"
        )
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
    - 失败时同时附带 ``data_error`` 字段，给出人类可读的具体原因（区分网络错误、
      数据源返回空、未知 ticker 等场景），避免调用方只能靠 ``data_source=="none"`` 推断。
    """
    valid_fields = _market_context_field_names()
    upper = ticker.upper()

    errors: List[str] = []

    for provider in _get_providers():
        name = getattr(provider, "name", provider.__class__.__name__)
        try:
            raw = provider.fetch(ticker)
        except Exception as exc:
            msg = f"{name} failed: {exc}"
            logger.warning("data provider '%s' failed for %s: %s", name, ticker, exc)
            errors.append(msg)
            continue
        if not raw:
            msg = f"{name} returned empty data"
            logger.warning("data provider '%s' returned empty data for %s", name, ticker)
            errors.append(msg)
            continue

        source = raw.pop("data_source", name)
        # 仅保留 MarketContext 合法字段，避免未知键导致 TypeError
        kwargs = {k: v for k, v in raw.items() if k in valid_fields and k != "ticker"}
        ctx = MarketContext(ticker=upper, **kwargs)
        setattr(ctx, "data_source", source)
        return ctx

    # 所有数据源均失败：返回空 context，但带来源标记与具体错误，便于下游识别“无数据”状态
    logger.warning("all data providers failed for %s; returning empty context", ticker)
    ctx = MarketContext(ticker=upper)
    setattr(ctx, "data_source", "none")
    if errors:
        setattr(ctx, "data_error", f"all providers failed for {ticker}: " + "; ".join(errors))
    else:
        setattr(ctx, "data_error", f"no data available for {ticker}")
    return ctx


# ============ Public API ============

# Fields fetch_edgar_fundamentals can compute, in the exact shape it
# returns them -- see _overlay_edgar_fundamentals below.
_EDGAR_OVERLAY_FIELDS = (
    "pe", "pb", "roe", "gross_margins", "operating_margins",
    "revenue_growth", "earnings_growth", "debt_ratio", "market_cap",
)


def _overlay_edgar_fundamentals(ctx: MarketContext) -> None:
    """Overlay EDGAR-sourced fundamentals onto an already-built context,
    field by field -- mutates ``ctx`` in place.

    Deliberately NOT a provider in the yfinance/stooq chain: that chain is
    "first success wins" (whichever provider returns first replaces the
    whole context), which is wrong for EDGAR -- it only ever has
    fundamentals, never price/sector/industry/rsi/sma/etc., so if it were
    inserted as a chain provider ahead of yfinance and "succeeded" the rest
    of the context would come back empty. Instead this runs *after* the
    existing chain has already populated everything, and replaces only the
    specific fields EDGAR actually computed (each is 0.0, its own "could not
    compute" sentinel, when EDGAR has nothing -- in which case the existing
    yfinance/stooq value is left untouched). Never raises: any failure here
    just leaves the context exactly as the provider chain built it.
    """
    if not ctx.price or ctx.price <= 0:
        return
    try:
        from augur.consensus.edgar_fundamentals import fetch_edgar_fundamentals

        today = datetime.now().strftime("%Y-%m-%d")
        edgar = fetch_edgar_fundamentals(ctx.ticker, today, price=ctx.price)
        if edgar.get("insufficient"):
            return
        applied = []
        for field in _EDGAR_OVERLAY_FIELDS:
            value = edgar.get(field)
            if value:
                setattr(ctx, field, value)
                applied.append(field)
        if applied:
            setattr(ctx, "fundamentals_source", "edgar")
            logger.debug("EDGAR overlay applied for %s: %s", ctx.ticker, applied)
    except Exception:
        logger.debug("EDGAR overlay failed for %s", ctx.ticker, exc_info=True)


def fetch_market_context(ticker: str, force_refresh: bool = False) -> MarketContext:
    """
    Fetch real-time data for a ticker and return a populated MarketContext.

    内部走 provider 链（yfinance -> stooq -> 空 context），对调用方完全透明。
    返回的 MarketContext 带有动态属性 ``data_source``，标记实际命中的数据源
    （"yfinance" / "stooq" / "none"）。

    在 provider 链之后，针对有 SEC CIK 的美股标的做一层字段级覆盖：
    pe/pb/roe/gross_margins/operating_margins/revenue_growth/earnings_growth/
    debt_ratio/market_cap 若能从 SEC EDGAR 真实财报算出（不含 0），优先采用，
    yfinance 的值仅在 EDGAR 算不出时保留。非美股 / 无 CIK / EDGAR 不可用时静默
    跳过，不影响原有数据。命中时 context 上追加动态属性
    ``fundamentals_source="edgar"``。

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
    try:
        ticker = _normalize_ticker(ticker)
    except ValueError as exc:
        logger.warning("invalid ticker rejected: %s", exc)
        # 兜底展示名：非字符串输入直接用 repr 避免再次触发 AttributeError
        fallback = ticker.strip().upper() if isinstance(ticker, str) else "INVALID"
        ctx = MarketContext(ticker=fallback)
        setattr(ctx, "data_source", "error")
        setattr(ctx, "data_error", f"invalid ticker: {exc}")
        return ctx

    cache_key = f"ctx:{ticker}"
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    ctx = _build_context_from_providers(ticker)
    _overlay_edgar_fundamentals(ctx)
    _cache_set(cache_key, ctx)
    return ctx


def fetch_market_context_batch(tickers: List[str], max_workers: int = 5) -> Dict[str, MarketContext]:
    """Fetch multiple tickers in parallel using ThreadPoolExecutor.

    Args:
        tickers: List of stock symbols to fetch. Non-list inputs (e.g. a bare
            string or None) are rejected with an empty result and a single
            ``INVALID`` entry that carries a ``data_error`` describing the
            misuse, so callers don't crash with ``TypeError`` and don't
            silently get one context per character of a string.
        max_workers: Maximum number of concurrent threads.

    Returns:
        Dict mapping each ticker to its MarketContext (empty context on failure).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # 校验顶层输入：防止把 str / None 当作可迭代对象（之前会被当作逐字符迭代，悄无声息地污染结果）
    if tickers is None:
        ctx = MarketContext(ticker="INVALID")
        setattr(ctx, "data_source", "error")
        setattr(ctx, "data_error", (
            f"invalid tickers argument: expected list, got "
            f"{type(tickers).__name__}"
        ))
        logger.warning("batch fetch rejected tickers=None")
        return {"INVALID": ctx}

    if not isinstance(tickers, (list, tuple)):
        ctx = MarketContext(ticker="INVALID")
        setattr(ctx, "data_source", "error")
        setattr(ctx, "data_error", (
            f"invalid tickers argument: expected list, got "
            f"{type(tickers).__name__}"
        ))
        logger.warning("batch fetch rejected tickers of type %s", type(tickers).__name__)
        return {"INVALID": ctx}

    if len(tickers) == 0:
        return {}

    # Validate max_workers: must be a positive int. Reject bool (subclass of int,
    # but semantically wrong here), floats, zero, and negatives. Cap at a sane
    # ceiling so a typo like max_workers=1_000_000 can't exhaust file descriptors.
    if isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1 or max_workers > 64:
        ctx = MarketContext(ticker="INVALID")
        setattr(ctx, "data_source", "error")
        setattr(ctx, "data_error", (
            f"invalid max_workers: expected int in [1, 64], got "
            f"{max_workers!r} ({type(max_workers).__name__})"
        ))
        logger.warning("batch fetch rejected max_workers=%r", max_workers)
        return {"INVALID": ctx}

    results: Dict[str, MarketContext] = {}
    norm_to_origs: Dict[str, List[str]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {}
        for t in tickers:
            try:
                norm = _normalize_ticker(t)
            except ValueError as exc:
                logger.warning("batch fetch skipped invalid ticker %s: %s", t, exc)
                # 字符串类型的非法 ticker 沿用旧行为（strip 后大写）以便在结果中可读；
                # 非字符串元素用 repr 安全地表示为 "INVALID"，避免再次崩溃
                key = t.strip().upper() if isinstance(t, str) else "INVALID"
                ctx = MarketContext(ticker=key or "INVALID")
                setattr(ctx, "data_source", "error")
                setattr(ctx, "data_error", f"invalid ticker: {exc}")
                results[str(t) if not isinstance(t, str) else t] = ctx
                continue
            norm_to_origs.setdefault(norm, []).append(t)
            if norm not in future_to_ticker.values():
                future_to_ticker[executor.submit(fetch_market_context, norm)] = norm
        for future in as_completed(future_to_ticker):
            norm = future_to_ticker[future]
            try:
                ctx = future.result()
            except Exception as e:
                logger.warning("batch fetch failed for %s: %s", norm, e)
                ctx = MarketContext(ticker=norm)
                setattr(ctx, "data_source", "error")
                setattr(ctx, "data_error", f"batch fetch failed: {e}")
            for orig in norm_to_origs.get(norm, []):
                results[orig] = ctx
    return results


def fetch_history(ticker: str, period: str = "1y", force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch historical price data.

    Args:
        ticker: Stock symbol (e.g. AAPL, 0700.HK, 600519.SS)
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
        force_refresh: If True, bypass the cache and fetch fresh data

    Returns:
        :class:`_ResultList` of ``{date, open, high, low, close, volume, change_pct}``。
        失败时返回空 ``_ResultList``，并附带 ``data_error`` 字段描述失败原因
        （``"invalid_ticker"`` / ``"yfinance_unavailable"`` / ``"network_error: ..."`` /
        ``"no_data: <ticker> returned empty history"``）。``isinstance(result, list)`` 仍为 True。
    """
    from augur.datasources.base import safe_num

    try:
        ticker = _normalize_ticker(ticker)
    except ValueError as exc:
        logger.warning("invalid ticker rejected for history: %s", exc)
        return _attach_error(
            _ResultList(), f"invalid ticker: {exc}", source="error"
        )

    cache_key = f"hist:{ticker}:{period}"
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            # 缓存值若已是 _ResultList 直接返回；否则透传（保持向后兼容）
            if isinstance(cached, list) and not isinstance(cached, _ResultList):
                cached = _ResultList(cached)
            return cached

    try:
        yf = _get_yfinance()
    except Exception as exc:
        msg = f"yfinance_unavailable: {exc}"
        logger.warning("history: yfinance unavailable: %s", exc)
        return _attach_error(_ResultList(), msg, source="error")

    stock = yf.Ticker(ticker)

    try:
        hist = stock.history(period=period)
    except Exception as exc:
        msg = f"network_error: failed to fetch history for {ticker}: {exc}"
        logger.warning("history: network error for %s: %s", ticker, exc)
        return _attach_error(_ResultList(), msg, source="error")

    if hist is None or hist.empty:
        return _attach_error(
            _ResultList(),
            f"no_data: {ticker} returned empty history for period={period}",
            source="yfinance",
        )

    results: _ResultList = _ResultList()
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
    closes = _sanitize_price_series(
        [p["close"] for p in prices if "close" in p]
    )
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
        ("ftse", "^FTSE", "富时100", "指数"),
        ("dax", "^GDAXI", "德国DAX", "指数"),
        ("nikkei", "^N225", "日经225", "指数"),
        ("gold", "GC=F", "黄金", "商品"),
        ("oil", "CL=F", "原油 WTI", "商品"),
        ("btc", "BTC-USD", "比特币", "加密"),
        ("eth", "ETH-USD", "以太坊", "加密"),
        ("dxy", "DX-Y.NYB", "美元指数", "汇率"),
    ]

    items: List[Dict[str, Any]] = []
    ok_count = 0
    yfinance_error: Optional[str] = None
    try:
        yf = _get_yfinance()
    except Exception as exc:
        yfinance_error = f"yfinance_unavailable: {exc}"
        logger.warning("market overview: yfinance unavailable: %s", exc)
        result = {"as_of": _now_iso(), "items": [], "source": "none",
                  "data_error": yfinance_error}
        _cache_set(cache_key, result)
        return result

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    def _fetch_one_instrument(entry):
        """Fetch a single instrument's price data with isolation."""
        key, symbol, name, group = entry
        price = 0.0
        prev = 0.0
        currency = "USD"
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
                currency = (getattr(fi, "currency", None) or "USD")
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
        return {
            "key": key,
            "symbol": symbol,
            "name": name,
            "group": group,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 4),
            "currency": currency,
        }

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_one_instrument, inst): inst for inst in instruments}
        for future in futures:
            try:
                item = future.result(timeout=10)
                items.append(item)
                if item["price"] > 0:
                    ok_count += 1
            except (FuturesTimeoutError, Exception) as exc:
                inst = futures[future]
                logger.debug("market overview timeout/error for %s: %s", inst[1], exc)
                items.append({
                    "key": inst[0],
                    "symbol": inst[1],
                    "name": inst[2],
                    "group": inst[3],
                    "price": 0.0,
                    "change": 0.0,
                    "change_pct": 0.0,
                    "currency": "USD",
                })

    source = "yfinance" if ok_count == len(instruments) else ("partial" if ok_count else "none")
    result = {"as_of": _now_iso(), "items": items, "source": source}
    if source != "yfinance":
        # 部分或全部失败时给出可读原因，避免前端无法区分“网络断”与“市场闭市”
        if ok_count == 0:
            result["data_error"] = (
                f"all {len(instruments)} instruments failed; "
                "market overview is empty"
            )
        else:
            failed = len(instruments) - ok_count
            result["data_error"] = (
                f"{failed}/{len(instruments)} instruments failed; "
                "showing partial data"
            )
    # 市场总览缓存 60 秒：通过预置时间戳老化实现（_CACHE_TTL=180, 预老化 120s, 有效剩余 60s）
    with _cache_lock:
        _cache[cache_key] = {"value": result, "ts": time.time() - (_CACHE_TTL - 60)}
    return result


def _safe_float(value: Any) -> float:
    """轻量级安全 float 转换（用于市场总览）。

    拒绝 ``bool``（在 Python 中 ``bool`` 是 ``int`` 的子类，``float(True)`` 会
    悄无声息地得到 ``1.0``，把一个布尔标记变成一个伪造的报价/市值）。其他非数值
    类型（``None``、list、dict 等）走 ``TypeError`` 路径返回 0.0。``NaN`` / ``±inf``
    也归一化为 0.0，避免污染下游计算。
    """
    if isinstance(value, bool):
        return 0.0
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
    except Exception as exc:
        logger.warning("hot tickers: yfinance unavailable: %s", exc)
        result: _ResultList = _ResultList()
        result.data_error = f"yfinance_unavailable: {exc}"
        result.data_source = "error"
        _cache_set(cache_key, result)
        return result

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    def _fetch_one_hot(entry):
        """Fetch a single hot ticker's data with isolation."""
        symbol, name_cn = entry
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
        return {
            "symbol": symbol,
            "name": name_cn,
            "price": round(price, 2),
            "change_pct": round(change_pct, 4),
            "market_cap": round(market_cap, 0),
        }

    items: _ResultList = _ResultList()
    failed_symbols: List[str] = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_one_hot, entry): entry for entry in HOT_SYMBOLS}
        for future in futures:
            try:
                item = future.result(timeout=10)
                items.append(item)
                if item["price"] <= 0:
                    failed_symbols.append(item["symbol"])
            except (FuturesTimeoutError, Exception) as exc:
                entry = futures[future]
                logger.debug("hot ticker timeout/error for %s: %s", entry[0], exc)
                failed_symbols.append(entry[0])
                items.append({
                    "symbol": entry[0],
                    "name": entry[1],
                    "price": 0.0,
                    "change_pct": 0.0,
                    "market_cap": 0.0,
                })

    if failed_symbols:
        items.data_error = (
            f"{len(failed_symbols)}/{len(HOT_SYMBOLS)} tickers failed: "
            + ", ".join(failed_symbols)
        )
    items.data_source = "yfinance"

    # 热门标的缓存 90 秒：通过预置时间戳老化实现（_CACHE_TTL=180, 预老化 90s, 有效剩余 90s）
    with _cache_lock:
        _cache[cache_key] = {"value": items, "ts": time.time() - (_CACHE_TTL - 90)}
    return items


def search_ticker(query: str) -> List[Dict[str, Any]]:
    """
    Search for tickers by name/symbol.

    Args:
        query: Search string (ticker symbol or company name). Must be a
            non-empty string; non-string / empty / invalid inputs return an
            empty ``_ResultList`` with a ``data_error`` describing the
            rejection, matching the rest of the data module's UX.

    Returns:
        List of dicts with keys: symbol, name, exchange, type. Returned as a
        ``_ResultList`` (``isinstance(result, list) == True``) that carries
        ``data_error`` / ``data_source`` on failure paths.
    """
    # 与模块其他接口一致：非字符串、空串、非法 ticker 都优雅降级，不再抛出 AttributeError / ImportError。
    try:
        normalized = _normalize_ticker(query)
    except ValueError as exc:
        logger.warning("search_ticker rejected query %r: %s", query, exc)
        return _attach_error(
            _ResultList(), f"invalid query: {exc}", source="error"
        )

    try:
        yf = _get_yfinance()
    except Exception as exc:
        logger.warning("search_ticker: yfinance unavailable: %s", exc)
        return _attach_error(
            _ResultList(), f"yfinance_unavailable: {exc}", source="error"
        )

    results: _ResultList = _ResultList()
    try:
        # yfinance search is limited; use Ticker info as fallback
        # Try direct ticker lookup first
        stock = yf.Ticker(normalized)
        info = stock.info or {}
        if info.get("symbol"):
            results.append({
                "symbol": info.get("symbol", normalized),
                "name": info.get("longName") or info.get("shortName", ""),
                "exchange": info.get("exchange", ""),
                "type": info.get("quoteType", "EQUITY"),
            })
    except Exception as exc:
        # 网络/解析失败不再静默吞掉，附 data_error 让调用方区分“无结果” vs “拉取失败”
        logger.warning("search_ticker fetch failed for %s: %s", normalized, exc)
        return _attach_error(
            results, f"network_error: failed to search {normalized}: {exc}",
            source="error",
        )

    results.data_source = "yfinance"
    return results


# ============ Internal Helpers ============

def _sanitize_price_series(closes: List[Any]) -> List[float]:
    """Drop non-finite, bool-coerced, and non-positive closing prices."""
    clean: List[float] = []
    for c in closes:
        if isinstance(c, bool):
            continue
        try:
            v = float(c)
        except (TypeError, ValueError):
            continue
        if math.isfinite(v) and v > 0:
            clean.append(v)
    return clean


def _calculate_technicals_from_prices(closes: List[float]) -> Dict[str, Any]:
    """Calculate technical indicators from a list of closing prices."""
    result = {}

    closes = _sanitize_price_series(closes)
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
    closes = _sanitize_price_series(closes)
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
    closes = _sanitize_price_series(closes)
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
