# -*- coding: utf-8 -*-
"""
augur.team_audit — Team Audit log (H05).

A small, shared action log for multi-user accountability. Records every
significant operation (``analyze``, ``export``, ``skill_run``,
``thesis_create``, …) with who did it and when, persisted to a single JSON
file under ``get_data_dir()``.

Typical usage::

    from augur.team_audit import AuditLog

    audit = AuditLog()
    audit.log("analyze", user="alice", details={"ticker": "AAPL"})
    audit.log("export", user="bob", details={"format": "csv"})

    audit.list_by_user("alice")
    audit.list_by_action("export")
    audit.recent(10)

Persistence:
    Entries are stored as a JSON array at ``get_data_dir()/audit_log.json``.
    The path can be overridden via the ``AUGUR_DATA_DIR`` environment variable
    (see :mod:`augur.data_dir`), or injected directly for tests via the
    ``path`` argument.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from augur.data_dir import get_data_dir

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


@dataclass
class AuditEntry:
    """A single audit-log record.

    Attributes:
        action:    Short verb identifying the operation
                   (``analyze``, ``export``, ``skill_run``, ``thesis_create``, …).
        timestamp: ISO-8601 UTC timestamp when the entry was recorded.
        user:      Who performed the action (defaults to ``"local"``).
        details:   Arbitrary extra context (ticker, format, skill name, …).
    """

    action: str
    timestamp: str
    user: str = "local"
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Build an entry from a parsed JSON object (lenient on missing keys)."""
        return cls(
            action=str(data.get("action", "")),
            timestamp=str(data.get("timestamp", "")),
            user=str(data.get("user", "local")),
            details=dict(data.get("details") or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for JSON persistence."""
        return asdict(self)


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------


class AuditLog:
    """Append-only audit log persisted to a single JSON file.

    Loads existing entries on construction and writes the full list back to
    disk on every :meth:`log`, keeping a small in-memory cache. A reentrant
    lock guards the file so concurrent writers do not corrupt it.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path) if path is not None else get_data_dir() / "audit_log.json"
        self._entries: List[AuditEntry] = []
        self._lock = threading.RLock()
        self._load()

    # -- write ---------------------------------------------------------------

    def log(
        self,
        action: str,
        user: str = "local",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record one action and persist it.

        Args:
            action:  Operation verb, e.g. ``"analyze"``, ``"export"``,
                     ``"skill_run"`` or ``"thesis_create"``.
            user:    Who performed the action.
            details: Optional free-form context dict.

        Returns:
            The newly created :class:`AuditEntry`.
        """
        entry = AuditEntry(
            action=action,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user=user or "local",
            details=dict(details or {}),
        )
        with self._lock:
            self._entries.append(entry)
            self._save()
        return entry

    # -- query ---------------------------------------------------------------

    def list_by_user(self, user: str) -> List[AuditEntry]:
        """Return all entries performed by ``user`` (chronological order)."""
        with self._lock:
            return [e for e in self._entries if e.user == user]

    def list_by_action(self, action: str) -> List[AuditEntry]:
        """Return all entries matching ``action`` (chronological order)."""
        with self._lock:
            return [e for e in self._entries if e.action == action]

    def recent(self, limit: int = 20) -> List[AuditEntry]:
        """Return the most recent ``limit`` entries, newest first."""
        with self._lock:
            return list(reversed(self._entries[-limit:]))

    # -- persistence ---------------------------------------------------------

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [e.to_dict() for e in self._entries]
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # Corrupt or unreadable file: start fresh rather than crash.
            self._entries = []
            return
        if not isinstance(raw, list):
            self._entries = []
            return
        self._entries = [AuditEntry.from_dict(item) for item in raw if isinstance(item, dict)]
