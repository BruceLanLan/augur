# -*- coding: utf-8 -*-
"""v14 step 3: ETFs are recognised and get a fund profile instead of company fields.

Info dicts are trimmed copies of live yfinance 1.7.0 output (2026-11-25/26,
see the v14 research notes); histories are the last few live bars.
"""
from unittest.mock import MagicMock

import pandas as pd
import pytest

from augur.datasources import YFinanceProvider
from augur.datasources import yfinance_provider as yp
from augur.datasources.fund_profile import (
    asset_type_for,
    cn_etf_code,
    premium_on_nav_date,
)

RATES = {"HKD": 0.1276, "CNY": 0.1501}

SPY_INFO = {
    "symbol": "SPY", "quoteType": "ETF", "longName": "State Street SPDR S&P 500 ETF Trust",
    "currency": "USD", "exchange": "PCX", "regularMarketPrice": 716.7, "navPrice": 718.51355,
    "totalAssets": 796865200128, "netExpenseRatio": 0.0945, "yield": 0.01,
    "category": "Large Blend", "averageVolume": 47952760, "bid": 716.43, "ask": 716.78,
    "trailingPE": 22.801332, "priceToBook": 1.6697731, "beta3Year": 0.97,
}
SPY_BARS = [("2026-11-21", 689.81), ("2026-11-24", 718.78), ("2026-11-25", 716.70)]

HK_INFO = {
    "symbol": "2800.HK", "quoteType": "ETF", "longName": "Tracker Fund Of Hong Kong",
    "currency": "HKD", "financialCurrency": "HKD", "exchange": "HKG",
    "regularMarketPrice": 22.5, "navPrice": 22.3503, "totalAssets": 123810512896,
    "netExpenseRatio": 0.1, "yield": 0.0325, "averageVolume": 568150043,
    "bid": 22.5, "ask": 22.52, "priceToBook": 0.76896787,
}
HK_BARS = [("2026-11-23", 22.50), ("2026-11-24", 22.34), ("2026-11-26", 22.50)]

CN_INFO = {
    "symbol": "510300.SS", "quoteType": "EQUITY", "longName": "Huatai-PineBridge CSI 300 ETF",
    "currency": "CNY", "regularMarketPrice": 3.974, "currentPrice": 3.974,
    "averageVolume": 1391665827, "bid": 3.973, "ask": 3.974,
}
CN_BARS = [("2026-11-23", 4.023), ("2026-11-24", 4.033), ("2026-11-26", 3.974)]


def _history(bars):
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d, _ in bars])
    return pd.DataFrame({"Close": [c for _, c in bars]}, index=idx)


