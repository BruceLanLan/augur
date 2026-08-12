# -*- coding: utf-8 -*-
"""
Material Catalyst Alerts (B07) + Event Readiness Score (B08).

Tracks material catalysts that can move a stock — filings, guidance changes,
insider clusters, ownership deltas, thesis triggers, and disagreement
widening — and evaluates how ready the system is to analyse a given event.

Classes:
    Alert               — immutable dataclass for a single catalyst alert
    AlertEngine         — detector / deduplicator / lifecycle manager for alerts
    ReadinessScore      — dataclass for event-readiness evaluation
    ReadinessEvaluator  — computes readiness scores and missing-data reports
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_alert_id(ticker: str, alert_type: str, title: str) -> str:
    """Generate ``al_{hash[:8]}`` from ticker + type + title."""
    raw = f"{ticker.upper()}:{alert_type}:{title}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"al_{h[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _severity_for_type(alert_type: str) -> str:
    """Map alert type to a default severity level."""
    mapping = {
        "filing_published": "high",
        "guidance_change": "high",
        "insider_cluster": "medium",
        "ownership_delta": "medium",
        "thesis_triggered": "critical",
        "disagreement_widened": "medium",
    }
    return mapping.get(alert_type, "low")


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------


@dataclass
class Alert:
    """Immutable record of a material catalyst alert.

    Attributes:
        alert_id: Unique identifier ``al_{hash[:8]}``.
        ticker: Instrument ticker (e.g. ``"AAPL"``).
        alert_type: One of ``filing_published`` | ``guidance_change`` |
            ``insider_cluster`` | ``ownership_delta`` | ``thesis_triggered`` |
            ``disagreement_widened``.
        title: Short, human-readable headline.
        description: Longer explanation of the catalyst.
        severity: ``critical`` | ``high`` | ``medium`` | ``low``.
        created_at: ISO-8601 creation timestamp (UTC).
        source_run_id: The :class:`RunBundle` id that triggered this alert.
        dismissed: Whether the user has dismissed this alert.
        cooldown_until: ISO-8601 timestamp after which a duplicate is
            allowed again.  Used by :meth:`AlertEngine.deduplicate`.
    """

    ticker: str
    alert_type: str
    title: str
    description: str
    alert_id: str = ""
    severity: str = "medium"
    created_at: str = ""
    source_run_id: str = ""
    dismissed: bool = False
    cooldown_until: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.alert_id:
            self.alert_id = _generate_alert_id(
                self.ticker, self.alert_type, self.title
            )


# ---------------------------------------------------------------------------
# AlertEngine
# ---------------------------------------------------------------------------


class AlertEngine:
    """Detector, deduplicator, and lifecycle manager for material catalyst alerts.

    Alerts are kept in-memory.  Each ``check_*`` method inspects a specific
    data source and yields zero or more :class:`Alert` objects.  Callers
    should pipe results through :meth:`deduplicate` before persisting or
    presenting them to avoid noisy repeats.

    Usage::

        engine = AlertEngine()
        new = engine.check_filing_alerts("AAPL", filing_dict)
        deduped = engine.deduplicate(new)
        engine._alerts.extend(deduped)
        active = engine.get_active("AAPL")
    """

    def __init__(self):
        self._alerts: List[Alert] = []

    # ------------------------------------------------------------------
    # Detectors
    # ------------------------------------------------------------------

    def check_filing_alerts(
        self, ticker: str, new_filing: dict
    ) -> List[Alert]:
        """Inspect a new filing for material catalysts.

        Args:
            ticker: The instrument ticker.
            new_filing: Dict with keys like ``filing_type``,
                ``material_change_count``, ``overall_assessment``, etc.
        """
        alerts: List[Alert] = []
        ticker = ticker.upper()
        ftype = new_filing.get("filing_type", "unknown")
        assessment = new_filing.get("overall_assessment", "")
        material_count = new_filing.get("material_change_count", 0)

        # Always alert on a new filing being published
        alerts.append(Alert(
            ticker=ticker,
            alert_type="filing_published",
            title=f"{ticker} {ftype} filed",
            description=(
                f"New {ftype} filing published"
                + (f" with {material_count} material change(s)"
                   if material_count else "")
            ),
            severity=_severity_for_filing(assessment, material_count),
            source_run_id=new_filing.get("run_id", ""),
        ))

        return alerts

    def check_guidance_alerts(
        self, ticker: str, guidance_changes: list
    ) -> List[Alert]:
        """Inspect guidance changes for raised / lowered / new / withdrawn.

        Args:
            ticker: The instrument ticker.
            guidance_changes: List of dicts, each with keys like
                ``metric``, ``direction``, ``previous_range``, ``new_range``.
        """
        alerts: List[Alert] = []
        ticker = ticker.upper()

        for gc in guidance_changes:
            metric = gc.get("metric", "guidance")
            direction = gc.get("direction", "changed")

            if direction == "raised":
                sev = "high"
                title = f"{ticker} raised {metric} guidance"
            elif direction == "lowered":
                sev = "critical"
                title = f"{ticker} lowered {metric} guidance"
            elif direction == "withdrawn":
                sev = "critical"
                title = f"{ticker} withdrew {metric} guidance"
            elif direction == "new":
                sev = "medium"
                title = f"{ticker} issued new {metric} guidance"
            elif direction == "narrowed":
                sev = "low"
                title = f"{ticker} narrowed {metric} guidance"
            else:
                sev = "low"
                title = f"{ticker} {metric} guidance {direction}"

            prev_r = gc.get("previous_range")
            new_r = gc.get("new_range")
            desc_parts = [title]
            if prev_r:
                desc_parts.append(
                    f"Previous: {prev_r[0]}–{prev_r[1]}"
                    if isinstance(prev_r, (list, tuple)) and len(prev_r) == 2
                    else f"Previous: {prev_r}"
                )
            if new_r:
                desc_parts.append(
                    f"New: {new_r[0]}–{new_r[1]}"
                    if isinstance(new_r, (list, tuple)) and len(new_r) == 2
                    else f"New: {new_r}"
                )

            alerts.append(Alert(
                ticker=ticker,
                alert_type="guidance_change",
                title=title,
                description=". ".join(desc_parts),
                severity=sev,
            ))

        return alerts

    def check_insider_alerts(
        self, ticker: str, clusters: list
    ) -> List[Alert]:
        """Inspect insider transaction clusters for material signals.

        Args:
            ticker: The instrument ticker.
            clusters: List of dicts, each with keys like ``direction``
                (``buying`` | ``selling``), ``participant_count``,
                ``total_value``, ``period_days``.
        """
        alerts: List[Alert] = []
        ticker = ticker.upper()

        for cluster in clusters:
            direction = cluster.get("direction", "")
            count = cluster.get("participant_count", 0)
            total_value = cluster.get("total_value", 0)
            period = cluster.get("period_days", 0)

            if count < 2:
                continue  # Not a cluster — single trades don't trigger

            if direction == "selling":
                sev = "high" if count >= 4 else "medium"
                title = (
                    f"{ticker} insider selling cluster: "
                    f"{count} insiders in {period}d"
                )
            elif direction == "buying":
                sev = "high"
                title = (
                    f"{ticker} insider buying cluster: "
                    f"{count} insiders in {period}d"
                )
            else:
                sev = "medium"
                title = f"{ticker} insider cluster ({direction}, {count} participants)"

            description = (
                f"${total_value:,.0f} total across {count} insiders "
                f"over {period} days"
            )

            alerts.append(Alert(
                ticker=ticker,
                alert_type="insider_cluster",
                title=title,
                description=description,
                severity=sev,
            ))

        return alerts

    def check_thesis_alerts(
        self, ticker: str, thesis_deltas: list
    ) -> List[Alert]:
        """Inspect thesis deltas for triggered or refuted theses.

        Args:
            ticker: The instrument ticker.
            thesis_deltas: List of :class:`ThesisDelta` objects or dicts
                with keys ``thesis_id``, ``overall_assessment``,
                ``falsification_triggered``, etc.
        """
        alerts: List[Alert] = []
        ticker = ticker.upper()

        for td in thesis_deltas:
            # Accept both dicts and ThesisDelta objects
            tid = td.get("thesis_id") if isinstance(td, dict) else getattr(td, "thesis_id", "")
            assessment = (
                td.get("overall_assessment")
                if isinstance(td, dict)
                else getattr(td, "overall_assessment", "")
            )
            triggered = (
                td.get("falsification_triggered", [])
                if isinstance(td, dict)
                else getattr(td, "falsification_triggered", [])
            )

            if assessment == "refuted":
                alerts.append(Alert(
                    ticker=ticker,
                    alert_type="thesis_triggered",
                    title=f"{ticker} thesis refuted: {tid}",
                    description=(
                        f"Thesis {tid} was refuted. "
                        f"Falsification conditions triggered: {', '.join(triggered) if triggered else 'none'}"
                    ),
                    severity="critical",
                ))
            elif assessment == "weakened":
                alerts.append(Alert(
                    ticker=ticker,
                    alert_type="thesis_triggered",
                    title=f"{ticker} thesis weakened: {tid}",
                    description=(
                        f"Thesis {tid} was weakened. Review the underlying "
                        f"fact and valuation changes."
                    ),
                    severity="high",
                ))
            elif assessment == "strengthened":
                alerts.append(Alert(
                    ticker=ticker,
                    alert_type="thesis_triggered",
                    title=f"{ticker} thesis strengthened: {tid}",
                    description=f"Thesis {tid} was strengthened by new evidence.",
                    severity="low",
                ))

        return alerts

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def deduplicate(
        self, alerts: List[Alert], cooldown_minutes: int = 60
    ) -> List[Alert]:
        """Filter *alerts* to those that are not already represented by an
        active alert on the same ticker + type, or still within cooldown.

        Args:
            alerts: Candidate alerts to deduplicate.
            cooldown_minutes: Minimum minutes between same-type alerts for
                the same ticker.  Default 60.
        """
        now = datetime.now(timezone.utc)
        result: List[Alert] = []

        for cand in alerts:
            # Check if any existing *active* alert covers the same ticker+type
            # and is either not cooldown-expired or not dismissed.
            duplicate = False
            for existing in self._alerts:
                if existing.dismissed:
                    continue
                if (
                    existing.ticker.upper() == cand.ticker.upper()
                    and existing.alert_type == cand.alert_type
                ):
                    if existing.cooldown_until:
                        try:
                            cd = datetime.fromisoformat(existing.cooldown_until)
                            if cd > now:
                                duplicate = True
                                break
                        except (ValueError, TypeError):
                            pass
                    # No cooldown set — still considered a duplicate if it
                    # exists and isn't dismissed
                    duplicate = True
                    break

            if not duplicate:
                result.append(cand)

        return result

    def get_active(self, ticker: Optional[str] = None) -> List[Alert]:
        """Return all non-dismissed alerts, optionally filtered by *ticker*.

        Args:
            ticker: If provided, only return alerts for this ticker
                (case-insensitive).
        """
        active = [a for a in self._alerts if not a.dismissed]
        if ticker:
            t = ticker.upper()
            active = [a for a in active if a.ticker.upper() == t]
        return sorted(active, key=lambda a: a.created_at, reverse=True)

    def dismiss(self, alert_id: str) -> bool:
        """Mark the alert with *alert_id* as dismissed.

        Returns:
            ``True`` if the alert was found and dismissed, ``False`` otherwise.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.dismissed = True
                return True
        return False


