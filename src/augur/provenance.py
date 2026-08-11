# -*- coding: utf-8 -*-
"""
augur.provenance - Metadata provenance tracking for analysis outputs.

Provides a structured ``ProvenanceBlock`` that captures the origin, freshness,
persona state, degradation, and calibration status of every analysis run.
Designed to be attached to Dashboard, CLI, and MCP outputs uniformly.
"""

import dataclasses
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclasses.dataclass
class ProvenanceBlock:
    """Immutable snapshot of analysis provenance metadata.

    Attributes:
        analysis_as_of: ISO-8601 timestamp of when the analysis was produced.
        data_source: ``"live"``, ``"replay"``, or ``"demo"``.
        freshness: ``"fresh"``, ``"stale"``, or ``"unknown"``.
        schema_version: The Augur package version at analysis time.
        code_version: Alias for schema_version (same release).
        model_version: Version string of the LLM backing the personas, if known.
        personas_enabled: List of persona IDs that contributed to this run.
        personas_skipped: Mapping of persona_id → reason it was skipped.
        missing_fields: Mapping of field_name → degradation reason (data absent).
        degraded_fields: Mapping of field_name → degradation reason (data partial/degraded).
        calibration_status: Probability calibration state:
            ``"raw"`` | ``"experimental"`` | ``"validated-calibrated"`` | ``"insufficient"``.
    """

    analysis_as_of: str = ""
    data_source: str = "unknown"
    freshness: str = "unknown"
    schema_version: str = ""
    code_version: str = ""
    model_version: str = ""
    personas_enabled: List[str] = dataclasses.field(default_factory=list)
    personas_skipped: Dict[str, str] = dataclasses.field(default_factory=dict)
    missing_fields: Dict[str, str] = dataclasses.field(default_factory=dict)
    degraded_fields: Dict[str, str] = dataclasses.field(default_factory=dict)
    calibration_status: str = "raw"


def _detect_data_source(output: Dict[str, Any]) -> str:
    """Heuristic to infer whether data came from live, replay, or demo."""
    warnings = output.get("warnings", [])
    results = output.get("results", {})

    # Explicit detection: if output has a data_source key, use it
    if "data_source" in output:
        ds = str(output.get("data_source", "")).lower()
        if ds in ("live", "yfinance", "finnhub", "alphavantage", "stooq"):
            return "live"
        if ds in ("replay", "replay_universe", "cached"):
            return "replay"
        if ds in ("demo", "manual", "fallback"):
            return "demo"

    # Heuristic from warnings
    for w in warnings:
        wl = w.lower()
        if "replay" in wl:
            return "replay"
        if "demo" in wl:
            return "demo"

    # If fetch succeeded, it's likely live
    fetch = results.get("fetch", {})
    if isinstance(fetch, dict) and "error" not in fetch and fetch.get("price"):
        return "live"

    # If fetch failed but other steps ran, likely demo/fallback
    if isinstance(fetch, dict) and "error" in fetch:
        return "demo"

    return "unknown"


def _detect_freshness(output: Dict[str, Any]) -> str:
    """Infer freshness from warnings and result quality."""
    warnings = output.get("warnings", [])
    for w in warnings:
        wl = w.lower()
        if "stale" in wl or "cache" in wl or "cached" in wl:
            return "stale"
        if "fallback" in wl:
            return "stale"

    # Check if there are degradation entries which suggest staleness
    degradation = output.get("degradation", [])
    if degradation:
        return "stale"

    # If a fetch succeeded, treat as fresh
    results = output.get("results", {})
    fetch = results.get("fetch", {})
    if isinstance(fetch, dict) and "error" not in fetch and fetch.get("price"):
        return "fresh"

    return "unknown"


def _detect_calibration_status(output: Dict[str, Any]) -> str:
    """Detect calibration status from consensus metadata."""
    results = output.get("results", {})
    consensus = results.get("consensus", {})
    if isinstance(consensus, dict):
        meta = consensus.get("metadata", {})
        if isinstance(meta, dict):
            cal = meta.get("calibration_status", "")
            if cal:
                return str(cal).lower()

    # Fallback: if consensus has confidence, at least raw
    if isinstance(consensus, dict) and "confidence" in consensus:
        return "raw"

    return "insufficient"


def _detect_model_version() -> str:
    """Try to detect the LLM model version from config."""
    try:
        from augur.config import get_config

        cfg = get_config()
        default_model = cfg.get("model", "") or cfg.get("llm_model", "") or cfg.get("default_model", "")
        if default_model:
            return str(default_model)
    except Exception:
        pass
    return ""


