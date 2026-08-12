# -*- coding: utf-8 -*-
"""
tests/test_cost_budget.py — F06 Cost / Latency Budgeting tests.

Validates:
  1. StepCost dataclass fields default and override correctly.
  2. RunCost aggregates correctly from empty and populated StepCost lists.
  3. CostTracker.track_step records StepCost with correct values.
  4. CostTracker.track_step uses per-step cost_per_token override.
  5. CostTracker.estimate_cost computes correctly.
  6. CostTracker.get_run_cost aggregates across multiple steps.
  7. CostTracker.reset clears all steps.
  8. CostTracker.step_count tracks number of steps.
  9. CostTracker with cost_per_1k_tokens constructor convenience.
 10. CostTracker.set_cost_per_token updates the default rate.
 11. CostTracker handles zero-cost (default) correctly.
"""

from __future__ import annotations

import pytest

from augur.cost_budget import CostTracker, RunCost, StepCost


# ---------------------------------------------------------------------------
# 1. StepCost dataclass
# ---------------------------------------------------------------------------

def test_step_cost_defaults():
    """StepCost defaults are zero/empty."""
    sc = StepCost(step_name="test")
    assert sc.step_name == "test"
    assert sc.tokens_used == 0
    assert sc.latency_ms == 0.0
    assert sc.cost_usd == 0.0
    assert sc.metadata == {}


def test_step_cost_with_values():
    """StepCost stores explicit values."""
    sc = StepCost(
        step_name="fetch",
        tokens_used=500,
        latency_ms=120.5,
        cost_usd=0.015,
        metadata={"model": "gpt-4"},
    )
    assert sc.tokens_used == 500
    assert sc.latency_ms == 120.5
    assert sc.cost_usd == 0.015
    assert sc.metadata == {"model": "gpt-4"}


# ---------------------------------------------------------------------------
# 2. RunCost dataclass
# ---------------------------------------------------------------------------

def test_run_cost_defaults():
    """RunCost defaults to zero totals and empty list."""
    rc = RunCost()
    assert rc.total_tokens == 0
    assert rc.total_latency == 0.0
    assert rc.total_cost == 0.0
    assert rc.step_costs == []


def test_run_cost_with_steps():
    """RunCost aggregates from explicit StepCost list."""
    steps = [
        StepCost("fetch", tokens_used=100, latency_ms=50.0, cost_usd=0.003),
        StepCost("analyze", tokens_used=200, latency_ms=150.0, cost_usd=0.006),
    ]
    rc = RunCost(
        total_tokens=300,
        total_latency=200.0,
        total_cost=0.009,
        step_costs=steps,
    )
    assert rc.total_tokens == 300
    assert rc.total_latency == 200.0
    assert rc.total_cost == 0.009
    assert len(rc.step_costs) == 2


# ---------------------------------------------------------------------------
# 3. CostTracker — track_step
# ---------------------------------------------------------------------------

def test_track_step_records_correctly():
    """track_step creates a StepCost with correct values."""
    tracker = CostTracker(cost_per_token=0.0001)  # $0.0001/token
    sc = tracker.track_step("fetch", tokens_used=100, latency_ms=50.0)
    assert sc.step_name == "fetch"
    assert sc.tokens_used == 100
    assert sc.latency_ms == 50.0
    assert sc.cost_usd == 0.01  # 100 * 0.0001
    assert tracker.step_count == 1


def test_track_step_per_step_cost_override():
    """Per-step cost_per_token overrides the tracker default."""
    tracker = CostTracker(cost_per_token=0.0001)
    sc = tracker.track_step(
        "analyze", tokens_used=200, latency_ms=100.0,
        cost_per_token=0.0005,  # 5× default
    )
    assert sc.cost_usd == 0.10  # 200 * 0.0005


def test_track_step_metadata():
    """Metadata is stored on the StepCost."""
    tracker = CostTracker()
    sc = tracker.track_step(
        "consensus", tokens_used=50, latency_ms=10.0,
        metadata={"provider": "openai", "model": "gpt-4o"},
    )
    assert sc.metadata == {"provider": "openai", "model": "gpt-4o"}