# ---------------------------------------------------------------------------
# Helpers for AlertEngine
# ---------------------------------------------------------------------------

def _severity_for_filing(assessment: str, material_count: int) -> str:
    """Determine alert severity based on filing assessment."""
    if assessment == "significant_changes":
        return "critical"
    if material_count >= 3:
        return "high"
    if material_count >= 1:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# ReadinessScore
# ---------------------------------------------------------------------------


@dataclass
class ReadinessScore:
    """Evaluation of how ready the system is to analyse a given event.

    Attributes:
        ticker: Instrument ticker.
        event_id: Unique identifier for the event being analysed.
        overall_score: 0-100 composite readiness score.
        data_availability: Percentage of required data present (0-100).
        analysis_freshness: How recent the last analysis is, as a
            percentage where 100 = within 1 hour and 0 = older than 30 days.
        evidence_completeness: Percentage of claims backed by evidence (0-100).
        missing_items: List of human-readable descriptions of missing data.
        recommendation: ``ready`` (>70 overall) | ``partial`` (40-70) |
            ``insufficient`` (<40).
    """

    ticker: str
    event_id: str
    overall_score: float = 0.0
    data_availability: float = 0.0
    analysis_freshness: float = 0.0
    evidence_completeness: float = 0.0
    missing_items: List[str] = field(default_factory=list)
    recommendation: str = "insufficient"

    def __post_init__(self):
        if not self.recommendation or self.recommendation == "insufficient":
            if self.overall_score >= 70:
                self.recommendation = "ready"
            elif self.overall_score >= 40:
                self.recommendation = "partial"
            else:
                self.recommendation = "insufficient"


