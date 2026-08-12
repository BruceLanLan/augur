
"""Cost & Latency Budgeting (F06) — per-step and per-run cost tracking."""
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class StepCost:
    step_name: str; tokens_used: int = 0
    latency_ms: float = 0; cost_usd: float = 0.0

@dataclass
class RunCost:
    total_tokens: int = 0; total_latency_ms: float = 0
    total_cost_usd: float = 0.0; step_costs: List[StepCost] = field(default_factory=list)

    @property
    def tokens_per_dollar(self) -> float:
        return self.total_tokens / max(self.total_cost_usd, 0.0001)

class CostTracker:
    def __init__(self): self._steps: List[StepCost] = []

    def track_step(self, step_name: str, tokens: int = 0, latency_ms: float = 0, model: str = "default") -> StepCost:
        cost_per_1k = {"default": 0.002, "claude-4": 0.015, "gpt-4o": 0.010, "cheap": 0.0005}
        rate = cost_per_1k.get(model, 0.002)
        cost = (tokens / 1000) * rate
        sc = StepCost(step_name=step_name, tokens_used=tokens, latency_ms=latency_ms, cost_usd=round(cost, 6))
        self._steps.append(sc)
        return sc

    def get_run_cost(self) -> RunCost:
        total_tokens = sum(s.tokens_used for s in self._steps)
        total_latency = sum(s.latency_ms for s in self._steps)
        total_cost = sum(s.cost_usd for s in self._steps)
        return RunCost(total_tokens=total_tokens, total_latency_ms=total_latency, total_cost_usd=round(total_cost, 6), step_costs=list(self._steps))

    def estimate_cost(self, expected_tokens: int, model: str = "default") -> float:
        cost_per_1k = {"default": 0.002, "claude-4": 0.015, "gpt-4o": 0.010}
        return round((expected_tokens / 1000) * cost_per_1k.get(model, 0.002), 6)
