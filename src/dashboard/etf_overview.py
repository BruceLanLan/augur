# -*- coding: utf-8 -*-
"""ETF overview card payload for the stock page.

Picks the card fields out of ``MarketContext.etf`` (keys documented in
``augur.etf``) and passes them through unformatted; the page formats them
(``static/js/etf-card.js``). Equities get ``None`` so the page renders no card.
"""

from typing import Any, Dict, Optional

from augur.etf import is_fund

_NUMERIC = ("aum_usd_bn", "expense_ratio", "premium_pct", "nav", "top10_weight", "spread_pct")
_TEXT = ("category", "nav_date", "source")


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def build_etf_overview(ctx: Any) -> Optional[Dict[str, Any]]:
    """Card payload for a fund context, ``None`` for anything else.

    Missing keys stay ``None`` (unknown), never 0.
    """
    if not is_fund(ctx):
        return None
    profile = getattr(ctx, "etf", None) or {}
    out: Dict[str, Any] = {"asset_type": str(getattr(ctx, "asset_type", "") or "").lower()}
    for k in _NUMERIC:
        out[k] = _num(profile.get(k))
    for k in _TEXT:
        v = profile.get(k)
        out[k] = str(v) if v not in (None, "") else None
    out["nav_date_inferred"] = bool(profile.get("nav_date_inferred", False))
    return out
