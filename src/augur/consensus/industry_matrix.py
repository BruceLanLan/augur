# -*- coding: utf-8 -*-
"""Industry-aware agent weight matrix."""

from typing import Dict, Tuple

# Base boosts by GICS-like sector keyword → agent_id multipliers
_SECTOR_WEIGHTS: Dict[str, Dict[str, float]] = {
    "technology": {
        "cathie_wood": 1.4, "aschenbrenner": 1.3, "thiel": 1.2, "lynch": 1.1,
        "buffett": 0.9, "graham": 0.85,
    },
    "financial": {
        "buffett": 1.3, "graham": 1.25, "marks": 1.2, "munger": 1.1,
        "cathie_wood": 0.85,
    },
    "healthcare": {
        "fisher": 1.3, "lynch": 1.15, "buffett": 1.05,
    },
    "consumer": {
        "buffett": 1.2, "munger": 1.15, "lynch": 1.2, "duan_yongping": 1.1,
    },
    "energy": {
        "dalio": 1.2, "soros": 1.15, "marks": 1.1,
    },
    "china": {
        "duan_yongping": 1.4, "zhang_lei": 1.3, "li_lu": 1.25, "dan_bin": 1.2, "dayu": 1.15,
    },
}


def detect_industry(ticker: str) -> Tuple[str, str]:
    """Detect sector/industry from yfinance. Returns (industry_key, raw_sector)."""
    try:
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
        sector = (ctx.sector or "").lower()
        industry = (ctx.industry or "").lower()
        if any(k in ticker.upper() for k in (".HK", ".SS", ".SZ")) or "china" in sector:
            return "china", ctx.sector or "China"
        if "tech" in sector or "software" in industry or "semiconductor" in industry:
            return "technology", ctx.sector or "Technology"
        if "financ" in sector or "bank" in industry:
            return "financial", ctx.sector or "Financials"
        if "health" in sector or "pharma" in industry or "biotech" in industry:
            return "healthcare", ctx.sector or "Healthcare"
        if "consumer" in sector or "retail" in industry:
            return "consumer", ctx.sector or "Consumer"
        if "energy" in sector or "oil" in industry:
            return "energy", ctx.sector or "Energy"
        return "general", ctx.sector or "General"
    except Exception:
        return "general", "Unknown"


def get_agent_weights(industry: str, trained: Dict = None) -> Dict[str, float]:
    """Return agent_id → weight for the given industry key."""
    trained = trained or {}
    if industry in trained:
        return dict(trained[industry])
    base = _SECTOR_WEIGHTS.get(industry, {})
    if not base:
        return {}
    total = sum(base.values())
    if total <= 0:
        return base
    return {k: v / total for k, v in base.items()}
