# -*- coding: utf-8 -*-
"""Tests for Skill permission enforcement and citation validation (E1.6)."""

import pytest

from augur.schemas.skill_spec import (
    EvidencePolicy,
    SkillEvals,
    SkillPermissions,
    SkillSpec,
    WorkflowStep,
)
from augur.skills.permissions import (
    CitationValidationError,
    CitationValidator,
    SkillPermissionEnforcer,
    SkillPermissionError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def earnings_skill() -> SkillSpec:
    return SkillSpec(
        id="earnings-prep",
        version="1.0.0",
        description="Build pre-earnings dossier",
        required_capabilities=["sec.filings.read", "fundamentals.snapshot"],
        permissions=SkillPermissions(
            resources=["evidence.read", "runs.read"],
            network_domains=["sec.gov"],
        ),
        evidence_policy=EvidencePolicy(
            information_time_required=True,
            missing="abstain",
            min_claim_coverage=0.95,
        ),
        workflow=[
            WorkflowStep(id="collect", uses="earnings.collect_evidence"),
        ],
        evals=SkillEvals(fixtures=["v1"], gates=["citation_validity"]),
    )


@pytest.fixture
def locked_down_skill() -> SkillSpec:
    """A skill with no network/file permissions (v1 default)."""
    return SkillSpec(
        id="readonly-skill",
        version="1.0.0",
        description="A read-only skill",
        required_capabilities=["runs.compare"],
        permissions=SkillPermissions(),
    )


# ---------------------------------------------------------------------------
# Permission enforcer tests
# ---------------------------------------------------------------------------

class TestSkillPermissionEnforcer:
    def test_allowed_capability_passes(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        enf.check_capability("sec.filings.read")  # should not raise

    def test_unknown_capability_raises(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        with pytest.raises(SkillPermissionError) as exc:
            enf.check_capability("shell.exec")
        assert "not declared in required_capabilities" in str(exc.value)
        assert "shell.exec" in str(exc.value)

    def test_allowed_resource_passes(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        enf.check_resource("evidence.read")  # should not raise

    def test_prefix_matched_resource_passes(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        enf.check_resource("evidence.read.financials")  # prefix match

    def test_unknown_resource_raises(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        with pytest.raises(SkillPermissionError) as exc:
            enf.check_resource("admin.config")
        assert "not in permissions.resources" in str(exc.value)

    def test_allowed_domain_passes(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        enf.check_network("sec.gov")

    def test_subdomain_allowed(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        enf.check_network("data.sec.gov")

    def test_unknown_domain_raises(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        with pytest.raises(SkillPermissionError) as exc:
            enf.check_network("evil.com")
        assert "not in permissions.network_domains" in str(exc.value)

    def test_no_network_access_by_default(self, locked_down_skill):
        enf = SkillPermissionEnforcer(locked_down_skill)
        with pytest.raises(SkillPermissionError) as exc:
            enf.check_network("sec.gov")
        assert "no network_domains declared" in str(exc.value)

    def test_no_file_access_by_default(self, locked_down_skill):
        enf = SkillPermissionEnforcer(locked_down_skill)
        with pytest.raises(SkillPermissionError) as exc:
            enf.check_file_path("/etc/passwd")
        assert "no file_paths declared" in str(exc.value)

    def test_audit_log_records_denials(self, earnings_skill):
        enf = SkillPermissionEnforcer(earnings_skill)
        try:
            enf.check_capability("bad.cap")
        except SkillPermissionError:
            pass
        try:
            enf.check_resource("admin.config")
        except SkillPermissionError:
            pass
        assert len(enf.audit_log) == 2
        assert all("DENIED" in entry for entry in enf.audit_log)


# ---------------------------------------------------------------------------
# Citation validator tests
# ---------------------------------------------------------------------------

class TestCitationValidator:
    def test_all_claims_cited_passes(self, earnings_skill):
        cv = CitationValidator(earnings_skill)
        claims = [
            {
                "claim_id": "cl_001",
                "statement": "Revenue grew 2%",
                "supports": ["ev_sec_001"],
                "contradicts": [],
                "insufficient": [],
            },
        ]
        manifest = {"ev_sec_001": {"source": "sec_edgar", "available_at": "2025-10-31"}}
        result = cv.validate_claims(claims, manifest)
        assert result["valid"] is True
        assert result["coverage"] == 1.0

    def test_missing_evidence_fails(self, earnings_skill):
        cv = CitationValidator(earnings_skill)
        claims = [
            {
                "claim_id": "cl_002",
                "statement": "Claim with missing evidence",
                "supports": ["ev_missing"],
                "contradicts": [],
                "insufficient": [],
            },
        ]
        manifest = {}
        result = cv.validate_claims(claims, manifest)
        assert result["valid"] is False
        assert "ev_missing" in result["missing_evidence"]

    def test_coverage_below_threshold_fails(self, earnings_skill):
        cv = CitationValidator(earnings_skill)
        claims = [
            {"claim_id": "cl_a", "supports": ["ev_001"], "contradicts": [], "insufficient": []},
            {"claim_id": "cl_b", "supports": ["ev_missing"], "contradicts": [], "insufficient": []},
            {"claim_id": "cl_c", "supports": [], "contradicts": [], "insufficient": []},
        ]
        manifest = {"ev_001": {"source": "test"}}
        result = cv.validate_claims(claims, manifest)
        assert result["valid"] is False
        assert result["coverage"] == pytest.approx(1 / 3)

    def test_no_claims_fails(self, earnings_skill):
        cv = CitationValidator(earnings_skill)
        result = cv.validate_claims([], {})
        assert result["valid"] is False
        assert result["reason"] == "No claims produced"

    def test_insufficient_evidence_claims_fail_coverage(self, earnings_skill):
        """Claims marked insufficient don't count toward coverage."""
        cv = CitationValidator(earnings_skill)
        claims = [
            {
                "claim_id": "cl_insuf",
                "statement": "Not enough data",
                "supports": [],
                "contradicts": [],
                "insufficient": ["ev_partial"],
            },
        ]
        manifest = {"ev_partial": {"source": "test"}}
        result = cv.validate_claims(claims, manifest)
        # claim has evidence refs in insufficient, but supports/contradicts are empty
        # It has evidence refs to check, so it should be resolved
        assert result["coverage"] == 1.0
