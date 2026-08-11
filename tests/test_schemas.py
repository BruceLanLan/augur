# -*- coding: utf-8 -*-
"""
Round-trip, validation, and backward-compatibility tests for E1.1 frozen schemas.

Covers:
  - EvidenceItem, Claim, StepResult, RunBundle  round-trip
  - SkillSpec v1 validator (forbidden keys, file paths, unregistered network)
  - EvidenceItem available_at substitution rejection
  - Backward-compat: old-schema fixtures produce clear errors, not silent loads
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from augur.schemas import (
    Claim,
    ClaimClassification,
    ClaimStatus,
    ConfidenceSource,
    CoverageStats,
    EvidenceItem,
    RunBundle,
    RunManifest,
    StepResult,
    StepStatus,
    generate_claim_id,
    generate_evidence_id,
    generate_run_id,
)
from augur.schemas.skill_spec import SkillSpec, validate_skill_spec

# ---------------------------------------------------------------------------
# Path to fixture directory
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# ======================================================================
# EvidenceItem round-trip
# ======================================================================

class TestEvidenceItemRoundTrip:
    """EvidenceItem: JSON serialize → deserialize → field equality."""

    @staticmethod
    def make_full() -> EvidenceItem:
        content_hash = "abcdef1234567890abcdef1234567890abcdef12"
        eid = generate_evidence_id("sec_edgar", content_hash)
        return EvidenceItem(
            evidence_id=eid,
            source="sec_edgar",
            source_locator="https://www.sec.gov/Archives/edgar/data/320193/0000320193-25-000001.txt",
            content_hash=content_hash,
            instrument="AAPL",
            metric="eps_diluted",
            value=2.40,
            unit="USD",
            currency="USD",
            effective_at=datetime(2024, 12, 28, tzinfo=timezone.utc),
            available_at=datetime(2025, 1, 30, 14, 0, tzinfo=timezone.utc),
            retrieved_at=datetime(2025, 1, 30, 18, 5, tzinfo=timezone.utc),
            transform_version="2.1",
            schema_version="1.0",
            code_version="10.15.0",
            coverage=1.0,
            missing=False,
            degraded=False,
            license="CC0-1.0",
            redistribution_allowed=True,
            metadata={"cik": "0000320193"},
        )

    def test_round_trip_full(self):
        """Full EvidenceItem survives JSON round-trip with all fields intact."""
        original = self.make_full()
        data = original.model_dump(mode="json")
        restored = EvidenceItem.model_validate(data)
        assert restored == original

    def test_round_trip_minimal(self):
        """Minimal EvidenceItem (only required fields) survives round-trip."""
        content_hash = "deadbeef" * 8  # 64 chars
        eid = generate_evidence_id("yfinance", content_hash)
        original = EvidenceItem(
            evidence_id=eid,
            source="yfinance",
            content_hash=content_hash,
        )
        data = original.model_dump(mode="json")
        restored = EvidenceItem.model_validate(data)
        assert restored == original

    def test_available_at_substitution_rejected(self):
        """Setting available_at == retrieved_at must raise ValidationError."""
        content_hash = "aaaa" * 16
        eid = generate_evidence_id("test", content_hash)
        now = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                evidence_id=eid,
                source="test",
                content_hash=content_hash,
                available_at=now,
                retrieved_at=now,
            )
        msg = str(exc_info.value).lower()
        assert "available_at" in msg
        assert "retrieved_at" in msg
        assert "substitut" in msg or "equal" in msg

    def test_evidence_id_prefix_mismatch_rejected(self):
        """evidence_id must start with ev_{source}_."""
        content_hash = "bbbb" * 16
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                evidence_id="ev_wrong_source_bbbbbbbbbbbb",
                source="actual_source",
                content_hash=content_hash,
            )
        assert "evidence_id" in str(exc_info.value).lower()

    def test_missing_required_fields(self):
        """Missing required fields produce a clear ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(source="test")  # type: ignore[arg-type]
        errors = str(exc_info.value)
        assert "evidence_id" in errors or "content_hash" in errors


