# -*- coding: utf-8 -*-
"""v14 step 1: ETF abstention, withheld consensus, ETF health checklist.

Contexts are hand-built (no network). The fund guard lives in
``BaseAgent.__init_subclass__`` so every ``agent.analyze(ctx)`` call path is
covered, including YAML personas.
"""

import importlib
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from augur.etf import (
    FUND_APPLICABLE_PERSONAS,
    MIN_APPLICABLE_FOR_CONSENSUS,
    assess_etf,
    etf_overview_lines,
    is_fund,
    unchecked_items,
)
from augur.personas.base import AgentResponse, BaseAgent, MarketContext, SignalType

_ROOT = Path(__file__).resolve().parents[1]
_YAML_DIR = _ROOT / "personas" / "custom"


def etf_ctx(**overrides) -> MarketContext:
    """SPY-like fund context following the v14 data contract (pe/pb = 0)."""
    base = dict(
        ticker="SPY", asset_type="etf", price=600.0, change_pct=0.3,
        rsi=55.0, macd=1.0, macd_signal=0.8, macd_histogram=0.2,
        sma20=595.0, sma50=585.0, sma200=560.0, atr=6.0,
        volatility_20d=0.14, beta_1y=1.0, price_vs_52w_high=-3.0,
        price_vs_52w_low=25.0, volume=7e7, avg_volume=7e7,
        currency="USD", fx_rate_usd=1.0, company_name="SPDR S&P 500 ETF Trust",
        etf={
            "aum_usd_bn": 797.0, "expense_ratio": 0.000945, "yield": 0.0115,
            "category": "Large Blend", "nav": 600.2, "nav_date": "2026-11-25",
            "nav_date_inferred": True, "premium_pct": -0.04,
            "top10_weight": 0.36, "spread_pct": 0.002, "portfolio_pe": 22.8,
            "source": "yfinance",
        },
    )
    base.update(overrides)
    return MarketContext(**base)


# Company fields perturbed by the invariance test, each at two extremes.
COMPANY_PERTURBATIONS = [
    {"pe": 8.0}, {"pe": 60.0},
    {"pb": 0.8}, {"pb": 12.0},
    {"roe": 0.35}, {"roe": -0.2},
    {"gross_margins": 0.7}, {"gross_margins": 0.1},
    {"operating_margins": 0.4}, {"operating_margins": -0.1},
    {"profit_margins": 0.3},
    {"revenue_growth": 0.5}, {"revenue_growth": -0.2},
    {"earnings_growth": 0.4},
    {"fcf": 50.0}, {"fcf": -5.0},
    {"debt_ratio": 0.9}, {"debt_ratio": 0.05},
    {"market_cap": 0.5}, {"market_cap": 3000.0},
    {"institutional_ownership": 90.0}, {"institutional_ownership": 5.0},
    # all at once, in the direction company-value rules reward
    {"pe": 8.0, "pb": 0.8, "roe": 0.3, "gross_margins": 0.6,
     "operating_margins": 0.35, "revenue_growth": 0.3, "fcf": 30.0,
     "debt_ratio": 0.1, "market_cap": 2000.0, "institutional_ownership": 80.0},
]


def _builtin_agents():
    from augur.registry import _BUILTIN_AGENTS
    out = []
    for agent_id, (module_path, class_name) in sorted(_BUILTIN_AGENTS.items()):
        cls = getattr(importlib.import_module(module_path), class_name)
        out.append((agent_id, cls()))
    return out


def _raw_analyze(agent):
    """The persona's own rules, bypassing the fund guard."""
    raw = type(agent).analyze.__wrapped__
    return lambda ctx: raw(agent, ctx)


# ---------------------------------------------------------------- guard ----

@pytest.mark.parametrize("persona", ["buffett", "dan_bin", "dayu", "thiel"])
def test_company_personas_abstain_on_etf(persona):
    agents = dict(_builtin_agents())
    resp = agents[persona].analyze(etf_ctx())
    assert resp.metadata.get("not_applicable") is True
    assert resp.signal == SignalType.NEUTRAL
    assert resp.coverage_confidence == 0
    assert resp.confidence == 0
    assert resp.key_findings == [] and resp.risks == []
    assert "不适用于基金" in resp.reasoning


