# -*- coding: utf-8 -*-
"""
augur.datasources.yfinance_provider - yfinance 数据源

把原先散落在 data.py 中的 yfinance 抓取 + 单位换算逻辑封装为一个 provider。

修复的数据引用 bug（详见各处注释）:
  1. NaN/None 守卫失效: 原代码用 ``info.get(k, 0) or 0``，但 ``nan or 0`` 返回 nan，
     导致 NaN 污染 MarketContext，引发下游 persona 评分异常。改用 ``safe_num``。
  2. 单位换算: market_cap / fcf / revenue 统一换算为“十亿 USD”；
     institutional/insider ownership 由 0-1 比例换算为 0-100 百分比并裁剪到合理区间；
     ROE / 毛利率 / 增长率保持 yfinance 原生的 0-1 小数。
  3. debt_to_equity -> debt_ratio: yfinance 的 debtToEquity 为百分比（162 表示 1.62），
     先 /100 得 D/E，再 D/A = D/E/(1+D/E)；对 None/NaN/<=0（负权益）安全归零。
  4. 货币（v14）: yfinance 的金额字段是原币。市值 / EV 按交易货币（``currency``）、
     FCF / 营收 / EBITDA / 现金 / 负债按财报货币（``financialCurrency``）换算为
     十亿美元；股价保持交易货币。汇率取不到时整体不换算、``fx_rate_usd=0``，
     并给出一条 ``data_warnings``。
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from augur.datasources.base import DataProvider, DataProviderError, clamp, safe_num
from augur.datasources.fund_profile import (
    asset_type_for,
    cn_etf_code,
    build_etf_profile,
    dated_closes_from_history,
)

logger = logging.getLogger(__name__)


# ============ FX (v14) ============

# yfinance quotes some markets in a minor unit: the price is in pence /
# cents / agorot while marketCap and the statements are in the major unit
# (checked live: SHEL.L currency "GBp", price 3555.5, marketCap 2.0e11 GBP).
_MINOR_UNITS: Dict[str, Tuple[str, float]] = {
    "GBp": ("GBP", 0.01),
    "GBX": ("GBP", 0.01),
    "ZAc": ("ZAR", 0.01),
    "ZAC": ("ZAR", 0.01),
    "ILA": ("ILS", 0.01),
}

_FX_TTL_SECONDS = 6 * 3600
_fx_cache: Dict[str, Tuple[float, float]] = {}
_fx_lock = threading.Lock()


def split_currency(ccy: str) -> Tuple[str, float]:
    """Return ``(major_currency, unit_factor)`` for a yfinance currency code.

    ``unit_factor`` converts one quoted unit into the major unit
    (``"GBp" -> ("GBP", 0.01)``); ordinary codes map to themselves with 1.0.
    Empty input returns ``("", 1.0)``.
    """
    ccy = (ccy or "").strip()
    if not ccy:
        return "", 1.0
    if ccy in _MINOR_UNITS:
        return _MINOR_UNITS[ccy]
    return ccy.upper(), 1.0


def clear_fx_cache() -> None:
    """Drop cached FX rates (called from ``augur.data.clear_cache``)."""
    with _fx_lock:
        _fx_cache.clear()


def _fx_to_usd(ccy: str) -> float:
    """USD per one unit of the *major* currency ``ccy``; 0.0 when unknown.

    Uses the latest close of yfinance's ``<CCY>USD=X``. Successful lookups
    are cached for a few hours; failures are not cached. Tests replace this
    function (``monkeypatch.setattr(yfinance_provider, "_fx_to_usd", ...)``).
    """
    ccy = (ccy or "").strip().upper()
    if not ccy:
        return 0.0
    if ccy == "USD":
        return 1.0
    now = time.time()
    with _fx_lock:
        hit = _fx_cache.get(ccy)
        if hit is not None and now - hit[1] < _FX_TTL_SECONDS:
            return hit[0]
    try:
        from augur import data as _data

        yf = _data._get_yfinance()
        hist = yf.Ticker(f"{ccy}USD=X").history(period="5d")
        closes = [safe_num(c) for c in hist["Close"].tolist()]
        closes = [c for c in closes if c > 0]
        rate = float(closes[-1]) if closes else 0.0
    except Exception as exc:
        logger.warning("FX lookup %sUSD failed: %s", ccy, exc)
        return 0.0
    if not (0 < rate < 1e6):
        return 0.0
    with _fx_lock:
        _fx_cache[ccy] = (rate, now)
    return rate


def resolve_fx(currency: str, financial_currency: str) -> Dict[str, Any]:
    """Work out the FX factors for one instrument.

    Returns a dict with:
      ``converted``   True when every amount can be expressed in USD
      ``price_rate``  USD per quoted price unit (``MarketContext.fx_rate_usd``)
      ``cap_rate``    USD per major trading-currency unit (market cap, EV, AUM)
      ``fin_rate``    USD per financial-currency unit (FCF, revenue, ...)
      ``warning``     human-readable reason when not converted, else ""

    All-or-nothing: if either leg's rate is missing nothing is converted, so
    a context never mixes USD and local amounts. An empty ``currency`` means
    "unknown" (stooq, hand-built contexts) and is left as-is with no warning.
    """
    major, factor = split_currency(currency)
    fin_major, _ = split_currency(financial_currency or currency)
    out = {"converted": False, "price_rate": 0.0, "cap_rate": 0.0, "fin_rate": 0.0, "warning": ""}
    if not major:
        return out
    cap_rate = _fx_to_usd(major)
    fin_rate = cap_rate if fin_major == major else _fx_to_usd(fin_major)
    if cap_rate > 0 and fin_rate > 0:
        out.update(converted=True, price_rate=cap_rate * factor, cap_rate=cap_rate, fin_rate=fin_rate)
        return out
    missing = [c for c, r in ((major, cap_rate), (fin_major, fin_rate)) if r <= 0]
    missing = sorted(set(missing))
    legs = f"market cap in {major}"
    legs += f", financials in {fin_major}" if fin_major else ""
    out["warning"] = (
        f"FX rate unavailable for {'/'.join(missing)}: amounts not converted to USD ({legs})"
    )
    return out


class YFinanceProvider(DataProvider):
    """基于 yfinance 的主数据源。

    为保持与既有测试（``patch("augur.data._get_yfinance")``）的兼容性，
    默认在**调用时**通过属性查找解析 ``augur.data._get_yfinance`` 与
    ``augur.data._calculate_technicals_from_prices``，而非在构造时捕获引用。
    """

    name = "yfinance"

    def __init__(
        self,
        yf_loader: Optional[Callable[[], Any]] = None,
        technicals_fn: Optional[Callable[[List[float]], Dict[str, Any]]] = None,
    ) -> None:
        self._yf_loader = yf_loader
        self._technicals_fn = technicals_fn

    # -- 延迟解析，确保 monkeypatch(augur.data._get_yfinance) 生效 --
    def _load_yf(self) -> Any:
        if self._yf_loader is not None:
            return self._yf_loader()
        from augur import data as _data
        return _data._get_yfinance()

    def _technicals(self, closes: List[float]) -> Dict[str, Any]:
        if self._technicals_fn is not None:
            return self._technicals_fn(closes)
        from augur import data as _data
        return _data._calculate_technicals_from_prices(closes)

    def fetch(self, ticker: str) -> Dict[str, Any]:
        yf = self._load_yf()
        stock = yf.Ticker(ticker)

        try:
            info = stock.info or {}
        except Exception as exc:  # 网络/解析异常 -> 触发 fallback
            raise DataProviderError(f"yfinance info error for {ticker}: {exc}") from exc

        # info 为空或缺少 'symbol' 视为无有效数据，触发 fallback 到下一个 provider
        if not info or "symbol" not in info:
            raise DataProviderError(f"yfinance returned no usable data for {ticker}")

        # ---- 估值 / 价格 (safe_num 统一处理 None/NaN) ----
        price = safe_num(info.get("currentPrice")) or safe_num(info.get("regularMarketPrice"))
        pe = safe_num(info.get("trailingPE"))
        pb = safe_num(info.get("priceToBook"))
        ps = safe_num(info.get("priceToSalesTrailing12Months"))
        forward_pe = safe_num(info.get("forwardPE"))
        peg_ratio = safe_num(info.get("trailingPegRatio")) or safe_num(info.get("pegRatio"))
        eps = safe_num(info.get("trailingEps"))
        forward_eps = safe_num(info.get("forwardEps"))

        # ---- 盈利能力 / 增长（yfinance 原生为 0-1 小数，保持不变）----
        roe = safe_num(info.get("returnOnEquity"))
        roa = safe_num(info.get("returnOnAssets"))
        gross_margins = safe_num(info.get("grossMargins"))
        operating_margins = safe_num(info.get("operatingMargins"))
        profit_margins = safe_num(info.get("profitMargins"))
        revenue_growth = safe_num(info.get("revenueGrowth"))
        earnings_growth = safe_num(info.get("earningsGrowth"))

        # ---- debt_to_equity -> debt_ratio ----
        # yfinance debtToEquity 是 D/E 百分比 (e.g. 162 => D/E=1.62)
        # D/A = D/E / (1 + D/E)。<=0（含负权益）或 NaN 安全归零，避免 ZeroDivisionError / 错误评分。
        debt_to_equity = safe_num(info.get("debtToEquity"))
        if debt_to_equity > 0:
            de_ratio = debt_to_equity / 100.0
            debt_ratio = de_ratio / (1.0 + de_ratio)
        else:
            debt_ratio = 0.0

        # ---- 货币: 交易货币 vs 财报货币 -> 美元换算因子 ----
        currency = info.get("currency") or ""
        financial_currency = info.get("financialCurrency") or currency
        fx = resolve_fx(currency, financial_currency)
        cap_rate = fx["cap_rate"] if fx["converted"] else 1.0
        fin_rate = fx["fin_rate"] if fx["converted"] else 1.0
        data_warnings: List[str] = [fx["warning"]] if fx["warning"] else []

        # ---- 现金流 / 规模 -> 统一换算为“十亿 USD”（汇率未知时保留原币）----
        fcf = safe_num(info.get("freeCashflow")) * fin_rate / 1e9
        market_cap = safe_num(info.get("marketCap")) * cap_rate / 1e9
        revenue = safe_num(info.get("totalRevenue")) * fin_rate / 1e9
        ebitda = safe_num(info.get("ebitda")) * fin_rate / 1e9
        enterprise_value = safe_num(info.get("enterpriseValue")) * cap_rate / 1e9
        total_cash = safe_num(info.get("totalCash")) * fin_rate / 1e9
        total_debt = safe_num(info.get("totalDebt")) * fin_rate / 1e9

        current_ratio = safe_num(info.get("currentRatio"))
        quick_ratio = safe_num(info.get("quickRatio"))
        sector = info.get("sector") or ""
        industry = info.get("industry") or ""
        business_summary = info.get("longBusinessSummary") or info.get("description") or ""
        volume = safe_num(info.get("volume")) or safe_num(info.get("regularMarketVolume"))
        avg_volume = safe_num(info.get("averageVolume")) or safe_num(info.get("averageVolume10days"))

        # ---- 公司元信息 / 行情扩展 ----
        company_name = info.get("longName") or info.get("shortName") or ""
        exchange = info.get("exchange") or info.get("fullExchangeName") or ""
        day_open = safe_num(info.get("regularMarketOpen")) or safe_num(info.get("open"))
        day_high = safe_num(info.get("regularMarketDayHigh")) or safe_num(info.get("dayHigh"))
        day_low = safe_num(info.get("regularMarketDayLow")) or safe_num(info.get("dayLow"))
        sma200 = safe_num(info.get("twoHundredDayAverage"))

        # ---- 股息 ----
        dividend_rate = safe_num(info.get("dividendRate"))
        # yfinance 的 dividendYield 格式不稳定（有时是 0.35 表示 0.35%，有时是 0.0035 小数）。
        # 最稳健的做法：当有每股股息与价格时，直接用 dividend_rate / price 计算真实收益率（小数）。
        if dividend_rate > 0 and price > 0:
            dividend_yield = dividend_rate / price
        else:
            dividend_yield = safe_num(info.get("dividendYield"))
            if dividend_yield > 1:  # 明显是百分数形式
                dividend_yield = dividend_yield / 100.0
        dividend_yield = clamp(dividend_yield, 0.0, 1.0)
        payout_ratio = clamp(safe_num(info.get("payoutRatio")), 0.0, 5.0)

        # ---- 分析师一致预期 ----
        target_mean_price = safe_num(info.get("targetMeanPrice"))
        target_high_price = safe_num(info.get("targetHighPrice"))
        target_low_price = safe_num(info.get("targetLowPrice"))
        recommendation_key = info.get("recommendationKey") or ""
        num_analyst_opinions = int(safe_num(info.get("numberOfAnalystOpinions")))

        # ---- 持股结构: 0-1 比例 -> 0-100 百分比，并裁剪到合理区间 ----
        institutional_ownership = clamp(safe_num(info.get("heldPercentInstitutions")) * 100, 0.0, 100.0)
        insider_ownership = clamp(safe_num(info.get("heldPercentInsiders")) * 100, 0.0, 100.0)

        # 做空比例: 占流通股的小数 (0-1)
        short_interest = safe_num(info.get("shortPercentOfFloat"))

        beta_1y = safe_num(info.get("beta"), default=1.0)

        # ---- 52 周高低点相对位置 (%) ----
        fifty_two_high = safe_num(info.get("fiftyTwoWeekHigh"))
        fifty_two_low = safe_num(info.get("fiftyTwoWeekLow"))
        price_vs_52w_high = ((price / fifty_two_high) - 1) * 100 if fifty_two_high and price else 0.0
        price_vs_52w_low = ((price / fifty_two_low) - 1) * 100 if fifty_two_low and price else 0.0

        # ---- 技术指标（基于 3 个月收盘价计算）----
        technicals: Dict[str, Any] = {}
        hist = None
        try:
            hist = stock.history(period="3mo")
            if hist is not None and not hist.empty:
                closes = [safe_num(c) for c in hist["Close"].tolist()]
                closes = [c for c in closes if c > 0]  # 过滤 NaN/0 收盘价
                if closes:
                    technicals = self._technicals(closes)
        except Exception:
            technicals = {}

        fields: Dict[str, Any] = {
            "price": price,
            "pe": pe,
            "pb": pb,
            "ps": ps,
            "roe": roe,
            "roa": roa,
            "gross_margins": gross_margins,
            "operating_margins": operating_margins,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "debt_ratio": debt_ratio,
            "fcf": fcf,
            "market_cap": market_cap,
            "revenue": revenue,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "sector": sector,
            "industry": industry,
            "business_summary": business_summary,
            "volume": volume,
            "avg_volume": avg_volume,
            "institutional_ownership": institutional_ownership,
            "insider_ownership": insider_ownership,
            "short_interest": short_interest,
            "beta_1y": beta_1y,
            "price_vs_52w_high": price_vs_52w_high,
            "price_vs_52w_low": price_vs_52w_low,
            # 新增: 公司元信息 / 行情扩展
            "company_name": company_name,
            "currency": currency,
            "financial_currency": financial_currency,
            "fx_rate_usd": fx["price_rate"],
            "exchange": exchange,
            "day_open": day_open,
            "day_high": day_high,
            "day_low": day_low,
            "fifty_two_week_high": fifty_two_high,
            "fifty_two_week_low": fifty_two_low,
            "sma200": sma200,
            # 新增: 估值 / 盈利扩展
            "forward_pe": forward_pe,
            "peg_ratio": peg_ratio,
            "eps": eps,
            "forward_eps": forward_eps,
            "profit_margins": profit_margins,
            "ebitda": ebitda,
            "enterprise_value": enterprise_value,
            "total_cash": total_cash,
            "total_debt": total_debt,
            # 新增: 股息
            "dividend_yield": dividend_yield,
            "dividend_rate": dividend_rate,
            "payout_ratio": payout_ratio,
            # 新增: 分析师一致预期
            "target_mean_price": target_mean_price,
            "target_high_price": target_high_price,
            "target_low_price": target_low_price,
            "recommendation_key": recommendation_key,
            "num_analyst_opinions": num_analyst_opinions,
            "rsi": technicals.get("rsi", 50),
            "macd": technicals.get("macd", 0),
            "macd_signal": technicals.get("macd_signal", 0),
            "macd_histogram": technicals.get("macd_histogram", 0),
            "sma20": technicals.get("sma20", 0),
            "sma50": technicals.get("sma50", 0),
            "atr": technicals.get("atr", 0),
            "volatility_20d": technicals.get("volatility_20d", 0),
            "data_source": self.name,
        }

        # ---- v14: ETF / 基金画像 ----
        asset_type = asset_type_for(ticker, info.get("quoteType") or "")
        fields["asset_type"] = asset_type
        if asset_type == "etf":
            self._apply_fund_profile(ticker, info, stock, hist, fields, fx, data_warnings)

        if data_warnings:
            fields["data_warnings"] = data_warnings
        return fields

    def _apply_fund_profile(self, ticker: str, info: Dict[str, Any], stock: Any, hist: Any,
                            fields: Dict[str, Any], fx: Dict[str, Any],
                            data_warnings: List[str]) -> None:
        """Fill ``fields["etf"]`` and strip company-valuation fields for a fund.

        Never raises: a failing ``funds_data`` only drops the keys it would
        have supplied.
        """
        try:
            funds_data = stock.funds_data
        except Exception as exc:
            logger.debug("funds_data unavailable for %s: %s", ticker, exc)
            funds_data = None
        converted = fx["converted"]
        dated_closes = dated_closes_from_history(hist)
        try:
            etf = build_etf_profile(
                ticker, info, funds_data, dated_closes,
                price=fields.get("price", 0.0), avg_volume=fields.get("avg_volume", 0.0),
                cap_rate=fx["cap_rate"] if converted else None,
                price_rate=fx["price_rate"] if converted else None,
            )
        except Exception as exc:  # defensive: profile is optional
            logger.warning("ETF profile failed for %s: %s", ticker, exc)
            etf = {"source": "yfinance"}
            data_warnings.append(f"ETF profile unavailable: {exc}")
        if "nav" not in etf and cn_etf_code(ticker):
            self._apply_cn_nav(ticker, etf, dated_closes)
        # Look-through P/E and P/B belong to the holdings, not the fund.
        fields["pe"] = 0.0
        fields["pb"] = 0.0
        # A fund's market value is its net assets; yfinance leaves marketCap empty.
        if not fields.get("market_cap") and etf.get("aum_usd_bn"):
            fields["market_cap"] = etf["aum_usd_bn"]
        fields["etf"] = etf

    @staticmethod
    def _apply_cn_nav(ticker: str, etf: Dict[str, Any], dated_closes: List[Any]) -> None:
        """Add the Sina NAV (with its real date) to an A-share ETF profile."""
        from augur.datasources import cn_fund_nav_provider as cn

        try:
            nav_info = cn.fetch_cn_fund_nav(ticker) or {}
        except Exception as exc:  # the lookup is optional; never fail the fetch
            logger.info("A-share NAV lookup failed for %s: %s", ticker, exc)
            return
        nav, nav_date = safe_num(nav_info.get("nav")), nav_info.get("nav_date") or ""
        if nav <= 0 or not nav_date:
            return
        etf["nav"] = nav
        etf["nav_date"] = nav_date
        etf["nav_date_inferred"] = False
        etf["source"] = "yfinance+sina"
        close = next((c for d, c in dated_closes if d == nav_date), 0.0)
        if close <= 0:
            # yfinance sometimes lacks the bar; Sina's quote supplies it unless
            # the history shows a session between the NAV and the quote
            # (then the previous close is not the NAV day's close).
            quote_date = nav_info.get("quote_date") or ""
            between = any(nav_date < d < quote_date for d, _ in dated_closes)
            if not between:
                close = cn.close_on_nav_date(nav_info)
        if close > 0:
            etf["premium_pct"] = (close / nav - 1.0) * 100.0
