# -*- coding: utf-8 -*-
"""
augur.coverage_health — Coverage & Data Health Center (A05) + Promotion Gate (F07)

A05 — CoverageAnalyzer:
  Inspects an evidence_store dict to produce per-field coverage stats,
  detect missing/stale fields, and summarise universe-level coverage.

F07 — PromotionGate:
  Evaluates experimental features against a criteria rubric, issues
  promote/hold/demote recommendations, and mutates a lightweight
  in-process status registry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# How many days before a field is considered "stale"
_DEFAULT_STALE_THRESHOLD_DAYS = 90


# ============================================================================
# A05 — Coverage & Data Health Center
# ============================================================================


@dataclass
class FieldCoverage:
    """Coverage metrics for a single data field of a ticker.

    Attributes:
        field: Field name (e.g. "market_cap", "pe_ratio", "revenue_growth")
        coverage_pct: Percentage of periods where this field is available (0-100)
        periods_available: Count of periods with non-null data
        first_available: ISO date string of the earliest available period
        last_available: ISO date string of the most recent available period
        source: Name of the data provider that supplies this field
    """

    field: str
    coverage_pct: float
    periods_available: int
    first_available: str
    last_available: str
    source: str


@dataclass
class DataHealthReport:
    """Overall data-health assessment for a single ticker.

    Attributes:
        ticker: Stock ticker symbol
        fields: Coverage details for every known field
        overall_coverage: Weighted or simple average of field coverage_pct
        missing_fields: Fields that never appear in any period
        stale_fields: Fields whose last_available is more than
                       ``stale_threshold_days`` ago (default 90)
        recommendation: Human-readable summary (e.g. "healthy", "needs_fill",
                        "stale_review")
    """

    ticker: str
    fields: List[FieldCoverage]
    overall_coverage: float
    missing_fields: List[str]
    stale_fields: List[str]
    recommendation: str


class CoverageAnalyzer:
    """Analyse field-level data coverage from an evidence store.

    An *evidence store* is expected to be a dict of shape::

        {
            ticker: {
                "fields": {
                    field_name: {
                        "periods": [
                            {"date": "2024-01-15", "value": 123.4},
                            ...
                        ],
                        "source": "yfinance",
                    },
                    ...
                },
                "meta": { ... }   # optional
            },
            ...
        }

    Missing top-level ticker keys, missing ``"fields"`` sub-key, or empty
    period lists are all handled gracefully and reflected in the report.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def analyze(
        ticker: str,
        evidence_store: dict,
        stale_threshold_days: int = _DEFAULT_STALE_THRESHOLD_DAYS,
    ) -> DataHealthReport:
        """Produce a full DataHealthReport for *ticker*.

        Args:
            ticker: Symbol to look up in *evidence_store*.
            evidence_store: Dict as described in the class docstring.
            stale_threshold_days: Age in days after which a field is
                classified as stale (default 90).

        Returns:
            DataHealthReport; if *ticker* is absent from the store the
            report will have zero fields and ``"no_data"`` recommendation.
        """
        ticker_data = evidence_store.get(ticker, {}).get("fields", {})

        fields: List[FieldCoverage] = []
        missing: List[str] = []
        stale: List[str] = []

        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(days=stale_threshold_days)

        for field_name, field_data in ticker_data.items():
            periods = field_data.get("periods", []) if isinstance(field_data, dict) else []
            source = field_data.get("source", "unknown") if isinstance(field_data, dict) else "unknown"

            fc = CoverageAnalyzer._build_field_coverage(
                field_name, periods, source, stale_cutoff
            )
            fields.append(fc)

            if fc.coverage_pct == 0.0:
                missing.append(field_name)
            elif fc.last_available and fc.last_available < stale_cutoff.isoformat():
                stale.append(field_name)

        overall = CoverageAnalyzer._overall_coverage(fields)
        recommendation = CoverageAnalyzer._make_recommendation(
            fields, missing, stale
        )

        return DataHealthReport(
            ticker=ticker,
            fields=fields,
            overall_coverage=overall,
            missing_fields=missing,
            stale_fields=stale,
            recommendation=recommendation,
        )

    @staticmethod
    def field_status(ticker: str, field: str, evidence_store: dict) -> FieldCoverage:
        """Return coverage for a single field, or a zero-coverage sentinel.

        Args:
            ticker: Symbol.
            field: Field name.
            evidence_store: As described in :class:`CoverageAnalyzer`.

        Returns:
            FieldCoverage — if the field does not exist the returned
            object will have ``coverage_pct=0.0`` and ``source="unknown"``.
        """
        ticker_data = evidence_store.get(ticker, {}).get("fields", {})
        field_data = ticker_data.get(field)

        if field_data is None:
            return FieldCoverage(
                field=field,
                coverage_pct=0.0,
                periods_available=0,
                first_available="",
                last_available="",
                source="unknown",
            )

        periods = field_data.get("periods", []) if isinstance(field_data, dict) else []
        source = field_data.get("source", "unknown") if isinstance(field_data, dict) else "unknown"

        return CoverageAnalyzer._build_field_coverage(
            field, periods, source,
            datetime.now(timezone.utc) - timedelta(days=_DEFAULT_STALE_THRESHOLD_DAYS),
        )

    @staticmethod
    def get_universe_coverage(
        tickers: List[str],
        evidence_store: dict,
    ) -> Dict[str, dict]:
        """Return per-ticker summary dicts for an entire universe.

        Args:
            tickers: List of ticker symbols.
            evidence_store: As described in :class:`CoverageAnalyzer`.

        Returns:
            Dict mapping ``ticker -> { "fields": N, "overall_coverage": pct,
            "missing": [...], "stale": [...], "recommendation": str }``.
        """
        result: Dict[str, dict] = {}
        for t in tickers:
            report = CoverageAnalyzer.analyze(t, evidence_store)
            result[t] = {
                "fields": len(report.fields),
                "overall_coverage": report.overall_coverage,
                "missing": report.missing_fields,
                "stale": report.stale_fields,
                "recommendation": report.recommendation,
            }
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_field_coverage(
        field: str,
        periods: list,
        source: str,
        stale_cutoff: datetime,
    ) -> FieldCoverage:
        """Construct a FieldCoverage from raw period data.

        We estimate *expected* periods by looking at the date span
        (first → last) plus assuming monthly frequency.  If only a single
        period is present we set coverage_pct = 100.0.
        """
        if not periods:
            return FieldCoverage(
                field=field,
                coverage_pct=0.0,
                periods_available=0,
                first_available="",
                last_available="",
                source=source,
            )

        dates: List[str] = []
        for p in periods:
            d = p.get("date", "") if isinstance(p, dict) else ""
            if d:
                dates.append(d)
        dates.sort()

        first = dates[0]
        last = dates[-1]
        actual = len(dates)

        # Estimate expected periods: assume monthly cadence
        try:
            fd = datetime.fromisoformat(first)
            ld = datetime.fromisoformat(last)
            months = (ld.year - fd.year) * 12 + (ld.month - fd.month) + 1
            expected = max(months, 1)
        except (ValueError, TypeError):
            expected = max(actual, 1)

        coverage_pct = round(min(actual / expected, 1.0) * 100.0, 2)

        return FieldCoverage(
            field=field,
            coverage_pct=coverage_pct,
            periods_available=actual,
            first_available=first,
            last_available=last,
            source=source,
        )

    @staticmethod
    def _overall_coverage(fields: List[FieldCoverage]) -> float:
        """Simple mean across all fields; 0.0 when empty."""
        if not fields:
            return 0.0
        return round(sum(f.coverage_pct for f in fields) / len(fields), 2)

    @staticmethod
    def _make_recommendation(
        fields: List[FieldCoverage],
        missing: List[str],
        stale: List[str],
    ) -> str:
        if not fields:
            return "no_data"
        if stale and missing:
            return "needs_review"
        if stale:
            return "stale_review"
        if missing:
            return "needs_fill"
        overall = CoverageAnalyzer._overall_coverage(fields)
        if overall < 50.0:
            return "poor_coverage"
        if overall < 80.0:
            return "monitor"
        return "healthy"


