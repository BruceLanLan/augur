# -*- coding: utf-8 -*-
"""
tests/test_run_tracker.py — E1.2 RunTracker tests.

Validates:
  1. Round-trip: create RunTracker → add steps → generate RunBundle → validate.
  2. Checkpoint save → resume → verify completed steps are skipped.
  3. Input hash mismatch → checkpoint resume rejected.
  4. RunBundle persisted to get_data_dir()/"runs"/.
  5. Checkpoint persisted to get_data_dir()/"checkpoints"/.
  6. StepResult content_hash computed correctly.
  7. Coverage stats computed from step results.
  8. StepResult rejects plain-string results.
  9. run_workflow produces run_id and run_bundle_path when track=True.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from augur.data_dir import get_data_dir
from augur.run_tracker import RunTracker, _compute_input_snapshot_hash
from augur.schemas.run_bundle import (
    CoverageStats,
    RunBundle,
    RunManifest,
    generate_run_id,
)
from augur.schemas.step_result import StepResult, StepStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Test: input_snapshot_hash is deterministic
# ---------------------------------------------------------------------------

def test_input_snapshot_hash_deterministic():
    """Same inputs produce the same hash."""
    h1 = _compute_input_snapshot_hash("AAPL", "fetch,analyze", "", "")
    h2 = _compute_input_snapshot_hash("AAPL", "fetch,analyze", "", "")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_input_snapshot_hash_different_inputs():
    """Different inputs produce different hashes."""
    h1 = _compute_input_snapshot_hash("AAPL", "fetch", "", "")
    h2 = _compute_input_snapshot_hash("AAPL", "fetch,analyze", "", "")
    assert h1 != h2


def test_input_snapshot_hash_ticker_normalized():
    """Ticker is uppercased before hashing."""
    h1 = _compute_input_snapshot_hash("aapl", "", "", "")
    h2 = _compute_input_snapshot_hash("AAPL", "", "", "")
    assert h1 == h2


# ---------------------------------------------------------------------------
# Test: RunTracker lifecycle (create → steps → bundle)
# ---------------------------------------------------------------------------

def test_tracker_lifecycle():
    """Full lifecycle: start_run → start_step → finish_step → finish_run."""
    tracker = RunTracker(ticker="AAPL")
    run_id = tracker.start_run(
        input_snapshot_hash=_sha256("test-inputs")
    )

    assert run_id.startswith("run_AAPL_")
    assert tracker.run_id == run_id
    assert tracker.manifest is not None
    assert tracker.manifest.input_snapshot_hash == _sha256("test-inputs")

    # Add a fetch step
    sid = tracker.start_step("fetch")
    assert sid.startswith(run_id + "_step")

    sr = tracker.finish_step(
        sid,
        StepStatus.SUCCESS,
        result={"price": 150.0, "pe": 25.0},
    )
    assert sr.step_name == "fetch"
    assert sr.status == StepStatus.SUCCESS
    assert sr.result == {"price": 150.0, "pe": 25.0}
    assert sr.elapsed_ms is not None
    assert sr.elapsed_ms >= 0
    assert sr.content_hash is not None
    assert sr.started_at is not None
    assert sr.finished_at is not None

    # Add an analyze step
    sid2 = tracker.start_step("analyze", input_refs=["ev_test_abc123456789"])
    sr2 = tracker.finish_step(
        sid2,
        StepStatus.SUCCESS,
        result={"agents": 18, "bullish": 12},
    )
    assert sr2.step_name == "analyze"
    assert sr2.input_refs == ["ev_test_abc123456789"]

    # Finish run
    bundle = tracker.finish_run()
    assert isinstance(bundle, RunBundle)
    assert bundle.run_id == run_id
    assert len(bundle.step_results) == 2
    assert bundle.coverage.total_evidence == 2
    assert bundle.coverage.covered_evidence == 2
    assert bundle.coverage.coverage_ratio == 1.0

    # Bundle is persisted
    runs_dir = get_data_dir() / "runs"
    bundle_path = runs_dir / f"{run_id}.json"
    assert bundle_path.exists()

    # Round-trip: read back and validate
    reloaded = RunBundle.model_validate(
        json.loads(bundle_path.read_text("utf-8"))
    )
    assert reloaded.run_id == run_id
    assert len(reloaded.step_results) == 2


def test_tracker_failure_and_degraded_steps():
    """Coverage stats correctly count failures and degraded steps."""
    tracker = RunTracker(ticker="MSFT")
    tracker.start_run(input_snapshot_hash=_sha256("test"))

    # Success
    sid = tracker.start_step("fetch")
    tracker.finish_step(sid, StepStatus.SUCCESS, result={"ok": True})

    # Failure
    sid2 = tracker.start_step("analyze")
    tracker.finish_step(sid2, StepStatus.FAILURE, diagnostics="timeout")

    # Degraded
    sid3 = tracker.start_step("consensus")
    tracker.finish_step(sid3, StepStatus.DEGRADED, result={"partial": True})

    bundle = tracker.finish_run()
    assert bundle.coverage.total_evidence == 3
    assert bundle.coverage.covered_evidence == 1
    assert bundle.coverage.missing_evidence == 1  # FAILURE counts as missing
    assert bundle.coverage.degraded_evidence == 1
    assert bundle.coverage.coverage_ratio == 1.0 / 3.0


def test_finish_run_before_start_raises():
    """finish_run() before start_run() raises RuntimeError."""
    tracker = RunTracker(ticker="AAPL")
    with pytest.raises(RuntimeError, match="start_run"):
        tracker.finish_run()


def test_finish_step_not_found_raises():
    """finish_step with unknown step_id raises ValueError."""
    tracker = RunTracker(ticker="AAPL")
    tracker.start_run(input_snapshot_hash=_sha256("test"))
    with pytest.raises(ValueError, match="not found"):
        tracker.finish_step("nonexistent", StepStatus.SUCCESS)


def test_step_result_rejects_plain_string():
    """StepResult validator rejects a plain string result."""
    tracker = RunTracker(ticker="AAPL")
    tracker.start_run(input_snapshot_hash=_sha256("test"))
    sid = tracker.start_step("fetch")

    with pytest.raises(ValueError, match="not a plain string"):
        tracker.finish_step(sid, StepStatus.SUCCESS, result="just a string")


# ---------------------------------------------------------------------------
# Test: Checkpoint save / resume
# ---------------------------------------------------------------------------

def test_checkpoint_save_and_resume():
    """Save a checkpoint, resume, and verify completed steps are tracked."""
    tracker = RunTracker(ticker="AAPL")
    input_hash = _compute_input_snapshot_hash("AAPL", "fetch,analyze", "", "")
    tracker.start_run(input_snapshot_hash=input_hash)

    # Complete fetch
    sid = tracker.start_step("fetch")
    tracker.finish_step(sid, StepStatus.SUCCESS, result={"price": 150.0})
    tracker.save_checkpoint()

    # Complete analyze
    sid2 = tracker.start_step("analyze")
    tracker.finish_step(sid2, StepStatus.SUCCESS, result={"agents": 18})
    ckpt_path = tracker.save_checkpoint()

    assert ckpt_path.exists()

    # Now resume from checkpoint
    resumed = RunTracker.resume_from_checkpoint(
        str(ckpt_path),
        ticker="AAPL",
        steps="fetch,analyze",
        agents="",
        question="",
    )

    assert resumed.is_step_completed("fetch") is True
    assert resumed.is_step_completed("analyze") is True
    assert resumed.is_step_completed("consensus") is False
    assert len(resumed.step_results) == 2

    # Verify the restored step results
    fetch_sr = resumed.step_results[0]
    assert fetch_sr.step_name == "fetch"
    assert fetch_sr.status == StepStatus.SUCCESS
    assert fetch_sr.result == {"price": 150.0}

    analyze_sr = resumed.step_results[1]
    assert analyze_sr.step_name == "analyze"
    assert analyze_sr.status == StepStatus.SUCCESS


def test_checkpoint_resume_rejects_input_change():
    """Resume with different inputs raises ValueError."""
    tracker = RunTracker(ticker="AAPL")
    input_hash = _compute_input_snapshot_hash(
        "AAPL", "fetch", "buffett", ""
    )
    tracker.start_run(input_snapshot_hash=input_hash)
    sid = tracker.start_step("fetch")
    tracker.finish_step(sid, StepStatus.SUCCESS, result={"price": 150.0})
    ckpt_path = tracker.save_checkpoint()

    # Try to resume with different agents
    with pytest.raises(ValueError, match="Input snapshot hash mismatch"):
        RunTracker.resume_from_checkpoint(
            str(ckpt_path),
            ticker="AAPL",
            steps="fetch",
            agents="munger",  # different!
            question="",
        )


def test_checkpoint_resume_file_not_found():
    """Resume from a nonexistent path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found"):
        RunTracker.resume_from_checkpoint(
            "/nonexistent/path.checkpoint.json",
            ticker="AAPL",
        )


