# -*- coding: utf-8 -*-
"""
augur.eval_lab — Chronological Evaluation Lab

使用不可变 RunBundle 在锁定的 walk-forward 窗口中比较 persona、prompt、因子的改动。

核心模块：
  - ChronologicalEvaluator: 对比 baseline vs candidate RunBundles，计算 Brier/log-loss/IC/accuracy
  - PersonaAblator: persona 消融实验，量化每个 persona 的边际贡献
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from augur.schemas.run_bundle import RunBundle

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class EvalMetric:
    """单个评估指标的结果。

    Attributes:
        name: 指标名称 ("brier", "log_loss", "accuracy", "ic")
        baseline_value: baseline 的指标值
        candidate_value: candidate 的指标值
        improvement: candidate - baseline（负值表示变差）
        significant: bootstrap CI 是否排除零
    """

    name: str
    baseline_value: float
    candidate_value: float
    improvement: float
    significant: bool


@dataclass
class EvalResult:
    """一次完整评估的结果。

    Attributes:
        eval_id: 评估唯一标识
        baseline_run_ids: baseline 使用的 RunBundle ID 列表
        candidate_run_ids: candidate 使用的 RunBundle ID 列表
        metrics: 各指标结果列表
        n_observations: 观测数
        n_tickers: 涉及的 ticker 数
        period_start: 评估窗口起始日期
        period_end: 评估窗口结束日期
        conclusion: 结论 "candidate_better" | "no_difference" | "baseline_better" | "insufficient_data"
    """

    eval_id: str
    baseline_run_ids: List[str]
    candidate_run_ids: List[str]
    metrics: List[EvalMetric]
    n_observations: int
    n_tickers: int
    period_start: str
    period_end: str
    conclusion: str


@dataclass
class AblationResult:
    """单个 persona 消融的结果。

    Attributes:
        persona_id: persona 标识
        removed: 是否被移除
        metrics_with: 有该 persona 时的指标值
        metrics_without: 移除后的指标值
        delta: 变化量（without - with，正值表示移除后改善）
        marginal_contribution: 边际贡献（所有 delta 绝对值的归一化权重）
        worth_keeping: 是否值得保留
    """

    persona_id: str
    removed: bool
    metrics_with: Dict[str, float]
    metrics_without: Dict[str, float]
    delta: Dict[str, float]
    marginal_contribution: float
    worth_keeping: bool


# ============================================================================
# Helper: extract predictions from RunBundles
# ============================================================================


def _extract_probability(bundle: RunBundle) -> Optional[float]:
    """从 RunBundle 中提取预测概率。

    查找 step_results 中 step_name 包含 "predict" 或 "signal" 的步骤，
    从 result dict 中提取 "probability" 或 "score" 字段，
    将 0-10 的 score 归一化到 0-1。

    Returns:
        0-1 之间的概率值，找不到则返回 None。
    """
    for step in bundle.step_results:
        if not isinstance(step.result, dict):
            continue
        name_lower = step.step_name.lower()
        if "predict" in name_lower or "signal" in name_lower or "score" in name_lower:
            result = step.result
            if "probability" in result:
                prob = float(result["probability"])
                return max(0.0, min(1.0, prob))
            if "score" in result:
                score = float(result["score"])
                # Normalize 0-10 score to 0-1 probability
                return max(0.0, min(1.0, score / 10.0))
            if "confidence" in result:
                conf = float(result["confidence"])
                return max(0.0, min(1.0, conf))

    # Fallback: scan all step results for any dict with probability/score
    for step in bundle.step_results:
        if isinstance(step.result, dict):
            if "probability" in step.result:
                return max(0.0, min(1.0, float(step.result["probability"])))
            if "score" in step.result:
                return max(0.0, min(1.0, float(step.result["score"]) / 10.0))

    return None


def _extract_ticker(bundle: RunBundle) -> str:
    """从 run_id 中提取 ticker。

    run_id 格式: run_{ticker}_{timestamp}_{hash[:8]}
    """
    parts = bundle.run_id.split("_")
    if len(parts) >= 3 and parts[0] == "run":
        return parts[1]
    return "unknown"


def _prepare_paired_data(
    baseline_runs: List[RunBundle],
    candidate_runs: List[RunBundle],
    outcome_data: Dict[str, float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """将 baseline 和 candidate RunBundles 与 outcome 配对。

    outcome_data 的 key 为 run_id 或 ticker，value 为实际收益/结果（0/1 或连续值）。

    Returns:
        (baseline_probs, candidate_probs, outcomes) 三个对齐的 numpy 数组
    """
    baseline_probs = []
    candidate_probs = []
    outcomes = []

    # Build lookup: run_id -> prob
    base_lookup: Dict[str, float] = {}
    for b in baseline_runs:
        prob = _extract_probability(b)
        if prob is not None:
            base_lookup[b.run_id] = prob
            # Also index by ticker
            ticker = _extract_ticker(b)
            base_lookup[ticker] = prob

    cand_lookup: Dict[str, float] = {}
    for c in candidate_runs:
        prob = _extract_probability(c)
        if prob is not None:
            cand_lookup[c.run_id] = prob
            ticker = _extract_ticker(c)
            cand_lookup[ticker] = prob

    for key, outcome in outcome_data.items():
        base_p = base_lookup.get(key)
        cand_p = cand_lookup.get(key)
        if base_p is not None and cand_p is not None:
            baseline_probs.append(base_p)
            candidate_probs.append(cand_p)
            outcomes.append(outcome)

    return (
        np.array(baseline_probs, dtype=np.float64),
        np.array(candidate_probs, dtype=np.float64),
        np.array(outcomes, dtype=np.float64),
    )


# ============================================================================
# ChronologicalEvaluator
# ============================================================================


class ChronologicalEvaluator:
    """Chronological Evaluation Engine.

    使用不可变 RunBundle 在锁定的 walk-forward 窗口中比较 baseline 与 candidate。
    支持 Brier score、log loss、accuracy、IC 四种指标，以及 bootstrap 显著性检验。
    """

    @staticmethod
    def compare_runs(
        baseline_runs: List[RunBundle],
        candidate_runs: List[RunBundle],
        outcome_data: Optional[Dict[str, float]] = None,
        forward_returns: Optional[Dict[str, float]] = None,
    ) -> EvalResult:
        """比较 baseline 和 candidate RunBundles。

        Args:
            baseline_runs: baseline 的 RunBundle 列表
            candidate_runs: candidate 的 RunBundle 列表
            outcome_data: run_id/ticker -> 实际二分类结果 (0/1) 的映射，用于 Brier/log-loss/accuracy
            forward_returns: run_id/ticker -> 前向收益的映射，用于 IC 计算

        Returns:
            EvalResult 包含所有指标和结论
        """
        metrics: List[EvalMetric] = []
        all_run_ids = [r.run_id for r in baseline_runs] + [r.run_id for r in candidate_runs]
        tickers = sorted({_extract_ticker(r) for r in baseline_runs + candidate_runs})
        n_obs = 0

        # Determine period from created_at timestamps
        all_times = sorted(
            r.created_at for r in baseline_runs + candidate_runs if r.created_at
        )
        period_start = all_times[0].strftime("%Y-%m-%d") if all_times else ""
        period_end = all_times[-1].strftime("%Y-%m-%d") if all_times else ""

        evaluator = ChronologicalEvaluator()

        # --- Classification metrics (Brier, log loss, accuracy) ---
        if outcome_data is not None and len(outcome_data) > 0:
            base_probs, cand_probs, outcomes = _prepare_paired_data(
                baseline_runs, candidate_runs, outcome_data
            )
            n_obs = len(outcomes)

            if n_obs > 0:
                # Brier score
                base_brier = float(evaluator.compute_brier_score(base_probs, outcomes))
                cand_brier = float(evaluator.compute_brier_score(cand_probs, outcomes))
                brier_imp = base_brier - cand_brier  # positive = improvement (lower is better)
                brier_sig = evaluator.check_significance(
                    evaluator._brier_per_obs(base_probs, outcomes),
                    evaluator._brier_per_obs(cand_probs, outcomes),
                )
                metrics.append(EvalMetric(
                    name="brier",
                    baseline_value=base_brier,
                    candidate_value=cand_brier,
                    improvement=brier_imp,
                    significant=brier_sig,
                ))

                # Log loss
                base_ll = float(evaluator.compute_log_loss(base_probs, outcomes))
                cand_ll = float(evaluator.compute_log_loss(cand_probs, outcomes))
                ll_imp = base_ll - cand_ll  # positive = improvement (lower is better)
                ll_sig = evaluator.check_significance(
                    evaluator._log_loss_per_obs(base_probs, outcomes),
                    evaluator._log_loss_per_obs(cand_probs, outcomes),
                )
                metrics.append(EvalMetric(
                    name="log_loss",
                    baseline_value=base_ll,
                    candidate_value=cand_ll,
                    improvement=ll_imp,
                    significant=ll_sig,
                ))

                # Accuracy (threshold at 0.5)
                base_acc = float(evaluator.compute_accuracy(base_probs, outcomes))
                cand_acc = float(evaluator.compute_accuracy(cand_probs, outcomes))
                acc_imp = cand_acc - base_acc  # positive = improvement
                acc_sig = evaluator.check_significance(
                    evaluator._accuracy_per_obs(base_probs, outcomes),
                    evaluator._accuracy_per_obs(cand_probs, outcomes),
                )
                metrics.append(EvalMetric(
                    name="accuracy",
                    baseline_value=base_acc,
                    candidate_value=cand_acc,
                    improvement=acc_imp,
                    significant=acc_sig,
                ))

        # --- IC ---
        if forward_returns is not None and len(forward_returns) > 0:
            base_fwd, cand_fwd, fwd_returns = _prepare_paired_data(
                baseline_runs, candidate_runs, forward_returns
            )
            if len(fwd_returns) > 0:
                base_ic = float(evaluator.compute_ic(base_fwd, fwd_returns))
                cand_ic = float(evaluator.compute_ic(cand_fwd, fwd_returns))
                ic_imp = cand_ic - base_ic  # positive = improvement
                ic_sig = evaluator.check_significance_ic(
                    base_fwd, cand_fwd, fwd_returns
                )
                metrics.append(EvalMetric(
                    name="ic",
                    baseline_value=base_ic,
                    candidate_value=cand_ic,
                    improvement=ic_imp,
                    significant=ic_sig,
                ))
                if n_obs == 0:
                    n_obs = len(fwd_returns)

        # --- Determine conclusion ---
        conclusion = ChronologicalEvaluator._derive_conclusion(metrics, n_obs)

        return EvalResult(
            eval_id=f"eval_{uuid.uuid4().hex[:12]}",
            baseline_run_ids=[r.run_id for r in baseline_runs],
            candidate_run_ids=[r.run_id for r in candidate_runs],
            metrics=metrics,
            n_observations=n_obs,
            n_tickers=len(tickers),
            period_start=period_start,
            period_end=period_end,
            conclusion=conclusion,
        )

    @staticmethod
    def _derive_conclusion(metrics: List[EvalMetric], n_obs: int) -> str:
        """从指标推导结论。"""
        if n_obs < 5:
            return "insufficient_data"
        if not metrics:
            return "insufficient_data"

        sig_better = 0
        sig_worse = 0
        for m in metrics:
            if not m.significant:
                continue
            # For brier and log_loss, improvement > 0 means candidate better (lower loss)
            # For accuracy and ic, improvement > 0 means candidate better
            if m.improvement > 0:
                sig_better += 1
            else:
                sig_worse += 1

        if sig_better > sig_worse and sig_better > 0:
            return "candidate_better"
        elif sig_worse > sig_better and sig_worse > 0:
            return "baseline_better"
        else:
            return "no_difference"

    # ------------------------------------------------------------------
    # Metric computation
    # ------------------------------------------------------------------

    @staticmethod
    def compute_brier_score(
        probabilities: np.ndarray, outcomes: np.ndarray
    ) -> float:
        """计算 Brier score。

        Brier = mean((p - o)^2)，值越小越好。

        Args:
            probabilities: 预测概率数组 (0-1)
            outcomes: 实际二分类结果 (0/1)
        """
        probs = np.asarray(probabilities, dtype=np.float64)
        outs = np.asarray(outcomes, dtype=np.float64)
        return float(np.mean((probs - outs) ** 2))

    @staticmethod
    def _brier_per_obs(
        probabilities: np.ndarray, outcomes: np.ndarray
    ) -> np.ndarray:
        """逐观测的 Brier score 分量。"""
        probs = np.asarray(probabilities, dtype=np.float64)
        outs = np.asarray(outcomes, dtype=np.float64)
        return (probs - outs) ** 2

    @staticmethod
    def compute_log_loss(
        probabilities: np.ndarray, outcomes: np.ndarray
    ) -> float:
        """计算 log loss（cross-entropy）。

        LogLoss = -mean(o * log(p) + (1-o) * log(1-p))

        Args:
            probabilities: 预测概率数组 (0-1)
            outcomes: 实际二分类结果 (0/1)
        """
        probs = np.asarray(probabilities, dtype=np.float64)
        outs = np.asarray(outcomes, dtype=np.float64)
        # Clip probabilities to avoid log(0)
        eps = 1e-15
        probs = np.clip(probs, eps, 1.0 - eps)
        return float(-np.mean(outs * np.log(probs) + (1.0 - outs) * np.log(1.0 - probs)))

    @staticmethod
    def _log_loss_per_obs(
        probabilities: np.ndarray, outcomes: np.ndarray
    ) -> np.ndarray:
        """逐观测的 log loss 分量。"""
        probs = np.asarray(probabilities, dtype=np.float64)
        outs = np.asarray(outcomes, dtype=np.float64)
        eps = 1e-15
        probs = np.clip(probs, eps, 1.0 - eps)
        return -(outs * np.log(probs) + (1.0 - outs) * np.log(1.0 - probs))

    @staticmethod
    def compute_accuracy(
        probabilities: np.ndarray, outcomes: np.ndarray, threshold: float = 0.5
    ) -> float:
        """计算准确率。

        预测概率 >= threshold 视为正类，否则负类。

        Args:
            probabilities: 预测概率数组 (0-1)
            outcomes: 实际二分类结果 (0/1)
            threshold: 分类阈值
        """
        probs = np.asarray(probabilities, dtype=np.float64)
        outs = np.asarray(outcomes, dtype=np.float64)
        preds = (probs >= threshold).astype(np.float64)
        return float(np.mean(preds == outs))

    @staticmethod
    def _accuracy_per_obs(
        probabilities: np.ndarray, outcomes: np.ndarray, threshold: float = 0.5
    ) -> np.ndarray:
        """逐观测的准确率分量 (1=正确, 0=错误)。"""
        probs = np.asarray(probabilities, dtype=np.float64)
        outs = np.asarray(outcomes, dtype=np.float64)
        preds = (probs >= threshold).astype(np.float64)
        return (preds == outs).astype(np.float64)

    @staticmethod
    def compute_ic(
        predictions: np.ndarray, forward_returns: np.ndarray
    ) -> float:
        """计算 Information Coefficient (Pearson 相关系数)。

        Args:
            predictions: 预测分数数组
            forward_returns: 前向收益数组
        """
        preds = np.asarray(predictions, dtype=np.float64)
        fwd = np.asarray(forward_returns, dtype=np.float64)
        if len(preds) < 2:
            return 0.0
        # Handle constant arrays
        if np.std(preds) == 0.0 or np.std(fwd) == 0.0:
            return 0.0
        return float(np.corrcoef(preds, fwd)[0, 1])

    # ------------------------------------------------------------------
    # Bootstrap & significance
    # ------------------------------------------------------------------

    @staticmethod
    def bootstrap_ci(
        values: np.ndarray,
        n_bootstrap: int = 1000,
        ci_level: float = 0.95,
        seed: Optional[int] = 42,
    ) -> Tuple[float, float]:
        """Bootstrap 置信区间。

        Args:
            values: 样本值数组
            n_bootstrap: bootstrap 重采样次数
            ci_level: 置信水平 (default 0.95)
            seed: 随机种子

        Returns:
            (lower, upper) 置信区间边界
        """
        vals = np.asarray(values, dtype=np.float64)
        n = len(vals)
        if n == 0:
            return (0.0, 0.0)

        rng = np.random.RandomState(seed)
        means = np.empty(n_bootstrap, dtype=np.float64)
        for i in range(n_bootstrap):
            sample = vals[rng.randint(0, n, size=n)]
            means[i] = np.mean(sample)

        alpha = (1.0 - ci_level) / 2.0
        lower = float(np.percentile(means, 100.0 * alpha))
        upper = float(np.percentile(means, 100.0 * (1.0 - alpha)))
        return (lower, upper)

    @staticmethod
    def check_significance(
        baseline_vals: np.ndarray,
        candidate_vals: np.ndarray,
        n_bootstrap: int = 1000,
        seed: Optional[int] = 42,
    ) -> bool:
        """检查 candidate 是否显著优于 baseline。

        对差值 (baseline - candidate) 做 bootstrap CI。
        如果 CI 不包含零，则认为显著。

        对于 Brier/log loss：baseline - candidate > 0 表示 candidate 更好
        对于 accuracy：candidate - baseline > 0 表示 candidate 更好

        这里使用 per-observation difference 的 bootstrap CI。

        Args:
            baseline_vals: baseline 逐观测指标值
            candidate_vals: candidate 逐观测指标值
            n_bootstrap: bootstrap 重采样次数
            seed: 随机种子

        Returns:
            True 如果差异显著（CI 不包含零）
        """
        base = np.asarray(baseline_vals, dtype=np.float64)
        cand = np.asarray(candidate_vals, dtype=np.float64)
        if len(base) != len(cand) or len(base) == 0:
            return False

        diff = base - cand  # positive = candidate better for loss metrics
        ci_low, ci_high = ChronologicalEvaluator.bootstrap_ci(
            diff, n_bootstrap=n_bootstrap, seed=seed
        )
        # If CI does not contain zero, significant
        return ci_low > 0.0 or ci_high < 0.0

    @staticmethod
    def check_significance_ic(
        baseline_preds: np.ndarray,
        candidate_preds: np.ndarray,
        forward_returns: np.ndarray,
        n_bootstrap: int = 1000,
        seed: Optional[int] = 42,
    ) -> bool:
        """IC 显著性检验。

        对 IC 差值做 bootstrap。

        Args:
            baseline_preds: baseline 预测值
            candidate_preds: candidate 预测值
            forward_returns: 前向收益
            n_bootstrap: bootstrap 重采样次数
            seed: 随机种子

        Returns:
            True 如果 IC 差异显著
        """
        base_p = np.asarray(baseline_preds, dtype=np.float64)
        cand_p = np.asarray(candidate_preds, dtype=np.float64)
        fwd = np.asarray(forward_returns, dtype=np.float64)
        n = len(fwd)
        if n < 3:
            return False

        rng = np.random.RandomState(seed)
        ic_diffs = np.empty(n_bootstrap, dtype=np.float64)
        for i in range(n_bootstrap):
            idx = rng.randint(0, n, size=n)
            base_ic = ChronologicalEvaluator.compute_ic(base_p[idx], fwd[idx])
            cand_ic = ChronologicalEvaluator.compute_ic(cand_p[idx], fwd[idx])
            ic_diffs[i] = cand_ic - base_ic  # positive = candidate better

        ci_low = float(np.percentile(ic_diffs, 2.5))
        ci_high = float(np.percentile(ic_diffs, 97.5))
        return ci_low > 0.0 or ci_high < 0.0


# ============================================================================
# PersonaAblator
# ============================================================================


class PersonaAblator:
    """Persona 消融实验引擎。

    量化每个 persona 对整体表现的边际贡献：
    1. 运行完整 persona 集合，记录 baseline 指标
    2. 逐一移除 persona，记录指标变化
    3. 计算 delta 和边际贡献
    4. 推荐保留/移除的 persona
    """

    def __init__(self, evaluator: Optional[ChronologicalEvaluator] = None):
        """初始化 PersonaAblator。

        Args:
            evaluator: ChronologicalEvaluator 实例，默认创建新的
        """
        self.evaluator = evaluator or ChronologicalEvaluator()

    def ablate_one(
        self,
        persona_id: str,
        full_results: Dict[str, List[RunBundle]],
        outcome_data: Dict[str, float],
    ) -> AblationResult:
        """对单个 persona 做消融实验。

        Args:
            persona_id: 要消融的 persona ID
            full_results: {persona_id: [RunBundle, ...]} 所有 persona 的结果
            outcome_data: run_id/ticker -> 实际结果

        Returns:
            AblationResult 包含消融前后对比
        """
        if persona_id not in full_results:
            raise ValueError(f"persona_id '{persona_id}' not found in full_results")

        # Collect all RunBundles from all personas (with)
        all_runs_with: List[RunBundle] = []
        for runs in full_results.values():
            all_runs_with.extend(runs)

        # Collect all RunBundles except the ablated persona (without)
        all_runs_without: List[RunBundle] = []
        for pid, runs in full_results.items():
            if pid != persona_id:
                all_runs_without.extend(runs)

        # Compute metrics with the persona
        metrics_with = self._compute_metric_dict(all_runs_with, outcome_data)

        # Compute metrics without the persona
        metrics_without = self._compute_metric_dict(all_runs_without, outcome_data)

        # Compute delta (without - with)
        # For brier/log_loss: positive delta = worse without (persona helps)
        # For accuracy/ic: negative delta = worse without (persona helps)
        delta = {
            k: metrics_without[k] - metrics_with[k] for k in metrics_with
        }

        # Marginal contribution: sum of absolute deltas, normalized later
        marginal_contribution = sum(abs(v) for v in delta.values())

        # A persona is worth keeping if removing it worsens metrics
        # For Brier/log_loss: worse = higher, so delta > 0 means worse without
        # For accuracy/IC: worse = lower, so delta < 0 means worse without
        worth_keeping = self._is_worth_keeping(delta)

        return AblationResult(
            persona_id=persona_id,
            removed=True,
            metrics_with=metrics_with,
            metrics_without=metrics_without,
            delta=delta,
            marginal_contribution=marginal_contribution,
            worth_keeping=worth_keeping,
        )

    def ablate_all(
        self,
        full_results: Dict[str, List[RunBundle]],
        outcome_data: Dict[str, float],
    ) -> List[AblationResult]:
        """对所有 persona 逐一消融，按边际贡献降序排列。

        Args:
            full_results: {persona_id: [RunBundle, ...]}
            outcome_data: run_id/ticker -> 实际结果

        Returns:
            按 marginal_contribution 降序排列的 AblationResult 列表
        """
        results = []
        for persona_id in full_results:
            try:
                result = self.ablate_one(persona_id, full_results, outcome_data)
                results.append(result)
            except Exception as e:
                logger.warning("Ablation failed for persona %s: %s", persona_id, e)

        # Normalize marginal contributions to [0, 1] range
        if results:
            max_contrib = max(r.marginal_contribution for r in results)
            if max_contrib > 0:
                for r in results:
                    r.marginal_contribution = r.marginal_contribution / max_contrib

        # Sort by marginal_contribution descending
        results.sort(key=lambda r: r.marginal_contribution, reverse=True)
        return results

    @staticmethod
    def recommend_retention(
        ablations: List[AblationResult],
        threshold: float = 0.01,
    ) -> List[str]:
        """推荐应该保留的 persona 列表。

        persona 值得保留如果：
        - worth_keeping 为 True（移除后指标变差）
        - 或 marginal_contribution >= threshold（边际贡献足够大）

        Args:
            ablations: ablate_all 的结果
            threshold: 边际贡献阈值

        Returns:
            值得保留的 persona_id 列表
        """
        keep = []
        for a in ablations:
            if a.worth_keeping or a.marginal_contribution >= threshold:
                keep.append(a.persona_id)
        return keep

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_metric_dict(
        self,
        runs: List[RunBundle],
        outcome_data: Dict[str, float],
    ) -> Dict[str, float]:
        """对一组 RunBundles 计算所有指标。"""
        if not runs or not outcome_data:
            return {"brier": 0.0, "log_loss": 0.0, "accuracy": 0.0}

        probs_list = []
        outs_list = []
        for key, outcome in outcome_data.items():
            for run in runs:
                if run.run_id == key:
                    prob = _extract_probability(run)
                    if prob is not None:
                        probs_list.append(prob)
                        outs_list.append(outcome)
                    break

        if not probs_list:
            return {"brier": 0.0, "log_loss": 0.0, "accuracy": 0.0}

        probs = np.array(probs_list, dtype=np.float64)
        outs = np.array(outs_list, dtype=np.float64)

        return {
            "brier": self.evaluator.compute_brier_score(probs, outs),
            "log_loss": self.evaluator.compute_log_loss(probs, outs),
            "accuracy": self.evaluator.compute_accuracy(probs, outs),
        }

    @staticmethod
    def _is_worth_keeping(delta: Dict[str, float]) -> bool:
        """判断 persona 是否值得保留。

        如果移除后 Brier/log_loss 增加（变差）或 accuracy 下降 = 值得保留。
        """
        brier_delta = delta.get("brier", 0.0)
        ll_delta = delta.get("log_loss", 0.0)
        acc_delta = delta.get("accuracy", 0.0)

        # For losses: positive delta = worse without persona → worth keeping
        # For accuracy: negative delta = worse without persona → worth keeping
        loss_worse = brier_delta > 0 or ll_delta > 0
        acc_worse = acc_delta < 0

        return loss_worse or acc_worse
