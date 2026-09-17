# -*- coding: utf-8 -*-
"""Skill runner: built-in skills execute end to end, permissions are enforced before any step runs.

Until 2026-09-17 there was no runner: `augur skill run` did not exist and all
six registered capabilities returned {"stub": True}.
"""
import json

import pytest
from click.testing import CliRunner

from augur.capability import Capability, CapabilityRegistry
from augur.datasources.base import DataProvider
from augur.schemas.skill_spec import SkillSpec
from augur.skills.permissions import SkillPermissionError
from augur.skills.runner import SkillNotRunnable, SkillRunner, run_skill


class _Provider(DataProvider):
    name = "mock_skill"

    def fetch(self, ticker):
        return {"data_source": "mock_skill", "price": 190.0, "pe": 45.0, "pb": 60.0, "roe": 1.5,
                "gross_margins": 0.46, "revenue_growth": 0.06, "debt_ratio": 0.8, "fcf": 100.0,
                "market_cap": 2900.0}


ANNUAL = [
    {"fiscal_year_end": "2025-09-27", "accession": "0000320193-25-000079", "filed": "2025-10-31",
     "metrics": {"revenue": 416.2e9, "net_income": 112.0e9, "gross_margin": 0.469, "operating_income": 133.1e9,
                 "ebitda": 144.7e9, "total_debt": 103.0e9, "total_equity": 73.7e9, "eps_diluted": 7.46}},
    {"fiscal_year_end": "2024-09-28", "accession": "0000320193-24-000123", "filed": "2024-11-01",
     "metrics": {"revenue": 391.0e9, "net_income": 93.7e9, "gross_margin": 0.462, "operating_income": 123.2e9,
                 "ebitda": 134.7e9, "total_debt": 107.6e9, "total_equity": 57.0e9, "eps_diluted": 6.08}},
]


class _FakeClient:
    def get_cik(self, ticker):
        return 320193


@pytest.fixture
def offline(monkeypatch, tmp_path):
    import augur.consensus.edgar_fundamentals as ef
    import augur.data as data_module

    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")
    # fetch_market_context caches contexts for 3 minutes across tests
    data_module.clear_cache()
    monkeypatch.setattr(data_module, "_get_providers", lambda: [_Provider()])
    monkeypatch.setattr(ef, "fetch_annual_financials", lambda ticker, years=2: [dict(p) for p in ANNUAL[:years]])
    monkeypatch.setattr(ef, "_get_client", lambda: _FakeClient())


def _bundle(run_id):
    from augur.run_tracker import load_run_bundle_dict

    return load_run_bundle_dict(run_id)


def test_earnings_prep_runs_end_to_end_and_compares_with_previous_run(offline):
    from augur.workflow import run_workflow

    previous = run_workflow("AAPL", steps="fetch,analyze,consensus")
    result = run_skill("earnings-prep", {"ticker": "aapl"})

    assert result.status == "success", result.error
    assert result.step_status == {"collect": "success", "analyze": "success", "compare": "success", "synthesize": "success"}
    assert result.outputs["evidence_manifest"], "collected evidence must be listed"
    assert result.outputs["previous_run_id"] == previous["run_id"]
    assert "# Pre-earnings dossier: AAPL" in result.outputs["summary_markdown"]
    assert result.outputs["dossier"]["disagreement"]["derivation"] == "factor-spread"

    bundle = _bundle(result.run_id)
    skill_meta = bundle["metadata"]["skill"]
    assert skill_meta["id"] == "earnings-prep" and skill_meta["status"] == "success"
    assert "ALLOWED network domain 'finance.yahoo.com' for 'earnings.collect_evidence'" in skill_meta["audit_log"]
    collect = next(s for s in bundle["step_results"] if s["step_name"] == "collect")
    assert collect["output_refs"] and "_ctx" not in collect["result"]
    assert bundle["coverage"]["total_evidence"] == len(result.outputs["evidence_manifest"])


def test_filing_delta_uses_the_two_latest_annual_periods(offline):
    result = run_skill("filing-delta", {"ticker": "AAPL"})

    assert result.status == "success", result.error
    report = result.outputs["delta_report"]
    assert report["new_accession"] == "0000320193-25-000079"
    assert report["previous_accession"] == "0000320193-24-000123"
    revenue = next(c for c in report["numeric_changes"] if c["metric"] == "revenue")
    assert revenue["new_value"] == 416.2e9 and revenue["previous_value"] == 391.0e9
    assert len(result.outputs["evidence_manifest"]) == sum(len(p["metrics"]) for p in ANNUAL)


def test_covenant_review_labels_reference_thresholds_and_missing_inputs(offline):
    result = run_skill("debt-covenant-review", {"ticker": "AAPL"})
    assert result.status == "success", result.error
    report = result.outputs["covenant_report"]
    assert report["thresholds_are_reference"] is True
    assert "interest_expense" in report["unavailable_inputs"]
    assert "not the company's contractual covenants" in result.outputs["summary_markdown"]

    custom = run_skill("debt-covenant-review", {"ticker": "AAPL", "debt_ebitda_max": "0.5"})
    assert custom.outputs["covenant_report"]["thresholds"]["debt_ebitda_max"] == 0.5
    assert custom.outputs["covenant_report"]["thresholds_are_reference"] is False


def test_insider_cluster_review(offline, monkeypatch):
    import augur.cli_commands.insider_cmd as insider_cmd
    from augur.ownership import InsiderTrade

    trades = [InsiderTrade("AAPL", f"cik{i}", "", "2026-09-01", "sell", 1000.0, 200.0, 200000.0) for i in range(3)]
    monkeypatch.setattr(insider_cmd, "_fetch_insider_trades", lambda ticker: trades)

    result = run_skill("insider-cluster-review", {"ticker": "AAPL"})
    assert result.status == "success", result.error
    assert result.outputs["cluster_report"]["total_sells"] == 3
    assert len(result.outputs["evidence_manifest"]) == 3


