# -*- coding: utf-8 -*-
"""
Earnings event service (P2.1 MVP).

Identifies upcoming earnings events from a watchlist, generates
pre-event dossiers using the earnings-prep Skill, and compares
filing deltas against previous runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from augur.data_dir import get_data_dir


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class EarningsEvent:
    """A detected or scheduled earnings event for a ticker."""

    ticker: str
    event_date: str          # ISO date (YYYY-MM-DD)
    confidence: str          # "confirmed" | "estimated" | "unknown"
    fiscal_period: str = ""  # e.g. "Q4 2025"
    source: str = ""         # Where the date came from


@dataclass
class DossierStatus:
    """Readiness status for a pre-event dossier."""

    ticker: str
    event: EarningsEvent
    ready: bool
    missing_items: List[str] = field(default_factory=list)
    last_generated: Optional[str] = None  # ISO timestamp
    run_id: Optional[str] = None


@dataclass
class FilingDelta:
    """Material changes between two filing snapshots."""

    ticker: str
    new_accession: str
    previous_accession: str
    changes: List[Dict[str, Any]] = field(default_factory=list)
    new_risks: List[str] = field(default_factory=list)
    removed_risks: List[str] = field(default_factory=list)
    guidance_change: Optional[str] = None
    run_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Earnings Event Service
# ---------------------------------------------------------------------------

class EarningsEventService:
    """Detect earnings events and manage dossier readiness.

    Uses a local cache of earnings calendars keyed by ticker.
    In production this would integrate with SEC EDGAR or provider APIs;
    the MVP reads from a lightweight JSON calendar.
    """

    def __init__(self, calendar_path: Optional[Path] = None):
        self._calendar_path = calendar_path or (
            get_data_dir() / "earnings_calendar.json"
        )

    # ------------------------------------------------------------------
    # Event detection
    # ------------------------------------------------------------------

    def detect_events(
        self,
        tickers: List[str],
        lookahead_days: int = 30,
    ) -> List[EarningsEvent]:
        """Return upcoming earnings events for *tickers* within *lookahead_days*.

        Only returns events whose ``event_date`` falls between today and
        today + *lookahead_days*.
        """
        now = datetime.utcnow().date()
        cutoff = now + timedelta(days=lookahead_days)
        all_events = self._load_calendar()
        upcoming: List[EarningsEvent] = []

        for ticker in tickers:
            t = ticker.upper()
            if t not in all_events:
                continue
            for raw in all_events[t]:
                try:
                    event_date = datetime.strptime(
                        raw["event_date"], "%Y-%m-%d"
                    ).date()
                except (ValueError, KeyError):
                    continue
                if now <= event_date <= cutoff:
                    upcoming.append(EarningsEvent(
                        ticker=t,
                        event_date=raw["event_date"],
                        confidence=raw.get("confidence", "unknown"),
                        fiscal_period=raw.get("fiscal_period", ""),
                        source=raw.get("source", ""),
                    ))
        return upcoming

    def identify_events_for_watchlist(
        self,
        watchlist_path: Optional[Path] = None,
        lookahead_days: int = 30,
    ) -> List[EarningsEvent]:
        """Convenience: read the watchlist YAML and detect events."""
        import yaml

        wl_path = watchlist_path or (get_data_dir() / "watchlist.yaml")
        if not wl_path.exists():
            return []

        with open(wl_path) as f:
            data = yaml.safe_load(f) or {}

        return self.detect_events(_watchlist_tickers(data), lookahead_days)

    # ------------------------------------------------------------------
    # Dossier readiness
    # ------------------------------------------------------------------

    def check_dossier_readiness(
        self,
        events: List[EarningsEvent],
    ) -> List[DossierStatus]:
        """For each event, check whether a dossier can be generated."""
        results: List[DossierStatus] = []
        for event in events:
            missing, run_id = self._readiness(event.ticker)
            results.append(DossierStatus(
                ticker=event.ticker,
                event=event,
                ready=len(missing) == 0,
                missing_items=missing,
                run_id=run_id,
            ))
        return results

    def _required_sources(self, ticker: str) -> List[str]:
        """Return list of missing required data sources for *ticker*."""
        return self._readiness(ticker)[0]

    def _readiness(self, ticker: str) -> Tuple[List[str], Optional[str]]:
        """(missing items, latest run_id) for *ticker*.

        Checks real sources only:

        - ``fundamentals_snapshot``: a saved RunBundle exists for the ticker
          (``run_tracker.latest_run_id``).
        - ``recent_filings``: that latest run carries at least one non-missing
          SEC/EDGAR evidence item in its step results.
        - ``prior_guidance``: ``GuidanceTracker`` (ticker-keyed, under
          ``<data_dir>/guidance/``) holds at least one record. The EDGAR
          guidance extraction cache is keyed by accession number, not
          ticker, so it cannot be looked up here.
        """
        from augur.run_tracker import latest_run_id, load_run_bundle_dict

        missing: List[str] = []
        t = ticker.upper()

        if not self._has_guidance(t):
            missing.append("prior_guidance")

        run_id = latest_run_id(t)
        if run_id is None:
            missing.append("fundamentals_snapshot")
            missing.append("recent_filings")
            return missing, None

        try:
            bundle = load_run_bundle_dict(run_id)
        except (OSError, ValueError):
            bundle = {}
        if not _bundle_has_sec_evidence(bundle):
            missing.append("recent_filings")
        return missing, run_id

    @staticmethod
    def _has_guidance(ticker: str) -> bool:
        path = get_data_dir() / "guidance" / f"{ticker.upper()}.json"
        if not path.exists():
            return False
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        return isinstance(records, list) and len(records) > 0

    # ------------------------------------------------------------------
    # Filing delta
    # ------------------------------------------------------------------

    def compare_filings(
        self,
        ticker: str,
        new_run_id: str,
        previous_run_id: Optional[str] = None,
    ) -> FilingDelta:
        """Compare two run bundles to identify filing-level changes.

        If *previous_run_id* is omitted, the most recent completed run
        for *ticker* is used.
        """
        runs_dir = get_data_dir() / "runs"

        # Resolve previous run
        if previous_run_id is None:
            from augur.run_tracker import list_run_ids

            # Newest first by created_at + start sequence, not by filename:
            # run_ids from the same second sort by hash, not start order.
            for rid in list_run_ids(ticker):
                if rid != new_run_id:
                    previous_run_id = rid
                    break

        new_bundle = self._load_run(runs_dir, new_run_id)
        prev_bundle = self._load_run(runs_dir, previous_run_id) if previous_run_id else None

        delta = FilingDelta(
            ticker=ticker.upper(),
            new_accession=new_bundle.get("manifest", {}).get("input_snapshot_hash", ""),
            previous_accession=(
                prev_bundle.get("manifest", {}).get("input_snapshot_hash", "")
                if prev_bundle else ""
            ),
            run_id=new_run_id,
        )

        if prev_bundle is None:
            delta.changes.append({"type": "initial_run", "detail": "No previous run to compare"})
            return delta

        # Compare step results
        new_steps = {s["step_name"]: s for s in new_bundle.get("step_results", [])}
        prev_steps = {s["step_name"]: s for s in prev_bundle.get("step_results", [])}

        for step_name in set(new_steps) | set(prev_steps):
            ns = new_steps.get(step_name)
            ps = prev_steps.get(step_name)
            if ns and ps:
                if ns.get("content_hash") != ps.get("content_hash"):
                    delta.changes.append({
                        "type": "step_changed",
                        "step": step_name,
                        "new_hash": ns.get("content_hash"),
                        "previous_hash": ps.get("content_hash"),
                    })
            elif ns and not ps:
                delta.changes.append({"type": "step_added", "step": step_name})
            elif ps and not ns:
                delta.changes.append({"type": "step_removed", "step": step_name})

        return delta

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_calendar(self) -> Dict[str, list]:
        if not self._calendar_path.exists():
            return {}
        try:
            return json.loads(self._calendar_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    @staticmethod
    def _load_run(runs_dir: Path, run_id: str) -> dict:
        run_path = runs_dir / f"{run_id}.json"
        if not run_path.exists():
            return {}
        try:
            return json.loads(run_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------

def _watchlist_tickers(data: Any) -> List[str]:
    """Tickers from a watchlist YAML payload.

    Accepts the shape ``augur watchlist-add`` writes
    (``{"watchlist": [{"ticker": "AAPL", ...}, ...]}``) and the legacy
    ``{"tickers": ["AAPL", ...]}``. Duplicates are dropped, order kept.
    """
    if not isinstance(data, dict):
        return []
    raw: List[Any] = []
    for key in ("watchlist", "tickers"):
        value = data.get(key)
        if isinstance(value, list):
            raw.extend(value)
    tickers: List[str] = []
    for item in raw:
        if isinstance(item, dict):
            item = item.get("ticker")
        if isinstance(item, str) and item.strip():
            t = item.strip().upper()
            if t not in tickers:
                tickers.append(t)
    return tickers


def _is_sec_source(source: Any) -> bool:
    s = str(source or "").lower()
    return s.startswith("sec_") or "edgar" in s


def _bundle_has_sec_evidence(bundle: Dict[str, Any]) -> bool:
    """True when a RunBundle dict holds a non-missing SEC/EDGAR evidence item."""
    for step in bundle.get("step_results", []) or []:
        result = step.get("result") if isinstance(step, dict) else None
        if not isinstance(result, dict):
            continue
        for ev in result.get("evidence_items") or []:
            if isinstance(ev, dict) and _is_sec_source(ev.get("source")) and not ev.get("missing"):
                return True
    return False


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_earnings_service: Optional[EarningsEventService] = None


def get_earnings_service() -> EarningsEventService:
    global _earnings_service
    if _earnings_service is None:
        _earnings_service = EarningsEventService()
    return _earnings_service
