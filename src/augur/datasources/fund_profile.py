# -*- coding: utf-8 -*-
"""
augur.datasources.fund_profile - ETF / fund detection and profile building (v14)

Fills ``MarketContext.etf`` with the keys defined in ``augur.etf``. Kept apart
from the yfinance provider so the A-share suffix rule can also be applied to
contexts built by other providers (stooq etc.).

Detection
---------
* yfinance ``quoteType`` ``ETF`` / ``MUTUALFUND`` -> ``"etf"``.
* yfinance reports A-share ETFs as ``EQUITY``, so a suffix + prefix fallback
  applies: ``.SS`` codes starting 51 / 56 / 58, ``.SZ`` codes starting 15.
  The suffix is required; a bare ``510300`` is not classified.

Premium / discount
------------------
yfinance's ``navPrice`` is the previous session's NAV and comes without a
date. Comparing it with today's price mixes two days (SPY: -0.25% raw vs
-0.04% aligned), so the premium uses the close of the bar *before* the
latest bar, ``nav_date`` is that bar's date and ``nav_date_inferred=True``.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from augur.datasources.base import safe_num

logger = logging.getLogger(__name__)

FUND_QUOTE_TYPES = frozenset({"ETF", "MUTUALFUND"})

_CN_ETF_RE = re.compile(r"^(?:(5[168]\d{4})\.SS|(15\d{4})\.SZ)$")


def cn_etf_code(ticker: str) -> str:
    """Six-digit fund code for an A-share ETF ticker, else ``""``."""
    m = _CN_ETF_RE.match((ticker or "").strip().upper())
    if not m:
        return ""
    return m.group(1) or m.group(2)


def asset_type_for(ticker: str, quote_type: str = "") -> str:
    """``"etf"`` for funds (quoteType or A-share code rule), else ``"equity"``."""
    if str(quote_type or "").upper() in FUND_QUOTE_TYPES:
        return "etf"
    if cn_etf_code(ticker):
        return "etf"
    return "equity"


def _date_str(value: Any) -> str:
    try:
        return value.strftime("%Y-%m-%d")
    except Exception:
        text = str(value or "")
        return text[:10]


def premium_on_nav_date(nav: float, dated_closes: Sequence[Tuple[str, float]],
                        nav_date: str = "") -> Dict[str, Any]:
    """Premium of the close on the NAV's date over the NAV.

    With ``nav_date`` given, the close of that date is used (no inference).
    Without it, the NAV is assumed to belong to the bar before the latest one.
    Returns ``{}`` when it cannot be computed.
    """
    if nav <= 0 or not dated_closes:
        return {}
    if nav_date:
        close = next((c for d, c in dated_closes if d == nav_date), 0.0)
        if close <= 0:
            return {"nav_date": nav_date, "nav_date_inferred": False}
        return {"nav_date": nav_date, "nav_date_inferred": False,
                "premium_pct": (close / nav - 1.0) * 100.0}
    if len(dated_closes) < 2:
        return {}
    d, close = dated_closes[-2]
    if close <= 0:
        return {}
    return {"nav_date": d, "nav_date_inferred": True,
            "premium_pct": (close / nav - 1.0) * 100.0}


def _safe_attr(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name)
    except Exception as exc:  # yfinance raises YFDataException for unsupported funds
        logger.debug("funds_data.%s unavailable: %s", name, exc)
        return None


def _frame_value(df: Any, row: str, col: str) -> float:
    try:
        if df is None or getattr(df, "empty", True):
            return 0.0
        if col in df.columns:
            return safe_num(df.loc[row, col])
        return safe_num(df.loc[row].iloc[0])
    except Exception:
        return 0.0


def _clean_weights(raw: Any) -> Dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k, v in raw.items():
        w = safe_num(v)
        if w > 0:
            out[str(k)] = w
    return out


def _holding_weights(top: Any) -> List[float]:
    try:
        if top is None or getattr(top, "empty", True):
            return []
        col = "Holding Percent" if "Holding Percent" in top.columns else top.columns[-1]
        weights = [safe_num(w) for w in top[col].tolist()]
    except Exception:
        return []
    return [w for w in weights if w > 0]


def build_etf_profile(
    ticker: str,
    info: Dict[str, Any],
    funds_data: Any,
    dated_closes: Sequence[Tuple[str, float]],
    *,
    price: float,
    avg_volume: float,
    cap_rate: Optional[float],
    price_rate: Optional[float],
) -> Dict[str, Any]:
    """Build the ``MarketContext.etf`` dict from yfinance data.

    ``cap_rate`` / ``price_rate`` are USD per major / quoted currency unit, or
    ``None`` when FX is unknown (then the USD-denominated keys are omitted).
    ``funds_data`` may be ``None``; any attribute that fails is skipped.
    """
    etf: Dict[str, Any] = {"source": "yfinance"}

    aum = safe_num(info.get("totalAssets")) or safe_num(info.get("netAssets"))
    if aum > 0 and cap_rate:
        etf["aum_usd_bn"] = aum * cap_rate / 1e9

    ops = _safe_attr(funds_data, "fund_operations") if funds_data is not None else None
    sym = (info.get("symbol") or ticker or "").upper()
    expense = _frame_value(ops, "Annual Report Expense Ratio", sym)
    if expense <= 0:
        # info's netExpenseRatio is a percent (SPY 0.0945 = 0.0945%).
        pct = safe_num(info.get("netExpenseRatio")) or safe_num(info.get("annualReportExpenseRatio"))
        expense = pct / 100.0 if pct > 0 else 0.0
    if expense > 0:
        etf["expense_ratio"] = expense
    turnover = _frame_value(ops, "Annual Holdings Turnover", sym)
    if turnover > 0:
        etf["turnover"] = turnover

    fund_yield = safe_num(info.get("yield"))
    if fund_yield > 1:  # occasionally reported as percent
        fund_yield /= 100.0
    if fund_yield > 0:
        etf["yield"] = fund_yield

    category = info.get("category") or ""
    if not category and funds_data is not None:
        overview = _safe_attr(funds_data, "fund_overview")
        if isinstance(overview, dict):
            category = overview.get("categoryName") or ""
    if category:
        etf["category"] = str(category)

    nav = safe_num(info.get("navPrice"))
    if nav > 0:
        etf["nav"] = nav
        etf.update(premium_on_nav_date(nav, dated_closes))

    if funds_data is not None:
        weights = _holding_weights(_safe_attr(funds_data, "top_holdings"))
        if weights:
            etf["top10_weight"] = sum(weights[:10])
            # Lower bound: only the disclosed top holdings are known.
            etf["hhi"] = sum(w * w for w in weights)
        sectors = _clean_weights(_safe_attr(funds_data, "sector_weightings"))
        if sectors:
            etf["sector_weights"] = sectors
        classes = _clean_weights(_safe_attr(funds_data, "asset_classes"))
        if classes:
            etf["asset_classes"] = classes

    bid, ask = safe_num(info.get("bid")), safe_num(info.get("ask"))
    if bid > 0 and ask >= bid:
        etf["spread_pct"] = (ask - bid) / ((ask + bid) / 2.0) * 100.0

    if avg_volume > 0 and price > 0 and price_rate:
        etf["dollar_volume"] = avg_volume * price * price_rate

    pe, pb = safe_num(info.get("trailingPE")), safe_num(info.get("priceToBook"))
    if pe > 0:
        etf["portfolio_pe"] = pe
    if pb > 0:
        etf["portfolio_pb"] = pb
    return etf


def dated_closes_from_history(hist: Any) -> List[Tuple[str, float]]:
    """``[(YYYY-MM-DD, close), ...]`` from a yfinance history frame; [] on any problem."""
    try:
        if hist is None or hist.empty:
            return []
        pairs = zip(list(hist.index), hist["Close"].tolist())
        out = [(_date_str(d), safe_num(c)) for d, c in pairs]
    except Exception:
        return []
    return [(d, c) for d, c in out if d and c > 0]
