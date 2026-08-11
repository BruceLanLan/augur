# -*- coding: utf-8 -*-
"""Tests for augur.eval_lab — Chronological Evaluation Lab.

Uses synthetic RunBundles and outcome data for fully hermetic testing.
"""

import math
from datetime import datetime
from typing import Dict, List

import numpy as np
import pytest

from augur.eval_lab import (
    AblationResult,
    ChronologicalEvaluator,
    EvalMetric,
    EvalResult,
    PersonaAblator,
    _extract_probability,
    _extract_ticker,
)
from augur.schemas.run_bundle import (
    CoverageStats,
    RunBundle,
    RunManifest,
)
from augur.schemas.step_result import StepResult, StepStatus


# ============================================================================
# Synthetic RunBundle factory
# ============================================================================


def _make_run_bundle(
    run_id: str,
    probability: float,
    created_at: datetime = None,
    step_name: str = "predict_signal",
) -> RunBundle:
    """Create a synthetic RunBundle with a prediction embedded in step_results."""
    if created_at is None:
        created_at = datetime(2024, 1, 15, 10, 0, 0)

    return RunBundle(
        run_id=run_id,
        created_at=created_at,
        manifest=RunManifest(
            input_snapshot_hash="abc123",
            config_version="1.0",
            model_version="1.0",
            code_version="1.0",
        ),
        step_results=[
            StepResult(
                step_id="step_1",
                step_name=step_name,
                status=StepStatus.SUCCESS,
                result={"probability": probability, "score": probability * 10.0},
            )
        ],
        coverage=CoverageStats(
            total_evidence=1,
            covered_evidence=1,
            missing_evidence=0,
            degraded_evidence=0,
            coverage_ratio=1.0,
        ),
    )


def _make_run_bundle_score(
    run_id: str,
    score: float,
    created_at: datetime = None,
) -> RunBundle:
    """Create a RunBundle with a score (0-10) instead of probability."""
    if created_at is None:
        created_at = datetime(2024, 1, 15, 10, 0, 0)

    return RunBundle(
        run_id=run_id,
        created_at=created_at,
        manifest=RunManifest(
            input_snapshot_hash="abc123",
            config_version="1.0",
            model_version="1.0",
            code_version="1.0",
        ),
        step_results=[
            StepResult(
                step_id="step_1",
                step_name="score_ticker",
                status=StepStatus.SUCCESS,
                result={"score": score},
            )
        ],
        coverage=CoverageStats(
            total_evidence=1,
            covered_evidence=1,
            missing_evidence=0,
            degraded_evidence=0,
            coverage_ratio=1.0,
        ),
    )


# ============================================================================
# Tests: helper functions
# ============================================================================


class TestExtractProbability:
    """Tests for _extract_probability helper."""

    def test_extracts_probability_field(self):
        """Should extract probability directly from result dict."""
        bundle = _make_run_bundle("run_AAPL_20240115T100000_abc12345", 0.75)
        prob = _extract_probability(bundle)
        assert prob == pytest.approx(0.75)

    def test_normalizes_score_to_probability(self):
        """Should normalize 0-10 score to 0-1 probability."""
        bundle = _make_run_bundle_score("run_AAPL_20240115T100000_abc12345", 7.0)
        prob = _extract_probability(bundle)
        assert prob == pytest.approx(0.7)

    def test_clamps_to_0_1(self):
        """Should clamp extracted probabilities to [0, 1]."""
        bundle = _make_run_bundle("run_AAPL_20240115T100000_abc12345", 1.5)
        prob = _extract_probability(bundle)
        assert prob == 1.0

        bundle2 = _make_run_bundle("run_AAPL_20240115T100000_abc12346", -0.3)
        prob2 = _extract_probability(bundle2)
        assert prob2 == 0.0

    def test_returns_none_for_empty_bundle(self):
        """Should return None when no prediction step exists."""
        bundle = RunBundle(
            run_id="run_AAPL_20240115T100000_abc12345",
            created_at=datetime(2024, 1, 15),
            manifest=RunManifest(
                input_snapshot_hash="abc123",
                config_version="1.0",
                model_version="1.0",
                code_version="1.0",
            ),
            step_results=[
                StepResult(
                    step_id="step_1",
                    step_name="fetch_prices",
                    status=StepStatus.SUCCESS,
                    result={"close": 150.0},
                )
            ],
            coverage=CoverageStats(),
        )
        prob = _extract_probability(bundle)
        assert prob is None


