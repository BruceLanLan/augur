# -*- coding: utf-8 -*-
"""
SkillSpec v1 — Capability specification schema with built-in validator.

A SkillSpec describes a named capability (skill) that can be invoked by
the Augur system.  **v1 strictly forbids**:

* ``module_path``, ``import``, ``shell``, ``exec``, ``eval``, ``subprocess``
* Arbitrary file paths (strings starting with ``/``, ``./``, ``../`` that
  are not ``http://`` / ``https://`` URLs)
* Any network domain not declared in ``permissions.network_domains``

Public API:
    SkillSpec       — Pydantic v2 model
    validate_skill_spec(spec: dict) -> list[str]
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Forbidden-pattern constants (searched case-insensitively in the raw spec)
# ---------------------------------------------------------------------------

_FORBIDDEN_KEYS_EXACT: tuple[str, ...] = (
    "import",
    "shell",
    "exec",
    "eval",
    "compile",
)

_FORBIDDEN_KEYS_CONTAINS: tuple[str, ...] = (
    "module_path",
    "subprocess",
    "os.system",
    "__import__",
)

# Keys whose *values* must not look like file-system paths.
_PATH_SENSITIVE_KEYS: tuple[str, ...] = (
    "module_path",
    "path",
    "file",
    "file_path",
    "script_path",
    "entrypoint",
)

_URL_RE = re.compile(r"^https?://")
_PATH_RE = re.compile(r"^(\.{0,2}/|/[^/\s])")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class SkillPermissions(BaseModel):
    """Network and resource access grants for a skill.

    Attributes:
        resources: Allowed resource identifiers (e.g. ``["edgar:filings"]``).
        network_domains: Allowed network domains (e.g. ``["api.example.com"]``).
    """

    resources: List[str] = Field(
        default_factory=list,
        description="Allowed resource identifiers",
    )
    network_domains: List[str] = Field(
        default_factory=list,
        description="Allowed network domains (hostnames only, no scheme)",
    )


class MissingStrategy(str, Enum):
    """What to do when expected evidence is missing."""

    ABSTAIN = "abstain"
    FLAG = "flag"
    ESTIMATE = "estimate"


class EvidencePolicy(BaseModel):
    """Evidence-handling rules for a skill.

    Attributes:
        information_time_required: Whether ``effective_at`` / ``available_at``
            must be present on every evidence item.
        missing_strategy: What to do when evidence is missing.
        min_claim_coverage: Minimum evidence coverage ratio (0.0–1.0)
            required before a claim can be emitted.
    """

    information_time_required: bool = Field(
        default=True,
        description="Whether effective_at/available_at must be present on evidence",
    )
    missing_strategy: MissingStrategy = Field(
        default=MissingStrategy.ABSTAIN,
        description="Strategy when evidence is missing",
    )
    min_claim_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum evidence coverage for claims (0.0-1.0)",
    )


class WorkflowStep(BaseModel):
    """A single step in a skill's workflow.

    Attributes:
        id: Step identifier (unique within the workflow).
        uses: Capability or resource identifier this step invokes.
        needs: Dependency list — step IDs or evidence IDs that must
            be satisfied before this step can execute.
    """

    id: str = Field(..., description="Step identifier")
    uses: str = Field(..., description="Capability or resource used")
    needs: List[str] = Field(
        default_factory=list,
        description="Dependencies (step IDs or evidence IDs)",
    )


class EvalFixture(BaseModel):
    """A single evaluation fixture.

    Attributes:
        input: Input payload for the skill.
        expected_output: Expected output payload.
    """

    input: Dict[str, Any] = Field(default_factory=dict)
    expected_output: Dict[str, Any] = Field(default_factory=dict)


class EvalGate(BaseModel):
    """A quality gate for evaluation.

    Attributes:
        metric: Metric name (e.g. ``"accuracy"``, ``"f1"``).
        threshold: Minimum acceptable value.
    """

    metric: str = Field(..., description="Metric name")
    threshold: float = Field(..., description="Minimum threshold")


class SkillEvals(BaseModel):
    """Evaluation configuration for a skill.

    Accepts both string-based and structured forms:
      - fixtures: ``["earnings-prep-v1"]`` or ``[{"input":..., "expected_output":...}]``
      - gates: ``["citation_validity"]`` or ``[{"metric":..., "threshold":...}]``
    """

    fixtures: List[Any] = Field(default_factory=list)
    gates: List[Any] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SkillSpec
# ---------------------------------------------------------------------------

class SkillSpec(BaseModel):
    """Specification for a named capability (skill).

    **v1 constraints:**

    * No ``module_path``, ``import``, ``shell``, arbitrary file paths,
      expression evaluation, or unregistered network access.
    * ``required_capabilities`` must only list registered capability names.
    * Workflow steps must have unique ``id`` values.

    Attributes:
        id: Unique skill identifier (kebab-case, e.g. ``"earnings-prep"``).
        version: Semantic version string (e.g. ``"1.0.0"``).
        description: Human-readable one-liner.
        license: SPDX license identifier or custom string.
        compatibility: Version constraints (e.g. ``{"augur": ">=10.15"}``).
        inputs_schema: JSON Schema dict describing expected inputs.
        required_capabilities: Names of capabilities this skill depends on.
        permissions: Network and resource access grants.
        evidence_policy: Evidence-handling rules.
        workflow: Ordered list of workflow steps.
        outputs_schema: JSON Schema dict describing outputs.
        evals: Evaluation fixtures and gates.
    """

    id: str = Field(
        ...,
        description="Unique skill identifier (kebab-case)",
        pattern=r"^[a-z][a-z0-9_-]{0,63}$",
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic version",
        pattern=r"^\d+\.\d+\.\d+",
    )
    description: str = Field(
        ...,
        description="What this skill does",
        min_length=1,
    )
    license: Optional[str] = Field(
        None,
        description="License identifier (SPDX or custom)",
    )
    compatibility: str = Field(
        default="",
        description="Compatibility constraints (e.g. '>=11,<12')",
    )

    # ---- I/O schemas ----
    inputs_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for inputs",
    )
    outputs_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for outputs",
    )

    # ---- capabilities & permissions ----
    required_capabilities: List[str] = Field(
        default_factory=list,
        description="Registered capability names required by this skill",
    )
    permissions: SkillPermissions = Field(
        default_factory=SkillPermissions,
        description="Network and resource access grants",
    )

    # ---- evidence policy ----
    evidence_policy: EvidencePolicy = Field(
        default_factory=EvidencePolicy,
        description="Evidence-handling rules",
    )

    # ---- workflow ----
    workflow: List[WorkflowStep] = Field(
        default_factory=list,
        description="Ordered workflow steps",
    )

    # ---- evals ----
    evals: SkillEvals = Field(
        default_factory=SkillEvals,
        description="Evaluation fixtures and gates",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_workflow_step_ids_unique(self) -> "SkillSpec":
        """Workflow step IDs must be unique."""
        ids = [step.id for step in self.workflow]
        if len(ids) != len(set(ids)):
            seen: set[str] = set()
            dupes = {sid for sid in ids if sid in seen or seen.add(sid)}  # type: ignore[func-returns-value]
            raise ValueError(
                f"Workflow step IDs must be unique; duplicates: {sorted(dupes)}"
            )
        return self


# ======================================================================
# Public validator (operates on raw dicts, not Pydantic models)
# ======================================================================

def _collect_forbidden_keys(obj: Any, path: str, violations: List[str]) -> None:
    """Recurse through *obj* looking for forbidden key names."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            for forbidden in _FORBIDDEN_KEYS_EXACT:
                if key_lower == forbidden:
                    violations.append(
                        f"Forbidden key {key!r} at {path}: "
                        f"SkillSpec v1 prohibits '{forbidden}'"
                    )
            for forbidden in _FORBIDDEN_KEYS_CONTAINS:
                if forbidden in key_lower:
                    violations.append(
                        f"Forbidden key {key!r} at {path}: "
                        f"SkillSpec v1 prohibits '{forbidden}'"
                    )
            # Check path-sensitive keys for file-system-looking values
            if key_lower in _PATH_SENSITIVE_KEYS or any(
                kw in key_lower for kw in ("_path", "_file", "_dir")
            ):
                if isinstance(value, str) and _PATH_RE.match(value):
                    if not _URL_RE.match(value):
                        violations.append(
                            f"File-system path in {key!r} at {path}: "
                            f"{value!r} — arbitrary file paths are forbidden in v1"
                        )
            _collect_forbidden_keys(value, f"{path}.{key}", violations)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _collect_forbidden_keys(item, f"{path}[{idx}]", violations)
    elif isinstance(obj, str):
        # Check for file-system paths in bare strings
        if _PATH_RE.match(obj) and not _URL_RE.match(obj):
            violations.append(
                f"Arbitrary file path at {path}: {obj!r} — forbidden in v1"
            )