# ======================================================================
# Claim round-trip
# ======================================================================

class TestClaimRoundTrip:
    """Claim: JSON serialize → deserialize → field equality."""

    @staticmethod
    def make_full() -> Claim:
        text = "AAPL Q1 FY2025 revenue will exceed $120B"
        cid = generate_claim_id(text)
        return Claim(
            claim_id=cid,
            text=text,
            persona_id="buffett_agent",
            supports=["ev_sec_edgar_abcdef123456", "ev_yfinance_123456abcdef"],
            contradicts=["ev_macro_contrarian001"],
            insufficient=[],
            classification=ClaimClassification.INFERENCE,
            confidence=0.75,
            confidence_source=ConfidenceSource.CALIBRATED_MODEL,
            status=ClaimStatus.ACTIVE,
            metadata={"ticker": "AAPL"},
        )

    def test_round_trip_full(self):
        original = self.make_full()
        data = original.model_dump(mode="json")
        restored = Claim.model_validate(data)
        assert restored == original

    def test_round_trip_minimal(self):
        text = "Simple fact claim"
        cid = generate_claim_id(text)
        original = Claim(
            claim_id=cid,
            text=text,
            persona_id="test_agent",
            classification=ClaimClassification.FACT,
            status=ClaimStatus.UNKNOWN,
        )
        data = original.model_dump(mode="json")
        restored = Claim.model_validate(data)
        assert restored == original

    def test_confidence_without_source_rejected(self):
        """Confidence without confidence_source must be rejected."""
        text = "Test"
        cid = generate_claim_id(text)
        with pytest.raises(ValidationError) as exc_info:
            Claim(
                claim_id=cid,
                text=text,
                persona_id="test",
                classification=ClaimClassification.FACT,
                confidence=0.5,
                # confidence_source missing
            )
        assert "confidence_source" in str(exc_info.value).lower()

    def test_insufficient_evidence_must_abstain(self):
        """No supports + no contradicts → status must be unknown/abstain."""
        text = "A claim with no evidence"
        cid = generate_claim_id(text)
        with pytest.raises(ValidationError) as exc_info:
            Claim(
                claim_id=cid,
                text=text,
                persona_id="test",
                classification=ClaimClassification.FACT,
                status=ClaimStatus.ACTIVE,  # should be unknown/abstain
            )
        assert "unknown" in str(exc_info.value).lower() or "abstain" in str(exc_info.value).lower()


# ======================================================================
# StepResult round-trip
# ======================================================================

class TestStepResultRoundTrip:
    """StepResult: JSON serialize → deserialize → field equality."""

    @staticmethod
    def make_full() -> StepResult:
        return StepResult(
            step_id="step_001",
            step_name="fetch_earnings",
            status=StepStatus.SUCCESS,
            input_refs=["ev_sec_edgar_abcdef123456"],
            output_refs=["ev_sec_edgar_parsed001"],
            result={"eps": 2.40, "revenue": 1.2e11},
            diagnostics=None,
            provenance="runner-01/10.15.0",
            elapsed_ms=1250.5,
            content_hash="sha256:feedface",
            started_at=datetime(2025, 1, 30, 14, 0, tzinfo=timezone.utc),
            finished_at=datetime(2025, 1, 30, 14, 0, 1, tzinfo=timezone.utc),
            metadata={"retry": 0},
        )

    def test_round_trip_full(self):
        original = self.make_full()
        data = original.model_dump(mode="json")
        restored = StepResult.model_validate(data)
        assert restored == original

    def test_round_trip_minimal(self):
        original = StepResult(
            step_id="step_min",
            step_name="minimal_step",
            status=StepStatus.SUCCESS,
        )
        data = original.model_dump(mode="json")
        restored = StepResult.model_validate(data)
        assert restored == original

    def test_plain_string_result_rejected(self):
        """A plain-string result must be rejected as not-typed."""
        with pytest.raises(ValidationError) as exc_info:
            StepResult(
                step_id="s1",
                step_name="bad_step",
                status=StepStatus.FAILURE,
                result="this is a plain string",  # forbidden
            )
        assert "string" in str(exc_info.value).lower() or "typed" in str(exc_info.value).lower()


