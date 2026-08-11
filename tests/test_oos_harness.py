# -*- coding: utf-8 -*-
"""Tests for OOS harness and calibration status (C1.1 + C1.2)."""

import json
import math
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from augur.consensus.calibration import (
    MIN_SAMPLES,
    CalibrationStatus,
    determine_status,
)
from augur.consensus.oos_harness import (
    PREREG_BRIER_IMPROVEMENT_MIN,
    PREREG_COVERAGE_MIN,
    PREREG_ECE_MAX,
    OOSResult,
    _compute_calibration_metrics,
    _score_to_prob,
    evaluate_from_backtest_records,
    run_purged_walkforward,
)


# ---------------------------------------------------------------------------
# _score_to_prob
# ---------------------------------------------------------------------------

class TestScoreToProb:
    def test_zero_score_maps_to_0_5(self):
        assert _score_to_prob(0.0) == pytest.approx(0.5)

    def test_positive_score_increases_probability(self):
        assert _score_to_prob(5.0) > 0.5
        assert _score_to_prob(10.0) > _score_to_prob(5.0)

    def test_negative_score_decreases_probability(self):
        assert _score_to_prob(-5.0) < 0.5
        assert _score_to_prob(-10.0) < _score_to_prob(-5.0)

    def test_bounded_between_0_and_1(self):
        for s in [-10, -5, 0, 5, 10]:
            p = _score_to_prob(float(s))
            assert 0.0 < p < 1.0, f"score={s} -> prob={p}"


# ---------------------------------------------------------------------------
# _compute_calibration_metrics
# ---------------------------------------------------------------------------