def test_every_non_applicable_builtin_abstains_and_applicable_runs():
    for agent_id, agent in _builtin_agents():
        resp = agent.analyze(etf_ctx())
        if agent_id in FUND_APPLICABLE_PERSONAS:
            assert not resp.metadata.get("not_applicable"), agent_id
        else:
            assert resp.metadata.get("not_applicable") is True, agent_id


def test_guard_does_not_run_rules_for_funds():
    calls = []

    class Probe(BaseAgent):
        def __init__(self):
            super().__init__("probe", "Probe", "", [], {}, {})

        def analyze(self, context):
            calls.append(context.ticker)
            return AgentResponse("probe", "Probe", SignalType.BULLISH, 0.9, 9.0, "ran")

    probe = Probe()
    assert probe.analyze(etf_ctx()).metadata["not_applicable"] is True
    assert calls == []
    assert probe.analyze(MarketContext(ticker="AAPL")).signal == SignalType.BULLISH
    assert calls == ["AAPL"]


def test_guard_wraps_once_and_survives_inheritance():
    class Parent(BaseAgent):
        def __init__(self, agent_id="parent"):
            super().__init__(agent_id, agent_id, "", [], {}, {})

        def analyze(self, context):
            return AgentResponse(self.agent_id, self.agent_id, SignalType.BULLISH, 0.8, 8.0, "p")

    class Child(Parent):
        def analyze(self, context):
            resp = super().analyze(context)
            resp.reasoning = "child"
            return resp

    class Inherits(Parent):
        pass

    assert Inherits.analyze is Parent.analyze
    assert Child.analyze.__wrapped__.__qualname__.endswith("Child.analyze")
    assert Child().analyze(etf_ctx()).metadata["not_applicable"] is True
    assert Child().analyze(MarketContext(ticker="X")).reasoning == "child"
    # applicable id passes through the guard
    assert Child("dalio").analyze(etf_ctx()).reasoning == "child"


def test_guard_tolerates_agents_without_init_and_odd_contexts():
    class Bare(BaseAgent):
        def __init__(self):  # deliberately skips BaseAgent.__init__
            pass

        def analyze(self, context):
            return AgentResponse("bare", "Bare", SignalType.NEUTRAL, 0.5, 5.0, "ran")

    assert Bare().analyze(etf_ctx()).metadata["not_applicable"] is True
    assert Bare().analyze(None).reasoning == "ran"
    assert Bare().analyze({"asset_type": "etf"}).reasoning == "ran"  # dicts are not contexts


def test_yaml_personas_abstain_on_etf():
    from augur.persona_loader import YamlAgent, load_personas_from_dir

    agents = load_personas_from_dir(_YAML_DIR)
    assert agents, "expected bundled YAML personas"
    assert getattr(YamlAgent.analyze, "_augur_fund_guard", False)
    for agent in agents:
        resp = agent.analyze(etf_ctx())
        assert resp.metadata.get("not_applicable") is True, agent.agent_id
        # equity contexts still run the YAML rules
        assert not agent.analyze(MarketContext(ticker="AAPL", pe=20)).metadata.get("not_applicable")


def test_fund_asset_type_is_case_insensitive():
    assert is_fund(MarketContext(ticker="X", asset_type="ETF"))
    assert is_fund(MarketContext(ticker="X", asset_type="Fund"))
    assert not is_fund(MarketContext(ticker="X", asset_type="equity"))


# ---------------------------------------------------- invariance / lock ----

def _invariant_personas():
    invariant = set()
    for agent_id, agent in _builtin_agents():
        run = _raw_analyze(agent)
        base = run(etf_ctx())
        moved = False
        for change in COMPANY_PERTURBATIONS:
            resp = run(etf_ctx(**change))
            if abs(resp.score - base.score) > 1e-9 or resp.signal != base.signal:
                moved = True
                break
        if not moved:
            invariant.add(agent_id)
    return invariant


def test_fund_applicable_personas_decided_by_score_invariance():
    """A persona applies to funds only if company fields cannot move it."""
    assert _invariant_personas() == set(FUND_APPLICABLE_PERSONAS)


