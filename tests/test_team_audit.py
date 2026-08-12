# -*- coding: utf-8 -*-
"""
tests/test_team_audit.py — H05 Team Audit tests.

Validates the :class:`augur.team_audit.AuditLog` API and its persistence:
  1. ``log()`` produces an entry with action/timestamp/user/details.
  2. Default user is ``"local"`` when omitted.
  3. ``list_by_user()`` filters by user.
  4. ``list_by_action()`` filters by action.
  5. ``recent()`` returns newest-first and honours ``limit``.
  6. Entries persist to disk and survive a new AuditLog instance.
  7. Timestamps are ISO-8601 / timezone-aware.
  8. A corrupt log file loads without crashing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from augur.team_audit import AuditEntry, AuditLog


@pytest.fixture
def audit_log(tmp_path: Path) -> AuditLog:
    """Create an AuditLog pointed at a temporary file."""
    return AuditLog(path=tmp_path / "audit_log.json")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_log_creates_entry_with_fields(audit_log: AuditLog):
    """log() returns an entry carrying action/timestamp/user/details."""
    entry = audit_log.log("analyze", user="alice", details={"ticker": "AAPL"})

    assert isinstance(entry, AuditEntry)
    assert entry.action == "analyze"
    assert entry.user == "alice"
    assert entry.details == {"ticker": "AAPL"}
    assert entry.timestamp  # non-empty


def test_log_default_user_is_local(audit_log: AuditLog):
    """Omitting user defaults to 'local'."""
    entry = audit_log.log("export")
    assert entry.user == "local"


def test_log_records_canonical_actions(audit_log: AuditLog):
    """All documented operation verbs can be recorded."""
    for action in ["analyze", "export", "skill_run", "thesis_create"]:
        audit_log.log(action, user="alice")

    assert len(audit_log.list_by_user("alice")) == 4
    assert [e.action for e in audit_log.list_by_user("alice")] == [
        "analyze",
        "export",
        "skill_run",
        "thesis_create",
    ]


def test_list_by_user_filters(audit_log: AuditLog):
    """list_by_user() returns only entries for the given user."""
    audit_log.log("analyze", user="alice", details={"ticker": "AAPL"})
    audit_log.log("export", user="bob")
    audit_log.log("analyze", user="alice", details={"ticker": "MSFT"})

    alice = audit_log.list_by_user("alice")
    bob = audit_log.list_by_user("bob")

    assert len(alice) == 2
    assert all(e.user == "alice" for e in alice)
    assert len(bob) == 1
    assert bob[0].action == "export"


def test_list_by_action_filters(audit_log: AuditLog):
    """list_by_action() returns only entries matching the action verb."""
    audit_log.log("analyze", user="alice")
    audit_log.log("export", user="bob")
    audit_log.log("analyze", user="carol")

    analyzes = audit_log.list_by_action("analyze")
    exports = audit_log.list_by_action("export")

    assert len(analyzes) == 2
    assert all(e.action == "analyze" for e in analyzes)
    assert len(exports) == 1
    assert exports[0].user == "bob"


def test_recent_returns_newest_first_and_limits(audit_log: AuditLog):
    """recent() honours limit and returns most recent first."""
    for i in range(5):
        audit_log.log("skill_run", user="alice", details={"run": i})

    recent_two = audit_log.recent(2)

    assert len(recent_two) == 2
    # Newest entry (run=4) should come first.
    assert recent_two[0].details["run"] == 4
    assert recent_two[1].details["run"] == 3


def test_entries_persist_across_instances(audit_log: AuditLog, tmp_path: Path):
    """Entries written by one instance are visible to a fresh instance."""
    audit_log.log("thesis_create", user="alice", details={"ticker": "NVDA"})
    audit_log.log("export", user="bob")

    path = tmp_path / "audit_log.json"
    reloaded = AuditLog(path=path)

    assert len(reloaded.recent(10)) == 2
    assert reloaded.list_by_action("thesis_create")[0].details == {"ticker": "NVDA"}
    assert reloaded.list_by_user("bob")[0].action == "export"


def test_timestamp_is_iso_and_timezone_aware(audit_log: AuditLog):
    """Timestamps parse as datetime and carry a UTC offset."""
    entry = audit_log.log("analyze", user="alice")

    ts = datetime.fromisoformat(entry.timestamp)
    assert ts.tzinfo is not None  # timezone-aware
    assert ts.tzinfo.utcoffset(ts) is not None


def test_corrupt_file_loads_without_crash(tmp_path: Path):
    """A malformed log file is treated as empty rather than raising."""
    path = tmp_path / "audit_log.json"
    path.write_text("{ not valid json", encoding="utf-8")

    audit = AuditLog(path=path)

    assert audit.recent(10) == []
    assert audit.list_by_user("alice") == []
    # A subsequent write should overwrite the corrupt file cleanly.
    audit.log("analyze", user="alice")
    assert len(audit.recent(10)) == 1


def test_persistence_file_is_valid_json(audit_log: AuditLog, tmp_path: Path):
    """The on-disk file is a JSON array of entry objects."""
    audit_log.log("analyze", user="alice", details={"ticker": "AAPL"})

    path = tmp_path / "audit_log.json"
    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["action"] == "analyze"
    assert data[0]["user"] == "alice"
    assert data[0]["details"] == {"ticker": "AAPL"}
    assert "timestamp" in data[0]
