# -*- coding: utf-8 -*-
"""
Cost / Latency Budgeting (F06)
==============================

Track per-step token usage, latency, and estimated cost across an
analysis run.  Useful for LLM-powered pipelines where API calls
dominate both time and spend.

Provenance: standard observability / cost-accounting patterns
(OpenAI usage API, LangSmith, Weights & Biases traces).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================================
# StepCost
# ============================================================================


@dataclass
class StepCost:
    """Cost and latency for a single pipeline step."""

    step_name: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    metadata: dict = field(default_factory=dict)


# ============================================================================
# RunCost
# ============================================================================


@dataclass
class RunCost:
    """Aggregated cost and latency for a complete analysis run."""

    total_tokens: int = 0
    total_latency: float = 0.0
    total_cost: float = 0.0
    step_costs: List[StepCost] = field(default_factory=list)


# ============================================================================
# CostTracker
# ============================================================================


class CostTracker:
    """Track per-step cost and latency, compute aggregates.

    Usage::

        tracker = CostTracker(cost_per_1k_tokens=0.03)  # $0.03/1k tokens
        tracker.track_step("fetch", tokens_used=500, latency_ms=120.0)
        tracker.track_step("analyze", tokens_used=2000, latency_ms=800.0)
        run_cost = tracker.get_run_cost()
        print(f"Total: ${run_cost.total_cost:.4f}")
    """

    def __init__(
        self,
        cost_per_token: float = 0.0,
        cost_per_1k_tokens: Optional[float] = None,
    ) -> None:
        if cost_per_1k_tokens is not None:
            self._cost_per_token = cost_per_1k_tokens / 1000.0
        else:
            self._cost_per_token = cost_per_token
        self._steps: List[StepCost] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track_step(
        self,
        step_name: str,
        tokens_used: int = 0,
        latency_ms: float = 0.0,
        *,
        cost_per_token: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> StepCost:
        """Record cost and latency for one pipeline step."""
        cpt = cost_per_token if cost_per_token is not None else self._cost_per_token
        cost = self.estimate_cost(tokens_used, cpt)
        step = StepCost(
            step_name=step_name,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            cost_usd=round(cost, 6),
            metadata=metadata or {},
        )
        self._steps.append(step)
        return step

    def estimate_cost(
        self,
        tokens: int,
        cost_per_token: Optional[float] = None,
    ) -> float:
        """Estimate USD cost for a given number of tokens."""
        cpt = cost_per_token if cost_per_token is not None else self._cost_per_token
        return tokens * cpt

    def get_run_cost(self) -> RunCost:
        """Aggregate all tracked steps into a RunCost summary."""
        total_tokens = sum(s.tokens_used for s in self._steps)
        total_latency = sum(s.latency_ms for s in self._steps)
        total_cost = sum(s.cost_usd for s in self._steps)
        return RunCost(
            total_tokens=total_tokens,
            total_latency=round(total_latency, 3),
            total_cost=round(total_cost, 6),
            step_costs=list(self._steps),
        )

    def reset(self) -> None:
        """Clear all tracked steps."""
        self._steps.clear()

    @property
    def step_count(self) -> int:
        """Number of steps tracked so far."""
        return len(self._steps)

    @property
    def cost_per_token(self) -> float:
        """Current default cost per token in USD."""
        return self._cost_per_token

    def set_cost_per_token(self, value: float) -> None:
        """Update the default cost-per-token rate."""
        self._cost_per_token = value
