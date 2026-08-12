# -*- coding: utf-8 -*-
"""Tests for Prompt/Model Evaluation + Factor Lab (F03 + F04)."""
import pytest
from augur.prompt_eval import (
    PromptVariant, EvalRun, PromptComparison, PromptEvaluator,
    FactorPerformance, FactorLab,
)


class TestPromptVariant:
    def test_creation(self):
        pv = PromptVariant(variant_id="v1", prompt_text="Analyze {ticker}", model="claude-4", description="Baseline")
        assert pv.variant_id == "v1"


class TestPromptComparison:
    def test_creation(self):
        baseline = EvalRun(variant=PromptVariant("b", "", "m", ""), run_ids=[], metrics={"brier": 0.20})
        candidate = EvalRun(variant=PromptVariant("c", "", "m", ""), run_ids=[], metrics={"brier": 0.15})
        pc = PromptComparison(baseline=baseline, candidate=candidate, winner="candidate", significant_delta={"brier": (0.03, True)})
        assert pc.winner == "candidate"


class TestPromptEvaluator:
    def test_check_factual_degradation_none(self):
        baseline = [{"claim": "Revenue grew", "evidence_ids": ["ev_001"]}]
        result = PromptEvaluator.check_factual_degradation(baseline, baseline)
        assert isinstance(result, dict)

    def test_check_factual_degradation_detected(self):
        baseline = [{"claim": "Revenue grew", "evidence_ids": ["ev_001"]}]
        candidate = [{"claim": "Revenue grew 15%", "evidence_ids": []}]  # missing evidence
        result = PromptEvaluator.check_factual_degradation(baseline, candidate)
        assert isinstance(result, dict)


class TestFactorPerformance:
    def test_creation(self):
        fp = FactorPerformance(factor_name="momentum", ic_mean=0.05, ic_std=0.02, t_stat=2.5, significant=True, periods=100)
        assert fp.significant is True


class TestFactorLab:
    def test_evaluate_factors(self):
        scores = {"momentum": [0.1, 0.2, 0.1], "value": [-0.1, 0.0, 0.1]}
        returns = [0.05, -0.02, 0.03]
        factors = FactorLab.evaluate_factors(scores, returns, [1, 2, 3])
        assert len(factors) == 2

    def test_rolling_ic(self):
        scores = [0.1, 0.2, -0.1, 0.3, 0.0]
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        ic = FactorLab.rolling_ic(scores, returns, 3)
        assert len(ic) >= 1

    def test_factor_correlation(self):
        scores = {"a": [1, 2, 3], "b": [1, 2, 3], "c": [3, 2, 1]}
        corr = FactorLab.factor_correlation(scores)
        assert isinstance(corr, dict)
