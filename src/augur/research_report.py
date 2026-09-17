# -*- coding: utf-8 -*-
"""Comprehensive research report — aggregate evidence, claims, disagreement, thesis.

Combines all v11 research-memory modules into a single machine-readable
+ human-readable research report with full provenance.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResearchReport:
    """Aggregated research report for a ticker."""

    ticker: str
    run_id: str = ""
    consensus: Dict[str, Any] = field(default_factory=dict)
    disagreement: Dict[str, Any] = field(default_factory=dict)
    thesis_deltas: List[Dict[str, Any]] = field(default_factory=list)
    change_ledger: Dict[str, Any] = field(default_factory=dict)
    scorecard: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    open_questions: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: str = ""

    def to_markdown(self) -> str:
        """Render the report as Markdown."""
        lines: List[str] = []
        lines.append(f"# Research Report: {self.ticker}")
        lines.append("")

        if self.consensus:
            lines.append("## Consensus")
            lines.append("")
            for k, v in self.consensus.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")

        if self.disagreement:
            lines.append("## Disagreement Map")
            lines.append("")
            dm = self.disagreement
            lines.append(f"Strength: {dm.get('consensus_strength', 'unknown')} · derivation: {dm.get('derivation', 'n/a')}")
            if dm.get("summary"):
                lines.append("")
                lines.append(dm["summary"])
            lines.append("")
            for cp in dm.get("conflict_points", [])[:5]:
                lines.append(f"- **{cp.get('claim', '')}** (impact: {cp.get('impact', '')})")
                scores = cp.get("persona_scores") or {}
                if cp.get("bullish_personas"):
                    lines.append("  - high: " + ", ".join(f"{p} {scores.get(p, '')}".strip() for p in cp["bullish_personas"]))
                if cp.get("bearish_personas"):
                    lines.append("  - low: " + ", ".join(f"{p} {scores.get(p, '')}".strip() for p in cp["bearish_personas"]))
                if cp.get("evidence_supporting"):
                    lines.append("  - evidence: " + ", ".join(f"`{e}`" for e in cp["evidence_supporting"]))
                if cp.get("information_that_would_resolve"):
                    lines.append(f"  - would resolve: {cp['information_that_would_resolve']}")
            for point in dm.get("agreement_points", []):
                lines.append(f"- agreement: {point}")
            for gap in dm.get("evidence_gaps", []):
                lines.append(f"- evidence gap: {gap}")
            lines.append("")

        if self.change_ledger and self.change_ledger.get("entries"):
            lines.append("## Change Ledger")
            lines.append("")
            for e in self.change_ledger["entries"][:10]:
                lines.append(f"- [{e.get('category', '')}] {e.get('before', '')} → {e.get('after', '')}")
            lines.append("")

        if self.thesis_deltas:
            lines.append("## Thesis Updates")
            lines.append("")
            for td in self.thesis_deltas:
                lines.append(f"- **{td.get('overall_assessment', '')}**")
            lines.append("")

        if self.scorecard:
            lines.append("## Scorecard")
            lines.append("")
            lines.append(f"Accuracy: {self.scorecard.get('accuracy', 0):.0%}")
            lines.append("")

        if self.open_questions:
            lines.append("## Open Questions")
            lines.append("")
            for q in self.open_questions:
                lines.append(f"- {q.get('question', '')}")
            lines.append("")

        if self.provenance:
            lines.append("## Provenance")
            lines.append("")
            for k, v in self.provenance.items():
                lines.append(f"- {k}: {v}")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialize the full report."""
        return json.dumps({
            "ticker": self.ticker, "run_id": self.run_id,
            "consensus": self.consensus, "disagreement": self.disagreement,
            "thesis_deltas": self.thesis_deltas, "change_ledger": self.change_ledger,
            "scorecard": self.scorecard, "provenance": self.provenance,
            "open_questions": self.open_questions, "generated_at": self.generated_at,
        }, indent=2, default=str)


class ResearchReportBuilder:
    """Build a ResearchReport by aggregating module outputs."""

    def build(
        self,
        ticker: str,
        run_id: str = "",
        consensus: Optional[Dict] = None,
        disagreement: Optional[Dict] = None,
        thesis_deltas: Optional[List[Dict]] = None,
        change_ledger: Optional[Dict] = None,
        scorecard: Optional[Dict] = None,
        provenance: Optional[Dict] = None,
        open_questions: Optional[List[Dict]] = None,
    ) -> ResearchReport:
        """Assemble all inputs into a single report."""
        from datetime import datetime, timezone
        return ResearchReport(
            ticker=ticker.upper(), run_id=run_id,
            consensus=consensus or {}, disagreement=disagreement or {},
            thesis_deltas=thesis_deltas or [], change_ledger=change_ledger or {},
            scorecard=scorecard or {}, provenance=provenance or {},
            open_questions=open_questions or [],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
