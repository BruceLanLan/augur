# -*- coding: utf-8 -*-
"""Tests for Post-earnings Scorecard (B03) and Management Language Diff (B06)."""

import pytest

from augur.scorecard import (
    LanguageChange,
    LanguageDiffAnalyzer,
    LanguageDiffReport,
    PostEarningsScorecard,
    ScorecardBuilder,
    ScorecardItem,
)


# ============================================================================
# B03 — Post-earnings Scorecard
# ============================================================================

class TestScorecardItem:
    """Unit tests for ScorecardItem dataclass."""

    def test_create_item_confirmed(self):
        item = ScorecardItem(
            question="Will revenue beat estimates?",
            pre_event_answer="Yes, revenue beat by 4%",
            actual_outcome="Revenue beat by 4.2%",
            verdict="confirmed",
            evidence_refs=["ev-001", "ev-002"],
        )
        assert item.question == "Will revenue beat estimates?"
        assert item.pre_event_answer == "Yes, revenue beat by 4%"
        assert item.verdict == "confirmed"
        assert item.evidence_refs == ["ev-001", "ev-002"]

    def test_create_item_refuted(self):
        item = ScorecardItem(
            question="Will EPS exceed $1.50?",
            pre_event_answer="Predicted EPS $1.65",
            actual_outcome="Actual EPS $1.32",
            verdict="refuted",
        )
        assert item.verdict == "refuted"
        assert item.evidence_refs == []

    def test_create_item_partially_correct(self):
        item = ScorecardItem(
            question="Revenue growth direction",
            pre_event_answer="Growth positive",
            actual_outcome="Revenue grew but below trend",
            verdict="partially_correct",
        )
        assert item.verdict == "partially_correct"

    def test_default_evidence_refs(self):
        item = ScorecardItem(
            question="Q",
            pre_event_answer="A",
            actual_outcome="A",
            verdict="confirmed",
        )
        assert item.evidence_refs == []


class TestPostEarningsScorecard:
    """Unit tests for PostEarningsScorecard dataclass."""

    def test_empty_scorecard(self):
        sc = PostEarningsScorecard(
            ticker="AAPL",
            event_id="evt-2025-q4",
            pre_event_run_id="run-pre-001",
            post_event_run_id="run-post-001",
        )
        assert sc.ticker == "AAPL"
        assert sc.items == []
        assert sc.accuracy == 0.0
        assert sc.summary == ""

    def test_full_scorecard(self):
        items = [
            ScorecardItem(
                question="Revenue beat?",
                pre_event_answer="Yes",
                actual_outcome="Yes",
                verdict="confirmed",
            ),
            ScorecardItem(
                question="EPS beat?",
                pre_event_answer="No",
                actual_outcome="Yes",
                verdict="refuted",
            ),
        ]
        sc = PostEarningsScorecard(
            ticker="MSFT",
            event_id="evt-001",
            pre_event_run_id="pre-001",
            post_event_run_id="post-001",
            items=items,
            accuracy=0.5,
            summary="50% accuracy",
        )
        assert sc.accuracy == 0.5
        assert len(sc.items) == 2