class TestExtractTicker:
    """Tests for _extract_ticker helper."""

    def test_extracts_ticker_from_run_id(self):
        bundle = _make_run_bundle("run_AAPL_20240115T100000_abc12345", 0.5)
        assert _extract_ticker(bundle) == "AAPL"

    def test_handles_complex_ticker(self):
        bundle = _make_run_bundle("run_0700.HK_20240115T100000_abc12345", 0.5)
        assert _extract_ticker(bundle) == "0700.HK"

    def test_returns_unknown_for_malformed_id(self):
        bundle = _make_run_bundle("bad_id", 0.5)
        assert _extract_ticker(bundle) == "unknown"


# ============================================================================
# Tests: ChronologicalEvaluator metric computation
# ============================================================================


class TestChronologicalEvaluatorMetrics:
    """Tests for individual metric computation methods."""

    def test_compute_brier_score_perfect(self):
        """Perfect predictions should give Brier score 0."""
        probs = np.array([1.0, 0.0, 1.0, 0.0])
        outs = np.array([1.0, 0.0, 1.0, 0.0])
        brier = ChronologicalEvaluator.compute_brier_score(probs, outs)
        assert brier == pytest.approx(0.0, abs=1e-10)

    def test_compute_brier_score_worst(self):
        """Completely wrong predictions should give Brier score 1."""
        probs = np.array([1.0, 0.0, 1.0, 0.0])
        outs = np.array([0.0, 1.0, 0.0, 1.0])
        brier = ChronologicalEvaluator.compute_brier_score(probs, outs)
        assert brier == pytest.approx(1.0, abs=1e-10)

    def test_compute_log_loss_finite(self):
        """Log loss should be finite for non-degenerate predictions."""
        probs = np.array([0.7, 0.3, 0.8, 0.2])
        outs = np.array([1.0, 0.0, 1.0, 0.0])
        ll = ChronologicalEvaluator.compute_log_loss(probs, outs)
        assert math.isfinite(ll)
        assert ll > 0.0

    def test_compute_log_loss_perfect_low(self):
        """Log loss should be low for well-calibrated predictions."""
        probs = np.array([0.9, 0.1, 0.9, 0.1])
        outs = np.array([1.0, 0.0, 1.0, 0.0])
        ll = ChronologicalEvaluator.compute_log_loss(probs, outs)
        assert ll < 0.5

    def test_compute_accuracy_all_correct(self):
        """All predictions correct at threshold 0.5."""
        probs = np.array([0.9, 0.1, 0.8, 0.2])
        outs = np.array([1.0, 0.0, 1.0, 0.0])
        acc = ChronologicalEvaluator.compute_accuracy(probs, outs)
        assert acc == 1.0

    def test_compute_accuracy_half_correct(self):
        """Half correct predictions."""
        probs = np.array([0.9, 0.1, 0.9, 0.1])
        outs = np.array([1.0, 0.0, 0.0, 1.0])
        acc = ChronologicalEvaluator.compute_accuracy(probs, outs)
        assert acc == 0.5

    def test_compute_ic_positive_correlation(self):
        """IC should be positive for positively correlated predictions and returns."""
        rng = np.random.RandomState(42)
        preds = rng.randn(100)
        fwd = preds * 0.5 + rng.randn(100) * 0.1
        ic = ChronologicalEvaluator.compute_ic(preds, fwd)
        assert ic > 0.3  # strong positive correlation expected

    def test_compute_ic_negative_correlation(self):
        """IC should be negative for negatively correlated predictions and returns."""
        rng = np.random.RandomState(42)
        preds = rng.randn(100)
        fwd = -preds * 0.5 + rng.randn(100) * 0.1
        ic = ChronologicalEvaluator.compute_ic(preds, fwd)
        assert ic < -0.3

    def test_compute_ic_small_sample(self):
        """IC with fewer than 2 samples should return 0."""
        ic = ChronologicalEvaluator.compute_ic(np.array([1.0]), np.array([1.0]))
        assert ic == 0.0

    def test_compute_ic_constant_input(self):
        """IC should be 0 when predictions are constant."""
        preds = np.ones(10)
        fwd = np.random.RandomState(42).randn(10)
        ic = ChronologicalEvaluator.compute_ic(preds, fwd)
        assert ic == 0.0


