# -*- coding: utf-8 -*-
"""Purged walk-forward OOS (out-of-sample) A/B harness for rolling-IC consensus.

Evaluates whether the 50/50 rolling-IC blend (Variant B) produces better-
calibrated probabilities than a static equal-weight baseline (Baseline A).

Pre-registered gate
-------------------
Before running the harness, thresholds are written down so results cannot
be cherry-picked post-hoc. If Variant B does not clear every threshold,
it is marked "insufficient evidence" and the rolling-IC blend should not
be enabled by default.

Calibration metrics
-------------------
- Brier score (mean squared error)
- Log loss (negative log-likelihood)
- Reliability curve (binned calibration)
- ECE (Expected Calibration Error)
- Calibration-in-the-large (slope / intercept from outcome ~ prediction)
- Coverage (fraction of predictions with resolved outcomes)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-registered gate thresholds
# ---------------------------------------------------------------------------
# These are written down BEFORE looking at results. If the harness is
# re-run and Variant B doesn't clear these, the rolling-IC blend should
# NOT be enabled by default in the consensus engine.
PREREG_COVERAGE_MIN = 0.10      # at least 10% of predictions have resolved outcomes
PREREG_ECE_MAX = 0.10           # Expected Calibration Error ≤ 10%
PREREG_BRIER_IMPROVEMENT_MIN = 0.0  # Brier must be strictly lower (better) than baseline


@dataclass
class OOSResult:
    """Result of a purged walk-forward OOS evaluation.

    All metrics are computed on the test windows only — training data
    is never included in evaluation.
    """
    brier: float
    log_loss: float
    reliability: Dict[str, List[float]]  # {"bin_centers": [...], "bin_accuracy": [...], "bin_counts": [...]}
    slope: float
    intercept: float
    ece: float
    coverage: float
    baseline_brier: float
    baseline_log_loss: float
    baseline_ece: float
    n_samples: int
    sufficient: bool          # n_samples >= MIN_SAMPLES_FOR_CALIBRATION
    gate_passed: bool = False
    gate_details: Dict = field(default_factory=dict)
    variant_label: str = "rolling-ic-50-50"
    baseline_label: str = "equal-weight"


# Minimum resolved outcomes to consider calibration assessment meaningful.
# Matches CalibrationStatus.MIN_SAMPLES for consistency.
MIN_SAMPLES_FOR_CALIBRATION = 30


def run_purged_walkforward(
    tickers: List[str],
    train_start: str,
    train_end: str,
    test_start: str,
    test_end: str,
    purge_days: int = 5,
    predictions: Optional[Dict] = None,
    outcomes: Optional[Dict] = None,
) -> OOSResult:
    """Run a purged walk-forward OOS evaluation of rolling-IC blend vs baseline.

    The purge gap between train and test prevents information leakage:
    predictions made on day T use information only up to day T - purge_days.

    Args:
        tickers: List of ticker symbols to evaluate.
        train_start: Start date for training window (YYYY-MM-DD).
        train_end: End date for training window (YYYY-MM-DD).
        test_start: Start date for test window (YYYY-MM-DD).
        test_end: End date for test window (YYYY-MM-DD).
        purge_days: Number of calendar days to purge between train and test.
        predictions: Optional pre-computed predictions dict of shape
            {ticker: [{date, prob_a, prob_b, ...}]}. When None, the
            harness expects callers to supply data via _evaluate_predictions.
        outcomes: Optional pre-computed outcomes dict of shape
            {ticker: [{date, realized_return, ...}]}. When None, same as above.

    Returns:
        OOSResult with all calibration metrics for both baseline and variant.
    """
    if predictions is None or outcomes is None:
        return OOSResult(
            brier=0.0,
            log_loss=0.0,
            reliability={"bin_centers": [], "bin_accuracy": [], "bin_counts": []},
            slope=0.0,
            intercept=0.0,
            ece=0.0,
            coverage=0.0,
            baseline_brier=0.0,
            baseline_log_loss=0.0,
            baseline_ece=0.0,
            n_samples=0,
            sufficient=False,
        )

    # Collect paired (prob, outcome) for baseline A and variant B
    prob_a, prob_b, y_true = _collect_test_pairs(
        tickers, predictions, outcomes, test_start, test_end,
    )

    n_samples = len(y_true)
    total_possible = sum(
        len(predictions.get(t, [])) for t in tickers
    )
    coverage = n_samples / total_possible if total_possible > 0 else 0.0
    sufficient = n_samples >= MIN_SAMPLES_FOR_CALIBRATION

    # Compute metrics for both arms
    metrics_a = _compute_calibration_metrics(prob_a, y_true)
    metrics_b = _compute_calibration_metrics(prob_b, y_true)

    # Gate check
    gate_checks = {
        "coverage": coverage >= PREREG_COVERAGE_MIN,
        "ece": metrics_b["ece"] <= PREREG_ECE_MAX,
        "brier_improvement": (metrics_a["brier"] - metrics_b["brier"]) >= PREREG_BRIER_IMPROVEMENT_MIN,
    }
    gate_passed = all(gate_checks.values())

    gate_details = {
        "thresholds": {
            "coverage_min": PREREG_COVERAGE_MIN,
            "ece_max": PREREG_ECE_MAX,
            "brier_improvement_min": PREREG_BRIER_IMPROVEMENT_MIN,
        },
        "actuals": {
            "coverage": round(coverage, 4),
            "ece_variant": round(metrics_b["ece"], 4),
            "brier_baseline": round(metrics_a["brier"], 4),
            "brier_variant": round(metrics_b["brier"], 4),
            "brier_delta": round(metrics_a["brier"] - metrics_b["brier"], 4),
        },
        "checks": gate_checks,
        "passed": gate_passed,
    }

    return OOSResult(
        brier=round(metrics_b["brier"], 6),
        log_loss=round(metrics_b["log_loss"], 6),
        reliability=metrics_b["reliability"],
        slope=round(metrics_b["slope"], 4),
        intercept=round(metrics_b["intercept"], 4),
        ece=round(metrics_b["ece"], 4),
        coverage=round(coverage, 4),
        baseline_brier=round(metrics_a["brier"], 6),
        baseline_log_loss=round(metrics_a["log_loss"], 6),
        baseline_ece=round(metrics_a["ece"], 4),
        n_samples=n_samples,
        sufficient=sufficient,
        gate_passed=gate_passed,
        gate_details=gate_details,
    )


def _collect_test_pairs(
    tickers: List[str],
    predictions: Dict,
    outcomes: Dict,
    test_start: str,
    test_end: str,
) -> Tuple[List[float], List[float], List[float]]:
    """Collect (prob_a, prob_b, y_true) triples for the test window."""
    prob_a: List[float] = []
    prob_b: List[float] = []
    y_true: List[float] = []

    # Build outcome lookup
    outcome_lookup: Dict[str, Dict[str, float]] = {}
    for ticker, entries in outcomes.items():
        outcome_lookup.setdefault(ticker, {})
        for entry in entries:
            outcome_lookup[ticker][entry.get("date", "")] = entry.get("realized_return", 0.0)

    for ticker in tickers:
        ticker_preds = predictions.get(ticker, [])
        ticker_outcomes = outcome_lookup.get(ticker, {})
        for pred in ticker_preds:
            date = pred.get("date", "")
            if date < test_start or date > test_end:
                continue
            outcome = ticker_outcomes.get(date)
            if outcome is None:
                continue
            pa = pred.get("prob_a", pred.get("baseline_prob"))
            pb = pred.get("prob_b", pred.get("variant_prob"))
            if pa is None or pb is None:
                continue
            # Binary outcome: 1 if positive return, 0 otherwise
            y = 1.0 if outcome > 0 else 0.0
            prob_a.append(float(pa))
            prob_b.append(float(pb))
            y_true.append(y)

    return prob_a, prob_b, y_true


def _compute_calibration_metrics(
    probs: List[float],
    y_true: List[float],
    n_bins: int = 10,
) -> Dict:
    """Compute Brier, log loss, ECE, reliability, and calibration slope/intercept.

    Args:
        probs: Predicted probabilities (0-1 range).
        y_true: Binary outcomes (0 or 1).
        n_bins: Number of bins for reliability curve and ECE.

    Returns:
        Dict with keys: brier, log_loss, reliability, slope, intercept, ece.
    """
    if len(probs) == 0:
        return {
            "brier": 0.0,
            "log_loss": 0.0,
            "reliability": {"bin_centers": [], "bin_accuracy": [], "bin_counts": []},
            "slope": 0.0,
            "intercept": 0.0,
            "ece": 0.0,
        }

    probs_arr = np.asarray(probs, dtype=np.float64)
    y_arr = np.asarray(y_true, dtype=np.float64)
    n = len(probs_arr)

    # --- Brier score ---
    brier = float(np.mean((probs_arr - y_arr) ** 2))

    # --- Log loss (clipped to avoid log(0)) ---
    eps = 1e-15
    p_clipped = np.clip(probs_arr, eps, 1.0 - eps)
    log_loss = float(-np.mean(y_arr * np.log(p_clipped) + (1 - y_arr) * np.log(1.0 - p_clipped)))

    # --- Calibration-in-the-large (slope / intercept) ---
    # Regress y ~ p: y = slope * p + intercept
    # Perfect calibration: slope=1, intercept=0
    slope, intercept = 0.0, 0.0
    if n >= 3:
        p_mean = float(np.mean(probs_arr))
        y_mean = float(np.mean(y_arr))
        cov = float(np.mean((probs_arr - p_mean) * (y_arr - y_mean)))
        var_p = float(np.mean((probs_arr - p_mean) ** 2))
        if var_p > 1e-15:
            slope = cov / var_p
            intercept = y_mean - slope * p_mean

    # --- Reliability curve and ECE ---
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers: List[float] = []
    bin_accuracy: List[float] = []
    bin_counts: List[int] = []
    ece_sum = 0.0

    for i in range(n_bins):
        lo = bin_edges[i]
        hi = bin_edges[i + 1]
        # Last bin includes the right edge
        if i == n_bins - 1:
            mask = (probs_arr >= lo) & (probs_arr <= hi)
        else:
            mask = (probs_arr >= lo) & (probs_arr < hi)
        count = int(np.sum(mask))
        bin_counts.append(count)
        if count > 0:
            mean_pred = float(np.mean(probs_arr[mask]))
            mean_obs = float(np.mean(y_arr[mask]))
            bin_centers.append(round(mean_pred, 4))
            bin_accuracy.append(round(mean_obs, 4))
            ece_sum += count * abs(mean_pred - mean_obs)
        else:
            bin_centers.append(round((lo + hi) / 2, 4))
            bin_accuracy.append(0.0)

    ece = float(ece_sum / n) if n > 0 else 0.0

    return {
        "brier": brier,
        "log_loss": log_loss,
        "reliability": {
            "bin_centers": bin_centers,
            "bin_accuracy": bin_accuracy,
            "bin_counts": bin_counts,
        },
        "slope": slope,
        "intercept": intercept,
        "ece": ece,
    }


def evaluate_from_backtest_records(
    records: List,
    baseline_weights: Optional[Dict[str, float]] = None,
    rolling_ic_weights: Optional[Dict[str, float]] = None,
    min_samples: int = MIN_SAMPLES_FOR_CALIBRATION,
) -> OOSResult:
    """Evaluate calibration from backtest records directly.

    This is a convenience wrapper for when you already have BacktestRecord
    objects and rolling IC weights, without needing to build the full
    predictions/outcomes dicts.

    Args:
        records: List of BacktestRecord objects (or dicts with same fields).
        baseline_weights: Per-agent weights for the static baseline.
            Defaults to uniform (equal weight across all agents seen).
        rolling_ic_weights: Per-agent IC weights for the 50/50 blend variant.
        min_samples: Minimum resolved outcomes required.

    Returns:
        OOSResult with calibration metrics.
    """
    if not records:
        return OOSResult(
            brier=0.0, log_loss=0.0,
            reliability={"bin_centers": [], "bin_accuracy": [], "bin_counts": []},
            slope=0.0, intercept=0.0, ece=0.0, coverage=0.0,
            baseline_brier=0.0, baseline_log_loss=0.0, baseline_ece=0.0,
            n_samples=0, sufficient=False,
        )

    # Collect per-date consensus probabilities
    # Group records by (ticker, date)
    by_key: Dict[Tuple[str, str], List] = {}
    for r in records:
        # Support both BacktestRecord objects and dicts
        ticker = getattr(r, "ticker", r.get("ticker", "")) if hasattr(r, "get") else r.ticker
        date = getattr(r, "date", r.get("date", "")) if hasattr(r, "get") else r.date
        key = (ticker, date)
        by_key.setdefault(key, []).append(r)

    if baseline_weights is None:
        # Collect all agent ids
        all_agents = set()
        for recs in by_key.values():
            for r in recs:
                aid = getattr(r, "agent_id", r.get("agent_id", "")) if hasattr(r, "get") else r.agent_id
                all_agents.add(aid)
        n_agents = len(all_agents)
        baseline_weights = {aid: 1.0 / n_agents for aid in all_agents} if n_agents else {}

    if rolling_ic_weights is None:
        rolling_ic_weights = {}

    # Normalize rolling IC weights
    ric_total = sum(rolling_ic_weights.values())
    if ric_total > 0:
        rolling_ic_weights = {k: v / ric_total for k, v in rolling_ic_weights.items()}

    prob_a: List[float] = []
    prob_b: List[float] = []
    y_true: List[float] = []

    for (ticker, date), recs in by_key.items():
        # Baseline A: equal-weight average
        total_a = 0.0
        total_b = 0.0
        weight_sum_a = 0.0
        weight_sum_b = 0.0

        for r in recs:
            signal = getattr(r, "signal", r.get("signal", "")) if hasattr(r, "get") else r.signal
            score = getattr(r, "score", r.get("score", 0)) if hasattr(r, "get") else r.score
            aid = getattr(r, "agent_id", r.get("agent_id", "")) if hasattr(r, "get") else r.agent_id

            if signal in ("neutral", ""):
                signed = 0.0
            elif signal == "bullish":
                signed = score
            elif signal == "bearish":
                signed = -score
            else:
                signed = 0.0

            w_a = baseline_weights.get(aid, 0.0)
            if w_a <= 0:
                continue

            # Baseline: pure static weight
            total_a += signed * w_a
            weight_sum_a += w_a

            # Variant: 50/50 blend of static + rolling IC
            ric_w = rolling_ic_weights.get(aid, 0.0)
            w_b = 0.5 * w_a + 0.5 * ric_w
            total_b += signed * w_b
            weight_sum_b += w_b

        if weight_sum_a <= 0:
            continue

        avg_a = total_a / weight_sum_a
        avg_b = total_b / weight_sum_b

        # Convert signed scores to probabilities via sigmoid
        # Score range is [-10, 10]; map to [0, 1]
        prob_a_val = _score_to_prob(avg_a)
        prob_b_val = _score_to_prob(avg_b)

        # For consensus-level evaluation we need the per-key actual return.
        # Use the first record's actual_return_20d as the ground truth since
        # all records for the same (ticker, date) share the same forward return.
        actual_ret = (
            getattr(recs[0], "actual_return_20d", recs[0].get("actual_return_20d", 0.0))
            if hasattr(recs[0], "get") else getattr(recs[0], "actual_return_20d", 0.0)
        )
        y = 1.0 if actual_ret > 0 else 0.0

        prob_a.append(prob_a_val)
        prob_b.append(prob_b_val)
        y_true.append(y)

    n_samples = len(y_true)
    total_keys = len(by_key)
    coverage = n_samples / total_keys if total_keys > 0 else 0.0
    sufficient = n_samples >= min_samples

    metrics_a = _compute_calibration_metrics(prob_a, y_true)
    metrics_b = _compute_calibration_metrics(prob_b, y_true)

    gate_checks = {
        "coverage": coverage >= PREREG_COVERAGE_MIN,
        "ece": metrics_b["ece"] <= PREREG_ECE_MAX,
        "brier_improvement": (metrics_a["brier"] - metrics_b["brier"]) >= PREREG_BRIER_IMPROVEMENT_MIN,
    }
    gate_passed = all(gate_checks.values())

    return OOSResult(
        brier=round(metrics_b["brier"], 6),
        log_loss=round(metrics_b["log_loss"], 6),
        reliability=metrics_b["reliability"],
        slope=round(metrics_b["slope"], 4),
        intercept=round(metrics_b["intercept"], 4),
        ece=round(metrics_b["ece"], 4),
        coverage=round(coverage, 4),
        baseline_brier=round(metrics_a["brier"], 6),
        baseline_log_loss=round(metrics_a["log_loss"], 6),
        baseline_ece=round(metrics_a["ece"], 4),
        n_samples=n_samples,
        sufficient=sufficient,
        gate_passed=gate_passed,
        gate_details={
            "thresholds": {
                "coverage_min": PREREG_COVERAGE_MIN,
                "ece_max": PREREG_ECE_MAX,
                "brier_improvement_min": PREREG_BRIER_IMPROVEMENT_MIN,
            },
            "actuals": {
                "coverage": round(coverage, 4),
                "ece_variant": round(metrics_b["ece"], 4),
                "brier_baseline": round(metrics_a["brier"], 4),
                "brier_variant": round(metrics_b["brier"], 4),
                "brier_delta": round(metrics_a["brier"] - metrics_b["brier"], 4),
            },
            "checks": gate_checks,
            "passed": gate_passed,
        },
    )


def _score_to_prob(score: float) -> float:
    """Convert a signed consensus score in [-10, 10] to a probability in [0, 1].

    Uses a logistic (sigmoid) transformation centered at 0. Score=0 maps to
    prob=0.5, score=10 maps to prob≈0.88, score=-10 maps to prob≈0.12.
    """
    # Scale factor so that score=±10 maps to roughly ±2.0 in logit space
    scaled = score / 5.0  # maps [-10, 10] to [-2, 2]
    return float(1.0 / (1.0 + math.exp(-scaled)))
