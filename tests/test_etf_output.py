# -*- coding: utf-8 -*-
"""v14 step 7: output surfaces (CLI / report / MCP) for ETFs, currency labels,
and pure-JSON stdout for --json. All contexts are hand-built; the data layer is
monkeypatched, so nothing touches the network."""

import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from augur.cli import main
from augur.personas.base import MarketContext


def spy_ctx() -> MarketContext:
    ctx = MarketContext(
        ticker="SPY", asset_type="etf", price=600.0, change_pct=0.3,
        rsi=55.0, macd=1.0, macd_signal=0.8, macd_histogram=0.2,
        sma20=595.0, sma50=585.0, sma200=560.0, atr=6.0, volatility_20d=0.14,
        beta_1y=1.0, price_vs_52w_high=-3.0, price_vs_52w_low=25.0,
        volume=7e7, currency="USD", fx_rate_usd=1.0,
        company_name="SPDR S&P 500 ETF Trust",
        etf={
            "aum_usd_bn": 797.0, "expense_ratio": 0.000945, "yield": 0.0115,
            "category": "Large Blend", "nav": 600.2, "nav_date": "2026-11-25",
            "nav_date_inferred": True, "premium_pct": -0.04,
            "top10_weight": 0.36, "spread_pct": 0.002, "portfolio_pe": 22.8,
            "source": "yfinance",
        },
    )
    ctx.data_source = "yfinance"
    return ctx


def aapl_ctx() -> MarketContext:
    ctx = MarketContext(
        ticker="AAPL", price=210.0, market_cap=3200.0, pe=32.0, pb=48.0,
        fcf=105.0, revenue=390.0, revenue_growth=0.05, gross_margins=0.46,
        operating_margins=0.31, roe=1.45, debt_ratio=0.62, rsi=58.0,
        sector="Technology", industry="Consumer Electronics",
        currency="USD", fx_rate_usd=1.0,
    )
    ctx.data_source = "yfinance"
    return ctx


def tencent_ctx(fx_rate_usd: float) -> MarketContext:
    """0700.HK: HKD quote, CNY statements. fx 0 = data layer could not convert."""
    converted = fx_rate_usd > 0
    ctx = MarketContext(
        ticker="0700.HK", price=380.0, currency="HKD", financial_currency="CNY",
        fx_rate_usd=fx_rate_usd,
        market_cap=400.0 if converted else 3100.0,
        fcf=22.0 if converted else 160.0,
        pe=18.0, roe=0.21, gross_margins=0.52, sector="Communication Services",
        industry="Internet Content & Information",
    )
    ctx.data_source = "yfinance"
    return ctx


class _FakeLearning:
    has_learned_weights = False

    def __init__(self):
        self.recorded = []

    def record_prediction(self, *args, **kwargs):
        self.recorded.append(args)

    @contextmanager
    def batch(self):
        yield

    def get_weights(self):
        return {}


@pytest.fixture
def fake_learning():
    le = _FakeLearning()
    with patch("augur.registry._get_learning_engine", return_value=le), \
         patch("augur.registry._check_and_record_outcomes", return_value=None):
        yield le


@pytest.fixture
def fetch_returns():
    """Route the data layer to a hand-built context per ticker."""
    contexts = {}

    def fake_fetch(ticker, *a, **kw):
        return contexts[ticker.upper()]()

    with patch("augur.data.fetch_market_context", side_effect=fake_fetch), \
         patch("augur.optional_deps.is_available", return_value=True):
        yield contexts


def _run(args):
    return CliRunner().invoke(main, args, catch_exceptions=False)


# ------------------------------------------------------------- --json ----

@pytest.mark.parametrize("args", [
    ["consensus", "AAPL", "--json"],
    ["analyze", "AAPL", "--json"],
    ["fetch", "AAPL", "--json"],
    ["portfolio", "AAPL", "--format", "json"],
])
def test_json_stdout_is_pure_json(args, fetch_returns, fake_learning):
    fetch_returns["AAPL"] = aapl_ctx
    result = _run(args)
    assert result.exit_code == 0, result.output
    json.loads(result.stdout)  # progress text must not be on stdout
    assert "Fetching" in result.stderr or "Auto-fetching" in result.stderr


