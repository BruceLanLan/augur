# -*- coding: utf-8 -*-
"""
augur.schemas — Frozen v1 schema definitions (E1.1).

Exports:
    EvidenceItem, generate_evidence_id
    Claim, ClaimClassification, ClaimStatus, ConfidenceSource, generate_claim_id
    StepResult, StepStatus
    RunBundle, RunManifest, CoverageStats, generate_run_id
"""

from augur.schemas.evidence import EvidenceItem, generate_evidence_id
from augur.schemas.claim import (
    Claim,
    ClaimClassification,
    ClaimStatus,
    ConfidenceSource,
    generate_claim_id,
)
from augur.schemas.step_result import StepResult, StepStatus
from augur.schemas.run_bundle import (
    CoverageStats,
    RunBundle,
    RunManifest,
    generate_run_id,
)
from augur.schemas.skill_spec import (
    EvidencePolicy,
    SkillEvals,
    SkillPermissions,
    SkillSpec,
    WorkflowStep,
    validate_skill_spec,
)

__all__ = [
    # Evidence
    "EvidenceItem",
    "generate_evidence_id",
    # Claim
    "Claim",
    "ClaimClassification",
    "ClaimStatus",
    "ConfidenceSource",
    "generate_claim_id",
    # StepResult
    "StepResult",
    "StepStatus",
    # RunBundle
    "RunBundle",
    "RunManifest",
    "CoverageStats",
    "generate_run_id",
    # SkillSpec
    "SkillSpec",
    "SkillPermissions",
    "EvidencePolicy",
    "WorkflowStep",
    "SkillEvals",
    "validate_skill_spec",
]
