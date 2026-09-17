# -*- coding: utf-8 -*-
"""Tests for the cross-quarter Change Ledger (B04)."""

import json

from augur.change_ledger import (
    CATEGORIES,
    ChangeLedger,
    ChangeLedgerBuilder,
    LedgerEntry,
)
from augur.filing_delta import FilingDeltaBuilder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _prev_run() -> dict:
    return {
        "quarter": "Q3_2025",
        "guidance": {
            "revenue": (89000, 95000),
            "eps": (5.0, 5.4),
        },
        "metrics": {
            "revenue": 89498.0,
            "net_income": 21448.0,
            "gross_margin": 45.9,
        },
        "risks": [
            "Supply chain concentration",
            "Currency fluctuation",
        ],
        "disagreement": {
            "consensus_strength": "moderate",
            "conflict_points": [{"claim": "growth"}, {"claim": "margin"}],
        },
    }


def _new_run() -> dict:
    return {
        "quarter": "Q4_2025",
        "guidance": {
            "revenue": (92000, 96000),
            "eps": (5.1, 5.3),
        },
        "metrics": {
            "revenue": 94930.0,
            "net_income": 22956.0,
            "gross_margin": 46.2,
        },
        "risks": [
            "Supply chain concentration",
            "AI regulation uncertainty",
        ],
        "disagreement": {
            "consensus_strength": "divided",
            "conflict_points": [
                {"claim": "growth"},
                {"claim": "margin"},
                {"claim": "valuation"},
            ],
        },
    }


# ---------------------------------------------------------------------------
# LedgerEntry
# ---------------------------------------------------------------------------

class TestLedgerEntry:
    def test_creation(self):
        e = LedgerEntry(
            entry_id="AAPL_Q4_2025_guidance_001",
            ticker="AAPL",
            quarter="Q4_2025",
            category="guidance",
            before="revenue: 89,000–95,000",
            after="revenue: 92,000–96,000 (raised)",
            material=True,
            evidence_refs=["guidance:revenue"],
        )
        assert e.entry_id == "AAPL_Q4_2025_guidance_001"
        assert e.ticker == "AAPL"
        assert e.quarter == "Q4_2025"
        assert e.category == "guidance"
        assert e.material is True
        assert e.evidence_refs == ["guidance:revenue"]

    def test_to_dict(self):
        e = LedgerEntry(
            entry_id="id", ticker="X", quarter="Q1_2025", category="risk",
            before="—", after="Added risk: foo", material=True,
        )
        d = e.to_dict()
        assert d["entry_id"] == "id"
        assert d["category"] == "risk"
        assert d["material"] is True
        assert d["evidence_refs"] == []

    def test_evidence_refs_defaults_empty(self):
        e = LedgerEntry(
            entry_id="id", ticker="X", quarter="Q1_2025", category="risk",
            before="—", after="y", material=False,
        )
        assert e.evidence_refs == []


# ---------------------------------------------------------------------------
# ChangeLedger
# ---------------------------------------------------------------------------

class TestChangeLedger:
    def test_material_entries_and_count(self):
        entries = [
            LedgerEntry("a", "AAPL", "Q4_2025", "guidance", "x", "y", True),
            LedgerEntry("b", "AAPL", "Q4_2025", "fundamentals", "x", "y", False),
            LedgerEntry("c", "AAPL", "Q4_2025", "risk", "x", "y", True),
        ]
        ledger = ChangeLedger("AAPL", "Q3_2025", "Q4_2025", entries, "s")
        assert ledger.material_change_count == 2
        assert [e.entry_id for e in ledger.material_entries] == ["a", "c"]

    def test_by_category(self):
        entries = [
            LedgerEntry("a", "AAPL", "Q4", "guidance", "x", "y", True),
            LedgerEntry("b", "AAPL", "Q4", "risk", "x", "y", True),
            LedgerEntry("c", "AAPL", "Q4", "risk", "x", "y", True),
        ]
        ledger = ChangeLedger("AAPL", "Q3", "Q4", entries, "")
        assert ledger.by_category == {"guidance": 1, "risk": 2}

    def test_roundtrip_json(self):
        ledger = ChangeLedger(
            "AAPL", "Q3_2025", "Q4_2025",
            [LedgerEntry("a", "AAPL", "Q4_2025", "risk", "—", "x", True)],
            "1 changes",
        )
        data = json.loads(ledger.to_json())
        assert data["ticker"] == "AAPL"
        assert data["from_quarter"] == "Q3_2025"
        assert data["to_quarter"] == "Q4_2025"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["category"] == "risk"

    def test_to_markdown(self):
        ledger = ChangeLedger(
            "AAPL", "Q3_2025", "Q4_2025",
            [LedgerEntry("a", "AAPL", "Q4_2025", "risk", "—", "x", True)],
            "1 changes",
        )
        md = ledger.to_markdown()
        assert "# Change Ledger: AAPL" in md
        assert "risk" in md