# ---------------------------------------------------------------------------
# 4. CostTracker — estimate_cost
# ---------------------------------------------------------------------------

def test_estimate_cost():
    """estimate_cost computes tokens * rate."""
    tracker = CostTracker(cost_per_token=0.00002)  # $0.02/1k
    assert tracker.estimate_cost(500) == 0.01
    assert tracker.estimate_cost(0) == 0.0


def test_estimate_cost_with_override():
    """Per-call cost_per_token override works."""
    tracker = CostTracker(cost_per_token=0.00001)
    assert tracker.estimate_cost(1000, cost_per_token=0.0001) == 0.10


# ---------------------------------------------------------------------------
# 5. CostTracker — get_run_cost
# ---------------------------------------------------------------------------

def test_get_run_cost_aggregates():
    """get_run_cost sums all steps correctly."""
    tracker = CostTracker(cost_per_token=0.0001)
    tracker.track_step("fetch", tokens_used=100, latency_ms=50.0)
    tracker.track_step("analyze", tokens_used=200, latency_ms=150.0)
    tracker.track_step("consensus", tokens_used=300, latency_ms=80.0)

    rc = tracker.get_run_cost()
    assert rc.total_tokens == 600
    assert rc.total_latency == 280.0
    assert rc.total_cost == 0.06  # 600 * 0.0001
    assert len(rc.step_costs) == 3


def test_get_run_cost_empty():
    """get_run_cost on empty tracker returns zeros."""
    tracker = CostTracker()
    rc = tracker.get_run_cost()
    assert rc.total_tokens == 0
    assert rc.total_latency == 0.0
    assert rc.total_cost == 0.0
    assert rc.step_costs == []


# ---------------------------------------------------------------------------
# 6. CostTracker — reset
# ---------------------------------------------------------------------------

def test_reset_clears_steps():
    """reset clears all tracked steps."""
    tracker = CostTracker(cost_per_token=0.0001)
    tracker.track_step("fetch", tokens_used=100, latency_ms=50.0)
    tracker.track_step("analyze", tokens_used=200, latency_ms=100.0)
    assert tracker.step_count == 2

    tracker.reset()
    assert tracker.step_count == 0
    rc = tracker.get_run_cost()
    assert rc.total_tokens == 0
    assert rc.total_cost == 0.0


# ---------------------------------------------------------------------------
# 7. CostTracker — constructor variants
# ---------------------------------------------------------------------------

def test_cost_per_1k_tokens_constructor():
    """cost_per_1k_tokens convenience correctly divides by 1000."""
    tracker = CostTracker(cost_per_1k_tokens=0.03)  # $0.03 / 1k tokens
    assert tracker.cost_per_token == pytest.approx(0.00003)
    sc = tracker.track_step("fetch", tokens_used=1000)
    assert sc.cost_usd == 0.03


def test_cost_per_1k_overrides_per_token():
    """When both are given, cost_per_1k_tokens wins."""
    tracker = CostTracker(cost_per_token=0.001, cost_per_1k_tokens=0.05)
    assert tracker.cost_per_token == 0.00005


# ---------------------------------------------------------------------------
# 8. CostTracker — set_cost_per_token
# ---------------------------------------------------------------------------

def test_set_cost_per_token():
    """set_cost_per_token updates the default rate."""
    tracker = CostTracker(cost_per_token=0.0001)
    tracker.set_cost_per_token(0.0002)
    assert tracker.cost_per_token == 0.0002
    sc = tracker.track_step("fetch", tokens_used=100)
    assert sc.cost_usd == 0.02


# ---------------------------------------------------------------------------
# 9. Zero-cost default
# ---------------------------------------------------------------------------

def test_zero_cost_default():
    """Default cost_per_token of 0.0 produces zero-cost steps."""
    tracker = CostTracker()
    sc = tracker.track_step("free_step", tokens_used=10000, latency_ms=5000.0)
    assert sc.cost_usd == 0.0
    rc = tracker.get_run_cost()
    assert rc.total_cost == 0.0
