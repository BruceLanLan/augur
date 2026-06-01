# -*- coding: utf-8 -*-
"""
augur.sentiment - Social Sentiment Analysis

Provides mock sentiment data for social platforms (X, Reddit, StockTwits).
Uses ticker hash for deterministic but realistic random scores.

Architecture:
    - SentimentAnalyzer: Main class that generates per-ticker sentiment scores
    - SentimentResult: Dataclass holding overall score, per-source scores, volume
    - Hash-based determinism: same ticker always produces same scores (testable)

Score Ranges:
    - overall_score: [-1.0, +1.0] (aggregated weighted sentiment)
    - per-source scores: [-1.0, +1.0] for X, Reddit, StockTwits
    - sentiment_factor: [-0.5, +0.5] (used as consensus score adjustment)
    - Source weights: X=40%, Reddit=35%, StockTwits=25%

Integration:
    - get_sentiment_factor() returns a value added to consensus score in registry.py
    - Score is clamped to [0, 10] after sentiment adjustment (review fix #3)

Usage:
    sa = SentimentAnalyzer()
    result = sa.get_sentiment("NVDA")
    factor = sa.get_sentiment_factor("NVDA")  # [-0.5, 0.5]
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SentimentResult:
    """Result of sentiment analysis for a ticker."""
    ticker: str
    overall_score: float  # -1.0 to 1.0
    sources: Dict[str, float] = field(default_factory=dict)  # x_score, reddit_score, stocktwits_score
    volume: int = 0  # Number of mentions
    trending: bool = False  # Whether the ticker is trending


class SentimentAnalyzer:
    """Analyzes social sentiment for tickers using mock data.

    Generates deterministic mock scores seeded by ticker hash to simulate
    real social sentiment from X (Twitter), Reddit, and StockTwits.
    Results are cached with a 60-second TTL for performance.
    """

    def __init__(self):
        self._cache: Dict[str, SentimentResult] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl: float = 60.0  # seconds

    def _hash_seed(self, ticker: str, salt: str = "") -> float:
        """Generate a deterministic float from ticker hash."""
        h = hashlib.sha256(f"{ticker.upper()}{salt}".encode()).hexdigest()
        # Convert first 8 hex chars to a float in [0, 1)
        return int(h[:8], 16) / 0xFFFFFFFF

    def _score_from_seed(self, seed: float) -> float:
        """Convert a [0, 1) seed to a score in [-1, 1]."""
        return round((seed * 2) - 1, 4)

    def get_sentiment(self, ticker: str) -> SentimentResult:
        """Get sentiment for a ticker. Uses mock data seeded by ticker hash.

        Results are cached with a 60-second TTL for performance.

        Args:
            ticker: Stock ticker symbol (e.g. 'AAPL', 'NVDA')

        Returns:
            SentimentResult with overall score, per-source scores, volume, trending.
        """
        ticker = ticker.upper().strip()

        # Check cache with TTL
        import time as _time
        now = _time.time()
        if ticker in self._cache:
            cache_time = self._cache_timestamps.get(ticker, 0)
            if (now - cache_time) < self._cache_ttl:
                return self._cache[ticker]

        # Generate deterministic but varied scores
        x_seed = self._hash_seed(ticker, "x_twitter")
        reddit_seed = self._hash_seed(ticker, "reddit")
        stocktwits_seed = self._hash_seed(ticker, "stocktwits")

        x_score = self._score_from_seed(x_seed)
        reddit_score = self._score_from_seed(reddit_seed)
        stocktwits_score = self._score_from_seed(stocktwits_seed)

        # Overall is weighted average
        overall_score = round(
            x_score * 0.4 + reddit_score * 0.35 + stocktwits_score * 0.25,
            4
        )

        # Volume based on hash
        vol_seed = self._hash_seed(ticker, "volume")
        volume = int(vol_seed * 50000) + 100

        # Trending if volume > 30000 or overall_score > 0.5
        trending = volume > 30000 or abs(overall_score) > 0.5

        result = SentimentResult(
            ticker=ticker,
            overall_score=overall_score,
            sources={
                "x_score": x_score,
                "reddit_score": reddit_score,
                "stocktwits_score": stocktwits_score,
            },
            volume=volume,
            trending=trending,
        )

        self._cache[ticker] = result
        self._cache_timestamps[ticker] = now
        return result

    def get_sentiment_factor(self, ticker: str) -> float:
        """Get a sentiment adjustment factor for use by DecisionCoordinator.

        Returns a value in [-0.5, 0.5] that can be added to consensus scores.
        """
        result = self.get_sentiment(ticker)
        # Scale overall_score to a smaller adjustment factor
        return round(result.overall_score * 0.5, 4)

    def clear_cache(self) -> None:
        """Clear the internal sentiment cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
