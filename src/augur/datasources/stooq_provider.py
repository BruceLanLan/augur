# -*- coding: utf-8 -*-
"""
augur.datasources.stooq_provider - Stooq 备用数据源 (fallback)

Stooq 提供免费的 CSV 行情快照，无需 API key:
    https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv

返回的 CSV 形如:
    Symbol,Date,Time,Open,High,Low,Close,Volume
    AAPL.US,2024-05-30,22:00:02,191.51,192.57,189.91,191.29,52280051

Stooq 仅提供行情（OHLCV），不含基本面数据，因此它作为 yfinance 失败时的**降级**
数据源：至少保证 price / volume / 当日涨跌可用，避免整个 context 为空导致分析无法产出。

符号映射: 美股需加 ``.us`` 后缀（如 ``aapl.us``）；其他带交易所后缀的代码统一小写。
"""

from __future__ import annotations

import logging
import urllib.request
from typing import Any, Dict

from augur.datasources.base import DataProvider, DataProviderError, safe_num

logger = logging.getLogger(__name__)

_STOOQ_URL = "https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
_HTTP_TIMEOUT = 8  # seconds


class StooqProvider(DataProvider):
    """基于 Stooq CSV 快照的备用数据源。"""

    name = "stooq"

    def __init__(self, timeout: int = _HTTP_TIMEOUT) -> None:
        self._timeout = timeout

    @staticmethod
    def _to_stooq_symbol(ticker: str) -> str:
        """把内部 ticker 映射为 Stooq 符号。

        - 纯字母数字（美股，无后缀）-> 追加 ``.us``
        - 已带后缀（``0700.HK`` / ``600519.SS`` 等）-> 统一小写
        """
        t = ticker.strip().lower()
        if "." not in t:
            return f"{t}.us"
        return t

    def _http_get(self, url: str) -> str:
        """发起 HTTP GET 并返回响应文本。抽成单独方法便于测试中 monkeypatch。"""
        req = urllib.request.Request(url, headers={"User-Agent": "augur-datasource/1.0"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
            return resp.read().decode("utf-8", errors="replace")

    def fetch(self, ticker: str) -> Dict[str, Any]:
        symbol = self._to_stooq_symbol(ticker)
        url = _STOOQ_URL.format(symbol=symbol)

        try:
            text = self._http_get(url)
        except Exception as exc:  # 网络错误 -> 触发 fallback / 空 context
            raise DataProviderError(f"stooq request failed for {ticker}: {exc}") from exc

        rows = [line for line in text.strip().splitlines() if line.strip()]
        if len(rows) < 2:
            raise DataProviderError(f"stooq returned no rows for {ticker}")

        header = [h.strip().lower() for h in rows[0].split(",")]
        values = rows[1].split(",")
        if len(values) < len(header):
            raise DataProviderError(f"stooq malformed row for {ticker}: {rows[1]!r}")

        record = dict(zip(header, [v.strip() for v in values]))

        # Stooq 对无数据的字段返回 'N/D'
        close_raw = record.get("close", "")
        if not close_raw or close_raw.upper() == "N/D":
            raise DataProviderError(f"stooq has no quote for {ticker}")

        close = safe_num(close_raw)
        if close <= 0:
            raise DataProviderError(f"stooq invalid close for {ticker}: {close_raw!r}")

        open_px = safe_num(record.get("open"))
        volume = safe_num(record.get("volume"))

        # 当日涨跌（以开盘价为基准的近似值，小数形式）
        change_pct = (close - open_px) / open_px if open_px > 0 else 0.0

        fields: Dict[str, Any] = {
            "price": close,
            "volume": volume,
            "change_pct": change_pct,
            "data_source": self.name,
        }
        return fields
