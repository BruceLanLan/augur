# -*- coding: utf-8 -*-
"""Tests for all 4 built-in skills — security + completeness."""
import pytest
from pathlib import Path

from augur.skills.loader import load_builtin_skills, load_skill
from augur.skills.permissions import SkillPermissionEnforcer, SkillPermissionError

SKILLS_DIR = Path(__file__).resolve().parent.parent / "src" / "augur" / "skills"


class TestBuiltinSkillsCompleteness:
    def test_all_four_skills_load(self):
        skills = load_builtin_skills()
        assert len(skills) == 4
        ids = {s.id for s in skills}
        assert ids == {
            "earnings-prep", "filing-delta",
            "debt-covenant-review", "insider-cluster-review",
        }

    def test_each_skill_has_required_capabilities(self):
        for spec in load_builtin_skills():
            assert len(spec.required_capabilities) >= 1, spec.id

    def test_each_skill_has_network_restrictions(self):
        # Built-in skills may only reach Augur's data providers. earnings-prep
        # needs live market data (Yahoo Finance) in addition to SEC EDGAR; the
        # runner additionally refuses any capability whose domains are not
        # declared (tests/test_skill_runner.py).
        allowed = {"sec.gov", "finance.yahoo.com"}
        for spec in load_builtin_skills():
            domains = spec.permissions.network_domains
            assert domains, spec.id
            assert set(domains) <= allowed, (spec.id, domains)

    def test_each_skill_has_evidence_policy(self):
        for spec in load_builtin_skills():
            assert spec.evidence_policy.information_time_required is True
            assert spec.evidence_policy.missing_strategy in ("abstain", "error")

    def test_each_skill_has_workflow(self):
        for spec in load_builtin_skills():
            assert len(spec.workflow) >= 1, spec.id


class TestSkillSecurity:
    def test_no_executable_keys_in_yaml_files(self):
        forbidden = {"module_path", "shell", "import", "exec", "eval", "file_path"}
        for yaml_file in SKILLS_DIR.glob("*.yaml"):
            text = yaml_file.read_text(encoding="utf-8")
            for key in forbidden:
                assert f"{key}:" not in text, f"{yaml_file.name} contains forbidden key {key}"

    def test_permission_enforcer_rejects_unregistered_domains(self):
        spec = load_skill(SKILLS_DIR / "earnings_prep.yaml")
        enforcer = SkillPermissionEnforcer(spec)
        with pytest.raises(SkillPermissionError):
            enforcer.check_network("evil.com")

    def test_permission_enforcer_allows_sec_gov(self):
        spec = load_skill(SKILLS_DIR / "earnings_prep.yaml")
        enforcer = SkillPermissionEnforcer(spec)
        enforcer.check_network("sec.gov")
        enforcer.check_network("data.sec.gov")
