# -*- coding: utf-8 -*-
"""
Citation Correction Queue (A04) — user-reported citation errors as regression cases.

Tracks user corrections to claim-evidence mappings, building a regression
test corpus that prevents the same citation errors from recurring.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from augur.data_dir import get_data_dir


@dataclass
class CitationCorrection:
    """A user-reported correction to a claim's evidence citation."""

    correction_id: str       # cc_{hash[:8]}
    claim_id: str            # claim being corrected
    ticker: str
    reported_by: str = ""    # user or "auto"
    issue_type: str = ""     # "wrong_source" | "fabricated" | "misattributed" | "outdated"
    incorrect_refs: List[str] = field(default_factory=list)
    correct_refs: List[str] = field(default_factory=list)
    description: str = ""
    status: str = "open"     # "open" | "accepted" | "rejected" | "fixed"
    created_at: str = ""
    resolved_at: str = ""


@dataclass
class CitationCorpus:
    """Regression test corpus built from citation corrections."""

    corrections: List[CitationCorrection] = field(default_factory=list)
    total_reported: int = 0
    total_accepted: int = 0
    total_fixed: int = 0


class CitationCorrectionQueue:
    """Queue for user-reported citation errors.

    Each accepted correction becomes a regression test case that
    CitationValidator must pass before future claims are considered valid.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self._path = storage_path or (get_data_dir() / "citation_corrections.json")
        self._corrections: Dict[str, CitationCorrection] = {}
        self._load()

    # ------------------------------------------------------------------
    # Queue operations
    # ------------------------------------------------------------------

    def report(
        self,
        claim_id: str,
        ticker: str,
        issue_type: str,
        incorrect_refs: List[str],
        correct_refs: List[str],
        description: str = "",
        reported_by: str = "user",
    ) -> CitationCorrection:
        """Report a citation error."""
        import hashlib
        cid = f"cc_{hashlib.sha256(claim_id.encode()).hexdigest()[:8]}"
        cc = CitationCorrection(
            correction_id=cid,
            claim_id=claim_id,
            ticker=ticker.upper(),
            reported_by=reported_by,
            issue_type=issue_type,
            incorrect_refs=list(incorrect_refs),
            correct_refs=list(correct_refs),
            description=description,
            status="open",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._corrections[cid] = cc
        self._save()
        return cc

    def accept(self, correction_id: str) -> Optional[CitationCorrection]:
        """Accept a correction — it becomes a regression test case."""
        cc = self._corrections.get(correction_id)
        if cc:
            cc.status = "accepted"
            cc.resolved_at = datetime.now(timezone.utc).isoformat()
            self._save()
        return cc

    def reject(self, correction_id: str, reason: str = "") -> Optional[CitationCorrection]:
        """Reject a correction."""
        cc = self._corrections.get(correction_id)
        if cc:
            cc.status = "rejected"
            cc.description = f"{cc.description} [Rejected: {reason}]"
            self._save()
        return cc

    def mark_fixed(self, correction_id: str) -> Optional[CitationCorrection]:
        """Mark as fixed after code changes."""
        cc = self._corrections.get(correction_id)
        if cc:
            cc.status = "fixed"
            cc.resolved_at = datetime.now(timezone.utc).isoformat()
            self._save()
        return cc

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_open(self) -> List[CitationCorrection]:
        return [c for c in self._corrections.values() if c.status == "open"]

    def list_accepted(self) -> List[CitationCorrection]:
        return [c for c in self._corrections.values() if c.status == "accepted"]

    def get_corpus(self) -> CitationCorpus:
        """Build the regression test corpus from accepted corrections."""
        corrections = list(self._corrections.values())
        return CitationCorpus(
            corrections=corrections,
            total_reported=len(corrections),
            total_accepted=sum(1 for c in corrections if c.status == "accepted"),
            total_fixed=sum(1 for c in corrections if c.status == "fixed"),
        )

    def get_regression_cases(self) -> List[dict]:
        """Return accepted corrections as regression test cases."""
        return [
            {
                "claim_id": c.claim_id,
                "incorrect_refs": c.incorrect_refs,
                "correct_refs": c.correct_refs,
                "issue_type": c.issue_type,
            }
            for c in self._corrections.values()
            if c.status == "accepted"
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        data = {
            cid: {
                "correction_id": cc.correction_id,
                "claim_id": cc.claim_id,
                "ticker": cc.ticker,
                "reported_by": cc.reported_by,
                "issue_type": cc.issue_type,
                "incorrect_refs": cc.incorrect_refs,
                "correct_refs": cc.correct_refs,
                "description": cc.description,
                "status": cc.status,
                "created_at": cc.created_at,
                "resolved_at": cc.resolved_at,
            }
            for cid, cc in self._corrections.items()
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for cid, d in raw.items():
                self._corrections[cid] = CitationCorrection(
                    correction_id=d.get("correction_id", cid),
                    claim_id=d.get("claim_id", ""),
                    ticker=d.get("ticker", ""),
                    reported_by=d.get("reported_by", ""),
                    issue_type=d.get("issue_type", ""),
                    incorrect_refs=d.get("incorrect_refs", []),
                    correct_refs=d.get("correct_refs", []),
                    description=d.get("description", ""),
                    status=d.get("status", "open"),
                    created_at=d.get("created_at", ""),
                    resolved_at=d.get("resolved_at", ""),
                )
        except (json.JSONDecodeError, OSError):
            self._corrections = {}
