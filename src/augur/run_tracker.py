# -*- coding: utf-8 -*-
"""
augur.run_tracker — StepResult wrapper and RunBundle lifecycle (E1.2).

Provides ``RunTracker``, a context manager that wraps ``run_workflow``
execution with structured step tracking, checkpoint save/resume, and
immutable RunBundle generation.

Usage inside ``run_workflow``::

    tracker = RunTracker(ticker, config_version="1.0", ...)
    tracker.start_run(input_snapshot_hash=...)

    sid = tracker.start_step("fetch", input_refs=[])
    # ... do fetch ...
    tracker.finish_step(sid, StepStatus.SUCCESS, result={...})
    tracker.save_checkpoint()

    # ... more steps ...

    bundle = tracker.finish_run()  # persists to get_data_dir()/"runs"/
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from augur.data_dir import get_data_dir
from augur.schemas.run_bundle import (
    CoverageStats,
    RunBundle,
    RunManifest,
    generate_run_id,
)
from augur.schemas.step_result import StepResult, StepStatus


def _compute_input_snapshot_hash(
    ticker: str,
    steps: str,
    agents: str,
    question: str,
) -> str:
    """Compute a deterministic hash of the run's key inputs.

    This hash is used in the RunManifest and in checkpoint files to
    verify that a resumed run is operating on the same inputs.
    """
    payload = json.dumps(
        {
            "ticker": ticker.upper(),
            "steps": steps,
            "agents": agents,
            "question": question,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# RunTracker
# ---------------------------------------------------------------------------


def _json_default(obj: Any) -> Any:
    """Serialise values that live market contexts carry into checkpoints.

    ``MarketContext.evidence_items`` holds provider evidence with ``datetime``
    fields; the checkpoint stores ``dataclasses.asdict(ctx)`` verbatim.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


#: run_ids handed out in this process (a run is only on disk once finished).
_ISSUED_RUN_IDS: Set[str] = set()
_ISSUED_RUN_IDS_LOCK = threading.Lock()


