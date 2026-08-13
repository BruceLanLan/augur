# -*- coding: utf-8 -*-
"""
augur.datasources.base - 数据源抽象层基类

定义统一的 DataProvider 接口，所有具体数据源（yfinance、stooq 等）都实现该接口。
data.py 通过 provider 链按优先级依次尝试，实现多数据源 fallback，消除单点故障。

设计要点:
  - 统一接口 ``fetch(ticker) -> dict``: 返回**已完成单位换算**的 MarketContext 字段字典，
    并附带一个 ``data_source`` 键标记来源；获取失败时抛出 ``DataProviderError``。
  - ``safe_num``: 健壮的数值清洗工具。yfinance 经常返回 ``None`` 或 ``NaN``，
    而 Python 中 ``float('nan')`` 为 truthy，导致 ``value or 0`` 守卫**失效**
    （``nan or 0`` 返回 ``nan``）。本工具统一把 ``None / NaN / inf / 非数值``
    归一到默认值，是修复数据引用 bug 的核心。
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class DataProviderError(Exception):
    """数据源获取失败时抛出，用于触发 provider 链的 fallback。"""


def safe_num(value: Any, default: float = 0.0) -> float:
    """把任意输入安全地转换为有限浮点数。

    处理以下下游会引发评分错误的情况:
      - ``None``                -> default
      - ``float('nan')``        -> default  （关键: ``nan or 0`` 在 Python 中返回 nan）
      - ``float('inf')`` / -inf -> default
      - 非数值（字符串等）       -> default

    Args:
        value: 任意原始值（来自 yfinance / CSV 等）
        default: 无法解析时返回的默认值

    Returns:
        一个有限的 float。
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(f) or math.isinf(f):
        return default
    return f


def clamp(value: float, low: float, high: float) -> float:
    """将数值限制在 [low, high] 区间内。"""
    return max(low, min(high, value))


class DataProvider(ABC):
    """数据源抽象基类。

    子类必须实现:
      - ``name`` 属性: 数据源标识（用于 ``data_source`` 标记与日志）
      - ``fetch(ticker)``: 返回字段字典或抛出 ``DataProviderError``
    """

    #: 数据源唯一标识，例如 "yfinance" / "stooq"
    name: str = "base"

    @abstractmethod
    def fetch(self, ticker: str) -> Dict[str, Any]:
        """获取并标准化某 ticker 的市场数据。

        Args:
            ticker: 已规范化的股票代码（大写）。

        Returns:
            一个 dict，键为 ``MarketContext`` 字段名，值已完成单位换算，
            并包含 ``data_source`` 键。

        Raises:
            DataProviderError: 当该数据源无法提供有效数据时（触发 fallback）。
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # EvidenceItem helpers (F0.3)
    # ------------------------------------------------------------------

    def to_evidence_item(
        self,
        field: str,
        value: Any,
        ticker: str,
        *,
        effective_at: Optional[datetime] = None,
        available_at: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """Build a minimal EvidenceItem dict for one MarketContext field.

        Returns None when the value is None/missing (caller should mark
        ``coverage="missing"`` separately). The returned dict is a *plain*
        dict (not a Pydantic model) so it can be attached to MarketContext
        without importing the schemas package in every provider.

        Args:
            field: MarketContext field name (e.g. "pe", "institutional_ownership").
            value: The field value (None → return None).
            ticker: Normalized ticker symbol.
            effective_at: When the data became effective (e.g. fiscal quarter end).
            available_at: When the data became publicly available (e.g. filing date).
        """
        if value is None:
            return None

        retrieved_at = datetime.now(timezone.utc)
        content_str = f"{self.name}:{ticker}:{field}:{value}"
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        from augur.schemas.evidence import generate_evidence_id

        return {
            "evidence_id": generate_evidence_id(self.name, content_hash),
            "source": self.name,
            "source_locator": f"provider://{self.name}/{ticker}",
            "content_hash": content_hash,
            "instrument": ticker,
            "metric": field,
            "value": float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None,
            "unit": None,
            "currency": None,
            "effective_at": effective_at,
            "available_at": available_at,
            "retrieved_at": retrieved_at,
            "transform_version": None,
            "schema_version": "1.0",
            "code_version": None,
            "coverage": 1.0,
            "missing": False,
            "degraded": False,
            "license": None,
            "redistribution_allowed": True,
            "metadata": {},
        }

    def coverage_report(self) -> Dict[str, str]:
        """Return per-field coverage status for this provider.

        Default implementation reports "unknown" for every field the
        provider *could* supply. Subclasses should override to report
        "live" for fields they actually supply.
        """
        return {}  # pragma: no cover — overridden by subclasses

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<DataProvider {self.name}>"
