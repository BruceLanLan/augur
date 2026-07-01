"""Rules Engine API routes."""

import re
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dashboard.deps import _get_rules_engine

router = APIRouter()


class RuleCreateBody(BaseModel):
    name: str
    conditions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    enabled: bool = True


@router.get("/api/rules")
async def api_list_rules():
    engine = _get_rules_engine()
    rules = engine.get_rules()
    return {"rules": [r.to_dict() for r in rules], "count": len(rules)}


@router.post("/api/rules")
async def api_create_rule(body: RuleCreateBody):
    from augur.rules import Rule
    if not body.name or len(body.name) > 100:
        raise HTTPException(status_code=400, detail="Rule name: 1-100 characters.")
    engine = _get_rules_engine()
    rule = Rule(id="", name=body.name, conditions=body.conditions, actions=body.actions, enabled=body.enabled)
    created = engine.add_rule(rule)
    return {"status": "ok", "rule": created.to_dict()}


@router.delete("/api/rules/{rule_id}")
async def api_delete_rule(rule_id: str):
    if not re.match(r'^[A-Za-z0-9._\-]{1,64}$', rule_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid rule_id format. Use 1-64 alphanumeric characters, dots, hyphens, or underscores.",
        )
    engine = _get_rules_engine()
    if not engine.remove_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return {"status": "ok", "message": "Rule deleted"}
