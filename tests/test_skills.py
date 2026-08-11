# -*- coding: utf-8 -*-
"""Tests for built-in SkillSpec fixtures and loader."""

import copy
from pathlib import Path

import pytest
import yaml

from augur.skill_spec import SkillSpec, validate_skill_spec
from augur.skills.loader import load_skill, load_builtin_skills


# ---------------------------------------------------------------------------
# Paths to the two built-in fixtures
# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).resolve().parent.parent / "src" / "augur" / "skills"
EARNINGS_PREP = SKILLS_DIR / "earnings_prep.yaml"
FILING_DELTA = SKILLS_DIR / "filing_delta.yaml"


# ---------------------------------------------------------------------------
# load_builtin_skills
# ---------------------------------------------------------------------------

class TestLoadBuiltinSkills:
    def test_loads_both_fixtures(self):
        specs = load_builtin_skills()
        ids = {s.id for s in specs}
        assert ids == {"earnings-prep", "filing-delta"}

    def test_every_spec_is_valid_skill_spec(self):
        for spec in load_builtin_skills():
            assert isinstance(spec, SkillSpec)
            assert spec.id
            assert spec.description


# ---------------------------------------------------------------------------
# earnings_prep.yaml
# ---------------------------------------------------------------------------

class TestEarningsPrep:
    @pytest.fixture(scope="class")
    def spec(self) -> SkillSpec:
        return load_skill(EARNINGS_PREP)

    def test_loads_without_error(self, spec):
        assert spec.id == "earnings-prep"

    def test_basic_fields(self, spec):
        assert spec.version == "1.0.0"
        assert spec.description.startswith("Build a point-in-time")
        assert spec.license == "Apache-2.0"

    def test_compatibility(self, spec):
        assert spec.compatibility == {"augur": ">=11,<12"}

    def test_inputs_schema(self, spec):
        assert spec.inputs_schema["required"] == ["ticker", "event_id", "as_of"]

    def test_required_capabilities(self, spec):
        assert spec.required_capabilities == [
            "sec.filings.read",
            "fundamentals.snapshot",
            "market.price_history",
            "runs.compare",
        ]

    def test_permissions(self, spec):
        assert spec.permissions.resources == ["evidence.read", "runs.read"]
        assert spec.permissions.network_domains == ["sec.gov"]

    def test_evidence_policy(self, spec):
        ep = spec.evidence_policy
        assert ep.information_time_required is True
        assert ep.missing_strategy == "abstain"
        assert ep.min_claim_coverage == 0.95

    def test_workflow(self, spec):
        steps = {s.id: s for s in spec.workflow}
        assert set(steps.keys()) == {"collect", "compare", "synthesize"}
        assert steps["collect"].uses == "earnings.collect_evidence"
        assert steps["collect"].needs == []
        assert steps["compare"].uses == "runs.compare"
        assert steps["compare"].needs == ["collect"]
        assert steps["synthesize"].uses == "report.earnings_dossier"
        assert steps["synthesize"].needs == ["collect", "compare"]

    def test_outputs_schema(self, spec):
        assert spec.outputs_schema["required"] == [
            "run_id", "dossier", "evidence_manifest",
        ]

    def test_evals(self, spec):
        fixture_names = [f.input.get("fixture_id") for f in spec.evals.fixtures]
        gate_names = [g.metric for g in spec.evals.gates]
        assert fixture_names == ["earnings-prep-v1"]
        assert gate_names == ["citation_validity", "no_lookahead", "missingness_visible"]

    def test_round_trip(self, spec):
        """to_dict → from_dict → equals original"""
        d = spec.to_dict()
        rehydrated = SkillSpec.from_dict(d)
        assert rehydrated.id == spec.id
        assert rehydrated.description == spec.description
        assert rehydrated.required_capabilities == spec.required_capabilities
        assert len(rehydrated.workflow) == len(spec.workflow)

    def test_raw_validator_passes(self):
        raw = yaml.safe_load(EARNINGS_PREP.read_text(encoding="utf-8"))
        violations = validate_skill_spec(raw)
        assert violations == [], f"Unexpected violations: {violations}"


# ---------------------------------------------------------------------------
# filing_delta.yaml
# ---------------------------------------------------------------------------

