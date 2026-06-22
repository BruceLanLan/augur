# -*- coding: utf-8 -*-
"""Risk manager — veto layer for consensus (pass-through by default)."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class RiskVerdict:
    approved: bool = True
    reason: str = ""
    size_multiplier: float = 1.0


class RiskManager:
    """Apply risk checks; reduces position on high beta + bearish VIX."""

    def evaluate(self, context, consensus, results, regime=None, vix=None) -> RiskVerdict:
        vix = vix or 20.0
        beta = getattr(context, "beta_1y", 1.0) or 1.0
        if vix > 35 and beta > 1.5:
            return RiskVerdict(approved=True, reason="High VIX + high beta", size_multiplier=0.5)
        if vix > 30:
            return RiskVerdict(approved=True, reason="Elevated VIX", size_multiplier=0.75)
        return RiskVerdict(approved=True)

    def apply_veto(self, result, verdict: RiskVerdict):
        if verdict.size_multiplier < 1.0 and result.metadata is not None:
            ps = result.metadata.setdefault("position_sizing", {})
            base = ps.get("position_pct", 0)
            if base:
                ps["position_pct"] = base * verdict.size_multiplier
                ps["risk_note"] = verdict.reason
        elif verdict.size_multiplier < 1.0:
            result.metadata = {
                "position_sizing": {"risk_note": verdict.reason, "size_multiplier": verdict.size_multiplier}
            }
        return result