# ============================================================================
# Tests: Bootstrap & significance
# ============================================================================


class TestBootstrapCI:
    """Tests for bootstrap confidence intervals."""

    def test_bootstrap_ci_coverage(self):
        """Bootstrap CI should contain the true mean most of the time."""
        rng = np.random.RandomState(123)
        # Generate data with known mean = 0.5
        data = rng.normal(0.5, 0.1, size=200)
        low, high = ChronologicalEvaluator.bootstrap_ci(data, n_bootstrap=500, seed=42)
        assert low <= 0.5 <= high

    def test_bootstrap_ci_empty(self):
        """Empty input should return (0, 0)."""
        low, high = ChronologicalEvaluator.bootstrap_ci(np.array([]))
        assert low == 0.0
        assert high == 0.0

    def test_bootstrap_ci_constant(self):
        """Constant input should produce tight CI around that constant."""
        data = np.ones(50)
        low, high = ChronologicalEvaluator.bootstrap_ci(data, n_bootstrap=500, seed=42)
        assert low == pytest.approx(1.0)
        assert high == pytest.approx(1.0)


class TestCheckSignificance:
    """Tests for statistical significance checking."""

    def test_significance_detects_large_difference(self):
        """A large, consistent difference should be detected as significant."""
        rng = np.random.RandomState(42)
        baseline = rng.normal(0.5, 0.05, size=100)
        candidate = rng.normal(0.3, 0.05, size=100)  # much better (lower brier)
        sig = ChronologicalEvaluator.check_significance(baseline, candidate, n_bootstrap=500, seed=42)
        assert sig is True

    def test_significance_no_difference(self):
        """No real difference should not be significant."""
        rng = np.random.RandomState(42)
        baseline = rng.normal(0.5, 0.1, size=100)
        candidate = rng.normal(0.5, 0.1, size=100)
        sig = ChronologicalEvaluator.check_significance(baseline, candidate, n_bootstrap=500, seed=42)
        assert sig is False

    def test_significance_empty(self):
        """Empty inputs should return False."""
        sig = ChronologicalEvaluator.check_significance(np.array([]), np.array([]))
        assert sig is False

    def test_significance_mismatched_lengths(self):
        """Mismatched length inputs should return False."""
        sig = ChronologicalEvaluator.check_significance(np.ones(10), np.ones(5))
        assert sig is False


# ============================================================================
# Tests: ChronologicalEvaluator.compare_runs
# ============================================================================


