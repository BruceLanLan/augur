# -*- coding: utf-8 -*-
"""
augur.datasources.finnhub_provider - Finnhub 数据源 (可选)

Finnhub 提供免费 tier 的实时报价、公司基本面与分析师评级:
    https://finnhub.io/docs/api

需要 API key（免费申请），通过环境变量 ``FINNHUB_API_KEY`` 启用。
未配置 key 时 ``is_configured()`` 返回 False，``default_providers()`` 不会把它加入链中。

Finnhub 同时覆盖**基本面 + 分析师一致预期**，是 yfinance 之外一个有价值的参考/兜底来源：
    - /quote                : 实时报价（c/o/h/l/pc）
    - /stock/metric         : 基本面指标（PE/PB/ROE/毛利率/52周高低等）
    - /stock/recommendation : 分析师买卖建议（最新一期）

设计为 provider 链中 yfinance 之后、stooq 之前的兜底：当 yfinance 限流/失败时，
Finnhub 仍能提供较完整的基本面，避免降级到只有价格的 stooq。
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

_FINNHUB_BASE = "https://finnhub.io/api/v1"
_HTTP_TIMEOUT = 8  # seconds


def is_configured() -> bool:
    """是否已配置 Finnhub API key。"""
    return bool(os.environ.get("FINNHUB_API_KEY", "").strip())


class FinnhubProvider(DataProvider):
    """基于 Finnhub REST API 的可选数据源（基本面 + 分析师评级）。"""

    name = "finnhub"

    def __init__(self, api_key: str = None, timeout: int = _HTTP_TIMEOUT) -> None:
        self._api_key = api_key or os.environ.get("FINNHUB_API_KEY", "").strip()
        self._timeout = timeout

    def _http_get_json(self, path: str, params: Dict[str, str]) -> Dict[str, Any]:
        params = dict(params)
        params["token"] = self._api_key
        url = f"{_FINNHUB_BASE}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "augur-datasource/1.0"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def fetch(self, ticker: str) -> Dict[str, Any]:
        if not self._api_key:
            raise DataProviderError("finnhub api key not configured")

        symbol = ticker.strip().upper()

        # --- 实时报价 ---
        try:
            quote = self._http_get_json("/quote", {"symbol": symbol})
        except Exception as exc:
            raise DataProviderError(f"finnhub quote failed for {ticker}: {exc}") from exc

        price = safe_num(quote.get("c"))  # current price
        if price <= 0:
            raise DataProviderError(f"finnhub has no quote for {ticker}")

        prev_close = safe_num(quote.get("pc"))
        change_pct = (price - prev_close) / prev_close if prev_close > 0 else 0.0

        fields: Dict[str, Any] = {
            "price": price,
            "day_open": safe_num(quote.get("o")),
            "day_high": safe_num(quote.get("h")),
            "day_low": safe_num(quote.get("l")),
            "change_pct": change_pct,
            "data_source": self.name,
        }

        # --- 基本面指标（best-effort，失败不影响报价）---
        try:
            metric_resp = self._http_get_json("/stock/metric", {"symbol": symbol, "metric": "all"})
            m = metric_resp.get("metric", {}) or {}
            fields.update({
                "pe": safe_num(m.get("peTTM")) or safe_num(m.get("peBasicExclExtraTTM")),
                "pb": safe_num(m.get("pbQuarterly")) or safe_num(m.get("pbAnnual")),
                "ps": safe_num(m.get("psTTM")),
                "roe": safe_num(m.get("roeTTM")) / 100.0,  # Finnhub 返回百分数
                "roa": safe_num(m.get("roaTTM")) / 100.0,
                "gross_margins": safe_num(m.get("grossMarginTTM")) / 100.0,
                "operating_margins": safe_num(m.get("operatingMarginTTM")) / 100.0,
                "profit_margins": safe_num(m.get("netProfitMarginTTM")) / 100.0,
                "current_ratio": safe_num(m.get("currentRatioQuarterly")),
                "dividend_yield": clamp(safe_num(m.get("dividendYieldIndicatedAnnual")) / 100.0, 0.0, 1.0),
                "fifty_two_week_high": safe_num(m.get("52WeekHigh")),
                "fifty_two_week_low": safe_num(m.get("52WeekLow")),
                "beta_1y": safe_num(m.get("beta"), default=1.0),
                "eps": safe_num(m.get("epsTTM")),
            })
        except Exception as exc:
            logger.debug("finnhub metric enrichment failed for %s: %s", ticker, exc)

        # --- 公司名 / 行业（best-effort）---
        try:
            profile = self._http_get_json("/stock/profile2", {"symbol": symbol})
            if profile:
                fields["company_name"] = profile.get("name", "") or ""
                fields["industry"] = profile.get("finnhubIndustry", "") or ""
                fields["exchange"] = profile.get("exchange", "") or ""
                fields["currency"] = profile.get("currency", "") or ""
                mc = safe_num(profile.get("marketCapitalization"))  # Finnhub 单位为百万
                if mc > 0:
                    fields["market_cap"] = mc / 1000.0  # 百万 -> 十亿
        except Exception as exc:
            logger.debug("finnhub profile enrichment failed for %s: %s", ticker, exc)

        # --- 分析师评级（best-effort）---
        try:
            recs = self._http_get_json("/stock/recommendation", {"symbol": symbol})
            if isinstance(recs, list) and recs:
                latest = recs[0]
                buy = safe_num(latest.get("strongBuy")) + safe_num(latest.get("buy"))
                hold = safe_num(latest.get("hold"))
                sell = safe_num(latest.get("sell")) + safe_num(latest.get("strongSell"))
                total = buy + hold + sell
                if total > 0:
                    if buy / total >= 0.6:
                        fields["recommendation_key"] = "buy"
                    elif sell / total >= 0.4:
                        fields["recommendation_key"] = "sell"
                    else:
                        fields["recommendation_key"] = "hold"
                    fields["num_analyst_opinions"] = int(total)
        except Exception as exc:
            logger.debug("finnhub recommendation enrichment failed for %s: %s", ticker, exc)

        return fields