# ---------------------------------------------------------------------------
# ChangeLedgerBuilder — diff methods
# ---------------------------------------------------------------------------

class TestDiffGuidance:
    def test_raised(self):
        entries = ChangeLedgerBuilder.diff_guidance(
            {"guidance": {"revenue": (89000, 95000)}},
            {"guidance": {"revenue": (92000, 96000)}},
        )
        assert len(entries) == 1
        assert entries[0].category == "guidance"
        assert entries[0].material is True
        assert "raised" in entries[0].after
        assert entries[0].evidence_refs == ["guidance:revenue"]

    def test_narrowed_not_material(self):
        entries = ChangeLedgerBuilder.diff_guidance(
            {"guidance": {"eps": (5.0, 5.4)}},
            {"guidance": {"eps": (5.1, 5.3)}},
        )
        assert len(entries) == 1
        assert "narrowed" in entries[0].after
        assert entries[0].material is False

    def test_new_and_withdrawn(self):
        entries = ChangeLedgerBuilder.diff_guidance(
            {"guidance": {"eps": (5.0, 6.0)}},
            {"guidance": {"fcf": (10000, 12000)}},
        )
        assert len(entries) == 2
        by_metric = {e.after.split(":")[0]: e for e in entries}
        assert "withdrawn" in by_metric["eps"].after
        assert "new" in by_metric["fcf"].after
        assert all(e.material for e in entries)


class TestDiffFundamentals:
    def test_material_change(self):
        entries = ChangeLedgerBuilder.diff_fundamentals(
            {"metrics": {"revenue": 100.0}},
            {"metrics": {"revenue": 110.0}},
        )
        assert len(entries) == 1
        assert entries[0].category == "fundamentals"
        assert entries[0].material is True
        assert "+10.0%" in entries[0].after

    def test_non_material_change(self):
        entries = ChangeLedgerBuilder.diff_fundamentals(
            {"metrics": {"revenue": 100.0}},
            {"metrics": {"revenue": 102.0}},
        )
        assert len(entries) == 1
        assert entries[0].material is False

    def test_unchanged_metric_skipped(self):
        entries = ChangeLedgerBuilder.diff_fundamentals(
            {"metrics": {"revenue": 100.0}},
            {"metrics": {"revenue": 100.0}},
        )
        assert entries == []

    def test_added_metric(self):
        entries = ChangeLedgerBuilder.diff_fundamentals(
            {"metrics": {}},
            {"metrics": {"net_income": 500.0}},
        )
        assert len(entries) == 1
        assert entries[0].before == "—"
        assert "(new)" in entries[0].after
        assert entries[0].material is True


class TestDiffRisks:
    def test_added_and_removed(self):
        entries = ChangeLedgerBuilder.diff_risks(
            {"risks": ["a", "b"]},
            {"risks": ["b", "c"]},
        )
        assert len(entries) == 2
        added = [e for e in entries if e.after.startswith("Added")]
        removed = [e for e in entries if e.before.startswith("Removed")]
        assert len(added) == 1
        assert len(removed) == 1
        assert "c" in added[0].after
        assert "a" in removed[0].before
        assert all(e.material for e in entries)

    def test_no_change(self):
        entries = ChangeLedgerBuilder.diff_risks(
            {"risks": ["a", "b"]},
            {"risks": ["a", "b"]},
        )
        assert entries == []

    def test_sections_risk_factors(self):
        entries = ChangeLedgerBuilder.diff_risks(
            {"sections": {"Risk Factors": "old risk text"}},
            {"sections": {"Risk Factors": "new risk text"}},
        )
        assert len(entries) == 2  # old removed, new added


