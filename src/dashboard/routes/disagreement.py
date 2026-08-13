"""Disagreement Map + Evidence Graph API routes (F05 UI integration)."""
from __future__ import annotations
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from augur.disagreement import DisagreementMapBuilder

router = APIRouter()


@router.get("/api/disagreement")
async def get_disagreement(ticker: str = "", run_id: str = "") -> Dict[str, Any]:
    """Return a DisagreementMap for a ticker.

    Currently derives from a placeholder persona output set; in production
    this reads the latest RunBundle for the ticker.
    """
    t = ticker.upper()
    if not t:
        raise HTTPException(status_code=400, detail="ticker required")

    # Placeholder: derive from latest run if available
    from augur.data_dir import get_data_dir
    import json
    from pathlib import Path

    runs_dir = get_data_dir() / "runs"
    latest = None
    for f in sorted(Path(runs_dir).glob(f"run_{t}_*.json"), reverse=True):
        try:
            latest = json.loads(f.read_text(encoding="utf-8"))
            break
        except Exception:
            continue

    builder = DisagreementMapBuilder(t, run_id or "latest")
    if latest:
        # Extract persona outputs from step results
        persona_outputs: Dict[str, Dict] = {}
        for step in latest.get("step_results", []):
            if step.get("step_name") == "analyze" and isinstance(step.get("result"), dict):
                for pid, pdata in step["result"].items():
                    if isinstance(pdata, dict):
                        persona_outputs[pid] = pdata
        result = builder.build(persona_outputs)
        return {
            "ticker": result.ticker,
            "run_id": result.run_id,
            "consensus_strength": result.consensus_strength,
            "agreement_points": result.agreement_points,
            "conflict_points": [
                {
                    "claim": c.claim,
                    "bullish_personas": c.bullish_personas,
                    "bearish_personas": c.bearish_personas,
                    "abstaining_personas": c.abstaining_personas,
                    "information_that_would_resolve": c.information_that_would_resolve,
                    "impact": c.impact,
                }
                for c in result.conflict_points
            ],
            "silent_personas": result.silent_personas,
            "summary": result.summary,
        }

    # Fallback: empty map
    result = builder.build({})
    return {
        "ticker": result.ticker,
        "run_id": result.run_id,
        "consensus_strength": result.consensus_strength,
        "agreement_points": [],
        "conflict_points": [],
        "silent_personas": [],
        "summary": result.summary,
    }


@router.get("/api/evidence/{evidence_id}")
async def get_evidence(evidence_id: str) -> Dict[str, Any]:
    """Return a single EvidenceItem by ID from the evidence store."""
    from augur.data_dir import get_data_dir
    import json
    from pathlib import Path

    ev_dir = get_data_dir() / "evidence"
    for f in Path(ev_dir).glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("evidence_id") == evidence_id:
                return data
        except Exception:
            continue
    raise HTTPException(status_code=404, detail=f"evidence {evidence_id} not found")
