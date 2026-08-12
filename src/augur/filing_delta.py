# -*- coding: utf-8 -*-
"""
Filing Delta — structured comparison between two SEC filing snapshots.

Identifies material changes in numbers, risk factors, management language,
and guidance between consecutive 10-K/10-Q/8-K filings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class NumericChange:
    """A change in a financial metric between two filings."""

    metric: str              # e.g. "revenue", "eps_diluted", "total_assets"
    previous_value: float
    new_value: float
    unit: str = ""
    change_pct: float = 0.0
    section: str = ""        # e.g. "Income Statement", "Balance Sheet"
    material: bool = True    # Whether change exceeds materiality threshold


@dataclass
class TextChange:
    """A change in textual content between two filings."""

    section: str             # e.g. "Risk Factors", "MD&A"
    change_type: str         # "added" | "removed" | "modified"
    summary: str             # One-line summary of what changed
    previous_text_snippet: str = ""
    new_text_snippet: str = ""
    material: bool = False


@dataclass
class GuidanceChange:
    """A change in management guidance between two filings."""

    metric: str              # e.g. "revenue_guidance", "eps_guidance"
    previous_range: Optional[tuple] = None  # (low, high)
    new_range: Optional[tuple] = None
    direction: str = ""      # "raised" | "lowered" | "narrowed" | "new" | "withdrawn"
    language_change: str = ""


@dataclass
class FilingDeltaReport:
    """Complete filing-to-filing comparison report."""

    ticker: str
    new_accession: str
    previous_accession: str
    new_filing_date: str = ""
    previous_filing_date: str = ""
    filing_type: str = ""    # "10-K", "10-Q", "8-K"

    # Changes
    numeric_changes: List[NumericChange] = field(default_factory=list)
    text_changes: List[TextChange] = field(default_factory=list)
    guidance_changes: List[GuidanceChange] = field(default_factory=list)

    # Summary
    material_change_count: int = 0
    overall_assessment: str = ""  # "significant_changes" | "minor_changes" | "no_material_changes"
    run_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the report to a JSON-compatible dict."""
        return {
            "ticker": self.ticker,
            "new_accession": self.new_accession,
            "previous_accession": self.previous_accession,
            "new_filing_date": self.new_filing_date,
            "previous_filing_date": self.previous_filing_date,
            "filing_type": self.filing_type,
            "numeric_changes": [
                {
                    "metric": nc.metric,
                    "previous_value": nc.previous_value,
                    "new_value": nc.new_value,
                    "unit": nc.unit,
                    "change_pct": nc.change_pct,
                    "section": nc.section,
                    "material": nc.material,
                }
                for nc in self.numeric_changes
            ],
            "text_changes": [
                {
                    "section": tc.section,
                    "change_type": tc.change_type,
                    "summary": tc.summary,
                    "material": tc.material,
                }
                for tc in self.text_changes
            ],
            "guidance_changes": [
                {
                    "metric": gc.metric,
                    "previous_range": list(gc.previous_range) if gc.previous_range else None,
                    "new_range": list(gc.new_range) if gc.new_range else None,
                    "direction": gc.direction,
                    "language_change": gc.language_change,
                }
                for gc in self.guidance_changes
            ],
            "material_change_count": self.material_change_count,
            "overall_assessment": self.overall_assessment,
            "run_id": self.run_id,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the report to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render the report as a Markdown table summary."""
        lines: List[str] = []

        # Header
        lines.append(f"# Filing Delta Report: {self.ticker}")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Ticker | {self.ticker} |")
        lines.append(f"| Filing Type | {self.filing_type} |")
        lines.append(f"| New Filing Date | {self.new_filing_date} |")
        lines.append(f"| Previous Filing Date | {self.previous_filing_date} |")
        lines.append(f"| New Accession | {self.new_accession} |")
        lines.append(f"| Previous Accession | {self.previous_accession} |")
        lines.append(f"| Overall Assessment | **{self.overall_assessment}** |")
        lines.append(f"| Material Change Count | {self.material_change_count} |")
        lines.append("")

        # Numeric changes table
        if self.numeric_changes:
            lines.append("## Numeric Changes")
            lines.append("")
            lines.append("| Metric | Previous | New | Change % | Material |")
            lines.append("|--------|----------|-----|----------|----------|")
            for nc in self.numeric_changes:
                material_mark = "⚠️ Yes" if nc.material else "No"
                lines.append(
                    f"| {nc.metric} | {nc.previous_value:,.2f} | {nc.new_value:,.2f} | "
                    f"{nc.change_pct:+.2f}% | {material_mark} |"
                )
            lines.append("")

        # Text changes table
        if self.text_changes:
            lines.append("## Text Changes")
            lines.append("")
            lines.append("| Section | Type | Summary | Material |")
            lines.append("|---------|------|---------|----------|")
            for tc in self.text_changes:
                material_mark = "⚠️ Yes" if tc.material else "No"
                lines.append(
                    f"| {tc.section} | {tc.change_type} | {tc.summary} | {material_mark} |"
                )
            lines.append("")

        # Guidance changes table
        if self.guidance_changes:
            lines.append("## Guidance Changes")
            lines.append("")
            lines.append("| Metric | Previous Range | New Range | Direction |")
            lines.append("|--------|---------------|-----------|-----------|")
            for gc in self.guidance_changes:
                prev_str = f"{gc.previous_range[0]:,.0f} – {gc.previous_range[1]:,.0f}" if gc.previous_range else "—"
                new_str = f"{gc.new_range[0]:,.0f} – {gc.new_range[1]:,.0f}" if gc.new_range else "—"
                lines.append(f"| {gc.metric} | {prev_str} | {new_str} | {gc.direction} |")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Filing Delta Builder
# ---------------------------------------------------------------------------

class FilingDeltaBuilder:
    """Build a FilingDeltaReport from two RunBundle or evidence dicts."""

    # Common financial metrics to compare
    _NUMERIC_METRICS = [
        "revenue", "revenue_growth", "gross_profit", "operating_income",
        "net_income", "eps_diluted", "eps_basic",
        "total_assets", "total_liabilities", "total_equity",
        "operating_cash_flow", "free_cash_flow",
        "current_ratio", "debt_to_equity", "gross_margin", "operating_margin",
        "net_margin", "roe", "roa",
        "shares_outstanding", "dividend_per_share",
    ]

    _MATERIALITY_THRESHOLD_PCT = 5.0  # 5% change = material

    def __init__(self, ticker: str, new_accession: str, previous_accession: str):
        self._ticker = ticker.upper()
        self._new_acc = new_accession
        self._prev_acc = previous_accession

    def build(
        self,
        new_data: Dict[str, Any],
        prev_data: Dict[str, Any],
        run_id: Optional[str] = None,
    ) -> FilingDeltaReport:
        """Compare two filing evidence dicts and produce a delta report.

        Args:
            new_data: Evidence dict for the newer filing.
            prev_data: Evidence dict for the older filing.
            run_id: Optional RunBundle ID for provenance.
        """
        report = FilingDeltaReport(
            ticker=self._ticker,
            new_accession=self._new_acc,
            previous_accession=self._prev_acc,
            run_id=run_id,
        )

        # Extract filing metadata
        report.new_filing_date = new_data.get("filing_date", "")
        report.previous_filing_date = prev_data.get("filing_date", "")
        report.filing_type = new_data.get("filing_type", "")

        # Compare numeric metrics
        new_metrics = new_data.get("metrics", new_data.get("financials", {}))
        prev_metrics = prev_data.get("metrics", prev_data.get("financials", {}))
        report.numeric_changes = self._compare_metrics(new_metrics, prev_metrics)

        # Compare text sections
        new_sections = new_data.get("sections", {})
        prev_sections = prev_data.get("sections", {})
        report.text_changes = self._compare_text(new_sections, prev_sections)

        # Compare guidance
        new_guidance = new_data.get("guidance", {})
        prev_guidance = prev_data.get("guidance", {})
        report.guidance_changes = self._compare_guidance(new_guidance, prev_guidance)

        # Summarize
        report.material_change_count = sum(
            1 for c in report.numeric_changes if c.material
        ) + sum(
            1 for c in report.text_changes if c.material
        ) + len(report.guidance_changes)

        if report.material_change_count >= 3:
            report.overall_assessment = "significant_changes"
        elif report.material_change_count >= 1:
            report.overall_assessment = "minor_changes"
        else:
            report.overall_assessment = "no_material_changes"

        return report

    # ------------------------------------------------------------------
    # Metric comparison
    # ------------------------------------------------------------------

    def _compare_metrics(
        self,
        new_metrics: Dict[str, float],
        prev_metrics: Dict[str, float],
    ) -> List[NumericChange]:
        changes: List[NumericChange] = []

        for metric in self._NUMERIC_METRICS:
            new_val = new_metrics.get(metric)
            prev_val = prev_metrics.get(metric)

            if new_val is None and prev_val is None:
                continue
            if new_val is None:
                changes.append(NumericChange(
                    metric=metric,
                    previous_value=prev_val or 0,
                    new_value=0,
                    change_pct=-100.0,
                    material=True,
                ))
                continue
            if prev_val is None:
                changes.append(NumericChange(
                    metric=metric,
                    previous_value=0,
                    new_value=new_val,
                    change_pct=100.0,
                    material=True,
                ))
                continue

            if prev_val == 0 and new_val == 0:
                continue

            prev = float(prev_val)
            new = float(new_val)
            if prev == 0:
                change_pct = 100.0 if new > 0 else -100.0
            else:
                change_pct = ((new - prev) / abs(prev)) * 100

            material = abs(change_pct) >= self._MATERIALITY_THRESHOLD_PCT

            changes.append(NumericChange(
                metric=metric,
                previous_value=prev,
                new_value=new,
                change_pct=round(change_pct, 2),
                material=material,
            ))

        # Sort by materiality and magnitude
        changes.sort(key=lambda c: (not c.material, -abs(c.change_pct)))
        return changes[:20]  # Top 20 changes

    # ------------------------------------------------------------------
    # Text comparison
    # ------------------------------------------------------------------

    def _compare_text(
        self,
        new_sections: Dict[str, str],
        prev_sections: Dict[str, str],
    ) -> List[TextChange]:
        changes: List[TextChange] = []
        all_sections = set(new_sections.keys()) | set(prev_sections.keys())

        for section in sorted(all_sections):
            new_text = new_sections.get(section, "")
            prev_text = prev_sections.get(section, "")

            if not prev_text and new_text:
                changes.append(TextChange(
                    section=section,
                    change_type="added",
                    summary=f"New section '{section}' added",
                    new_text_snippet=new_text[:200],
                    material=self._is_material_section(section),
                ))
            elif prev_text and not new_text:
                changes.append(TextChange(
                    section=section,
                    change_type="removed",
                    summary=f"Section '{section}' removed",
                    previous_text_snippet=prev_text[:200],
                    material=self._is_material_section(section),
                ))
            elif new_text != prev_text:
                # Simple length-based change detection
                len_diff = abs(len(new_text) - len(prev_text))
                len_pct = len_diff / max(len(prev_text), 1) * 100
                if len_pct > 10:
                    changes.append(TextChange(
                        section=section,
                        change_type="modified",
                        summary=f"Section '{section}' modified ({len_pct:.0f}% length change)",
                        previous_text_snippet=prev_text[:150],
                        new_text_snippet=new_text[:150],
                        material=self._is_material_section(section),
                    ))

        return changes

    # ------------------------------------------------------------------
    # Guidance comparison
    # ------------------------------------------------------------------

    def _compare_guidance(
        self,
        new_guidance: Dict[str, Any],
        prev_guidance: Dict[str, Any],
    ) -> List[GuidanceChange]:
        changes: List[GuidanceChange] = []

        for key in set(new_guidance.keys()) | set(prev_guidance.keys()):
            ng = new_guidance.get(key)
            pg = prev_guidance.get(key)

            if pg is None and ng is not None:
                changes.append(GuidanceChange(
                    metric=key,
                    new_range=self._parse_range(ng),
                    direction="new",
                ))
            elif pg is not None and ng is None:
                changes.append(GuidanceChange(
                    metric=key,
                    previous_range=self._parse_range(pg),
                    direction="withdrawn",
                ))
            elif pg is not None and ng is not None:
                prev_range = self._parse_range(pg)
                new_range = self._parse_range(ng)
                if prev_range and new_range:
                    prev_mid = (prev_range[0] + prev_range[1]) / 2
                    new_mid = (new_range[0] + new_range[1]) / 2
                    if new_mid > prev_mid * 1.02:
                        direction = "raised"
                    elif new_mid < prev_mid * 0.98:
                        direction = "lowered"
                    else:
                        direction = "narrowed"
                    changes.append(GuidanceChange(
                        metric=key,
                        previous_range=prev_range,
                        new_range=new_range,
                        direction=direction,
                    ))

        return changes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_range(val: Any) -> Optional[tuple]:
        """Parse a guidance value as (low, high) tuple."""
        if isinstance(val, (list, tuple)) and len(val) == 2:
            return (float(val[0]), float(val[1]))
        if isinstance(val, dict):
            lo = val.get("low", val.get("min"))
            hi = val.get("high", val.get("max"))
            if lo is not None and hi is not None:
                return (float(lo), float(hi))
        if isinstance(val, (int, float)):
            return (float(val), float(val))
        return None

    @staticmethod
    def _is_material_section(section: str) -> bool:
        """Check if a section name indicates material content."""
        material_keywords = [
            "risk", "md&a", "management discussion",
            "legal", "guidance", "outlook", "restatement",
            "internal control", "going concern",
        ]
        section_lower = section.lower()
        return any(kw in section_lower for kw in material_keywords)
