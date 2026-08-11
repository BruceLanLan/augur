# -*- coding: utf-8 -*-
"""Tests for FilingDelta engine."""

import pytest

from augur.filing_delta import (
    FilingDeltaBuilder,
    FilingDeltaReport,
    GuidanceChange,
    NumericChange,
    TextChange,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_new_filing() -> dict:
    return {
        "filing_date": "2025-11-01",
        "filing_type": "10-Q",
        "metrics": {
            "revenue": 94930.0,
            "net_income": 22956.0,
            "eps_diluted": 1.47,
            "total_assets": 352755.0,
            "gross_margin": 46.2,
            "operating_margin": 29.8,
            "roe": 0.45,
        },
        "sections": {
            "Risk Factors": "We face intense competition... (updated text)",
            "MD&A": "Revenue grew 6% year-over-year...",
        },
        "guidance": {
            "revenue_guidance": (92000, 96000),
        },
    }


@pytest.fixture
def sample_prev_filing() -> dict:
    return {
        "filing_date": "2025-08-01",
        "filing_type": "10-Q",
        "metrics": {
            "revenue": 89498.0,
            "net_income": 21448.0,
            "eps_diluted": 1.38,
            "total_assets": 345000.0,
            "gross_margin": 45.9,
            "operating_margin": 29.5,
            "roe": 0.43,
        },
        "sections": {
            "Risk Factors": "We face intense competition in all markets...",
        },
        "guidance": {
            "revenue_guidance": (89000, 95000),
        },
    }


# ---------------------------------------------------------------------------
# NumericChange
# ---------------------------------------------------------------------------

class TestNumericChange:
    def test_creation(self):
        nc = NumericChange(
            metric="revenue",
            previous_value=100,
            new_value=110,
            change_pct=10.0,
            material=True,
        )
        assert nc.metric == "revenue"
        assert nc.change_pct == 10.0
        assert nc.material is True


# ---------------------------------------------------------------------------
# TextChange
# ---------------------------------------------------------------------------

class TestTextChange:
    def test_creation(self):
        tc = TextChange(
            section="Risk Factors",
            change_type="modified",
            summary="Added new risk",
            material=True,
        )
        assert tc.section == "Risk Factors"


# ---------------------------------------------------------------------------
# FilingDeltaBuilder
# ---------------------------------------------------------------------------

class TestFilingDeltaBuilder:
    def test_build_has_all_sections(self, sample_new_filing, sample_prev_filing):
        builder = FilingDeltaBuilder("AAPL", "new_acc", "prev_acc")
        report = builder.build(sample_new_filing, sample_prev_filing)

        assert report.ticker == "AAPL"
        assert report.new_accession == "new_acc"
        assert report.filing_type == "10-Q"
        assert len(report.numeric_changes) > 0
        assert report.overall_assessment in (
            "significant_changes", "minor_changes", "no_material_changes",
        )

    def test_revenue_change_detected(self, sample_new_filing, sample_prev_filing):
        builder = FilingDeltaBuilder("AAPL", "new", "prev")
        report = builder.build(sample_new_filing, sample_prev_filing)

        rev_change = next(
            (c for c in report.numeric_changes if c.metric == "revenue"), None
        )
        assert rev_change is not None
        assert rev_change.previous_value == 89498.0
        assert rev_change.new_value == 94930.0
        assert rev_change.change_pct > 5.0  # ~6.07% growth → material

    def test_text_section_added_detected(self, sample_new_filing, sample_prev_filing):
        builder = FilingDeltaBuilder("AAPL", "new", "prev")
        report = builder.build(sample_new_filing, sample_prev_filing)

        mdna_changes = [
            c for c in report.text_changes if c.section == "MD&A"
        ]
        assert len(mdna_changes) >= 1  # MD&A added

    def test_guidance_raised_detected(self, sample_new_filing, sample_prev_filing):
        builder = FilingDeltaBuilder("AAPL", "new", "prev")
        report = builder.build(sample_new_filing, sample_prev_filing)

        rev_guidance = next(
            (g for g in report.guidance_changes
             if g.metric == "revenue_guidance"), None
        )
        assert rev_guidance is not None
        # Midpoint: prev=(89000+95000)/2=92000, new=(92000+96000)/2=94000
        # 94000 > 92000*1.02=93840 → raised
        assert rev_guidance.direction == "raised"

    def test_guidance_withdrawn_detected(self):
        new_data = {"guidance": {}}
        prev_data = {"guidance": {"eps_guidance": (5.0, 6.0)}}
        builder = FilingDeltaBuilder("TEST", "n", "p")
        report = builder.build(new_data, prev_data)

        assert len(report.guidance_changes) == 1
        assert report.guidance_changes[0].direction == "withdrawn"

    def test_overall_assessment_significant(self, sample_new_filing, sample_prev_filing):
        builder = FilingDeltaBuilder("AAPL", "new", "prev")
        report = builder.build(sample_new_filing, sample_prev_filing)
        # Multiple material changes expected
        assert report.material_change_count >= 1

    def test_empty_filings(self):
        builder = FilingDeltaBuilder("TEST", "n", "p")
        report = builder.build({}, {})
        assert report.overall_assessment == "no_material_changes"
        assert report.numeric_changes == []
        assert report.text_changes == []

    def test_run_id_preserved(self, sample_new_filing, sample_prev_filing):
        builder = FilingDeltaBuilder("AAPL", "new", "prev")
        report = builder.build(
            sample_new_filing, sample_prev_filing, run_id="run_test_001"
        )
        assert report.run_id == "run_test_001"


# ---------------------------------------------------------------------------
# GuidanceChange
# ---------------------------------------------------------------------------

class TestGuidanceChange:
    def test_creation_raised(self):
        gc = GuidanceChange(
            metric="revenue_guidance",
            previous_range=(89000, 95000),
            new_range=(92000, 96000),
            direction="raised",
        )
        assert gc.metric == "revenue_guidance"
        assert gc.previous_range == (89000, 95000)
        assert gc.direction == "raised"

    def test_creation_withdrawn(self):
        gc = GuidanceChange(
            metric="eps_guidance",
            previous_range=(5.0, 6.0),
            direction="withdrawn",
        )
        assert gc.new_range is None
        assert gc.direction == "withdrawn"

    def test_creation_new(self):
        gc = GuidanceChange(
            metric="fcf_guidance",
            new_range=(10000, 12000),
            direction="new",
        )
        assert gc.previous_range is None
        assert gc.direction == "new"


# ---------------------------------------------------------------------------
# FilingDeltaReport
# ---------------------------------------------------------------------------

class TestFilingDeltaReport:
    def test_creation(self):
        nc = NumericChange(
            metric="revenue", previous_value=100, new_value=110,
            change_pct=10.0, material=True,
        )
        report = FilingDeltaReport(
            ticker="AAPL",
            new_accession="new_acc",
            previous_accession="prev_acc",
            new_filing_date="2025-11-01",
            previous_filing_date="2025-08-01",
            filing_type="10-Q",
            numeric_changes=[nc],
            overall_assessment="minor_changes",
        )
        assert report.ticker == "AAPL"
        assert report.filing_type == "10-Q"
        assert len(report.numeric_changes) == 1
        assert report.overall_assessment == "minor_changes"


# ---------------------------------------------------------------------------
# Additional builder edge-case tests
# ---------------------------------------------------------------------------

class TestFilingDeltaBuilderEdgeCases:
    def test_guidance_narrowed(self):
        """When midpoint stays within ±2%, guidance is 'narrowed'."""
        new_data = {"guidance": {"eps_guidance": (5.10, 5.30)}}
        prev_data = {"guidance": {"eps_guidance": (5.00, 5.40)}}
        builder = FilingDeltaBuilder("TEST", "n", "p")
        report = builder.build(new_data, prev_data)
        assert len(report.guidance_changes) == 1
        # Both midpoints are 5.20 → within 2% → narrowed
        assert report.guidance_changes[0].direction == "narrowed"

    def test_guidance_dict_format(self):
        """Guidance in dict format should also be parsed."""
        new_data = {"guidance": {"rev": {"low": 100, "high": 120}}}
        prev_data = {"guidance": {"rev": {"low": 80, "high": 100}}}
        builder = FilingDeltaBuilder("TEST", "n", "p")
        report = builder.build(new_data, prev_data)
        assert len(report.guidance_changes) == 1
        assert report.guidance_changes[0].direction == "raised"

    def test_material_section_detection(self):
        """Verify _is_material_section identifies key sections."""
        assert FilingDeltaBuilder._is_material_section("Risk Factors") is True
        assert FilingDeltaBuilder._is_material_section("MD&A") is True
        assert FilingDeltaBuilder._is_material_section("Legal Proceedings") is True
        assert FilingDeltaBuilder._is_material_section("Outlook") is True
        assert FilingDeltaBuilder._is_material_section("Signatures") is False
        assert FilingDeltaBuilder._is_material_section("Exhibits") is False

    def test_metric_removed_detected(self):
        """When a metric disappears, it should still appear as a change."""
        new_data = {"metrics": {"revenue": 1000}}
        prev_data = {"metrics": {"revenue": 1000, "net_income": 500}}
        builder = FilingDeltaBuilder("TEST", "n", "p")
        report = builder.build(new_data, prev_data)
        # net_income went from 500 to None → treated as -100% change
        ni_change = next(
            (c for c in report.numeric_changes if c.metric == "net_income"), None
        )
        assert ni_change is not None
        assert ni_change.change_pct == -100.0
        assert ni_change.material is True

    def test_filings_with_financials_key(self):
        """Builder should accept 'financials' as alternative to 'metrics' key."""
        new_data = {"financials": {"revenue": 5000}}
        prev_data = {"financials": {"revenue": 4000}}
        builder = FilingDeltaBuilder("TEST", "n", "p")
        report = builder.build(new_data, prev_data)
        rev_change = next(
            (c for c in report.numeric_changes if c.metric == "revenue"), None
        )
        assert rev_change is not None
        assert rev_change.change_pct == 25.0
