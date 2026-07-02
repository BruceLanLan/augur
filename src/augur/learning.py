# -*- coding: utf-8 -*-
"""
augur.learning - Agent Learning Engine

Tracks prediction accuracy from IC (Information Coefficient) feedback,
adjusts agent consensus weights based on historical accuracy, and
persists learned weights to disk.

Architecture:
    - LearningEngine: Records predictions, tracks outcomes, recalculates weights
    - Weight persistence: JSON file at ~/.augur/learned_weights.json
    - IC-based scoring: combines accuracy rate + information coefficient

Workflow:
    1. record_prediction() - store agent predictions during analysis
    2. record_outcome() - provide actual returns for a ticker
    3. Internally: evaluate correctness, update IC, recalculate weights
    4. get_weights() - retrieve optimized weights for use in consensus

Weight Calculation:
    - Accuracy rate: correct predictions / total predictions
    - IC contribution: correlation between predicted score direction and actual return
    - Combined weight: 50% accuracy + 50% IC-based score, clamped to [0.1, 3.0]
    - Normalized to sum to 1.0 across all tracked agents

Integration:
    - Used as module-level singleton in registry.py (_get_learning_engine())
    - Weights blended into consensus: 60% base weight + 40% learned weight
    - Minimum 3 predictions required before weights become active

Usage:
    engine = LearningEngine()
    engine.record_prediction("AAPL", "buffett", "bullish", 7.5, 0.8)
    engine.record_outcome("AAPL", actual_return=0.05)
    weights = engine.get_weights()
"""

import json
import logging
import math
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def _get_weights_path() -> Path:
    """Get the path for persisting learned weights."""
    augur_dir = Path.home() / ".augur"
    augur_dir.mkdir(parents=True, exist_ok=True)
    return augur_dir / "learned_weights.json"


