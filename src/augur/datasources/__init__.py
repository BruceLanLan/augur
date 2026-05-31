# -*- coding: utf-8 -*-
"""
augur.datasources - 多数据源抽象层

提供统一的 ``DataProvider`` 接口与多个具体实现，data.py 通过 provider 链
（yfinance 优先，stooq 兜底）实现 fallback，消除单点故障。

公开接口:
    DataProvider        - 抽象基类
    DataProviderError   - 失败异常（触发 fallback）
    safe_num            - None/NaN/inf 安全数值清洗
    YFinanceProvider    - 主数据源（基本面 + 行情 + 技术指标）
    StooqProvider       - 备用行情数据源（免费 CSV，无需 API key）
    default_providers   - 返回默认 provider 链
"""

from augur.datasources.base import (
    DataProvider,
    DataProviderError,
    clamp,
    safe_num,
)
from augur.datasources.stooq_provider import StooqProvider
from augur.datasources.yfinance_provider import YFinanceProvider

__all__ = [
    "DataProvider",
    "DataProviderError",
    "clamp",
    "safe_num",
    "YFinanceProvider",
    "StooqProvider",
    "default_providers",
]


def default_providers():
    """返回默认的 provider 链：yfinance 优先，stooq 兜底。"""
    return [YFinanceProvider(), StooqProvider()]
