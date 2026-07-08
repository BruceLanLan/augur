# -*- coding: utf-8 -*-
"""SEC EDGAR point-in-time fundamentals provider — supersedes pit_fundamentals.py.

Why this exists
----------------
``pit_fundamentals.py`` (P2-4, v10.16.9) solved the "backtest feeds constant-
zero fundamentals to value agents" bug using yfinance's annual statements,
but two limitations of that approach motivated this replacement (see
docs/superpowers/specs/2026-07-03-edgar-fundamentals-design.md):

1. yfinance's retained annual history is short — historical coverage only
   reaches back to ~2022, which is why P2-4's own OOS validation ended up
   with just 9 usable bear-high-vol-regime days.
2. The "available as of" date was a guessed +90-day filing-lag buffer, since
   no per-ticker real filing-date dataset was available in that environment
   (yfinance's ``earnings_dates`` needs ``lxml``, not installed there).

SEC EDGAR is the primary source those figures were filed *from* in the
first place: its ``companyfacts`` API exposes every XBRL fact tagged with
its real ``filed`` (SEC submission) date, and coverage reaches back to
whenever a company started filing XBRL-tagged reports (~2009-2011 for most
large caps) — both limitations above are structural, not just "try harder
with the same data source."

Point-in-time discipline
-------------------------
Same principle as ``pit_fundamentals.py``, but now the "available from" date
is the real ``filed`` date on the record instead of a guess. Only annual
(``form="10-K"``, ``fp="FY"``) periods are used for Phase 1 — matching
``pit_fundamentals.py``'s own annual-only granularity. Quarterly XBRL facts
are deliberately excluded here, not just unused: SEC XBRL commonly reports
the *same* concept twice within one quarterly filing (a cumulative
year-to-date value and a discrete single-quarter value share the same
``fp`` label but different ``start`` dates) — picking the wrong one silently
would be exactly the kind of null-by-construction bug this module exists to
prevent. Restricting to annual filings sidesteps that ambiguity entirely.

XBRL tag drift across a company's own history is real and must be merged,
not chosen once: Apple, for example, reported revenue under the ``Revenues``
tag through FY2018 and switched to
``RevenueFromContractWithCustomerExcludingAssessedTax`` starting FY2019
(confirmed against real EDGAR data during implementation). A naive port of
``pit_fundamentals.py``'s "first tag with any data wins for the whole
company" pattern would silently lose one side of that split. Instead, every
concept here is defined as a *family* of alternative tags, and matching
periods are merged across every tag in the family before period selection
happens.

Filing-restatement duplicates are also real: the same fiscal-year-end
period routinely reappears as a prior-year comparative figure in one or two
subsequent annual filings, each with a later ``filed`` date and (usually)
an identical value. The correct "first available" date for a period is the
*earliest* ``filed`` date across every filing that reports it, not
whichever happens to be scanned first.

``debt_ratio`` here is Liabilities / Assets (both listed as core concepts
in the spec), not yfinance's narrower "Total Debt" (interest-bearing debt
only) that ``pit_fundamentals.py`` used — XBRL has no single universal tag
for "total debt" the way yfinance's normalized statement does, and hunting
for a fragile per-company approximation isn't worth it for Phase 1. This is
a deliberate, documented definitional change, not an oversight.

Caching
-------
Unlike ``pit_fundamentals.py``'s process-lifetime-only in-memory cache, this
module persists both the CIK map and each ticker's companyfacts payload to
``~/.augur/edgar_cache/`` — a multi-day annual dataset doesn't need
re-fetching every process run. See ``EdgarClient`` for TTLs.

SEC fair-use requirements
--------------------------
SEC enforces a 10 req/sec rate limit and requires every request to carry a
``User-Agent`` header with a real, reachable contact (fair-use policy —
long-term use of a placeholder risks the caller's IP being blocked). Set
``AUGUR_EDGAR_CONTACT_EMAIL`` to your real email; a placeholder is used
otherwise with a one-time warning.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CACHE_DIR = Path.home() / ".augur" / "edgar_cache"
_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

_TICKER_MAP_TTL_SECONDS = 7 * 86400       # CIK map changes rarely; refresh weekly
_COMPANYFACTS_TTL_SECONDS = 24 * 3600     # a new annual filing appears at most once a year
_HTTP_TIMEOUT = 15                        # companyfacts payloads can be several MB
_RATE_LIMIT_PER_SEC = 10.0                # SEC's documented fair-use cap
_DEFAULT_CONTACT_EMAIL = "augur-agents-user@example.com"

# Only annual figures are used (see module docstring for why quarterly is
# deliberately excluded). Each entry is a family of alternative XBRL tags
# for the same underlying concept — records are merged across every tag in
# the family, not "first tag that has any data wins for the whole ticker".
_CONCEPT_TAGS: Dict[str, List[str]] = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    "net_income": ["NetIncomeLoss"],
    "stockholders_equity": ["StockholdersEquity"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "diluted_eps": ["EarningsPerShareDiluted"],
    "shares_outstanding": ["CommonStockSharesOutstanding", "CommonStockSharesIssued"],
}


# ============ Rate limiting ============

class _TokenBucket:
    """Thread-safe token bucket limiting to ``rate`` requests/sec."""

    def __init__(self, rate: float = _RATE_LIMIT_PER_SEC) -> None:
        self._rate = rate
        self._tokens = rate
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._tokens = min(self._rate, self._tokens + (now - self._last) * self._rate)
            self._last = now
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self._rate
                time.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# ============ EdgarClient ============

class EdgarClient:
    """CIK lookup + companyfacts fetch, with rate limiting and disk caching.

    Never raises: every network/parse failure returns ``None`` so callers
    can degrade to the next fallback (yfinance) rather than crash.
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir is not None else _CACHE_DIR
        self._bucket = _TokenBucket()
        self._ticker_to_cik: Optional[Dict[str, int]] = None
        self._contact_email = self._resolve_contact_email()

    @staticmethod
    def _resolve_contact_email() -> str:
        email = os.environ.get("AUGUR_EDGAR_CONTACT_EMAIL", "").strip()
        if email:
            return email
        logger.warning(
            "AUGUR_EDGAR_CONTACT_EMAIL is not set — using a placeholder contact "
            "email in the SEC EDGAR User-Agent header. SEC's fair-use policy "
            "requires a real, reachable contact; sustained use of the "
            "placeholder risks your IP being rate-limited or blocked. Set "
            "this environment variable to your real email address."
        )
        return _DEFAULT_CONTACT_EMAIL

    def _user_agent(self) -> str:
        return f"augur-agents ({self._contact_email})"

    def _http_get_json(self, url: str) -> Optional[Any]:
        """GET ``url`` and parse as JSON. Separated for easy test mocking.

        One retry on a transient network error (EDGAR is a first-party REST
        API, not the flaky scraped-internals yfinance path pit_fundamentals
        had to defend against with 3 retries — one is enough here).
        """
        self._bucket.acquire()
        req = urllib.request.Request(url, headers={"User-Agent": self._user_agent()})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:  # noqa: S310
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                # 4xx (unknown CIK, bad request) won't succeed on retry.
                logger.debug("EDGAR HTTP error for %s: %s", url, exc)
                return None
            except Exception as exc:
                logger.debug("EDGAR request failed for %s (attempt %d/2): %s", url, attempt + 1, exc)
                if attempt == 0:
                    continue
                return None
        return None

    # ---- CIK mapping ----

    def _ticker_map_cache_path(self) -> Path:
        return self._cache_dir / "company_tickers.json"

    def _load_ticker_map(self) -> Dict[str, int]:
        """Load ticker->CIK map from disk cache if fresh, else refetch."""
        if self._ticker_to_cik is not None:
            return self._ticker_to_cik

        path = self._ticker_map_cache_path()
        if path.exists():
            try:
                age = time.time() - path.stat().st_mtime
                if age < _TICKER_MAP_TTL_SECONDS:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    self._ticker_to_cik = {
                        v["ticker"].upper(): int(v["cik_str"])
                        for v in raw.values()
                        if isinstance(v, dict) and v.get("ticker") and v.get("cik_str") is not None
                    }
                    return self._ticker_to_cik
            except Exception:
                logger.debug("EDGAR ticker map cache unreadable, refetching", exc_info=True)

        raw = self._http_get_json(_TICKER_MAP_URL)
        if not isinstance(raw, dict):
            # Serve a stale cache rather than nothing if the refresh failed.
            if path.exists():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    self._ticker_to_cik = {}
                    return self._ticker_to_cik
            else:
                self._ticker_to_cik = {}
                return self._ticker_to_cik
        else:
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(raw), encoding="utf-8")
            except Exception:
                logger.debug("failed to persist EDGAR ticker map cache", exc_info=True)

        self._ticker_to_cik = {
            v["ticker"].upper(): int(v["cik_str"])
            for v in raw.values()
            if isinstance(v, dict) and v.get("ticker") and v.get("cik_str") is not None
        }
        return self._ticker_to_cik

    def get_cik(self, ticker: str) -> Optional[int]:
        """Return the CIK for ``ticker``, or ``None`` if not found (e.g. a
        non-US ticker with no SEC filings)."""
        try:
            return self._load_ticker_map().get(ticker.strip().upper())
        except Exception:
            return None

    # ---- companyfacts ----

    def _companyfacts_cache_path(self, ticker: str) -> Path:
        return self._cache_dir / f"companyfacts_{ticker.strip().upper()}.json"

    def get_company_facts(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Return the raw ``companyfacts`` payload for ``ticker`` (cached to
        disk, refreshed after ``_COMPANYFACTS_TTL_SECONDS``). ``None`` if
        the ticker has no CIK or the fetch fails with nothing cached to
        fall back to."""
        path = self._companyfacts_cache_path(ticker)
        if path.exists():
            try:
                age = time.time() - path.stat().st_mtime
                if age < _COMPANYFACTS_TTL_SECONDS:
                    return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                logger.debug("EDGAR companyfacts cache unreadable for %s, refetching", ticker, exc_info=True)

        cik = self.get_cik(ticker)
        if cik is None:
            return None

        data = self._http_get_json(_COMPANYFACTS_URL.format(cik=cik))
        if data is None:
            # Serve a stale cache rather than nothing if the refresh failed.
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    return None
            return None

        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            logger.debug("failed to persist EDGAR companyfacts cache for %s", ticker, exc_info=True)

        return data


_client_lock = threading.Lock()
_client: Optional[EdgarClient] = None


def _get_client() -> EdgarClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = EdgarClient()
        return _client


def reset_edgar_client() -> None:
    """Reset the module-level client singleton (for tests)."""
    global _client
    with _client_lock:
        _client = None


# ============ XBRL fact extraction ============

_MIN_ANNUAL_DURATION_DAYS = 300  # see _is_full_year_duration


def _is_full_year_duration(record: Dict[str, Any]) -> bool:
    """True if a duration-type record (has both ``start`` and ``end``)
    actually spans close to a full fiscal year, not a shorter period.

    Confirmed against real EDGAR data (NVDA FY2015 10-K, filed 2015-03-12):
    ``form="10-K", fp="FY"`` alone does NOT reliably mean "the annual
    figure" for duration concepts (revenue, net income, EPS, margins). The
    same 10-K also XBRL-tags supplementary Q4-only figures with the exact
    same ``form``/``fp`` combination — distinguishable only by ``start`` to
    ``end`` being ~90 days instead of ~365. Picking the wrong one silently
    produces a nonsense YoY comparison (confirmed: an unfiltered version of
    this function computed NVDA's FY2015-vs-Q3FY2015 "growth" as +282%,
    which is not a real year-over-year figure). Instant-type records (no
    ``start`` at all — balance sheet items) always pass, since they're
    inherently point-in-time and have no such ambiguity.
    """
    start = record.get("start")
    end = record.get("end")
    if not start:
        return True  # instant fact (balance sheet item) -- no duration to check
    try:
        days = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days
    except (TypeError, ValueError):
        return False
    return days >= _MIN_ANNUAL_DURATION_DAYS


def _annual_records(facts: Dict[str, Any], tag_family: List[str], namespace: str = "us-gaap") -> List[Dict[str, Any]]:
    """Merge annual (form=10-K, fp=FY, full-year duration) records for
    every tag in ``tag_family`` into one list, across every unit type
    present (concepts are normally single-unit, but this stays defensive)."""
    out: List[Dict[str, Any]] = []
    ns_facts = facts.get(namespace, {})
    for tag in tag_family:
        concept = ns_facts.get(tag)
        if not concept:
            continue
        for unit_records in concept.get("units", {}).values():
            for r in unit_records:
                if (
                    r.get("form") == "10-K"
                    and r.get("fp") == "FY"
                    and r.get("end")
                    and r.get("filed")
                    and _is_full_year_duration(r)
                ):
                    out.append(r)
    return out


def _available_periods(records: List[Dict[str, Any]], as_of: datetime) -> List[str]:
    """Return period-end date strings (sorted ascending) that are as-of
    available: the *earliest* filed date across every filing reporting that
    period must be <= as_of (restatement duplicates in later filings don't
    change when the period first became public)."""
    earliest_filed: Dict[str, str] = {}
    for r in records:
        end = r["end"]
        filed = r["filed"]
        if end not in earliest_filed or filed < earliest_filed[end]:
            earliest_filed[end] = filed

    as_of_str = as_of.strftime("%Y-%m-%d")
    periods = [end for end, filed in earliest_filed.items() if filed <= as_of_str]
    periods.sort()
    return periods


def _value_at(records: List[Dict[str, Any]], period_end: str) -> Optional[float]:
    """Return the value reported for ``period_end`` (any filing that
    reports it — values for a given period are consistent across the
    filings that mention it, confirmed against real EDGAR data)."""
    for r in records:
        if r.get("end") == period_end:
            try:
                v = float(r["val"])
                if v == v:  # NaN check
                    return v
            except (TypeError, ValueError, KeyError):
                continue
    return None


# ============ Public API ============

def fetch_edgar_fundamentals(
    ticker: str,
    as_of_date: str,
    price: Optional[float] = None,
) -> Dict[str, Any]:
    """Return point-in-time fundamentals for ``ticker`` as of ``as_of_date``,
    sourced from real SEC EDGAR filing dates.

    Same contract as the ``pit_fundamentals.fetch_pit_fundamentals`` it
    supersedes:

    Args:
        ticker: stock symbol.
        as_of_date: ``"YYYY-MM-DD"`` — the day being evaluated.
        price: closing price near ``as_of_date``. If ``None``, fetched
            internally via ``augur.data.fetch_history``.

    Returns:
        ``{"insufficient": True}`` if no 10-K annual period is as-of
        available yet, or the ticker has no SEC CIK (non-US ticker, or a US
        entity that doesn't file XBRL-tagged 10-Ks). Otherwise a dict with
        whatever subset of ``pe/pb/roe/gross_margins/operating_margins/
        revenue_growth/earnings_growth/debt_ratio/market_cap`` could be
        computed — fields that couldn't be computed because a required
        concept was absent are left at 0, never raised.

    Never raises: any unexpected exception is swallowed and treated as
    "insufficient" so a single bad ticker/date can't crash a backtest loop
    or a live analysis request.
    """
    try:
        as_of = datetime.strptime(as_of_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        return {"insufficient": True}

    try:
        client = _get_client()
        facts = client.get_company_facts(ticker)
        if not facts or "facts" not in facts:
            return {"insufficient": True}
        fact_data = facts["facts"]

        net_income_records = _annual_records(fact_data, _CONCEPT_TAGS["net_income"])
        anchor_records = net_income_records
        if not anchor_records:
            anchor_records = _annual_records(fact_data, _CONCEPT_TAGS["revenue"])
        periods = _available_periods(anchor_records, as_of)
        if not periods:
            return {"insufficient": True}

        period_end = periods[-1]  # most recent as-of-available fiscal year-end

        if price is None:
            price = _fetch_price_near(ticker, as_of_date)
        if price is None or price <= 0:
            return {"insufficient": True}

        revenue_records = _annual_records(fact_data, _CONCEPT_TAGS["revenue"])
        equity_records = _annual_records(fact_data, _CONCEPT_TAGS["stockholders_equity"])
        assets_records = _annual_records(fact_data, _CONCEPT_TAGS["assets"])
        liabilities_records = _annual_records(fact_data, _CONCEPT_TAGS["liabilities"])
        gross_profit_records = _annual_records(fact_data, _CONCEPT_TAGS["gross_profit"])
        operating_income_records = _annual_records(fact_data, _CONCEPT_TAGS["operating_income"])
        eps_records = _annual_records(fact_data, _CONCEPT_TAGS["diluted_eps"])
        shares_records = _annual_records(fact_data, _CONCEPT_TAGS["shares_outstanding"])

        net_income = _value_at(net_income_records, period_end)
        total_revenue = _value_at(revenue_records, period_end)
        stockholders_equity = _value_at(equity_records, period_end)
        total_assets = _value_at(assets_records, period_end)
        total_liabilities = _value_at(liabilities_records, period_end)
        gross_profit = _value_at(gross_profit_records, period_end)
        operating_income = _value_at(operating_income_records, period_end)
        diluted_eps = _value_at(eps_records, period_end)
        shares_outstanding = _value_at(shares_records, period_end)

        result: Dict[str, Any] = {}

        # --- EPS / PE ---
        if diluted_eps is None and net_income is not None and shares_outstanding and shares_outstanding > 0:
            diluted_eps = net_income / shares_outstanding
        result["pe"] = price / diluted_eps if diluted_eps and diluted_eps > 0 else 0.0

        # --- Book value / PB ---
        book_value_per_share = None
        if stockholders_equity is not None and shares_outstanding and shares_outstanding > 0:
            book_value_per_share = stockholders_equity / shares_outstanding
        result["pb"] = (
            price / book_value_per_share
            if book_value_per_share and book_value_per_share > 0
            else 0.0
        )

        # --- ROE ---
        result["roe"] = (
            net_income / stockholders_equity
            if net_income is not None and stockholders_equity and stockholders_equity > 0
            else 0.0
        )

        # --- Margins ---
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
            prior_revenue = _value_at(revenue_records, prior_period_end)
            if total_revenue is not None and prior_revenue:
                result["revenue_growth"] = (total_revenue / prior_revenue) - 1.0
            prior_net_income = _value_at(net_income_records, prior_period_end)
            if net_income is not None and prior_net_income:
                result["earnings_growth"] = (net_income / prior_net_income) - 1.0

        # --- Debt ratio: Liabilities/Assets (see module docstring — a
        # deliberate definitional change from pit_fundamentals.py's
        # narrower "Total Debt", since XBRL has no single universal
        # interest-bearing-debt-only tag). ---
        result["debt_ratio"] = (
            total_liabilities / total_assets
            if total_liabilities is not None and total_assets
            else 0.0
        )

        # --- Market cap ---
        result["market_cap"] = (
            price * shares_outstanding if shares_outstanding and shares_outstanding > 0 else 0.0
        )

        return result
    except Exception:
        logger.debug("edgar_fundamentals: unexpected failure for %s as of %s", ticker, as_of_date, exc_info=True)
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
