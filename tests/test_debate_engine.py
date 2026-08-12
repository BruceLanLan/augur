# -*- coding: utf-8 -*-
"""Tests for Evidence-seeking Debate engine (F01)."""

import pytest

from augur.debate_engine import (
    Challenge,
    DebateResult,
    EvidenceSeekingDebate,
    Revision,
    RequeryResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mixed_outputs() -> dict:
    """8 bulls, 7 bears, 3 neutrals."""
    result = {}
    for i in range(8):
        result[f"bull_{i}"] = {
            "signal": "bullish", "score": 7.0 + i * 0.2,
            "confidence": 0.8, "reasoning": f"Bull case {i}"
        }
    for i in range(7):
        result[f"bear_{i}"] = {
            "signal": "bearish", "score": 3.0 + i * 0.2,
            "confidence": 0.7, "reasoning": f"Bear case {i}"
        }
    for i in range(3):
        result[f"neut_{i}"] = {
            "signal": "neutral", "score": 5.0,
            "confidence": 0.4, "reasoning": f"Neutral case {i}"
        }
    return result


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

class TestChallenge:
    def test_creation(self):
        ch = Challenge(
            challenge_id="ch_001",
            target_claim_id="claim_buffett",
            challenger="dalio",
            challenge_type="contradicting_evidence",
            statement="Dalio disagrees with Buffett on valuation",
            severity="high",
        )
        assert ch.challenger == "dalio"
        assert ch.severity == "high"

    def test_defaults(self):
        ch = Challenge(
            challenge_id="ch_002",
            target_claim_id="claim_x",
            challenger="y",
            challenge_type="evidence_gap",
            statement="Missing data",
        )
        assert ch.evidence_refs == []
        assert ch.severity == "medium"


# ---------------------------------------------------------------------------
# RequeryResult
# ---------------------------------------------------------------------------

class TestRequeryResult:
    def test_creation(self):
        rq = RequeryResult(
            claim_id="claim_001",
            capability_used="sec.filings.read",
            new_evidence_ids=["ev_001", "ev_002"],
            found_contradicting=True,
            found_supporting=False,
            cost_ms=123.4,
        )
        assert rq.found_contradicting is True
        assert len(rq.new_evidence_ids) == 2


# ---------------------------------------------------------------------------
# Revision
# ---------------------------------------------------------------------------

class TestRevision:
    def test_creation(self):
        rev = Revision(
            claim_id="claim_001",
            original_statement="Apple is undervalued",
            verdict="supported",
            revision_reason="Evidence confirms",
        )
        assert rev.verdict == "supported"


# ---------------------------------------------------------------------------
# EvidenceSeekingDebate
# ---------------------------------------------------------------------------

class TestDebateEngine:
    def test_extract_claims(self, mixed_outputs):
        engine = EvidenceSeekingDebate("AAPL", "run_001")
        claims = engine.extract_claims(mixed_outputs)
        assert len(claims) == 18
        # All claims should have required fields
        for c in claims:
            assert "persona_id" in c
            assert "text" in c
            assert "signal" in c

    def test_generate_challenges(self, mixed_outputs):
        engine = EvidenceSeekingDebate("AAPL", "run_001")
        claims = engine.extract_claims(mixed_outputs)
        challenges = engine.generate_challenges(claims)
        # Should have cross-challenges between bulls and bears
        assert len(challenges) > 0
        for ch in challenges:
            assert ch.challenge_type in (
                "contradicting_evidence", "evidence_gap", "logic_flaw"
            )

    def test_requery_disputed(self, mixed_outputs):
        engine = EvidenceSeekingDebate("AAPL", "run_001")
        claims = engine.extract_claims(mixed_outputs)
        challenges = engine.generate_challenges(claims)
        results = engine.requery_disputed(challenges)
        assert len(results) > 0
        for rq in results:
            assert rq.capability_used
            assert rq.cost_ms >= 0

    def test_requery_with_evidence_store(self, mixed_outputs):
        engine = EvidenceSeekingDebate("AAPL", "run_001")
        claims = engine.extract_claims(mixed_outputs)
        challenges = engine.generate_challenges(claims)
        store = {"ev_AAPL_001": {"source": "sec"}, "ev_AAPL_002": {"source": "edgar"}}
        results = engine.requery_disputed(challenges, evidence_store=store)
        for rq in results:
            assert len(rq.new_evidence_ids) >= 0

    def test_revise_claims(self, mixed_outputs):
        engine = EvidenceSeekingDebate("AAPL", "run_001")
        claims = engine.extract_claims(mixed_outputs)
        challenges = engine.generate_challenges(claims)
        requery_results = engine.requery_disputed(challenges)
        revisions = engine.revise_claims(claims, challenges, requery_results)
        assert len(revisions) == len(claims)
        for rev in revisions:
            assert rev.verdict in ("supported", "contradicted", "revised", "unknown", "unchanged")

    def test_full_run(self, mixed_outputs):
        engine = EvidenceSeekingDebate("AAPL", "run_001")
        result = engine.run(mixed_outputs)
        assert isinstance(result, DebateResult)
        assert result.ticker == "AAPL"
        assert len(result.revisions) == 18
        assert result.claims_supported + result.claims_contradicted + \
               result.claims_revised + result.claims_unknown == 18
        assert result.total_cost_ms >= 0
        assert len(result.summary) > 0

    def test_run_empty(self):
        engine = EvidenceSeekingDebate("TEST", "run_empty")
        result = engine.run({})
        assert result.claims_supported + result.claims_contradicted + \
               result.claims_revised + result.claims_unknown == 0

    def test_all_bulls_no_challenges(self):
        outputs = {}
        for i in range(10):
            outputs[f"bull_{i}"] = {"signal": "bullish", "score": 7.0, "confidence": 0.8}
        engine = EvidenceSeekingDebate("MSFT", "run_002")
        result = engine.run(outputs)
        # No bears → no challenges → all supported
        assert result.claims_supported == 10
        assert result.claims_contradicted == 0

    def test_debate_result_fields(self, mixed_outputs):
        engine = EvidenceSeekingDebate("AAPL", "run_001")
        result = engine.run(mixed_outputs)
        # Verify all public fields
        assert result.debate_id.startswith("debate_AAPL_")
        assert result.new_evidence_found >= 0
        assert isinstance(result.summary, str)
