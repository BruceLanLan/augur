# -*- coding: utf-8 -*-
"""Tests for augur.sentiment - Social Sentiment Analysis"""

import pytest
from augur.sentiment import SentimentAnalyzer, SentimentResult


class TestSentimentAnalyzer:
    def test_get_sentiment_returns_result(self):
        """get_sentiment returns a SentimentResult."""
        analyzer = SentimentAnalyzer()
        result = analyzer.get_sentiment("AAPL")
        assert isinstance(result, SentimentResult)
        assert result.ticker == "AAPL"

    def test_sentiment_score_range(self):
        """Scores are in [-1, 1] range."""
        analyzer = SentimentAnalyzer()
        result = analyzer.get_sentiment("NVDA")
        assert -1.0 <= result.overall_score <= 1.0
        for key, score in result.sources.items():
            assert -1.0 <= score <= 1.0

    def test_sentiment_sources_present(self):
        """All three source scores are present."""
        analyzer = SentimentAnalyzer()
        result = analyzer.get_sentiment("MSFT")
        assert "x_score" in result.sources
        assert "reddit_score" in result.sources
        assert "stocktwits_score" in result.sources

    def test_sentiment_volume_positive(self):
        """Volume is always a positive integer."""
        analyzer = SentimentAnalyzer()
        result = analyzer.get_sentiment("TSLA")
        assert isinstance(result.volume, int)
        assert result.volume > 0

    def test_sentiment_deterministic(self):
        """Same ticker always produces same scores (seeded by hash)."""
        a1 = SentimentAnalyzer()
        a2 = SentimentAnalyzer()
        r1 = a1.get_sentiment("GOOGL")
        r2 = a2.get_sentiment("GOOGL")
        assert r1.overall_score == r2.overall_score
        assert r1.sources == r2.sources
        assert r1.volume == r2.volume

    def test_different_tickers_different_scores(self):
        """Different tickers produce different scores."""
        analyzer = SentimentAnalyzer()
        r1 = analyzer.get_sentiment("AAPL")
        r2 = analyzer.get_sentiment("NVDA")
        # Extremely unlikely to be identical
        assert r1.overall_score != r2.overall_score or r1.sources != r2.sources

    def test_get_sentiment_factor(self):
        """get_sentiment_factor returns value in [-0.5, 0.5]."""
        analyzer = SentimentAnalyzer()
        factor = analyzer.get_sentiment_factor("AAPL")
        assert -0.5 <= factor <= 0.5

    def test_ticker_case_insensitive(self):
        """Ticker is normalized to uppercase."""
        analyzer = SentimentAnalyzer()
        r1 = analyzer.get_sentiment("aapl")
        r2 = analyzer.get_sentiment("AAPL")
        assert r1.ticker == "AAPL"
        assert r1.overall_score == r2.overall_score

    def test_trending_flag(self):
        """Trending is a boolean."""
        analyzer = SentimentAnalyzer()
        result = analyzer.get_sentiment("META")
        assert isinstance(result.trending, bool)

    def test_cache_works(self):
        """Cache returns same object for same ticker."""
        analyzer = SentimentAnalyzer()
        r1 = analyzer.get_sentiment("AMD")
        r2 = analyzer.get_sentiment("AMD")
        assert r1 is r2

    def test_clear_cache(self):
        """clear_cache resets internal state."""
        analyzer = SentimentAnalyzer()
        analyzer.get_sentiment("AAPL")
        analyzer.clear_cache()
        assert "AAPL" not in analyzer._cache

    def test_empty_ticker_returns_neutral(self):
        """Empty ticker should not hit external APIs or crash."""
        analyzer = SentimentAnalyzer()
        result = analyzer.get_sentiment("  ")
        assert result.ticker == ""
        assert result.overall_score == 0.0
        assert result.volume == 0

    def test_whitespace_ticker_normalized(self):
        """Leading/trailing whitespace is stripped before lookup."""
        analyzer = SentimentAnalyzer()
        result = analyzer.get_sentiment("  nvda  ")
        assert result.ticker == "NVDA"
        assert -1.0 <= result.overall_score <= 1.0