def test_fund_applicable_personas_locked():
    # v14.0 lock. Changing this set needs the invariance test above to agree.
    assert FUND_APPLICABLE_PERSONAS == frozenset({"dalio"})
    assert len(FUND_APPLICABLE_PERSONAS) < MIN_APPLICABLE_FOR_CONSENSUS


# ------------------------------------------------------------ consensus ----

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


def _coordinator():
    from augur.registry import AgentRegistry, DecisionCoordinator
    return DecisionCoordinator(AgentRegistry())


def test_etf_consensus_is_withheld(fake_learning):
    ctx = etf_ctx()
    coord = _coordinator()
    results = coord.analyze_with_all(ctx)
    consensus = coord.get_consensus(results, ticker="SPY", context=ctx)

    meta = consensus.metadata
    assert meta["consensus_withheld"] is True
    assert consensus.signal == SignalType.NEUTRAL
    assert consensus.confidence == 0
    assert meta["applicable_agents"] == ["dalio"]
    assert "buffett" in meta["abstained_agents"]
    assert "dalio" not in meta["abstained_agents"]
    assert meta["position_pct"] == 0
    assert meta["position_sizing"]["position_pct"] == 0
    assert meta["asset_type"] == "etf"
    assert "适用大师 1 位" in consensus.reasoning
    assert fake_learning.recorded == []


def test_withheld_without_context_uses_abstentions(fake_learning):
    from augur.consensus.engine import ConsensusEngine

    ctx = etf_ctx()
    results = {aid: a.analyze(ctx) for aid, a in _builtin_agents()}
    consensus = ConsensusEngine().compute(results, ticker="SPY", context=None)
    assert consensus.metadata["consensus_withheld"] is True
    assert fake_learning.recorded == []


def test_all_personas_abstaining_still_withholds(fake_learning):
    from augur.consensus.engine import ConsensusEngine

    ctx = etf_ctx()
    agents = dict(_builtin_agents())
    results = {aid: agents[aid].analyze(ctx) for aid in ("buffett", "graham")}
    consensus = ConsensusEngine().compute(results, ticker="SPY", context=ctx)
    assert consensus.metadata["consensus_withheld"] is True
    assert consensus.metadata["applicable_agents"] == []


def test_fund_with_enough_applicable_personas_has_no_position_or_record(fake_learning):
    """If >= 3 personas ever apply to funds, consensus runs on them only,
    still without a position or a learning record."""
    from augur.consensus.engine import ConsensusEngine

    def resp(aid, sig=SignalType.BULLISH, score=9.0):
        return AgentResponse(aid, aid, sig, 0.9, score, "r")

    results = {"a": resp("a"), "b": resp("b"), "c": resp("c"),
               "buffett": dict(_builtin_agents())["buffett"].analyze(etf_ctx())}
    consensus = ConsensusEngine().compute(results, ticker="SPY", context=etf_ctx())
    assert not consensus.metadata.get("consensus_withheld")
    assert consensus.metadata["position_pct"] == 0
    assert consensus.metadata["abstained_agents"] == ["buffett"]
    assert consensus.metadata["weighting"]["participating_agents"] == 3
    assert fake_learning.recorded == []


def test_equity_low_participation_is_not_withheld(fake_learning):
    """< 3 results on an equity keeps the pre-v14 low_participation path."""
    from augur.consensus.engine import ConsensusEngine

    results = {"x": AgentResponse("x", "x", SignalType.BULLISH, 0.8, 8.0, "r")}
    consensus = ConsensusEngine().compute(results, ticker="AAPL",
                                          context=MarketContext(ticker="AAPL"))
    assert not consensus.metadata.get("consensus_withheld")
    assert consensus.metadata.get("low_participation") is True
    assert len(fake_learning.recorded) == 1


def test_equity_consensus_still_records_predictions(fake_learning):
    ctx = MarketContext(ticker="AAPL", price=210, pe=30, roe=1.4, gross_margins=0.46,
                        market_cap=3200, sector="Technology")
    coord = _coordinator()
    results = coord.analyze_with_all(ctx)
    consensus = coord.get_consensus(results, ticker="AAPL", context=ctx)
    assert not consensus.metadata.get("consensus_withheld")
    assert "abstained_agents" not in consensus.metadata
    assert len(fake_learning.recorded) == len(results)


