# -*- coding: utf-8 -*-
"""Live-shaped evidence must survive the tracked workflow.

Regression for two bugs found by running the README quickstart from a
fresh wheel install (2026-09-17):

1. ``augur workflow TSLA`` failed with "Object of type datetime is not JSON
   serializable". Real providers attach ``evidence_items`` carrying datetime
   values to ``MarketContext``; ``run_workflow`` stores ``asdict(ctx)`` in the
   checkpoint and ``RunTracker.save_checkpoint`` passed it straight to
   ``json.dumps``. Existing tests built contexts without evidence, so the
   path was never exercised.
2. ``fetch_market_context`` stamped ``available_at`` with naive local time
   while ``retrieved_at`` is UTC-aware, so in any UTC+N timezone evidence
   appeared to become available *after* it was retrieved — the opposite of
   what the no-lookahead contract needs.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from augur.datasources.base import DataProvider


class _LiveShapedProvider(DataProvider):
    name = "mock_live"

    def fetch(self, ticker):
        return {
            "data_source": "mock_live",
            "price": 150.0,
            "pe": 20.0,
            "roe": 0.18,
            "gross_margins": 0.45,
            "revenue_growth": 0.15,
            "market_cap": 500.0,
        }


@pytest.fixture
def live_provider(monkeypatch):
    import augur.data as data_module

    # fetch_market_context caches contexts for 3 minutes across tests

    data_module.clear_cache()

    monkeypatch.setattr(data_module, "_get_providers", lambda: [_LiveShapedProvider()])
    # Consensus otherwise pulls live VIX/SPY history for regime detection.
    monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")
    return data_module


def test_evidence_timestamps_are_utc_aware_and_not_after_retrieval(live_provider):
    ctx = live_provider.fetch_market_context("AAPL", force_refresh=True)

    assert ctx.evidence_items, "provider should have produced evidence items"
    for ev in ctx.evidence_items:
        available_at = ev["available_at"]
        retrieved_at = ev["retrieved_at"]
        assert isinstance(available_at, datetime)
        assert available_at.tzinfo is not None, f"naive available_at on {ev['metric']}"
        assert retrieved_at.tzinfo is not None, f"naive retrieved_at on {ev['metric']}"
        assert available_at <= retrieved_at, (
            f"{ev['metric']}: available_at {available_at} is after retrieved_at {retrieved_at}"
        )


def test_tracked_workflow_checkpoints_live_evidence(live_provider):
    from augur.data_dir import get_data_dir
    from augur.workflow import run_workflow

    result = run_workflow("AAPL", steps="fetch,analyze,consensus")

    assert "error" not in result.get("results", {}).get("fetch", {})
    run_id = result["run_id"]
    ckpt = Path(get_data_dir()) / "checkpoints" / f"{run_id}.checkpoint.json"
    assert ckpt.exists(), "workflow should have written a checkpoint"
    state = json.loads(ckpt.read_text(encoding="utf-8"))["_checkpoint_state"]
    assert state["ctx"]["evidence_items"], "checkpoint should carry the evidence"


def test_workflow_resumes_from_checkpoint_with_live_evidence(live_provider, monkeypatch):
    from augur.data_dir import get_data_dir
    from augur.workflow import run_workflow

    import time

    first = run_workflow("AAPL", steps="fetch,analyze,consensus")
    ckpt = Path(get_data_dir()) / "checkpoints" / f"{first['run_id']}.checkpoint.json"
    time.sleep(1.1)  # run ids have one-second resolution; resuming must not mint a new one

    # A resumed run must not refetch: make any provider call fail loudly.
    def _no_network():
        raise AssertionError("resume should restore ctx from the checkpoint")

    monkeypatch.setattr(live_provider, "_get_providers", _no_network)
    resumed = run_workflow("AAPL", steps="fetch,analyze,consensus", resume_from=str(ckpt))

    assert resumed["run_id"] == first["run_id"]
    assert resumed["results"]["consensus"]["score"] == pytest.approx(
        first["results"]["consensus"]["score"]
    )


def test_save_checkpoint_serialises_datetime_state(tmp_path):
    from augur.run_tracker import RunTracker

    tracker = RunTracker(ticker="AAPL")
    tracker.start_run(input_snapshot_hash="0" * 64)
    moment = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
    tracker.set_checkpoint_state("ctx", {"evidence_items": [{"retrieved_at": moment}]})

    path = tracker.save_checkpoint(str(tmp_path / "ckpt.json"))

    data = json.loads(path.read_text(encoding="utf-8"))
    stored = data["_checkpoint_state"]["ctx"]["evidence_items"][0]["retrieved_at"]
    assert datetime.fromisoformat(stored) == moment
