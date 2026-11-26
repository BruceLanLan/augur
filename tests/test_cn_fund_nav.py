# -*- coding: utf-8 -*-
"""v14 step 6: A-share ETF NAV from Sina, parsed from recorded responses."""
from unittest.mock import MagicMock

import pandas as pd
import pytest

from augur.datasources import YFinanceProvider
from augur.datasources import cn_fund_nav_provider as cn
from augur.datasources import yfinance_provider as yp

# Recorded 2026-11-26 13:01 CST (decoded from GBK).
SH_510300 = (
    'var hq_str_f_510300="华泰柏瑞沪深300ETF,3.9718,1.7998,4.0383,2026-11-25,241.196";\n'
    'var hq_str_sh510300="沪深300ETF华泰柏瑞,3.987,3.970,3.978,3.995,3.970,3.977,3.978,'
    '428387482,1705729040.000,106800,3.977,635800,3.976,260900,3.975,1975300,3.974,243100,'
    '3.973,174800,3.978,918600,3.979,2575700,3.980,4265000,3.981,1290900,3.982,'
    '2026-11-26,13:01:42,00,";\n'
)
SZ_159919 = (
    'var hq_str_f_159919="嘉实沪深300ETF,4.146,1.9325,4.2154,2026-11-25,68.6632";\n'
    'var hq_str_sz159919="沪深300,4.152,4.142,4.151,4.172,4.143,4.150,4.151,63816900,'
    '265203716.500,2000,4.150,212500,4.148,715800,4.147,1016900,4.146,701700,4.145,308800,'
    '4.151,681000,4.152,1823000,4.153,3939400,4.154,1242600,4.155,2026-11-26,13:01:45,00";\n'
)
UNKNOWN = 'var hq_str_f_999999="";\n'


def test_parse_shanghai():
    out = cn.parse_sina_response(SH_510300, "510300", "sh")
    assert out == {"name": "华泰柏瑞沪深300ETF", "nav": 3.9718, "nav_date": "2026-11-25",
                   "prev_close": 3.970, "price": 3.978, "quote_date": "2026-11-26"}


def test_parse_shenzhen():
    out = cn.parse_sina_response(SZ_159919, "159919", "sz")
    assert out["nav"] == 4.146
    assert out["nav_date"] == "2026-11-25"
    assert out["prev_close"] == 4.142


@pytest.mark.parametrize("text", [UNKNOWN, "", "Forbidden",
                                  'var hq_str_f_510300="x,abc,1,2,not-a-date,3";'])
def test_parse_bad_input_returns_empty(text):
    assert cn.parse_sina_response(text, "510300", "sh") == {}


def test_nav_without_quote_line():
    text = SH_510300.splitlines()[0]
    out = cn.parse_sina_response(text, "510300", "sh")
    assert out["nav"] == 3.9718 and "quote_date" not in out


def test_close_on_nav_date():
    info = cn.parse_sina_response(SH_510300, "510300", "sh")
    assert cn.close_on_nav_date(info) == 3.970  # quote is the next session
    assert cn.close_on_nav_date(dict(info, quote_date="2026-11-25")) == 3.978
    assert cn.close_on_nav_date(dict(info, quote_date="2026-11-24")) == 0.0


def test_fetch_requests_both_lines_with_referer(monkeypatch):
    seen = {}

    def _get(url):
        seen["url"] = url
        return SH_510300

    monkeypatch.setattr(cn, "_http_get", _get)
    out = cn.fetch_cn_fund_nav("510300.SS")
    assert seen["url"] == "https://hq.sinajs.cn/list=f_510300,sh510300"
    assert out["nav"] == 3.9718
    assert cn.SINA_HEADERS["Referer"].startswith("https://finance.sina.com.cn")


def test_fetch_failure_is_silent(monkeypatch):
    def _boom(url):
        raise OSError("network down")

    monkeypatch.setattr(cn, "_http_get", _boom)
    assert cn.fetch_cn_fund_nav("510300.SS") == {}


def test_non_fund_ticker_makes_no_request(monkeypatch):
    monkeypatch.setattr(cn, "_http_get", lambda url: pytest.fail("should not request"))
    assert cn.fetch_cn_fund_nav("600519.SS") == {}


# ---------------- provider integration ----------------

CN_INFO = {"symbol": "510300.SS", "quoteType": "EQUITY", "currency": "CNY",
           "regularMarketPrice": 3.974, "currentPrice": 3.974}


def _yf(bars):
    tk = MagicMock()
    tk.info = dict(CN_INFO)
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d, _ in bars])
    tk.history.return_value = pd.DataFrame({"Close": [c for _, c in bars]}, index=idx)
    tk.funds_data = None
    mod = MagicMock()
    mod.Ticker.return_value = tk
    return mod


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(yp, "_fx_to_usd", lambda c: {"USD": 1.0, "CNY": 0.1501}.get(c, 0.0))
    monkeypatch.setattr(cn, "_http_get", lambda url: SH_510300)


def test_provider_uses_history_close_on_nav_date():
    bars = [("2026-11-24", 4.033), ("2026-11-25", 3.969), ("2026-11-26", 3.974)]
    etf = YFinanceProvider(yf_loader=lambda: _yf(bars)).fetch("510300.SS")["etf"]
    assert etf["nav"] == 3.9718
    assert etf["nav_date"] == "2026-11-25"
    assert etf["nav_date_inferred"] is False
    assert etf["source"] == "yfinance+sina"
    assert etf["premium_pct"] == pytest.approx((3.969 / 3.9718 - 1) * 100)


def test_provider_fills_missing_bar_from_sina_quote():
    # Live yfinance history skipped 2026-11-25 for Asian listings.
    bars = [("2026-11-24", 4.033), ("2026-11-26", 3.974)]
    etf = YFinanceProvider(yf_loader=lambda: _yf(bars)).fetch("510300.SS")["etf"]
    assert etf["premium_pct"] == pytest.approx((3.970 / 3.9718 - 1) * 100)


def test_provider_no_premium_when_nav_is_stale(monkeypatch):
    stale = SH_510300.replace("2026-11-25,241.196", "2026-11-20,241.196")
    monkeypatch.setattr(cn, "_http_get", lambda url: stale)
    bars = [("2026-11-21", 4.0), ("2026-11-24", 4.033), ("2026-11-26", 3.974)]
    etf = YFinanceProvider(yf_loader=lambda: _yf(bars)).fetch("510300.SS")["etf"]
    assert etf["nav_date"] == "2026-11-20"
    assert "premium_pct" not in etf


def test_provider_degrades_when_sina_fails(monkeypatch):
    monkeypatch.setattr(cn, "_http_get", lambda url: (_ for _ in ()).throw(OSError("x")))
    bars = [("2026-11-24", 4.033), ("2026-11-26", 3.974)]
    out = YFinanceProvider(yf_loader=lambda: _yf(bars)).fetch("510300.SS")
    assert out["asset_type"] == "etf"
    assert "nav" not in out["etf"]
