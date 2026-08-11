# -*- coding: utf-8 -*-
"""
Research Inbox — event queue aggregating items that need user attention.

Surfaces earnings events, filing deltas, thesis reviews, guidance changes,
and risk alerts into a unified priority-ordered inbox backed by JSON files
under ``get_data_dir() / "inbox" /``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from augur.data_dir import get_data_dir


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class InboxItem:
    """A single item in the research inbox."""

    item_id: str             # ib_{hash[:8]}
    item_type: str           # "earnings_event" | "filing_delta" | "thesis_review" | "guidance_change" | "risk_alert"
    ticker: str
    title: str
    description: str
    priority: str            # "high" | "medium" | "low"
    created_at: str          # ISO timestamp
    dismissed: bool = False
    action_link: str = ""    # clickable action link


# ---------------------------------------------------------------------------
# Research Inbox
# ---------------------------------------------------------------------------

class ResearchInbox:
    """Persistent research inbox backed by a single JSON file."""

    _SUBDIR = "inbox"
    _FILENAME = "items.json"

    def __init__(self, data_dir: Optional[Path] = None):
        self._root = (data_dir or get_data_dir()) / self._SUBDIR
        self._root.mkdir(parents=True, exist_ok=True)
        self._file = self._root / self._FILENAME

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_all(self) -> List[dict]:
        if not self._file.exists():
            return []
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_all(self, items: List[dict]) -> None:
        self._file.write_text(
            json.dumps(items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _item_to_dict(item: InboxItem) -> dict:
        return {
            "item_id": item.item_id,
            "item_type": item.item_type,
            "ticker": item.ticker.upper(),
            "title": item.title,
            "description": item.description,
            "priority": item.priority,
            "created_at": item.created_at,
            "dismissed": item.dismissed,
            "action_link": item.action_link,
        }

    @staticmethod
    def _dict_to_item(d: dict) -> InboxItem:
        return InboxItem(
            item_id=d["item_id"],
            item_type=d["item_type"],
            ticker=d["ticker"],
            title=d["title"],
            description=d["description"],
            priority=d["priority"],
            created_at=d["created_at"],
            dismissed=d.get("dismissed", False),
            action_link=d.get("action_link", ""),
        )

    @staticmethod
    def _generate_id(ticker: str, title: str, created_at: str) -> str:
        raw = f"{ticker.upper()}:{title}:{created_at}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:8]
        return f"ib_{h}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, item: InboxItem) -> str:
        """Persist an inbox item.  Generates ``item_id`` if empty."""
        if not item.item_id:
            item.item_id = self._generate_id(
                item.ticker, item.title, item.created_at
            )

        items = self._load_all()
        items.append(self._item_to_dict(item))
        self._save_all(items)
        return item.item_id

    def list(
        self,
        ticker: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 20,
    ) -> List[InboxItem]:
        """List non-dismissed inbox items, optionally filtered.

        Results are ordered by priority (high → medium → low), then by
        ``created_at`` descending within each priority bucket.
        """
        all_items = [self._dict_to_item(d) for d in self._load_all()]
        # Filter dismissed
        visible = [it for it in all_items if not it.dismissed]

        if ticker:
            visible = [it for it in visible if it.ticker == ticker.upper()]
        if priority:
            visible = [it for it in visible if it.priority == priority]

        # Sort: priority first, then newest first
        _prio_order = {"high": 0, "medium": 1, "low": 2}

        visible.sort(
            key=lambda it: (_prio_order.get(it.priority, 99), it.created_at),
            reverse=False,
        )
        # high priority first, then newest first within same priority
        # Actually we want high first, then by created_at descending
        visible.sort(
            key=lambda it: (_prio_order.get(it.priority, 99), it.created_at),
        )
        # Reverse created_at within each priority bucket
        from itertools import groupby
        result: List[InboxItem] = []
        for _prio, group in groupby(
            visible, key=lambda it: _prio_order.get(it.priority, 99)
        ):
            bucket = list(group)
            bucket.sort(key=lambda it: it.created_at, reverse=True)
            result.extend(bucket)

        return result[:limit]

    def dismiss(self, item_id: str) -> None:
        """Mark an inbox item as dismissed."""
        items = self._load_all()
        for d in items:
            if d["item_id"] == item_id:
                d["dismissed"] = True
                break
        self._save_all(items)

    def count_unread(self) -> int:
        """Return the number of non-dismissed inbox items."""
        items = self._load_all()
        return sum(1 for d in items if not d.get("dismissed", False))

    # ------------------------------------------------------------------
    # Event generation
    # ------------------------------------------------------------------

    def generate_from_events(
        self,
        earnings_events: Optional[List[Any]] = None,
        filing_deltas: Optional[List[Any]] = None,
        thesis_reviews: Optional[List[Any]] = None,
    ) -> List[InboxItem]:
        """Generate inbox items from external event feeds.

        Each argument is an optional iterable of domain objects:
          - *earnings_events*: objects with ``ticker``, ``event_date``, ``fiscal_period``
          - *filing_deltas*: objects with ``ticker``, ``new_accession``, ``overall_assessment``
          - *thesis_reviews*: objects with ``ticker``, ``status``

        Existing items with the same ``(ticker, item_type)`` are **not** duplicated.
        """
        now = datetime.utcnow().isoformat()
        existing_keys = {
            (d["ticker"], d["item_type"]) for d in self._load_all()
        }
        new_items: List[InboxItem] = []

        def _is_new(ticker: str, item_type: str) -> bool:
            return (ticker.upper(), item_type) not in existing_keys

        # Earnings events
        for ev in (earnings_events or []):
            ticker = getattr(ev, "ticker", "")
            event_date = getattr(ev, "event_date", "")
            fiscal_period = getattr(ev, "fiscal_period", "")
            if not _is_new(ticker, "earnings_event"):
                continue
            item = InboxItem(
                item_id="",
                item_type="earnings_event",
                ticker=ticker,
                title=f"{ticker} {fiscal_period} Earnings",
                description=(
                    f"Upcoming earnings for {ticker} "
                    f"({fiscal_period}) on {event_date}"
                ),
                priority="high",
                created_at=now,
            )
            item.item_id = self._generate_id(item.ticker, item.title, item.created_at)
            new_items.append(item)
            existing_keys.add((ticker.upper(), "earnings_event"))

        # Filing deltas
        for fd in (filing_deltas or []):
            ticker = getattr(fd, "ticker", "")
            assessment = getattr(fd, "overall_assessment", "")
            accession = getattr(fd, "new_accession", "")
            if not _is_new(ticker, "filing_delta"):
                continue
            priority = (
                "high" if assessment == "significant_changes"
                else "medium" if assessment == "minor_changes"
                else "low"
            )
            item = InboxItem(
                item_id="",
                item_type="filing_delta",
                ticker=ticker,
                title=f"{ticker} Filing Delta: {assessment}",
                description=(
                    f"Material changes detected in {ticker} filing "
                    f"(accession {accession})"
                ),
                priority=priority,
                created_at=now,
            )
            item.item_id = self._generate_id(item.ticker, item.title, item.created_at)
            new_items.append(item)
            existing_keys.add((ticker.upper(), "filing_delta"))

        # Thesis reviews
        for tr in (thesis_reviews or []):
            ticker = getattr(tr, "ticker", "")
            status = getattr(tr, "status", "pending")
            if not _is_new(ticker, "thesis_review"):
                continue
            item = InboxItem(
                item_id="",
                item_type="thesis_review",
                ticker=ticker,
                title=f"{ticker} Thesis Review",
                description=(
                    f"Thesis review for {ticker} is due (status: {status})"
                ),
                priority="medium",
                created_at=now,
            )
            item.item_id = self._generate_id(item.ticker, item.title, item.created_at)
            new_items.append(item)
            existing_keys.add((ticker.upper(), "thesis_review"))

        # Persist new items
        if new_items:
            all_items = self._load_all()
            for item in new_items:
                all_items.append(self._item_to_dict(item))
            self._save_all(all_items)

        return new_items
