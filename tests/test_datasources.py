# -*- coding: utf-8 -*-
"""
Tests for the multi-source data provider layer (augur.datasources) and its
integration into augur.data.fetch_market_context.

覆盖:
  - safe_num: None/NaN/inf 安全清洗（核心 bug 修复）
  - YFinanceProvider: 单位换算、NaN 优雅降级、无数据时抛错
  - StooqProvider: CSV 解析、符号映射、无报价降级
  - provider 链 fallback: yfinance 失败 -> stooq；全部失败 -> 空 context
  - data_source 标记
  - 缓存行为（命中 / force_refresh / TTL）
"""

import math
from unittest.mock import MagicMock, patch

import pytest

from augur.datasources import (
    DataProvider,
    DataProviderError,
    StooqProvider,
    YFinanceProvider,
    default_providers,
    safe_num,
)
from augur.datasources.base import clamp
from augur.personas.base import MarketContext


# ============ Helpers ============


def _make_yf_mock(info, history_empty=True):
    """构造一个 mock yfinance 模块及其 Ticker。"""
    mock_ticker = MagicMock()
    mock_ticker.info = info
    mock_ticker.history.return_value = MagicMock(empty=history_empty)
    mock_yf = MagicMock()
    mock_yf.Ticker.return_value = mock_ticker
    return mock_yf


# ============ safe_num ============


class TestSafeNum:
    def test_none_returns_default(self):
        assert safe_num(None) == 0.0
        assert safe_num(None, default=5.0) == 5.0

    def test_nan_returns_default(self):
        """核心 bug: float('nan') 是 truthy, 'nan or 0' 返回 nan。safe_num 必须归零。"""
        assert safe_num(float("nan")) == 0.0
        assert safe_num(float("nan"), default=1.0) == 1.0

    def test_inf_returns_default(self):
        assert safe_num(float("inf")) == 0.0
        assert safe_num(float("-inf")) == 0.0

    def test_non_numeric_returns_default(self):
        assert safe_num("not a number") == 0.0
        assert safe_num("N/D") == 0.0
        assert safe_num([1, 2, 3]) == 0.0

    def test_numeric_string_parsed(self):
        assert safe_num("191.29") == 191.29
        assert safe_num("100") == 100.0

    def test_valid_numbers_passthrough(self):
        assert safe_num(42) == 42.0
        assert safe_num(3.14) == 3.14
        assert safe_num(0) == 0.0
        assert safe_num(-5.5) == -5.5

    def test_result_is_always_finite(self):
        for v in [None, float("nan"), float("inf"), "x", 1.5, 0]:
            r = safe_num(v)
            assert not math.isnan(r) and not math.isinf(r)


class TestClamp:
    def test_clamp_within(self):
        assert clamp(50, 0, 100) == 50

    def test_clamp_low(self):
        assert clamp(-10, 0, 100) == 0

    def test_clamp_high(self):
        assert clamp(150, 0, 100) == 100


# ============ YFinanceProvider ============


