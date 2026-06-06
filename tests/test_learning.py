# -*- coding: utf-8 -*-
"""Tests for augur.learning - Agent Learning Engine"""

import json
import logging
import math
import time
from unittest.mock import patch

import pytest
from pathlib import Path

from augur.learning import LearningEngine


@pytest.fixture
def learning_engine(tmp_path):
    """Create a LearningEngine with temporary storage."""
    weights_path = tmp_path / "test_weights.json"
    return LearningEngine(weights_path=weights_path)


def test_learning_engine_init(learning_engine):
    """Test LearningEngine initialization."""
    assert learning_engine.has_learned_weights is False
    assert learning_engine.prediction_count == 0
    assert learning_engine.get_weights() == {}


def test_record_prediction(learning_engine):
    """Test recording predictions."""
    learning_engine.record_prediction(
        ticker="AAPL",
        agent_id="buffett",
        signal="bullish",
        score=7.5,
        confidence=0.8,
    )
    assert learning_engine.prediction_count == 1


def test_record_outcome_updates_accuracy(learning_engine):
    """Test that recording outcomes updates accuracy data."""
    # Record predictions
    learning_engine.record_prediction("AAPL", "buffett", "bullish", 7.5, 0.8)
    learning_engine.record_prediction("AAPL", "graham", "bearish", 3.0, 0.7)
    learning_engine.record_prediction("AAPL", "lynch", "bullish", 8.0, 0.9)

    # Record positive outcome (stock went up 5%)
    learning_engine.record_outcome("AAPL", 0.05)

    accuracy = learning_engine.get_accuracy()
    assert "buffett" in accuracy
    assert accuracy["buffett"]["total_predictions"] == 1
    assert accuracy["buffett"]["correct_predictions"] == 1  # Bullish was correct


def test_record_outcome_bearish_correct(learning_engine):
    """Test bearish prediction is correct when stock drops."""
    learning_engine.record_prediction("TSLA", "graham", "bearish", 3.0, 0.8)
    learning_engine.record_outcome("TSLA", -0.05)

    accuracy = learning_engine.get_accuracy()
    assert accuracy["graham"]["correct_predictions"] == 1


def test_weights_recalculated_after_outcome(learning_engine):
    """Test that weights are recalculated after recording outcomes."""
    # Multiple predictions for different agents
    for i in range(5):
        learning_engine.record_prediction("AAPL", "buffett", "bullish", 7.5, 0.8)
        learning_engine.record_prediction("AAPL", "graham", "bearish", 3.0, 0.7)

    # Stock goes up - buffett should get higher weight
    for i in range(5):
        learning_engine.record_outcome("AAPL", 0.03)

    weights = learning_engine.get_weights()
    assert len(weights) > 0
    # Buffett should have higher weight (was correct more often)
    if "buffett" in weights and "graham" in weights:
        assert weights["buffett"] > weights["graham"]


def test_persistence(tmp_path):
    """Test that weights are persisted to disk and loaded back."""
    weights_path = tmp_path / "weights.json"

    # Create engine, record data, trigger save
    engine1 = LearningEngine(weights_path=weights_path)
    for i in range(4):
        engine1.record_prediction("AAPL", "buffett", "bullish", 7.0, 0.8)
    engine1.record_outcome("AAPL", 0.05)

    # Verify file exists
    assert weights_path.exists()

    # Load a new engine from same path
    engine2 = LearningEngine(weights_path=weights_path)
    assert engine2.has_learned_weights
    assert len(engine2.get_weights()) > 0


def test_reset(learning_engine):
    """Test resetting all learned data."""
    for _ in range(4):
        learning_engine.record_prediction("AAPL", "buffett", "bullish", 7.5, 0.8)
    learning_engine.record_outcome("AAPL", 0.05)
    assert learning_engine.has_learned_weights

    learning_engine.reset()
    assert learning_engine.has_learned_weights is False
    assert learning_engine.prediction_count == 0
    assert learning_engine.get_weights() == {}


