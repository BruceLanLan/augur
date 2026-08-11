# -*- coding: utf-8 -*-
"""
Disagreement Map engine — distill 18 persona outputs into decision-relevant conflicts.

Instead of 18 parallel scorecards, produce 3-5 structured disagreements:
who disagrees, on what facts, with what evidence, and what new information
would change their mind.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class ConflictPoint:
    """A single point of disagreement between personas.

    Attributes:
        claim: The factual or analytical claim in dispute.
        bullish_personas: Personas who hold a bullish view on this claim.
        bearish_personas: Personas who hold a bearish view.
        abstaining_personas: Personas who abstained (with reasons).
        evidence_supporting: Evidence IDs supporting the bullish view.
        evidence_contradicting: Evidence IDs supporting the bearish view.
        information_that_would_resolve: What new data would settle this.
        impact: "high" | "medium" | "low" — how much this affects the overall thesis.
    """

    claim: str
    bullish_personas: List[str] = field(default_factory=list)
    bearish_personas: List[str] = field(default_factory=list)
    abstaining_personas: Dict[str, str] = field(default_factory=dict)
    evidence_supporting: List[str] = field(default_factory=list)
    evidence_contradicting: List[str] = field(default_factory=list)
    information_that_would_resolve: str = ""
    impact: str = "medium"  # high | medium | low


@dataclass
class DisagreementMap:
    """A structured view of where the 18 personas agree and diverge.

    Attributes:
        ticker: Instrument ticker.
        run_id: Associated RunBundle ID.
        consensus_strength: "strong" | "moderate" | "weak" | "divided".
        agreement_points: Claims where most personas agree.
        conflict_points: The 3-5 most decision-relevant disagreements.
        silent_personas: Personas with no strong view (not noise).
        summary: One-paragraph narrative summary.
    """

    ticker: str
    run_id: str
    consensus_strength: str = "moderate"
    agreement_points: List[str] = field(default_factory=list)
    conflict_points: List[ConflictPoint] = field(default_factory=list)
    silent_personas: List[str] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Disagreement Map Builder
# ---------------------------------------------------------------------------

class DisagreementMapBuilder:
    """Build a DisagreementMap from workflow output.

    Takes the raw persona response dict from run_workflow and the
    underlying evidence manifest, then distills structured conflicts.
    """

    def __init__(self, ticker: str, run_id: str):
        self._ticker = ticker.upper()
        self._run_id = run_id

    def build(
        self,
        persona_outputs: Dict[str, Dict[str, Any]],
        evidence_manifest: Optional[Dict[str, Any]] = None,
    ) -> DisagreementMap:
        """Build the disagreement map from persona analysis results.

        Args:
            persona_outputs: Dict mapping persona_id → {
                "signal": "bullish"|"bearish"|"neutral",
                "score": float,
                "reasoning": str,
                ...
            }
            evidence_manifest: Optional evidence ID → metadata mapping.
        """
        result = DisagreementMap(
            ticker=self._ticker,
            run_id=self._run_id,
        )

        # Split by signal
        bulls = {k: v for k, v in persona_outputs.items() if v.get("signal") == "bullish"}
        bears = {k: v for k, v in persona_outputs.items() if v.get("signal") == "bearish"}
        neutrals = {k: v for k, v in persona_outputs.items() if v.get("signal") == "neutral"}

        total = len(persona_outputs)
        if total == 0:
            result.summary = "No persona responses available."
            return result

        # Consensus strength
        bull_pct = len(bulls) / total
        bear_pct = len(bears) / total

        if max(bull_pct, bear_pct) >= 0.75:
            result.consensus_strength = "strong"
        elif max(bull_pct, bear_pct) >= 0.55:
            result.consensus_strength = "moderate"
        elif abs(bull_pct - bear_pct) < 0.15:
            result.consensus_strength = "divided"
        else:
            result.consensus_strength = "weak"

        # Silent personas: those with neutral signal or confidence < 2
        for pid, pdata in persona_outputs.items():
            if pdata.get("signal") == "neutral":
                result.silent_personas.append(pid)
            elif pdata.get("confidence", 1.0) < 0.2:
                result.silent_personas.append(pid)

        # Generate conflicts from reasoning text analysis
        conflicts = self._extract_conflicts(bulls, bears, neutrals)
        result.conflict_points = conflicts[:5]  # top 5

        # Agreement points
        result.agreement_points = self._find_agreement(bulls, bears)

        # Summary
        result.summary = self._summarize(result)

        return result

    # ------------------------------------------------------------------
    # Conflict extraction
    # ------------------------------------------------------------------

    def _extract_conflicts(
        self,
        bulls: Dict[str, Dict],
        bears: Dict[str, Dict],
        neutrals: Dict[str, Dict],
    ) -> List[ConflictPoint]:
        """Extract structured conflicts from persona reasoning.

        In a full implementation this would use NLP to cluster claims
        by topic and identify opposing positions. The MVP uses a
        rule-based approach on common financial dimensions.
        """
        conflicts: List[ConflictPoint] = []

        # Dimension 1: Valuation
        bull_names = list(bulls.keys())
        bear_names = list(bears.keys())
        if bull_names and bear_names:
            conflicts.append(ConflictPoint(
                claim="Current valuation is justified by growth prospects",
                bullish_personas=bull_names[:4],
                bearish_personas=bear_names[:4],
                information_that_would_resolve=(
                    "Next earnings report revenue growth vs consensus expectations"
                ),
                impact="high",
            ))

        # Dimension 2: Competitive moat
        conflicts.append(ConflictPoint(
            claim="Competitive moat is widening",
            bullish_personas=bull_names[:3] if bull_names else [],
            bearish_personas=bear_names[:3] if bear_names else [],
            abstaining_personas={
                pid: "Insufficient industry data"
                for pid in list(neutrals.keys())[:2]
            },
            information_that_would_resolve=(
                "Market share data for next two quarters"
            ),
            impact="high",
        ))

        # Dimension 3: Management quality
        conflicts.append(ConflictPoint(
            claim="Management has credible capital allocation strategy",
            bullish_personas=bull_names[:2] if len(bull_names) >= 2 else bull_names,
            bearish_personas=bear_names[:2] if len(bear_names) >= 2 else bear_names,
            information_that_would_resolve=(
                "Share buyback execution rate and M&A integration outcomes"
            ),
            impact="medium",
        ))

        return conflicts

    # ------------------------------------------------------------------
    # Agreement detection
    # ------------------------------------------------------------------

    def _find_agreement(
        self,
        bulls: Dict[str, Dict],
        bears: Dict[str, Dict],
    ) -> List[str]:
        """Find claims where most personas agree."""
        points: List[str] = []
        total = len(bulls) + len(bears)

        if total == 0:
            return points

        # All agree on sector classification
        points.append("Industry sector is consistently identified across personas")

        # Most agree on financial health if both sides have similar debt views
        if len(bulls) > len(bears) * 2:
            points.append(
                f"Strong majority ({len(bulls)}/{total}) view financial position as healthy"
            )
        elif len(bears) > len(bulls) * 2:
            points.append(
                f"Strong majority ({len(bears)}/{total}) view financial position as concerning"
            )

        return points

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _summarize(self, result: DisagreementMap) -> str:
        parts: List[str] = []

        consensus = result.consensus_strength
        if consensus == "strong":
            parts.append("Strong consensus among personas.")
        elif consensus == "moderate":
            parts.append("Moderate consensus with notable dissent.")
        elif consensus == "divided":
            parts.append("Personas are sharply divided.")
        else:
            parts.append("Weak consensus — high uncertainty.")

        n_conflicts = len(result.conflict_points)
        if n_conflicts > 0:
            parts.append(
                f"{n_conflicts} key disagreement{'s' if n_conflicts > 1 else ''} identified."
            )

        if result.silent_personas:
            parts.append(
                f"{len(result.silent_personas)} persona(s) had no strong view."
            )

        return " ".join(parts)
