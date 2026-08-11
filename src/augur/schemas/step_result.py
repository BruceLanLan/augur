# -*- coding: utf-8 -*-
"""
StepResult — Frozen v1 schema for the outcome of a single workflow step.

Attributes:
  - step_id, step_name
  - status: success | failure | degraded
  - input_refs / output_refs
  - typed result (not a plain string)
  - diagnostics, provenance
  - elapsed_ms, content_hash
  - started_at, finished_at
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class StepStatus(str, Enum):
    """Outcome status of a single workflow step."""

    SUCCESS = "success"
    FAILURE = "failure"
    DEGRADED = "degraded"


class StepResult(BaseModel):
    """Outcome of a single discrete workflow step.

    Attributes:
        step_id: Unique step identifier.
        step_name: Human-readable step name (e.g. ``"fetch_prices"``).
        status: ``success`` | ``failure`` | ``degraded``.
        input_refs: References to input artifacts (evidence IDs, claim IDs, etc.).
        output_refs: References to produced artifacts.
        result: Typed result — a dict, list, number, or bool; **never a plain string**.
        diagnostics: Error messages, warnings, or diagnostic information.
        provenance: Provenance chain (who ran this, on what machine).
        elapsed_ms: Wall-clock duration in milliseconds.
        content_hash: Hash of the step output for integrity verification.
        started_at: When the step began.
        finished_at: When the step finished.
        metadata: Arbitrary extra key-value pairs.
    """

    step_id: str = Field(
        ...,
        description="Unique step identifier",
    )
    step_name: str = Field(
        ...,
        description="Human-readable step name",
    )

    status: StepStatus = Field(
        ...,
        description="success | failure | degraded",
    )

    # ---- artifact references ----
    input_refs: List[str] = Field(
        default_factory=list,
        description="References to input artifacts (evidence IDs, claim IDs, etc.)",
    )
    output_refs: List[str] = Field(
        default_factory=list,
        description="References to produced artifacts",
    )

    # ---- typed result (not a string) ----
    result: Any = Field(
        default=None,
        description="Typed result — dict, list, number, or bool (not a plain string)",
    )

    # ---- diagnostics & provenance ----
    diagnostics: Optional[str] = Field(
        None,
        description="Error messages, warnings, or diagnostic information",
    )
    provenance: Optional[str] = Field(
        None,
        description="Provenance chain: who ran this, on what machine",
    )

    # ---- timing & integrity ----
    elapsed_ms: Optional[float] = Field(
        None,
        ge=0.0,
        description="Wall-clock duration in milliseconds",
    )
    content_hash: Optional[str] = Field(
        None,
        description="Hash of step output for integrity verification",
    )

    started_at: Optional[datetime] = Field(
        None,
        description="When the step began",
    )
    finished_at: Optional[datetime] = Field(
        None,
        description="When the step finished",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary extra key-value pairs",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_result_not_plain_string(self) -> "StepResult":
        """Reject a plain-string result — must be a typed value."""
        if isinstance(self.result, str):
            raise ValueError(
                "result must be a typed value (dict, list, number, bool), "
                "not a plain string"
            )
        return self
