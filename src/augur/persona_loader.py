# -*- coding: utf-8 -*-
"""
YAML Persona Loader - define custom agent personas via YAML config files.

Each YAML file describes a persona with factors and scoring rules.

Usage:
    from augur.persona_loader import load_persona_yaml, load_personas_from_dir
    from augur.registry import get_registry

    agent = load_persona_yaml("personas/my_quant.yaml")
    get_registry().register(agent)

    # or bulk-load a directory
    for agent in load_personas_from_dir("personas/custom/"):
        get_registry().register(agent)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from augur.personas.base import AgentResponse, BaseAgent, MarketContext, SignalType

logger = logging.getLogger(__name__)

# Fields of MarketContext that rules may reference
_CTX_FIELDS = {
    f.name for f in MarketContext.__dataclass_fields__.values()  # type: ignore[attr-defined]
} if hasattr(MarketContext, "__dataclass_fields__") else set()


def _eval_rule_condition(condition: str, ctx: MarketContext) -> bool:
    """Safely evaluate a boolean rule condition string against a MarketContext."""
    ns = {field: getattr(ctx, field, 0) for field in _CTX_FIELDS}
    ns.update({"True": True, "False": False})
    try:
        return bool(eval(condition, {"__builtins__": {}}, ns))  # noqa: S307
    except Exception:
        return False


def _compute_factor(factor_def: Dict, ctx: MarketContext) -> float:
    score = float(factor_def.get("base", 5))
    for rule in factor_def.get("rules", []):
        condition = rule.get("if", "False")
        delta = float(rule.get("add", 0))
        if _eval_rule_condition(condition, ctx):
            score += delta
    return min(max(score, 0.0), 10.0)


class YamlAgent(BaseAgent):
    """A dynamically-defined agent loaded from a YAML persona file."""

    def __init__(self, spec: Dict):
        super().__init__(
            agent_id=spec["agent_id"],
            name=spec["name"],
            identity=spec.get("identity", ""),
            philosophy=spec.get("philosophy", []),
            scoring_weights=spec.get("scoring_weights", {}),
            thresholds=spec.get("thresholds", {"bullish_threshold": 7.0, "bearish_threshold": 4.0}),
            biases=spec.get("biases", {}),
        )
        self._factor_defs: Dict[str, Dict] = spec.get("factors", {})
        self._spec = spec

    def get_system_prompt(self) -> str:
        return f"""You are a {self.name}-style investor (YAML custom persona).
Identity: {self.identity}
Philosophy: {', '.join(self.philosophy)}
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        factors: Dict[str, float] = {}
        for factor_name, factor_def in self._factor_defs.items():
            factors[factor_name] = _compute_factor(factor_def, context)

        # Fallback: if no factors defined, return neutral
        if not factors:
            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.name,
                signal=SignalType.NEUTRAL,
                confidence=0.3,
                score=5.0,
                reasoning=f"## {self.name}\nNo factor rules defined.",
                key_findings=[],
                risks=["YAML persona has no factor rules - using neutral default"],
                metadata={"philosophy": self.philosophy},
                coverage_confidence=0.3,
            )

        total_score = sum(factors[k] * self.scoring_weights.get(k, 1.0 / len(factors)) for k in factors)
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.80, 0.4 + avg_score / 20.0)

        bullish_th = self.thresholds.get("bullish_threshold", 7.0)
        bearish_th = self.thresholds.get("bearish_threshold", 4.0)

        factor_lines = "\n".join(
            f"- {k}: {v:.1f}/10" for k, v in factors.items()
        )
        reasoning = f"""## {self.name} Analysis for {context.ticker}

{factor_lines}

**Score: {total_score:.1f}/10**
Signal: {'Bullish' if avg_score >= bullish_th else 'Bearish' if avg_score <= bearish_th else 'Neutral'}
"""
        coverage_confidence = min(1.0, len(self._factor_defs) / max(1, len(self.scoring_weights)))

        return AgentResponse(
            agent_id=self.agent_id,
            agent_name=self.name,
            signal=signal,
            confidence=confidence,
            score=total_score,
            reasoning=reasoning,
            key_findings=[],
            risks=[],
            metadata={"factors": factors, "philosophy": self.philosophy},
            coverage_confidence=coverage_confidence,
        )


def load_persona_yaml(path: str | Path) -> YamlAgent:
    """Load a single YAML persona file and return a YamlAgent instance."""
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("pyyaml is required for YAML persona loading: pip install pyyaml") from exc

    path = Path(path)
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    _validate_spec(spec, path)
    logger.debug("Loaded YAML persona: %s from %s", spec.get("agent_id"), path)
    return YamlAgent(spec)


def load_personas_from_dir(directory: str | Path) -> List[YamlAgent]:
    """Load all *.yaml / *.yml persona files from a directory."""
    directory = Path(directory)
    agents = []
    for p in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
        try:
            agents.append(load_persona_yaml(p))
        except Exception as exc:
            logger.warning("Failed to load persona from %s: %s", p, exc)
    return agents


def _validate_spec(spec: Dict, path: Path) -> None:
    required = ["agent_id", "name", "scoring_weights"]
    missing = [k for k in required if k not in spec]
    if missing:
        raise ValueError(f"YAML persona {path} is missing required keys: {missing}")
    total_w = sum(spec["scoring_weights"].values())
    if abs(total_w - 1.0) > 0.05:
        logger.warning(
            "Persona %s scoring_weights sum to %.3f (expected ~1.0) - will be used as-is",
            spec["agent_id"], total_w,
        )