# ======================================================================
# RunBundle round-trip
# ======================================================================

class TestRunBundleRoundTrip:
    """RunBundle: JSON serialize → deserialize → field equality."""

    NOW = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)

    @staticmethod
    def make_full() -> RunBundle:
        manifest = RunManifest(
            input_snapshot_hash="abc123def456",
            config_version="2.0",
            model_version="gpt-4o-2025-05",
            code_version="10.15.0",
        )
        step = StepResult(
            step_id="s1",
            step_name="fetch",
            status=StepStatus.SUCCESS,
            result={"price": 150.25},
        )
        rid = generate_run_id(
            "AAPL",
            TestRunBundleRoundTrip.NOW,
            "abcdef1234567890",
        )
        return RunBundle(
            run_id=rid,
            created_at=TestRunBundleRoundTrip.NOW,
            supersedes=None,
            manifest=manifest,
            step_results=[step],
            coverage=CoverageStats(
                total_evidence=10,
                covered_evidence=9,
                missing_evidence=1,
                degraded_evidence=0,
                coverage_ratio=0.9,
            ),
            metadata={"trigger": "cron"},
        )

    def test_round_trip_full(self):
        original = self.make_full()
        data = original.model_dump(mode="json")
        restored = RunBundle.model_validate(data)
        assert restored == original

    def test_supersedes_self_rejected(self):
        """A run cannot supersede itself."""
        rid = "run_AAPL_20250601T120000_deadbeef"
        manifest = RunManifest(
            input_snapshot_hash="h",
            config_version="v1",
            model_version="m1",
            code_version="c1",
        )
        step = StepResult(
            step_id="s1",
            step_name="fetch",
            status=StepStatus.SUCCESS,
        )
        with pytest.raises(ValidationError) as exc_info:
            RunBundle(
                run_id=rid,
                created_at=self.NOW,
                supersedes=rid,  # self-reference
                manifest=manifest,
                step_results=[step],
            )
        assert "supersede" in str(exc_info.value).lower() or "self" in str(exc_info.value).lower()

    def test_empty_step_results_rejected(self):
        """A run must have at least one StepResult."""
        rid = "run_AAPL_20250601T120000_deadbeef"
        manifest = RunManifest(
            input_snapshot_hash="h",
            config_version="v1",
            model_version="m1",
            code_version="c1",
        )
        with pytest.raises(ValidationError) as exc_info:
            RunBundle(
                run_id=rid,
                created_at=self.NOW,
                manifest=manifest,
                step_results=[],  # empty
            )
        assert "step" in str(exc_info.value).lower()


# ======================================================================
# SkillSpec validator
# ======================================================================

