# -*- coding: utf-8 -*-
"""Persona baseline snapshot: equity results must match v13 behaviour.

The fixture tests/fixtures/v13_persona_baseline.json is produced by
scripts/gen_persona_baseline.py. Later v14 steps that intentionally change a
persona output declare it in ``ALLOWED_DIFFS`` instead of regenerating the
fixture, so every deviation from v13 stays explicit and reviewable.
"""

import fnmatch
import importlib.util
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set

from augur.personas.base import MarketContext

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _ROOT / "scripts" / "gen_persona_baseline.py"
_FIXTURE_PATH = _ROOT / "tests" / "fixtures" / "v13_persona_baseline.json"

_spec = importlib.util.spec_from_file_location("gen_persona_baseline", _SCRIPT_PATH)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

# Expected deviations from the v13 baseline.
# Key: "<context>/<persona>" glob (e.g. "*/dayu", "small_cap_growth/*").
# Value: snapshot fields allowed to differ
#   (signal, score, confidence, coverage_confidence, risk_adjusted_score,
#    key_findings, risks).
# Step 0: empty -- everything must match exactly.
ALLOWED_DIFFS: Dict[str, Set[str]] = {
    # Step 5: dayu compared volatility_20d (a fraction, 0.30) against percent
    # thresholds (25/40/60), so every stock got the "<15% low vol" +1. Now
    # converted to percent: 0.22 -> 0 adj, 0.30 -> -1, 0.65 -> -3 plus the
    # ">40%" risk line. "empty" (vol 0) is unchanged and deliberately not listed.
    "large_cap_us/dayu": {"score"},
    "hk_stock/dayu": {"score", "confidence"},
    "small_cap_growth/dayu": {"score", "key_findings", "risks"},
    # Step 5: same unit fix in personas/custom/da-yu.yaml risk_capital rules
    # (20-40% -> +1, >40% -> -2). large_cap_us crosses neutral -> bullish.
    "large_cap_us/yaml:dayu": {"score", "confidence", "signal"},
    # + loader list literals: da-yu.yaml "sector in [...]" rules now evaluate
    # (real names "Technology"/"Communication Services"); hk crosses to bullish.
    "hk_stock/yaml:dayu": {"score", "confidence", "signal"},
    "small_cap_growth/yaml:dayu": {"score"},
    # Step 5: Thiel counts Communication Services / internet as tech, so the
    # "非科技行业" risk no longer fires for Tencent.
    "hk_stock/thiel": {"risks"},
    # Loader list literals: thiel.yaml "sector in ['Technology']" rules
    # (monopoly_power, founder_quality) were always blocked; now +1 each.
    "large_cap_us/yaml:thiel": {"score", "confidence"},
    "small_cap_growth/yaml:thiel": {"score"},
    # v14.1 ATR recalibration: atr is now a true-range Wilder ATR (~1.86x the
    # old close-to-close proxy), so dalio's ATR% bands moved <2/>5 -> <3.75/
    # >9.25 (docs/research/ATR_RECALIBRATION_2026-11.md). The fixture's
    # hand-set atr values sit on the old scale: hk_stock 2.4% now counts as
    # low vol (+3 risk_adjusted), small_cap_growth 5.8% no longer counts as
    # high vol (-3 gone) and crosses neutral -> bullish. munger's >3 -> >5.75
    # move changes no fixture context (1.7% / 2.4% / 5.8% stay on the same side).
    "hk_stock/dalio": {"score"},
    "small_cap_growth/dalio": {"score", "signal"},
}


def allowed_fields(ctx_name: str, persona: str,
                   allow: Dict[str, Set[str]]) -> Set[str]:
    key = f"{ctx_name}/{persona}"
    out: Set[str] = set()
    for pattern, fields in allow.items():
        if fnmatch.fnmatchcase(key, pattern):
            out |= set(fields)
    return out


def diff_against_baseline(actual: Dict, baseline: Dict,
                          allow: Dict[str, Set[str]] = None) -> List[str]:
    """Return human-readable mismatches not covered by ``allow``."""
    allow = allow or {}
    problems: List[str] = []
    for ctx_name in sorted(set(baseline) | set(actual)):
        exp_ctx, act_ctx = baseline.get(ctx_name), actual.get(ctx_name)
        if exp_ctx is None or act_ctx is None:
            problems.append(f"context {ctx_name}: present only in "
                            f"{'actual' if exp_ctx is None else 'baseline'}")
            continue
        for persona in sorted(set(exp_ctx) | set(act_ctx)):
            exp, act = exp_ctx.get(persona), act_ctx.get(persona)
            if exp is None or act is None:
                problems.append(f"{ctx_name}/{persona}: present only in "
                                f"{'actual' if exp is None else 'baseline'}")
                continue
            skip = allowed_fields(ctx_name, persona, allow)
            for name in sorted(set(exp) | set(act)):
                if name in skip or exp.get(name) == act.get(name):
                    continue
                problems.append(f"{ctx_name}/{persona}.{name}: "
                                f"baseline={exp.get(name)!r} actual={act.get(name)!r}")
    return problems


def _format(problems: Iterable[str]) -> str:
    return "\n".join(problems)


def test_personas_match_v13_baseline():
    baseline = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    actual = gen.generate()
    problems = diff_against_baseline(actual, baseline, ALLOWED_DIFFS)
    assert not problems, "persona output drifted from v13 baseline:\n" + _format(problems)


def test_baseline_covers_all_personas_and_contexts():
    baseline = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert set(baseline) == {"large_cap_us", "small_cap_growth", "hk_stock", "empty"}
    keys = {k for k, _ in gen.build_agents()}
    assert len([k for k in keys if not k.startswith("yaml:")]) == 18
    for ctx_name, per in baseline.items():
        assert set(per) == keys, ctx_name


def test_allowlist_helper_masks_only_declared_fields():
    base = {"c": {"p": {"signal": "bullish", "score": 7.0}}}
    act = {"c": {"p": {"signal": "neutral", "score": 6.0}}}
    assert len(diff_against_baseline(act, base)) == 2
    assert diff_against_baseline(act, base, {"c/*": {"score"}}) == [
        "c/p.signal: baseline='bullish' actual='neutral'"
    ]
    assert diff_against_baseline(act, base, {"*/p": {"score", "signal"}}) == []


def test_market_context_v14_fields_default():
    d = MarketContext(ticker="X").to_dict()
    assert d["asset_type"] == "equity"
    assert d["etf"] == {}
    assert d["financial_currency"] == ""
    assert d["fx_rate_usd"] == 0.0
    assert MarketContext(ticker="X").etf is not MarketContext(ticker="Y").etf


def test_etf_contract():
    from augur.etf import ETF_PROFILE_KEYS, FUND_APPLICABLE_PERSONAS, assess_etf, is_fund

    assert not is_fund(MarketContext(ticker="AAPL"))
    assert is_fund(MarketContext(ticker="SPY", asset_type="etf"))
    assert is_fund(MarketContext(ticker="X", asset_type="fund"))
    assert "dalio" in FUND_APPLICABLE_PERSONAS
    assert {"aum_usd_bn", "premium_pct", "portfolio_pe", "source"} <= set(ETF_PROFILE_KEYS)
    assert assess_etf({}) == []