def test_get_agent_weight(learning_engine):
    """Test getting a specific agent's weight."""
    assert learning_engine.get_agent_weight("buffett") is None

    for i in range(4):
        learning_engine.record_prediction("AAPL", "buffett", "bullish", 7.0, 0.8)
    learning_engine.record_outcome("AAPL", 0.05)

    weight = learning_engine.get_agent_weight("buffett")
    assert weight is not None
    assert 0 < weight <= 1.0


def test_neutral_prediction_correct(learning_engine):
    """Test neutral prediction is correct when stock moves little."""
    learning_engine.record_prediction("MSFT", "marks", "neutral", 5.0, 0.6)
    learning_engine.record_outcome("MSFT", 0.01)  # Within 2% threshold

    accuracy = learning_engine.get_accuracy()
    assert accuracy["marks"]["correct_predictions"] == 1


def test_record_outcome_min_age_days(learning_engine):
    """Stale predictions (>= min_age_days) resolve; recent ones stay pending."""
    now = 1_700_000_000.0  # fixed epoch — avoids boundary flakiness under load
    learning_engine._predictions.append({
        "ticker": "AAPL",
        "agent_id": "buffett",
        "signal": "bullish",
        "score": 7.0,
        "confidence": 0.8,
        "timestamp": now - 35 * 86400,
        "outcome": None,
    })
    learning_engine._predictions.append({
        "ticker": "AAPL",
        "agent_id": "graham",
        "signal": "bearish",
        "score": 3.0,
        "confidence": 0.7,
        "timestamp": now,
        "outcome": None,
    })

    with patch("augur.learning.time.time", return_value=now):
        learning_engine.record_outcome("AAPL", 0.04, min_age_days=30)

    accuracy = learning_engine.get_accuracy()
    assert "buffett" in accuracy
    assert accuracy["buffett"]["total_predictions"] == 1
    assert "graham" not in accuracy
    assert learning_engine._predictions[-1]["outcome"] is None


def test_record_outcome_too_stale_skipped(learning_engine):
    """Predictions older than lookback+min_age window stay unresolved."""
    now = 1_700_000_000.0
    learning_engine._predictions.append({
        "ticker": "AAPL",
        "agent_id": "buffett",
        "signal": "bullish",
        "score": 7.0,
        "confidence": 0.8,
        "timestamp": now - 65 * 86400,
        "outcome": None,
    })

    with patch("augur.learning.time.time", return_value=now):
        learning_engine.record_outcome("AAPL", 0.04, min_age_days=30)

    assert learning_engine.get_accuracy() == {}
    assert learning_engine._predictions[0]["outcome"] is None


def test_record_outcome_skipped_predictions_log_debug(learning_engine, caplog):
    """Predictions dropped by lookback / min_age / max_age filters emit a debug log."""
    now = 1_700_000_000.0
    # Too-recent prediction (blocked by min_age_days=30)
    learning_engine._predictions.append({
        "ticker": "AAPL",
        "agent_id": "graham",
        "signal": "bearish",
        "score": 3.0,
        "confidence": 0.7,
        "timestamp": now - 5 * 86400,
        "outcome": None,
    })
    # Way-too-stale prediction (outside lookback+min_age window of 60d)
    learning_engine._predictions.append({
        "ticker": "AAPL",
        "agent_id": "lynch",
        "signal": "bullish",
        "score": 8.0,
        "confidence": 0.9,
        "timestamp": now - 90 * 86400,
        "outcome": None,
    })

    with caplog.at_level(logging.DEBUG, logger="augur.learning"):
        with patch("augur.learning.time.time", return_value=now):
            # min_age_days=30 path: graham (5d) skipped as "not old enough";
            # lynch (90d) skipped as "too stale" (window is 30+30=60d).
            learning_engine.record_outcome("AAPL", 0.04, min_age_days=30)

    messages = [r.getMessage() for r in caplog.records
                if r.name == "augur.learning" and r.levelno == logging.DEBUG]
    assert any("not old enough" in m and "graham" in m for m in messages), messages
    assert any("too stale" in m and "lynch" in m for m in messages), messages
    # None of the skipped predictions should have been resolved.
    assert all(p["outcome"] is None for p in learning_engine._predictions)

    # Now exercise the default-lookback branch with a separate, stale prediction.
    caplog.clear()
    learning_engine._predictions.append({
        "ticker": "MSFT",
        "agent_id": "buffett",
        "signal": "bullish",
        "score": 7.0,
        "confidence": 0.8,
        "timestamp": now - 60 * 86400,
        "outcome": None,
    })
    with caplog.at_level(logging.DEBUG, logger="augur.learning"):
        with patch("augur.learning.time.time", return_value=now):
            learning_engine.record_outcome("MSFT", 0.02)

    messages = [r.getMessage() for r in caplog.records
                if r.name == "augur.learning" and r.levelno == logging.DEBUG]
    assert any("outside lookback window" in m and "buffett" in m for m in messages), messages


