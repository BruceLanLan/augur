# -*- coding: utf-8 -*-
"""SEC EDGAR Form 4 insider-trading factor — Phase 2 of the EDGAR data
deepening (see docs/superpowers/specs/2026-07-03-edgar-fundamentals-design.md).

Signal: ``insider_buying_signal`` — a 0-10 score (5.0 = neutral) derived
from trailing-90-day net dollar buying by company insiders, relative to the
stock's own trading volume. Reuses ``EdgarClient`` from
``edgar_fundamentals.py`` (CIK lookup, rate limiting, disk caching) per the
spec's "all four phases share one client" architecture.

Why only transactionCode P/S (open-market purchase/sale)
-----------------------------------------------------------
The spec's original framing ("买入总额 − 卖出总额", gross bought minus gross
sold) undercounts what actually matters if taken literally against real
Form 4 data. Confirmed against real AAPL filings during implementation: a
single Form 4 routinely contains multiple ``nonDerivativeTransaction``
entries with *different* SEC transaction codes sharing the same
Acquired/Disposed direction as a genuine market trade, but representing
entirely mechanical events with no signal content:

  - ``M`` — exercise/conversion of a derivative security (RSU vesting).
    Happens on a pre-set schedule regardless of the insider's view on the
    stock.
  - ``F`` — shares withheld by the company to cover tax on that vesting.
    Not a market transaction at all.
  - ``G`` — gift.
  - ``A`` — grant/award (the company giving the insider equity, not the
    insider choosing to buy).

Across 6 sampled real recent AAPL Form 4 filings, the transaction-code
distribution was M:11, S:5, F:3, G:1, P:0 — summing "acquired minus
disposed" naively would have mis-counted 11 scheduled RSU vestings and
3 tax-withholding dispositions as if they were discretionary trades,
diluting the 5 genuine open-market sales into noise. This module restricts
to ``transactionCode in ("P", "S")`` — open-market purchase / open-market
sale — matching the convention used by standard insider-trading trackers
(OpenInsider, Finviz, etc.), which is what actually reflects an insider's
own capital-allocation decision.

Point-in-time discipline: a Form 4 must be legally filed within 2 business
days of the transaction, but this module uses the filing's own
``filingDate`` (from the submissions index) as the "available from" date
for as-of-date filtering, not the (earlier) ``transactionDate`` — a
backtest evaluating a historical day must only see filings that had
actually posted to EDGAR by that day.
"""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from augur.consensus.edgar_fundamentals import _get_client

logger = logging.getLogger(__name__)

_TRAILING_WINDOW_DAYS = 90
_CLUSTER_WINDOW_DAYS = 7
_CLUSTER_MIN_DISTINCT_INSIDERS = 2
_CLUSTER_AMPLIFICATION = 1.3
# Scale for the tanh squash: a net-buy of ~2% of trailing average daily
# dollar volume maps to roughly signal=8.8; a net-sell of the same
# magnitude maps to roughly signal=1.2. Tunable, not derived from any
# external benchmark -- documented so a future recalibration has a
# concrete anchor to compare against.
_SIGNAL_SCALE = 0.02

_OPEN_MARKET_CODES = ("P", "S")  # purchase, sale -- see module docstring


def _squash_to_signal(ratio: float) -> float:
    """Map an unbounded net-buy/ADV ratio to a bounded 0-10 score, 5.0 at
    ratio=0. tanh gives a smooth squash instead of an abrupt linear clamp."""
    return max(0.0, min(10.0, 5.0 + 5.0 * math.tanh(ratio / _SIGNAL_SCALE)))


def _parse_form4_transactions(xml_text: str, filing_date: str) -> List[Dict[str, Any]]:
    """Extract open-market (P/S) non-derivative transactions from one Form
    4's raw XML. Returns a list of {reporting_owner_cik, transaction_date,
    code, shares, price, filing_date} dicts. Never raises: malformed XML
    or missing fields just yield fewer/no transactions from this filing."""
    out: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out

    owner_cik = None
    owner_el = root.find("./reportingOwner/reportingOwnerId/rptOwnerCik")
    if owner_el is not None and owner_el.text:
        owner_cik = owner_el.text.strip()

    table = root.find("nonDerivativeTable")
    if table is None:
        return out

    for txn in table.findall("nonDerivativeTransaction"):
        code_el = txn.find("./transactionCoding/transactionCode")
        code = code_el.text.strip() if code_el is not None and code_el.text else None
        if code not in _OPEN_MARKET_CODES:
            continue

        date_el = txn.find("./transactionDate/value")
        txn_date = date_el.text.strip() if date_el is not None and date_el.text else None

        shares_el = txn.find("./transactionAmounts/transactionShares/value")
        try:
            shares = float(shares_el.text) if shares_el is not None and shares_el.text else None
        except (TypeError, ValueError):
            shares = None

        price_el = txn.find("./transactionAmounts/transactionPricePerShare/value")
        try:
            price = float(price_el.text) if price_el is not None and price_el.text else None
        except (TypeError, ValueError):
            price = None

        if not txn_date or shares is None or price is None or shares <= 0 or price <= 0:
            continue

        out.append({
            "reporting_owner_cik": owner_cik,
            "transaction_date": txn_date,
            "code": code,
            "shares": shares,
            "price": price,
            "filing_date": filing_date,
        })

    return out


