"""Coverage Health + Provider Health REST endpoints (A05/G08 UI wiring)."""
from __future__ import annotations
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/api/coverage/{ticker}")
async def coverage_report(ticker: str) -> Dict[str, Any]:
    """Return data coverage report for a ticker."""
    t = ticker.upper()
    if not t or len(t) > 15:
        raise HTTPException(status_code=400, detail="invalid ticker")

    from augur.coverage_health import CoverageAnalyzer
    analyzer = CoverageAnalyzer()
    report = analyzer.analyze(t, {})
    return {
        "ticker": t,
        "overall_coverage": report.overall_coverage,
        "fields": [
            {"field": f.field, "coverage_pct": f.coverage_pct,
             "source": f.source, "last_available": f.last_available}
            for f in report.fields
        ],
        "missing_fields": report.missing_fields,
        "stale_fields": report.stale_fields,
        "recommendation": report.recommendation,
    }


@router.get("/api/providers/health")
async def providers_health() -> Dict[str, Any]:
    """Return aggregate provider health dashboard."""
    from augur.provider_health import get_provider_health_tracker
    tracker = get_provider_health_tracker()
    dash = tracker.get_dashboard()
    return {
        "generated_at": dash.generated_at,
        "healthy_count": dash.healthy_count,
        "degraded_count": dash.degraded_count,
        "down_count": dash.down_count,
        "providers": [
            {"name": p.provider_name, "status": p.status,
             "success_rate_7d": p.success_rate_7d,
             "avg_latency_ms": p.avg_latency_ms,
             "total_checks": p.total_checks}
            for p in dash.providers
        ],
    }