# ---------------------------------------------------------------------------
# Enforcement happens before any handler runs
# ---------------------------------------------------------------------------

def _spec(uses="test.echo", required=("test.echo",), domains=("sec.gov",)):
    return SkillSpec.model_validate({
        "id": "probe", "version": "1.0.0", "description": "probe", "license": "MIT",
        "compatibility": ">=11,<12", "inputs_schema": {"required": ["ticker"]},
        "required_capabilities": list(required),
        "permissions": {"resources": ["evidence.read"], "network_domains": list(domains)},
        "evidence_policy": {"information_time_required": False, "missing_strategy": "abstain", "min_claim_coverage": 0.0},
        "workflow": [{"id": "first", "uses": "test.safe"}, {"id": "second", "uses": uses, "needs": ["first"]}],
        "outputs_schema": {"required": ["run_id"]},
        "evals": {"fixtures": [], "gates": []},
    })


def _registry(calls, network=("sec.gov",)):
    reg = CapabilityRegistry()
    schema = {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]}
    for name, domains in (("test.safe", ()), ("test.echo", network)):
        reg.register(Capability(name, name, schema, {"type": "object"},
                                handler=lambda inputs, up, n=name: calls.append(n) or {"ok": True},
                                network_domains=list(domains)))
    return reg


def test_undeclared_capability_is_refused_before_any_step(offline):
    calls = []
    runner = SkillRunner(_spec(required=("test.safe",)), registry=_registry(calls))
    with pytest.raises(SkillPermissionError, match="test.echo"):
        runner.run({"ticker": "AAPL"})
    assert calls == [], "no handler may run when a later step is not permitted"


def test_unpermitted_network_domain_is_refused_before_any_step(offline):
    calls = []
    runner = SkillRunner(_spec(required=("test.safe", "test.echo"), domains=("sec.gov",)),
                         registry=_registry(calls, network=("evil.example",)))
    with pytest.raises(SkillPermissionError, match="evil.example"):
        runner.run({"ticker": "AAPL"})
    assert calls == []
    assert any("DENIED network domain 'evil.example'" in line for line in runner.enforcer.audit_log)


def test_unimplemented_capability_is_not_runnable(offline):
    calls = []
    runner = SkillRunner(_spec(uses="test.missing", required=("test.safe", "test.missing")), registry=_registry(calls))
    with pytest.raises(SkillNotRunnable, match="test.missing"):
        runner.run({"ticker": "AAPL"})
    assert calls == []


def test_handler_failure_marks_run_failed_and_keeps_bundle(offline, monkeypatch):
    import augur.consensus.edgar_fundamentals as ef

    def boom(ticker, years=2):
        raise LookupError("no annual SEC financials for ZZZZ")

    monkeypatch.setattr(ef, "fetch_annual_financials", boom)
    result = run_skill("filing-delta", {"ticker": "ZZZZ"})
    assert result.status == "failed"
    assert "no annual SEC financials" in result.error
    assert result.step_status == {"fetch_filings": "failure"}
    assert _bundle(result.run_id)["metadata"]["skill"]["status"] == "failed"


def test_bad_inputs_are_rejected():
    with pytest.raises(SkillNotRunnable, match="unknown skill"):
        run_skill("nope", {"ticker": "AAPL"})
    with pytest.raises(SkillNotRunnable, match="unknown input"):
        run_skill("filing-delta", {"ticker": "AAPL", "accession": "x"})


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def test_cli_list_show_run(offline):
    from augur.cli import main

    runner = CliRunner()
    listed = runner.invoke(main, ["skill", "list"])
    assert listed.exit_code == 0 and "earnings-prep" in listed.output and "insider-cluster-review" in listed.output

    shown = runner.invoke(main, ["skill", "show", "filing-delta"])
    assert "sec.financials.annual" in shown.output and "NOT IMPLEMENTED" not in shown.output

    ran = runner.invoke(main, ["skill", "run", "debt-covenant-review", "AAPL", "--set", "debt_ebitda_max=3.0"])
    assert ran.exit_code == 0, ran.output
    assert "Covenant review: AAPL" in ran.output and "Run ID: run_AAPL_" in ran.output

    bad = runner.invoke(main, ["skill", "run", "nope", "AAPL"])
    assert bad.exit_code == 1


def test_mcp_tool_helper(offline):
    from augur.mcp_server import _run_skill_tool

    payload = json.loads(_run_skill_tool("filing-delta", "AAPL"))
    assert payload["status"] == "success" and payload["run_id"].startswith("run_AAPL_")
    assert "error" in json.loads(_run_skill_tool("filing-delta", "AAPL", inputs_json="[1]"))


def test_runs_without_persona_analysis_are_skipped_when_comparing(offline):
    """A newer filing-delta run must not hide the last run that has persona results."""
    from augur.cli import main
    from augur.workflow import run_workflow

    workflow = run_workflow("AAPL", steps="fetch,analyze,consensus")
    assert run_skill("filing-delta", {"ticker": "AAPL"}).status == "success"

    prep = run_skill("earnings-prep", {"ticker": "AAPL"})
    assert prep.outputs["previous_run_id"] == workflow["run_id"]

    report = CliRunner().invoke(main, ["research-report", "AAPL"])
    assert report.exit_code == 0, report.output
    assert prep.run_id in report.output, "the skill run with personas is now the newest analysed run"
    assert "## Consensus" in report.output