# ---------------------------------------------------------------------------
# ReadinessEvaluator
# ---------------------------------------------------------------------------


class ReadinessEvaluator:
    """Compute readiness scores and missing-data reports for a ticker.

    Usage::

        evaluator = ReadinessEvaluator()
        score = evaluator.evaluate("AAPL", {"event_id": "earnings_2025Q3", ...})
        missing = evaluator.missing_data_report("AAPL")
    """

    # Fields considered "required" for a full analysis
    _REQUIRED_DATA_FIELDS = [
        "market_cap",
        "revenue",
        "net_income",
        "eps_diluted",
        "pe_ratio",
        "price",
        "sector",
        "industry",
    ]

    # Fields that are strongly recommended but not strictly required
    _RECOMMENDED_DATA_FIELDS = [
        "free_cash_flow",
        "debt_to_equity",
        "roe",
        "guidance",
        "insider_transactions",
        "institutional_ownership",
    ]

    def __init__(self):
        self._data_snapshots: Dict[str, Dict[str, Any]] = {}
        self._last_analysis: Dict[str, str] = {}  # ticker -> ISO timestamp

    def set_data_snapshot(self, ticker: str, data: Dict[str, Any]) -> None:
        """Register a data snapshot for *ticker* (e.g. from fetch_market_context)."""
        self._data_snapshots[ticker.upper()] = data

    def set_last_analysis(self, ticker: str, iso_timestamp: str) -> None:
        """Record the timestamp of the last analysis run for *ticker*."""
        self._last_analysis[ticker.upper()] = iso_timestamp

    def evaluate(self, ticker: str, event: dict) -> ReadinessScore:
        """Compute a readiness score for *ticker* given an *event* dict.

        Args:
            ticker: The instrument ticker.
            event: Dict with at least ``event_id``.  May also contain
                ``required_fields`` (list of field names needed for this
                specific event) and ``evidence_claims`` (list of claim dicts).

        Returns:
            A :class:`ReadinessScore` with the composite evaluation.
        """
        ticker = ticker.upper()
        event_id = event.get("event_id", "")

        data = self._data_snapshots.get(ticker, {})

        # Determine which fields are required for this specific event
        event_required = event.get("required_fields", list(self._REQUIRED_DATA_FIELDS))
        all_desired = set(event_required) | set(self._RECOMMENDED_DATA_FIELDS)

        # --- Data availability ---
        available = sum(1 for f in all_desired if f in data and data[f] is not None)
        data_availability = (
            (available / len(all_desired) * 100) if all_desired else 100.0
        )
        missing = [
            f"Missing field: {f}"
            for f in sorted(all_desired)
            if f not in data or data[f] is None
        ]

        # --- Analysis freshness ---
        last_ts = self._last_analysis.get(ticker)
        if last_ts:
            try:
                last_dt = datetime.fromisoformat(last_ts)
                age_hours = (
                    datetime.now(timezone.utc) - last_dt.replace(tzinfo=timezone.utc)
                ).total_seconds() / 3600
                # 100% if ≤1 hour old, linear decay to 0% at 720 hours (30 days)
                analysis_freshness = max(0.0, 100.0 * (1.0 - age_hours / 720.0))
            except (ValueError, TypeError):
                analysis_freshness = 0.0
        else:
            analysis_freshness = 0.0
            missing.append("No prior analysis found for this ticker")

        # --- Evidence completeness ---
        evidence_claims = event.get("evidence_claims", [])
        if evidence_claims:
            backed = sum(
                1 for c in evidence_claims
                if c.get("evidence") or c.get("source")
            )
            evidence_completeness = (
                (backed / len(evidence_claims) * 100) if evidence_claims else 100.0
            )
        else:
            evidence_completeness = 100.0  # No claims to check = no gap

        # --- Composite score ---
        overall = round(
            data_availability * 0.40
            + analysis_freshness * 0.35
            + evidence_completeness * 0.25,
            1,
        )

        return ReadinessScore(
            ticker=ticker,
            event_id=event_id,
            overall_score=overall,
            data_availability=round(data_availability, 1),
            analysis_freshness=round(analysis_freshness, 1),
            evidence_completeness=round(evidence_completeness, 1),
            missing_items=missing,
        )

    def missing_data_report(self, ticker: str) -> List[str]:
        """Return a human-readable list of missing data items for *ticker*.

        Args:
            ticker: The instrument ticker.

        Returns:
            List of strings describing what data is missing.
        """
        ticker = ticker.upper()
        data = self._data_snapshots.get(ticker, {})

        if not data:
            return [f"No data snapshot registered for {ticker}"]

        all_desired = set(self._REQUIRED_DATA_FIELDS) | set(self._RECOMMENDED_DATA_FIELDS)
        missing = []
        for field in sorted(all_desired):
            if field not in data or data[field] is None:
                missing.append(f"Missing: {field}")

        if not missing:
            missing.append("All expected data fields are present")

        return missing
