# -*- coding: utf-8 -*-
"""
Disagreement Map engine — distill 18 persona outputs into decision-relevant conflicts.

Instead of 18 parallel scorecards, produce up to five structured disagreements:
who disagrees, on which dimension, how far apart their scores are, which
evidence items that dimension rests on, and what new information would move
the scores.

Derivation (2026-09-17): every persona reports per-dimension ``factors``
(0–10). Factor names differ per persona (``moat``, ``moat_quality``,
``brand_moat``…), so :data:`DIMENSIONS` maps them to a shared dimension and
to the MarketContext metrics it is computed from. A conflict is a dimension
where at least one persona scores it high (≥ 6.5) and another low (≤ 3.5);
it cites the evidence ids of that dimension's metrics from the run's fetch
step. A dimension the personas split on but for which the run holds no
evidence is reported as an evidence gap, not as a conflict. Runs without
factor scores produce no conflict points — the map says so instead of
inventing claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

HIGH = 6.5
LOW = 3.5


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class ConflictPoint:
    """A single point of disagreement between personas.

    Attributes:
        claim: The dimension in dispute, stated with the evidence values it rests on.
        bullish_personas: Personas scoring the dimension high.
        bearish_personas: Personas scoring the dimension low.
        abstaining_personas: Personas with a middling score, with the score as reason.
        evidence_supporting: Evidence ids the high scorers' view rests on.
        evidence_contradicting: Evidence ids the low scorers' view rests on.
            Both sides read the same underlying metrics, so for factor-derived
            conflicts the two lists are identical — the disagreement is about
            interpretation, not about which data exists.
        information_that_would_resolve: What new data would settle this.
        impact: "high" | "medium" | "low" — how much this affects the overall thesis.
        dimension: Canonical dimension key (see :data:`DIMENSIONS`).
        persona_scores: The factor score (0–10) behind each persona's side.
        metrics: Metric values cited in ``claim``, keyed by MarketContext field.
    """

    claim: str
    bullish_personas: List[str] = field(default_factory=list)
    bearish_personas: List[str] = field(default_factory=list)
    abstaining_personas: Dict[str, str] = field(default_factory=dict)
    evidence_supporting: List[str] = field(default_factory=list)
    evidence_contradicting: List[str] = field(default_factory=list)
    information_that_would_resolve: str = ""
    impact: str = "medium"  # high | medium | low
    dimension: str = ""
    persona_scores: Dict[str, float] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class DisagreementMap:
    """A structured view of where the 18 personas agree and diverge.

    Attributes:
        ticker: Instrument ticker.
        run_id: Associated RunBundle ID.
        consensus_strength: "strong" | "moderate" | "weak" | "divided".
        agreement_points: Dimensions where the scoring personas agree, with evidence values.
        conflict_points: Up to five evidence-backed disagreements, most decision-relevant first.
        silent_personas: Personas with no strong view (not noise).
        summary: One-paragraph narrative summary.
        derivation: "factor-spread" when built from per-dimension factor scores,
            "signal-only" when the run has no factor scores.
        evidence_gaps: Dimensions the personas split on but the run holds no evidence for.
    """

    ticker: str
    run_id: str
    consensus_strength: str = "moderate"
    agreement_points: List[str] = field(default_factory=list)
    conflict_points: List[ConflictPoint] = field(default_factory=list)
    silent_personas: List[str] = field(default_factory=list)
    summary: str = ""
    derivation: str = "signal-only"
    evidence_gaps: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dimension table
# ---------------------------------------------------------------------------

#: dimension -> (label, persona factor names, MarketContext metrics, what would resolve it)
DIMENSIONS: Dict[str, Tuple[str, Tuple[str, ...], Tuple[str, ...], str]] = {
    "valuation": (
        "Valuation",
        ("valuation", "relative_valuation", "valuation_acceptability", "valuation_reasonableness",
         "valuation_fairness", "intrinsic_value_discount", "margin_of_safety", "peg",
         "distressed_discount", "risk_pricing", "crypto_valuation"),
        ("pe", "pb", "ps", "fcf", "market_cap"),
        "Next earnings: does growth justify the multiple (EPS and FCF vs expectations)?",
    ),
    "moat": (
        "Competitive moat and business quality",
        ("moat", "moat_quality", "competitive_moat", "brand_moat", "technology_moat", "moat_durability",
         "moat_reinforcement", "monopoly_power", "competitive_position", "pricing_power",
         "business_model_quality", "business_clarity", "quality", "margin_sustainability"),
        ("gross_margins", "operating_margins", "roe"),
        "Gross-margin and market-share trend over the next two quarters.",
    ),
    "management": (
        "Management and capital allocation",
        ("management_quality", "management_integrity", "management_excellence", "management_vision",
         "founder_quality", "sales_organization"),
        ("roe", "insider_ownership"),
        "Buyback / M&A execution and insider transactions (Form 4).",
    ),
    "balance_sheet": (
        "Balance sheet strength",
        ("financial_strength", "balance_sheet", "financial_soundness", "liquidity_risk"),
        ("debt_ratio", "current_ratio", "fcf"),
        "Debt maturities, interest coverage and FCF in the next 10-Q.",
    ),
    "earnings_quality": (
        "Earnings predictability",
        ("earnings_predictability", "earnings_stability", "long_term_durability"),
        ("earnings_growth", "fcf", "operating_margins"),
        "Consistency of the next two quarters' earnings versus guidance.",
    ),
    "growth": (
        "Growth runway",
        ("growth", "growth_durability", "growth_franchise", "tam_size", "tam_expansion",
         "disruption_score", "innovation_diffusion", "industry_tailwinds", "structural_opportunity",
         "ai_exposure", "ai_compute_demand", "compute_infrastructure", "china_structural_theme",
         "long_term_bet", "ark_framework"),
        ("revenue_growth", "earnings_growth"),
        "Revenue growth versus consensus and forward guidance.",
    ),
    "momentum": (
        "Price trend and sentiment",
        ("momentum", "momentum_signal", "trend_strength", "trend_reinforcement", "momentum_sentiment",
         "market_bias", "options_iv_momentum", "narrative_timing", "contrarian_timing",
         "inflection_condition", "pendulum_position", "exit_signal"),
        ("rsi", "sma50", "sma200", "price"),
        "Price action through the next earnings event.",
    ),
    "macro": (
        "Macro and liquidity backdrop",
        ("macro_outlook", "macro_background", "liquidity", "geopolitical_catalyst", "stablecoin_signal",
         "supply_chain_bottleneck"),
        (),
        "Rates, liquidity and policy data (not captured as evidence in this run).",
    ),
}

_FACTOR_TO_DIMENSION: Dict[str, str] = {
    name: key for key, (_label, names, _metrics, _resolve) in DIMENSIONS.items() for name in names
}


def _format_metric(metric: str, value: float) -> str:
    pct = {"gross_margins", "operating_margins", "roe", "debt_ratio", "revenue_growth",
           "earnings_growth", "insider_ownership"}
    if metric in pct:
        return f"{metric.replace('_', ' ')} {value * 100:.1f}%"
    if metric in ("fcf", "market_cap"):
        return f"{metric.replace('_', ' ')} ${value:,.1f}B"
    if metric == "price":
        return f"price ${value:,.2f}"
    return f"{metric.upper() if len(metric) <= 3 else metric.replace('_', ' ')} {value:,.1f}"


def _index_evidence(evidence_manifest: Any) -> Dict[str, List[Dict[str, Any]]]:
    """metric -> evidence item dicts (accepts a list of items or an id -> item mapping)."""
    items: Iterable[Any]
    if isinstance(evidence_manifest, dict):
        items = evidence_manifest.values()
    elif isinstance(evidence_manifest, list):
        items = evidence_manifest
    else:
        items = []
    by_metric: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        if isinstance(item, dict) and item.get("evidence_id") and item.get("metric"):
            by_metric.setdefault(item["metric"], []).append(item)
    return by_metric


# ---------------------------------------------------------------------------
# Disagreement Map Builder
# ---------------------------------------------------------------------------

class DisagreementMapBuilder:
    """Build a DisagreementMap from workflow output."""

    def __init__(self, ticker: str, run_id: str):
        self._ticker = ticker.upper()
        self._run_id = run_id

    def build(
        self,
        persona_outputs: Dict[str, Dict[str, Any]],
        evidence_manifest: Optional[Any] = None,
    ) -> DisagreementMap:
        """Build the disagreement map from persona analysis results.

        Args:
            persona_outputs: persona_id → {"signal", "score", "confidence",
                "factors": {name: 0-10}, ...} (the analyze step result).
            evidence_manifest: Evidence items from the run's fetch step, as a
                list of dicts or an evidence_id → dict mapping.
        """
        result = DisagreementMap(ticker=self._ticker, run_id=self._run_id)

        bulls = {k: v for k, v in persona_outputs.items() if v.get("signal") == "bullish"}
        bears = {k: v for k, v in persona_outputs.items() if v.get("signal") == "bearish"}

        total = len(persona_outputs)
        if total == 0:
            result.summary = "No persona responses available."
            return result

        bull_pct = len(bulls) / total
        bear_pct = len(bears) / total
        if max(bull_pct, bear_pct) >= 0.75:
            result.consensus_strength = "strong"
        elif max(bull_pct, bear_pct) >= 0.55:
            result.consensus_strength = "moderate"
        elif abs(bull_pct - bear_pct) < 0.15:
            result.consensus_strength = "divided"
        else:
            result.consensus_strength = "weak"

        for pid, pdata in persona_outputs.items():
            if pdata.get("signal") == "neutral" or pdata.get("confidence", 1.0) < 0.2:
                result.silent_personas.append(pid)

        scores = self._dimension_scores(persona_outputs)
        if scores:
            result.derivation = "factor-spread"
            evidence = _index_evidence(evidence_manifest)
            result.conflict_points, result.evidence_gaps = self._extract_conflicts(scores, evidence)
            result.agreement_points = self._find_agreement(scores, evidence, len(bulls), len(bears), total)
        else:
            result.derivation = "signal-only"
            result.agreement_points = self._signal_agreement(len(bulls), len(bears), total)

        result.summary = self._summarize(result)
        return result

    # ------------------------------------------------------------------
    # Factor scores per dimension
    # ------------------------------------------------------------------

    @staticmethod
    def _dimension_scores(persona_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """dimension -> persona -> mean score of that persona's factors in the dimension."""
        collected: Dict[str, Dict[str, List[float]]] = {}
        for pid, pdata in persona_outputs.items():
            for name, value in (pdata.get("factors") or {}).items():
                dim = _FACTOR_TO_DIMENSION.get(name)
                if dim is None or not isinstance(value, (int, float)):
                    continue
                collected.setdefault(dim, {}).setdefault(pid, []).append(float(value))
        return {
            dim: {pid: sum(vals) / len(vals) for pid, vals in per.items()}
            for dim, per in collected.items()
        }

    @staticmethod
    def _cited(dim: str, evidence: Dict[str, List[Dict[str, Any]]]) -> Tuple[List[str], Dict[str, float], List[str]]:
        """(evidence ids, metric values, missing metrics) for a dimension."""
        ids: List[str] = []
        values: Dict[str, float] = {}
        missing: List[str] = []
        for metric in DIMENSIONS[dim][2]:
            items = evidence.get(metric, [])
            present = [i for i in items if not i.get("missing") and isinstance(i.get("value"), (int, float))]
            if present:
                ids.extend(i["evidence_id"] for i in present)
                values[metric] = float(present[0]["value"])
            elif items:
                missing.append(metric)
        return ids, values, missing

    # ------------------------------------------------------------------
    # Conflict extraction
    # ------------------------------------------------------------------

    def _extract_conflicts(
        self,
        scores: Dict[str, Dict[str, float]],
        evidence: Dict[str, List[Dict[str, Any]]],
    ) -> Tuple[List[ConflictPoint], List[str]]:
        conflicts: List[Tuple[Tuple[int, int, float], ConflictPoint]] = []
        gaps: List[str] = []
        impact_rank = {"high": 0, "medium": 1, "low": 2}
        for dim, per in scores.items():
            label, _names, _metrics, resolve = DIMENSIONS[dim]
            high = {p: s for p, s in per.items() if s >= HIGH}
            low = {p: s for p, s in per.items() if s <= LOW}
            if not high or not low:
                continue
            spread = sum(high.values()) / len(high) - sum(low.values()) / len(low)
            ids, values, missing = self._cited(dim, evidence)
            split = (f"{label}: {len(high)} persona(s) score it high "
                     f"({', '.join(sorted(high))}) and {len(low)} low ({', '.join(sorted(low))})")
            if not ids:
                gaps.append(split + " — no evidence for this dimension in the run")
                continue
            smaller_side = min(len(high), len(low))
            if smaller_side >= 2 and spread >= 5:
                impact = "high"
            elif spread >= 4:
                impact = "medium"
            else:
                impact = "low"
            metric_text = ", ".join(_format_metric(m, v) for m, v in values.items())
            abstaining = {p: f"middling score {s:.1f}/10" for p, s in per.items() if LOW < s < HIGH}
            for metric in missing:
                abstaining.setdefault(f"evidence:{metric}", "missing in this run")
            cp = ConflictPoint(
                claim=f"{label} ({metric_text})",
                bullish_personas=sorted(high, key=lambda p: -high[p]),
                bearish_personas=sorted(low, key=lambda p: low[p]),
                abstaining_personas=abstaining,
                evidence_supporting=list(ids),
                evidence_contradicting=list(ids),
                information_that_would_resolve=resolve,
                impact=impact,
                dimension=dim,
                persona_scores={p: round(s, 1) for p, s in {**high, **low}.items()},
                metrics=values,
            )
            conflicts.append(((impact_rank[impact], -smaller_side, -spread), cp))
        conflicts.sort(key=lambda item: item[0])
        return [cp for _key, cp in conflicts[:5]], gaps

    # ------------------------------------------------------------------
    # Agreement detection
    # ------------------------------------------------------------------

    def _find_agreement(
        self,
        scores: Dict[str, Dict[str, float]],
        evidence: Dict[str, List[Dict[str, Any]]],
        n_bulls: int,
        n_bears: int,
        total: int,
    ) -> List[str]:
        points: List[str] = []
        for dim, per in scores.items():
            if len(per) < 3:
                continue
            label = DIMENSIONS[dim][0]
            _ids, values, _missing = self._cited(dim, evidence)
            suffix = f" ({', '.join(_format_metric(m, v) for m, v in values.items())})" if values else ""
            if all(s >= HIGH for s in per.values()):
                points.append(f"{label}: all {len(per)} scoring personas rate it strong{suffix}")
            elif all(s <= LOW for s in per.values()):
                points.append(f"{label}: all {len(per)} scoring personas rate it weak{suffix}")
        return points + self._signal_agreement(n_bulls, n_bears, total)

    @staticmethod
    def _signal_agreement(n_bulls: int, n_bears: int, total: int) -> List[str]:
        if n_bulls + n_bears == 0:
            return []
        if n_bulls > n_bears * 2:
            return [f"Signals: strong majority bullish ({n_bulls}/{total})"]
        if n_bears > n_bulls * 2:
            return [f"Signals: strong majority bearish ({n_bears}/{total})"]
        return []

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _summarize(self, result: DisagreementMap) -> str:
        parts: List[str] = []

        consensus = result.consensus_strength
        if consensus == "strong":
            parts.append("Strong consensus among personas.")
        elif consensus == "moderate":
            parts.append("Moderate consensus with notable dissent.")
        elif consensus == "divided":
            parts.append("Personas are sharply divided.")
        else:
            parts.append("Weak consensus — high uncertainty.")

        n_conflicts = len(result.conflict_points)
        if n_conflicts > 0:
            parts.append(
                f"{n_conflicts} evidence-backed disagreement{'s' if n_conflicts > 1 else ''} identified."
            )
        if result.evidence_gaps:
            parts.append(f"{len(result.evidence_gaps)} split dimension(s) lack evidence in this run.")
        if result.derivation == "signal-only":
            parts.append("No per-dimension factor scores in this run, so no conflict points were derived "
                         "(re-run `augur workflow` to record them).")

        if result.silent_personas:
            parts.append(
                f"{len(result.silent_personas)} persona(s) had no strong view."
            )

        return " ".join(parts)


# ---------------------------------------------------------------------------
# RunBundle helper
# ---------------------------------------------------------------------------

def build_disagreement_from_bundle(bundle: Dict[str, Any], ticker: str, run_id: str) -> DisagreementMap:
    """Build the map from a persisted RunBundle dict (analyze + fetch steps)."""
    steps = {sr.get("step_name"): sr for sr in bundle.get("step_results", []) if isinstance(sr, dict)}
    persona_outputs = {
        pid: pdata for pid, pdata in ((steps.get("analyze") or {}).get("result") or {}).items()
        if isinstance(pdata, dict)
    }
    fetch_result = (steps.get("fetch") or {}).get("result") or {}
    evidence = fetch_result.get("evidence_items") if isinstance(fetch_result, dict) else None
    return DisagreementMapBuilder(ticker, run_id).build(persona_outputs, evidence or [])
