# -*- coding: utf-8 -*-
"""Disagreement map derived from factor scores and cited evidence.

Before 2026-09-17 every map carried the same three hard-coded claims
("Current valuation is justified by growth prospects", "Competitive moat is
widening", "Management has credible capital allocation strategy") filled with
the first few bullish/bearish persona names, whatever the data said.
"""
import dataclasses

from augur.disagreement import DisagreementMapBuilder, build_disagreement_from_bundle


def _ev(metric, value, missing=False):
    return {"evidence_id": f"ev_{metric}", "metric": metric, "value": None if missing else value, "missing": missing}


EVIDENCE = [_ev("pe", 44.6), _ev("pb", 61.2), _ev("gross_margins", 0.469), _ev("roe", 1.52),
            _ev("insider_ownership", None, missing=True)]

PERSONAS = {
    # valuation: bimodal; moat: unanimous high; macro: split with no evidence
    "graham":        {"signal": "bearish", "score": 3.0, "confidence": 0.8, "factors": {"valuation": 1.5, "margin_of_safety": 1.0}},
    "buffett":       {"signal": "neutral", "score": 6.0, "confidence": 0.9, "factors": {"moat": 8.0, "valuation": 3.0}},
    "duan_yongping": {"signal": "bullish", "score": 7.0, "confidence": 0.8, "factors": {"moat_quality": 9.0, "valuation_reasonableness": 8.0}},
    "zhang_lei":     {"signal": "bullish", "score": 7.5, "confidence": 0.8, "factors": {"competitive_moat": 7.5, "valuation_fairness": 7.0}},
    "dalio":         {"signal": "bullish", "score": 7.0, "confidence": 0.7, "factors": {"macro_outlook": 8.0}},
    "arps":          {"signal": "bearish", "score": 3.0, "confidence": 0.6, "factors": {"macro_background": 2.0}},
    "lynch":         {"signal": "neutral", "score": 5.0, "confidence": 0.5, "factors": {"growth": 5.0}},
}


def _map():
    return DisagreementMapBuilder("AAPL", "run_x").build(PERSONAS, EVIDENCE)


def test_valuation_conflict_names_the_right_personas_and_cites_evidence():
    dm = _map()
    assert dm.derivation == "factor-spread"
    [valuation] = [c for c in dm.conflict_points if c.dimension == "valuation"]
    assert set(valuation.bullish_personas) == {"duan_yongping", "zhang_lei"}
    assert set(valuation.bearish_personas) == {"graham", "buffett"}
    assert valuation.persona_scores["graham"] == 1.2  # mean of its two valuation factors
    assert valuation.evidence_supporting == ["ev_pe", "ev_pb"]
    assert "PE 44.6" in valuation.claim and "PB 61.2" in valuation.claim
    assert valuation.impact == "high"


def test_unanimous_dimension_is_an_agreement_point_not_a_conflict():
    dm = _map()
    assert not [c for c in dm.conflict_points if c.dimension == "moat"]
    assert any(p.startswith("Competitive moat and business quality: all 3 scoring personas rate it strong")
               and "gross margins 46.9%" in p for p in dm.agreement_points)


def test_split_without_evidence_is_a_gap_not_a_conflict():
    dm = _map()
    assert not [c for c in dm.conflict_points if c.dimension == "macro"]
    assert any(g.startswith("Macro and liquidity backdrop") and "no evidence" in g for g in dm.evidence_gaps)


def test_no_template_claims_ever():
    dm = _map()
    text = " ".join(c.claim for c in dm.conflict_points)
    for template in ("justified by growth prospects", "moat is widening", "credible capital allocation"):
        assert template not in text


def test_runs_without_factor_scores_produce_no_conflicts():
    legacy = {p: {k: v for k, v in d.items() if k != "factors"} for p, d in PERSONAS.items()}
    dm = DisagreementMapBuilder("AAPL", "run_old").build(legacy, EVIDENCE)
    assert dm.derivation == "signal-only"
    assert dm.conflict_points == []
    assert "re-run `augur workflow`" in dm.summary


def test_bundle_helper_reads_analyze_and_fetch_steps():
    bundle = {"step_results": [
        {"step_name": "fetch", "result": {"evidence_items": EVIDENCE}},
        {"step_name": "analyze", "result": PERSONAS},
    ]}
    dm = build_disagreement_from_bundle(bundle, "aapl", "run_b")
    assert dm.ticker == "AAPL" and dm.run_id == "run_b"
    assert [c.dimension for c in dm.conflict_points] == ["valuation"]


def test_workflow_run_feeds_real_evidence_into_the_map(monkeypatch, tmp_path):
    """End to end: a tracked workflow stores evidence + factors, and the map cites them."""
    from click.testing import CliRunner

    import augur.data as data_module
    from augur.cli import main
    from augur.datasources.base import DataProvider
    from augur.run_tracker import load_run_bundle_dict
    from augur.workflow import run_workflow

    class _Provider(DataProvider):
        name = "mock_dm"

        def fetch(self, ticker):
            return {"data_source": "mock_dm", "price": 190.0, "pe": 45.0, "pb": 60.0, "roe": 1.5,
                    "gross_margins": 0.46, "revenue_growth": 0.06, "debt_ratio": 0.8, "fcf": 100.0,
                    "market_cap": 2900.0}

    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")
    # fetch_market_context caches contexts for 3 minutes across tests
    data_module.clear_cache()
    monkeypatch.setattr(data_module, "_get_providers", lambda: [_Provider()])

    run = run_workflow("AAPL", steps="fetch,analyze,consensus")
    bundle = load_run_bundle_dict(run["run_id"])
    fetch = next(s for s in bundle["step_results"] if s["step_name"] == "fetch")
    assert fetch["output_refs"], "fetch step must list its evidence ids"
    assert bundle["coverage"]["total_evidence"] == len(fetch["result"]["evidence_items"])

    dm = build_disagreement_from_bundle(bundle, "AAPL", run["run_id"])
    assert dm.derivation == "factor-spread"
    known_ids = set(fetch["output_refs"])
    for cp in dm.conflict_points:
        assert cp.evidence_supporting and set(cp.evidence_supporting) <= known_ids

    report = CliRunner().invoke(main, ["research-report", "AAPL"])
    assert "derivation: factor-spread" in report.output

    from fastapi.testclient import TestClient

    from dashboard.app import app

    body = TestClient(app).get("/api/disagreement", params={"ticker": "AAPL", "run_id": run["run_id"]}).json()
    assert body["run_id"] == run["run_id"] and body["derivation"] == "factor-spread"
    assert body == dataclasses.asdict(dm)