class TestYFinanceProvider:
    def test_fetch_basic_fields(self):
        info = {
            "symbol": "AAPL",
            "currentPrice": 190.0,
            "trailingPE": 30.0,
            "marketCap": 3_000_000_000_000,
            "freeCashflow": 90_000_000_000,
            "returnOnEquity": 0.45,
            "grossMargins": 0.44,
            "heldPercentInstitutions": 0.62,
        }
        provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock(info))
        fields = provider.fetch("AAPL")

        assert fields["data_source"] == "yfinance"
        assert fields["price"] == 190.0
        assert fields["pe"] == 30.0
        # 单位换算: 十亿 USD
        assert fields["market_cap"] == 3000.0
        assert fields["fcf"] == 90.0
        # ROE / 毛利率保持小数
        assert fields["roe"] == 0.45
        assert fields["gross_margins"] == 0.44
        # 持股: 0-1 -> 0-100
        assert fields["institutional_ownership"] == 62.0

    def test_nan_values_degrade_gracefully(self):
        """yfinance 返回 NaN 时应归零，而不是把 NaN 传入 MarketContext。"""
        nan = float("nan")
        info = {
            "symbol": "BADDATA",
            "currentPrice": nan,
            "regularMarketPrice": nan,
            "trailingPE": nan,
            "priceToBook": nan,
            "returnOnEquity": nan,
            "grossMargins": nan,
            "revenueGrowth": nan,
            "marketCap": nan,
            "freeCashflow": nan,
            "debtToEquity": nan,
            "heldPercentInstitutions": nan,
            "beta": nan,
        }
        provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock(info))
        fields = provider.fetch("BADDATA")

        for key in ("price", "pe", "pb", "roe", "gross_margins", "revenue_growth",
                    "market_cap", "fcf", "debt_ratio", "institutional_ownership"):
            assert fields[key] == 0, f"{key} should degrade NaN to 0, got {fields[key]}"
            assert not math.isnan(fields[key])
        # beta 默认 1.0
        assert fields["beta_1y"] == 1.0

    def test_none_values_degrade_gracefully(self):
        info = {
            "symbol": "NONES",
            "currentPrice": None,
            "trailingPE": None,
            "marketCap": None,
            "freeCashflow": None,
            "debtToEquity": None,
            "heldPercentInstitutions": None,
        }
        provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock(info))
        fields = provider.fetch("NONES")
        assert fields["price"] == 0
        assert fields["market_cap"] == 0
        assert fields["debt_ratio"] == 0
        assert fields["institutional_ownership"] == 0

    def test_debt_ratio_conversion(self):
        info = {"symbol": "T", "debtToEquity": 162, "currentPrice": 100}
        provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock(info))
        fields = provider.fetch("T")
        assert abs(fields["debt_ratio"] - 0.618) < 0.01

    def test_debt_ratio_negative_equity(self):
        info = {"symbol": "T", "debtToEquity": -150, "currentPrice": 100}
        provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock(info))
        fields = provider.fetch("T")
        assert fields["debt_ratio"] == 0

    def test_ownership_clamped_to_100(self):
        """yfinance 偶发 >1.0 的脏数据应被裁剪到 100。"""
        info = {"symbol": "T", "heldPercentInstitutions": 1.5, "currentPrice": 100}
        provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock(info))
        fields = provider.fetch("T")
        assert fields["institutional_ownership"] == 100.0

    def test_missing_symbol_raises(self):
        """info 缺少 symbol -> 抛 DataProviderError 触发 fallback。"""
        provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock({}))
        with pytest.raises(DataProviderError):
            provider.fetch("UNKNOWN")

    def test_info_exception_raises(self):
        def boom_loader():
            mock_yf = MagicMock()
            bad_ticker = MagicMock()
            type(bad_ticker).info = property(lambda self: (_ for _ in ()).throw(RuntimeError("net down")))
            mock_yf.Ticker.return_value = bad_ticker
            return mock_yf

        provider = YFinanceProvider(yf_loader=boom_loader)
        with pytest.raises(DataProviderError):
            provider.fetch("AAPL")

    def test_technicals_computed_from_history(self):
        """有历史数据时应计算技术指标。"""
        info = {"symbol": "AAPL", "currentPrice": 100}
        closes = [100 + i * 0.5 for i in range(60)]

        mock_ticker = MagicMock()
        mock_ticker.info = info
        hist = MagicMock()
        hist.empty = False
        hist.__getitem__.return_value.tolist.return_value = closes
        mock_ticker.history.return_value = hist
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        provider = YFinanceProvider(yf_loader=lambda: mock_yf)
        fields = provider.fetch("AAPL")
        assert fields["sma20"] > 0
        assert fields["sma50"] > 0
        assert fields["rsi"] != 50 or fields["rsi"] == 100  # trending up


# ============ StooqProvider ============


class TestStooqProvider:
    def test_symbol_mapping_us(self):
        assert StooqProvider._to_stooq_symbol("AAPL") == "aapl.us"

    def test_symbol_mapping_suffixed(self):
        assert StooqProvider._to_stooq_symbol("0700.HK") == "0700.hk"
        assert StooqProvider._to_stooq_symbol("600519.SS") == "600519.ss"

    def test_fetch_parses_csv(self):
        csv = (
            "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
            "AAPL.US,2024-05-30,22:00:02,191.51,192.57,189.91,191.29,52280051\n"
        )
        provider = StooqProvider()
        provider._http_get = lambda url: csv
        fields = provider.fetch("AAPL")

        assert fields["data_source"] == "stooq"
        assert fields["price"] == 191.29
        assert fields["volume"] == 52280051
        # change_pct = (191.29 - 191.51) / 191.51
        assert fields["change_pct"] < 0

    def test_fetch_no_data_raises(self):
        csv = (
            "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
            "BADSYM.US,N/D,N/D,N/D,N/D,N/D,N/D,N/D\n"
        )
        provider = StooqProvider()
        provider._http_get = lambda url: csv
        with pytest.raises(DataProviderError):
            provider.fetch("BADSYM")

    def test_fetch_empty_response_raises(self):
        provider = StooqProvider()
        provider._http_get = lambda url: "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
        with pytest.raises(DataProviderError):
            provider.fetch("AAPL")

    def test_fetch_network_error_raises(self):
        def boom(url):
            raise OSError("connection refused")

        provider = StooqProvider()
        provider._http_get = boom
        with pytest.raises(DataProviderError):
            provider.fetch("AAPL")


# ============ Provider chain integration in data.py ============


