# -*- coding: utf-8 -*-
"""
EvidenceItem — Frozen v1 schema for a single timestamped unit of evidence.

ID rule:  ev_{source}_{hash[:12]}
Three time semantics:
  - effective_at  : when the information became true/effective in the real world
  - available_at  : when the information became publicly available
  - retrieved_at  : when we fetched/ingested the information

Validation: available_at must not be substituted by retrieved_at.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, model_validator


def generate_evidence_id(source: str, content_hash: str) -> str:
    """Generate a v1 evidence_id: ``ev_{source}_{content_hash[:12]}``."""
    short_hash = content_hash[:12]
    return f"ev_{source}_{short_hash}"


class EvidenceItem(BaseModel):
    """A single timestamped piece of evidence with full provenance metadata.

    Attributes:
        evidence_id: Unique identifier following ``ev_{source}_{hash[:12]}``.
        source: Provider name (e.g. ``"sec_edgar"``, ``"yfinance"``).
        source_locator: URL, accession number, or other retrieval locator.
        content_hash: SHA-256 hash of the raw fetched content.
        instrument: Ticker or instrument identifier.
        metric: What is being measured (e.g. ``"pe_ratio"``).
        value: Numeric value of the metric.
        unit: Unit of measurement (e.g. ``"USD"``, ``"shares"``).
        currency: ISO-4217 currency code.
        effective_at: When the information became true/effective in the real world.
        available_at: When the information became publicly available.
            **Must be set independently** — never substitute with ``retrieved_at``.
        retrieved_at: When we fetched/ingested the information.
        transform_version: Version of the transform pipeline applied.
        schema_version: Schema version for this evidence item (default ``"1.0"``).
        code_version: Code version that produced this evidence item.
        coverage: Coverage score 0.0–1.0 (1.0 = fully covered).
        missing: Whether the expected data point is absent.
        degraded: Whether the data quality is degraded.
        license: Data license identifier (SPDX or custom).
        redistribution_allowed: Whether the data may be redistributed.
        metadata: Arbitrary extra key-value pairs.
    """

    evidence_id: str = Field(
        ...,
        description="Unique ID: ev_{source}_{hash[:12]}",
        pattern=r"^ev_[a-z0-9_.-]+_[a-f0-9]{12}$",
    )
    source: str = Field(
        ...,
        description="Provider name (e.g. 'sec_edgar', 'yfinance')",
    )
    source_locator: Optional[str] = Field(
        None,
        description="URL, accession number, or other retrieval locator",
    )
    content_hash: str = Field(
        ...,
        description="SHA-256 hex digest of raw fetched content",
        min_length=12,
    )

    # ---- what is being measured ----
    instrument: Optional[str] = Field(
        None,
        description="Ticker or instrument identifier",
    )
    metric: Optional[str] = Field(
        None,
        description="What is being measured (e.g. 'pe_ratio')",
    )
    value: Optional[float] = Field(
        None,
        description="Numeric value of the metric",
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measurement",
    )
    currency: Optional[str] = Field(
        None,
        description="ISO-4217 currency code",
    )

    # ---- three time semantics ----
    effective_at: Optional[datetime] = Field(
        None,
        description=(
            "When the information became true/effective in the real world. "
            "e.g. the fiscal quarter-end date for an earnings report."
        ),
    )
    available_at: Optional[datetime] = Field(
        None,
        description=(
            "When the information became publicly available. "
            "e.g. the filing date for an SEC submission. "
            "Must be set independently — never substitute with retrieved_at."
        ),
    )
    retrieved_at: Optional[datetime] = Field(
        None,
        description="When we fetched/ingested the information.",
    )

    # ---- versioning ----
    transform_version: Optional[str] = Field(
        None,
        description="Version of the transform pipeline applied",
    )
    schema_version: str = Field(
        default="1.0",
        description="Schema version for this evidence item",
    )
    code_version: Optional[str] = Field(
        None,
        description="Code version that produced this evidence item",
    )

    # ---- quality flags ----
    coverage: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Coverage score 0.0–1.0 (1.0 = fully covered)",
    )
    missing: bool = Field(
        default=False,
        description="Whether the expected data point is absent",
    )
    degraded: bool = Field(
        default=False,
        description="Whether the data quality is degraded",
    )

    # ---- licensing ----
    license: Optional[str] = Field(
        None,
        description="Data license identifier (SPDX or custom)",
    )
    redistribution_allowed: bool = Field(
        default=True,
        description="Whether the data may be redistributed",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary extra key-value pairs",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_available_at_not_substituted(self) -> "EvidenceItem":
        """Reject specs where ``available_at`` is a copy of ``retrieved_at``.

        ``available_at`` captures when information became *publicly* available;
        ``retrieved_at`` captures when *we* fetched it.  Setting both to the
        same value means the author tried to substitute one for the other.
        """
        if self.available_at is not None and self.retrieved_at is not None:
            if self.available_at == self.retrieved_at:
                raise ValueError(
                    "available_at must not equal retrieved_at — "
                    "available_at represents when information became publicly available, "
                    "retrieved_at represents when we fetched it. "
                    "Do not substitute retrieved_at for available_at."
                )
        return self

    @model_validator(mode="after")
    def _validate_evidence_id_format(self) -> "EvidenceItem":
        """Verify evidence_id matches the expected pattern."""
        prefix = f"ev_{self.source}_"
        if not self.evidence_id.startswith(prefix):
            raise ValueError(
                f"evidence_id {self.evidence_id!r} must start with {prefix!r}"
            )
        return self