def test_checkpoint_resume_skips_failed_steps():
    """Failed steps are NOT marked as completed — they should be re-run."""
    tracker = RunTracker(ticker="AAPL")
    input_hash = _compute_input_snapshot_hash("AAPL", "fetch,analyze", "", "")
    tracker.start_run(input_snapshot_hash=input_hash)

    # fetch succeeds
    sid = tracker.start_step("fetch")
    tracker.finish_step(sid, StepStatus.SUCCESS, result={"price": 150.0})

    # analyze fails
    sid2 = tracker.start_step("analyze")
    tracker.finish_step(sid2, StepStatus.FAILURE, diagnostics="timeout")

    ckpt_path = tracker.save_checkpoint()

    resumed = RunTracker.resume_from_checkpoint(
        str(ckpt_path),
        ticker="AAPL",
        steps="fetch,analyze",
        agents="",
        question="",
    )

    # fetch should be completed, analyze should NOT
    assert resumed.is_step_completed("fetch") is True
    assert resumed.is_step_completed("analyze") is False


def test_checkpoint_state_persistence():
    """Intermediate checkpoint state is saved and restored."""
    tracker = RunTracker(ticker="AAPL")
    input_hash = _compute_input_snapshot_hash("AAPL", "fetch", "", "")
    tracker.start_run(input_snapshot_hash=input_hash)

    tracker.set_checkpoint_state("ctx", {"price": 150.0, "pe": 25.0})
    tracker.set_checkpoint_state("responses", {"buffett": {"signal": "bullish"}})

    sid = tracker.start_step("fetch")
    tracker.finish_step(sid, StepStatus.SUCCESS, result={"price": 150.0})
    ckpt_path = tracker.save_checkpoint()

    resumed = RunTracker.resume_from_checkpoint(
        str(ckpt_path),
        ticker="AAPL",
        steps="fetch",
        agents="",
        question="",
    )

    assert resumed.get_checkpoint_state("ctx") == {"price": 150.0, "pe": 25.0}
    assert resumed.get_checkpoint_state("responses") == {
        "buffett": {"signal": "bullish"}
    }
    assert resumed.get_checkpoint_state("nonexistent", "default") == "default"


