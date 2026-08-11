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
    SkillSpec       — dataclass model with to_dict() / from_dict()
    validate_skill_spec(spec: dict) -> list[str]
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Forbidden-pattern constants
# ---------------------------------------------------------------------------

_FORBIDDEN_KEYS: tuple[str, ...] = (
    "module_path",
    "import",
    "shell",
    "exec",
    "eval",
    "subprocess",
    "os.system",
    "__import__",
    "compile",
)

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
_SKILL_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

@dataclass
class SkillPermissions:
    resources: List[str] = field(default_factory=list)
    network_domains: List[str] = field(default_factory=list)
    def to_dict(self) -> dict:
        return {"resources": list(self.resources), "network_domains": list(self.network_domains)}
    @classmethod
    def from_dict(cls, d: dict) -> "SkillPermissions":
        return cls(resources=d.get("resources", []), network_domains=d.get("network_domains", []))


@dataclass
class EvidencePolicy:
    information_time_required: bool = True
    missing_strategy: str = "abstain"
    min_claim_coverage: float = 0.0
    def to_dict(self) -> dict:
        return {"information_time_required": self.information_time_required,
                "missing_strategy": self.missing_strategy,
                "min_claim_coverage": self.min_claim_coverage}
    @classmethod
    def from_dict(cls, d: dict) -> "EvidencePolicy":
        return cls(information_time_required=d.get("information_time_required", True),
                   missing_strategy=d.get("missing_strategy", "abstain"),
                   min_claim_coverage=d.get("min_claim_coverage", 0.0))


@dataclass
class WorkflowStep:
    id: str
    uses: str = ""
    needs: List[str] = field(default_factory=list)
    def to_dict(self) -> dict:
        return {"id": self.id, "uses": self.uses, "needs": list(self.needs)}
    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowStep":
        return cls(id=d["id"], uses=d.get("uses", ""), needs=d.get("needs", []))


@dataclass
class EvalFixture:
    input: Dict[str, Any] = field(default_factory=dict)
    expected_output: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict:
        return {"input": copy.deepcopy(self.input), "expected_output": copy.deepcopy(self.expected_output)}
    @classmethod
    def from_dict(cls, d: dict) -> "EvalFixture":
        return cls(input=copy.deepcopy(d.get("input", {})), expected_output=copy.deepcopy(d.get("expected_output", {})))


@dataclass
class EvalGate:
    metric: str
    threshold: float = 0.0
    def to_dict(self) -> dict:
        return {"metric": self.metric, "threshold": self.threshold}
    @classmethod
    def from_dict(cls, d: dict) -> "EvalGate":
        return cls(metric=d["metric"], threshold=d.get("threshold", 0.0))


@dataclass
class SkillEvals:
    fixtures: List[EvalFixture] = field(default_factory=list)
    gates: List[EvalGate] = field(default_factory=list)
    def to_dict(self) -> dict:
        return {"fixtures": [f.to_dict() for f in self.fixtures], "gates": [g.to_dict() for g in self.gates]}
    @classmethod
    def from_dict(cls, d: dict) -> "SkillEvals":
        return cls(fixtures=[EvalFixture.from_dict(f) for f in d.get("fixtures", [])],
                   gates=[EvalGate.from_dict(g) for g in d.get("gates", [])])


# ---------------------------------------------------------------------------
# SkillSpec
# ---------------------------------------------------------------------------

