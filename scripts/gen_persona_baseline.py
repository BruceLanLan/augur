#!/usr/bin/env python3
"""Generate the persona baseline snapshot (tests/fixtures/v13_persona_baseline.json).

Runs every builtin persona plus every YAML persona in personas/custom/ on four
fixed hand-built MarketContexts and records signal / scores / findings. The
snapshot pins v13 behaviour so later v14 steps can assert "equity results
unchanged" without network access.

Deterministic: no network, no timestamps, and AUGUR_DATA_DIR points at an
empty temp dir so saved hyperparameter overlays cannot leak in.

Usage:
    .venv/bin/python scripts/gen_persona_baseline.py          # rewrite fixture
    .venv/bin/python scripts/gen_persona_baseline.py --check  # diff only
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "v13_persona_baseline.json"
YAML_DIR = REPO_ROOT / "personas" / "custom"

FLOAT_FIELDS = ("score", "confidence", "coverage_confidence", "risk_adjusted_score")
LIST_FIELDS = ("key_findings", "risks")


def build_contexts() -> Dict[str, Any]:
    """Four fixed contexts. Units follow the yfinance provider (billions USD,
    0-1 decimals for margins/growth, percent for ownership and 52w distance)."""
    from augur.personas.base import MarketContext

    large_cap_us = MarketContext(
        ticker="AAPL", price=210.0, change_pct=0.8, market_cap=3200.0,
        pe=32.0, pb=48.0, ps=8.2, fcf=105.0, revenue=390.0,
        revenue_growth=0.05, earnings_growth=0.08, gross_margins=0.46,
        operating_margins=0.31, roe=1.45, roa=0.28, debt_ratio=0.62,
        current_ratio=0.95, quick_ratio=0.85, institutional_ownership=62.0,
        insider_ownership=0.07, price_vs_52w_high=-6.0, price_vs_52w_low=28.0,
        sector="Technology", industry="Consumer Electronics",
        business_summary="Designs smartphones, personal computers, wearables and services.",
        volume=55e6, rsi=58.0, macd=1.2, macd_signal=0.9, macd_histogram=0.3,
        bb_upper=218.0, bb_middle=206.0, bb_lower=194.0, sma20=206.0,
        sma50=200.0, sma200=190.0, atr=3.6, volatility_20d=0.22,
        volatility_60d=0.24, volatility_252d=0.26, sharpe_ratio=1.1,
        sortino_ratio=1.5, max_drawdown=-0.18, beta_1y=1.2,
        company_name="Apple Inc.", currency="USD", exchange="NMS",
        forward_pe=28.0, peg_ratio=2.4, eps=6.5, forward_eps=7.4,
        profit_margins=0.25, ebitda=130.0, enterprise_value=3250.0,
        total_cash=65.0, total_debt=105.0, dividend_yield=0.005,
        payout_ratio=0.15, target_mean_price=235.0, recommendation_key="buy",
        num_analyst_opinions=40,
    )
    small_cap_growth = MarketContext(
        ticker="SMLG", price=24.0, change_pct=3.5, market_cap=1.8,
        pe=0.0, pb=6.5, ps=9.0, fcf=-0.05, revenue=0.2,
        revenue_growth=0.65, earnings_growth=0.0, gross_margins=0.72,
        operating_margins=-0.15, roe=-0.08, roa=-0.04, debt_ratio=0.2,
        current_ratio=3.2, quick_ratio=3.0, institutional_ownership=45.0,
        insider_ownership=18.0, price_vs_52w_high=-35.0, price_vs_52w_low=80.0,
        sector="Technology", industry="Software - Application",
        business_summary="Cloud software platform using AI for enterprise workflow automation.",
        volume=2.5e6, rsi=67.0, macd=0.6, macd_signal=0.4, macd_histogram=0.2,
        sma20=22.0, sma50=20.0, sma200=18.0, atr=1.4, volatility_20d=0.65,
        volatility_60d=0.6, volatility_252d=0.7, max_drawdown=-0.45,
        beta_1y=1.8, short_interest=0.12, company_name="Small Growth Co.",
        currency="USD", exchange="NMS", forward_pe=0.0, total_cash=0.4,
        total_debt=0.05,
    )
    hk_stock = MarketContext(
        ticker="0700.HK", price=380.0, change_pct=-1.2, market_cap=3500.0,
        pe=18.0, pb=3.6, ps=5.5, fcf=160.0, revenue=640.0,
        revenue_growth=0.08, earnings_growth=0.15, gross_margins=0.52,
        operating_margins=0.32, roe=0.21, roa=0.11, debt_ratio=0.3,
        current_ratio=1.3, quick_ratio=1.2, institutional_ownership=30.0,
        insider_ownership=28.0, price_vs_52w_high=-10.0, price_vs_52w_low=35.0,
        sector="Communication Services", industry="Internet Content & Information",
        business_summary="Internet services: social networking, games, fintech and cloud.",
        volume=18e6, rsi=45.0, macd=-1.5, macd_signal=-0.8, macd_histogram=-0.7,
        sma20=385.0, sma50=390.0, sma200=360.0, atr=9.0, volatility_20d=0.3,
        volatility_252d=0.35, beta_1y=0.9, southbound_hold_pct=9.5,
        company_name="Tencent Holdings Ltd", currency="HKD", exchange="HKG",
        forward_pe=15.0, eps=21.0, profit_margins=0.3, dividend_yield=0.009,
    )
    empty = MarketContext(ticker="EMPTY")
    return {
        "large_cap_us": large_cap_us,
        "small_cap_growth": small_cap_growth,
        "hk_stock": hk_stock,
        "empty": empty,
    }


def build_agents() -> List[Tuple[str, Any]]:
    """All builtin personas (ignores enabled_personas) plus every YAML persona.

    YAML personas are keyed ``yaml:<agent_id>`` because the registry never
    lets them shadow a builtin with the same id."""
    import importlib

    from augur.persona_loader import load_personas_from_dir
    from augur.registry import _BUILTIN_AGENTS

    agents: List[Tuple[str, Any]] = []
    for agent_id, (module_path, class_name) in sorted(_BUILTIN_AGENTS.items()):
        cls = getattr(importlib.import_module(module_path), class_name)
        agents.append((agent_id, cls()))
    for agent in sorted(load_personas_from_dir(YAML_DIR), key=lambda a: a.agent_id):
        agents.append((f"yaml:{agent.agent_id}", agent))
    return agents


def _snapshot(resp: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"signal": resp.signal.value}
    for name in FLOAT_FIELDS:
        out[name] = round(float(getattr(resp, name)), 6)
    for name in LIST_FIELDS:
        out[name] = [str(x) for x in getattr(resp, name)]
    return out


def generate() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Return {context_name: {persona_key: snapshot}}."""
    contexts = build_contexts()
    agents = build_agents()
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for ctx_name, ctx in contexts.items():
        result[ctx_name] = {key: _snapshot(agent.analyze(ctx)) for key, agent in agents}
    return result


def main(argv: List[str]) -> int:
    os.environ.setdefault("AUGUR_DATA_DIR", tempfile.mkdtemp(prefix="augur_baseline_"))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    data = generate()
    text = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if "--check" in argv:
        same = FIXTURE_PATH.exists() and FIXTURE_PATH.read_text(encoding="utf-8") == text
        print("baseline matches" if same else "baseline DIFFERS")
        return 0 if same else 1
    FIXTURE_PATH.write_text(text, encoding="utf-8")
    n = sum(len(v) for v in data.values())
    print(f"wrote {FIXTURE_PATH.relative_to(REPO_ROOT)} ({n} persona runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
