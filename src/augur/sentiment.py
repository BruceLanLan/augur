# -*- coding: utf-8 -*-
"""
augur.sentiment - Social Sentiment Analysis

Fetches real sentiment from StockTwits (no auth) and optionally Reddit (PRAW).
Falls back to hash-based mock when network unavailable or rate-limited.

Sources and weights:
    StockTwits  50%  — free, no auth, bullish/bearish tags per message
    Reddit      30%  — optional, needs REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET env vars
    X (Twitter) 20%  — hash mock (X API free tier too restrictive for real use)

Score ranges:
    overall_score: [-1.0, +1.0]
    sentiment_factor: [-0.5, +0.5] added to consensus score in registry.py

Cache TTL: 5 minutes (real API); 60 seconds (mock fallback)

Environment variables (optional):
    REDDIT_CLIENT_ID      — Reddit app client ID
    REDDIT_CLIENT_SECRET  — Reddit app client secret
    REDDIT_USER_AGENT     — defaults to "augur-sentiment/8.0"
"""

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class SentimentResult:
    ticker: str
    overall_score: float          # -1.0 to 1.0
    sources: Dict[str, float] = field(default_factory=dict)
    volume: int = 0
    trending: bool = False
    data_source: str = "mock"     # "live" | "partial" | "mock"


# ── StockTwits ────────────────────────────────────────────────────────────────

def _fetch_stocktwits(ticker: str) -> Tuple[float, int]:
    """
    Fetch StockTwits stream for ticker. No authentication required.
    Returns (score [-1,1], message_count).
    StockTwits messages optionally include a 'sentiment' tag: Bullish or Bearish.
    """
    try:
        import urllib.request
        import json as _json

        sym = ticker.replace("-", ".")          # StockTwits uses dots for crypto pairs
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{sym}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "augur-sentiment/8.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read())

        messages = data.get("messages", [])
        if not messages:
            return 0.0, 0

        bullish = sum(
            1 for m in messages
            if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish"
        )
        bearish = sum(
            1 for m in messages
            if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish"
        )
        total = bullish + bearish
        if total == 0:
            return 0.0, len(messages)

        score = (bullish - bearish) / total   # -1 to +1
        return round(score, 4), len(messages)

    except Exception:
        return None, 0     # None signals fetch failure → fall back to mock


# ── Reddit (optional) ─────────────────────────────────────────────────────────

def _fetch_reddit(ticker: str) -> Optional[float]:
    """
    Fetch Reddit sentiment from r/stocks and r/wallstreetbets.
    Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars.
    Returns score [-1,1] or None if unavailable.
    """
    client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    try:
        import praw  # type: ignore
        user_agent = os.environ.get("REDDIT_USER_AGENT", "augur-sentiment/8.0")
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        positive_words = {"bull", "bullish", "buy", "long", "moon", "up", "gain",
                          "strong", "growth", "beat", "upgrade", "outperform"}
        negative_words = {"bear", "bearish", "sell", "short", "crash", "down", "loss",
                          "weak", "miss", "downgrade", "underperform", "dump"}

        pos = neg = 0
        for sub in ("stocks", "wallstreetbets", "investing"):
            try:
                for post in reddit.subreddit(sub).search(ticker, limit=20, time_filter="week"):
                    text = (post.title + " " + (post.selftext or "")).lower()
                    words = set(text.split())
                    pos += len(words & positive_words)
                    neg += len(words & negative_words)
            except Exception:
                continue

        total = pos + neg
        if total == 0:
            return 0.0
        return round((pos - neg) / total, 4)

    except ImportError:
        return None
    except Exception:
        return None


# ── Hash-based mock (deterministic fallback) ──────────────────────────────────

def _mock_score(ticker: str, salt: str) -> float:
    h = hashlib.sha256(f"{ticker.upper()}{salt}".encode()).hexdigest()
    seed = int(h[:8], 16) / 0xFFFFFFFF
    return round((seed * 2) - 1, 4)


# ── Main Analyzer ─────────────────────────────────────────────────────────────

class SentimentAnalyzer:
    """
    Fetches real social sentiment and caches results.

    Real API calls: StockTwits (always attempted), Reddit (if env vars set).
    Falls back to deterministic hash mock on network failure.
    """

    REAL_CACHE_TTL = 300.0   # 5 min for live data
    MOCK_CACHE_TTL = 60.0    # 1 min for mock data

    def __init__(self):
        self._cache: Dict[str, SentimentResult] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_source: Dict[str, str] = {}

    def _is_cached(self, ticker: str) -> bool:
        if ticker not in self._cache:
            return False
        src = self._cache_source.get(ticker, "mock")
        ttl = self.REAL_CACHE_TTL if src == "live" else self.MOCK_CACHE_TTL
        return (time.time() - self._cache_timestamps.get(ticker, 0)) < ttl

    def get_sentiment(self, ticker: str) -> SentimentResult:
        # Input validation: only accept string tickers, normalise, and reject
        # anything containing whitespace, non-printable chars, or excessive
        # length (which would break the StockTwits URL or pollute the cache).
        if not isinstance(ticker, str) or not ticker.strip():
            return SentimentResult(
                ticker="",
                overall_score=0.0,
                sources={"stocktwits_score": 0.0, "reddit_score": 0.0, "x_score": 0.0},
                volume=0,
                trending=False,
                data_source="mock",
            )
        ticker = ticker.strip().upper()
        if any(ch.isspace() for ch in ticker) or len(ticker) > 12 or not ticker.isprintable():
            return SentimentResult(
                ticker="",
                overall_score=0.0,
                sources={"stocktwits_score": 0.0, "reddit_score": 0.0, "x_score": 0.0},
                volume=0,
                trending=False,
                data_source="mock",
            )
        if self._is_cached(ticker):
            return self._cache[ticker]

        st_score, st_volume = _fetch_stocktwits(ticker)
        reddit_score = _fetch_reddit(ticker)
        x_score_mock = _mock_score(ticker, "x_twitter")   # X stays mock

        live_sources = {}
        data_source = "mock"

        if st_score is not None:
            live_sources["stocktwits_score"] = st_score
            data_source = "partial"
        else:
            live_sources["stocktwits_score"] = _mock_score(ticker, "stocktwits")

        if reddit_score is not None:
            live_sources["reddit_score"] = reddit_score
            if data_source == "partial":
                data_source = "live"
        else:
            live_sources["reddit_score"] = _mock_score(ticker, "reddit")

        live_sources["x_score"] = x_score_mock

        # Weighted average: StockTwits 50%, Reddit 30%, X 20%
        overall = round(
            live_sources["stocktwits_score"] * 0.50
            + live_sources["reddit_score"] * 0.30
            + live_sources["x_score"] * 0.20,
            4,
        )

        volume = st_volume if st_volume > 0 else (
            int(abs(int(hashlib.sha256(ticker.encode()).hexdigest()[:8], 16) % 40000) + 100)
        )
        trending = volume > 15000 or abs(overall) > 0.4

        result = SentimentResult(
            ticker=ticker,
            overall_score=overall,
            sources=live_sources,
            volume=volume,
            trending=trending,
            data_source=data_source,
        )

        self._cache[ticker] = result
        self._cache_timestamps[ticker] = time.time()
        self._cache_source[ticker] = data_source
        return result

    def get_sentiment_factor(self, ticker: str) -> float:
        """Return a score adjustment in [-0.5, +0.5] for use in consensus."""
        return round(self.get_sentiment(ticker).overall_score * 0.5, 4)

    def clear_cache(self) -> None:
        self._cache.clear()
        self._cache_timestamps.clear()
        self._cache_source.clear()