def _collect_unregistered_network(
    obj: Any, path: str, allowed_domains: set[str], violations: List[str]
) -> None:
    """Recurse through *obj* looking for URLs whose host is not in *allowed_domains*."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            _collect_unregistered_network(value, f"{path}.{key}", allowed_domains, violations)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _collect_unregistered_network(item, f"{path}[{idx}]", allowed_domains, violations)
    elif isinstance(obj, str):
        if _URL_RE.match(obj):
            # Crude host extraction — good enough for validation
            m = re.match(r"^https?://([^/:\s]+)", obj)
            if m:
                host = m.group(1)
                if host not in allowed_domains and "*" not in allowed_domains:
                    violations.append(
                        f"Unregistered network domain {host!r} at {path}: "
                        f"not in permissions.network_domains {sorted(allowed_domains)}"
                    )


def validate_skill_spec(spec: dict) -> List[str]:
    """Validate a SkillSpec dictionary against v1 constraints.

    Returns a **list of violation strings** (empty list ⇒ valid).

    Checks performed:

    1. Top-level structure (must be a dict with required keys).
    2. Forbidden keys: ``module_path``, ``import``, ``shell``, ``exec``,
       ``eval``, ``subprocess``, ``os.system``, ``__import__``, ``compile``.
    3. Arbitrary file-path strings (``/abs/path``, ``./relative``, ``../escape``).
    4. Unregistered network domains (URLs whose host is not listed in
       ``permissions.network_domains``).
    """
    violations: List[str] = []

    if not isinstance(spec, dict):
        return ["SkillSpec must be a dict"]

    # --- 1. Required keys ---
    for key in ("id", "description"):
        if key not in spec:
            violations.append(f"Missing required key: {key!r}")
        elif not isinstance(spec[key], str) or not spec[key].strip():
            violations.append(f"{key!r} must be a non-empty string")

    # --- 2. Forbidden keys & file paths ---
    _collect_forbidden_keys(spec, "<root>", violations)

    # --- 3. Unregistered network access ---
    perms = spec.get("permissions", {})
    if isinstance(perms, dict):
        allowed = set(perms.get("network_domains", []))
    else:
        allowed = set()
    _collect_unregistered_network(spec, "<root>", allowed, violations)

    return violations
