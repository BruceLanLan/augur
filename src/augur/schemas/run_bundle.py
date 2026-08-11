# -*- coding: utf-8 -*-
"""
RunBundle — Frozen v1 schema for a complete analysis run record.

ID rule:  run_{ticker}_{timestamp}_{hash[:8]}

A RunBundle is immutable once created.  The ``supersedes`` field links a
new run to the one it replaces without mutating the historical bundle.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from augur.schemas.step_result import StepResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_run_id(ticker: str, timestamp: datetime, manifest_hash: str) -> str:
    """Generate a v1 run_id: ``run_{ticker}_{timestamp}_{manifest_hash[:8]}``.

    Args:
        ticker: Instrument ticker (e.g. ``"AAPL"``).
        timestamp: The ``created_at`` datetime.
        manifest_hash: Hex digest of the serialized run manifest.
    """
    ts_str = timestamp.strftime("%Y%m%dT%H%M%S")
    return f"run_{ticker}_{ts_str}_{manifest_hash[:8]}"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class RunManifest(BaseModel):
    """Immutable snapshot of the run's inputs and environment.

    Attributes:
        input_snapshot_hash: Hash of all input data at run time.
        config_version: Configuration version identifier.
        model_version: Model version identifier.
        code_version: Code version identifier.
    """

    input_snapshot_hash: str = Field(
        ...,
        description="Hash of all input data at run time",
    )
    config_version: str = Field(
        ...,
        description="Configuration version",
    )
    model_version: str = Field(
        ...,
        description="Model version",
    )
    code_version: str = Field(
        ...,
        description="Code version",
    )


class CoverageStats(BaseModel):
    """Aggregated coverage and missingness statistics for a run.

    Attributes:
        total_evidence: Total evidence items expected.
        covered_evidence: Items with coverage ≥ threshold.
        missing_evidence: Items flagged as missing.
        degraded_evidence: Items flagged as degraded.
        coverage_ratio: ``covered_evidence / total_evidence`` (0.0–1.0).
    """

    total_evidence: int = Field(default=0, ge=0)
    covered_evidence: int = Field(default=0, ge=0)
    missing_evidence: int = Field(default=0, ge=0)
    degraded_evidence: int = Field(default=0, ge=0)
    coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# RunBundle
# ---------------------------------------------------------------------------

class RunBundle(BaseModel):
    """Complete record of a single analysis run.

    Immutable once created.  Superseded runs remain intact; the new run
    references the old one via ``supersedes``.

    Attributes:
        run_id: Unique identifier following ``run_{ticker}_{timestamp}_{hash[:8]}``.
        created_at: When this run was created.
        supersedes: ``run_id`` of the run this one replaces (if any).
        manifest: Immutable snapshot of inputs, config, model, and code versions.
        step_results: Ordered list of :class:`StepResult` entries.
        coverage: Aggregated coverage/missingness statistics.
        metadata: Arbitrary extra key-value pairs.
    """

    run_id: str = Field(
        ...,
        description="Unique ID: run_{ticker}_{timestamp}_{hash[:8]}",
        pattern=r"^run_[A-Z0-9_.-]+_\d{8}T\d{6}_[a-f0-9]{8}$",
    )
    created_at: datetime = Field(
        ...,
        description="When this run was created",
    )
    supersedes: Optional[str] = Field(
        None,
        description="run_id of the run this one supersedes",
    )

    manifest: RunManifest = Field(
        ...,
        description="Immutable run manifest (input snapshot, config/model/code versions)",
    )
    step_results: List[StepResult] = Field(
        default_factory=list,
        description="Ordered step results",
    )
    coverage: CoverageStats = Field(
        default_factory=CoverageStats,
        description="Coverage/missingness statistics",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary extra key-value pairs",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_supersedes_not_self(self) -> "RunBundle":
        """A run cannot supersede itself."""
        if self.supersedes is not None and self.supersedes == self.run_id:
            raise ValueError(
                f"A run cannot supersede itself (run_id={self.run_id!r})"
            )
        return self

    @model_validator(mode="after")
    def _validate_step_results_not_empty(self) -> "RunBundle":
        """A run must contain at least one step result."""
        if len(self.step_results) == 0:
            raise ValueError(
                "RunBundle must contain at least one StepResult"
            )
        return self
