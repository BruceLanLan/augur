
"""Decision outcome tracking — score decision quality over time (E03 enhancement)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DecisionScore:
    decision_id: str
    action: str
    outcome: str          # "correct" | "incorrect" | "neutral" | "pending"
    pnl_pct: float = 0.0  # optional return attribution


@dataclass
class OutcomeReport:
    total_decisions: int
    resolved: int
    pending: int
    win_rate: float        # resolved correct / resolved
    by_action: Dict[str, Dict[str, int]] = field(default_factory=dict)
    avg_pnl_pct: float = 0.0


class OutcomeTracker:
    """Track decision outcomes and compute win-rate statistics."""

    def __init__(self):
        self._scores: Dict[str, DecisionScore] = {}

    def record(self, score: DecisionScore) -> None:
        self._scores[score.decision_id] = score

    def report(self) -> OutcomeReport:
        resolved = [s for s in self._scores.values() if s.outcome != "pending"]
        pending = [s for s in self._scores.values() if s.outcome == "pending"]
        correct = sum(1 for s in resolved if s.outcome == "correct")
        win_rate = correct / len(resolved) if resolved else 0.0

        by_action: Dict[str, Dict[str, int]] = {}
        for s in resolved:
            a = by_action.setdefault(s.action, {"correct": 0, "incorrect": 0, "neutral": 0})
            if s.outcome in a:
                a[s.outcome] += 1

        avg_pnl = (
            sum(s.pnl_pct for s in resolved) / len(resolved) if resolved else 0.0
        )

        return OutcomeReport(
            total_decisions=len(self._scores),
            resolved=len(resolved),
            pending=len(pending),
            win_rate=round(win_rate, 4),
            by_action=by_action,
            avg_pnl_pct=round(avg_pnl, 4),
        )