class LearningEngine:
    """
    Agent Learning Engine.

    Tracks prediction accuracy and adjusts consensus weights based on
    historical performance. Agents with higher IC scores receive higher
    weights in future consensus calculations.
    """

    def __init__(self, weights_path: Path = None):
        """
        Initialize the LearningEngine.

        Args:
            weights_path: Path to store learned weights.
                         Defaults to ~/.augur/learned_weights.json.
        """
        self.weights_path = (
            Path(weights_path) if weights_path is not None else _get_weights_path()
        )
        self._predictions: List[Dict[str, Any]] = []
        self._weights: Dict[str, float] = {}
        self._accuracy: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._load_weights()

    def _load_weights(self):
        """Load persisted weights from disk."""
        if self.weights_path.exists():
            try:
                data = json.loads(self.weights_path.read_text(encoding="utf-8"))
                self._weights = data.get("weights", {})
                self._accuracy = data.get("accuracy", {})
                self._predictions = data.get("predictions", [])
            except (json.JSONDecodeError, OSError):
                self._weights = {}
                self._accuracy = {}
                self._predictions = []

    def _save_weights(self):
        """Persist learned weights to disk."""
        data = {
            "weights": self._weights,
            "accuracy": self._accuracy,
            "predictions": self._predictions[-100:],  # Keep last 100 predictions
            "updated_at": time.time(),
        }
        self.weights_path.parent.mkdir(parents=True, exist_ok=True)
        self.weights_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def record_prediction(
        self,
        ticker: str,
        agent_id: str,
        signal: str,
        score: float,
        confidence: float,
    ):
        """
        Record an agent's prediction for future accuracy tracking.

        Args:
            ticker: Stock ticker.
            agent_id: The agent that made the prediction.
            signal: The signal (bullish/bearish/neutral).
            score: The score (0-10).
            confidence: Confidence level (0-1).
        """
        signal = (signal or "neutral").strip().lower()
        if signal not in ("bullish", "bearish", "neutral"):
            signal = "neutral"

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 5.0
        if isinstance(score, bool) or not math.isfinite(score):
            score = 5.0
        score = max(0.0, min(10.0, score))

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        if isinstance(confidence, bool) or not math.isfinite(confidence):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        with self._lock:
            self._predictions.append({
                "ticker": ticker,
                "agent_id": agent_id,
                "signal": signal,
                "score": score,
                "confidence": confidence,
                "timestamp": time.time(),
                "outcome": None,  # To be filled in later
            })

    def record_outcome(
        self,
        ticker: str,
        actual_return: float,
        lookback_days: int = 30,
        min_age_days: Optional[int] = None,
    ):
        """
        Record the actual outcome for predictions and update accuracy.

        Args:
            ticker: Stock ticker.
            actual_return: The actual return (e.g., 0.05 for +5%).
            lookback_days: How far back to look for matching predictions (recent window).
            min_age_days: When set, only resolve predictions at least this many days old
                          (used by auto-outcome checks for stale predictions).
        """
        now = time.time()
        if not isinstance(actual_return, (int, float)) or isinstance(actual_return, bool):
            logger.debug("record_outcome ignored non-numeric return for %s", ticker)
            return
        if not math.isfinite(float(actual_return)):
            logger.debug("record_outcome ignored non-finite return for %s", ticker)
            return
        cutoff = now - (lookback_days * 86400)
        min_age_cutoff = now - (min_age_days * 86400) if min_age_days is not None else None
        updated = False

        with self._lock:
            for pred in self._predictions:
                if pred["ticker"] == ticker and pred["outcome"] is None:
                    ts = pred["timestamp"]
                    if min_age_cutoff is not None:
                        if ts > min_age_cutoff:
                            logger.debug(
                                "skipping prediction for %s from %s: not old enough (age=%.1fd < min_age=%dd)",
                                ticker, pred["agent_id"],
                                (now - ts) / 86400.0, min_age_days,
                            )
                            continue  # prediction not old enough yet
                        max_age_cutoff = now - ((lookback_days + min_age_days) * 86400)
                        if ts < max_age_cutoff:
                            logger.debug(
                                "skipping prediction for %s from %s: too stale (age=%.1fd > lookback+min_age=%dd)",
                                ticker, pred["agent_id"],
                                (now - ts) / 86400.0, lookback_days + min_age_days,
                            )
                            continue  # too stale to auto-resolve
                    elif ts < cutoff:
                        logger.debug(
                            "skipping prediction for %s from %s: outside lookback window (age=%.1fd > lookback=%dd)",
                            ticker, pred["agent_id"],
                            (now - ts) / 86400.0, lookback_days,
                        )
                        continue  # outside recent lookback window
                    pred["outcome"] = actual_return
                    was_correct = self._evaluate_prediction(pred, actual_return)
                    self._update_accuracy(pred["agent_id"], was_correct, actual_return, pred["score"])
                    updated = True

            if updated:
                self._recalculate_weights()
                self._save_weights()

    def _evaluate_prediction(self, prediction: Dict[str, Any], actual_return: float) -> bool:
        """Evaluate if a prediction was correct."""
        signal = str(prediction.get("signal", "neutral")).strip().lower()
        if signal == "bullish" and actual_return > 0.02:
            return True
        elif signal == "bearish" and actual_return < -0.02:
            return True
        elif signal == "neutral" and abs(actual_return) <= 0.02:
            return True
        return False

    def _update_accuracy(self, agent_id: str, was_correct: bool, actual_return: float, predicted_score: float):
        """Update accuracy tracking for an agent."""
        if agent_id not in self._accuracy:
            self._accuracy[agent_id] = {
                "correct": 0,
                "total": 0,
                "ic_sum": 0.0,
                "ic_count": 0,
            }

        acc = self._accuracy[agent_id]
        acc["total"] += 1
        if was_correct:
            acc["correct"] += 1

        # Calculate IC contribution (correlation between predicted score and actual return)
        # Normalize predicted score from 0-10 to -1 to 1
        normalized_score = (predicted_score - 5.0) / 5.0
        # Simple IC approximation: product of direction signals
        ic_contribution = normalized_score * (1.0 if actual_return > 0 else -1.0)
        acc["ic_sum"] += ic_contribution
        acc["ic_count"] += 1

    def _recalculate_weights(self):
        """Recalculate weights based on accumulated accuracy data."""
        if not self._accuracy:
            return

        raw_weights = {}
        for agent_id, acc in self._accuracy.items():
            if acc["total"] < 3:
                # Not enough data, use neutral weight
                raw_weights[agent_id] = 1.0
                continue

            # Weight based on accuracy rate and IC
            accuracy_rate = acc["correct"] / acc["total"]
            ic = acc["ic_sum"] / acc["ic_count"] if acc["ic_count"] > 0 else 0.0

            # Combine accuracy and IC into a weight
            # Higher accuracy and positive IC = higher weight
            weight = 0.5 * (accuracy_rate * 2) + 0.5 * max(0, ic + 1)
            raw_weights[agent_id] = max(0.1, min(3.0, weight))  # Clamp to [0.1, 3.0]

        # Normalize weights to sum to 1
        total = sum(raw_weights.values())
        if total > 0:
            self._weights = {k: v / total for k, v in raw_weights.items()}
        else:
            self._weights = {k: 1.0 / len(raw_weights) for k in raw_weights}

    def get_weights(self) -> Dict[str, float]:
        """Get current learned weights."""
        with self._lock:
            return self._weights.copy()

    def get_accuracy(self) -> Dict[str, Dict[str, Any]]:
        """Get accuracy data for all agents."""
        with self._lock:
            accuracy = dict(self._accuracy)
        result = {}
        for agent_id, acc in accuracy.items():
            result[agent_id] = {
                "accuracy_rate": acc["correct"] / acc["total"] if acc["total"] > 0 else 0.0,
                "total_predictions": acc["total"],
                "correct_predictions": acc["correct"],
                "ic": acc["ic_sum"] / acc["ic_count"] if acc["ic_count"] > 0 else 0.0,
            }
        return result

    def get_agent_weight(self, agent_id: str) -> Optional[float]:
        """Get the learned weight for a specific agent."""
        with self._lock:
            return self._weights.get(agent_id)

    def reset(self):
        """Reset all learned data."""
        with self._lock:
            self._predictions = []
            self._weights = {}
            self._accuracy = {}
            if self.weights_path.exists():
                self.weights_path.unlink()

    @property
    def has_learned_weights(self) -> bool:
        """Check if there are meaningful learned weights (>=3 outcomes per agent)."""
        with self._lock:
            if not self._weights:
                return False
            return any(acc.get("total", 0) >= 3 for acc in self._accuracy.values())

    @property
    def pending_count(self) -> int:
        """Number of recorded predictions still awaiting outcome resolution."""
        with self._lock:
            return sum(1 for p in self._predictions if p["outcome"] is None)

    @property
    def prediction_count(self) -> int:
        """Get total number of recorded predictions."""
        with self._lock:
            return len(self._predictions)
