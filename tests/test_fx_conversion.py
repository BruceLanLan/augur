# -*- coding: utf-8 -*-
"""v14 step 2: amounts in MarketContext are USD billions for every market.

yfinance returns amounts in the instrument's own currency: market cap / EV in
the trading currency (``currency``), statements in ``financialCurrency``.
Tencent (0700.HK) trades in HKD but reports in CNY; before v14 its HKD 3.1T
market cap was read as $3,097B and the DCF compared a CNY per-share value
against an HKD price (-68.9%).
"""
from unittest.mock import MagicMock

import pytest

from augur.datasources import YFinanceProvider
from augur.datasources import yfinance_provider as yp

RATES = {"HKD": 0.1276, "CNY": 0.1501, "GBP": 1.31, "TWD": 0.031}


def _yf(info):
    ticker = MagicMock()
    ticker.info = info
    ticker.history.return_value = MagicMock(empty=True)
    mod = MagicMock()
    mod.Ticker.return_value = ticker
    return mod


@pytest.fixture
def fx(monkeypatch):
    calls = []

    def _fake(ccy):
        calls.append(ccy)
        if ccy == "USD":
            return 1.0
        return RATES.get(ccy, 0.0)

    monkeypatch.setattr(yp, "_fx_to_usd", _fake)
    return calls


@pytest.fixture(autouse=True)
def _no_live_fx(monkeypatch):
    """Fail loudly if an unpatched FX lookup would reach yfinance."""
    import augur.data as data_module

    def _boom():
        # pytest.fail raises a BaseException, so _fx_to_usd's except cannot swallow it.
        pytest.fail("network yfinance access in a hermetic test")

    monkeypatch.setattr(data_module, "_get_yfinance", _boom)
    yp.clear_fx_cache()


TENCENT = {
    "symbol": "0700.HK", "currency": "HKD", "financialCurrency": "CNY",
    "currentPrice": 344.0, "marketCap": 3.0976e12, "enterpriseValue": 3.2005e12,
    "freeCashflow": 6.0255e10, "totalRevenue": 8.0295e11, "ebitda": 2.9e11,
    "totalCash": 4.0e11, "totalDebt": 3.5e11,
}


def test_tencent_market_cap_and_financials_in_usd(fx):
    out = YFinanceProvider(yf_loader=lambda: _yf(dict(TENCENT))).fetch("0700.HK")
    assert out["market_cap"] == pytest.approx(3.0976e12 * 0.1276 / 1e9)
    assert 380 < out["market_cap"] < 420
    assert out["enterprise_value"] == pytest.approx(3.2005e12 * 0.1276 / 1e9)
    # Statements are CNY -> CNY rate, not the HKD one.
    assert out["fcf"] == pytest.approx(6.0255e10 * 0.1501 / 1e9)
    assert out["revenue"] == pytest.approx(8.0295e11 * 0.1501 / 1e9)
    assert out["ebitda"] == pytest.approx(2.9e11 * 0.1501 / 1e9)
    assert out["total_cash"] == pytest.approx(4.0e11 * 0.1501 / 1e9)
    assert out["total_debt"] == pytest.approx(3.5e11 * 0.1501 / 1e9)
    # Price stays in the trading currency.
    assert out["price"] == 344.0
    assert out["currency"] == "HKD"
    assert out["financial_currency"] == "CNY"
    assert out["fx_rate_usd"] == pytest.approx(0.1276)
    assert "data_warnings" not in out


def test_usd_stock_unchanged_and_no_lookup(fx):
    info = {"symbol": "AAPL", "currency": "USD", "financialCurrency": "USD",
            "currentPrice": 200.0, "marketCap": 3.0e12, "freeCashflow": 1.0e11}
    out = YFinanceProvider(yf_loader=lambda: _yf(info)).fetch("AAPL")
    assert out["market_cap"] == pytest.approx(3000.0)
    assert out["fcf"] == pytest.approx(100.0)
    assert out["fx_rate_usd"] == 1.0
    assert set(fx) <= {"USD"}


def test_missing_currency_is_left_alone(fx):
    info = {"symbol": "X", "currentPrice": 10.0, "marketCap": 5.0e9}
    out = YFinanceProvider(yf_loader=lambda: _yf(info)).fetch("X")
    assert out["market_cap"] == pytest.approx(5.0)
    assert out["fx_rate_usd"] == 0.0
    assert "data_warnings" not in out
    assert fx == []


def test_adr_converts_financials_only(fx):
    info = {"symbol": "TSM", "currency": "USD", "financialCurrency": "TWD",
            "currentPrice": 200.0, "marketCap": 1.0e12, "freeCashflow": 9.0e11}
    out = YFinanceProvider(yf_loader=lambda: _yf(info)).fetch("TSM")
    assert out["market_cap"] == pytest.approx(1000.0)
    assert out["fcf"] == pytest.approx(9.0e11 * 0.031 / 1e9)
    assert out["fx_rate_usd"] == 1.0


def test_pence_quote_uses_pound_for_cap_and_pence_rate_for_price(fx):
    # Live shape (SHEL.L): price in GBp, marketCap in GBP.
    info = {"symbol": "SHEL.L", "currency": "GBp", "financialCurrency": "USD",
            "currentPrice": 3555.5, "marketCap": 2.0049e11, "freeCashflow": 2.9e10}
    out = YFinanceProvider(yf_loader=lambda: _yf(info)).fetch("SHEL.L")
    assert out["market_cap"] == pytest.approx(2.0049e11 * 1.31 / 1e9)
    assert out["fcf"] == pytest.approx(29.0)
    assert out["fx_rate_usd"] == pytest.approx(0.0131)
    assert out["price"] == 3555.5


