"""Research Report REST endpoint — aggregated v11 report."""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, HTTPException

from augur.research_report import ResearchReportBuilder

router = APIRouter()


@router.get("/api/report/{ticker}")
async def get_research_report(ticker: str, format: str = "markdown") -> Any:
    """Return a comprehensive research report for a ticker.

    Aggregates consensus, disagreement, change ledger, thesis updates,
    scorecard, provenance, and open questions.
    """
    t = ticker.upper()
    if not t or len(t) > 15:
        raise HTTPException(status_code=400, detail="invalid ticker")

    builder = ResearchReportBuilder()
    report = builder.build(t)

    if format == "json":
        from fastapi.responses import JSONResponse
        import json as _json
        return JSONResponse(content=_json.loads(report.to_json()))
    return {"ticker": t, "markdown": report.to_markdown()}
