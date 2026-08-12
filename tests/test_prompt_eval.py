# -*- coding: utf-8 -*-
"""Tests for augur.prompt_eval — Prompt/Model Evaluation + Chronological Factor Lab.

Covers F03 (PromptEvaluator) and F04 (FactorLab) with synthetic data.
"""

import numpy as np
import pytest

from augur.prompt_eval import (
    EvalRun,
    FactorLab,
    FactorPerformance,
    PromptComparison,
    PromptEvaluator,
    PromptVariant,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_variant(variant_id: str, model: str = "test-model") -> PromptVariant:
    """Create a minimal PromptVariant for testing."""
    return PromptVariant(
        variant_id=variant_id,
        prompt_text=f"Test prompt for {variant_id}",
        model=model,
        description=f"Variant {variant_id}",
    )


def _make_eval_run(
    variant_id: str,
    metrics: dict,
    model: str = "test-model",
    n_runs: int = 10,
) -> EvalRun:
    """Create an EvalRun with synthetic metrics."""
    return EvalRun(
        variant=_make_variant(variant_id, model),
        run_ids=[f"run_{variant_id}_{i:03d}" for i in range(n_runs)],
        metrics=metrics,
    )


# ============================================================================
# F03 — PromptEvaluator.compare
# ============================================================================


class TestPromptEvaluatorCompare:
    """Tests for PromptEvaluator.compare."""

    def test_candidate_wins_on_accuracy(self):
        """When candidate has higher accuracy, it should be declared winner."""
        baseline = _make_eval_run("v1-baseline", {"brier": 0.25, "accuracy": 0.60})
        candidate = _make_eval_run("v2-improved", {"brier": 0.15, "accuracy": 0.80})

        result = PromptEvaluator.compare(baseline, candidate)

        assert isinstance(result, PromptComparison)
        assert result.winner == "candidate"
        assert "brier" in result.significant_delta
        assert "accuracy" in result.significant_delta

    def test_baseline_wins_when_candidate_worse(self):
        """When candidate has worse metrics, baseline should win."""
        baseline = _make_eval_run("v1-good", {"brier": 0.10, "accuracy": 0.90})
        candidate = _make_eval_run("v2-regressed", {"brier": 0.35, "accuracy": 0.55})

        result = PromptEvaluator.compare(baseline, candidate)

        assert result.winner == "baseline"

    def test_tie_when_metrics_equal(self):
        """Equal metrics should produce a tie."""
        baseline = _make_eval_run("v1", {"brier": 0.20, "accuracy": 0.75})
        candidate = _make_eval_run("v2", {"brier": 0.20, "accuracy": 0.75})

        result = PromptEvaluator.compare(baseline, candidate)

        assert result.winner == "tie"
        for _metric_name, (_p_val, sig) in result.significant_delta.items():
            assert sig is False

    def test_compare_with_outcome_data(self):
        """With outcome_data, bootstrap significance should run."""
        baseline = _make_eval_run("v1", {"brier": 0.30, "accuracy": 0.55})
        candidate = _make_eval_run("v2", {"brier": 0.15, "accuracy": 0.75})
        outcome = np.array([0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0])

        result = PromptEvaluator.compare(baseline, candidate, outcome_data=outcome)

        assert isinstance(result, PromptComparison)
        assert result.winner in ("baseline", "candidate", "tie")
        assert len(result.significant_delta) > 0
        for p_val, sig in result.significant_delta.values():
            assert isinstance(p_val, float)
            assert isinstance(sig, bool)

    def test_compare_handles_missing_metrics(self):
        """When metrics keys differ between baseline and candidate."""
        baseline = _make_eval_run("v1", {"brier": 0.20})
        candidate = _make_eval_run("v2", {"accuracy": 0.80, "ic": 0.05})

        result = PromptEvaluator.compare(baseline, candidate)

        assert "brier" in result.significant_delta
        assert "accuracy" in result.significant_delta
        assert "ic" in result.significant_delta

    def test_compare_generates_comparison_id(self):
        """Each comparison should have a unique ID."""
        baseline = _make_eval_run("v1", {"brier": 0.20})
        candidate = _make_eval_run("v2", {"brier": 0.18})

        r1 = PromptEvaluator.compare(baseline, candidate)
        r2 = PromptEvaluator.compare(baseline, candidate)

        assert r1.comparison_id != ""
        assert r2.comparison_id != ""
        assert r1.comparison_id != r2.comparison_id


# ============================================================================
# F03 — PromptEvaluator.check_factual_degradation
# ============================================================================


class TestCheckFactualDegradation:
    """Tests for PromptEvaluator.check_factual_degradation."""

    def test_detects_degradation(self):
        """When candidate has fewer factual claims, degradation > 0."""
        baseline = [
            {"claim": "A is true", "is_factual": True},
            {"claim": "B is true", "is_factual": True},
            {"claim": "C is true", "is_factual": True},
        ]
        candidate = [
            {"claim": "A is true", "is_factual": True},
            {"claim": "B is false", "is_factual": False},
            {"claim": "C is true", "is_factual": True},
        ]

        result = PromptEvaluator.check_factual_degradation(baseline, candidate)

        assert result["baseline_accuracy"] == 1.0
        assert result["candidate_accuracy"] == pytest.approx(2.0 / 3.0, abs=0.01)
        assert result["degradation"] > 0
        assert result["new_errors"] == 1
        assert result["fixed_errors"] == 0

    def test_detects_improvement(self):
        """When candidate fixes errors, result should show improvement."""
        baseline = [
            {"claim": "X", "is_factual": False},
            {"claim": "Y", "is_factual": True},
        ]
        candidate = [
            {"claim": "X", "is_factual": True},
            {"claim": "Y", "is_factual": True},
        ]

        result = PromptEvaluator.check_factual_degradation(baseline, candidate)

        assert result["degradation"] < 0
        assert result["new_errors"] == 0
        assert result["fixed_errors"] == 1

    def test_empty_claims_returns_zeros(self):
        """Empty claim lists should return zero metrics without error."""
        result = PromptEvaluator.check_factual_degradation([], [])

        assert result["baseline_accuracy"] == 0.0
        assert result["candidate_accuracy"] == 0.0
        assert result["degradation"] == 0.0
        assert result["baseline_n"] == 0
        assert result["candidate_n"] == 0

    def test_unequal_lengths_handled(self):
        """Claims of different lengths should not crash."""
        baseline = [{"claim": "A", "is_factual": True}] * 5
        candidate = [{"claim": "A", "is_factual": True}] * 3

        result = PromptEvaluator.check_factual_degradation(baseline, candidate)

        assert result["baseline_n"] == 5
        assert result["candidate_n"] == 3
        assert isinstance(result["new_errors"], int)
        assert isinstance(result["fixed_errors"], int)


# ============================================================================
# F04 — FactorLab.evaluate_factors
# ============================================================================


class TestFactorLabEvaluateFactors:
    """Tests for FactorLab.evaluate_factors."""

    def test_basic_factor_evaluation(self):
        """Single factor with positive IC should have positive ic_mean."""
        rng = np.random.RandomState(42)
        n = 100
        score = rng.randn(n)
        fwd = score * 0.3 + rng.randn(n) * 0.1

        results = FactorLab.evaluate_factors({"momentum": score}, fwd)

        assert len(results) == 1
        r = results[0]
        assert isinstance(r, FactorPerformance)
        assert r.factor_name == "momentum"
        assert r.ic_mean > 0.1
        assert r.periods > 0

    def test_significant_factor_detected(self):
        """A factor with consistent IC should be marked significant."""
        rng = np.random.RandomState(42)
        n = 200
        score = rng.randn(n)
        fwd = score * 0.4 + rng.randn(n) * 0.05

        results = FactorLab.evaluate_factors(
            {"strong_factor": score}, fwd, periods=20
        )

        assert results[0].significant is True
        assert results[0].p_value < 0.05

    def test_multiple_factors_sorted_by_ic(self):
        """Results should be sorted by absolute IC mean descending."""
        rng = np.random.RandomState(42)
        n = 100
        scores = {
            "weak": rng.randn(n) * 0.1 + rng.randn(n),
            "strong": rng.randn(n) * 0.5 + rng.randn(n) * 0.1,
            "medium": rng.randn(n) * 0.3 + rng.randn(n) * 0.1,
        }
        fwd = rng.randn(n)

        results = FactorLab.evaluate_factors(scores, fwd)

        assert len(results) == 3
        for i in range(len(results) - 1):
            assert abs(results[i].ic_mean) >= abs(results[i + 1].ic_mean)

    def test_2d_cross_sectional_scores(self):
        """2-D factor scores (n_periods × n_assets) should compute per-period IC."""
        rng = np.random.RandomState(42)
        n_periods, n_assets = 50, 20
        scores_2d = rng.randn(n_periods, n_assets)
        fwd_2d = scores_2d * 0.3 + rng.randn(n_periods, n_assets) * 0.1

        results = FactorLab.evaluate_factors({"cs_factor": scores_2d}, fwd_2d)

        assert len(results) == 1
        assert results[0].periods == n_periods

    def test_insufficient_data_returns_safe_defaults(self):
        """Single observation should return safe defaults, not crash."""
        score = np.array([1.0])
        fwd = np.array([0.02])

        results = FactorLab.evaluate_factors({"tiny": score}, fwd)

        assert results[0].ic_std == 0.0
        assert results[0].significant is False
        assert results[0].p_value == 1.0


# ============================================================================
# F04 — FactorLab.rolling_ic
# ============================================================================


class TestFactorLabRollingIC:
    """Tests for FactorLab.rolling_ic."""

    def test_rolling_ic_output_length(self):
        """Rolling IC should produce n - window + 1 values."""
        rng = np.random.RandomState(42)
        n = 100
        window = 20
        scores = rng.randn(n)
        returns = scores * 0.2 + rng.randn(n) * 0.1

        rolling = FactorLab.rolling_ic(scores, returns, window)

        assert len(rolling) == n - window + 1
        assert all(isinstance(v, float) for v in rolling)

    def test_rolling_ic_minimum_window(self):
        """Window smaller than 2 should be clamped to 2."""
        rng = np.random.RandomState(42)
        scores = rng.randn(10)
        returns = rng.randn(10)

        rolling = FactorLab.rolling_ic(scores, returns, window=1)

        assert len(rolling) == 9

    def test_rolling_ic_all_nan_handled(self):
        """Constant scores should produce finite (zero) IC values."""
        scores = np.ones(30)
        returns = np.random.RandomState(42).randn(30)

        rolling = FactorLab.rolling_ic(scores, returns, window=10)

        assert len(rolling) == 30 - 10 + 1
        assert all(np.isfinite(v) for v in rolling)


# ============================================================================
# F04 — FactorLab.factor_correlation
# ============================================================================


class TestFactorLabFactorCorrelation:
    """Tests for FactorLab.factor_correlation."""

    def test_correlation_matrix_shape(self):
        """Matrix should be symmetric with 1.0 on diagonal."""
        rng = np.random.RandomState(42)
        n = 50
        scores = {
            "factor_a": rng.randn(n),
            "factor_b": rng.randn(n),
            "factor_c": rng.randn(n),
        }

        corr = FactorLab.factor_correlation(scores)

        assert corr["labels"] == ["factor_a", "factor_b", "factor_c"]
        matrix = corr["matrix"]
        assert len(matrix) == 3

        for name in corr["labels"]:
            assert matrix[name][name] == 1.0

        for i in corr["labels"]:
            for j in corr["labels"]:
                assert matrix[i][j] == pytest.approx(matrix[j][i])

    def test_single_factor_returns_empty_matrix(self):
        """Single factor should produce empty matrix with mean_abs_corr=0."""
        scores = {"only": np.random.RandomState(42).randn(30)}

        corr = FactorLab.factor_correlation(scores)

        assert corr["labels"] == ["only"]
        assert corr["matrix"] == {}
        assert corr["mean_abs_corr"] == 0.0

    def test_highly_correlated_factors(self):
        """Nearly identical factors should have correlation close to 1.0."""
        rng = np.random.RandomState(42)
        base = rng.randn(100)
        scores = {
            "factor_x": base + rng.randn(100) * 0.01,
            "factor_y": base + rng.randn(100) * 0.01,
        }

        corr = FactorLab.factor_correlation(scores)

        assert corr["matrix"]["factor_x"]["factor_y"] > 0.95
        assert corr["mean_abs_corr"] > 0.9