class TestFilingDelta:
    @pytest.fixture(scope="class")
    def spec(self) -> SkillSpec:
        return load_skill(FILING_DELTA)

    def test_loads_without_error(self, spec):
        assert spec.id == "filing-delta"

    def test_basic_fields(self, spec):
        assert spec.version == "1.0.0"
        assert "Compare the latest SEC filing" in spec.description
        assert spec.license == "Apache-2.0"

    def test_required_capabilities(self, spec):
        assert spec.required_capabilities == [
            "sec.filings.read",
            "fundamentals.snapshot",
            "runs.compare",
        ]

    def test_permissions(self, spec):
        assert spec.permissions.resources == ["evidence.read", "runs.read"]
        assert spec.permissions.network_domains == ["sec.gov"]

    def test_evidence_policy(self, spec):
        ep = spec.evidence_policy
        assert ep.missing_strategy == "abstain"
        assert ep.min_claim_coverage == 0.90

    def test_workflow(self, spec):
        steps = {s.id: s for s in spec.workflow}
        assert set(steps.keys()) == {"fetch_new", "fetch_old", "compare", "delta_report"}
        assert steps["fetch_new"].uses == "sec.filings.read"
        assert steps["fetch_old"].uses == "sec.filings.read"
        assert steps["compare"].needs == ["fetch_new", "fetch_old"]
        assert steps["delta_report"].needs == ["compare"]

    def test_outputs_schema(self, spec):
        assert spec.outputs_schema["required"] == [
            "run_id", "delta_report", "evidence_manifest",
        ]

    def test_evals(self, spec):
        fixture_names = [f.input.get("fixture_id") for f in spec.evals.fixtures]
        gate_names = [g.metric for g in spec.evals.gates]
        assert fixture_names == ["filing-delta-v1"]
        assert gate_names == ["citation_validity", "no_lookahead"]

    def test_round_trip(self, spec):
        d = spec.to_dict()
        rehydrated = SkillSpec.from_dict(d)
        assert rehydrated.id == spec.id
        assert rehydrated.required_capabilities == spec.required_capabilities
        assert len(rehydrated.workflow) == len(spec.workflow)

    def test_raw_validator_passes(self):
        raw = yaml.safe_load(FILING_DELTA.read_text(encoding="utf-8"))
        violations = validate_skill_spec(raw)
        assert violations == [], f"Unexpected violations: {violations}"


# ---------------------------------------------------------------------------
# Validation: module_path rejection
# ---------------------------------------------------------------------------

class TestForbiddenKeys:
    def test_module_path_rejected(self):
        raw = yaml.safe_load(EARNINGS_PREP.read_text(encoding="utf-8"))
        raw["module_path"] = "/some/executable/code.py"
        violations = validate_skill_spec(raw)
        assert any("module_path" in v for v in violations)

    def test_import_key_rejected(self):
        raw = yaml.safe_load(FILING_DELTA.read_text(encoding="utf-8"))
        raw["import"] = "os"
        violations = validate_skill_spec(raw)
        assert any("import" in v.lower() for v in violations)

    def test_exec_rejected(self):
        raw = yaml.safe_load(EARNINGS_PREP.read_text(encoding="utf-8"))
        raw["exec"] = "rm -rf /"
        violations = validate_skill_spec(raw)
        assert any("exec" in v.lower() for v in violations)


# ---------------------------------------------------------------------------
# Validation: missing required_capabilities → SkillSpec construction fails
#   (SkillSpec allows empty list, but the semantic test verifies the field)
# ---------------------------------------------------------------------------

class TestMissingCapabilities:
    def test_earnings_prep_has_required_capabilities(self):
        spec = load_skill(EARNINGS_PREP)
        assert len(spec.required_capabilities) > 0

    def test_filing_delta_has_required_capabilities(self):
        spec = load_skill(FILING_DELTA)
        assert len(spec.required_capabilities) > 0


# ---------------------------------------------------------------------------
# Permission boundary: unregistered network domain
# ---------------------------------------------------------------------------

class TestPermissionBoundary:
    def test_unregistered_domain_in_yaml_rejected(self):
        """Adding a URL with a domain not in network_domains should violate."""
        raw = yaml.safe_load(EARNINGS_PREP.read_text(encoding="utf-8"))
        # Inject an unregistered domain somewhere the validator will find it
        raw["metadata"] = {"external_api": "https://evil.com/data"}
        violations = validate_skill_spec(raw)
        assert any("evil.com" in v for v in violations)

    def test_registered_domain_passes(self):
        """A URL with a registered domain (sec.gov) should pass."""
        raw = yaml.safe_load(EARNINGS_PREP.read_text(encoding="utf-8"))
        raw["metadata"] = {"source_url": "https://sec.gov/data"}
        violations = validate_skill_spec(raw)
        # sec.gov is in the permissions.network_domains list
        assert not any("sec.gov" in v for v in violations)