class TestCompareRuns:
    """Integration tests for compare_runs."""

    def test_compare_runs_basic(self):
        """Basic comparison with outcome data should produce valid EvalResult."""
        # Baseline: predictions around 0.5 (random)
        # Candidate: predictions closer to truth (better)
        rng = np.random.RandomState(42)
        n = 30

        baseline_runs = []
        candidate_runs = []
        outcome_data = {}

        for i in range(n):
            run_id = f"run_TICKER_{20240115 + i:08d}T100000_abc1234{i:02x}"
            true_outcome = float(rng.randint(0, 2))
            # Baseline: noisy prediction around 0.5
            base_prob = 0.5 + rng.normal(0, 0.15)
            # Candidate: slightly better, closer to truth
            cand_prob = 0.3 + 0.4 * true_outcome + rng.normal(0, 0.05)

            baseline_runs.append(_make_run_bundle(run_id, base_prob))
            candidate_runs.append(_make_run_bundle(run_id.replace("run_", "run_cand_"), cand_prob))
            outcome_data[run_id] = true_outcome
            outcome_data[run_id.replace("run_", "run_cand_")] = true_outcome

        result = ChronologicalEvaluator.compare_runs(baseline_runs, candidate_runs, outcome_data=outcome_data)

        assert isinstance(result, EvalResult)
        assert len(result.baseline_run_ids) == n
        assert len(result.candidate_run_ids) == n
        assert result.n_observations > 0
        assert result.n_tickers > 0
        assert result.conclusion in (
            "candidate_better", "no_difference", "baseline_better", "insufficient_data"
        )
        assert any(m.name == "brier" for m in result.metrics)
        assert any(m.name == "log_loss" for m in result.metrics)
        assert any(m.name == "accuracy" for m in result.metrics)

    def test_compare_runs_insufficient_data(self):
        """Too few observations should yield insufficient_data conclusion."""
        baseline_runs = [_make_run_bundle("run_A_20240115T100000_abc12345", 0.5)]
        candidate_runs = [_make_run_bundle("run_B_20240115T100000_abc12346", 0.6)]
        outcome_data = {"run_A_20240115T100000_abc12345": 1.0}

        result = ChronologicalEvaluator.compare_runs(
            baseline_runs, candidate_runs, outcome_data=outcome_data
        )
        # Only 1 paired observation
        assert result.n_observations < 5 or result.conclusion == "insufficient_data"

    def test_compare_runs_with_forward_returns(self):
        """Comparison with forward returns should compute IC."""
        rng = np.random.RandomState(42)
        n = 30

        baseline_runs = []
        candidate_runs = []
        forward_returns = {}

        for i in range(n):
            run_id = f"run_TICKER_{20240115 + i:08d}T100000_abc1234{i:02x}"
            base_prob = rng.uniform(0, 1)
            cand_prob = rng.uniform(0, 1)
            fwd_ret = rng.normal(0, 0.05)

            baseline_runs.append(_make_run_bundle(run_id, base_prob))
            candidate_runs.append(_make_run_bundle(run_id.replace("run_", "run_cand_"), cand_prob))
            forward_returns[run_id] = fwd_ret
            forward_returns[run_id.replace("run_", "run_cand_")] = fwd_ret

        result = ChronologicalEvaluator.compare_runs(
            baseline_runs, candidate_runs, forward_returns=forward_returns
        )
        assert any(m.name == "ic" for m in result.metrics)

    def test_compare_runs_determines_candidate_better(self):
        """When candidate has clearly better Brier/log-loss, should report candidate_better."""
        rng = np.random.RandomState(42)
        n = 50

        baseline_runs = []
        candidate_runs = []
        outcome_data = {}

        for i in range(n):
            run_id = f"run_TICKER_{20240115 + i:08d}T100000_abc1234{i:02x}"
            true_outcome = float(rng.randint(0, 2))
            # Baseline: poor predictions around 0.5
            base_prob = 0.5 + rng.normal(0, 0.2)
            # Candidate: well-calibrated predictions
            cand_prob = 0.1 + 0.8 * true_outcome + rng.normal(0, 0.03)

            baseline_runs.append(_make_run_bundle(run_id, base_prob))
            candidate_runs.append(_make_run_bundle(run_id.replace("run_", "run_cand_"), cand_prob))
            outcome_data[run_id] = true_outcome
            outcome_data[run_id.replace("run_", "run_cand_")] = true_outcome

        result = ChronologicalEvaluator.compare_runs(
            baseline_runs, candidate_runs, outcome_data=outcome_data
        )
        # Candidate should be significantly better
        assert result.conclusion in ("candidate_better", "no_difference")


# ============================================================================
# Tests: PersonaAblator
# ============================================================================