# ---------------------------------------------------------------------------
# Round 6 additions: hit/miss boundary, rolling winrate, cold start, decay/cap
# ---------------------------------------------------------------------------

def test_bullish_miss_below_threshold(learning_engine):
    """Bullish prediction with a small positive return (<2%) counts as a miss."""
    learning_engine.record_prediction("AAPL", "buffett", "bullish", 7.0, 0.8)
    learning_engine.record_outcome("AAPL", 0.01)  # up, but below 2% threshold
    acc = learning_engine.get_accuracy()
    assert acc["buffett"]["total_predictions"] == 1
    assert acc["buffett"]["correct_predictions"] == 0
    # IC uses sign-of-return, not magnitude — 0.01 > 0 yields a positive IC contribution.
    assert acc["buffett"]["ic"] > 0


def test_bearish_miss_when_stock_rises(learning_engine):
    """Bearish prediction with a positive return counts as a miss."""
    learning_engine.record_prediction("TSLA", "graham", "bearish", 3.0, 0.8)
    learning_engine.record_outcome("TSLA", 0.05)
    acc = learning_engine.get_accuracy()
    assert acc["graham"]["correct_predictions"] == 0
    # IC sign: bearish score (normalized <0) * positive-return sign = negative
    assert acc["graham"]["ic"] < 0


def test_neutral_miss_outside_band(learning_engine):
    """Neutral prediction outside the +/-2% band counts as a miss."""
    learning_engine.record_prediction("MSFT", "marks", "neutral", 5.0, 0.6)
    learning_engine.record_outcome("MSFT", 0.04)  # outside 2% band
    acc = learning_engine.get_accuracy()
    assert acc["marks"]["total_predictions"] == 1
    assert acc["marks"]["correct_predictions"] == 0


def test_rolling_winrate_updates_with_each_outcome(learning_engine):
    """Accuracy rate is recomputed as a rolling fraction over all outcomes."""
    agent = "buffett"
    # 4 outcomes: 3 correct (bullish, return > 2%) + 1 miss (return = 0.01)
    for i in range(3):
        learning_engine.record_prediction(f"T{i}", agent, "bullish", 7.5, 0.8)
    learning_engine.record_prediction("TMISS", agent, "bullish", 7.5, 0.8)
    for i in range(3):
        learning_engine.record_outcome(f"T{i}", 0.05)
    learning_engine.record_outcome("TMISS", 0.01)

    acc = learning_engine.get_accuracy()[agent]
    assert acc["total_predictions"] == 4
    assert acc["correct_predictions"] == 3
    assert acc["accuracy_rate"] == pytest.approx(0.75)


def test_cold_start_no_learned_weights(learning_engine):
    """Before 3 outcomes per agent, has_learned_weights is False and weights stay neutral/empty."""
    agent = "buffett"
    learning_engine.record_prediction("AAPL", agent, "bullish", 7.0, 0.8)
    learning_engine.record_prediction("AAPL", agent, "bullish", 7.0, 0.8)
    learning_engine.record_outcome("AAPL", 0.05)
    learning_engine.record_outcome("AAPL", 0.05)

    # Only 2 outcomes — not enough for learned weights.
    assert learning_engine.has_learned_weights is False
    acc = learning_engine.get_accuracy()[agent]
    assert acc["total_predictions"] == 2
    assert acc["accuracy_rate"] == 1.0  # both correct, but cold start


