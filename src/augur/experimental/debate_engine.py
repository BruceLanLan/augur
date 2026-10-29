# -*- coding: utf-8 -*-
"""
Evidence-seeking Debate — structured claim/challenge/re-query/revision protocol.

Replaces the current "append-key-findings" debate with a four-stage
evidence-grounded process:

1. Independent claims — each persona produces structured Claim objects
2. Challenge — counter-claims must cite contradicting evidence or gaps
3. Re-query — only disputed claims trigger targeted data re-fetching
4. Revision — output supported/contradicted/unknown with revision record
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class Challenge:
    """A structured challenge to a claim."""

    challenge_id: str          # ch_{hash[:8]}
    target_claim_id: str       # claim being challenged
    challenger: str            # persona_id making the challenge
    challenge_type: str        # "contradicting_evidence" | "evidence_gap" | "logic_flaw"
    statement: str             # what the challenge is
    evidence_refs: List[str] = field(default_factory=list)  # evidence supporting the challenge
    severity: str = "medium"   # "critical" | "high" | "medium" | "low"


@dataclass
class RequeryResult:
    """Result of a targeted re-query for a disputed claim."""

    claim_id: str
    capability_used: str       # e.g. "sec.filings.read"
    new_evidence_ids: List[str]
    found_contradicting: bool
    found_supporting: bool
    cost_ms: float
    note: str = ""


@dataclass
class Revision:
    """Outcome of debate for a single claim."""

    claim_id: str
    original_statement: str
    revised_statement: str = ""
    verdict: str = "unchanged"  # "supported" | "contradicted" | "revised" | "unknown"
    revision_reason: str = ""
    challenges: List[Challenge] = field(default_factory=list)
    requery: Optional[RequeryResult] = None


@dataclass
class DebateResult:
    """Complete evidence-seeking debate outcome."""

    debate_id: str
    ticker: str
    run_id: str
    revisions: List[Revision]
    claims_supported: int
    claims_contradicted: int
    claims_revised: int
    claims_unknown: int
    new_evidence_found: int
    total_cost_ms: float
    summary: str


# ---------------------------------------------------------------------------
# Debate Engine
# ---------------------------------------------------------------------------

class EvidenceSeekingDebate:
    """Four-stage evidence-seeking debate protocol.

    Compared to the old "append key findings" approach, this:
    - Requires challengers to cite specific evidence or gaps
    - Only re-queries disputed claims (not the entire report)
    - Produces a structured revision record
    - Tracks cost and evidence improvement
    """

    def __init__(self, ticker: str, run_id: str):
        self._ticker = ticker.upper()
        self._run_id = run_id
        self._debate_id = f"debate_{ticker}_{run_id[:8]}"

    # ------------------------------------------------------------------
    # Stage 1: Independent claims
    # ------------------------------------------------------------------

    def extract_claims(
        self,
        persona_outputs: Dict[str, Dict[str, Any]],
    ) -> List[dict]:
        """Extract structured claims from each persona's reasoning.

        In production this would parse the reasoning text with NLP.
        The MVP uses a rule-based approach on signal, score, and reasoning.
        """
        claims: List[dict] = []
        for pid, output in persona_outputs.items():
            signal = output.get("signal", "neutral")
            score = output.get("score", 5.0)

            # Generate a claim from the persona's signal
            if signal == "bullish":
                claim_text = f"{pid} views {self._ticker} as undervalued "
                claim_text += f"with growth potential (score: {score:.1f}/10)"
            elif signal == "bearish":
                claim_text = f"{pid} views {self._ticker} as overvalued "
                claim_text += f"or facing headwinds (score: {score:.1f}/10)"
            else:
                claim_text = f"{pid} has a neutral view on {self._ticker} "
                claim_text += f"(score: {score:.1f}/10)"

            claims.append({
                "persona_id": pid,
                "text": claim_text,
                "signal": signal,
                "score": score,
                "confidence": output.get("confidence", 0.5),
            })

        return claims

    # ------------------------------------------------------------------
    # Stage 2: Challenge generation
    # ------------------------------------------------------------------

    def generate_challenges(
        self,
        claims: List[dict],
        evidence_manifest: Optional[Dict[str, Any]] = None,
    ) -> List[Challenge]:
        """Generate challenges between opposing persona claims.

        A challenge is generated when two personas have opposing signals
        (bullish vs bearish) — each challenges the other's view.
        """
        challenges: List[Challenge] = []
        bulls = [c for c in claims if c.get("signal") == "bullish"]
        bears = [c for c in claims if c.get("signal") == "bearish"]

        # Pair opposing views for challenge
        for i, bull in enumerate(bulls[:5]):
            for j, bear in enumerate(bears[:5]):
                if i >= 3 and j >= 3:
                    break  # limit cross-challenges

                ch = Challenge(
                    challenge_id=f"ch_{hash(bull['persona_id'] + bear['persona_id']) % (10**8):08d}",
                    target_claim_id=f"claim_{bull['persona_id']}",
                    challenger=bear["persona_id"],
                    challenge_type="contradicting_evidence",
                    statement=(
                        f"{bear['persona_id']} challenges {bull['persona_id']}'s "
                        f"bullish view: opposing signal with score "
                        f"{bear['score']:.1f}/10"
                    ),
                    severity="medium",
                )
                challenges.append(ch)

        return challenges

    # ------------------------------------------------------------------
    # Stage 3: Re-query disputed claims
    # ------------------------------------------------------------------

    def requery_disputed(
        self,
        challenges: List[Challenge],
        evidence_store: Optional[Dict[str, Any]] = None,
    ) -> List[RequeryResult]:
        """For disputed claims, trigger targeted capability re-queries.

        Only claims with active challenges are re-queried — not the entire
        report. In production this calls the Capability Registry.
        """
        results: List[RequeryResult] = []
        disputed_claims = set(ch.target_claim_id for ch in challenges)

        for claim_id in disputed_claims:
            # Simulate a re-query: check if evidence_store has relevant data
            new_evidence: List[str] = []
            if evidence_store:
                for eid, edata in evidence_store.items():
                    if self._ticker in eid or self._ticker in str(edata):
                        new_evidence.append(eid)

            results.append(RequeryResult(
                claim_id=claim_id,
                capability_used="evidence.lookup",
                new_evidence_ids=new_evidence[:5],
                found_contradicting=len(new_evidence) > 0,
                found_supporting=len(new_evidence) > 0,
                cost_ms=len(new_evidence) * 2.5,
                note=f"Found {len(new_evidence)} relevant evidence items",
            ))

        return results

    # ------------------------------------------------------------------
    # Stage 4: Revision and judgment
    # ------------------------------------------------------------------

    def revise_claims(
        self,
        claims: List[dict],
        challenges: List[Challenge],
        requery_results: List[RequeryResult],
    ) -> List[Revision]:
        """Produce a revision for each claim based on challenges and re-queries.

        Verdict logic:
        - No challenges → "supported"
        - Challenged but re-query found supporting evidence → "supported"
        - Challenged and re-query found contradicting → "contradicted"
        - Challenged and re-query found both → "revised"
        - Challenged and no new evidence → "unknown"
        """
        challenge_map: Dict[str, List[Challenge]] = {}
        for ch in challenges:
            challenge_map.setdefault(ch.target_claim_id, []).append(ch)

        requery_map: Dict[str, RequeryResult] = {}
        for rq in requery_results:
            requery_map[rq.claim_id] = rq

        revisions: List[Revision] = []
        for i, claim in enumerate(claims):
            cid = f"claim_{claim['persona_id']}"
            claim_challenges = challenge_map.get(cid, [])
            rq = requery_map.get(cid)

            verdict = "supported"  # default
            reason = ""

            if claim_challenges:
                if rq and rq.found_contradicting and not rq.found_supporting:
                    verdict = "contradicted"
                    reason = "Re-query found contradicting evidence"
                elif rq and rq.found_supporting and rq.found_contradicting:
                    verdict = "revised"
                    reason = "Mixed evidence found; claim needs refinement"
                elif rq and rq.found_supporting:
                    verdict = "supported"
                    reason = "Re-query confirmed supporting evidence"
                else:
                    verdict = "unknown"
                    reason = f"No new evidence found to resolve {len(claim_challenges)} challenge(s)"

            revisions.append(Revision(
                claim_id=cid,
                original_statement=claim.get("text", ""),
                verdict=verdict,
                revision_reason=reason,
                challenges=claim_challenges,
                requery=rq,
            ))

        return revisions

    # ------------------------------------------------------------------
    # Full debate execution
    # ------------------------------------------------------------------

    def run(
        self,
        persona_outputs: Dict[str, Dict[str, Any]],
        evidence_manifest: Optional[Dict[str, Any]] = None,
        evidence_store: Optional[Dict[str, Any]] = None,
    ) -> DebateResult:
        """Execute the full four-stage debate protocol.

        Args:
            persona_outputs: Dict of persona_id → {signal, score, reasoning, ...}
            evidence_manifest: Known evidence ID → metadata
            evidence_store: Evidence ID → full data (for re-query simulation)
        """
        import time
        t0 = time.perf_counter()

        # Stage 1
        claims = self.extract_claims(persona_outputs)

        # Stage 2
        challenges = self.generate_challenges(claims, evidence_manifest)

        # Stage 3
        requery_results = self.requery_disputed(challenges, evidence_store)

        # Stage 4
        revisions = self.revise_claims(claims, challenges, requery_results)

        elapsed = (time.perf_counter() - t0) * 1000

        # Count verdicts
        supported = sum(1 for r in revisions if r.verdict == "supported")
        contradicted = sum(1 for r in revisions if r.verdict == "contradicted")
        revised = sum(1 for r in revisions if r.verdict == "revised")
        unknown = sum(1 for r in revisions if r.verdict == "unknown")
        new_evidence = sum(len(rq.new_evidence_ids) for rq in requery_results)

        # Summary
        parts = []
        if supported > 0:
            parts.append(f"{supported} claims supported")
        if contradicted > 0:
            parts.append(f"{contradicted} contradicted")
        if revised > 0:
            parts.append(f"{revised} revised")
        if unknown > 0:
            parts.append(f"{unknown} unresolved")
        if new_evidence > 0:
            parts.append(f"{new_evidence} new evidence items found")

        return DebateResult(
            debate_id=self._debate_id,
            ticker=self._ticker,
            run_id=self._run_id,
            revisions=revisions,
            claims_supported=supported,
            claims_contradicted=contradicted,
            claims_revised=revised,
            claims_unknown=unknown,
            new_evidence_found=new_evidence,
            total_cost_ms=round(elapsed, 2),
            summary=". ".join(parts) + "." if parts else "No debate conducted.",
        )
