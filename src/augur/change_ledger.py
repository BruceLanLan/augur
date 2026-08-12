# -*- coding: utf-8 -*-
"""
Cross-quarter Change Ledger (B04) — track what changed between quarters.

Integrates with FilingDelta output to produce a categorized change ledger
covering guidance, fundamentals, risks, language, ownership, and disagreement.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LedgerEntry:
    """A single material change between two quarters."""

    entry_id: str
    ticker: str
    category: str          # guidance | fundamentals | risk | language | ownership | disagreement
    quarter_from: str
    quarter_to: str
    before: str
    after: str
    material: bool = True
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class ChangeLedger:
    """Complete cross-quarter change ledger."""

    ticker: str
    from_quarter: str
    to_quarter: str
    entries: List[LedgerEntry] = field(default_factory=list)
    summary: str = ""

    @property
    def material_count(self) -> int:
        return sum(1 for e in self.entries if e.material)

    @property
    def by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.entries:
            counts[e.category] = counts.get(e.category, 0) + 1
        return counts


class ChangeLedgerBuilder:
    """Build a ChangeLedger from two run bundles or filing data dicts."""

    def __init__(self, ticker: str):
        self._ticker = ticker.upper()

    def build(
        self,
        prev: Dict[str, Any],
        new: Dict[str, Any],
        from_quarter: str = "",
        to_quarter: str = "",
    ) -> ChangeLedger:
        """Build a complete change ledger comparing two quarters."""
        ledger = ChangeLedger(
            ticker=self._ticker,
            from_quarter=from_quarter,
            to_quarter=to_quarter,
        )

        ledger.entries.extend(self.diff_guidance(prev, new, from_quarter, to_quarter))
        ledger.entries.extend(self.diff_fundamentals(prev, new, from_quarter, to_quarter))
        ledger.entries.extend(self.diff_risks(prev, new, from_quarter, to_quarter))
        ledger.entries.extend(self.diff_disagreement(prev, new, from_quarter, to_quarter))

        # Summary
        cats = ledger.by_category
        parts = []
        for cat in ("guidance", "fundamentals", "risk", "disagreement"):
            if cats.get(cat):
                parts.append(f"{cats[cat]} {cat}")
        ledger.summary = (
            f"{self._ticker} {from_quarter}→{to_quarter}: "
            + (", ".join(parts) if parts else "no material changes")
        )
        return ledger

    # ------------------------------------------------------------------
    # Diff helpers
    # ------------------------------------------------------------------

    def diff_guidance(
        self, prev: Dict, new: Dict, qf: str = "", qt: str = ""
    ) -> List[LedgerEntry]:
        entries: List[LedgerEntry] = []
        pg = prev.get("guidance", {})
        ng = new.get("guidance", {})
        for key in set(pg.keys()) | set(ng.keys()):
            p = pg.get(key)
            n = ng.get(key)
            if p != n and (p is not None or n is not None):
                entries.append(self._entry(
                    "guidance", qf, qt,
                    str(p or "none"), str(n or "none"),
                ))
        return entries

    def diff_fundamentals(
        self, prev: Dict, new: Dict, qf: str = "", qt: str = ""
    ) -> List[LedgerEntry]:
        entries: List[LedgerEntry] = []
        pf = prev.get("metrics", prev.get("financials", {}))
        nf = new.get("metrics", new.get("financials", {}))
        for key in set(pf.keys()) | set(nf.keys()):
            p = pf.get(key)
            n = nf.get(key)
            if p != n and p is not None and n is not None:
                try:
                    change_pct = abs((float(n) - float(p)) / max(abs(float(p)), 1e-9)) * 100
                    if change_pct >= 5.0:
                        entries.append(self._entry(
                            "fundamentals", qf, qt,
                            f"{key}={p}", f"{key}={n} ({change_pct:.1f}% change)",
                        ))
                except (TypeError, ValueError, ZeroDivisionError):
                    continue
        return entries

    def diff_risks(
        self, prev: Dict, new: Dict, qf: str = "", qt: str = ""
    ) -> List[LedgerEntry]:
        entries: List[LedgerEntry] = []
        pr = set(prev.get("risks", []))
        nr = set(new.get("risks", []))
        for r in nr - pr:
            entries.append(self._entry("risk", qf, qt, "none", f"new risk: {r}"))
        for r in pr - nr:
            entries.append(self._entry("risk", qf, qt, f"removed risk: {r}", "none"))
        return entries

    def diff_disagreement(
        self, prev: Dict, new: Dict, qf: str = "", qt: str = ""
    ) -> List[LedgerEntry]:
        entries: List[LedgerEntry] = []
        pc = prev.get("consensus_strength", "")
        nc = new.get("consensus_strength", "")
        if pc != nc and pc and nc:
            entries.append(self._entry(
                "disagreement", qf, qt, pc, nc,
            ))
        return entries

    def _entry(
        self, category: str, qf: str, qt: str, before: str, after: str
    ) -> LedgerEntry:
        eid = f"le_{hashlib.sha256(f'{self._ticker}:{category}:{before}:{after}'.encode()).hexdigest()[:12]}"
        return LedgerEntry(
            entry_id=eid,
            ticker=self._ticker,
            category=category,
            quarter_from=qf,
            quarter_to=qt,
            before=before[:200],
            after=after[:200],
        )