# ------------------------------------------------------------ checklist ----

def test_assess_etf_clean_profile_has_no_findings():
    assert assess_etf(etf_ctx().etf) == []


def test_assess_etf_flags_each_problem():
    findings = assess_etf({
        "expense_ratio": 0.0075, "aum_usd_bn": 0.03, "premium_pct": -1.6,
        "nav_date_inferred": True, "top10_weight": 0.62, "spread_pct": 0.9,
    })
    text = "\n".join(findings)
    assert len(findings) == 5
    assert "费率偏高" in text and "0.75%" in text
    assert "清盘风险" in text and "$30.0M" in text
    assert "折价偏大" in text and "-1.60%" in text and "推断" in text
    assert "前十大占 62.0%" in text
    assert "买卖价差偏宽" in text


def test_assess_etf_boundaries_and_bad_values():
    assert assess_etf({"expense_ratio": 0.02})[0].startswith("费率很高")
    assert assess_etf({"premium_pct": 1.0}) == []       # strict >
    assert assess_etf({"premium_pct": 1.2})[0].startswith("溢价偏大")
    assert assess_etf({"aum_usd_bn": 0}) == []           # 0 = unknown, not tiny
    assert assess_etf({"top10_weight": 0.5}) == []
    assert assess_etf({"expense_ratio": float("nan"), "spread_pct": "x",
                       "premium_pct": True}) == []
    assert assess_etf(None) == []


def test_unchecked_items_lists_missing_inputs():
    assert unchecked_items({}) == ["费率", "规模", "溢价折价", "持仓集中度", "买卖价差"]
    assert unchecked_items({}, lang="en") == [
        "expense ratio", "AUM", "premium/discount", "concentration", "bid/ask spread"]
    assert unchecked_items(etf_ctx().etf) == []


def test_assess_etf_english():
    findings = assess_etf({
        "expense_ratio": 0.0075, "aum_usd_bn": 0.03, "premium_pct": -1.6,
        "nav_date_inferred": True, "top10_weight": 0.62, "spread_pct": 0.9,
    }, lang="en")
    text = "\n".join(findings)
    assert len(findings) == 5
    assert "High expense ratio: 0.75%" in text and "closure risk" in text
    assert "Large discount: -1.60%" in text and "NAV date inferred" in text
    assert "top 10 holdings are 62.0%" in text and "Wide bid/ask spread" in text
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in text)


def test_etf_overview_lines():
    text = "\n".join(etf_overview_lines(etf_ctx()))
    assert "ETF profile" in text and "ETF health check" in text
    assert "$797.00B" in text and "0.09%" in text and "-0.04%" in text
    assert "36.0%" in text and "inferred" in text
    assert "No issues flagged" in text
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in text)
    sparse = "\n".join(etf_overview_lines(MarketContext(ticker="X", asset_type="etf")))
    assert "  AUM              unknown" in sparse
    assert "Not checked (no data): expense ratio, AUM" in sparse


# ------------------------------------------------------------- engine misc --

def test_neutral_consensus_gets_zero_kelly(fake_learning):
    from augur.consensus.engine import ConsensusEngine

    results = {aid: AgentResponse(aid, aid, SignalType.NEUTRAL, 0.9, 5.5, "r")
               for aid in ("a", "b", "c")}
    consensus = ConsensusEngine().compute(results, ticker="AAPL",
                                          context=MarketContext(ticker="AAPL"))
    assert consensus.signal == SignalType.NEUTRAL
    assert consensus.metadata["position_pct"] == 0.0


@pytest.mark.parametrize("sector,industry,expected", [
    ("Technology", "Consumer Electronics", True),
    ("Information Technology", "", True),
    ("Communication Services", "Internet Content & Information", True),
    ("Communication Services", "", True),
    ("Consumer Cyclical", "Internet Retail", True),
    ("Healthcare", "Biotechnology", False),
    ("Financial Services", "Banks - Diversified", False),
    ("Industrials", "Software - Infrastructure", True),
    ("", "", False),
])
def test_is_tech_sector(sector, industry, expected):
    from augur.consensus.engine import is_tech_sector
    assert is_tech_sector(sector, industry) is expected
