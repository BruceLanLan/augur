# -*- coding: utf-8 -*-
"""
Re-export SkillSpec v1 from augur.schemas.skill_spec.

This module exists for backward-compatibility with code that imports
from ``augur.skill_spec``.  New code should import directly from
``augur.schemas``.
"""

from augur.schemas.skill_spec import (
    EvalFixture,
    EvalGate,
    EvidencePolicy,
    SkillEvals,
    SkillPermissions,
    SkillSpec,
    WorkflowStep,
    validate_skill_spec,
)

__all__ = [
    "EvalFixture",
    "EvalGate",
    "SkillSpec",
    "SkillPermissions",
    "EvidencePolicy",
    "WorkflowStep",
    "SkillEvals",
    "validate_skill_spec",
]
