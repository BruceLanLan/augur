# -*- coding: utf-8 -*-
"""v14 step 5: persona unit / sector fixes (dayu volatility, Thiel sector)."""

from pathlib import Path

from augur.personas.base import MarketContext
from augur.personas.dayu import DayuAgent
from augur.personas.thiel import ThielAgent, is_tech_business

_YAML = Path(__file__).resolve().parents[1] / "personas" / "custom" / "da-yu.yaml"


class TestDayuVolatilityUnits:
    def test_high_volatility_lowers_risk_score(self):
        agent = DayuAgent()
        calm = agent._score_risk_capital(MarketContext(ticker="X", volatility_20d=0.20))
        wild = agent._score_risk_capital(MarketContext(ticker="X", volatility_20d=0.65))
        assert wild < calm

    def test_065_hits_top_bucket(self):
        # 65% > 60% -> -3 from the base 5 (max_drawdown 0 -> +1)
        assert DayuAgent()._score_risk_capital(
            MarketContext(ticker="X", volatility_20d=0.65)) == 3.0

    def test_high_volatility_risk_and_display_in_percent(self):
        resp = DayuAgent().analyze(MarketContext(ticker="X", price=10.0, volatility_20d=0.65))
        assert any("超高波动(65%)" in r for r in resp.risks)
        assert "20日波动: 65.0%" in resp.reasoning

    def test_moderate_volatility_no_high_vol_risk(self):
        resp = DayuAgent().analyze(MarketContext(ticker="X", price=10.0, volatility_20d=0.30))
        assert not any("超高波动" in r for r in resp.risks)

    def test_yaml_volatility_rules_use_percent(self):
        from augur.persona_loader import _compute_factor, load_persona_yaml

        agent = load_persona_yaml(_YAML)
        fdef = agent._factor_defs["risk_capital"]
        base = _compute_factor(fdef, MarketContext(ticker="X", volatility_20d=0.0))
        mid = _compute_factor(fdef, MarketContext(ticker="X", volatility_20d=0.30))
        high = _compute_factor(fdef, MarketContext(ticker="X", volatility_20d=0.65))
        assert mid == base + 1
        assert high == base - 2


class TestThielSector:
    def _googl(self):
        return MarketContext(
            ticker="GOOGL", price=170.0, market_cap=2100.0, pe=24.0, ps=6.0,
            gross_margins=0.58, operating_margins=0.32, roe=0.30,
            revenue_growth=0.12, fcf=70.0,
            sector="Communication Services",
            industry="Internet Content & Information",
        )

    def test_googl_not_flagged_non_tech(self):
        resp = ThielAgent().analyze(self._googl())
        assert not any("非科技行业" in r for r in resp.risks)

    def test_energy_still_flagged_non_tech(self):
        ctx = self._googl()
        ctx.ticker, ctx.sector, ctx.industry = "XOM", "Energy", "Oil & Gas Integrated"
        resp = ThielAgent().analyze(ctx)
        assert any("非科技行业" in r for r in resp.risks)

    def test_predicate(self):
        assert is_tech_business("Technology", "Consumer Electronics")
        assert is_tech_business("Communication Services", "Telecom Services")
        assert is_tech_business("Consumer Cyclical", "Internet Retail")
        assert is_tech_business("", "Software - Application")
        assert not is_tech_business("Energy", "Oil & Gas Integrated")
        assert not is_tech_business("", "")