# ============================================================================
# F07 — Promotion Gate
# ============================================================================


@dataclass
class PromotionCandidate:
    """A feature being considered for promotion (or demotion).

    Attributes:
        feature: Feature identifier (e.g. "rolling_ic_weight", "debate_engine").
        current_status: Current lifecycle stage — "raw", "experimental",
                        "production", or "deprecated".
        eval_results: Dict of metric → value from the eval lab
                      (e.g. ``{"brier": 0.18, "ic": 0.07}``).
        meets_criteria: Whether the latest eval satisfies the criteria.
        recommended_action: One of ``"promote"``, ``"hold"``, ``"demote"``.
    """

    feature: str
    current_status: str  # "raw" | "experimental" | "production" | "deprecated"
    eval_results: dict
    meets_criteria: bool = False
    recommended_action: str = "hold"  # "promote" | "hold" | "demote"


# Default promotion criteria
_DEFAULT_CRITERIA: dict = {
    "min_brier": 0.25,       # Brier score must be <= this (lower is better)
    "min_accuracy": 0.55,    # Accuracy must be >= this
    "min_ic": 0.03,          # IC must be >= this
    "min_observations": 50,  # Need enough data to be confident
}


class PromotionGate:
    """Evaluate feature candidates and manage their lifecycle status.

    A lightweight in-process status store.  For production use the caller
    should persist status updates to config (e.g. ``config/agents.yaml``)
    via a callback or by subclassing.
    """

    def __init__(self, criteria: Optional[dict] = None):
        """Create a PromotionGate.

        Args:
            criteria: Dict of metric thresholds.  Defaults to
                      :data:`_DEFAULT_CRITERIA`.  Supported keys:
                      ``min_brier``, ``min_accuracy``, ``min_ic``,
                      ``min_observations``.
        """
        self._criteria = dict(criteria) if criteria else dict(_DEFAULT_CRITERIA)
        self._statuses: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self, candidate: PromotionCandidate, criteria: Optional[dict] = None
    ) -> PromotionCandidate:
        """Evaluate a candidate against criteria and return it with
        ``meets_criteria`` and ``recommended_action`` populated.

        Args:
            candidate: The candidate to evaluate.  ``current_status`` and
                       ``eval_results`` are read; ``meets_criteria`` and
                       ``recommended_action`` are written back.
            criteria: Optional per-call criteria override.  Falls back to
                      the instance-level criteria dict.

        Returns:
            The same ``PromotionCandidate`` object, mutated in place.
            It is also returned for call chaining convenience.
        """
        crit = dict(criteria) if criteria else dict(self._criteria)

        meets = self._check_metrics(candidate.eval_results, crit)
        candidate.meets_criteria = meets

        candidate.recommended_action = self._determine_action(
            meets, candidate.current_status
        )

        return candidate

    def promote(self, feature: str) -> None:
        """Promote *feature* to the next lifecycle stage and cache the
        new status internally.

        Lifecycle order: raw → experimental → production (terminal promotion).
        """
        current = self.get_status(feature)
        order = ["raw", "experimental", "production"]
        if current not in order:
            self._statuses[feature] = "experimental"
            return
        idx = order.index(current)
        if idx < len(order) - 1:
            self._statuses[feature] = order[idx + 1]
        logger.info("Promoted feature '%s' from %s → %s", feature, current, self._statuses[feature])

    def demote(self, feature: str) -> None:
        """Demote *feature* one lifecycle stage.

        Lifecycle order (reverse): production → experimental → raw.
        """
        current = self.get_status(feature)
        order = ["raw", "experimental", "production"]
        if current == "raw":
            self._statuses[feature] = "raw"
            return
        if current not in order:
            self._statuses[feature] = "raw"
            return
        idx = order.index(current)
        if idx > 0:
            self._statuses[feature] = order[idx - 1]
        logger.info("Demoted feature '%s' from %s → %s", feature, current, self._statuses[feature])

    def get_status(self, feature: str) -> str:
        """Return the current lifecycle status for *feature*.

        If the feature has never been registered the fallback is
        ``"raw"`` (the default starting point).
        """
        return self._statuses.get(feature, "raw")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_metrics(eval_results: dict, criteria: dict) -> bool:
        """Return True when every applicable criterion is satisfied."""
        obs = eval_results.get("n_observations", 0)

        # Require minimum observation count when configured
        min_obs = criteria.get("min_observations", 0)
        if obs < min_obs:
            return False

        # Brier: lower is better
        brier = eval_results.get("brier")
        if brier is not None and brier > criteria.get("min_brier", 0.25):
            return False

        # Accuracy: higher is better
        acc = eval_results.get("accuracy")
        if acc is not None and acc < criteria.get("min_accuracy", 0.55):
            return False

        # IC: higher is better
        ic_val = eval_results.get("ic")
        if ic_val is not None and ic_val < criteria.get("min_ic", 0.03):
            return False

        return True

    @staticmethod
    def _determine_action(meets: bool, current_status: str) -> str:
        """Pick promote/hold/demote based on metrics + current stage."""
        if meets:
            if current_status in ("raw", "experimental"):
                return "promote"
            return "hold"  # already production
        else:
            if current_status == "production":
                return "demote"
            return "hold"