class _SpyFunds:
    fund_overview = {"categoryName": "Large Blend", "family": "State Street"}
    fund_operations = pd.DataFrame(
        {"SPY": [0.000945, 0.03, 504496.28], "Category Average": [0.007218, 0.9461, 504496.28]},
        index=["Annual Report Expense Ratio", "Annual Holdings Turnover", "Total Net Assets"],
    )
    top_holdings = pd.DataFrame(
        {"Name": ["Apple", "NVIDIA", "Microsoft", "Amazon", "Alphabet A", "Broadcom",
                  "Meta", "Alphabet C", "Tesla", "Berkshire"],
         "Holding Percent": [0.077007, 0.075823, 0.059332, 0.036119, 0.025141, 0.023752,
                             0.020763, 0.020, 0.019, 0.016]},
        index=["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "AVGO", "META", "GOOG", "TSLA", "BRK-B"],
    )
    sector_weightings = {"technology": 0.3823, "financial_services": 0.1203, "healthcare": 0.1025,
                         "realestate": 0.018}
    asset_classes = {"cashPosition": 0.0006, "stockPosition": 0.9994, "bondPosition": 0.0}

    @property
    def equity_holdings(self):  # earnings-yield style numbers; must not be used as P/E
        return pd.DataFrame({"SPY": [0.0416, 0.197]}, index=["Price/Earnings", "Price/Book"])


class _BrokenFunds:
    def __getattr__(self, name):
        raise RuntimeError("YFDataException: No Fund data found")


def _yf(info, bars, funds=None, funds_raises=False):
    ticker = MagicMock()
    ticker.info = info
    ticker.history.return_value = _history(bars)
    if funds_raises:
        type(ticker).funds_data = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    else:
        ticker.funds_data = funds
    mod = MagicMock()
    mod.Ticker.return_value = ticker
    return mod


@pytest.fixture(autouse=True)
def fake_fx(monkeypatch):
    monkeypatch.setattr(yp, "_fx_to_usd", lambda c: 1.0 if c == "USD" else RATES.get(c, 0.0))
    import augur.data as data_module

    def _boom():
        pytest.fail("network yfinance access in a hermetic test")

    monkeypatch.setattr(data_module, "_get_yfinance", _boom)


@pytest.fixture(autouse=True)
def no_cn_nav(monkeypatch):
    """Step 6 adds a Sina NAV lookup for A-share ETFs; keep it offline here."""
    try:
        import augur.datasources.cn_fund_nav_provider as cn
    except ImportError:
        return
    monkeypatch.setattr(cn, "fetch_cn_fund_nav", lambda code: {})


def _fetch(info, bars, **kw):
    return YFinanceProvider(yf_loader=lambda: _yf(dict(info), bars, **kw)).fetch(info["symbol"])


# ---------------- detection ----------------


@pytest.mark.parametrize("ticker,quote_type,expected", [
    ("SPY", "ETF", "etf"),
    ("VFIAX", "MUTUALFUND", "etf"),
    ("AAPL", "EQUITY", "equity"),
    ("510300.SS", "EQUITY", "etf"),
    ("560010.SS", "", "etf"),
    ("588000.SS", "", "etf"),
    ("159919.SZ", "EQUITY", "etf"),
    ("600519.SS", "EQUITY", "equity"),
    ("000858.SZ", "EQUITY", "equity"),
    ("150001.SS", "", "equity"),   # 15 prefix only counts on Shenzhen
    ("510300.SZ", "", "equity"),   # 51 prefix only counts on Shanghai
    ("510300", "", "equity"),      # suffix required
])
def test_asset_type_rule(ticker, quote_type, expected):
    assert asset_type_for(ticker, quote_type) == expected


def test_cn_etf_code():
    assert cn_etf_code("510300.ss") == "510300"
    assert cn_etf_code("159919.SZ") == "159919"
    assert cn_etf_code("0700.HK") == ""


# ---------------- SPY ----------------


def test_spy_profile():
    out = _fetch(SPY_INFO, SPY_BARS, funds=_SpyFunds())
    assert out["asset_type"] == "etf"
    etf = out["etf"]
    assert etf["source"] == "yfinance"
    assert etf["aum_usd_bn"] == pytest.approx(796.865, rel=1e-3)
    assert etf["expense_ratio"] == pytest.approx(0.000945)
    assert etf["yield"] == pytest.approx(0.01)
    assert etf["category"] == "Large Blend"
    assert etf["turnover"] == pytest.approx(0.03)
    assert etf["nav"] == pytest.approx(718.51355)
    assert etf["top10_weight"] == pytest.approx(0.372937, rel=1e-4)
    assert 0 < etf["hhi"] < etf["top10_weight"]
    assert etf["sector_weights"]["technology"] == pytest.approx(0.3823)
    assert "bondPosition" not in etf["asset_classes"]
    assert etf["spread_pct"] == pytest.approx((716.78 - 716.43) / 716.605 * 100)
    assert etf["dollar_volume"] == pytest.approx(47952760 * 716.7)
    # Fund P/E and P/B move into the profile; the company fields stay 0.
    assert etf["portfolio_pe"] == pytest.approx(22.801332)
    assert etf["portfolio_pb"] == pytest.approx(1.6697731)
    assert out["pe"] == 0 and out["pb"] == 0
    # Market value of a fund is its net assets (was $0.0B).
    assert out["market_cap"] == pytest.approx(796.865, rel=1e-3)


def test_spy_premium_uses_close_on_nav_date():
    etf = _fetch(SPY_INFO, SPY_BARS, funds=_SpyFunds())["etf"]
    # navPrice is yesterday's NAV: compare with yesterday's close, not today's.
    assert etf["nav_date"] == "2026-11-24"
    assert etf["nav_date_inferred"] is True
    assert etf["premium_pct"] == pytest.approx((718.78 / 718.51355 - 1) * 100)
    assert abs(etf["premium_pct"]) < 0.1
    naive = (716.7 / 718.51355 - 1) * 100
    assert naive == pytest.approx(-0.25, abs=0.01)


# ---------------- 2800.HK ----------------


def test_hk_etf_profile_in_usd():
    out = _fetch(HK_INFO, HK_BARS, funds=None)
    assert out["asset_type"] == "etf"
    etf = out["etf"]
    assert etf["aum_usd_bn"] == pytest.approx(123.81 * 0.1276, rel=1e-3)
    assert etf["expense_ratio"] == pytest.approx(0.001)
    assert etf["nav_date"] == "2026-11-24"
    assert etf["premium_pct"] == pytest.approx((22.34 / 22.3503 - 1) * 100)
    assert etf["dollar_volume"] == pytest.approx(568150043 * 22.5 * 0.1276)
    assert etf["portfolio_pb"] == pytest.approx(0.76896787)
    assert "category" not in etf
    assert out["pb"] == 0


def test_hk_etf_without_fx_omits_usd_keys(monkeypatch):
    monkeypatch.setattr(yp, "_fx_to_usd", lambda c: 0.0)
    out = _fetch(HK_INFO, HK_BARS)
    assert "aum_usd_bn" not in out["etf"]
    assert "dollar_volume" not in out["etf"]
    assert out["etf"]["nav"] == pytest.approx(22.3503)
    assert out["data_warnings"]


# ---------------- 510300.SS ----------------


def test_cn_etf_recognised_despite_equity_quote_type():
    out = _fetch(CN_INFO, CN_BARS, funds=_BrokenFunds())
    assert out["asset_type"] == "etf"
    etf = out["etf"]
    assert etf["source"] == "yfinance"
    assert "nav" not in etf  # yfinance has no NAV for A-share funds
    assert etf["spread_pct"] > 0
    assert out["pe"] == 0


def test_funds_data_exception_degrades_not_fails():
    out = _fetch(SPY_INFO, SPY_BARS, funds_raises=True)
    assert out["asset_type"] == "etf"
    etf = out["etf"]
    assert etf["aum_usd_bn"] > 700
    assert etf["expense_ratio"] == pytest.approx(0.000945)  # from info, percent / 100
    assert "top10_weight" not in etf
    assert out["price"] == pytest.approx(716.7)


def test_broken_funds_attributes_degrade():
    out = _fetch(SPY_INFO, SPY_BARS, funds=_BrokenFunds())
    assert out["etf"]["category"] == "Large Blend"
    assert "sector_weights" not in out["etf"]


def test_equity_has_no_profile():
    info = {"symbol": "AAPL", "quoteType": "EQUITY", "currency": "USD",
            "currentPrice": 200.0, "trailingPE": 30.0, "priceToBook": 45.0, "marketCap": 3e12}
    out = _fetch(info, SPY_BARS)
    assert out["asset_type"] == "equity"
    assert "etf" not in out
    assert out["pe"] == 30.0


# ---------------- premium helper ----------------


def test_premium_with_known_nav_date():
    bars = [("2026-11-24", 4.033), ("2026-11-25", 3.970), ("2026-11-26", 3.974)]
    res = premium_on_nav_date(3.9718, bars, nav_date="2026-11-25")
    assert res["nav_date_inferred"] is False
    assert res["premium_pct"] == pytest.approx((3.970 / 3.9718 - 1) * 100)


def test_premium_needs_two_bars_when_inferring():
    assert premium_on_nav_date(10.0, [("2026-11-26", 10.0)]) == {}
    assert premium_on_nav_date(0.0, SPY_BARS) == {}


# ---------------- context level ----------------


def _ctx_for(monkeypatch, provider, ticker):
    import augur.data as data_module

    monkeypatch.setattr(data_module, "_get_providers", lambda: [provider])
    data_module.clear_cache()
    return data_module


def test_context_skips_edgar_for_etf(monkeypatch):
    import augur.consensus.edgar_fundamentals as ef

    called = []
    monkeypatch.setattr(ef, "fetch_edgar_fundamentals", lambda *a, **k: called.append(a) or {})
    provider = YFinanceProvider(yf_loader=lambda: _yf(dict(SPY_INFO), SPY_BARS, funds=_SpyFunds()))
    data_module = _ctx_for(monkeypatch, provider, "SPY")
    ctx = data_module.fetch_market_context("SPY", force_refresh=True)
    assert ctx.asset_type == "etf"
    assert ctx.etf["aum_usd_bn"] > 700
    assert ctx.pe == 0
    assert called == []
    assert ctx.to_dict()["etf"]["nav_date_inferred"] is True


def test_stooq_style_context_gets_suffix_rule(monkeypatch):
    from augur.datasources.base import DataProvider

    class _Plain(DataProvider):
        name = "plain"

        def fetch(self, ticker):
            return {"price": 3.97, "pe": 12.0, "pb": 1.4}

    data_module = _ctx_for(monkeypatch, _Plain(), "510300.SS")
    ctx = data_module._build_context_from_providers("510300.SS")
    assert ctx.asset_type == "etf"
    assert ctx.pe == 0 and ctx.pb == 0
    assert ctx.etf == {"portfolio_pe": 12.0, "portfolio_pb": 1.4}

    ctx2 = data_module._build_context_from_providers("600519.SS")
    assert ctx2.asset_type == "equity"
    assert ctx2.pe == 12.0


def test_edgar_overlay_updates_evidence(monkeypatch):
    """Bug 4: evidence must cite the value the personas actually read."""
    import augur.consensus.edgar_fundamentals as ef
    import augur.data as data_module
    from augur.personas.base import MarketContext

    monkeypatch.setattr(ef, "fetch_edgar_fundamentals",
                        lambda *a, **k: {"debt_ratio": 0.72, "pe": 0.0})
    ctx = MarketContext(ticker="AAPL", price=200.0, debt_ratio=0.457, pe=30.0)
    ctx.evidence_items = [
        {"metric": "debt_ratio", "value": 0.457, "source": "yfinance"},
        {"metric": "pe", "value": 30.0, "source": "yfinance"},
    ]
    data_module._overlay_edgar_fundamentals(ctx)
    assert ctx.debt_ratio == 0.72
    by_metric = {ev["metric"]: ev for ev in ctx.evidence_items}
    assert by_metric["debt_ratio"]["value"] == pytest.approx(0.72)
    assert by_metric["debt_ratio"]["source"] == "edgar"
    assert by_metric["pe"]["source"] == "yfinance"  # not overlaid, untouched
