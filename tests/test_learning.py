# -*- coding: utf-8 -*-
"""Tests for augur.learning - Agent Learning Engine"""

import json
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
