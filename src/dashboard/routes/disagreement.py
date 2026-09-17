"""Disagreement Map + Evidence Graph API routes (F05 UI integration)."""
from __future__ import annotations
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from augur.disagreement import DisagreementMapBuilder

router = APIRouter()


@router.get("/api/disagreement")
async def get_disagreement(ticker: str = "", run_id: str = "") -> Dict[str, Any]:
    """Return the evidence-derived DisagreementMap for a ticker's run.

    Uses ``run_id`` when given, otherwise the newest RunBundle for the ticker.
    """
    import dataclasses

    from augur.disagreement import build_disagreement_from_bundle
    from augur.run_tracker import latest_run_id, load_run_bundle_dict

    t = ticker.upper()
    if not t:
        raise HTTPException(status_code=400, detail="ticker required")

    rid = run_id or latest_run_id(t)
    if rid:
        try:
            bundle = load_run_bundle_dict(rid)
        except (FileNotFoundError, ValueError):
            raise HTTPException(status_code=404, detail=f"run {rid} not found")
        return dataclasses.asdict(build_disagreement_from_bundle(bundle, t, rid))

    return dataclasses.asdict(DisagreementMapBuilder(t, "").build({}))


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