@pytest.mark.parametrize("missing", ["HKD", "CNY"])
def test_any_missing_leg_converts_nothing(monkeypatch, missing):
    monkeypatch.setattr(yp, "_fx_to_usd", lambda c: 0.0 if c == missing else RATES.get(c, 1.0))
    out = YFinanceProvider(yf_loader=lambda: _yf(dict(TENCENT))).fetch("0700.HK")
    assert out["market_cap"] == pytest.approx(3097.6)
    assert out["fcf"] == pytest.approx(60.255)
    assert out["fx_rate_usd"] == 0.0
    assert len(out["data_warnings"]) == 1
    assert missing in out["data_warnings"][0]


def test_adr_with_missing_financial_rate_is_flagged(monkeypatch):
    monkeypatch.setattr(yp, "_fx_to_usd", lambda c: 1.0 if c == "USD" else 0.0)
    info = {"symbol": "TSM", "currency": "USD", "financialCurrency": "TWD",
            "currentPrice": 200.0, "marketCap": 1.0e12, "freeCashflow": 9.0e11}
    out = YFinanceProvider(yf_loader=lambda: _yf(info)).fetch("TSM")
    assert out["fx_rate_usd"] == 0.0
    assert out["fcf"] == pytest.approx(900.0)
    assert "TWD" in out["data_warnings"][0]


def test_warning_reaches_context(monkeypatch):
    import augur.data as data_module

    monkeypatch.setattr(yp, "_fx_to_usd", lambda c: 0.0)
    provider = YFinanceProvider(yf_loader=lambda: _yf(dict(TENCENT)))
    monkeypatch.setattr(data_module, "_get_providers", lambda: [provider])
    data_module.clear_cache()
    ctx = data_module._build_context_from_providers("0700.HK")
    assert ctx.fx_rate_usd == 0
    assert ctx.financial_currency == "CNY"
    assert ctx.data_warnings and "HKD" in ctx.data_warnings[0]


def test_fx_lookup_reads_latest_close_and_caches(monkeypatch):
    import augur.data as data_module

    hist = MagicMock()
    hist.__getitem__.return_value.tolist.return_value = [0.1275, 0.1276]
    tk = MagicMock()
    tk.history.return_value = hist
    yf = MagicMock()
    yf.Ticker.return_value = tk
    monkeypatch.setattr(data_module, "_get_yfinance", lambda: yf)
    yp.clear_fx_cache()
    assert yp._fx_to_usd("HKD") == pytest.approx(0.1276)
    assert yp._fx_to_usd("hkd") == pytest.approx(0.1276)
    yf.Ticker.assert_called_once_with("HKDUSD=X")
    assert yp._fx_to_usd("USD") == 1.0
    data_module.clear_cache()
    assert yp._fx_cache == {}


def test_fx_lookup_failure_returns_zero_and_is_not_cached(monkeypatch):
    import augur.data as data_module

    yf = MagicMock()
    yf.Ticker.side_effect = RuntimeError("offline")
    monkeypatch.setattr(data_module, "_get_yfinance", lambda: yf)
    yp.clear_fx_cache()
    assert yp._fx_to_usd("HKD") == 0.0
    assert "HKD" not in yp._fx_cache


def test_split_currency():
    assert yp.split_currency("GBp") == ("GBP", 0.01)
    assert yp.split_currency("hkd") == ("HKD", 1.0)
    assert yp.split_currency("") == ("", 1.0)


# ---------------- valuation in one currency ----------------


@pytest.fixture
def fetched(monkeypatch):
    import augur.data as data_module

    holder = {}
    monkeypatch.setattr(data_module, "fetch_market_context", lambda t, *a, **k: holder["ctx"])
    return holder


def _tencent_ctx(**kw):
    from augur.personas.base import MarketContext

    base = dict(ticker="0700.HK", price=344.0, currency="HKD", financial_currency="CNY",
                fx_rate_usd=0.1276, market_cap=3.0976e12 * 0.1276 / 1e9,
                fcf=6.0255e10 * 0.1501 / 1e9, total_cash=60.0, total_debt=52.5)
    base.update(kw)
    return MarketContext(**base)


def test_valuation_compares_in_one_currency(fetched):
    from augur.cli_commands.valuation_cmd import run_valuation

    fetched["ctx"] = _tencent_ctx()
    out = run_valuation("0700.HK")
    # shares = USD cap / USD price = the real ~9.0B share count
    assert "Shares Outstanding:  9.00B" in out
    assert "Market Price:        HKD 344.00 ($43.89)" in out
    fair_usd = float(out.split("Fair Value/Share:    $")[1].split()[0])
    fair_hkd = float(out.split("Fair Value (HKD):")[1].split()[0])
    assert fair_hkd == pytest.approx(fair_usd / 0.1276, rel=1e-3)
    upside = float(out.split("Upside/Downside:")[1].split("%")[0])
    assert upside == pytest.approx((fair_usd / (344.0 * 0.1276) - 1) * 100, abs=0.1)


def test_valuation_without_fx_does_not_mix_currencies(fetched):
    from augur.cli_commands.valuation_cmd import run_valuation

    fetched["ctx"] = _tencent_ctx(fx_rate_usd=0.0, market_cap=3097.6, fcf=60.255)
    out = run_valuation("0700.HK")
    assert out.startswith("Error:")
    assert "FX rate for HKD unavailable" in out
    explicit = run_valuation("0700.HK", fcf=9e9, shares=9e9, net_debt=0)
    assert "Upside/Downside" not in explicit