# ---------------------------------------------------------------------------
# Test: run_workflow integration (track=True)
# ---------------------------------------------------------------------------

def test_run_workflow_produces_run_id():
    """run_workflow with track=True produces run_id and run_bundle_path."""
    from unittest.mock import MagicMock, patch

    from augur.personas.base import MarketContext

    # Use a real MarketContext so dataclasses.asdict() works for checkpointing
    ctx = MarketContext(ticker="AAPL", price=150.0, pe=25.0,
                        sector="Technology", industry="Consumer Electronics")

    # We mock the heavy parts so the test runs fast and offline
    with patch("augur.data.fetch_market_context", return_value=ctx) as mock_fetch, \
         patch("augur.registry.AgentRegistry") as mock_registry_cls, \
         patch("augur.registry.DecisionCoordinator") as mock_coord_cls:

        # Setup mock registry
        mock_registry = MagicMock()
        mock_registry.get_all.return_value = []
        mock_registry_cls.return_value = mock_registry

        # Setup mock coordinator
        mock_coord = MagicMock()
        mock_coord_cls.return_value = mock_coord

        # Mock analyze_with_all to return an empty dict (skips analyze)
        mock_coord.analyze_with_all.return_value = {}

        from augur.workflow import run_workflow

        result = run_workflow("AAPL", steps="fetch", track=True)

        assert "run_id" in result
        assert result["run_id"].startswith("run_AAPL_")
        assert "run_bundle_path" in result
        assert "fetch" in result["results"]
        assert result["results"]["fetch"]["price"] == 150.0

        # Verify RunBundle was persisted
        bundle_path = Path(result["run_bundle_path"])
        assert bundle_path.exists()


