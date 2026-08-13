"""Valuation API routes: DCF sensitivity grid and export endpoints."""

from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from augur.valuation import DCFInputs, sensitivity_grid

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SensitivityRequest(BaseModel):
    free_cash_flow: float = 10_000_000_000.0
    growth_rate_stage1: float = 0.12
    stage1_years: int = 5
    growth_rate_terminal: float = 0.025
    wacc: float = 0.10
    shares_outstanding: float = 1_000_000_000.0
    net_debt: float = 0.0
    wacc_min: Optional[float] = None   # auto-derived from wacc ± 2 pp if not set
    wacc_max: Optional[float] = None
    growth_min: Optional[float] = None
    growth_max: Optional[float] = None
    steps: int = 9


class ExportRequest(BaseModel):
    format: str = "json"  # "json" | "markdown" | "pdf"
    title: str = "Augur DCF Sensitivity Analysis"
    headers: List[str] = []
    rows: List[List[Any]] = []
    params: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# POST /api/valuation/sensitivity
# ---------------------------------------------------------------------------

@router.post("/api/valuation/sensitivity", summary="Compute DCF sensitivity grid")
async def api_valuation_sensitivity(body: SensitivityRequest):
    """Compute a WACC × Terminal Growth DCF fair-value sensitivity grid.

    Returns a labeled matrix suitable for rendering as a heatmap table,
    plus the raw 2-D grid and the WACC/growth axis labels.
    """
    # Build DCFInputs
    dcf = DCFInputs(
        free_cash_flow=body.free_cash_flow,
        growth_rate_stage1=body.growth_rate_stage1,
        stage1_years=body.stage1_years,
        growth_rate_terminal=body.growth_rate_terminal,
        wacc=body.wacc,
        shares_outstanding=body.shares_outstanding,
        net_debt=body.net_debt,
    )

    # Auto-derive ranges (±2 pp around base values) if not explicitly provided
    wacc_min = body.wacc_min if body.wacc_min is not None else body.wacc - 0.02
    wacc_max = body.wacc_max if body.wacc_max is not None else body.wacc + 0.02
    growth_min = body.growth_min if body.growth_min is not None else body.growth_rate_terminal - 0.02
    growth_max = body.growth_max if body.growth_max is not None else body.growth_rate_terminal + 0.02

    steps = max(3, min(body.steps, 25))  # clamp for sanity

    # Compute the raw grid
    raw_grid: List[List[float]] = sensitivity_grid(
        dcf,
        wacc_range=(wacc_min, wacc_max),
        growth_range=(growth_min, growth_max),
        steps=steps,
    )

    # Build axis labels
    wacc_step = (wacc_max - wacc_min) / max(steps - 1, 1)
    growth_step = (growth_max - growth_min) / max(steps - 1, 1)
    wacc_labels = [round(wacc_min + i * wacc_step, 4) for i in range(steps)]
    growth_labels = [round(growth_min + j * growth_step, 4) for j in range(steps)]

    # Build labeled rows for table rendering
    labeled_rows: List[Dict[str, Any]] = []
    for i, wacc_label in enumerate(wacc_labels):
        cells: List[Dict[str, Any]] = []
        for j, growth_label in enumerate(growth_labels):
            val = raw_grid[i][j]
            cells.append({
                "growth": growth_label,
                "fair_value": val if val > 0 else None,
                "highlight": _highlight_cell(val, wacc_label, growth_label),
            })
        labeled_rows.append({
            "wacc": wacc_label,
            "cells": cells,
        })

    return {
        "status": "ok",
        "grid": raw_grid,
        "wacc_labels": wacc_labels,
        "growth_labels": growth_labels,
        "labeled_rows": labeled_rows,
        "params": {
            "free_cash_flow": body.free_cash_flow,
            "growth_rate_stage1": body.growth_rate_stage1,
            "growth_rate_terminal": body.growth_rate_terminal,
            "wacc": body.wacc,
            "shares_outstanding": body.shares_outstanding,
            "net_debt": body.net_debt,
            "stage1_years": body.stage1_years,
            "wacc_range": [wacc_min, wacc_max],
            "growth_range": [growth_min, growth_max],
        },
    }


def _highlight_cell(fair_value: float, wacc: float, growth: float) -> Optional[str]:
    """Return a CSS class hint for heatmap-style cells."""
    if fair_value <= 0 or wacc <= growth:
        return "cell-invalid"
    return None


# ---------------------------------------------------------------------------
# POST /api/export  —  valuation / generic table export
# ---------------------------------------------------------------------------