def test_learned_weights_activate_after_three_outcomes(learning_engine):
    """has_learned_weights flips to True once an agent has >= 3 outcomes."""
    agent = "buffett"
    for i in range(3):
        learning_engine.record_prediction(f"T{i}", agent, "bullish", 7.0, 0.8)
    for i in range(3):
        learning_engine.record_outcome(f"T{i}", 0.05)

    assert learning_engine.has_learned_weights is True
    weights = learning_engine.get_weights()
    assert agent in weights
    # Single-agent normalization: weight is 1.0
    assert weights[agent] == pytest.approx(1.0)


def test_outcome_only_marks_matching_ticker(learning_engine):
    """record_outcome only updates predictions for the specified ticker."""
    # Two tickers, two agents — record outcomes one ticker at a time.
    learning_engine.record_prediction("AAPL", "buffett", "bullish", 7.0, 0.8)
    learning_engine.record_prediction("MSFT", "graham", "bearish", 3.0, 0.8)
    learning_engine.record_outcome("AAPL", 0.05)

    acc = learning_engine.get_accuracy()
    assert "buffett" in acc and "graham" not in acc
    # The MSFT prediction should still be unresolved.
    assert learning_engine._predictions[1]["outcome"] is None


def test_predictions_capped_at_100_on_persist(tmp_path):
    """Persisted predictions are trimmed to the most recent 100 (rolling cap)."""
    weights_path = tmp_path / "cap_weights.json"
    engine = LearningEngine(weights_path=weights_path)
    # Record 120 predictions and resolve them so _save_weights runs.
    for i in range(120):
        engine.record_prediction(f"T{i:03d}", "buffett", "bullish", 7.0, 0.8)
    for i in range(120):
        engine.record_outcome(f"T{i:03d}", 0.05)

    # In-memory list still holds everything until next save triggers.
    # Force a save via a fresh outcome on a new ticker.
    engine.record_prediction("T_TRIG", "buffett", "bullish", 7.0, 0.8)
    engine.record_outcome("T_TRIG", 0.05)

    data = json.loads(weights_path.read_text(encoding="utf-8"))
    assert len(data["predictions"]) == 100
    # The earliest in-memory prediction is gone from disk; newest 100 remain.
    tickers_on_disk = [p["ticker"] for p in data["predictions"]]
    assert "T000" not in tickers_on_disk
    assert tickers_on_disk[-1] == "T_TRIG"


def test_learning_engine_accepts_string_weights_path(tmp_path):
    """weights_path may be passed as str; must not crash on .exists()."""
    path = str(tmp_path / "weights.json")
    engine = LearningEngine(weights_path=path)
    assert engine.weights_path == Path(path)


def test_record_prediction_normalizes_signal_case(learning_engine):
    """Uppercase signal strings are normalized before outcome evaluation."""
    learning_engine.record_prediction("AAPL", "buffett", "BULLISH", 7.0, 0.8)
    learning_engine.record_outcome("AAPL", 0.05)
    acc = learning_engine.get_accuracy()
    assert acc["buffett"]["correct_predictions"] == 1


def test_record_prediction_sanitizes_non_numeric_score(learning_engine):
    """Non-numeric scores are coerced instead of breaking weight math."""
    learning_engine.record_prediction("AAPL", "buffett", "bullish", "bad", 0.8)
    pred = learning_engine._predictions[-1]
    assert pred["score"] == 5.0
    assert isinstance(pred["confidence"], float)


def test_record_outcome_ignores_nan_return(learning_engine):
    """NaN actual returns must not corrupt accuracy tracking."""
    learning_engine.record_prediction("AAPL", "buffett", "bullish", 7.0, 0.8)
    learning_engine.record_outcome("AAPL", float("nan"))
    assert learning_engine.get_accuracy() == {}
    assert learning_engine._predictions[-1]["outcome"] is None
