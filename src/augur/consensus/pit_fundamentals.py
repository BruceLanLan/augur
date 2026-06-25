# -*- coding: utf-8 -*-
"""Point-in-time (PIT) fundamentals provider for historical backtest replay.

Why this exists
----------------
``Backtester.run_live_backtest`` (see ``augur.backtest``) replays daily price
history through every agent, but historically only ever populated
price/rsi/macd/sma in each day's context -- pe/pb/roe/etc. stayed at the
``MarketContext`` dataclass default of 0 for every single historical day.
Since value-style agents (marks/dalio/graham/buffett/soros/munger) derive
their score primarily from pe/pb/roe, feeding them constant-zero fundamentals
makes their score a constant for the whole backtest window -- "reweighting"
a constant-score agent just adds a constant offset to the consensus and can
never move a rank-IC. This module provides each historical day with the
fundamentals that would actually have been *available* as of that day, so
value agents can genuinely differentiate across dates and tickers in a
backtest replay.

Point-in-time discipline
-------------------------
Annual statements are filed well after the fiscal period they describe ends.
Using the period-end date itself as the "available" date is a look-ahead
bug: it lets a backtest see e.g. a fiscal-year-end Dec 31 statement on
Jan 1, when in reality that 10-K isn't filed for another 1-3 months. This
module applies a conservative flat ``+90`` calendar day filing-lag buffer
to each period's end date (no real per-ticker filing-date dataset is
available in this environment -- ``yfinance``'s ``earnings_dates`` requires
``lxml``, which isn't installed here -- so the buffer is an approximation,
documented as such everywhere this module's output is surfaced).

Caching
-------
The full annual ``financials``/``balance_sheet`` statements are fetched from
yfinance **once per ticker** and cached in a module-level dict. All
as-of-date slicing happens in-memory against that cached statement, so a
backtest that calls this function once per day for a year never re-fetches
the same ticker's statement twice.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ticker -> {"financials": DataFrame, "balance_sheet": DataFrame} (raw, unfiltered).
# A *non-empty* fetch is cached permanently (one network round-trip per ticker
# per process). An *empty* fetch is deliberately NOT cached -- see
# ``_get_statements`` below: yfinance has been observed to transiently return
# an empty ``financials``/``balance_sheet`` DataFrame for a ticker that has
# real, retrievable data on a later call within the same process (confirmed
# empirically: 2 of 3 fresh-process calls for the same ticker returned 5 valid
# annual columns, 1 of 3 returned an empty frame). Caching that transient empty
# response as permanent truth would silently and incorrectly zero-fill or drop
# every backtest day for that ticker for the rest of the run.
_STATEMENT_CACHE: Dict[str, Dict[str, Any]] = {}

# Max attempts to fetch a ticker's statements before accepting an empty result
# as genuine (rather than a transient yfinance hiccup).
_FETCH_RETRY_ATTEMPTS = 3

# Conservative buffer between a fiscal period's end date and the date its
# annual statement is treated as "available" for point-in-time purposes.
FILING_LAG_DAYS = 90


def _is_empty_statement(df) -> bool:
    """True if ``df`` is ``None`` or an empty DataFrame (nothing usable fetched)."""
    return df is None or df.empty


def _get_statements(ticker: str) -> Dict[str, Any]:
    """Fetch and cache the full annual financials + balance sheet for ``ticker``.

    Retries up to ``_FETCH_RETRY_ATTEMPTS`` times if yfinance comes back with
    an empty (but not exception-raising) result, since yfinance has been
    observed to transiently return an empty statement for tickers that do
    have real data on a subsequent call. Only a result that is still empty
    after all retries is cached and treated as "this ticker truly has no
    fundamentals" -- a successful non-empty fetch is cached immediately and
    never re-fetched again for the life of the process.
    """
    ticker = ticker.upper()
    if ticker in _STATEMENT_CACHE:
        return _STATEMENT_CACHE[ticker]

    entry: Dict[str, Any] = {"financials": None, "balance_sheet": None}
    for attempt in range(_FETCH_RETRY_ATTEMPTS):
        try:
            import yfinance as yf

            tk = yf.Ticker(ticker)
            financials = tk.financials
            balance_sheet = tk.balance_sheet
        except Exception:
            logger.debug(
                "pit_fundamentals: failed to fetch statements for %s (attempt %d/%d)",
                ticker, attempt + 1, _FETCH_RETRY_ATTEMPTS, exc_info=True,
            )
            financials, balance_sheet = None, None

        entry["financials"] = financials
        entry["balance_sheet"] = balance_sheet

        # A non-empty financials fetch is good enough to stop retrying and
        # cache permanently, even if balance_sheet itself came back empty
        # (some tickers genuinely lack one or the other).
        if not _is_empty_statement(financials):
            break
        logger.debug(
            "pit_fundamentals: empty financials for %s on attempt %d/%d, retrying",
            ticker, attempt + 1, _FETCH_RETRY_ATTEMPTS,
        )

    _STATEMENT_CACHE[ticker] = entry
    return entry


def _row(df, *names: str):
    """Return the first matching row (as a pandas Series indexed by period-end) found in ``df``."""
    if df is None:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def _val(series, period_end) -> Optional[float]:
    """Extract a single scalar from ``series`` at ``period_end``, treating NaN as missing."""
    if series is None or period_end not in series.index:
        return None
    try:
        v = series[period_end]
    except Exception:
        return None
    try:
        if v is None:
            return None
        fv = float(v)
        if fv != fv:  # NaN check without importing math/pandas for this one comparison
            return None
        return fv
    except (TypeError, ValueError):
        return None


# Rows checked to decide whether a period column has real (non-NaN) data at
# all. yfinance pads its oldest retained annual column with NaN once it ages
# out of full retention (observed directly: NVDA's earliest kept column had
# every row NaN) -- a column like that must NOT be treated as "available",
# even though it has a column label, because every field derived from it
# would silently fall through to the 0.0 defaults below (the exact
# null-by-construction failure mode this module exists to prevent).
_CORE_ROWS_FOR_AVAILABILITY = ("Net Income", "Total Revenue", "Operating Revenue")


def _period_has_real_data(financials, period_end) -> bool:
    """True if at least one core row is a real (non-NaN) value for ``period_end``."""
    for name in _CORE_ROWS_FOR_AVAILABILITY:
        if _val(_row(financials, name), period_end) is not None:
            return True
    return False


def _available_periods(financials, as_of: datetime):
    """Return period-end timestamps (sorted ascending) whose filing is as-of available.

    A period is "as-of available" iff both:
      1. ``period_end + FILING_LAG_DAYS <= as_of`` -- the look-ahead guard: a
         backtest day must never see a statement that, in reality, would not
         yet have been filed as of that day.
      2. At least one core row (net income / revenue) is a real, non-NaN
         value for that period column -- guards against yfinance's
         NaN-padded oldest-retained column being mistaken for real data.
    """
    if financials is None or financials.empty:
        return []
    periods = []
    for period_end in financials.columns:
        try:
            available_from = period_end.to_pydatetime() + timedelta(days=FILING_LAG_DAYS)
        except Exception:
            continue
        if available_from <= as_of and _period_has_real_data(financials, period_end):
            periods.append(period_end)
    periods.sort()
    return periods


def fetch_pit_fundamentals(
    ticker: str,
    as_of_date: str,
    price: Optional[float] = None,
) -> Dict[str, Any]:
    """Return point-in-time fundamentals for ``ticker`` as of ``as_of_date``.

    Args:
        ticker: stock symbol.
        as_of_date: ``"YYYY-MM-DD"`` -- the backtest day being evaluated.
        price: closing price near ``as_of_date``. If ``None``, this function
            fetches it internally via ``augur.data.fetch_history`` (prefer
            passing it in when the caller already has it, to avoid a
            redundant network call).

    Returns:
        ``{"insufficient": True}`` if no annual statement is as-of available
        yet (i.e. ``as_of_date`` is earlier than any period's
        ``period_end + 90 days``). Otherwise a dict with whatever subset of
        ``pe/pb/roe/gross_margins/operating_margins/revenue_growth/
        earnings_growth/debt_ratio/market_cap`` could be computed (fields
        that could not be computed because a required row was absent are
        left at 0, never raised).

    Never raises: any unexpected exception is swallowed and treated as
    "insufficient" so a single bad ticker/date can't crash a backtest loop.
    """
    try:
        as_of = datetime.strptime(as_of_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        return {"insufficient": True}

    try:
        statements = _get_statements(ticker)
        financials = statements.get("financials")
        balance_sheet = statements.get("balance_sheet")

        periods = _available_periods(financials, as_of)
        if not periods:
            return {"insufficient": True}

        period_end = periods[-1]  # most recent as-of-available period

        if price is None:
            price = _fetch_price_near(ticker, as_of_date)
        if price is None or price <= 0:
            return {"insufficient": True}

        result: Dict[str, Any] = {}

        # --- EPS / PE ---
        diluted_eps = _val(_row(financials, "Diluted EPS"), period_end)
        if diluted_eps is None:
            net_income = _val(_row(financials, "Net Income"), period_end)
            diluted_shares = _val(_row(financials, "Diluted Average Shares"), period_end)
            if net_income is not None and diluted_shares and diluted_shares > 0:
                diluted_eps = net_income / diluted_shares
        pe = 0.0
        if diluted_eps and diluted_eps > 0:
            pe = price / diluted_eps
        result["pe"] = pe

        # --- Book value / PB ---
        stockholders_equity = _val(
            _row(balance_sheet, "Stockholders Equity", "Common Stock Equity"), period_end
        )
        shares_outstanding = _val(
            _row(balance_sheet, "Ordinary Shares Number", "Share Issued"), period_end
        )
        pb = 0.0
        book_value_per_share = None
        if stockholders_equity is not None and shares_outstanding and shares_outstanding > 0:
            book_value_per_share = stockholders_equity / shares_outstanding
            if book_value_per_share > 0:
                pb = price / book_value_per_share
        result["pb"] = pb

        # --- ROE ---
        roe = 0.0
        net_income = _val(_row(financials, "Net Income"), period_end)
        if net_income is not None and stockholders_equity and stockholders_equity > 0:
            roe = net_income / stockholders_equity
        result["roe"] = roe

        # --- Margins ---
        total_revenue = _val(_row(financials, "Total Revenue", "Operating Revenue"), period_end)
        gross_profit = _val(_row(financials, "Gross Profit"), period_end)
        operating_income = _val(_row(financials, "Operating Income"), period_end)
        result["gross_margins"] = (
            gross_profit / total_revenue if gross_profit is not None and total_revenue else 0.0
        )
        result["operating_margins"] = (
            operating_income / total_revenue if operating_income is not None and total_revenue else 0.0
        )

        # --- YoY growth (only using two as-of-available periods, never a future one) ---
        result["revenue_growth"] = 0.0
        result["earnings_growth"] = 0.0
        if len(periods) >= 2:
            prior_period_end = periods[-2]
            prior_revenue = _val(_row(financials, "Total Revenue", "Operating Revenue"), prior_period_end)
            if total_revenue is not None and prior_revenue:
                result["revenue_growth"] = (total_revenue / prior_revenue) - 1.0
            prior_net_income = _val(_row(financials, "Net Income"), prior_period_end)
            if net_income is not None and prior_net_income:
                result["earnings_growth"] = (net_income / prior_net_income) - 1.0

        # --- Debt ratio ---
        total_debt = _val(_row(balance_sheet, "Total Debt"), period_end)
        total_assets = _val(_row(balance_sheet, "Total Assets"), period_end)
        result["debt_ratio"] = (
            total_debt / total_assets if total_debt is not None and total_assets else 0.0
        )

        # --- Market cap ---
        result["market_cap"] = (
            price * shares_outstanding if shares_outstanding and shares_outstanding > 0 else 0.0
        )

        return result
    except Exception:
        logger.debug(
            "pit_fundamentals: unexpected failure for %s as of %s", ticker, as_of_date, exc_info=True
        )
        return {"insufficient": True}


def _fetch_price_near(ticker: str, as_of_date: str) -> Optional[float]:
    """Fetch the closing price at/near ``as_of_date`` via ``augur.data.fetch_history``."""
    try:
        from augur.data import fetch_history

        history = fetch_history(ticker, period="5y")
        if not history:
            return None
        candidates = [day for day in history if day.get("date", "") <= as_of_date]
        if not candidates:
            return None
        return float(candidates[-1]["close"])
    except Exception:
        return None


def clear_pit_cache() -> None:
    """Clear the module-level statement cache (for tests)."""
    _STATEMENT_CACHE.clear()
