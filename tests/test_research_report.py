# -*- coding: utf-8 -*-
"""Tests for comprehensive research report aggregator."""
import json
import pytest
from augur.research_report import ResearchReport, ResearchReportBuilder


class TestResearchReport:
    def test_empty_report(self):
        r = ResearchReport(ticker="AAPL")
        assert r.ticker == "AAPL"
        assert r.consensus == {}

    def test_to_markdown_empty(self):
        r = ResearchReport(ticker="AAPL")
        md = r.to_markdown()
        assert "# Research Report: AAPL" in md

    def test_to_markdown_full(self):
        r = ResearchReport(
            ticker="AAPL", consensus={"signal": "bullish"},
            disagreement={"consensus_strength": "divided"},
            change_ledger={"entries": [{"category": "risk", "before": "a", "after": "b"}]},
            thesis_deltas=[{"overall_assessment": "weakened"}],
            scorecard={"accuracy": 0.66},
            open_questions=[{"question": "q1"}],
            provenance={"data_source": "live"},
        )
        md = r.to_markdown()
        assert "Consensus" in md
        assert "Disagreement Map" in md
        assert "Change Ledger" in md
        assert "Thesis Updates" in md
        assert "Scorecard" in md
        assert "Open Questions" in md
        assert "Provenance" in md

    def test_to_json(self):
        r = ResearchReport(ticker="MSFT", consensus={"score": 8.0})
        js = r.to_json()
        data = json.loads(js)
        assert data["ticker"] == "MSFT"
        assert data["consensus"]["score"] == 8.0


class TestResearchReportBuilder:
    def test_build_basic(self):
        b = ResearchReportBuilder()
        r = b.build("AAPL")
        assert r.ticker == "AAPL"
        assert r.generated_at  # timestamp auto-generated

    def test_build_full(self):
        b = ResearchReportBuilder()
        r = b.build(
            "AAPL", run_id="run_001",
            consensus={"signal": "bullish"},
            disagreement={"conflict_points": []},
            thesis_deltas=[{"overall_assessment": "intact"}],
            change_ledger={"entries": []},
            scorecard={"accuracy": 0.5},
            provenance={"source": "test"},
            open_questions=[{"question": "q"}],
        )
        assert r.run_id == "run_001"
        assert len(r.thesis_deltas) == 1
        assert r.provenance["source"] == "test"