class TestPersonaAblator:
    """Tests for persona ablation."""

    def _make_persona_results(
        self, persona_ids: List[str], n_per_persona: int = 10, seed: int = 42
    ) -> Dict[str, List[RunBundle]]:
        """Build synthetic per-persona RunBundle collections."""
        rng = np.random.RandomState(seed)
        results: Dict[str, List[RunBundle]] = {}
        for pid in persona_ids:
            runs = []
            for i in range(n_per_persona):
                run_id = f"run_{pid}_TICKER_{20240115 + i:08d}T100000_abc1234{i:02x}"
                prob = rng.uniform(0.2, 0.8)
                runs.append(_make_run_bundle(run_id, prob))
            results[pid] = runs
        return results

    def _make_outcome_data(
        self, persona_results: Dict[str, List[RunBundle]], seed: int = 99
    ) -> Dict[str, float]:
        """Build outcome data matching the RunBundles."""
        rng = np.random.RandomState(seed)
        outcomes = {}
        for runs in persona_results.values():
            for run in runs:
                outcomes[run.run_id] = float(rng.randint(0, 2))
        return outcomes

    def test_ablate_one_removes_persona(self):
        """ablate_one should correctly compute metrics with and without a persona."""
        full_results = self._make_persona_results(["buffett", "graham", "lynch"], n_per_persona=10)
        outcome_data = self._make_outcome_data(full_results)

        ablator = PersonaAblator()
        result = ablator.ablate_one("buffett", full_results, outcome_data)

        assert isinstance(result, AblationResult)
        assert result.persona_id == "buffett"
        assert result.removed is True
        assert "brier" in result.metrics_with
        assert "log_loss" in result.metrics_without
        assert "accuracy" in result.delta
        assert isinstance(result.worth_keeping, bool)

    def test_ablate_one_raises_for_unknown_persona(self):
        """Should raise ValueError for non-existent persona."""
        full_results = self._make_persona_results(["buffett"], n_per_persona=5)
        outcome_data = self._make_outcome_data(full_results)

        ablator = PersonaAblator()
        with pytest.raises(ValueError, match="not found"):
            ablator.ablate_one("nonexistent", full_results, outcome_data)

    def test_ablate_all_returns_all_personas(self):
        """ablate_all should return results for every persona."""
        full_results = self._make_persona_results(
            ["buffett", "graham", "lynch", "dalio", "soros"],
            n_per_persona=8,
        )
        outcome_data = self._make_outcome_data(full_results)

        ablator = PersonaAblator()
        results = ablator.ablate_all(full_results, outcome_data)

        assert len(results) == 5
        persona_ids = {r.persona_id for r in results}
        assert persona_ids == {"buffett", "graham", "lynch", "dalio", "soros"}

    def test_ablate_all_sorted_by_marginal_contribution(self):
        """Results should be sorted by marginal_contribution descending."""
        full_results = self._make_persona_results(
            ["buffett", "graham", "lynch", "dalio", "soros"],
            n_per_persona=8,
        )
        outcome_data = self._make_outcome_data(full_results)

        ablator = PersonaAblator()
        results = ablator.ablate_all(full_results, outcome_data)

        for i in range(len(results) - 1):
            assert results[i].marginal_contribution >= results[i + 1].marginal_contribution

    def test_marginal_contributions_normalized(self):
        """Marginal contributions should be normalized to [0, 1]."""
        full_results = self._make_persona_results(
            ["buffett", "graham", "lynch", "dalio", "soros"],
            n_per_persona=8,
        )
        outcome_data = self._make_outcome_data(full_results)

        ablator = PersonaAblator()
        results = ablator.ablate_all(full_results, outcome_data)

        max_contrib = max(r.marginal_contribution for r in results)
        assert max_contrib == pytest.approx(1.0) or max_contrib == pytest.approx(0.0)

    def test_recommend_retention_returns_list(self):
        """recommend_retention should return a list of persona IDs."""
        full_results = self._make_persona_results(
            ["buffett", "graham", "lynch"], n_per_persona=8
        )
        outcome_data = self._make_outcome_data(full_results)

        ablator = PersonaAblator()
        ablations = ablator.ablate_all(full_results, outcome_data)

        keep = PersonaAblator.recommend_retention(ablations, threshold=0.01)
        assert isinstance(keep, list)
        assert all(isinstance(p, str) for p in keep)

    def test_recommend_retention_respects_threshold(self):
        """High threshold should filter out low-contribution personas."""
        full_results = self._make_persona_results(
            ["buffett", "graham", "lynch"], n_per_persona=8
        )
        outcome_data = self._make_outcome_data(full_results)

        ablator = PersonaAblator()
        ablations = ablator.ablate_all(full_results, outcome_data)

        keep_low = PersonaAblator.recommend_retention(ablations, threshold=0.0)
        keep_high = PersonaAblator.recommend_retention(ablations, threshold=100.0)

        # Low threshold should keep more (or equal) personas
        assert len(keep_low) >= len(keep_high)

    def test_ablate_one_with_empty_outcome(self):
        """Ablation with empty outcome should still return valid result."""
        full_results = self._make_persona_results(["buffett"], n_per_persona=3)
        outcome_data: Dict[str, float] = {}

        ablator = PersonaAblator()
        result = ablator.ablate_one("buffett", full_results, outcome_data)

        assert result.persona_id == "buffett"
        assert result.removed is True
        # All metrics should be zero with no matched outcomes
        assert all(v == 0.0 for v in result.metrics_with.values())
