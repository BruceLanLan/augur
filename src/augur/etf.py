"""
ETF / fund contract
===================
Shared contract for fund-native analysis (v14). This module only defines the
shape of the data; data population lives in the datasources layer and the
persona abstention guard lives in ``augur.personas.base``.

``MarketContext.etf`` profile keys (all optional; missing = unknown):

    aum_usd_bn         float  total net assets, billions of USD
    expense_ratio      float  net expense ratio, 0-1 decimal (0.0009 = 0.09%)
    yield              float  distribution yield, 0-1 decimal
    category           str    fund category, e.g. "Large Blend"
    nav                float  net asset value per share, trading currency
    nav_date           str    ISO date the NAV refers to
    nav_date_inferred  bool   True when nav_date was guessed (previous session)
    premium_pct        float  (close on nav_date / nav - 1) * 100
    top10_weight       float  combined weight of top-10 holdings, 0-1 decimal
    hhi                float  Herfindahl index of holding weights, 0-1
    sector_weights     dict   sector -> weight (0-1 decimal)
    asset_classes      dict   asset class -> weight (0-1 decimal)
    turnover           float  annual portfolio turnover, 0-1 decimal
    spread_pct         float  bid/ask spread as percent of mid
    dollar_volume      float  average daily dollar volume, USD
    portfolio_pe       float  look-through P/E of holdings
    portfolio_pb       float  look-through P/B of holdings
    source             str    where the profile came from, e.g. "yfinance"

For funds, company valuation fields (``ctx.pe`` / ``ctx.pb``) stay 0 and the
look-through ratios go to ``portfolio_pe`` / ``portfolio_pb`` instead.
"""

import math
from typing import Any, Dict, List, Optional

ETF_PROFILE_KEYS = (
    "aum_usd_bn", "expense_ratio", "yield", "category", "nav", "nav_date",
    "nav_date_inferred", "premium_pct", "top10_weight", "hhi",
    "sector_weights", "asset_classes", "turnover", "spread_pct",
    "dollar_volume", "portfolio_pe", "portfolio_pb", "source",
)

FUND_ASSET_TYPES = frozenset({"etf", "fund"})

# Personas whose rules stay meaningful on a fund. Decided by the
# score-invariance test (tests/test_etf_consensus.py): on an ETF context, a
# persona is applicable only if perturbing company fields (pe, pb, roe,
# margins, revenue growth, fcf, debt ratio, market cap, institutional
# ownership) leaves its score and signal unchanged. v14.0: only dalio passed.
# v14.1: marks, soros and arps gained fund paths (``analyze_fund``) that read
# only technical / market / ETF-profile fields, and pass the same test.
FUND_APPLICABLE_PERSONAS: frozenset = frozenset({"dalio", "marks", "soros", "arps"})

# Below this many applicable personas a fund gets no consensus signal.
MIN_APPLICABLE_FOR_CONSENSUS = 3

# Fixed signal cut-offs for the personas' fund paths (``analyze_fund``). They
# are deliberately separate from each persona's ``thresholds``, which are
# tuned on equities and can be overlaid by saved hyper-parameters.
FUND_BULLISH_CUTOFF = 6.5
FUND_BEARISH_CUTOFF = 4.0

# What a fund reading may look at: technicals, market/macro state and the
# ETF profile. Never company fields (pe, pb, roe, margins, growth, fcf, debt,
# market_cap, institutional ownership).
FUND_READING_BASIS = "technical + market + ETF profile fields only (no company fundamentals)"

# ---- ETF health-check thresholds (assess_etf) ----
EXPENSE_RATIO_HIGH = 0.005       # 0.50%
EXPENSE_RATIO_VERY_HIGH = 0.01   # 1.00%
AUM_CLOSURE_RISK_USD_BN = 0.05   # $50M
PREMIUM_ABS_MAX_PCT = 1.0        # |premium| > 1%
TOP10_CONCENTRATION = 0.5        # top-10 holdings > 50%
SPREAD_WIDE_PCT = 0.5            # bid/ask spread > 0.5% of mid


def is_fund(ctx: Any) -> bool:
    """True when the context describes an ETF or other fund."""
    return str(getattr(ctx, "asset_type", "") or "").lower() in FUND_ASSET_TYPES


def _num(profile: Dict[str, Any], key: str) -> Optional[float]:
    """Finite float value of ``profile[key]`` or None when missing/invalid."""
    value = (profile or {}).get(key)
    if isinstance(value, bool) or value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def profile_num(ctx: Any, key: str) -> Optional[float]:
    """Finite numeric ETF-profile value of a context, or None when unknown."""
    return _num(dict(getattr(ctx, "etf", None) or {}), key)


def fund_signal(score: float) -> str:
    """Signal value for a fund-path score on the fixed fund cut-offs."""
    if score >= FUND_BULLISH_CUTOFF:
        return "bullish"
    if score <= FUND_BEARISH_CUTOFF:
        return "bearish"
    return "neutral"