class TestSkillSpecValidator:
    """validate_skill_spec() rejects forbidden patterns."""

    def test_valid_skill_spec_passes(self):
        """A clean SkillSpec dict produces zero violations."""
        spec = {
            "id": "earnings-prep",
            "version": "1.0.0",
            "description": "Prepare earnings analysis data",
            "permissions": {
                "network_domains": ["api.sec.gov"],
            },
            "workflow": [
                {"id": "fetch", "uses": "edgar:fetch", "needs": []},
            ],
        }
        violations = validate_skill_spec(spec)
        assert violations == [], f"Unexpected violations: {violations}"

    def test_module_path_rejected(self):
        spec = {
            "id": "bad-skill",
            "description": "Has module_path",
            "module_path": "/opt/skills/bad.py",
        }
        violations = validate_skill_spec(spec)
        assert any("module_path" in v.lower() for v in violations), violations

    def test_import_key_rejected(self):
        spec = {
            "id": "bad-skill",
            "description": "Has import",
            "import": "some_library",
        }
        violations = validate_skill_spec(spec)
        assert any("import" in v.lower() for v in violations), violations

    def test_shell_key_rejected(self):
        spec = {
            "id": "bad-skill",
            "description": "Has shell",
            "shell": "rm -rf /",
        }
        violations = validate_skill_spec(spec)
        assert any("shell" in v.lower() for v in violations), violations

    def test_exec_key_rejected(self):
        spec = {
            "id": "bad-skill",
            "description": "Has exec",
            "exec": "print('hello')",
        }
        violations = validate_skill_spec(spec)
        assert any("exec" in v.lower() for v in violations), violations

    def test_eval_key_rejected(self):
        spec = {
            "id": "bad-skill",
            "description": "Has eval",
            "eval": "1 + 1",
        }
        violations = validate_skill_spec(spec)
        assert any("eval" in v.lower() for v in violations), violations

    def test_subprocess_key_rejected(self):
        spec = {
            "id": "bad-skill",
            "description": "Has subprocess",
            "subprocess": True,
        }
        violations = validate_skill_spec(spec)
        assert any("subprocess" in v.lower() for v in violations), violations

    def test_os_system_key_rejected(self):
        spec = {
            "id": "bad-skill",
            "description": "Has os.system",
            "os.system": "ls",
        }
        violations = validate_skill_spec(spec)
        assert any("os.system" in v.lower() for v in violations), violations

    def test_arbitrary_file_path_rejected(self):
        """A string value that looks like an absolute file path must be flagged."""
        spec = {
            "id": "bad-skill",
            "description": "Has a path value",
            "entrypoint": "/usr/local/bin/tool",
        }
        violations = validate_skill_spec(spec)
        assert any("file" in v.lower() or "path" in v.lower() for v in violations), violations

    def test_relative_file_path_rejected(self):
        spec = {
            "id": "bad-skill",
            "description": "Has relative path",
            "script_path": "./run.sh",
        }
        violations = validate_skill_spec(spec)
        assert any("path" in v.lower() for v in violations), violations

    def test_url_allowed_when_registered(self):
        """URLs whose domain is in network_domains must NOT be flagged."""
        spec = {
            "id": "net-safe",
            "description": "Uses registered domain",
            "permissions": {
                "network_domains": ["api.sec.gov"],
            },
            "workflow": [
                {
                    "id": "fetch",
                    "uses": "https://api.sec.gov/edgar/data",
                    "needs": [],
                },
            ],
        }
        violations = validate_skill_spec(spec)
        assert violations == [], f"Unexpected violations: {violations}"

    def test_unregistered_network_rejected(self):
        """URLs whose domain is NOT in network_domains must be flagged."""
        spec = {
            "id": "net-bad",
            "description": "Uses unregistered domain",
            "permissions": {
                "network_domains": ["api.sec.gov"],
            },
            "workflow": [
                {
                    "id": "fetch",
                    "uses": "https://evil.example.com/steal",
                    "needs": [],
                },
            ],
        }
        violations = validate_skill_spec(spec)
        assert any("evil.example.com" in v for v in violations), violations

    def test_not_a_dict(self):
        violations = validate_skill_spec("not a dict")  # type: ignore[arg-type]
        assert len(violations) >= 1
        assert "dict" in violations[0].lower()

    def test_missing_id(self):
        spec = {"description": "No id here"}
        violations = validate_skill_spec(spec)
        assert any("id" in v.lower() for v in violations), violations

    def test_missing_description(self):
        spec = {"id": "no-desc"}
        violations = validate_skill_spec(spec)
        assert any("description" in v.lower() for v in violations), violations


# ======================================================================
# SkillSpec Pydantic model round-trip
# ======================================================================