def _fetch_form4_transactions(ticker: str, as_of_date: str) -> List[Dict[str, Any]]:
    """Fetch and parse every as-of-available Form 4 open-market transaction
    for ``ticker`` within the trailing ``_TRAILING_WINDOW_DAYS`` window.
    Never raises: any failure yields an empty list (treated as "no
    signal", not "insufficient" -- see module docstring)."""
    try:
        client = _get_client()
        cik = client.get_cik(ticker)
        if cik is None:
            return []

        as_of = datetime.strptime(as_of_date, "%Y-%m-%d")
        window_start = as_of - timedelta(days=_TRAILING_WINDOW_DAYS)
        as_of_str = as_of.strftime("%Y-%m-%d")
        window_start_str = window_start.strftime("%Y-%m-%d")

        submissions = client.get_submissions(cik)
        if not submissions:
            return []
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accns = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])

        transactions: List[Dict[str, Any]] = []
        for form, accn, filing_date in zip(forms, accns, filing_dates):
            if form != "4":
                continue
            # Point-in-time guard: only filings already posted as of the
            # evaluation date, within the trailing window.
            if filing_date > as_of_str or filing_date < window_start_str:
                continue

            xml_text = client.get_filing_document(cik, accn, "form4.xml")
            if not xml_text:
                continue
            transactions.extend(_parse_form4_transactions(xml_text, filing_date))

        return transactions
    except Exception:
        logger.debug("edgar_insider: failed to fetch Form 4 transactions for %s as of %s", ticker, as_of_date, exc_info=True)
        return []


def fetch_insider_buying_signal(
    ticker: str,
    as_of_date: str,
    avg_daily_dollar_volume: Optional[float] = None,
) -> Dict[str, Any]:
    """Return ``{"insider_buying_signal": float}`` (0-10, 5.0=neutral) for
    ``ticker`` as of ``as_of_date``. Always returns a usable value — never
    an "insufficient" flag — since this is a persona-consumable factor
    score (like the other ~70 factors in ``metadata.factors``), not a
    fundamentals field that needs to distinguish "no data" from "zero" for
    a caller doing its own arithmetic.

    Never raises: any fetch/parse failure yields the neutral 5.0.

    Args:
        ticker: stock symbol.
        as_of_date: ``"YYYY-MM-DD"``.
        avg_daily_dollar_volume: trailing average daily dollar volume, used
            as the denominator for normalizing net insider buying pressure.
            If ``None``, computed internally via ``augur.data.fetch_history``.
    """
    try:
        transactions = _fetch_form4_transactions(ticker, as_of_date)
        if not transactions:
            return {"insider_buying_signal": 5.0}

        if avg_daily_dollar_volume is None:
            avg_daily_dollar_volume = _fetch_avg_daily_dollar_volume(ticker, as_of_date)
        if not avg_daily_dollar_volume or avg_daily_dollar_volume <= 0:
            return {"insider_buying_signal": 5.0}

        net_dollar_flow = 0.0
        buy_owner_dates: List[tuple] = []  # (owner_cik, transaction_date) for cluster detection
        for t in transactions:
            dollar_amount = t["shares"] * t["price"]
            if t["code"] == "P":
                net_dollar_flow += dollar_amount
                buy_owner_dates.append((t["reporting_owner_cik"], t["transaction_date"]))
            elif t["code"] == "S":
                net_dollar_flow -= dollar_amount

        ratio = net_dollar_flow / avg_daily_dollar_volume
        if _has_cluster_buying(buy_owner_dates) and ratio > 0:
            ratio *= _CLUSTER_AMPLIFICATION

        return {"insider_buying_signal": round(_squash_to_signal(ratio), 3)}
    except Exception:
        logger.debug("edgar_insider: unexpected failure for %s as of %s", ticker, as_of_date, exc_info=True)
        return {"insider_buying_signal": 5.0}


def _has_cluster_buying(buy_owner_dates: List[tuple]) -> bool:
    """True if 2+ *distinct* insiders each made an open-market purchase
    within the same 7-calendar-day window -- a stronger signal than any
    single insider's purchase, per the spec's cluster-buying amplification."""
    distinct_owners = {o for o, _ in buy_owner_dates if o}
    if len(distinct_owners) < _CLUSTER_MIN_DISTINCT_INSIDERS:
        return False

    dates = sorted(datetime.strptime(d, "%Y-%m-%d") for _, d in buy_owner_dates if d)
    for i, d in enumerate(dates):
        window_owners = {
            o for o, od in buy_owner_dates
            if od and 0 <= (d - datetime.strptime(od, "%Y-%m-%d")).days <= _CLUSTER_WINDOW_DAYS
        }
        if len(window_owners) >= _CLUSTER_MIN_DISTINCT_INSIDERS:
            return True
    return False


def _fetch_avg_daily_dollar_volume(ticker: str, as_of_date: str, lookback_days: int = 90) -> Optional[float]:
    """Trailing average daily dollar volume (price * volume) up to
    ``as_of_date``, via ``augur.data.fetch_history``."""
    try:
        from augur.data import fetch_history

        history = fetch_history(ticker, period="6mo")
        if not history:
            return None
        candidates = [
            day for day in history
            if day.get("date", "") <= as_of_date and day.get("close") and day.get("volume")
        ]
        if not candidates:
            return None
        recent = candidates[-lookback_days:]
        dollar_volumes = [day["close"] * day["volume"] for day in recent]
        if not dollar_volumes:
            return None
        return sum(dollar_volumes) / len(dollar_volumes)
    except Exception:
        return None
