# -*- coding: utf-8 -*-
"""ROADMAP step 18: same-second runs keep their real created_at and order correctly."""

import hashlib
import json
import re
from datetime import datetime, timezone

import pytest

import augur.run_tracker as rt
from augur.run_tracker import RunTracker, latest_run_id, list_run_ids, load_run_bundle_dict
from augur.schemas.run_bundle import RunBundle, generate_run_id
from augur.schemas.step_result import StepStatus

FROZEN = datetime(2026, 10, 29, 12, 0, 0, 0, tzinfo=timezone.utc)
RUN_ID_RE = re.compile(r"^run_[A-Z0-9_.-]+_\d{8}T\d{6}_[a-f0-9]{8}$")


class _FrozenDatetime(datetime):
    """datetime whose now() always returns the same instant (same second, same µs)."""

    @classmethod
    def now(cls, tz=None):
        return FROZEN if tz else FROZEN.replace(tzinfo=None)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"


def _run(ticker: str) -> RunTracker:
    t = RunTracker(ticker=ticker)
    t.start_run(input_snapshot_hash="b" * 64)
    sid = t.start_step("analyze")
    t.finish_step(sid, StepStatus.SUCCESS, result={"ok": True})
    t.finish_run()
    return t


@pytest.mark.parametrize("count", [2, 3])
def test_same_instant_runs_keep_created_at_and_get_distinct_ids(data_dir, monkeypatch, count):
    monkeypatch.setattr(rt, "datetime", _FrozenDatetime)
    trackers = [_run("SAME") for _ in range(count)]

    ids = [t.run_id for t in trackers]
    assert len(set(ids)) == count
    for t in trackers:
        # created_at is the true start time, never pushed forward
        assert t.created_at == FROZEN
        assert RUN_ID_RE.match(t.run_id)
        bundle = load_run_bundle_dict(t.run_id)
        assert datetime.fromisoformat(bundle["created_at"].replace("Z", "+00:00")) == FROZEN
        RunBundle.model_validate(bundle)  # still a valid bundle

    # every id carries the real (shared) timestamp
    assert all("_20261029T120000_" in rid for rid in ids)
    # first run keeps the plain, un-disambiguated id (backward compatible format)
    manifest_hash = hashlib.sha256(
        trackers[0].manifest.model_dump_json(exclude_none=True).encode("utf-8")
    ).hexdigest()
    assert ids[0] == generate_run_id("SAME", FROZEN, manifest_hash)

    # latest-run lookup returns the last started run; full list is newest first
    assert latest_run_id("SAME") == ids[-1]
    assert list_run_ids("SAME") == list(reversed(ids))


def test_latest_run_ignores_id_sort_order(data_dir, monkeypatch):
    """Ids from the same second sort by hash; ordering must not depend on them."""
    monkeypatch.setattr(rt, "datetime", _FrozenDatetime)
    ids = [_run("ORD").run_id for _ in range(3)]
    # Regardless of lexicographic id order, the last-started run wins.
    assert latest_run_id("ORD") == ids[-1]


def test_real_clock_runs_order_by_start(data_dir):
    ids = [_run("REAL").run_id for _ in range(3)]
    assert len(set(ids)) == 3
    assert latest_run_id("REAL") == ids[-1]


def test_legacy_bundle_without_start_seq_still_loads_and_orders(data_dir, monkeypatch):
    # A pre-v12 bundle: plain id, no start_seq, created_at earlier.
    old = _run("LEG")
    path = data_dir / "runs" / f"{old.run_id}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["metadata"].pop("start_seq", None)
    raw["created_at"] = "2020-01-01T00:00:00Z"
    path.write_text(json.dumps(raw), encoding="utf-8")

    assert load_run_bundle_dict(old.run_id)["run_id"] == old.run_id
    new = _run("LEG")
    assert latest_run_id("LEG") == new.run_id
    assert list_run_ids("LEG") == [new.run_id, old.run_id]


def test_resumed_run_keeps_id_created_at_and_seq(data_dir, monkeypatch):
    from augur.run_tracker import _compute_input_snapshot_hash

    h = _compute_input_snapshot_hash("RES", "", "", "")
    t = RunTracker(ticker="RES")
    t.start_run(input_snapshot_hash=h)
    sid = t.start_step("fetch")
    t.finish_step(sid, StepStatus.SUCCESS, result={"ok": True})
    ckpt = t.save_checkpoint()

    r = RunTracker.resume_from_checkpoint(str(ckpt), ticker="RES")
    assert r.start_run(input_snapshot_hash=h) == t.run_id
    assert r.created_at == t.created_at
    assert r.start_seq == t.start_seq
