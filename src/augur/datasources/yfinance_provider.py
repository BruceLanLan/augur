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
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from augur.datasources.base import DataProvider, DataProviderError, clamp, safe_num

logger = logging.getLogger(__name__)


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

        # ---- 盈利能力 / 增长（yfinance 原生为 0-1 小数，保持不变）----
        roe = safe_num(info.get("returnOnEquity"))
        roa = safe_num(info.get("returnOnAssets"))
        gross_margins = safe_num(info.get("grossMargins"))
        operating_margins = safe_num(info.get("operatingMargins"))
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

        # ---- 现金流 / 规模 -> 统一换算为“十亿 USD” ----
        fcf = safe_num(info.get("freeCashflow")) / 1e9
        market_cap = safe_num(info.get("marketCap")) / 1e9
        revenue = safe_num(info.get("totalRevenue")) / 1e9

        current_ratio = safe_num(info.get("currentRatio"))
        quick_ratio = safe_num(info.get("quickRatio"))
        sector = info.get("sector") or ""
        industry = info.get("industry") or ""
        volume = safe_num(info.get("volume")) or safe_num(info.get("regularMarketVolume"))

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
            "volume": volume,
            "institutional_ownership": institutional_ownership,
            "insider_ownership": insider_ownership,
            "short_interest": short_interest,
            "beta_1y": beta_1y,
            "price_vs_52w_high": price_vs_52w_high,
            "price_vs_52w_low": price_vs_52w_low,
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
        return fields