def assess_etf(profile: Dict[str, Any], lang: str = "zh") -> List[str]:
    """Deterministic ETF health checklist; returns findings, never a score.

    Only problems are reported. A check whose input is missing is skipped
    (see :func:`unchecked_items`), so an empty list means "nothing flagged",
    not "everything verified".

    ``lang="zh"`` (default) is the wording used by the Chinese report and the
    engine metadata; ``lang="en"`` is used by the English CLI / MCP text.
    """
    profile = profile or {}
    en = lang == "en"
    findings: List[str] = []

    er = _num(profile, "expense_ratio")
    if er is not None:
        if er > EXPENSE_RATIO_VERY_HIGH:
            findings.append(
                f"Very high expense ratio: {er * 100:.2f}% (> {EXPENSE_RATIO_VERY_HIGH * 100:.2f}%)" if en
                else f"费率很高：{er * 100:.2f}%（> {EXPENSE_RATIO_VERY_HIGH * 100:.2f}%）")
        elif er > EXPENSE_RATIO_HIGH:
            findings.append(
                f"High expense ratio: {er * 100:.2f}% (> {EXPENSE_RATIO_HIGH * 100:.2f}%)" if en
                else f"费率偏高：{er * 100:.2f}%（> {EXPENSE_RATIO_HIGH * 100:.2f}%）")

    aum = _num(profile, "aum_usd_bn")
    if aum is not None and 0 < aum < AUM_CLOSURE_RISK_USD_BN:
        findings.append(
            f"Small fund: ${aum * 1000:.1f}M (< $50M), closure risk" if en
            else f"规模过小：${aum * 1000:.1f}M（< $50M），有清盘风险")

    prem = _num(profile, "premium_pct")
    if prem is not None and abs(prem) > PREMIUM_ABS_MAX_PCT:
        if en:
            kind = "Large premium" if prem > 0 else "Large discount"
            note = " (NAV date inferred)" if profile.get("nav_date_inferred") else ""
            findings.append(f"{kind}: {prem:+.2f}% (|premium| > {PREMIUM_ABS_MAX_PCT:.0f}%){note}")
        else:
            kind = "溢价" if prem > 0 else "折价"
            note = "（净值日期为推断）" if profile.get("nav_date_inferred") else ""
            findings.append(f"{kind}偏大：{prem:+.2f}%（|溢价| > {PREMIUM_ABS_MAX_PCT:.0f}%）{note}")

    top10 = _num(profile, "top10_weight")
    if top10 is not None and top10 > TOP10_CONCENTRATION:
        findings.append(
            f"Concentrated: top 10 holdings are {top10 * 100:.1f}% (> {TOP10_CONCENTRATION * 100:.0f}%)" if en
            else f"持仓集中：前十大占 {top10 * 100:.1f}%（> {TOP10_CONCENTRATION * 100:.0f}%）")

    spread = _num(profile, "spread_pct")
    if spread is not None and spread > SPREAD_WIDE_PCT:
        findings.append(
            f"Wide bid/ask spread: {spread:.2f}% (> {SPREAD_WIDE_PCT:.1f}%)" if en
            else f"买卖价差偏宽：{spread:.2f}%（> {SPREAD_WIDE_PCT:.1f}%）")

    return findings


_CHECK_INPUTS = (
    ("expense_ratio", "费率", "expense ratio"),
    ("aum_usd_bn", "规模", "AUM"),
    ("premium_pct", "溢价折价", "premium/discount"),
    ("top10_weight", "持仓集中度", "concentration"),
    ("spread_pct", "买卖价差", "bid/ask spread"),
)


def unchecked_items(profile: Dict[str, Any], lang: str = "zh") -> List[str]:
    """Labels of health checks skipped because their input is missing."""
    idx = 2 if lang == "en" else 1
    return [item[idx] for item in _CHECK_INPUTS if _num(profile or {}, item[0]) is None]


def etf_overview_lines(ctx: Any) -> List[str]:
    """Plain-text "ETF profile + health check" block for the CLI and MCP text.

    English, like the rest of the CLI frame (Ticker / Price / RSI ...); the
    Chinese Markdown report has its own table in ``augur.report``. Values sit
    in the same column as the 18-wide labels of ``augur fetch``.
    """
    p = dict(getattr(ctx, "etf", None) or {})
    ccy = str(getattr(ctx, "currency", "") or "").upper()
    unknown = "unknown"
    lines: List[str] = ["ETF profile"]

    def row(label: str, value: str) -> None:
        lines.append(f"  {label:<17s}{value}")

    name = getattr(ctx, "company_name", "") or ""
    if name:
        row("Name", name)
    if p.get("category"):
        row("Category", str(p["category"]))
    aum = _num(p, "aum_usd_bn")
    row("AUM", f"${aum:,.2f}B" if aum is not None else unknown)
    er = _num(p, "expense_ratio")
    row("Expense ratio", f"{er * 100:.2f}%" if er is not None else unknown)
    yld = _num(p, "yield")
    if yld is not None:
        row("Yield", f"{yld * 100:.2f}%")
    nav = _num(p, "nav")
    if nav is not None:
        date = p.get("nav_date") or "date unknown"
        if p.get("nav_date_inferred"):
            date = f"{date}, inferred"
        row("NAV", f"{nav:,.4f} {ccy}".rstrip() + f" ({date})")
    prem = _num(p, "premium_pct")
    row("Premium/discount", f"{prem:+.2f}%" if prem is not None else unknown)
    top10 = _num(p, "top10_weight")
    row("Top-10 weight", f"{top10 * 100:.1f}%" if top10 is not None else unknown)
    spread = _num(p, "spread_pct")
    if spread is not None:
        row("Bid/ask spread", f"{spread:.3f}%")
    ppe = _num(p, "portfolio_pe")
    if ppe:
        row("Holdings P/E", f"{ppe:.1f}")

    lines.append("ETF health check")
    findings = assess_etf(p, lang="en")
    if findings:
        lines.extend(f"  ! {f}" for f in findings)
    else:
        lines.append("  No issues flagged")
    missing = unchecked_items(p, lang="en")
    if missing:
        lines.append(f"  Not checked (no data): {', '.join(missing)}")
    return lines