class TestSkillSpecRoundTrip:
    """SkillSpec Pydantic model: JSON serialize → deserialize → equality."""

    def test_round_trip_full(self):
        from augur.schemas.skill_spec import (
            EvalFixture,
            EvalGate,
            EvidencePolicy,
            MissingStrategy,
            SkillEvals,
            SkillPermissions,
            WorkflowStep,
        )

        original = SkillSpec(
            id="earnings-prep",
            version="1.0.0",
            description="Prepare earnings analysis data from SEC EDGAR",
            license="MIT",
            compatibility={"augur": ">=10.15"},
            inputs_schema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "fiscal_quarter": {"type": "string"},
                },
                "required": ["ticker"],
            },
            required_capabilities=["edgar:fetch", "edgar:parse"],
            permissions=SkillPermissions(
                resources=["edgar:filings"],
                network_domains=["api.sec.gov"],
            ),
            evidence_policy=EvidencePolicy(
                information_time_required=True,
                missing_strategy=MissingStrategy.ABSTAIN,
                min_claim_coverage=0.5,
            ),
            workflow=[
                WorkflowStep(
                    id="fetch",
                    uses="edgar:fetch",
                    needs=[],
                ),
                WorkflowStep(
                    id="parse",
                    uses="edgar:parse_xbrl",
                    needs=["fetch"],
                ),
            ],
            outputs_schema={
                "type": "object",
                "properties": {
                    "eps": {"type": "number"},
                    "revenue": {"type": "number"},
                },
            },
            evals=SkillEvals(
                fixtures=[
                    EvalFixture(
                        input={"ticker": "AAPL"},
                        expected_output={"eps": 2.40},
                    ),
                ],
                gates=[
                    EvalGate(metric="accuracy", threshold=0.9),
                ],
            ),
        )

        data = original.model_dump(mode="json")
        restored = SkillSpec.model_validate(data)
        assert restored == original

    def test_duplicate_workflow_step_ids_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            SkillSpec(
                id="dup-steps",
                description="Has duplicate step ids",
                workflow=[
                    {"id": "fetch", "uses": "x"},
                    {"id": "fetch", "uses": "y"},
                ],
            )
        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


# ======================================================================
# Backward-compatibility: old-schema fixtures → clear errors
# ======================================================================

class TestBackwardCompat:
    """Old-schema fixture files must produce clear ValidationError, not silent loads."""

    def test_old_evidence_rejected(self):
        path = os.path.join(FIXTURES_DIR, "old_evidence.json")
        with open(path) as fh:
            data = json.load(fh)
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem.model_validate(data)
        msg = str(exc_info.value)
        # Must mention missing fields, not silently succeed
        assert "evidence_id" in msg or "content_hash" in msg or "field required" in msg.lower()

    def test_old_claim_rejected(self):
        path = os.path.join(FIXTURES_DIR, "old_claim.json")
        with open(path) as fh:
            data = json.load(fh)
        with pytest.raises(ValidationError) as exc_info:
            Claim.model_validate(data)
        msg = str(exc_info.value)
        assert "claim_id" in msg or "persona_id" in msg or "classification" in msg or "field required" in msg.lower()

    def test_old_step_result_rejected(self):
        path = os.path.join(FIXTURES_DIR, "old_step_result.json")
        with open(path) as fh:
            data = json.load(fh)
        with pytest.raises(ValidationError) as exc_info:
            StepResult.model_validate(data)
        msg = str(exc_info.value)
        assert "step_id" in msg or "field required" in msg.lower()

    def test_old_run_bundle_rejected(self):
        path = os.path.join(FIXTURES_DIR, "old_run_bundle.json")
        with open(path) as fh:
            data = json.load(fh)
        with pytest.raises(ValidationError) as exc_info:
            RunBundle.model_validate(data)
        msg = str(exc_info.value)
        assert "manifest" in msg or "created_at" in msg or "step" in msg or "field required" in msg.lower()

    def test_old_skill_spec_rejected(self):
        path = os.path.join(FIXTURES_DIR, "old_skill_spec.json")
        with open(path) as fh:
            data = json.load(fh)
        violations = validate_skill_spec(data)
        assert len(violations) >= 3, (
            f"Expected at least 3 violations (module_path, import, shell, unregistered network), "
            f"got {len(violations)}: {violations}"
        )
        # Verify specific violations
        combined = " ".join(violations).lower()
        assert "module_path" in combined
        assert "import" in combined
        assert "shell" in combined
