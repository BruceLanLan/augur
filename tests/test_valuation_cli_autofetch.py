# -*- coding: utf-8 -*-
"""`augur valuation TICKER` must not print a made-up fair value.

Found by running the README command from a fresh install (2026-09-17): for
AAPL it printed "Free Cash Flow: $0.0B ... Fair Value/Share: $0.00".
MarketContext stores fcf / market_cap / total_cash / total_debt in billions
of USD, but run_valuation treated ctx.fcf as dollars, invented
shares_outstanding=1e9 when it could not find one, and substituted
revenue * 0.15 for a missing FCF.
"""
import pytest

from augur.personas.base import MarketContext


def _ctx(**kw):
    base = dict(ticker="AAPL", price=200.0, market_cap=3000.0, fcf=100.0,
                total_cash=60.0, total_debt=110.0, revenue=400.0)
    base.update(kw)
    return MarketContext(**base)


@pytest.fixture
def fetched(monkeypatch):
    import augur.data as data_module

    holder = {}

    def _fake_fetch(ticker, *a, **k):
        return holder["ctx"]

    monkeypatch.setattr(data_module, "fetch_market_context", _fake_fetch)
    return holder


def test_autofetch_converts_billions_and_derives_shares(fetched):
    from augur.cli_commands.valuation_cmd import run_valuation

    fetched["ctx"] = _ctx()
    out = run_valuation("AAPL")

    assert "Free Cash Flow:      $100.0B" in out
    # 3000B market cap / $200 = 15B shares; net debt 110B - 60B = 50B.
    assert "Shares Outstanding:  15.00B" in out
    assert "Net Debt:            $50.0B" in out
    assert "Market Price:        $200.00" in out
    fair = float(out.split("Fair Value/Share:    $")[1].split()[0])
    assert 50 < fair < 1000, out


def test_matches_explicit_dollar_inputs(fetched):
    from augur.cli_commands.valuation_cmd import run_valuation

    fetched["ctx"] = _ctx()
    auto = run_valuation("AAPL")
    explicit = run_valuation("AAPL", fcf=100e9, shares=15e9, net_debt=50e9)

    pick = lambda s: s.split("Fair Value/Share:    $")[1].split()[0]  # noqa: E731
    assert pick(auto) == pick(explicit)


def test_missing_fcf_is_an_error_not_a_revenue_guess(fetched):
    from augur.cli_commands.valuation_cmd import run_valuation

    fetched["ctx"] = _ctx(fcf=0.0)
    out = run_valuation("AAPL")

    assert out.startswith("Error:")
    assert "--fcf" in out


def test_missing_shares_is_an_error_not_one_billion(fetched):
    from augur.cli_commands.valuation_cmd import run_valuation

    fetched["ctx"] = _ctx(market_cap=0.0)
    out = run_valuation("AAPL")

    assert out.startswith("Error:")
    assert "--shares" in out


def test_cli_exits_nonzero_on_insufficient_data(fetched):
    from click.testing import CliRunner

    from augur.cli_commands.valuation_cmd import valuation_cmd

    fetched["ctx"] = _ctx(fcf=0.0, market_cap=0.0, price=0.0)
    result = CliRunner().invoke(valuation_cmd, ["AAPL"])

    assert result.exit_code == 1
    assert "Error:" in result.output
