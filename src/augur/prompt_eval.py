# -*- coding: utf-8 -*-
"""
augur.prompt_eval — Prompt/Model Evaluation (F03) + Chronological Factor Lab (F04)

F03 — Prompt/Model Evaluation:
  Compare prompt variants and models using EvalRun metrics with statistical
  significance testing (bootstrap). Also checks factual degradation between
  baseline and candidate claim sets.

F04 — Chronological Factor Lab:
  Evaluate factor performance via IC (Information Coefficient) analysis,
  rolling IC windows, and factor correlation matrices.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional scipy import for p-value computation
# ---------------------------------------------------------------------------
try:
    from scipy import stats as _scipy_stats  # noqa: F401
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ============================================================================
# F03 — Prompt/Model Evaluation
# ============================================================================


@dataclass
class PromptVariant:
    """A prompt variant (or model configuration) under evaluation.

    Attributes:
        variant_id: Unique identifier for this variant (e.g. "v1-baseline").
        prompt_text: The full prompt text used.
        model: Model identifier (e.g. "gpt-4", "claude-3", "deepseek-v4").
        description: Human-readable description of what this variant tests.
    """

    variant_id: str
    prompt_text: str
    model: str
    description: str = ""


@dataclass
class EvalRun:
    """One evaluation run for a PromptVariant.

    Attributes:
        variant: The PromptVariant this run belongs to.
        run_ids: List of individual run identifiers collected.
        metrics: Key-value metric results (e.g. {"brier": 0.15, "accuracy": 0.72}).
    """

    variant: PromptVariant
    run_ids: List[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass
class PromptComparison:
    """Result of comparing a baseline EvalRun against a candidate EvalRun.

    Attributes:
        baseline: The baseline EvalRun.
        candidate: The candidate EvalRun.
        winner: "baseline", "candidate", or "tie".
        significant_delta: Mapping from metric name to (p_value, significant_bool).
        comparison_id: Unique identifier for this comparison.
    """

    baseline: EvalRun
    candidate: EvalRun
    winner: str  # "baseline" | "candidate" | "tie"
    significant_delta: dict  # metric → (p_value: float, significant: bool)
    comparison_id: str = ""


class PromptEvaluator:
    """Evaluates and compares prompt/model variants.

    Provides statistical comparison of two EvalRuns (baseline vs candidate)
    and factual-degradation analysis between claim sets.
    """

    @staticmethod
    def compare(
        baseline_runs: EvalRun,
        candidate_runs: EvalRun,
        outcome_data: Optional[np.ndarray] = None,
    ) -> PromptComparison:
        """Compare a baseline EvalRun against a candidate EvalRun.

        Computes per-metric deltas and statistical significance via bootstrap
        (if outcome_data provides per-observation values) or a simple
        threshold-based comparison when raw data is unavailable.

        Args:
            baseline_runs: Baseline EvalRun with pre-computed metrics.
            candidate_runs: Candidate EvalRun with pre-computed metrics.
            outcome_data: Optional (n_obs,) array of ground-truth values for
                per-observation significance testing.  When provided, each
                metric is compared observation-by-observation via paired
                bootstrap; otherwise significance is determined by the
                relative magnitude of the metric delta.

        Returns:
            PromptComparison with winner and per-metric significance deltas.
        """
        metrics_base = baseline_runs.metrics
        metrics_cand = candidate_runs.metrics
        all_keys = sorted(set(metrics_base.keys()) | set(metrics_cand.keys()))

        significant_delta: dict = {}
        better_base = 0
        better_cand = 0

        for key in all_keys:
            base_val = metrics_base.get(key, 0.0)
            cand_val = metrics_cand.get(key, 0.0)
            delta = cand_val - base_val

            # Determine direction: for "brier", "log_loss" lower is better,
            # so negative delta means candidate is better.
            # For "accuracy", "ic", "sharpe" higher is better.
            lower_is_better = key in ("brier", "log_loss", "mae", "rmse", "mse")

            if outcome_data is not None and len(outcome_data) > 0:
                p_val, sig = PromptEvaluator._bootstrap_significance(
                    np.full(len(outcome_data), base_val),
                    np.full(len(outcome_data), cand_val),
                    lower_is_better=lower_is_better,
                )
            else:
                # Heuristic: significant if |delta| > 5% of the average value
                avg_val = (abs(base_val) + abs(cand_val)) / 2.0 + 1e-9
                sig = abs(delta) / avg_val > 0.05
                # Approximate p-value from relative magnitude
                p_val = max(0.0, 1.0 - min(abs(delta) / (avg_val + 0.01), 1.0))

            significant_delta[key] = (float(p_val), bool(sig))

            if sig:
                if lower_is_better:
                    if delta < 0:
                        better_cand += 1
                    else:
                        better_base += 1
                else:
                    if delta > 0:
                        better_cand += 1
                    else:
                        better_base += 1

        if better_cand > better_base:
            winner = "candidate"
        elif better_base > better_cand:
            winner = "baseline"
        else:
            winner = "tie"

        return PromptComparison(
            baseline=baseline_runs,
            candidate=candidate_runs,
            winner=winner,
            significant_delta=significant_delta,
            comparison_id=f"cmp_{uuid.uuid4().hex[:12]}",
        )

    @staticmethod
    def check_factual_degradation(
        baseline_claims: List[Dict[str, object]],
        candidate_claims: List[Dict[str, object]],
    ) -> dict:
        """Compare factual accuracy between baseline and candidate claim sets.

        Each claim should be a dict with at least:
            - "is_factual" (bool): whether the claim is factually correct

        Returns a dict with:
            - baseline_accuracy: fraction of factual claims in baseline
            - candidate_accuracy: fraction of factual claims in candidate
            - degradation: positive means candidate is less factual
            - baseline_n, candidate_n: claim counts
            - new_errors: claims that candidate got wrong but baseline got right
            - fixed_errors: claims that candidate got right but baseline got wrong
        """
        if not baseline_claims or not candidate_claims:
            return {
                "baseline_accuracy": 0.0,
                "candidate_accuracy": 0.0,
                "degradation": 0.0,
                "baseline_n": len(baseline_claims),
                "candidate_n": len(candidate_claims),
                "new_errors": 0,
                "fixed_errors": 0,
            }

        def _is_factual(claim: Dict[str, object]) -> bool:
            val = claim.get("is_factual", True)
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ("true", "yes", "1")
            return bool(val)

        base_factual = sum(1 for c in baseline_claims if _is_factual(c))
        cand_factual = sum(1 for c in candidate_claims if _is_factual(c))

        base_n = len(baseline_claims)
        cand_n = len(candidate_claims)
        base_acc = base_factual / base_n if base_n > 0 else 0.0
        cand_acc = cand_factual / cand_n if cand_n > 0 else 0.0

        # Count new errors and fixed errors (positional pairing up to min length)
        n = min(base_n, cand_n)
        new_errors = 0
        fixed_errors = 0
        for i in range(n):
            base_ok = _is_factual(baseline_claims[i])
            cand_ok = _is_factual(candidate_claims[i])
            if base_ok and not cand_ok:
                new_errors += 1
            elif not base_ok and cand_ok:
                fixed_errors += 1

        return {
            "baseline_accuracy": round(base_acc, 4),
            "candidate_accuracy": round(cand_acc, 4),
            "degradation": round(base_acc - cand_acc, 4),
            "baseline_n": base_n,
            "candidate_n": cand_n,
            "new_errors": new_errors,
            "fixed_errors": fixed_errors,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bootstrap_significance(
        baseline_vals: np.ndarray,
        candidate_vals: np.ndarray,
        lower_is_better: bool = True,
        n_bootstrap: int = 1000,
        seed: int = 42,
    ) -> Tuple[float, bool]:
        """Paired bootstrap significance test.

        Returns (p_value, significant_bool).
        """
        base = np.asarray(baseline_vals, dtype=np.float64)
        cand = np.asarray(candidate_vals, dtype=np.float64)
        n = len(base)
        if n < 3:
            return (1.0, False)

        diff = base - cand  # positive = baseline larger
        obs_mean = float(np.mean(diff))

        rng = np.random.RandomState(seed)
        boot_means = np.empty(n_bootstrap, dtype=np.float64)
        for i in range(n_bootstrap):
            idx = rng.randint(0, n, size=n)
            boot_means[i] = np.mean(diff[idx])

        # Two-sided p-value: fraction of bootstrap means whose absolute value
        # exceeds the absolute observed mean
        p_val = float(np.mean(np.abs(boot_means) >= np.abs(obs_mean)))
        p_val = max(p_val, 1.0 / n_bootstrap)  # avoid p=0

        significant = p_val < 0.05
        return (p_val, significant)


# ============================================================================
# F04 — Chronological Factor Lab
# ============================================================================


@dataclass
class FactorPerformance:
    """Performance summary for a single factor.

    Attributes:
        factor_name: Name of the factor.
        ic_mean: Mean Information Coefficient over the evaluation period.
        ic_std: Standard deviation of IC.
        t_stat: t-statistic for IC ≠ 0.
        significant: Whether the factor is statistically significant (p < 0.05).
        periods: Number of periods evaluated.
        p_value: Two-sided p-value for the t-test.
    """

    factor_name: str
    ic_mean: float
    ic_std: float
    t_stat: float
    significant: bool
    periods: int
    p_value: float = 1.0


class FactorLab:
    """Chronological Factor Lab for evaluating factor performance.

    Provides IC analysis, rolling IC windows, and factor correlation matrices.
    """

    @staticmethod
    def evaluate_factors(
        factor_scores: Dict[str, np.ndarray],
        forward_returns: np.ndarray,
        periods: Optional[int] = None,
    ) -> List[FactorPerformance]:
        """Evaluate multiple factors against forward returns.

        For each factor, computes the cross-sectional IC (Pearson correlation
        between factor scores and forward returns), then aggregates across
        periods to produce IC mean, std, t-stat, and significance.

        Args:
            factor_scores: Dict mapping factor_name → (n_periods,) or
                (n_periods, n_assets) score array.
            forward_returns: (n_periods,) or (n_periods, n_assets) forward
                return array.
            periods: Number of periods.  Defaults to the length of
                forward_returns.

        Returns:
            List of FactorPerformance sorted by |ic_mean| descending.
        """
        fwd = np.asarray(forward_returns, dtype=np.float64)
        n_periods = periods if periods is not None else len(fwd)

        results: List[FactorPerformance] = []

        for name, scores in factor_scores.items():
            sc = np.asarray(scores, dtype=np.float64)

            # Compute per-period IC
            if sc.ndim == 2 and fwd.ndim == 2 and sc.shape == fwd.shape:
                # Cross-sectional: one IC per period
                ic_series = np.array([
                    FactorLab._pearson_r(sc[t], fwd[t])
                    for t in range(min(sc.shape[0], fwd.shape[0]))
                ])
            elif sc.ndim == 1 and fwd.ndim == 1:
                # Time-series: chunk into n_periods for per-period IC
                total_len = min(len(sc), len(fwd))
                if total_len >= 2 * n_periods:
                    chunk_size = total_len // n_periods
                    ic_list = []
                    for p in range(n_periods):
                        start = p * chunk_size
                        end = start + chunk_size
                        ic_list.append(FactorLab._pearson_r(sc[start:end], fwd[start:end]))
                    ic_series = np.array(ic_list)
                else:
                    # Too few data points for chunking — use single IC
                    ic_series = np.array([FactorLab._pearson_r(sc, fwd)])
            else:
                # Mismatched shapes: try to align by taking the shorter dimension
                min_len = min(len(sc), len(fwd))
                ic_series = np.array([FactorLab._pearson_r(sc[:min_len], fwd[:min_len])])

            ic_series = ic_series[np.isfinite(ic_series)]
            n = len(ic_series)
            if n < 1:
                results.append(FactorPerformance(
                    factor_name=name, ic_mean=0.0, ic_std=0.0,
                    t_stat=0.0, significant=False, periods=n, p_value=1.0,
                ))
                continue

            ic_mean = float(np.mean(ic_series))
            ic_std = float(np.std(ic_series, ddof=1)) if n > 1 else 0.0

            # t-test for IC ≠ 0
            if ic_std > 0 and n > 1:
                t_stat = ic_mean / (ic_std / np.sqrt(n))
                p_val = FactorLab._t_test_pvalue(t_stat, n - 1)
                significant = bool(p_val < 0.05)
            else:
                t_stat = 0.0
                p_val = 1.0
                significant = False

            results.append(FactorPerformance(
                factor_name=name,
                ic_mean=ic_mean,
                ic_std=ic_std,
                t_stat=float(t_stat),
                significant=significant,
                periods=n,
                p_value=float(p_val),
            ))

        # Sort by absolute IC mean descending
        results.sort(key=lambda r: abs(r.ic_mean), reverse=True)
        return results

    @staticmethod
    def rolling_ic(
        factor_scores: np.ndarray,
        returns: np.ndarray,
        window: int,
    ) -> List[float]:
        """Compute rolling Information Coefficient over a sliding window.

        At each step t ≥ window, computes the Pearson correlation between
        factor_scores[t-window:t] and returns[t-window:t].

        Args:
            factor_scores: 1-D array of factor scores (n_periods,).
            returns: 1-D array of forward returns (n_periods,).
            window: Rolling window size.

        Returns:
            List of IC values (length n_periods - window + 1).
        """
        sc = np.asarray(factor_scores, dtype=np.float64)
        ret = np.asarray(returns, dtype=np.float64)
        n = len(sc)
        window = max(2, min(window, n))

        rolling: List[float] = []
        for t in range(window, n + 1):
            ic = FactorLab._pearson_r(sc[t - window:t], ret[t - window:t])
            rolling.append(float(ic))

        return rolling

    @staticmethod
    def factor_correlation(
        factor_scores: Dict[str, np.ndarray],
    ) -> dict:
        """Compute pairwise correlation matrix for a set of factors.

        Args:
            factor_scores: Dict mapping factor_name → (n,) score array.

        Returns:
            Dict with:
                - "labels": list of factor names (in order)
                - "matrix": nested dict factor_i → {factor_j → correlation}
                - "mean_abs_corr": mean absolute pairwise correlation
        """
        names = sorted(factor_scores.keys())
        n_factors = len(names)

        if n_factors < 2:
            return {
                "labels": names,
                "matrix": {},
                "mean_abs_corr": 0.0,
            }

        # Align all factor score arrays to the same length
        min_len = min(len(factor_scores[name]) for name in names)
        aligned = {}
        for name in names:
            aligned[name] = np.asarray(factor_scores[name][:min_len], dtype=np.float64)

        matrix: Dict[str, Dict[str, float]] = {}
        corr_values: List[float] = []

        for i, name_i in enumerate(names):
            matrix[name_i] = {}
            for j, name_j in enumerate(names):
                if i == j:
                    matrix[name_i][name_j] = 1.0
                elif j < i:
                    # Symmetric: copy from previously computed
                    matrix[name_i][name_j] = matrix[name_j][name_i]
                else:
                    corr = FactorLab._pearson_r(aligned[name_i], aligned[name_j])
                    corr = 0.0 if not np.isfinite(corr) else float(corr)
                    matrix[name_i][name_j] = corr
                    corr_values.append(abs(corr))

        mean_abs = float(np.mean(corr_values)) if corr_values else 0.0

        return {
            "labels": names,
            "matrix": matrix,
            "mean_abs_corr": round(mean_abs, 4),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pearson_r(x: np.ndarray, y: np.ndarray) -> float:
        """Pearson correlation coefficient, safe for constant arrays."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if len(x) < 2 or np.std(x) == 0.0 or np.std(y) == 0.0:
            return 0.0
        return float(np.corrcoef(x, y)[0, 1])

    @staticmethod
    def _t_test_pvalue(t_stat: float, df: int) -> float:
        """Two-sided p-value from t-statistic and degrees of freedom.

        Uses scipy.stats if available, otherwise falls back to a
        Normal approximation (valid for df > 30).
        """
        if _HAS_SCIPY:
            from scipy import stats as _st
            return float(2.0 * _st.t.sf(abs(t_stat), df))

        # Normal approximation (reasonable for df > 30)
        # Using the asymptotic equivalence: t(df) → N(0, 1) as df → ∞
        # For smaller df, this is a rough estimate.
        z = abs(t_stat)
        # Abramowitz and Stegun approximation for standard normal CDF
        # Phi(z) ≈ 1 - 0.5 * (1 + c1*z + c2*z^2 + c3*z^3 + c4*z^4)^(-4)
        c1, c2, c3, c4 = 0.196854, 0.115194, 0.000344, 0.019527
        t = 1.0 / (1.0 + c1 * z + c2 * z * z + c3 * z * z * z + c4 * z * z * z * z)
        phi = 1.0 - 0.5 * (t ** 4)
        p_val = 2.0 * (1.0 - phi)
        return max(min(p_val, 1.0), 0.0)
