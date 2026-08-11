# -*- coding: utf-8 -*-
"""
Claim — Frozen v1 schema for a statement backed by evidence.

ID rule:  cl_{hash[:12]}  (hash = SHA-256 of claim text)

Classification:
  - fact       : verifiable true/false statement
  - inference  : reasoned conclusion from facts
  - scenario   : hypothetical or counterfactual

Confidence must come from ``explicit_rule`` or ``calibrated_model``.
When no supporting or contradicting evidence is present the claim
status must be ``unknown`` or ``abstain``.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ClaimClassification(str, Enum):
    """What kind of claim this is."""

    FACT = "fact"
    INFERENCE = "inference"
    SCENARIO = "scenario"


class ConfidenceSource(str, Enum):
    """Where a numeric confidence value came from."""

    EXPLICIT_RULE = "explicit_rule"
    CALIBRATED_MODEL = "calibrated_model"


class ClaimStatus(str, Enum):
    """Claim lifecycle status."""

    ACTIVE = "active"
    UNKNOWN = "unknown"
    ABSTAIN = "abstain"


def generate_claim_id(text: str) -> str:
    """Generate a v1 claim_id: ``cl_{sha256(text)[:12]}``."""
    hash_hex = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"cl_{hash_hex[:12]}"


class Claim(BaseModel):
    """A statement about the world backed by structured evidence.

    Attributes:
        claim_id: Unique identifier following ``cl_{hash[:12]}``.
        text: The claim text itself.
        persona_id: ID of the persona that made this claim.
        supports: Evidence IDs that support this claim.
        contradicts: Evidence IDs that contradict this claim.
        insufficient: Evidence IDs deemed insufficient to decide.
        classification: ``fact`` | ``inference`` | ``scenario``.
        confidence: 0.0–1.0 confidence score.  Must be accompanied by
            ``confidence_source``.
        confidence_source: ``explicit_rule`` or ``calibrated_model``.
        status: ``active`` when evidence is present, ``unknown`` or
            ``abstain`` when insufficient.
        metadata: Arbitrary extra key-value pairs.
    """

    claim_id: str = Field(
        ...,
        description="Unique ID: cl_{hash[:12]}",
        pattern=r"^cl_[a-f0-9]{12}$",
    )
    text: str = Field(
        ...,
        description="The claim text",
        min_length=1,
    )
    persona_id: str = Field(
        ...,
        description="ID of the persona making the claim",
    )

    # ---- evidence linkage ----
    supports: List[str] = Field(
        default_factory=list,
        description="Evidence IDs supporting this claim",
    )
    contradicts: List[str] = Field(
        default_factory=list,
        description="Evidence IDs contradicting this claim",
    )
    insufficient: List[str] = Field(
        default_factory=list,
        description="Evidence IDs deemed insufficient",
    )

    # ---- classification ----
    classification: ClaimClassification = Field(
        ...,
        description="fact | inference | scenario",
    )

    # ---- confidence (must be traceable) ----
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0–1.0",
    )
    confidence_source: Optional[ConfidenceSource] = Field(
        None,
        description="Where confidence came from: explicit_rule or calibrated_model",
    )

    # ---- status ----
    status: ClaimStatus = Field(
        default=ClaimStatus.ACTIVE,
        description="active | unknown | abstain (unknown/abstain when insufficient evidence)",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary extra key-value pairs",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_confidence_source_required(self) -> "Claim":
        """Confidence values must declare their source."""
        if self.confidence is not None and self.confidence_source is None:
            raise ValueError(
                "confidence requires confidence_source — "
                "must be 'explicit_rule' or 'calibrated_model'"
            )
        return self

    @model_validator(mode="after")
    def _validate_insufficient_evidence_abstain(self) -> "Claim":
        """When no supporting or contradicting evidence exists, abstain."""
        if not self.supports and not self.contradicts:
            if self.status not in (ClaimStatus.UNKNOWN, ClaimStatus.ABSTAIN):
                raise ValueError(
                    "Claim has no supporting or contradicting evidence — "
                    "status must be 'unknown' or 'abstain'"
                )
        return self