class RunTracker:
    """Tracks a single ``run_workflow`` execution through its lifecycle.

    Each call to ``run_workflow`` creates one RunTracker.  The tracker:

    * Generates a unique ``run_id`` on ``start_run()``.
    * Wraps each pipeline phase with ``start_step()`` / ``finish_step()``,
      producing immutable :class:`StepResult` entries.
    * Persists a checkpoint after every step (recoverable via
      ``resume_from_checkpoint()``).
    * Assembles and persists a final :class:`RunBundle` on ``finish_run()``.

    Parameters:
        ticker: Instrument ticker (e.g. ``"AAPL"``).
        config_version: Configuration version identifier.
        model_version: Model version identifier.
        code_version: Code version identifier.
    """

    def __init__(
        self,
        ticker: str,
        config_version: str = "1.0",
        model_version: str = "1.0",
        code_version: str = "11.0.0rc1",
    ) -> None:
        self.ticker = ticker.upper()
        self.config_version = config_version
        self.model_version = model_version
        self.code_version = code_version

        # Populated by start_run()
        self.run_id: Optional[str] = None
        self.manifest: Optional[RunManifest] = None
        self.created_at: Optional[datetime] = None
        self.input_snapshot_hash: Optional[str] = None

        # Accumulated step results (order preserved)
        self._step_results: List[StepResult] = []
        self._step_counter: int = 0

        # Set of step names already completed (from a checkpoint resume)
        self._completed_steps: Set[str] = set()

        # Intermediate state snapshot for checkpoint resume.
        # Populated by run_workflow with serializable proxies of ctx,
        # responses, consensus_result so that skipped steps can still
        # provide their outputs to downstream steps.
        self._checkpoint_state: Dict[str, Any] = {}
        self._run_metadata: Dict[str, Any] = {}
        self._evidence_coverage: Optional[CoverageStats] = None

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def start_run(
        self,
        input_snapshot_hash: Optional[str] = None,
    ) -> str:
        """Begin a new run — create the manifest and generate a run_id.

        Args:
            input_snapshot_hash: Hex digest of all input data at run time.
                When omitted, an empty-string hash is used (callers should
                supply a real hash).

        Returns:
            The generated ``run_id``.
        """
        resumed = self.run_id is not None and self.created_at is not None
        if not resumed:
            self.created_at = datetime.now(timezone.utc)
        self.input_snapshot_hash = input_snapshot_hash or hashlib.sha256(
            b""
        ).hexdigest()

        self.manifest = RunManifest(
            input_snapshot_hash=self.input_snapshot_hash,
            config_version=self.config_version,
            model_version=self.model_version,
            code_version=self.code_version,
        )

        # Compute manifest hash for the run_id suffix
        manifest_hash = hashlib.sha256(
            self.manifest.model_dump_json(exclude_none=True).encode("utf-8")
        ).hexdigest()
        if resumed:
            # A tracker restored from a checkpoint keeps its run_id and
            # created_at; regenerating them split one run into two bundles.
            return self.run_id

        # run_ids have one-second resolution. Two identical runs in the same
        # second produced the same id and the second bundle overwrote the
        # first, so step the timestamp until the id is unused.
        run_id = generate_run_id(self.ticker, self.created_at, manifest_hash)
        data_dir = get_data_dir()
        with _ISSUED_RUN_IDS_LOCK:  # dashboard requests can start runs concurrently
            while (data_dir / "runs" / f"{run_id}.json").exists() or run_id in _ISSUED_RUN_IDS:
                self.created_at += timedelta(seconds=1)
                run_id = generate_run_id(self.ticker, self.created_at, manifest_hash)
            _ISSUED_RUN_IDS.add(run_id)
        self.run_id = run_id
        return self.run_id

    # ------------------------------------------------------------------
    # Step lifecycle
    # ------------------------------------------------------------------

    def start_step(
        self,
        step_name: str,
        input_refs: Optional[List[str]] = None,
    ) -> str:
        """Record the start of a workflow step.

        Args:
            step_name: Human-readable step name (e.g. ``"fetch"``).
            input_refs: References to input artifacts (evidence IDs, etc.).

        Returns:
            The generated ``step_id``.
        """
        self._step_counter += 1
        step_id = f"{self.run_id}_step{self._step_counter}"
        sr = StepResult(
            step_id=step_id,
            step_name=step_name,
            status=StepStatus.SUCCESS,  # placeholder; overwritten on finish
            input_refs=input_refs or [],
            started_at=datetime.now(timezone.utc),
        )
        self._step_results.append(sr)
        return step_id

    def finish_step(
        self,
        step_id: str,
        status: StepStatus,
        result: Any = None,
        diagnostics: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        output_refs: Optional[List[str]] = None,
    ) -> StepResult:
        """Finalise a previously started step.

        Args:
            step_id: The step identifier returned by ``start_step()``.
            status: ``success`` | ``failure`` | ``degraded``.
            result: Typed step output (dict, list, number, or bool).
            diagnostics: Error messages or warnings.
            metadata: Arbitrary extra key-value pairs for the step.
            output_refs: Ids of artifacts the step produced (e.g. evidence ids).

        Returns:
            The updated :class:`StepResult`.

        Raises:
            ValueError: If ``step_id`` is not found.
        """
        for sr in self._step_results:
            if sr.step_id == step_id:
                sr.status = status
                sr.finished_at = datetime.now(timezone.utc)
                if sr.started_at is not None:
                    sr.elapsed_ms = (
                        sr.finished_at - sr.started_at
                    ).total_seconds() * 1000
                if result is not None:
                    sr.result = result
                if diagnostics is not None:
                    sr.diagnostics = diagnostics
                if metadata:
                    sr.metadata.update(metadata)
                if output_refs is not None:
                    sr.output_refs = list(output_refs)
                # Compute content_hash from the result
                if result is not None:
                    sr.content_hash = hashlib.sha256(
                        json.dumps(
                            result, sort_keys=True, default=str
                        ).encode("utf-8")
                    ).hexdigest()
                # Re-validate to catch schema violations (e.g. plain-string
                # result).  Pydantic validators run on construction; after
                # mutation we rebuild through model_validate to trigger them.
                validated = StepResult.model_validate(sr.model_dump())
                idx = self._step_results.index(sr)
                self._step_results[idx] = validated
                return validated
        raise ValueError(f"Step {step_id!r} not found in tracker")

    # ------------------------------------------------------------------
    # Run finalisation
    # ------------------------------------------------------------------

    def finish_run(self) -> RunBundle:
        """Assemble and persist the final :class:`RunBundle`.

        The bundle is written to ``get_data_dir() / "runs" / {run_id}.json``.

        Returns:
            The assembled :class:`RunBundle`.

        Raises:
            RuntimeError: If ``start_run()`` has not been called.
        """
        if self.run_id is None or self.manifest is None or self.created_at is None:
            raise RuntimeError(
                "start_run() must be called before finish_run()"
            )

        if self._evidence_coverage is not None:
            coverage = self._evidence_coverage
        else:
            # No evidence recorded (e.g. a run without a fetch step): fall
            # back to counting step outcomes, as before.
            total = len(self._step_results)
            covered = sum(
                1 for sr in self._step_results if sr.status == StepStatus.SUCCESS
            )
            degraded = sum(
                1 for sr in self._step_results if sr.status == StepStatus.DEGRADED
            )
            missing = total - covered - degraded

            coverage = CoverageStats(
                total_evidence=total,
                covered_evidence=covered,
                missing_evidence=missing,
                degraded_evidence=degraded,
                coverage_ratio=(covered / total) if total > 0 else 0.0,
            )

        bundle = RunBundle(
            run_id=self.run_id,
            created_at=self.created_at,
            manifest=self.manifest,
            step_results=list(self._step_results),
            coverage=coverage,
            metadata={
                **self._run_metadata,
                "ticker": self.ticker,
                "code_version": self.code_version,
            },
        )

        # Persist to disk
        runs_dir = get_data_dir() / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_path = runs_dir / f"{self.run_id}.json"
        run_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

        return bundle

    # ------------------------------------------------------------------
    # Checkpoint save / resume
    # ------------------------------------------------------------------

    def save_checkpoint(self, path: Optional[str] = None) -> Path:
        """Save the current tracker progress as a JSON checkpoint.

        Args:
            path: Absolute file path for the checkpoint.  When omitted,
                the file is written to
                ``get_data_dir() / "checkpoints" / {run_id}.checkpoint.json``.

        Returns:
            The ``Path`` where the checkpoint was written.
        """
        if self.run_id is None:
            raise RuntimeError(
                "start_run() must be called before save_checkpoint()"
            )

        if path is None:
            ckpt_dir = get_data_dir() / "checkpoints"
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            file_path = ckpt_dir / f"{self.run_id}.checkpoint.json"
        else:
            file_path = Path(path)

        payload: Dict[str, Any] = {
            "run_id": self.run_id,
            "ticker": self.ticker,
            "input_snapshot_hash": self.input_snapshot_hash,
            "created_at": self.created_at.isoformat()
            if self.created_at
            else None,
            "step_results": [
                sr.model_dump(mode="json") for sr in self._step_results
            ],
            "config_version": self.config_version,
            "model_version": self.model_version,
            "code_version": self.code_version,
            "_checkpoint_state": self._checkpoint_state,
        }
        file_path.write_text(
            json.dumps(
                payload, indent=2, ensure_ascii=False, default=_json_default
            ),
            encoding="utf-8",
        )
        return file_path

    @classmethod
    def resume_from_checkpoint(
        cls,
        path: str,
        ticker: str,
        steps: str = "",
        agents: str = "",
        question: str = "",
    ) -> "RunTracker":
        """Load a checkpoint and return a tracker pre-populated with
        completed steps.

        The checkpoint's ``input_snapshot_hash`` is compared against a
        freshly computed hash of the supplied inputs.  If they differ, a
        ``ValueError`` is raised — the caller must not resume a run whose
        inputs have changed.

        Args:
            path: Path to the checkpoint JSON file.
            ticker: Current ticker.
            steps: Current steps string.
            agents: Current agents string.
            question: Current question string.

        Returns:
            A ``RunTracker`` with completed steps loaded and
            ``_completed_steps`` populated.

        Raises:
            ValueError: If the input snapshot hash does not match.
            FileNotFoundError: If the checkpoint file does not exist.
        """
        ckpt_path = Path(path)
        if not ckpt_path.exists():
            raise FileNotFoundError(
                f"Checkpoint file not found: {ckpt_path}"
            )

        raw = json.loads(ckpt_path.read_text(encoding="utf-8"))

        # Verify input snapshot
        current_hash = _compute_input_snapshot_hash(
            ticker, steps, agents, question
        )
        stored_hash = raw.get("input_snapshot_hash", "")
        if current_hash != stored_hash:
            raise ValueError(
                f"Input snapshot hash mismatch: "
                f"checkpoint has {stored_hash[:16]}..., "
                f"current inputs hash to {current_hash[:16]}... "
                f"— inputs have changed; cannot resume."
            )

        tracker = cls(
            ticker=ticker,
            config_version=raw.get("config_version", "1.0"),
            model_version=raw.get("model_version", "1.0"),
            code_version=raw.get("code_version", "11.0.0rc1"),
        )

        # Restore run-level state
        tracker.run_id = raw["run_id"]
        tracker.input_snapshot_hash = stored_hash
        created_str = raw.get("created_at")
        if created_str:
            tracker.created_at = datetime.fromisoformat(created_str)

        # Rebuild manifest
        tracker.manifest = RunManifest(
            input_snapshot_hash=stored_hash,
            config_version=tracker.config_version,
            model_version=tracker.model_version,
            code_version=tracker.code_version,
        )

        # Restore completed steps
        completed_steps: Set[str] = set()
        for sr_data in raw.get("step_results", []):
            sr = StepResult.model_validate(sr_data)
            tracker._step_results.append(sr)
            tracker._step_counter = max(tracker._step_counter, len(tracker._step_results))
            # Only count SUCCESS and DEGRADED as "completed" — FAILURE
            # steps should be re-run.
            if sr.status in (StepStatus.SUCCESS, StepStatus.DEGRADED):
                completed_steps.add(sr.step_name)

        tracker._completed_steps = completed_steps
        tracker._checkpoint_state = raw.get("_checkpoint_state", {})
        return tracker

    # ------------------------------------------------------------------
    # Helpers for workflow integration
    # ------------------------------------------------------------------

    def is_step_completed(self, step_name: str) -> bool:
        """Return ``True`` if *step_name* was already completed in a
        resumed checkpoint and should be skipped."""
        return step_name in self._completed_steps

    def get_checkpoint_state(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the intermediate checkpoint state."""
        return self._checkpoint_state.get(key, default)

    def record_evidence_coverage(self, evidence_items: List[Dict[str, Any]]) -> None:
        """Compute the bundle's CoverageStats from real evidence items.

        ``missing`` / ``degraded`` flags on each item decide the buckets.
        Without this the stats counted workflow *steps*, so a run with three
        successful steps reported "3 evidence items, 100% covered".
        """
        total = len(evidence_items)
        missing = sum(1 for e in evidence_items if e.get("missing"))
        degraded = sum(1 for e in evidence_items if e.get("degraded") and not e.get("missing"))
        covered = total - missing - degraded
        self._evidence_coverage = CoverageStats(
            total_evidence=total,
            covered_evidence=covered,
            missing_evidence=missing,
            degraded_evidence=degraded,
            coverage_ratio=(covered / total) if total else 0.0,
        )

    def set_run_metadata(self, key: str, value: Any) -> None:
        """Attach JSON-serialisable run-level metadata to the final RunBundle."""
        self._run_metadata[key] = value

    def set_checkpoint_state(self, key: str, value: Any) -> None:
        """Store a serializable value in the intermediate checkpoint state."""
        self._checkpoint_state[key] = value

    @property
    def step_results(self) -> List[StepResult]:
        """Read-only view of accumulated step results."""
        return list(self._step_results)


def list_run_ids(ticker: str) -> List[str]:
    """Persisted RunBundle ids for ``ticker``, newest first (by ``created_at``, then id)."""
    runs_dir = get_data_dir() / "runs"
    if not runs_dir.is_dir():
        return []
    keyed = []
    for path in runs_dir.glob("*.json"):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(bundle.get("metadata", {}).get("ticker", "")).upper() != ticker.upper():
            continue
        keyed.append((str(bundle.get("created_at", "")), str(bundle.get("run_id", path.stem)), bundle))
    keyed.sort(reverse=True)
    return [run_id for _created, run_id, _bundle in keyed]


def extract_persona_results(bundle: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """(persona outputs, consensus) from a workflow or skill RunBundle dict.

    Workflow runs keep them in the ``analyze`` / ``consensus`` steps; skill
    runs (``personas.analyze``) nest them under ``personas`` / ``consensus``.
    """
    personas: Dict[str, Dict[str, Any]] = {}
    consensus: Dict[str, Any] = {}
    for step in bundle.get("step_results", []):
        result = step.get("result") if isinstance(step, dict) else None
        if not isinstance(result, dict):
            continue
        if isinstance(result.get("personas"), dict):
            personas = {k: v for k, v in result["personas"].items() if isinstance(v, dict)}
        elif step.get("step_name") == "analyze":
            personas = {k: v for k, v in result.items() if isinstance(v, dict)}
        if isinstance(result.get("consensus"), dict):
            consensus = dict(result["consensus"])
        elif step.get("step_name") == "consensus":
            consensus = dict(result)
    return personas, consensus


def bundle_has_persona_analysis(bundle: Dict[str, Any]) -> bool:
    """True when a bundle holds per-persona results (workflow or skill run)."""
    personas, _consensus = extract_persona_results(bundle)
    return any("signal" in p for p in personas.values())


def latest_run_id(ticker: str, require_persona_analysis: bool = False) -> Optional[str]:
    """Return the newest persisted RunBundle id for ``ticker``, if any.

    With ``require_persona_analysis`` skip runs without persona results, such
    as filing-delta or insider-cluster skill runs.
    """
    for run_id in list_run_ids(ticker):
        if not require_persona_analysis:
            return run_id
        try:
            if bundle_has_persona_analysis(load_run_bundle_dict(run_id)):
                return run_id
        except (OSError, ValueError):
            continue
    return None


def load_run_bundle_dict(run_id: str) -> Dict[str, Any]:
    """Load a persisted RunBundle as a plain dict (raises FileNotFoundError)."""
    path = get_data_dir() / "runs" / f"{run_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))