def test_consensus_json_for_etf(fetch_returns, fake_learning):
    fetch_returns["SPY"] = spy_ctx
    result = _run(["consensus", "SPY", "--json"])
    payload = json.loads(result.stdout)
    assert payload["asset_type"] == "etf"
    meta = payload["consensus"]["metadata"]
    assert meta["consensus_withheld"] is True
    assert meta["applicable_agents"] == ["dalio"]
    assert payload["etf"]["aum_usd_bn"] == 797.0
    assert payload["etf_findings"] == []
    assert payload["individual"]["buffett"]["metadata"]["not_applicable"] is True
    assert fake_learning.recorded == []


def test_portfolio_json_marks_withheld_fund(fetch_returns, fake_learning):
    fetch_returns["SPY"] = spy_ctx
    payload = json.loads(_run(["portfolio", "SPY", "--format", "json"]).stdout)
    row = payload["tickers"][0]
    assert row["signal"] == "WITHHELD" and row["kelly_pct"] == 0.0
    assert row["consensus_withheld"] is True
    assert payload["cash_pct"] == 100.0


# --------------------------------------------------------- consensus text --

def test_consensus_text_for_etf(fetch_returns, fake_learning):
    fetch_returns["SPY"] = spy_ctx
    result = _run(["consensus", "SPY"])
    out = result.stdout
    assert "SPY Consensus (ETF)" in out
    assert "WITHHELD" in out
    assert "适用大师 1 位，不输出共识" in out
    assert "ETF 概况" in out and "ETF 体检" in out and "$797.00B" in out
    assert "Applicable personas (1)" in out and "Dalio" in out
    assert "Abstained (17" in out and "buffett" in out
    # no company-fundamental verdicts or position for a fund
    for banned in ("小市值", "毛利率过低", "Market Cap", "ROE", "Kelly Size: 0"):
        assert banned not in out, banned


def test_analyze_text_for_etf_uses_fund_block(fetch_returns, fake_learning):
    fetch_returns["SPY"] = spy_ctx
    out = _run(["analyze", "SPY"]).stdout
    assert "WITHHELD" in out and "ETF 体检" in out
    assert "Masters Consensus" not in out


def test_analyze_single_persona_not_applicable(fetch_returns, fake_learning):
    fetch_returns["SPY"] = spy_ctx
    out = _run(["analyze", "SPY", "--persona", "buffett"]).stdout
    assert "N/A (not applicable to funds)" in out
    assert "不适用于基金" in out


def test_equity_consensus_text_unchanged_shape(fetch_returns, fake_learning):
    fetch_returns["AAPL"] = aapl_ctx
    out = _run(["consensus", "AAPL"]).stdout
    assert "AAPL Consensus" in out and "Agent Breakdown" in out
    assert "ETF" not in out


# ----------------------------------------------------------------- fetch --

def test_fetch_text_for_etf_hides_company_lines(fetch_returns):
    fetch_returns["SPY"] = spy_ctx
    out = _run(["fetch", "SPY"]).stdout
    assert "Type               ETF" in out
    assert "Price              600.00 USD" in out
    assert "ETF 概况" in out and "费率" in out and "0.09%" in out
    assert "溢价折价" in out and "-0.04%" in out and "36.0%" in out
    for banned in ("Market Cap", "ROE", "Gross Margins", "FCF", "Debt Ratio"):
        assert banned not in out, banned
    assert "RSI" in out


def test_fetch_text_hk_unconverted_labels_native_currency(fetch_returns):
    fetch_returns["0700.HK"] = lambda: tencent_ctx(0.0)
    out = _run(["fetch", "0700.HK"]).stdout
    assert "Market Cap (HKD)   3,100.0B HKD" in out
    assert "FCF (CNY)          160.00B CNY" in out
    assert "Price              380.00 HKD" in out
    assert "$3,100" not in out


def test_fetch_text_hk_converted_is_usd(fetch_returns):
    fetch_returns["0700.HK"] = lambda: tencent_ctx(0.128)
    out = _run(["fetch", "0700.HK"]).stdout
    assert "Market Cap         $400.0B" in out
    assert "FCF                $22.00B" in out
    assert "Price              380.00 HKD" in out


def test_fetch_text_usd_equity(fetch_returns):
    fetch_returns["AAPL"] = aapl_ctx
    out = _run(["fetch", "AAPL"]).stdout
    assert "Market Cap         $3,200.0B" in out
    assert "ROE" in out


# ---------------------------------------------------------------- report --

