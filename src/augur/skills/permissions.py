# -*- coding: utf-8 -*-
"""
Skill permission enforcer and citation validator (E1.6).

Provides runtime enforcement of SkillSpec v1 permissions and
post-execution citation validation against the evidence ledger.
"""

from __future__ import annotations

from typing import Dict, List, Set

from augur.schemas.skill_spec import SkillSpec


class SkillPermissionError(Exception):
    """Raised when a Skill attempts a forbidden action."""


class CitationValidationError(Exception):
    """Raised when a Skill output fails citation validation."""


class SkillPermissionEnforcer:
    """Runtime enforcer for SkillSpec v1 permissions.

    Checks every capability invocation, network request, and file access
    against the Skill's declared permissions before execution.
    """

    def __init__(self, spec: SkillSpec):
        self._spec = spec
        self._allowed_resources: Set[str] = set(spec.permissions.resources)
        self._allowed_domains: Set[str] = set(spec.permissions.network_domains)
        self._allowed_paths: Set[str] = set(getattr(spec.permissions, "file_paths", []))
        self._audit_log: List[str] = []

    # ------------------------------------------------------------------
    # Permission checks
    # ------------------------------------------------------------------

    def check_capability(self, capability_name: str) -> None:
        """Verify that *capability_name* is in the skill's required_capabilities."""
        if capability_name not in self._spec.required_capabilities:
            self._audit_log.append(
                f"DENIED capability '{capability_name}' — not in required_capabilities"
            )
            raise SkillPermissionError(
                f"Skill '{self._spec.id}' cannot use capability "
                f"'{capability_name}': not declared in required_capabilities"
            )

    def check_resource(self, resource: str) -> None:
        """Verify that *resource* is in the skill's allowed resources.

        Resource permissions use prefix matching:
        ``"evidence.read"`` matches ``"evidence.read.financials"``.
        """
        for allowed in self._allowed_resources:
            if resource == allowed or resource.startswith(allowed + "."):
                return
        self._audit_log.append(
            f"DENIED resource '{resource}' — not in permissions.resources"
        )
        raise SkillPermissionError(
            f"Skill '{self._spec.id}' cannot access resource "
            f"'{resource}': not in permissions.resources"
        )

    def check_network(self, domain: str) -> None:
        """Verify that *domain* is in the skill's allowed network domains.

        If ``permissions.network_domains`` is empty, all network access
        is denied.
        """
        if not self._allowed_domains:
            self._audit_log.append(
                f"DENIED network access to '{domain}' — "
                f"skill has no network_domains declared"
            )
            raise SkillPermissionError(
                f"Skill '{self._spec.id}' cannot access network: "
                f"no network_domains declared in permissions"
            )
        for allowed in self._allowed_domains:
            if domain == allowed or domain.endswith("." + allowed):
                return
        self._audit_log.append(
            f"DENIED network domain '{domain}' — not in permissions.network_domains"
        )
        raise SkillPermissionError(
            f"Skill '{self._spec.id}' cannot access domain "
            f"'{domain}': not in permissions.network_domains"
        )

    def check_file_path(self, path: str) -> None:
        """Verify that *path* is in the skill's allowed file paths.

        If ``permissions.file_paths`` is empty, all file access is denied
        (v1 default).
        """
        if not self._allowed_paths:
            self._audit_log.append(
                f"DENIED file access to '{path}' — "
                f"skill has no file_paths declared (v1 default: no file access)"
            )
            raise SkillPermissionError(
                f"Skill '{self._spec.id}' cannot access file path "
                f"'{path}': no file_paths declared in permissions (v1 default)"
            )
        if path not in self._allowed_paths:
            self._audit_log.append(
                f"DENIED file path '{path}' — not in permissions.file_paths"
            )
            raise SkillPermissionError(
                f"Skill '{self._spec.id}' cannot access file path "
                f"'{path}': not in permissions.file_paths"
            )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    @property
    def audit_log(self) -> List[str]:
        """Read-only view of the permission audit trail."""
        return list(self._audit_log)


class CitationValidator:
    """Post-execution citation validator.

    Checks that a Skill's output claims have corresponding evidence
    and that the minimum claim coverage threshold is met.
    """

    def __init__(self, spec: SkillSpec):
        self._spec = spec
        self._min_coverage = spec.evidence_policy.min_claim_coverage

    def validate_claims(
        self,
        claims: List[dict],
        evidence_manifest: Dict[str, dict],
    ) -> Dict[str, any]:
        """Validate claims against the evidence manifest.

        Args:
            claims: List of claim dicts, each with at least ``claim_id``
                and ``supports``/``contradicts`` evidence ID lists.
            evidence_manifest: Dict mapping evidence_id → evidence metadata.

        Returns:
            Dict with ``valid`` (bool), ``coverage`` (float),
            ``unresolved_claims`` (List[str]), and ``missing_evidence``
            (List[str]).
        """
        total = len(claims)
        if total == 0:
            return {
                "valid": False,
                "coverage": 0.0,
                "unresolved_claims": [],
                "missing_evidence": [],
                "reason": "No claims produced",
            }

        resolved = 0
        unresolved_claims: List[str] = []
        missing_evidence: List[str] = []

        for claim in claims:
            claim_id = claim.get("claim_id", "unknown")
            all_refs = set(
                claim.get("supports", [])
                + claim.get("contradicts", [])
                + claim.get("insufficient", [])
            )

            # Every evidence reference must exist in the manifest
            claim_resolved = True
            for ref in all_refs:
                if ref not in evidence_manifest:
                    missing_evidence.append(ref)
                    claim_resolved = False

            if claim_resolved and all_refs:
                resolved += 1
            else:
                unresolved_claims.append(claim_id)

        coverage = resolved / total

        return {
            "valid": coverage >= self._min_coverage,
            "coverage": coverage,
            "unresolved_claims": unresolved_claims,
            "missing_evidence": missing_evidence,
            "threshold": self._min_coverage,
        }
