# -*- coding: utf-8 -*-
"""EDGAR-based backfill for ``<data dir>/earnings_calendar.json``.

Past earnings releases are read from 8-K filings carrying Item 2.02
("Results of Operations and Financial Condition"). One next date is then
*estimated* from the filing cadence. Estimated dates are always tagged
``confidence: "estimated"`` — never ``"confirmed"``.

Merging never overwrites what the user wrote: an existing entry for the
same ticker + date wins, only missing dates are added.
"""
from __future__ import annotations

import json
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from augur.data_dir import get_data_dir

SOURCE_8K = "sec_8k_2.02"
SOURCE_ESTIMATED = "estimated_from_8k_cadence"
_MAX_GAPS = 4


class EdgarFetchError(RuntimeError):
    """Submissions could not be fetched for a ticker."""


def _parse_date(value: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _has_item_202(items: Any) -> bool:
    if not items:
        return False
    return any(part.strip() == "2.02" for part in str(items).split(","))


def estimate_events_from_edgar(ticker: str, submissions: dict, today: date) -> List[Dict[str, Any]]:
    """Past 8-K Item 2.02 events plus at most one cadence-estimated next event.

    ``ticker`` is accepted for call-site symmetry; the submissions payload
    already belongs to it. Only filings dated on/before ``today`` count as
    history. The estimate is added only with >= 2 past events.
    """
    recent = ((submissions or {}).get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    items = recent.get("items") or []
    accessions = recent.get("accessionNumber") or []

    by_date: Dict[date, Dict[str, Any]] = {}
    for i, form in enumerate(forms):
        if str(form).upper() not in ("8-K", "8-K/A"):
            continue
        if not _has_item_202(items[i] if i < len(items) else ""):
            continue
        d = _parse_date(dates[i] if i < len(dates) else None)
        if d is None or d > today or d in by_date:
            continue
        by_date[d] = {
            "event_date": d.isoformat(),
            "confidence": "historical",
            "source": SOURCE_8K,
            "accession": accessions[i] if i < len(accessions) else "",
        }

    past = [by_date[d] for d in sorted(by_date)]
    if len(past) < 2:
        return past

    ordered = sorted(by_date)
    gaps = [(b - a).days for a, b in zip(ordered, ordered[1:])][-_MAX_GAPS:]
    median_gap = int(round(statistics.median(gaps)))
    if median_gap <= 0:
        return past
    nxt = ordered[-1] + timedelta(days=median_gap)
    past.append({
        "event_date": nxt.isoformat(),
        "confidence": "estimated",
        "source": SOURCE_ESTIMATED,
    })
    return past


def fetch_submissions(ticker: str) -> dict:
    """Submissions JSON via the project's existing EDGAR client (CIK lookup,
    User-Agent / contact email, rate limit, disk cache). Raises
    :class:`EdgarFetchError` when the ticker is unknown or the fetch fails."""
    from augur.consensus.edgar_fundamentals import _get_client

    client = _get_client()
    cik = client.get_cik(ticker)
    if cik is None:
        raise EdgarFetchError(f"no CIK found for {ticker} (or ticker map unavailable)")
    data = client.get_submissions(cik)
    if not data:
        raise EdgarFetchError(f"EDGAR submissions unavailable for {ticker} (CIK {cik})")
    return data


def merge_events(calendar: Dict[str, list], ticker: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add ``events`` to ``calendar[ticker]`` in place; existing dates win.
    Returns the events actually added."""
    t = ticker.upper()
    existing = calendar.setdefault(t, [])
    have = {str(e.get("event_date")) for e in existing if isinstance(e, dict)}
    added = []
    for ev in events:
        if ev["event_date"] in have:
            continue
        existing.append(dict(ev))
        have.add(ev["event_date"])
        added.append(ev)
    existing.sort(key=lambda e: str(e.get("event_date", "")) if isinstance(e, dict) else "")
    return added


def backfill_calendar(
    tickers: List[str],
    path: Optional[Path] = None,
    *,
    today: Optional[date] = None,
    fetch: Optional[Callable[[str], dict]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Backfill the calendar file for ``tickers``.

    Returns ``{ticker: {"added": [...], "estimated": n, "error": str|None}}``.
    Per-ticker fetch errors are recorded, not raised. The file is written
    only when something was added.
    """
    path = Path(path) if path else get_data_dir() / "earnings_calendar.json"
    today = today or datetime.now(timezone.utc).date()
    fetch = fetch or fetch_submissions

    calendar: Dict[str, list] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                calendar = loaded
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"cannot read {path}: {exc} — refusing to overwrite") from exc

    report: Dict[str, Dict[str, Any]] = {}
    changed = False
    for raw in tickers:
        t = raw.strip().upper()
        try:
            submissions = fetch(t)
        except Exception as exc:  # network / lookup errors are per-ticker
            report[t] = {"added": [], "estimated": 0, "error": str(exc) or type(exc).__name__}
            continue
        events = estimate_events_from_edgar(t, submissions, today)
        added = merge_events(calendar, t, events)
        if not calendar.get(t):
            calendar.pop(t, None)
        changed = changed or bool(added)
        report[t] = {
            "added": added,
            "estimated": sum(1 for e in added if e.get("confidence") == "estimated"),
            "error": None,
        }

    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(calendar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(path)
    return report