def test_report_for_etf(fake_learning):
    from augur.registry import AgentRegistry, DecisionCoordinator
    from augur.report import generate_report

    ctx = spy_ctx()
    coord = DecisionCoordinator(AgentRegistry())
    results = coord.analyze_with_all(ctx)
    consensus = coord.get_consensus(results, ticker="SPY", context=ctx)
    report = generate_report("SPY", ctx, results, consensus)
    assert "SPY 基金分析报告（ETF）" in report
    assert "不输出共识信号" in report and "适用大师 1 位" in report
    assert "## ETF 概况" in report and "### ETF 体检" in report
    assert "$797.00B" in report and "按上一交易日推断" in report
    assert "弃权" in report and "不提供仓位建议" in report
    for banned in ("毛利率", "ROE", "建议仓位", "半Kelly", "小市值"):
        assert banned not in report, banned


def test_report_currency_labels():
    from augur.report import _format_financial_overview, _format_market_cap

    unconverted = _format_financial_overview(tencent_ctx(0.0))
    assert "| 市值 (HKD) | 3.10万亿 HKD |" in unconverted
    assert "| 自由现金流 (CNY) | 160.00B CNY |" in unconverted
    assert "| 当前价格 | 380.00 HKD |" in unconverted
    converted = _format_financial_overview(tencent_ctx(0.128))
    assert "| 市值 | $400.00B |" in converted
    assert "| 当前价格 | 380.00 HKD |" in converted
    assert _format_market_cap(float("nan"), "HKD") == "N/A"


def test_report_neutral_position_text_has_no_light_position():
    from augur.personas.base import AgentResponse, SignalType
    from augur.report import _format_position_recommendation

    cons = AgentResponse("consensus", "c", SignalType.NEUTRAL, 0.8, 5.5, "r",
                         metadata={"position_pct": 0.0})
    text = _format_position_recommendation(cons)
    assert "轻仓" not in text and "观望" in text


# ------------------------------------------------------------------- MCP --

def test_mcp_build_context_asset_type():
    from augur.mcp_server import _build_context, _validate_asset_type

    ctx = _build_context("SPY", price=600, asset_type="ETF")
    assert ctx.asset_type == "etf"
    assert _build_context("AAPL", price=200).asset_type == "equity"
    assert _validate_asset_type("etf") is None and _validate_asset_type("") is None
    assert _validate_asset_type("crypto").startswith("Error")


def test_mcp_build_context_asset_type_overrides_fetch():
    from augur.mcp_server import _build_context

    with patch("augur.data.fetch_market_context", side_effect=lambda *a, **k: aapl_ctx()):
        assert _build_context("X", asset_type="fund").asset_type == "fund"
        assert _build_context("X").asset_type == "equity"


def test_mcp_fetch_text():
    from augur.mcp_server import _fetch_text

    etf = _fetch_text(spy_ctx())
    assert "Type:         ETF" in etf and "ETF 概况" in etf and "ROE" not in etf
    hk = _fetch_text(tencent_ctx(0.0))
    assert "Market Cap (HKD):" in hk and "3,100B HKD" in hk and "FCF (CNY):" in hk
    assert "Price:        380.00 HKD" in hk


def _call_tool(name, args):
    import asyncio
    pytest.importorskip("mcp")
    from augur.mcp_server import create_server

    out = asyncio.run(create_server().call_tool(name, args))
    if isinstance(out, tuple):  # newer FastMCP: (content, structured)
        out = out[0]
    return "\n".join(getattr(c, "text", str(c)) for c in out)


def test_mcp_consensus_manual_etf(fake_learning):
    text = _call_tool("augur_consensus", {"ticker": "SPY", "price": 600, "asset_type": "etf"})
    assert "Consensus for SPY (ETF)" in text
    assert "WITHHELD" in text and "Kelly Position: n/a (fund)" in text
    assert "Abstained (17" in text
    assert fake_learning.recorded == []


def test_mcp_analyze_manual_etf_persona():
    text = _call_tool("augur_analyze", {"ticker": "SPY", "price": 600,
                                        "asset_type": "etf", "persona": "buffett"})
    assert "N/A (not applicable to funds)" in text


def test_mcp_configure_is_deprecated_noop(tmp_path, monkeypatch):
    from augur import config as cfg

    called = []
    monkeypatch.setattr(cfg, "save_config", lambda *a, **k: called.append(1))
    monkeypatch.setattr(cfg, "set_config", lambda *a, **k: called.append(1))
    text = _call_tool("augur_configure", {"persona_id": "buffett", "model": "gpt-4o"})
    assert "Augur does not call models" in text and "no effect" in text
    assert called == []
