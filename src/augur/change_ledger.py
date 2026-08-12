# -*- coding: utf-8 -*-
"""
Change Ledger — cross-quarter change accounting (B04).

Compares two analysis "run" snapshots (one per fiscal quarter) and produces a
:class:`ChangeLedger` of individual :class:`LedgerEntry` records, one per
detected change, tagged by category:

  - ``guidance``       — management guidance raised / lowered / narrowed / new / withdrawn
  - ``fundamentals``   — financial metrics that moved materially
  - ``risk``           — risk factors added or removed
  - ``disagreement``   — analyst disagreement / consensus shifts
  - ``language``       — (reserved) management language drift
  - ``ownership``      — (reserved) ownership-structure changes

The builder consumes plain dicts (the same shape produced/consumed by
:mod:`augur.filing_delta`), so it can be driven directly off filing-evidence
snapshots.  ``language`` and ``ownership`` are part of the entry vocabulary but
are not auto-extracted yet.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Valid entry categories, in a stable display order.
CATEGORIES = (
    "guidance",
    "fundamentals",
    "risk",
    "language",
    "ownership",
    "disagreement",
)

# A metric move at or above this absolute percentage counts as material.
_MATERIALITY_THRESHOLD_PCT = 5.0

# Guidance midpoint shift at or above this percentage is raised/lowered.
_GUIDANCE_MOVE_THRESHOLD_PCT = 2.0


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class LedgerEntry:
    """A single cross-quarter change.

    Attributes:
        entry_id: Stable identifier (``TICKER_QUARTER_CATEGORY_NNN``).
        ticker: Instrument ticker.
        quarter: The quarter the change lands in (the "to" quarter), e.g. ``"Q4_2025"``
            for a ``"Q3_2025"`` → ``"Q4_2025"`` transition.
        category: One of :data:`CATEGORIES`.
        before: Human-readable "before" value (``"—"`` when there was no prior value).
        after: Human-readable "after" value (``"—"`` when the value was removed).
        material: Whether this change is material to the thesis.
        evidence_refs: Source locators backing this change.
    """

    entry_id: str
    ticker: str
    quarter: str
    category: str
    before: str
    after: str
    material: bool
    evidence_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "entry_id": self.entry_id,
            "ticker": self.ticker,
            "quarter": self.quarter,
            "category": self.category,
            "before": self.before,
            "after": self.after,
            "material": self.material,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass
class ChangeLedger:
    """All cross-quarter changes for a ticker between two quarters."""

    ticker: str
    from_quarter: str
    to_quarter: str
    entries: List[LedgerEntry] = field(default_factory=list)
    summary: str = ""

    @property
    def material_entries(self) -> List[LedgerEntry]:
        """Return only the material entries."""
        return [e for e in self.entries if e.material]

    @property
    def material_change_count(self) -> int:
        """Number of material entries."""
        return len(self.material_entries)

    @property
    def by_category(self) -> Dict[str, int]:
        """Count of entries per category."""
        counts = Counter(e.category for e in self.entries)
        return dict(counts)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "ticker": self.ticker,
            "from_quarter": self.from_quarter,
            "to_quarter": self.to_quarter,
            "entries": [e.to_dict() for e in self.entries],
            "summary": self.summary,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render the ledger as a Markdown table."""
        lines: List[str] = [
            f"# Change Ledger: {self.ticker} ({self.from_quarter or '—'} → "
            f"{self.to_quarter or '—'})",
            "",
            self.summary,
            "",
        ]
        if not self.entries:
            return "\n".join(lines)

        lines += [
            "| # | Category | Before | After | Material |",
            "|---|----------|--------|-------|----------|",
        ]
        for e in self.entries:
            material_mark = "⚠️ Yes" if e.material else "No"
            before = e.before.replace("|", "\\|")
            after = e.after.replace("|", "\\|")
            lines.append(
                f"| {e.entry_id} | {e.category} | {before} | {after} | {material_mark} |"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Change Ledger Builder
# ---------------------------------------------------------------------------

class ChangeLedgerBuilder:
    """Build a :class:`ChangeLedger` from two quarter run snapshots.

    A "run" dict is a per-quarter snapshot with any of the following keys
    (all optional, unknown keys ignored)::

        quarter | fiscal_period | filing_date   — used to infer the quarter label
        guidance                                — {metric: (low, high) | {low, high} | scalar}
        metrics | financials | fundamentals     — {metric: number}
        risks | risk_factors                    — [str, ...]
        sections                                — {section_name: text}
        disagreement                            — dict or list (consensus/conflict data)
    """

    @staticmethod
    def build(prev_run: dict, new_run: dict, ticker: str) -> ChangeLedger:
        """Compare two quarter snapshots and produce a :class:`ChangeLedger`.

        Args:
            prev_run: Snapshot for the earlier quarter.
            new_run: Snapshot for the later quarter.
            ticker: Instrument ticker.
        """
        ticker = ticker.upper()
        from_quarter = ChangeLedgerBuilder._extract_quarter(prev_run)
        to_quarter = ChangeLedgerBuilder._extract_quarter(new_run) or from_quarter

        grouped: List[List[LedgerEntry]] = [
            ChangeLedgerBuilder.diff_guidance(prev_run, new_run),
            ChangeLedgerBuilder.diff_fundamentals(prev_run, new_run),
            ChangeLedgerBuilder.diff_risks(prev_run, new_run),
            ChangeLedgerBuilder.diff_disagreement(prev_run, new_run),
        ]

        entries: List[LedgerEntry] = []
        for group in grouped:
            entries.extend(group)

        # Fill in per-entry context and assign stable ids.
        for i, entry in enumerate(entries):
            entry.ticker = ticker
            entry.quarter = to_quarter
            entry.entry_id = f"{ticker}_{to_quarter}_{entry.category}_{i + 1:03d}"

        summary = ChangeLedgerBuilder._summarize(
            ticker, from_quarter, to_quarter, entries
        )
        return ChangeLedger(
            ticker=ticker,
            from_quarter=from_quarter,
            to_quarter=to_quarter,
            entries=entries,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Guidance diff
    # ------------------------------------------------------------------

    @staticmethod
    def diff_guidance(prev: dict, new: dict) -> List[LedgerEntry]:
        """Diff guidance ranges between two snapshots."""
        prev_g = prev.get("guidance", {}) or {}
        new_g = new.get("guidance", {}) or {}
        if not isinstance(prev_g, dict) or not isinstance(new_g, dict):
            return []

        entries: List[LedgerEntry] = []
        for metric in sorted(set(prev_g) | set(new_g)):
            prev_range = ChangeLedgerBuilder._parse_range(prev_g.get(metric))
            new_range = ChangeLedgerBuilder._parse_range(new_g.get(metric))

            if prev_range is None and new_range is None:
                continue
            if prev_range is None:
                direction, material = "new", True
            elif new_range is None:
                direction, material = "withdrawn", True
            else:
                direction = ChangeLedgerBuilder._range_direction(
                    prev_range, new_range
                )
                material = direction in ("raised", "lowered")

            entries.append(LedgerEntry(
                entry_id="",
                ticker="",
                quarter="",
                category="guidance",
                before=f"{metric}: {ChangeLedgerBuilder._fmt_range(prev_range)}",
                after=(
                    f"{metric}: {ChangeLedgerBuilder._fmt_range(new_range)} "
                    f"({direction})"
                ),
                material=material,
                evidence_refs=[f"guidance:{metric}"],
            ))
        return entries

    # ------------------------------------------------------------------
    # Fundamentals diff
    # ------------------------------------------------------------------

    @staticmethod
    def diff_fundamentals(prev: dict, new: dict) -> List[LedgerEntry]:
        """Diff fundamental metrics between two snapshots."""
        prev_m = ChangeLedgerBuilder._extract_metrics(prev)
        new_m = ChangeLedgerBuilder._extract_metrics(new)

        entries: List[LedgerEntry] = []
        for metric in sorted(set(prev_m) | set(new_m)):
            p = prev_m.get(metric)
            n = new_m.get(metric)

            if p is None and n is None:
                continue
            if p is None:
                entries.append(LedgerEntry(
                    entry_id="",
                    ticker="",
                    quarter="",
                    category="fundamentals",
                    before="—",
                    after=f"{metric}: {ChangeLedgerBuilder._fmt_num(n)} (new)",
                    material=True,
                    evidence_refs=[f"fundamentals:{metric}"],
                ))
                continue
            if n is None:
                entries.append(LedgerEntry(
                    entry_id="",
                    ticker="",
                    quarter="",
                    category="fundamentals",
                    before=f"{metric}: {ChangeLedgerBuilder._fmt_num(p)}",
                    after="—",
                    material=True,
                    evidence_refs=[f"fundamentals:{metric}"],
                ))
                continue

            p_f, n_f = float(p), float(n)
            if p_f == 0 and n_f == 0:
                continue
            change_pct = ChangeLedgerBuilder._change_pct(p_f, n_f)
            if abs(change_pct) < 0.01:
                continue  # unchanged metric — skip entirely
            material = abs(change_pct) >= _MATERIALITY_THRESHOLD_PCT

            entries.append(LedgerEntry(
                entry_id="",
                ticker="",
                quarter="",
                category="fundamentals",
                before=f"{metric}: {ChangeLedgerBuilder._fmt_num(p_f)}",
                after=(
                    f"{metric}: {ChangeLedgerBuilder._fmt_num(n_f)} "
                    f"({change_pct:+.1f}%)"
                ),
                material=material,
                evidence_refs=[f"fundamentals:{metric}"],
            ))
        return entries

    # ------------------------------------------------------------------
    # Risk diff
    # ------------------------------------------------------------------

    @staticmethod
    def diff_risks(prev: dict, new: dict) -> List[LedgerEntry]:
        """Diff risk factors between two snapshots (added / removed)."""
        prev_risks = ChangeLedgerBuilder._extract_risks(prev)
        new_risks = ChangeLedgerBuilder._extract_risks(new)

        entries: List[LedgerEntry] = []
        for text in sorted(new_risks - prev_risks):
            entries.append(LedgerEntry(
                entry_id="",
                ticker="",
                quarter="",
                category="risk",
                before="—",
                after=f"Added risk: {text}",
                material=True,
                evidence_refs=[ChangeLedgerBuilder._text_ref("risk", text)],
            ))
        for text in sorted(prev_risks - new_risks):
            entries.append(LedgerEntry(
                entry_id="",
                ticker="",
                quarter="",
                category="risk",
                before=f"Removed risk: {text}",
                after="—",
                material=True,
                evidence_refs=[ChangeLedgerBuilder._text_ref("risk", text)],
            ))
        return entries


    # ------------------------------------------------------------------
    # Disagreement helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _consensus_strength(d: Any) -> str:
        """Extract consensus strength from a disagreement dict."""
        if isinstance(d, dict):
            return str(d.get("consensus_strength", d.get("strength", "unknown")))
        return "unknown"

    @staticmethod
    def _conflict_count(d: Any) -> int:
        """Count conflict points in a disagreement dict."""
        if isinstance(d, dict):
            conflicts = d.get("conflict_points", d.get("conflicts", []))
            if isinstance(conflicts, list):
                return len(conflicts)
        return 0

    # ------------------------------------------------------------------
    # Disagreement diff
    # ------------------------------------------------------------------

    @staticmethod
    def diff_disagreement(prev: dict, new: dict) -> List[LedgerEntry]:
        """Diff analyst disagreement / consensus signals between snapshots."""
        prev_d = prev.get("disagreement")
        new_d = new.get("disagreement")
        if not prev_d and not new_d:
            return []

        prev_strength = ChangeLedgerBuilder._consensus_strength(prev_d)
        new_strength = ChangeLedgerBuilder._consensus_strength(new_d)
        prev_count = ChangeLedgerBuilder._conflict_count(prev_d)
        new_count = ChangeLedgerBuilder._conflict_count(new_d)

        if prev_strength == new_strength and prev_count == new_count:
            return []

        def describe(d: Any) -> str:
            strength = ChangeLedgerBuilder._consensus_strength(d)
            count = ChangeLedgerBuilder._conflict_count(d)
            return f"consensus: {strength} ({count} conflict(s))"

        return [LedgerEntry(
            entry_id="",
            ticker="",
            quarter="",
            category="disagreement",
            before=describe(prev_d),
            after=describe(new_d),
            material=prev_strength != new_strength or prev_count != new_count,
            evidence_refs=["disagreement:consensus"],
        )]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize(
        ticker: str,
        from_quarter: str,
        to_quarter: str,
        entries: List[LedgerEntry],
    ) -> str:
        if not entries:
            return (
                f"No cross-quarter changes detected for {ticker} "
                f"between {from_quarter or '—'} and {to_quarter or '—'}."
            )
        material_count = sum(1 for e in entries if e.material)
        counts = Counter(e.category for e in entries)
        parts = ", ".join(
            f"{n} {cat}" for cat, n in sorted(counts.items())
        )
        return (
            f"{len(entries)} changes ({material_count} material) between "
            f"{from_quarter or '—'} and {to_quarter or '—'}: {parts}."
        )

    @staticmethod
    def _extract_quarter(run: dict) -> str:
        """Best-effort quarter label (``Q{N}_{YYYY}``) from a run dict."""
        for key in ("quarter", "fiscal_period", "period"):
            raw = run.get(key)
            if raw:
                m = re.search(r"Q([1-4])[\s_\-]*(\d{4})", str(raw), re.IGNORECASE)
                if m:
                    return f"Q{m.group(1)}_{m.group(2)}"

        filing_date = run.get("filing_date") or run.get("date")
        if filing_date:
            try:
                dt = datetime.strptime(str(filing_date)[:10], "%Y-%m-%d")
                return f"Q{(dt.month - 1) // 3 + 1}_{dt.year}"
            except ValueError:
                pass
        return ""

    @staticmethod
    def _extract_metrics(run: dict) -> Dict[str, Any]:
        for key in ("metrics", "financials", "fundamentals"):
            val = run.get(key)
            if isinstance(val, dict):
                return val
        return {}

    @staticmethod
    def _extract_risks(run: dict) -> "set[str]":
        for key in ("risks", "risk_factors"):
            val = run.get(key)
            if isinstance(val, list):
                return {str(x).strip() for x in val if str(x).strip()}

        sections = run.get("sections")
        if isinstance(sections, dict):
            risk_text = sections.get("Risk Factors") or sections.get("risk_factors")
            if risk_text:
                return {str(risk_text).strip()}
        return set()

    @staticmethod
    def _parse_range(val: Any) -> Optional[tuple]:
        """Parse a guidance value as ``(low, high)`` or ``None``."""
        if isinstance(val, (list, tuple)) and len(val) == 2:
            try:
                return (float(val[0]), float(val[1]))
            except (TypeError, ValueError):
                return None
        if isinstance(val, dict):
            lo = val.get("low", val.get("min"))
            hi = val.get("high", val.get("max"))
            if lo is not None and hi is not None:
                try:
                    return (float(lo), float(hi))
                except (TypeError, ValueError):
                    return None
        if isinstance(val, (int, float)):
            return (float(val), float(val))
        return None

    @staticmethod
    def _range_direction(prev_range: tuple, new_range: tuple) -> str:
        """Classify a guidance range move as raised/lowered/narrowed."""
        prev_mid = (prev_range[0] + prev_range[1]) / 2
        new_mid = (new_range[0] + new_range[1]) / 2
        if prev_mid == 0:
            return "narrowed"
        delta_pct = ((new_mid - prev_mid) / abs(prev_mid)) * 100
        if delta_pct > _GUIDANCE_MOVE_THRESHOLD_PCT:
            return "raised"
        if delta_pct < -_GUIDANCE_MOVE_THRESHOLD_PCT:
            return "lowered"
        return "narrowed"

    @staticmethod
    def _change_pct(prev: float, new: float) -> float:
        if prev == 0:
            return 100.0 if new > 0 else -100.0
        return ((new - prev) / abs(prev)) * 100

    @staticmethod
    def _fmt_range(r: Optional[tuple]) -> str:
        if r is None:
            return "—"
        lo, hi = r
        if lo == hi:
            return f"{lo:,.0f}"
        return f"{lo:,.0f}–{hi:,.0f}"

    @staticmethod
    def _fmt_num(v: Any) -> str:
        return f"{float(v):,.2f}"

    @staticmethod
    def _text_ref(kind: str, text: str) -> str:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        return f"{kind}:{digest}"
