# -*- coding: utf-8 -*-
"""
SkillSpec loader — reads YAML skill manifests, validates them, and returns
``SkillSpec`` instances.

Public API:
    load_skill(path: Path) -> SkillSpec
    load_builtin_skills() -> List[SkillSpec]
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List

import yaml

from augur.skill_spec import (
    SkillSpec,
    SkillPermissions,
    EvidencePolicy,
    WorkflowStep,
    SkillEvals,
    EvalFixture,
    EvalGate,
    validate_skill_spec,
)


# ---------------------------------------------------------------------------
# Helpers — map YAML field names to SkillSpec field names
# ---------------------------------------------------------------------------

def _map_evidence_policy(raw: dict) -> dict:
    """Map ``missing`` (YAML) → ``missing_strategy`` (SkillSpec)."""
    mapped = dict(raw)
    if "missing" in mapped:
        mapped["missing_strategy"] = mapped.pop("missing")
    return mapped


def _map_evals(raw: dict) -> dict:
    """Map string-based eval fixtures/gates to structured objects.

    YAML:
        fixtures: [earnings-prep-v1]
        gates: [citation_validity]

    SkillSpec:
        fixtures: [{"input": {}, "expected_output": {}}]
        gates: [{"metric": "...", "threshold": 0.0}]
    """
    mapped: Dict[str, Any] = {}
    fixtures = raw.get("fixtures", [])
    if isinstance(fixtures, list) and fixtures and isinstance(fixtures[0], str):
        mapped["fixtures"] = [
            {"input": {"fixture_id": name}, "expected_output": {}}
            for name in fixtures
        ]
    else:
        mapped["fixtures"] = fixtures

    gates = raw.get("gates", [])
    if isinstance(gates, list) and gates and isinstance(gates[0], str):
        mapped["gates"] = [
            {"metric": name, "threshold": 0.0} for name in gates
        ]
    else:
        mapped["gates"] = gates

    return mapped


def _map_compatibility(raw: Any) -> dict:
    """Normalise compatibility to the dict form SkillSpec expects.

    YAML may use a plain string (e.g. ``">=11,<12"``); convert it to
    ``{"augur": ">=11,<12"}``.
    """
    if isinstance(raw, str):
        return {"augur": raw}
    if isinstance(raw, dict):
        return raw
    return {}


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------

def load_skill(path: Path) -> SkillSpec:
    """Load a SkillSpec from a YAML file, validate it, and return the model.

    Raises ``ValueError`` with all validation violations if the spec is
    invalid.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Skill YAML at {path} must be a mapping, got {type(raw).__name__}")

    # 1. Validate the raw dict against v1 constraints
    violations = validate_skill_spec(raw)
    if violations:
        raise ValueError(
            f"Skill {raw.get('id', path.name)!r} validation failed:\n" +
            "\n".join(f"  - {v}" for v in violations)
        )

    # 2. Map YAML field names → SkillSpec field names
    spec_dict = copy.deepcopy(raw)

    if "compatibility" in spec_dict:
        spec_dict["compatibility"] = _map_compatibility(spec_dict["compatibility"])

    if "evidence_policy" in spec_dict:
        spec_dict["evidence_policy"] = _map_evidence_policy(spec_dict["evidence_policy"])

    if "evals" in spec_dict:
        spec_dict["evals"] = _map_evals(spec_dict["evals"])

    # 3. Build SkillSpec
    return SkillSpec.from_dict(spec_dict)


def load_builtin_skills() -> List[SkillSpec]:
    """Load every built-in SkillSpec from the ``skills/`` sibling directory.

    Returns them in filesystem order.
    """
    skills_dir = Path(__file__).resolve().parent
    yaml_files = sorted(skills_dir.glob("*.yaml"))
    specs: List[SkillSpec] = []
    for yf in yaml_files:
        # Skip non-skill YAML files (e.g. __init__ placeholders)
        if yf.name.startswith("_"):
            continue
        spec = load_skill(yf)
        specs.append(spec)
    return specs