def _resolve_personas(output: Dict[str, Any]) -> tuple:
    """Return (enabled, skipped) persona info from the output dict."""
    agents_filter = output.get("agents_filter") or []
    agents_skipped = output.get("agents_skipped") or {}

    enabled: List[str] = []
    skipped: Dict[str, str] = {}

    if isinstance(agents_filter, list):
        enabled = [str(a) for a in agents_filter]

    if isinstance(agents_skipped, list):
        skipped = {str(a): "not_in_registry" for a in agents_skipped}
    elif isinstance(agents_skipped, dict):
        skipped = {str(k): str(v) for k, v in agents_skipped.items()}

    # If no filter was applied, try to extract from analyze results
    if not enabled:
        results = output.get("results", {})
        analyze = results.get("analyze", {})
        if isinstance(analyze, dict) and "error" not in analyze:
            enabled = list(analyze.keys())

    return enabled, skipped


def _resolve_degradation(output: Dict[str, Any]) -> tuple:
    """Extract missing and degraded fields from the degradation list."""
    degradation: List[Dict[str, str]] = output.get("degradation", [])
    missing: Dict[str, str] = {}
    degraded: Dict[str, str] = {}

    for entry in degradation:
        if not isinstance(entry, dict):
            continue
        field = entry.get("field", entry.get("step_name", ""))
        reason = entry.get("reason", entry.get("message", ""))
        entry_type = entry.get("type", "degraded")

        if not field:
            continue

        if entry_type == "missing":
            missing[field] = reason
        else:
            degraded[field] = reason

    return missing, degraded


def build_provenance(
    output: Dict[str, Any],
    tracker: Any = None,
) -> ProvenanceBlock:
    """Build a ProvenanceBlock from a workflow output dict and optional tracker.

    Args:
        output: The workflow result dictionary (as returned by
            ``run_workflow``).
        tracker: Optional ``RunTracker`` instance for additional metadata.

    Returns:
        A fully populated ``ProvenanceBlock``.
    """
    from augur import __version__

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    enabled, skipped = _resolve_personas(output)
    missing, degraded = _resolve_degradation(output)

    model_version = _detect_model_version()

    # Prefer tracker metadata when available
    if tracker is not None:
        try:
            tracker_model = getattr(tracker, "model_version", "") or getattr(tracker, "model", "")
            if tracker_model:
                model_version = str(tracker_model)
        except Exception:
            pass

    return ProvenanceBlock(
        analysis_as_of=output.get("analysis_as_of", now),
        data_source=output.get("data_source") or _detect_data_source(output),
        freshness=output.get("freshness") or _detect_freshness(output),
        schema_version=__version__,
        code_version=__version__,
        model_version=model_version,
        personas_enabled=enabled,
        personas_skipped=skipped,
        missing_fields=missing,
        degraded_fields=degraded,
        calibration_status=output.get("calibration_status") or _detect_calibration_status(output),
    )


def provenance_to_dict(block: ProvenanceBlock) -> Dict[str, Any]:
    """Serialize a ProvenanceBlock to a plain dictionary for JSON output."""
    return dataclasses.asdict(block)


def format_provenance_cli(block: ProvenanceBlock) -> str:
    """Format a ProvenanceBlock as a CLI-friendly text block.

    Used by ``format_workflow_summary`` to append a provenance section.
    """
    lines = [
        "── Provenance ──",
        f"  Analysis as-of: {block.analysis_as_of}",
        f"  Data source:    {block.data_source}",
        f"  Freshness:      {block.freshness}",
        f"  Schema version: {block.schema_version}",
    ]

    if block.model_version:
        lines.append(f"  Model version:  {block.model_version}")

    if block.personas_enabled:
        lines.append(f"  Personas enabled: {', '.join(block.personas_enabled)}")

    if block.personas_skipped:
        skipped_str = ", ".join(
            f"{pid} ({reason})" for pid, reason in block.personas_skipped.items()
        )
        lines.append(f"  Personas skipped: {skipped_str}")

    if block.missing_fields:
        missing_str = ", ".join(
            f"{field}: {reason}" for field, reason in block.missing_fields.items()
        )
        lines.append(f"  Missing fields:   {missing_str}")

    if block.degraded_fields:
        degraded_str = ", ".join(
            f"{field}: {reason}" for field, reason in block.degraded_fields.items()
        )
        lines.append(f"  Degraded fields:   {degraded_str}")

    lines.append(f"  Calibration:     {block.calibration_status}")
    lines.append("")

    return "\n".join(lines)
