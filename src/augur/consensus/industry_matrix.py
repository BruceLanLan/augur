# -*- coding: utf-8 -*-
"""Industry-aware agent weight matrix."""

from typing import Any, Dict, Optional, Tuple

# Base boosts by GICS-like sector keyword → agent_id multipliers
_SECTOR_WEIGHTS: Dict[str, Dict[str, float]] = {
    "technology": {
        "cathie_wood": 1.45, "aschenbrenner": 1.35, "thiel": 1.25, "lynch": 1.15,
        "arps": 1.1, "buffett": 0.88, "graham": 0.82,
    },
    "financial": {
        "buffett": 1.35, "graham": 1.3, "marks": 1.25, "munger": 1.15, "lynch": 1.05,
        "cathie_wood": 0.82, "aschenbrenner": 0.85,
    },
    "healthcare": {
        "fisher": 1.35, "lynch": 1.2, "buffett": 1.08, "munger": 1.05,
        "cathie_wood": 0.9, "aschenbrenner": 0.88,
    },
    "consumer": {
        "buffett": 1.25, "munger": 1.2, "lynch": 1.25, "duan_yongping": 1.15,
        "fisher": 1.05,
    },
    "energy": {
        "dalio": 1.25, "soros": 1.2, "marks": 1.15, "buffett": 1.05,
    },
    "industrials": {
        "buffett": 1.15, "munger": 1.12, "lynch": 1.1, "marks": 1.08, "fisher": 1.05,
    },
    "materials": {
        "dalio": 1.15, "marks": 1.12, "soros": 1.1, "buffett": 1.05,
    },
    "utilities": {
        "graham": 1.2, "buffett": 1.15, "marks": 1.1, "munger": 1.05,
    },
    "real_estate": {
        "graham": 1.2, "buffett": 1.15, "marks": 1.12, "munger": 1.08,
    },
    "communication": {
        "lynch": 1.15, "buffett": 1.1, "thiel": 1.08, "munger": 1.05,
    },
    "china": {
        "duan_yongping": 1.45, "zhang_lei": 1.35, "li_lu": 1.3, "dan_bin": 1.22,
        "dayu": 1.18, "munger": 1.05,
    },
}

_CHINA_TICKER_SUFFIXES = (".HK", ".SS", ".SZ", ".SH")


def classify_industry(
    sector: str = "",
    industry: str = "",
    ticker: str = "",
) -> Tuple[str, str]:
    """Map sector/industry/ticker strings to an internal industry key and label."""
    sector_l = (sector or "").lower()
    industry_l = (industry or "").lower()
    ticker_u = (ticker or "").upper()

    if any(ticker_u.endswith(s) for s in _CHINA_TICKER_SUFFIXES):
        return "china", sector or "China"
    if "china" in sector_l or "hong kong" in sector_l:
        return "china", sector or "China"

    if (
        "tech" in sector_l
        or "information technology" in sector_l
        or any(k in industry_l for k in ("software", "semiconductor", "cloud", "internet"))
        or any(
            k in industry_l
            for k in ("artificial intelligence", "machine learning", "data processing")
        )
    ):
        return "technology", sector or "Technology"

    if "financ" in sector_l or any(k in industry_l for k in ("bank", "insurance", "capital markets")):
        return "financial", sector or "Financials"

    if (
        "health" in sector_l
        or any(k in industry_l for k in ("pharma", "biotech", "medical", "drug", "life sciences"))
    ):
        return "healthcare", sector or "Healthcare"

    if "consumer" in sector_l or any(k in industry_l for k in ("retail", "restaurant", "apparel")):
        return "consumer", sector or "Consumer"

    if "energy" in sector_l or any(k in industry_l for k in ("oil", "gas", "renewable")):
        return "energy", sector or "Energy"

    if "industrial" in sector_l or "machinery" in industry_l or "aerospace" in industry_l:
        return "industrials", sector or "Industrials"

    if "material" in sector_l or "mining" in industry_l or "chemical" in industry_l:
        return "materials", sector or "Materials"

    if "utilit" in sector_l or "electric" in industry_l:
        return "utilities", sector or "Utilities"

    if "real estate" in sector_l or "reit" in industry_l:
        return "real_estate", sector or "Real Estate"

    if "communication" in sector_l or "media" in industry_l or "telecom" in industry_l:
        return "communication", sector or "Communication Services"

    return "general", sector or "General"


def detect_industry(
    ticker: str,
    context: Any = None,
) -> Tuple[str, str]:
    """Detect sector/industry from context or market data."""
    if context is not None:
        sector = getattr(context, "sector", "") or ""
        industry = getattr(context, "industry", "") or ""
        if sector or industry:
            return classify_industry(sector, industry, ticker)

    try:
        from augur.data import fetch_market_context

        ctx = fetch_market_context(ticker)
        return classify_industry(ctx.sector or "", ctx.industry or "", ticker)
    except Exception:
        return classify_industry("", "", ticker)


def get_agent_weights(industry: str, trained: Optional[Dict] = None) -> Dict[str, float]:
    """Return normalized agent_id → weight for the given industry key."""
    trained = trained or {}
    if industry in trained and isinstance(trained[industry], dict):
        raw = {
            str(k): float(v)
            for k, v in trained[industry].items()
            if isinstance(v, (int, float)) and float(v) > 0
        }
        if raw:
            total = sum(raw.values())
            if total > 0:
                return {k: v / total for k, v in raw.items()}
            return raw

    base = _SECTOR_WEIGHTS.get(industry, {})
    if not base:
        return {}
    total = sum(base.values())
    if total <= 0:
        return base
    return {k: v / total for k, v in base.items()}