class TestScorecardBuilder:
    """Tests for ScorecardBuilder.build()."""

    @pytest.fixture
    def pre_run(self):
        return {
            "run_id": "run-pre-001",
            "ticker": "AAPL",
            "manifest": {"event_id": "evt-2025-q4"},
            "step_results": [
                {"step_name": "Will revenue beat?",
                 "content": "Revenue beat by 4%"},
                {"step_name": "Will EPS exceed $1.50?",
                 "content": "Predicted EPS $1.55"},
                {"step_name": "margin direction?",
                 "content": "Margins will expand"},
            ],
            "evidence": [
                {"evidence_id": "ev-001"},
                {"evidence_id": "ev-002"},
            ],
        }

    @pytest.fixture
    def post_run(self):
        return {
            "run_id": "run-post-001",
            "ticker": "AAPL",
            "step_results": [
                {"step_name": "Will revenue beat?",
                 "content": "Revenue beat by 4.2%"},
                {"step_name": "Will EPS exceed $1.50?",
                 "content": "EPS came in at $1.32"},
                {"step_name": "margin direction?",
                 "content": "Margins contracted slightly"},
            ],
        }

    @pytest.fixture
    def questions(self):
        return [
            "Will revenue beat?",
            "Will EPS exceed $1.50?",
            "margin direction?",
        ]

    def test_build_returns_scorecard(self, pre_run, post_run, questions):
        builder = ScorecardBuilder()
        result = builder.build(pre_run, post_run, questions)
        assert isinstance(result, PostEarningsScorecard)
        assert result.ticker == "AAPL"

    def test_build_pre_post_run_ids(self, pre_run, post_run, questions):
        builder = ScorecardBuilder()
        result = builder.build(pre_run, post_run, questions)
        assert result.pre_event_run_id == "run-pre-001"
        assert result.post_event_run_id == "run-post-001"

    def test_build_accuracy_calculation(self, pre_run, post_run, questions):
        builder = ScorecardBuilder()
        result = builder.build(pre_run, post_run, questions)
        assert 0.0 <= result.accuracy <= 1.0
        assert abs(result.accuracy - 1.0/3.0) < 0.01  # only exact "Revenue beat" matches

    def test_build_summary_includes_accuracy(self, pre_run, post_run, questions):
        builder = ScorecardBuilder()
        result = builder.build(pre_run, post_run, questions)
        assert "Accuracy" in result.summary
        assert "33" in result.summary or "0.33" in result.summary.replace("%", " %")

    def test_build_all_items_have_verdict(self, pre_run, post_run, questions):
        builder = ScorecardBuilder()
        result = builder.build(pre_run, post_run, questions)
        valid_verdicts = {"confirmed", "refuted", "partially_correct", "unknown"}
        for item in result.items:
            assert item.verdict in valid_verdicts

    def test_build_empty_questions(self, pre_run, post_run):
        builder = ScorecardBuilder()
        result = builder.build(pre_run, post_run, [])
        assert result.items == []
        assert result.accuracy == 0.0

    def test_build_empty_runs(self):
        builder = ScorecardBuilder()
        result = builder.build({}, {}, ["What is revenue?"])
        assert result.ticker == "UNKNOWN"
        assert len(result.items) == 1
        assert result.items[0].verdict == "unknown"

    def test_build_resolves_ticker_from_post_run(self):
        builder = ScorecardBuilder()
        result = builder.build(
            {}, {"ticker": "MSFT"}, ["Q"]
        )
        assert result.ticker == "MSFT"

    def test_build_numeric_confirmation(self):
        """Pre and post answers that parse to numbers within 5% → confirmed."""
        pre = {"run_id": "r1", "ticker": "TSLA", "step_results": [
            {"step_name": "revenue", "content": "100"},
        ]}
        post = {"run_id": "r2", "step_results": [
            {"step_name": "revenue", "content": "102"},
        ]}
        builder = ScorecardBuilder()
        result = builder.build(pre, post, ["revenue"])
        assert result.items[0].verdict == "confirmed"

    def test_build_numeric_refuted(self):
        """Pre and post answers that parse to numbers far apart → refuted."""
        pre = {"run_id": "r1", "ticker": "TSLA", "step_results": [
            {"step_name": "revenue", "content": "100"},
        ]}
        post = {"run_id": "r2", "step_results": [
            {"step_name": "revenue", "content": "200"},
        ]}
        builder = ScorecardBuilder()
        result = builder.build(pre, post, ["revenue"])
        assert result.items[0].verdict == "refuted"


# ============================================================================
# B06 — Management Language Diff
# ============================================================================

class TestLanguageChange:
    """Unit tests for LanguageChange dataclass."""

    def test_create_language_change(self):
        lc = LanguageChange(
            section="MD&A",
            phrase_before="We expect strong growth",
            phrase_after="We anticipate modest growth",
            sentiment_shift="more_cautious",
            material=True,
        )
        assert lc.section == "MD&A"
        assert lc.phrase_before == "We expect strong growth"
        assert lc.sentiment_shift == "more_cautious"
        assert lc.material is True


class TestLanguageDiffReport:
    """Unit tests for LanguageDiffReport dataclass."""

    def test_empty_report(self):
        rpt = LanguageDiffReport(ticker="AAPL")
        assert rpt.ticker == "AAPL"
        assert rpt.changes == []
        assert rpt.overall_sentiment_shift == "neutral"