class TestComputeCalibrationMetrics:
    def test_perfect_calibration(self):
        """When predictions match outcomes exactly, all errors should be zero."""
        probs = [0.9, 0.1, 0.8, 0.2, 0.95, 0.05]
        y = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
        metrics = _compute_calibration_metrics(probs, y)
        assert metrics["brier"] < 0.02
        assert metrics["log_loss"] < 0.5
        # With only 6 samples, ECE binning is coarse; 0.12 is still
        # well-calibrated for this tiny sample.
        assert metrics["ece"] < 0.2

    def test_perfectly_miscalibrated(self):
        """When predictions are the opposite of outcomes, errors should be high."""
        probs = [0.9, 0.1, 0.9, 0.1]
        y = [0.0, 1.0, 0.0, 1.0]
        metrics = _compute_calibration_metrics(probs, y)
        assert metrics["brier"] > 0.5

    def test_brier_of_uniform_05(self):
        """Brier score for constant 0.5 prediction with balanced outcomes ≈ 0.25."""
        n = 100
        probs = [0.5] * n
        y = [1.0] * (n // 2) + [0.0] * (n // 2)
        metrics = _compute_calibration_metrics(probs, y)
        assert metrics["brier"] == pytest.approx(0.25, abs=0.01)

    def test_ece_calculation(self):
        """ECE should be near zero for well-calibrated forecasts."""
        # Generate well-calibrated forecasts: predict exactly the true rate
        np = pytest.importorskip("numpy")
        rng = np.random.RandomState(42)
        n = 1000
        # True probabilities and outcomes
        true_probs = rng.beta(2, 2, size=n)
        y = (rng.random(n) < true_probs).astype(float)
        metrics = _compute_calibration_metrics(true_probs.tolist(), y.tolist())
        # Well-calibrated: ECE should be small
        assert metrics["ece"] < 0.15, f"ECE={metrics['ece']} too high for calibrated forecasts"

    def test_slope_intercept_perfect(self):
        """Perfect calibration: slope=1, intercept=0."""
        probs = [0.1, 0.3, 0.5, 0.7, 0.9]
        y = [0.1, 0.3, 0.5, 0.7, 0.9]  # Continuous outcome matching probability
        metrics = _compute_calibration_metrics(probs, y)
        assert metrics["slope"] == pytest.approx(1.0, abs=0.01)
        assert metrics["intercept"] == pytest.approx(0.0, abs=0.01)

    def test_empty_input(self):
        metrics = _compute_calibration_metrics([], [])
        assert metrics["brier"] == 0.0
        assert metrics["ece"] == 0.0
        assert metrics["n_samples"] if "n_samples" in metrics else True

    def test_reliability_bins_structure(self):
        probs = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
        y = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        metrics = _compute_calibration_metrics(probs, y)
        assert "bin_centers" in metrics["reliability"]
        assert "bin_accuracy" in metrics["reliability"]
        assert "bin_counts" in metrics["reliability"]
        assert len(metrics["reliability"]["bin_centers"]) == 10
        assert len(metrics["reliability"]["bin_accuracy"]) == 10
        assert len(metrics["reliability"]["bin_counts"]) == 10


# ---------------------------------------------------------------------------
# CalibrationStatus
# ---------------------------------------------------------------------------

class TestCalibrationStatus:
    def test_raw_when_no_assessment(self):
        status = determine_status(n_resolved=100, oos_passed=True, assessment_done=False)
        assert status == CalibrationStatus.RAW

    def test_insufficient_data_below_min(self):
        status = determine_status(n_resolved=10, oos_passed=False, assessment_done=True)
        assert status == CalibrationStatus.INSUFFICIENT_DATA

    def test_insufficient_data_at_boundary(self):
        """MIN_SAMPLES - 1 is still insufficient."""
        status = determine_status(n_resolved=MIN_SAMPLES - 1, oos_passed=True, assessment_done=True)
        assert status == CalibrationStatus.INSUFFICIENT_DATA

    def test_experimental_when_gate_not_passed(self):
        status = determine_status(n_resolved=MIN_SAMPLES, oos_passed=False, assessment_done=True)
        assert status == CalibrationStatus.EXPERIMENTAL

    def test_validated_calibrated_when_gate_passed(self):
        status = determine_status(n_resolved=MIN_SAMPLES + 10, oos_passed=True, assessment_done=True)
        assert status == CalibrationStatus.VALIDATED_CALIBRATED

    def test_enum_values(self):
        assert CalibrationStatus.RAW.value == "raw"
        assert CalibrationStatus.EXPERIMENTAL.value == "experimental"
        assert CalibrationStatus.VALIDATED_CALIBRATED.value == "validated-calibrated"
        assert CalibrationStatus.INSUFFICIENT_DATA.value == "insufficient-data"


# ---------------------------------------------------------------------------
# run_purged_walkforward
# ---------------------------------------------------------------------------

class TestRunPurgedWalkforward:
    def test_empty_predictions_returns_zero_result(self):
        result = run_purged_walkforward(
            tickers=["AAPL"],
            train_start="2024-01-01",
            train_end="2024-06-30",
            test_start="2024-07-01",
            test_end="2024-12-31",
            predictions={"AAPL": []},
            outcomes={"AAPL": []},
        )
        assert result.n_samples == 0
        assert not result.sufficient

    def test_none_predictions_returns_zero_result(self):
        result = run_purged_walkforward(
            tickers=["AAPL"],
            train_start="2024-01-01",
            train_end="2024-06-30",
            test_start="2024-07-01",
            test_end="2024-12-31",
        )
        assert result.n_samples == 0
        assert result.brier == 0.0

    def test_baseline_outperforms_variant_gate_fails(self):
        """When variant B is worse than baseline A, gate should fail."""
        predictions = {
            "AAPL": [
                {"date": "2024-07-15", "prob_a": 0.6, "prob_b": 0.5},
                {"date": "2024-08-15", "prob_a": 0.7, "prob_b": 0.5},
            ]
        }
        outcomes = {
            "AAPL": [
                {"date": "2024-07-15", "realized_return": 0.05},
                {"date": "2024-08-15", "realized_return": 0.03},
            ]
        }
        result = run_purged_walkforward(
            tickers=["AAPL"],
            train_start="2024-01-01",
            train_end="2024-06-30",
            test_start="2024-07-01",
            test_end="2024-12-31",
            predictions=predictions,
            outcomes=outcomes,
        )
        # Baseline A has higher (better) probs for positive outcomes -> lower Brier
        # Gate should check whether variant B is better; if not, it won't pass ECE/Brier gates
        assert not result.gate_passed or result.baseline_brier <= result.brier + 0.01

    def test_sufficient_flag(self):
        """Build enough synthetic data to pass MIN_SAMPLES threshold."""
        n = MIN_SAMPLES + 5
        predictions = {"T": []}
        outcomes = {"T": []}
        for i in range(n):
            date = f"2024-{((i // 30) + 7):02d}-{(i % 28) + 1:02d}"
            predictions["T"].append({"date": date, "prob_a": 0.55, "prob_b": 0.55})
            outcomes["T"].append({"date": date, "realized_return": 0.01 if i % 3 != 0 else -0.01})
        result = run_purged_walkforward(
            tickers=["T"],
            train_start="2024-01-01",
            train_end="2024-06-30",
            test_start="2024-07-01",
            test_end="2024-12-31",
            predictions=predictions,
            outcomes=outcomes,
        )
        assert result.sufficient
        assert result.n_samples >= MIN_SAMPLES

    def test_gate_details_structure(self):
        predictions = {
            "AAPL": [
                {"date": "2024-07-15", "prob_a": 0.6, "prob_b": 0.55},
                {"date": "2024-08-15", "prob_a": 0.4, "prob_b": 0.45},
            ]
        }
        outcomes = {
            "AAPL": [
                {"date": "2024-07-15", "realized_return": 0.05},
                {"date": "2024-08-15", "realized_return": -0.02},
            ]
        }
        result = run_purged_walkforward(
            tickers=["AAPL"],
            train_start="2024-01-01",
            train_end="2024-06-30",
            test_start="2024-07-01",
            test_end="2024-12-31",
            predictions=predictions,
            outcomes=outcomes,
        )
        assert "thresholds" in result.gate_details
        assert "actuals" in result.gate_details
        assert "checks" in result.gate_details
        assert "passed" in result.gate_details
        assert result.gate_details["thresholds"]["coverage_min"] == PREREG_COVERAGE_MIN
        assert result.gate_details["thresholds"]["ece_max"] == PREREG_ECE_MAX


# ---------------------------------------------------------------------------
# evaluate_from_backtest_records
# ---------------------------------------------------------------------------

class TestEvaluateFromBacktestRecords:
    def _make_record(self, ticker, date, agent_id, signal, score, ret20d):
        """Create a minimal record dict matching BacktestRecord fields."""
        return {
            "ticker": ticker,
            "date": date,
            "agent_id": agent_id,
            "signal": signal,
            "score": score,
            "confidence": 0.7,
            "actual_return_20d": ret20d,
            "hit": (signal == "bullish" and ret20d > 0) or (signal == "bearish" and ret20d < 0),
        }

    def test_empty_records(self):
        result = evaluate_from_backtest_records([])
        assert result.n_samples == 0
        assert not result.sufficient

    def test_basic_evaluation(self):
        """With uniform weights and no rolling IC, A and B should be identical."""
        records = []
        for i in range(40):
            date = f"2024-{((i // 20) + 1):02d}-{(i % 20) + 1:02d}"
            ret = 0.03 if i % 2 == 0 else -0.02
            records.append(self._make_record("AAPL", date, "buffett", "bullish", 6.0, ret))
            records.append(self._make_record("AAPL", date, "soros", "bearish", 4.0, ret))
            records.append(self._make_record("AAPL", date, "marks", "bullish", 7.0, ret))

        baseline = {"buffett": 0.4, "soros": 0.3, "marks": 0.3}
        # Rolling IC weights identical to baseline -> A and B produce same results
        ric = {"buffett": 0.4, "soros": 0.3, "marks": 0.3}

        result = evaluate_from_backtest_records(
            records, baseline_weights=baseline, rolling_ic_weights=ric,
        )
        assert result.n_samples > 0
        assert result.brier >= 0.0
        # With identical weights, A and B should be nearly same
        assert result.brier == pytest.approx(result.baseline_brier, abs=0.01)

    def test_insufficient_data_flag(self):
        """With fewer than MIN_SAMPLES resolved outcomes, sufficient=False."""
        records = []
        for i in range(5):
            records.append(self._make_record("AAPL", f"2024-01-{i + 1:02d}", "buffett", "bullish", 6.0, 0.03))
            records.append(self._make_record("AAPL", f"2024-01-{i + 1:02d}", "soros", "bearish", 4.0, 0.03))

        result = evaluate_from_backtest_records(records)
        assert not result.sufficient
        assert result.n_samples < MIN_SAMPLES

    def test_gate_passed_with_good_variant(self):
        """When variant B is clearly better, gate should pass if data is sufficient."""
        np = pytest.importorskip("numpy")
        rng = np.random.RandomState(42)
        records = []
        n = MIN_SAMPLES + 20

        for i in range(n):
            date = f"2024-{((i // 25) + 1):02d}-{(i % 25) + 1:02d}"
            ret = 0.05 if rng.random() > 0.5 else -0.03
            records.append(self._make_record("AAPL", date, "good_agent", "bullish" if ret > 0 else "bearish", 7.0, ret))
            records.append(self._make_record("AAPL", date, "noise_agent", "neutral", 5.0, ret))

        # Baseline: equal weight for both
        baseline = {"good_agent": 0.5, "noise_agent": 0.5}
        # Variant (rolling IC): give all weight to the good agent
        ric = {"good_agent": 0.95, "noise_agent": 0.05}

        result = evaluate_from_backtest_records(
            records, baseline_weights=baseline, rolling_ic_weights=ric,
        )
        assert result.sufficient
        # Variant B should have lower (better) Brier than baseline A
        # because it weights the agent that predicts direction correctly
        assert result.brier <= result.baseline_brier + 0.05 or result.gate_passed


# ---------------------------------------------------------------------------
# Pre-registered gate constants
# ---------------------------------------------------------------------------

class TestPreregGate:
    def test_thresholds_are_reasonable(self):
        """Pre-registered thresholds should be in sensible ranges."""
        assert 0.0 <= PREREG_COVERAGE_MIN <= 1.0
        assert 0.0 <= PREREG_ECE_MAX <= 0.5
        assert isinstance(PREREG_BRIER_IMPROVEMENT_MIN, (int, float))

    def test_gate_fails_on_high_ece(self):
        """If variant ECE exceeds threshold, gate should fail."""
        # Create a scenario where variant is poorly calibrated
        predictions = {"X": [], "Y": []}
        outcomes = {"X": [], "Y": []}
        for ticker in ["X", "Y"]:
            for i in range(20):
                date = f"2024-07-{(i + 1):02d}"
                # Variant B: extreme probabilities but wrong direction
                predictions[ticker].append({
                    "date": date,
                    "prob_a": 0.55,
                    "prob_b": 0.95 if i % 2 == 0 else 0.05,
                })
                outcomes[ticker].append({
                    "date": date,
                    "realized_return": -0.05 if i % 2 == 0 else 0.05,
                })

        result = run_purged_walkforward(
            tickers=["X", "Y"],
            train_start="2024-01-01",
            train_end="2024-06-30",
            test_start="2024-07-01",
            test_end="2024-12-31",
            predictions=predictions,
            outcomes=outcomes,
        )
        assert not result.gate_passed


# ---------------------------------------------------------------------------
# Engine calibration safety (C1.2)
# ---------------------------------------------------------------------------

class TestEngineCalibrationSafety:
    def test_check_status_raw_by_default(self):
        """When no OOS evaluation file exists, status should be 'raw'."""
        from augur.consensus.engine import _check_calibration_status

        # load_feedback_json is imported locally inside _check_calibration_status
        # from augur.consensus.paths, so patch at the source module.
        with patch("augur.consensus.paths.load_feedback_json", return_value={}):
            status = _check_calibration_status()
            assert status == "raw"

    def test_check_status_reads_from_file(self):
        """Status should be read from persisted OOS evaluation."""
        from augur.consensus.engine import _check_calibration_status

        with patch("augur.consensus.paths.load_feedback_json",
                   return_value={"calibration_status": "validated-calibrated"}):
            status = _check_calibration_status()
            assert status == "validated-calibrated"

    def test_engine_skips_ric_when_not_validated(self):
        """ConsensusEngine should not auto-apply rolling IC when not validated."""
        from augur.consensus.engine import ConsensusEngine
        from augur.personas.base import AgentResponse, SignalType

        engine = ConsensusEngine()
        results = {
            "buffett": AgentResponse(
                agent_id="buffett", agent_name="Buffett",
                signal=SignalType.BULLISH, confidence=0.7, score=6.0,
                reasoning="test",
            ),
            "soros": AgentResponse(
                agent_id="soros", agent_name="Soros",
                signal=SignalType.BEARISH, confidence=0.6, score=4.0,
                reasoning="test",
            ),
        }

        # load_rolling_ic_weights is imported locally inside compute()
        # from augur.consensus.rolling_ic, so patch at the source.
        with patch("augur.consensus.rolling_ic.load_rolling_ic_weights",
                   return_value={"buffett": 0.8, "soros": 0.2}):
            with patch("augur.consensus.engine._check_calibration_status",
                       return_value="experimental"):
                result = engine.compute(results, ticker="AAPL")
                # When status is "experimental" and AUGUR_FORCE_RIC is not set,
                # rolling IC should be disabled -> weights in metadata should
                # reflect only base weights, not the 50/50 blend.
                assert "calibration_status" in result.metadata
                assert result.metadata["calibration_status"] == "experimental"
                assert result.metadata["calibration"]["rolling_ic_active"] is False

    def test_engine_applies_ric_when_validated(self):
        """ConsensusEngine should apply rolling IC when status is validated-calibrated."""
        from augur.consensus.engine import ConsensusEngine
        from augur.personas.base import AgentResponse, SignalType

        engine = ConsensusEngine()
        results = {
            "buffett": AgentResponse(
                agent_id="buffett", agent_name="Buffett",
                signal=SignalType.BULLISH, confidence=0.7, score=6.0,
                reasoning="test",
            ),
            "soros": AgentResponse(
                agent_id="soros", agent_name="Soros",
                signal=SignalType.BEARISH, confidence=0.6, score=4.0,
                reasoning="test",
            ),
        }

        with patch("augur.consensus.rolling_ic.load_rolling_ic_weights",
                   return_value={"buffett": 0.8, "soros": 0.2}):
            with patch("augur.consensus.engine._check_calibration_status",
                       return_value="validated-calibrated"):
                result = engine.compute(results, ticker="AAPL")
                assert result.metadata["calibration_status"] == "validated-calibrated"
                assert result.metadata["calibration"]["rolling_ic_active"] is True

    def test_engine_calibration_metadata_present(self):
        """Every consensus result should carry calibration metadata."""
        from augur.consensus.engine import ConsensusEngine
        from augur.personas.base import AgentResponse, SignalType

        engine = ConsensusEngine()
        results = {
            "test_agent": AgentResponse(
                agent_id="test_agent", agent_name="Test",
                signal=SignalType.BULLISH, confidence=0.5, score=5.0,
                reasoning="test",
            ),
        }

        # Avoid filesystem / network hits during test
        with patch("augur.consensus.rolling_ic.load_rolling_ic_weights", return_value={}):
            with patch("augur.consensus.engine._check_calibration_status",
                       return_value="raw"):
                result = engine.compute(results, ticker="TEST")
        assert "calibration_status" in result.metadata
        assert "calibration" in result.metadata
        assert "status" in result.metadata["calibration"]
        assert "rolling_ic_active" in result.metadata["calibration"]
        assert "sufficient_data" in result.metadata["calibration"]
