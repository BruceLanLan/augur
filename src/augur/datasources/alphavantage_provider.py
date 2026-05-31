# -*- coding: utf-8 -*-
"""
augur.datasources.alphavantage_provider - Alpha Vantage 数据源 (可选)

Alpha Vantage 提供免费 tier 的报价与公司基本面(OVERVIEW):
    https://www.alphavantage.co/documentation/

需要 API key（免费申请），通过环境变量 ``ALPHAVANTAGE_API_KEY`` 启用。
未配置 key 时 ``is_configured()`` 返回 False，``default_providers()`` 不会把它加入链中。

覆盖:
    - GLOBAL_QUOTE : 实时报价（price / change% / volume）
    - OVERVIEW     : 公司基本面（PE/PEG/PB/ROE/利润率/52周高低/目标价/股息等）

注意: Alpha Vantage 免费 tier 限速较严（约 5 次/分钟、500 次/天），
因此放在 provider 链中 yfinance/finnhub 之后，仅作补充兜底。
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict

from augur.datasources.base import DataProvider, DataProviderError, clamp, safe_num

logger = logging.getLogger(__name__)

_AV_BASE = "https://www.alphavantage.co/query"
_HTTP_TIMEOUT = 10  # seconds


def is_configured() -> bool:
    """是否已配置 Alpha Vantage API key。"""
    return bool(os.environ.get("ALPHAVANTAGE_API_KEY", "").strip())


class AlphaVantageProvider(DataProvider):
    """基于 Alpha Vantage REST API 的可选数据源（报价 + 基本面）。"""

    name = "alphavantage"

    def __init__(self, api_key: str = None, timeout: int = _HTTP_TIMEOUT) -> None:
        self._api_key = api_key or os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
        self._timeout = timeout

    def _http_get_json(self, params: Dict[str, str]) -> Dict[str, Any]:
        params = dict(params)
        params["apikey"] = self._api_key
        url = f"{_AV_BASE}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "augur-datasource/1.0"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def fetch(self, ticker: str) -> Dict[str, Any]:
        if not self._api_key:
            raise DataProviderError("alphavantage api key not configured")

        symbol = ticker.strip().upper()

        # --- 实时报价 ---
        try:
            quote_resp = self._http_get_json({"function": "GLOBAL_QUOTE", "symbol": symbol})
        except Exception as exc:
            raise DataProviderError(f"alphavantage quote failed for {ticker}: {exc}") from exc

        # 限速时返回 {"Note": "..."} 或 {"Information": "..."}
        if "Note" in quote_resp or "Information" in quote_resp:
            raise DataProviderError(f"alphavantage rate-limited for {ticker}")

        quote = quote_resp.get("Global Quote", {}) or {}
        price = safe_num(quote.get("05. price"))
        if price <= 0:
            raise DataProviderError(f"alphavantage has no quote for {ticker}")

        change_pct_raw = (quote.get("10. change percent", "") or "").replace("%", "")
        change_pct = safe_num(change_pct_raw) / 100.0

        fields: Dict[str, Any] = {
            "price": price,
            "day_open": safe_num(quote.get("02. open")),
            "day_high": safe_num(quote.get("03. high")),
            "day_low": safe_num(quote.get("04. low")),
            "volume": safe_num(quote.get("06. volume")),
            "change_pct": change_pct,
            "data_source": self.name,
        }

        # --- 公司基本面 OVERVIEW（best-effort）---
        try:
            ov = self._http_get_json({"function": "OVERVIEW", "symbol": symbol})
            if ov and "Symbol" in ov:
                fields.update({
                    "company_name": ov.get("Name", "") or "",
                    "sector": ov.get("Sector", "") or "",
                    "industry": ov.get("Industry", "") or "",
                    "currency": ov.get("Currency", "") or "",
                    "exchange": ov.get("Exchange", "") or "",
                    "pe": safe_num(ov.get("PERatio")),
                    "forward_pe": safe_num(ov.get("ForwardPE")),
                    "peg_ratio": safe_num(ov.get("PEGRatio")),
                    "pb": safe_num(ov.get("PriceToBookRatio")),
                    "ps": safe_num(ov.get("PriceToSalesRatioTTM")),
                    "eps": safe_num(ov.get("EPS")),
                    "roe": safe_num(ov.get("ReturnOnEquityTTM")),
                    "roa": safe_num(ov.get("ReturnOnAssetsTTM")),
                    "profit_margins": safe_num(ov.get("ProfitMargin")),
                    "operating_margins": safe_num(ov.get("OperatingMarginTTM")),
                    "market_cap": safe_num(ov.get("MarketCapitalization")) / 1e9,
                    "ebitda": safe_num(ov.get("EBITDA")) / 1e9,
                    "revenue": safe_num(ov.get("RevenueTTM")) / 1e9,
                    "beta_1y": safe_num(ov.get("Beta"), default=1.0),
                    "dividend_yield": clamp(safe_num(ov.get("DividendYield")), 0.0, 1.0),
                    "dividend_rate": safe_num(ov.get("DividendPerShare")),
                    "fifty_two_week_high": safe_num(ov.get("52WeekHigh")),
                    "fifty_two_week_low": safe_num(ov.get("52WeekLow")),
                    "sma200": safe_num(ov.get("200DayMovingAverage")),
                    "target_mean_price": safe_num(ov.get("AnalystTargetPrice")),
                })
        except Exception as exc:
            logger.debug("alphavantage overview enrichment failed for %s: %s", ticker, exc)

        return fields
