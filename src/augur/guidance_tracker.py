# -*- coding: utf-8 -*-
"""
Guidance Tracker — structured tracking of management guidance ranges and revisions.

Persists guidance records to ``get_data_dir() / "guidance" /`` as JSON files
keyed by ticker.  Provides comparison, accuracy checking, and conversion to
``EvidenceItem`` for downstream consensus pipelines.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from augur.data_dir import get_data_dir


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class GuidanceRecord:
    """A single management guidance range for one metric/period."""

    ticker: str
    metric: str              # "revenue", "eps", "fcf"
    fiscal_period: str       # "Q4 2025", "FY2025"
    low: float
    high: float
    actual_result: Optional[float] = None  # filled post-hoc
    source_filing: str       # accession number
    published_date: str      # ISO date


# ---------------------------------------------------------------------------
# Guidance Tracker
# ---------------------------------------------------------------------------

class GuidanceTracker:
    """Persistent guidance tracker backed by JSON files under the data dir."""

    _SUBDIR = "guidance"

    def __init__(self, data_dir: Optional[Path] = None):
        self._root = (data_dir or get_data_dir()) / self._SUBDIR
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _file_path(self, ticker: str) -> Path:
        return self._root / f"{ticker.upper()}.json"

    def _load(self, ticker: str) -> List[dict]:
        path = self._file_path(ticker)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, ticker: str, records: List[dict]) -> None:
        path = self._file_path(ticker)
        path.write_text(
            json.dumps(records, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _record_to_dict(self, r: GuidanceRecord) -> dict:
        return {
            "ticker": r.ticker.upper(),
            "metric": r.metric,
            "fiscal_period": r.fiscal_period,
            "low": r.low,
            "high": r.high,
            "actual_result": r.actual_result,
            "source_filing": r.source_filing,
            "published_date": r.published_date,
        }

    def _dict_to_record(self, d: dict) -> GuidanceRecord:
        return GuidanceRecord(
            ticker=d["ticker"],
            metric=d["metric"],
            fiscal_period=d["fiscal_period"],
            low=float(d["low"]),
            high=float(d["high"]),
            actual_result=float(d["actual_result"]) if d.get("actual_result") is not None else None,
            source_filing=d["source_filing"],
            published_date=d["published_date"],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, record: GuidanceRecord) -> None:
        """Persist a guidance record."""
        records = self._load(record.ticker)
        records.append(self._record_to_dict(record))
        self._save(record.ticker, records)

    def get_history(
        self, ticker: str, metric: str
    ) -> List[GuidanceRecord]:
        """Return all guidance records for *ticker* and *metric*, oldest first."""
        records = self._load(ticker)
        return [
            self._dict_to_record(r)
            for r in records
            if r["metric"] == metric
        ]

    def compare(self, ticker: str, metric: str) -> dict:
        """Compare latest vs previous guidance for *ticker*/*metric*.

        Returns a dict with keys:
          - ``direction``: ``"raised"`` | ``"lowered"`` | ``"unchanged"`` | ``"initial"`` | ``"no_history"``
          - ``latest`` / ``previous``: the two ``GuidanceRecord`` dicts (previous may be ``None``)
          - ``midpoint_delta_pct``: percentage change in the midpoint
        """
        history = self.get_history(ticker, metric)
        if len(history) < 1:
            return {
                "direction": "no_history",
                "latest": None,
                "previous": None,
                "midpoint_delta_pct": 0.0,
            }

        latest = history[-1]
        if len(history) < 2:
            return {
                "direction": "initial",
                "latest": self._record_to_dict(latest),
                "previous": None,
                "midpoint_delta_pct": 0.0,
            }

        previous = history[-2]
        prev_mid = (previous.low + previous.high) / 2
        new_mid = (latest.low + latest.high) / 2

        if prev_mid == 0:
            delta_pct = 0.0
        else:
            delta_pct = ((new_mid - prev_mid) / abs(prev_mid)) * 100

        if delta_pct > 2.0:
            direction = "raised"
        elif delta_pct < -2.0:
            direction = "lowered"
        else:
            direction = "unchanged"

        return {
            "direction": direction,
            "latest": self._record_to_dict(latest),
            "previous": self._record_to_dict(previous),
            "midpoint_delta_pct": round(delta_pct, 2),
        }

    def check_accuracy(self, ticker: str, metric: str) -> dict:
        """Evaluate how often past guidance was met or missed.

        Returns a dict:
          - ``total_periods``: number of periods with actual results
          - ``met``: actual fell within [low, high]
          - ``missed``: actual outside the range
          - ``accuracy_pct``: met / total * 100
          - ``periods``: list of {fiscal_period, low, high, actual, was_met}
          - ``avg_deviation_pct``: average absolute deviation from midpoint
        """
        history = self.get_history(ticker, metric)
        periods_with_results = [r for r in history if r.actual_result is not None]

        if not periods_with_results:
            return {
                "total_periods": 0,
                "met": 0,
                "missed": 0,
                "accuracy_pct": 0.0,
                "periods": [],
                "avg_deviation_pct": 0.0,
            }

        met = 0
        missed = 0
        deviations: List[float] = []
        period_details: List[dict] = []

        for r in periods_with_results:
            actual = r.actual_result  # type: ignore[assignment]
            was_met = r.low <= actual <= r.high
            if was_met:
                met += 1
            else:
                missed += 1

            mid = (r.low + r.high) / 2
            if mid != 0:
                dev = abs(actual - mid) / abs(mid) * 100
            else:
                dev = 0.0
            deviations.append(dev)

            period_details.append({
                "fiscal_period": r.fiscal_period,
                "low": r.low,
                "high": r.high,
                "actual": actual,
                "was_met": was_met,
            })

        total = len(periods_with_results)
        avg_dev = sum(deviations) / len(deviations) if deviations else 0.0

        return {
            "total_periods": total,
            "met": met,
            "missed": missed,
            "accuracy_pct": round((met / total) * 100, 1),
            "periods": period_details,
            "avg_deviation_pct": round(avg_dev, 2),
        }

    def to_evidence_items(
        self, ticker: str
    ) -> List[Any]:
        """Convert guidance records to ``EvidenceItem`` objects.

        Each record produces one evidence item with the guidance midpoint
        as the value, tagged with ``metric="guidance_{metric}"``.
        """
        from augur.schemas.evidence import EvidenceItem, generate_evidence_id

        records = self._load(ticker)
        items: List[Any] = []

        for r_dict in records:
            r = self._dict_to_record(r_dict)
            mid = (r.low + r.high) / 2
            raw = json.dumps(r_dict, sort_keys=True)
            content_hash = hashlib.sha256(raw.encode()).hexdigest()

            try:
                pub_date = datetime.fromisoformat(r.published_date)
            except (ValueError, TypeError):
                pub_date = datetime.utcnow()

            item = EvidenceItem(
                evidence_id=generate_evidence_id("sec_edgar", content_hash),
                source="sec_edgar",
                source_locator=r.source_filing,
                content_hash=content_hash,
                instrument=r.ticker,
                metric=f"guidance_{r.metric}",
                value=round(mid, 4),
                unit="USD" if r.metric in ("revenue", "fcf") else "USD_per_share",
                currency="USD",
                effective_at=pub_date,
                available_at=pub_date,
                retrieved_at=datetime.utcnow(),
                metadata={
                    "fiscal_period": r.fiscal_period,
                    "low": r.low,
                    "high": r.high,
                    "actual_result": r.actual_result,
                },
            )
            items.append(item)

        return items