@dataclass
class SkillSpec:
    id: str
    description: str
    version: str = "1.0.0"
    license: Optional[str] = None
    compatibility: Dict[str, str] = field(default_factory=dict)
    inputs_schema: Dict[str, Any] = field(default_factory=dict)
    outputs_schema: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    permissions: SkillPermissions = field(default_factory=SkillPermissions)
    evidence_policy: EvidencePolicy = field(default_factory=EvidencePolicy)
    workflow: List[WorkflowStep] = field(default_factory=list)
    evals: SkillEvals = field(default_factory=SkillEvals)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _SKILL_NAME_RE.match(self.id):
            raise ValueError(f"SkillSpec id {self.id!r} must be kebab-case (lowercase letters, digits, hyphens, underscores; max 64 chars)")
        if self.version and not re.match(r"^\d+\.\d+\.\d+", self.version):
            raise ValueError(f"SkillSpec version {self.version!r} should be semver-like (e.g. '1.0.0')")
        step_ids = [step.id for step in self.workflow]
        if len(step_ids) != len(set(step_ids)):
            dupes = sorted({sid for sid in step_ids if step_ids.count(sid) > 1})
            raise ValueError(f"Workflow step IDs must be unique; duplicates: {dupes}")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "version": self.version, "description": self.description,
            "license": self.license, "compatibility": copy.deepcopy(self.compatibility),
            "inputs_schema": copy.deepcopy(self.inputs_schema),
            "required_capabilities": list(self.required_capabilities),
            "permissions": self.permissions.to_dict(),
            "evidence_policy": self.evidence_policy.to_dict(),
            "workflow": [s.to_dict() for s in self.workflow],
            "outputs_schema": copy.deepcopy(self.outputs_schema),
            "evals": self.evals.to_dict(),
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SkillSpec":
        skill_id = d.get("id") or d.get("name", "")
        inputs = copy.deepcopy(d.get("inputs_schema") or d.get("parameters", {}))
        return cls(
            id=skill_id, description=d.get("description", ""),
            version=d.get("version", "1.0.0"), license=d.get("license"),
            compatibility=copy.deepcopy(d.get("compatibility", {})),
            inputs_schema=inputs,
            required_capabilities=d.get("required_capabilities", []),
            permissions=SkillPermissions.from_dict(d.get("permissions", {})),
            evidence_policy=EvidencePolicy.from_dict(d.get("evidence_policy", {})),
            workflow=[WorkflowStep.from_dict(s) for s in d.get("workflow", [])],
            outputs_schema=copy.deepcopy(d.get("outputs_schema", {})),
            evals=SkillEvals.from_dict(d.get("evals", {})),
            metadata=copy.deepcopy(d.get("metadata", {})),
        )


# ======================================================================
# Public validator (operates on raw dicts)
# ======================================================================

def _collect_forbidden_keys(obj: Any, path: str, violations: List[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            for forbidden in _FORBIDDEN_KEYS:
                if forbidden in key_lower or key_lower == forbidden:
                    violations.append(f"Forbidden key {key!r} at {path}: SkillSpec v1 prohibits '{forbidden}'")
            if key_lower in _PATH_SENSITIVE_KEYS or any(kw in key_lower for kw in ("_path", "_file", "_dir")):
                if isinstance(value, str) and _PATH_RE.match(value):
                    if not _URL_RE.match(value):
                        violations.append(f"File-system path in {key!r} at {path}: {value!r} — arbitrary file paths are forbidden in v1")
            _collect_forbidden_keys(value, f"{path}.{key}", violations)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _collect_forbidden_keys(item, f"{path}[{idx}]", violations)
    elif isinstance(obj, str):
        if _PATH_RE.match(obj) and not _URL_RE.match(obj):
            violations.append(f"Arbitrary file path at {path}: {obj!r} — forbidden in v1")


def _collect_unregistered_network(obj: Any, path: str, allowed_domains: set, violations: List[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            _collect_unregistered_network(value, f"{path}.{key}", allowed_domains, violations)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _collect_unregistered_network(item, f"{path}[{idx}]", allowed_domains, violations)
    elif isinstance(obj, str):
        if _URL_RE.match(obj):
            m = re.match(r"^https?://([^/:\s]+)", obj)
            if m:
                host = m.group(1)
                if host not in allowed_domains and "*" not in allowed_domains:
                    violations.append(f"Unregistered network domain {host!r} at {path}: not in permissions.network_domains {sorted(allowed_domains)}")


def validate_skill_spec(spec: dict) -> List[str]:
    violations: List[str] = []
    if not isinstance(spec, dict):
        return ["SkillSpec must be a dict"]
    for key in ("id", "description"):
        if key not in spec:
            violations.append(f"Missing required key: {key!r}")
        elif not isinstance(spec[key], str) or not spec[key].strip():
            violations.append(f"{key!r} must be a non-empty string")
    _collect_forbidden_keys(spec, "<root>", violations)
    perms = spec.get("permissions", {})
    allowed = set(perms.get("network_domains", [])) if isinstance(perms, dict) else set()
    _collect_unregistered_network(spec, "<root>", allowed, violations)
    return violations