class TestDiffDisagreement:
    def test_consensus_shift(self):
        entries = ChangeLedgerBuilder.diff_disagreement(
            {"disagreement": {"consensus_strength": "moderate"}},
            {"disagreement": {"consensus_strength": "divided"}},
        )
        assert len(entries) == 1
        assert entries[0].category == "disagreement"
        assert entries[0].material is True
        assert "moderate" in entries[0].before
        assert "divided" in entries[0].after

    def test_no_change(self):
        entries = ChangeLedgerBuilder.diff_disagreement(
            {"disagreement": {"consensus_strength": "moderate"}},
            {"disagreement": {"consensus_strength": "moderate"}},
        )
        assert entries == []

    def test_absent_both(self):
        assert ChangeLedgerBuilder.diff_disagreement({}, {}) == []


# ---------------------------------------------------------------------------
# ChangeLedgerBuilder — build
# ---------------------------------------------------------------------------

class TestChangeLedgerBuilderBuild:
    def test_build_full_ledger(self):
        ledger = ChangeLedgerBuilder.build(_prev_run(), _new_run(), "aapl")
        assert ledger.ticker == "AAPL"
        assert ledger.from_quarter == "Q3_2025"
        assert ledger.to_quarter == "Q4_2025"
        assert len(ledger.entries) > 0

        # Every entry is contextualized with ticker/quarter/entry_id.
        for e in ledger.entries:
            assert e.ticker == "AAPL"
            assert e.quarter == "Q4_2025"
            assert e.entry_id.startswith("AAPL_Q4_2025_")
            assert e.category in CATEGORIES

        assert "changes" in ledger.summary

    def test_build_same_quarter_summary_uses_run_dates(self):
        prev = {"date": "2026-09-10", "metrics": {"revenue": 100.0}}
        new = {"date": "2026-09-17", "metrics": {"revenue": 120.0}}
        ledger = ChangeLedgerBuilder.build(prev, new, "TEST")
        assert ledger.from_quarter == ledger.to_quarter == "Q3_2026"
        assert "between runs on 2026-09-10 and 2026-09-17 (both Q3_2026):" in ledger.summary

        empty = ChangeLedgerBuilder.build(prev, dict(prev, date="2026-09-17"), "TEST")
        assert empty.summary == "No changes detected for TEST between runs on 2026-09-10 and 2026-09-17 (both Q3_2026)."

    def test_build_different_quarters_summary_uses_quarters(self):
        prev = {"date": "2026-06-10", "metrics": {"revenue": 100.0}}
        new = {"date": "2026-09-17", "metrics": {"revenue": 120.0}}
        assert "between Q2_2026 and Q3_2026:" in ChangeLedgerBuilder.build(prev, new, "TEST").summary

    def test_build_quarter_inferred_from_filing_date(self):
        prev = {"filing_date": "2025-08-01", "metrics": {"revenue": 100.0}}
        new = {"filing_date": "2025-11-01", "metrics": {"revenue": 120.0}}
        ledger = ChangeLedgerBuilder.build(prev, new, "TEST")
        assert ledger.from_quarter == "Q3_2025"
        assert ledger.to_quarter == "Q4_2025"

    def test_build_empty_runs(self):
        ledger = ChangeLedgerBuilder.build({}, {}, "TEST")
        assert ledger.ticker == "TEST"
        assert ledger.entries == []
        assert ledger.from_quarter == ""
        assert ledger.to_quarter == ""


# ---------------------------------------------------------------------------
# filing_delta integration
# ---------------------------------------------------------------------------

class TestFilingDeltaIntegration:
    def test_filing_delta_build_attaches_ledger(self):
        new_filing = {
            "filing_date": "2025-11-01",
            "filing_type": "10-Q",
            "metrics": {"revenue": 94930.0},
            "guidance": {"revenue_guidance": (92000, 96000)},
            "risks": ["new risk"],
        }
        prev_filing = {
            "filing_date": "2025-08-01",
            "filing_type": "10-Q",
            "metrics": {"revenue": 89498.0},
            "guidance": {"revenue_guidance": (89000, 95000)},
            "risks": ["old risk"],
        }
        report = FilingDeltaBuilder("AAPL", "n", "p").build(new_filing, prev_filing)
        assert report.ledger is not None
        assert report.ledger.ticker == "AAPL"
        assert report.ledger.from_quarter == "Q3_2025"
        assert report.ledger.to_quarter == "Q4_2025"
        assert len(report.ledger.entries) > 0

        # Serialized output includes the ledger.
        data = report.to_dict()
        assert data["ledger"] is not None
        assert data["ledger"]["ticker"] == "AAPL"
