# -*- coding: utf-8 -*-
"""Tests for Citation Correction Queue (A04)."""
import tempfile
from pathlib import Path
import pytest
from augur.citation_queue import (
    CitationCorrection, CitationCorpus, CitationCorrectionQueue,
)


class TestCitationCorrection:
    def test_creation(self):
        cc = CitationCorrection(
            correction_id="cc_001", claim_id="cl_001", ticker="AAPL",
            issue_type="wrong_source", incorrect_refs=["ev_001"],
            correct_refs=["ev_002"], status="open",
        )
        assert cc.issue_type == "wrong_source"
        assert cc.status == "open"


class TestCitationCorpus:
    def test_counts(self):
        corpus = CitationCorpus(
            corrections=[],
            total_reported=10, total_accepted=6, total_fixed=4,
        )
        assert corpus.total_accepted == 6


class TestCitationCorrectionQueue:
    def test_report(self):
        q = CitationCorrectionQueue(storage_path=Path(tempfile.mktemp(suffix=".json")))
        cc = q.report("cl_001", "AAPL", "wrong_source", ["ev_bad"], ["ev_good"], "Wrong filing cited")
        assert cc.status == "open"
        assert cc.ticker == "AAPL"

    def test_accept(self):
        q = CitationCorrectionQueue(storage_path=Path(tempfile.mktemp(suffix=".json")))
        cc = q.report("cl_002", "MSFT", "fabricated", ["ev_fake"], ["ev_real"], "")
        updated = q.accept(cc.correction_id)
        assert updated.status == "accepted"

    def test_reject(self):
        q = CitationCorrectionQueue(storage_path=Path(tempfile.mktemp(suffix=".json")))
        cc = q.report("cl_003", "TSLA", "outdated", [], [], "")
        q.reject(cc.correction_id, "Not a real error")
        updated = q.list_open()
        assert len(updated) == 0

    def test_mark_fixed(self):
        q = CitationCorrectionQueue(storage_path=Path(tempfile.mktemp(suffix=".json")))
        cc = q.report("cl_004", "GOOG", "misattributed", [], [], "")
        q.accept(cc.correction_id)
        q.mark_fixed(cc.correction_id)
        corpus = q.get_corpus()
        assert corpus.total_fixed == 1

    def test_list_open(self):
        q = CitationCorrectionQueue(storage_path=Path(tempfile.mktemp(suffix=".json")))
        q.report("c1", "AAPL", "wrong_source", [], [], "")
        q.report("c2", "MSFT", "fabricated", [], [], "")
        assert len(q.list_open()) == 2

    def test_list_accepted(self):
        q = CitationCorrectionQueue(storage_path=Path(tempfile.mktemp(suffix=".json")))
        cc = q.report("c5", "AAPL", "wrong_source", [], [], "")
        q.accept(cc.correction_id)
        assert len(q.list_accepted()) == 1

    def test_get_regression_cases(self):
        q = CitationCorrectionQueue(storage_path=Path(tempfile.mktemp(suffix=".json")))
        cc = q.report("cl_x", "TST", "fabricated", ["ev_1"], ["ev_2"], "")
        q.accept(cc.correction_id)
        cases = q.get_regression_cases()
        assert len(cases) == 1
        assert cases[0]["claim_id"] == "cl_x"

    def test_persistence(self):
        path = Path(tempfile.mktemp(suffix=".json"))
        q1 = CitationCorrectionQueue(storage_path=path)
        q1.report("cl_p", "AAPL", "wrong_source", [], [], "test persist")
        q2 = CitationCorrectionQueue(storage_path=path)
        assert len(q2.list_open()) == 1