class TestProviderChainFallback:
    def setup_method(self):
        from augur import data
        data.clear_cache()
        # 重置 provider 链缓存，避免测试间互相污染
        data._providers_cache = None

    def teardown_method(self):
        from augur import data
        data.clear_cache()
        data._providers_cache = None

    def test_yfinance_success_used_first(self):
        """yfinance 成功时不应触及 stooq。"""
        from augur import data

        info = {"symbol": "AAPL", "currentPrice": 190.0, "marketCap": 3_000_000_000_000}
        yf_provider = YFinanceProvider(yf_loader=lambda: _make_yf_mock(info))
        stooq = StooqProvider()
        stooq._http_get = MagicMock(side_effect=AssertionError("stooq should not be called"))

        with patch.object(data, "_get_providers", return_value=[yf_provider, stooq]):
            ctx = data.fetch_market_context("AAPL")

        assert ctx.price == 190.0
        assert ctx.market_cap == 3000.0
        assert getattr(ctx, "data_source") == "yfinance"
        stooq._http_get.assert_not_called()

    def test_fallback_to_stooq_when_yfinance_fails(self):
        """yfinance 抛错 -> 链应自动降级到 stooq。"""
        from augur import data

        # yfinance loader 抛错
        def failing_loader():
            raise RuntimeError("yfinance unavailable")

        yf_provider = YFinanceProvider(yf_loader=failing_loader)

        csv = (
            "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
            "AAPL.US,2024-05-30,22:00:02,191.51,192.57,189.91,191.29,52280051\n"
        )
        stooq = StooqProvider()
        stooq._http_get = lambda url: csv

        with patch.object(data, "_get_providers", return_value=[yf_provider, stooq]):
            ctx = data.fetch_market_context("AAPL")

        assert getattr(ctx, "data_source") == "stooq"
        assert ctx.price == 191.29
        assert ctx.volume == 52280051

    def test_all_providers_fail_returns_empty_context(self):
        """全部失败 -> 返回空 context 且 data_source='none'，不抛异常。"""
        from augur import data

        def failing_loader():
            raise RuntimeError("down")

        yf_provider = YFinanceProvider(yf_loader=failing_loader)
        stooq = StooqProvider()
        stooq._http_get = MagicMock(side_effect=OSError("down"))

        with patch.object(data, "_get_providers", return_value=[yf_provider, stooq]):
            ctx = data.fetch_market_context("ZZZZ")

        assert isinstance(ctx, MarketContext)
        assert ctx.ticker == "ZZZZ"
        assert ctx.price == 0
        assert getattr(ctx, "data_source") == "none"

    def test_default_providers_order(self):
        providers = default_providers()
        assert isinstance(providers[0], YFinanceProvider)
        assert isinstance(providers[1], StooqProvider)
        assert all(isinstance(p, DataProvider) for p in providers)


# ============ Cache behaviour ============


class TestCacheBehaviour:
    def setup_method(self):
        from augur import data
        data.clear_cache()
        data._providers_cache = None

    def teardown_method(self):
        from augur import data
        data.clear_cache()
        data._providers_cache = None

    def test_cache_hit_avoids_second_fetch(self):
        """第二次调用应命中缓存，不再调用 provider.fetch。"""
        from augur import data

        info = {"symbol": "AAPL", "currentPrice": 190.0}
        fetch_spy = MagicMock(return_value={"price": 190.0, "data_source": "yfinance"})
        fake_provider = MagicMock(spec=DataProvider)
        fake_provider.name = "yfinance"
        fake_provider.fetch = fetch_spy

        with patch.object(data, "_get_providers", return_value=[fake_provider]):
            ctx1 = data.fetch_market_context("AAPL")
            ctx2 = data.fetch_market_context("AAPL")

        assert ctx1 is ctx2  # 返回同一缓存对象
        assert fetch_spy.call_count == 1

    def test_force_refresh_bypasses_cache(self):
        from augur import data

        fetch_spy = MagicMock(return_value={"price": 190.0, "data_source": "yfinance"})
        fake_provider = MagicMock(spec=DataProvider)
        fake_provider.name = "yfinance"
        fake_provider.fetch = fetch_spy

        with patch.object(data, "_get_providers", return_value=[fake_provider]):
            data.fetch_market_context("AAPL")
            data.fetch_market_context("AAPL", force_refresh=True)

        assert fetch_spy.call_count == 2

    def test_cache_expiry(self):
        """TTL 过期后应重新抓取。"""
        from augur import data

        fetch_spy = MagicMock(return_value={"price": 1.0, "data_source": "yfinance"})
        fake_provider = MagicMock(spec=DataProvider)
        fake_provider.name = "yfinance"
        fake_provider.fetch = fetch_spy

        with patch.object(data, "_get_providers", return_value=[fake_provider]):
            data.fetch_market_context("AAPL")
            # 手动把缓存时间戳改成过期
            with data._cache_lock:
                data._cache["ctx:AAPL"]["ts"] -= (data._CACHE_TTL + 10)
            data.fetch_market_context("AAPL")

        assert fetch_spy.call_count == 2

    def test_clear_cache(self):
        from augur import data

        fetch_spy = MagicMock(return_value={"price": 1.0, "data_source": "yfinance"})
        fake_provider = MagicMock(spec=DataProvider)
        fake_provider.name = "yfinance"
        fake_provider.fetch = fetch_spy

        with patch.object(data, "_get_providers", return_value=[fake_provider]):
            data.fetch_market_context("AAPL")
            data.clear_cache()
            data.fetch_market_context("AAPL")

        assert fetch_spy.call_count == 2
        assert data.cache_info()["size"] >= 1