def test_run_workflow_track_false_no_bundle():
    """run_workflow with track=False does NOT produce run_id."""
    from unittest.mock import patch

    from augur.personas.base import MarketContext

    ctx = MarketContext(ticker="AAPL", price=150.0, pe=25.0,
                        sector="Technology", industry="Consumer Electronics")

    with patch("augur.data.fetch_market_context", return_value=ctx):

        from augur.workflow import run_workflow

        result = run_workflow("AAPL", steps="fetch", track=False)

        assert "run_id" not in result
        assert "run_bundle_path" not in result
        assert result["results"]["fetch"]["price"] == 150.0


def test_run_workflow_analyze_tracked():
    """run_workflow with analyze step produces proper StepResult."""
    from unittest.mock import MagicMock, patch

    from augur.personas.base import MarketContext

    ctx = MarketContext(ticker="AAPL", price=150.0, pe=25.0,
                        sector="Tech", industry="Electronics")

    with patch("augur.data.fetch_market_context", return_value=ctx), \
         patch("augur.registry.AgentRegistry") as mock_reg_cls, \
         patch("augur.registry.DecisionCoordinator") as mock_coord_cls:

        mock_reg = MagicMock()
        mock_reg.get_all.return_value = []
        mock_reg_cls.return_value = mock_reg

        # Create mock agent responses
        from augur.personas.base import AgentResponse, SignalType

        mock_resp = AgentResponse(
            agent_id="buffett",
            agent_name="Warren Buffett",
            signal=SignalType.BULLISH,
            confidence=0.8,
            score=7.5,
            reasoning="Good value",
        )
        mock_coord = MagicMock()
        mock_coord.analyze_with_all.return_value = {"buffett": mock_resp}
        mock_coord_cls.return_value = mock_coord

        from augur.workflow import run_workflow

        result = run_workflow(
            "AAPL", steps="fetch,analyze", track=True
        )

        assert "run_id" in result
        assert "analyze" in result["results"]
        assert result["results"]["analyze"]["buffett"]["signal"] == "bullish"
        assert result["results"]["analyze"]["buffett"]["score"] == 7.5


# ---------------------------------------------------------------------------
# Test: RunBundle round-trip validates with all fields
# ---------------------------------------------------------------------------

def test_run_bundle_full_round_trip():
    """RunBundle with multiple step types round-trips correctly."""
    now = datetime.now(timezone.utc)
    manifest = RunManifest(
        input_snapshot_hash=_sha256("snapshot"),
        config_version="1.0",
        model_version="2.0",
        code_version="11.0.0",
    )
    manifest_hash = hashlib.sha256(
        manifest.model_dump_json(exclude_none=True).encode("utf-8")
    ).hexdigest()
    run_id = generate_run_id("TSLA", now, manifest_hash)

    steps = [
        StepResult(
            step_id=f"{run_id}_step1",
            step_name="fetch",
            status=StepStatus.SUCCESS,
            result={"price": 250.0},
            elapsed_ms=100.0,
            content_hash=_sha256('{"price":250.0}'),
            started_at=now,
            finished_at=now,
        ),
        StepResult(
            step_id=f"{run_id}_step2",
            step_name="analyze",
            status=StepStatus.SUCCESS,
            result={"agents": 18},
            elapsed_ms=500.0,
            started_at=now,
            finished_at=now,
        ),
        StepResult(
            step_id=f"{run_id}_step3",
            step_name="consensus",
            status=StepStatus.DEGRADED,
            result={"partial": True},
            diagnostics="low participation",
            elapsed_ms=50.0,
        ),
    ]

    coverage = CoverageStats(
        total_evidence=3,
        covered_evidence=2,
        missing_evidence=0,
        degraded_evidence=1,
        coverage_ratio=2.0 / 3.0,
    )

    bundle = RunBundle(
        run_id=run_id,
        created_at=now,
        manifest=manifest,
        step_results=steps,
        coverage=coverage,
        metadata={"trigger": "test"},
    )

    # Serialise and reload
    reloaded = RunBundle.model_validate(bundle.model_dump())
    assert reloaded.run_id == run_id
    assert len(reloaded.step_results) == 3
    assert reloaded.coverage.degraded_evidence == 1
    assert reloaded.metadata == {"trigger": "test"}

    # Verify the run_id matches the expected pattern
    import re
    assert re.match(r"^run_[A-Z0-9_.-]+_\d{8}T\d{6}_[a-f0-9]{8}$", run_id)