@router.post("/api/export", summary="Export table data as Markdown / JSON / PDF")
async def api_export(body: ExportRequest):
    """Export tabular data (e.g. sensitivity grid) in Markdown, JSON, or PDF format.

    ``format``: ``"json"``, ``"markdown"`` (or ``"md"``), or ``"pdf"``.
    ``title``: used as the document heading.
    ``headers``: column header strings.
    ``rows``: list of row lists (each row is a list of cell values).
    ``params``: optional key-value metadata block rendered above the table.
    """
    fmt = body.format.lower().strip()

    if fmt in ("json",):
        return _export_json(body)

    if fmt in ("markdown", "md"):
        md = _export_markdown(body)
        return Response(
            content=md,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=valuation.md"},
        )

    if fmt in ("pdf",):
        pdf_bytes = _export_pdf(body)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=valuation.pdf"},
        )

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported export format: {fmt!r}. Supported: json, markdown, pdf.",
    )


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------

def _export_json(body: ExportRequest) -> JSONResponse:
    """Return the structured data as JSON."""
    payload: Dict[str, Any] = {
        "title": body.title,
        "headers": body.headers,
        "rows": body.rows,
    }
    if body.params:
        payload["params"] = body.params
    return JSONResponse(content=payload)


def _export_markdown(body: ExportRequest) -> str:
    """Build a Markdown table document."""
    lines: List[str] = []
    lines.append(f"# {body.title}")
    lines.append("")

    if body.params:
        lines.append("## Parameters")
        lines.append("")
        for key, val in body.params.items():
            lines.append(f"- **{key}**: {val}")
        lines.append("")

    if body.headers:
        lines.append("## Sensitivity Grid")
        lines.append("")
        # Header row
        hdrs = [""] + [str(h) for h in body.headers]
        lines.append("| " + " | ".join(hdrs) + " |")
        # Separator
        lines.append("|" + "|".join(["---"] * len(hdrs)) + "|")
        # Data rows
        for row in body.rows:
            cells = [str(cell) if cell is not None else "N/A" for cell in row]
            lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("*Generated by Augur Valuation Engine*")
    return "\n".join(lines)


def _export_pdf(body: ExportRequest) -> bytes:
    """Build a simple HTML page and convert to PDF via weasyprint if available.

    Falls back to a plain-text representation when weasyprint is not installed.
    """
    html = _build_export_html(body)

    # Try weasyprint
    try:
        from weasyprint import HTML
        pdf_buffer = BytesIO()
        HTML(string=html).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()
    except ImportError:
        pass

    # Fallback: return HTML as text in a PDF-friendly way via a simple approach
    # If we can't generate real PDF, return HTML with a hint
    try:
        import markdown as md_lib
        md_content = _export_markdown(body)
        html_content = md_lib.markdown(md_content, extensions=["tables", "fenced_code"])
        html = _build_export_html(body, body_html=html_content)
        from weasyprint import HTML
        pdf_buffer = BytesIO()
        HTML(string=html).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="PDF export requires weasyprint. Install with: pip install weasyprint",
        )


def _build_export_html(body: ExportRequest, body_html: Optional[str] = None) -> str:
    """Build a standalone HTML document for PDF export."""
    if body_html is None:
        # Build table HTML
        table_html = ""
        if body.headers:
            hdr_cells = "".join(f"<th>{h}</th>" for h in body.headers)
            table_html += f"<thead><tr><th>WACC \\ Growth</th>{hdr_cells}</tr></thead><tbody>"
            for row in body.rows:
                cells = "".join(
                    f"<td>{cell if cell is not None else 'N/A'}</td>" for cell in row
                )
                table_html += f"<tr>{cells}</tr>"
            table_html += "</tbody>"

        params_html = ""
        if body.params:
            params_html = "<h2>Parameters</h2><ul>"
            for key, val in body.params.items():
                params_html += f"<li><strong>{key}</strong>: {val}</li>"
            params_html += "</ul>"

        body_html = f"""
        {params_html}
        <h2>Sensitivity Grid</h2>
        <table>{table_html}</table>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{body.title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 960px; margin: 40px auto; padding: 0 20px; line-height: 1.6;
       color: #1a1a2e; }}
h1, h2 {{ color: #1a1a2e; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 0.85em; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: right; }}
th {{ background-color: #f4f4f8; font-weight: 600; }}
td:first-child, th:first-child {{ font-weight: 600; background-color: #fafafa; }}
tr:nth-child(even) td {{ background-color: #fafbfc; }}
</style>
</head>
<body>
<h1>{body.title}</h1>
{body_html}
<p style="color:#888;font-size:0.85em;margin-top:2em;">Generated by Augur Valuation Engine</p>
</body>
</html>"""