class TestLanguageDiffAnalyzer:
    """Tests for LanguageDiffAnalyzer.analyze() and detect_sentiment_words()."""

    @pytest.fixture
    def analyzer(self):
        return LanguageDiffAnalyzer()

    @pytest.fixture
    def prev_filing(self):
        return {
            "ticker": "AAPL",
            "sections": {
                "MD&A": (
                    "Revenue increased 15% year-over-year driven by strong demand. "
                    "We expect growth to continue into the next quarter. "
                    "The outlook remains positive."
                ),
                "Risk Factors": (
                    "Competition remains a challenge. Supply chain disruption could "
                    "impact production."
                ),
            },
        }

    @pytest.fixture
    def new_filing(self):
        return {
            "ticker": "AAPL",
            "sections": {
                "MD&A": (
                    "Revenue increased 5% year-over-year reflecting market headwinds. "
                    "We anticipate a slowdown in growth given softening demand. "
                    "The outlook remains cautious."
                ),
                "Risk Factors": (
                    "Competition remains a challenge. Supply chain disruption could "
                    "impact production. Macroeconomic uncertainty adds additional risk."
                ),
            },
        }

    # --- detect_sentiment_words ---

    def test_detect_bullish_words(self, analyzer):
        text = "We achieved record revenue and strong growth with confident outlook."
        counts = analyzer.detect_sentiment_words(text)
        assert counts["bullish"] > 0
        assert counts["bullish"] >= 3  # achieved, record, strong, growth, confident

    def test_detect_bearish_words(self, analyzer):
        text = "Declining demand and weaker pricing pressure create headwinds."
        counts = analyzer.detect_sentiment_words(text)
        assert counts["bearish"] > 0

    def test_detect_cautious_words(self, analyzer):
        text = "We believe the market may stabilize although uncertainty remains."
        counts = analyzer.detect_sentiment_words(text)
        assert counts["cautious"] > 0

    def test_detect_empty_text(self, analyzer):
        counts = analyzer.detect_sentiment_words("")
        assert counts == {"bullish": 0, "bearish": 0, "cautious": 0}

    # --- analyze ---

    def test_analyze_returns_report(self, analyzer, prev_filing, new_filing):
        result = analyzer.analyze(prev_filing, new_filing)
        assert isinstance(result, LanguageDiffReport)
        assert result.ticker == "AAPL"

    def test_analyze_detects_changes(self, analyzer, prev_filing, new_filing):
        result = analyzer.analyze(prev_filing, new_filing)
        assert len(result.changes) > 0  # should find at least one change

    def test_analyze_overall_sentiment_set(self, analyzer, prev_filing, new_filing):
        result = analyzer.analyze(prev_filing, new_filing)
        valid_shifts = {"more_bullish", "more_bearish", "more_cautious", "neutral"}
        assert result.overall_sentiment_shift in valid_shifts

    def test_analyze_empty_filings(self, analyzer):
        result = analyzer.analyze({}, {})
        assert result.ticker == "UNKNOWN"
        assert result.changes == []
        assert result.overall_sentiment_shift == "neutral"

    def test_analyze_no_changes_when_identical(self, analyzer):
        filing = {
            "ticker": "TSLA",
            "sections": {
                "MD&A": "Strong demand for our products continues.",
            },
        }
        result = analyzer.analyze(filing, filing)
        assert result.ticker == "TSLA"
        # Identical filings should produce zero meaningful changes
        # (exact same sentences produce no additions or removals)
        assert len(result.changes) == 0

    def test_analyze_detects_added_section(self, analyzer):
        prev = {"ticker": "IBM"}
        new = {
            "ticker": "IBM",
            "sections": {
                "Risk Factors": (
                    "New regulatory requirements pose substantial compliance risk. "
                    "Failure to adapt may materially impact operations and revenue."
                ),
            },
        }
        result = analyzer.analyze(prev, new)
        assert len(result.changes) > 0

    def test_analyze_material_flag_set(self, analyzer, prev_filing, new_filing):
        result = analyzer.analyze(prev_filing, new_filing)
        # At least one change should have material set
        any_material = any(c.material for c in result.changes)
        assert any_material, (
            "Expected at least one material change in the diff"
        )
