# -*- coding: utf-8 -*-
"""augur.consensus_display - show a withheld consensus as withheld, not 5.0.

When too few personas apply to a fund, ``ConsensusEngine`` returns a
neutral result with ``score=5.0`` and ``metadata["consensus_withheld"]``.
The 5.0 is a placeholder, not a reading. Every surface that prints or
stores a consensus goes through these helpers so the placeholder never
shows up as a HOLD 5.0/10.

The helpers key off the withheld flag only, never off the asset type: a
fund can get a real consensus once enough personas apply to it.

They accept an ``AgentResponse``-like object or a dict in any of the
shapes already in use: ``to_dict()`` output (flag under ``metadata``), API
payloads with a top-level ``consensus_withheld``, and workflow / committee
payloads with ``withheld``.
"""

from typing import Any, Dict, List, Optional, Tuple

WITHHELD_SIGNAL = "WITHHELD (fund)"
WITHHELD_SCORE = "--"


def consensus_withheld(consensus: Any) -> bool:
    """True when the engine withheld this consensus."""
    if consensus is None:
        return False
    if isinstance(consensus, dict):
        if consensus.get("consensus_withheld") or consensus.get("withheld") is True:
            return True
        meta = consensus.get("metadata")
    else:
        meta = getattr(consensus, "metadata", None)
    return bool(isinstance(meta, dict) and meta.get("consensus_withheld"))


def withheld_reason(consensus: Any) -> str:
    """The engine's explanation, or '' when not withheld / not recorded."""
    if not consensus_withheld(consensus):
        return ""
    if isinstance(consensus, dict):
        meta = consensus.get("metadata") if isinstance(consensus.get("metadata"), dict) else {}
        return str(consensus.get("withheld_reason") or meta.get("withheld_reason") or "")
    meta = getattr(consensus, "metadata", None) or {}
    return str(meta.get("withheld_reason") or "")


def _field(consensus: Any, name: str, default: Any = None) -> Any:
    if isinstance(consensus, dict):
        return consensus.get(name, default)
    return getattr(consensus, name, default)


def _signal_value(consensus: Any) -> str:
    sig = _field(consensus, "signal", "")
    return str(getattr(sig, "value", sig) or "")


def display_signal(consensus: Any, labels: Optional[Dict[str, str]] = None) -> str:
    """Signal text: ``WITHHELD (fund)`` when withheld, else the (labelled) signal."""
    if consensus_withheld(consensus):
        return WITHHELD_SIGNAL
    value = _signal_value(consensus)
    if labels:
        return labels.get(value, value)
    return value.upper()


def display_score(consensus: Any, fmt: str = "{:.1f}/10") -> str:
    """Score text: ``--`` when withheld, else ``fmt`` applied to the score."""
    if consensus_withheld(consensus):
        return WITHHELD_SCORE
    score = _field(consensus, "score", 0.0)
    try:
        return fmt.format(float(score or 0.0))
    except (TypeError, ValueError):
        return WITHHELD_SCORE


def display_confidence(consensus: Any, fmt: str = "{:.0%}") -> str:
    """Confidence text: ``--`` when withheld."""
    if consensus_withheld(consensus):
        return WITHHELD_SCORE
    try:
        return fmt.format(float(_field(consensus, "confidence", 0.0) or 0.0))
    except (TypeError, ValueError):
        return WITHHELD_SCORE


def consensus_record(consensus: Any, score_digits: int = 1,
                     confidence_digits: int = 2) -> Dict[str, Any]:
    """Compact dict for history / API payloads that keeps the withheld flag.

    The numeric ``score`` stays (old readers expect a number); readers must
    check ``consensus_withheld`` before plotting or comparing it.
    """
    record: Dict[str, Any] = {
        "signal": _signal_value(consensus),
        "score": round(float(_field(consensus, "score", 0.0) or 0.0), score_digits),
        "confidence": round(float(_field(consensus, "confidence", 0.0) or 0.0), confidence_digits),
    }
    if consensus_withheld(consensus):
        record["consensus_withheld"] = True
        record["withheld_reason"] = withheld_reason(consensus)
    return record


def persona_abstained(result: Any) -> bool:
    """True when a persona abstained (its rules do not apply to a fund)."""
    if isinstance(result, dict):
        meta = result.get("metadata")
        if result.get("not_applicable"):
            return True
    else:
        meta = getattr(result, "metadata", None)
    return bool(isinstance(meta, dict) and meta.get("not_applicable"))


def display_persona_score(result: Any, fmt: str = "{:.1f}/10") -> str:
    """A persona's score text: ``N/A`` when it abstained."""
    if persona_abstained(result):
        return "N/A"
    try:
        return fmt.format(float(_field(result, "score", 0.0) or 0.0))
    except (TypeError, ValueError):
        return "N/A"


FUND_DATA_MISSING = "fund_data_missing"


def _abstain_reason(result: Any) -> str:
    if isinstance(result, dict):
        meta = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        return str(result.get("abstain_reason") or meta.get("reason") or "")
    return str((getattr(result, "metadata", None) or {}).get("reason") or "")


def split_abstained(results: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """(rules not applicable, fund data missing) persona ids among abstainers.

    Accepts ``AgentResponse`` objects (reason in ``metadata["reason"]``) or
    persisted persona dicts (``abstain_reason``). A missing reason counts as
    "rules not applicable", which is what every pre-14.1 abstention meant.
    """
    no_rules: List[str] = []
    no_data: List[str] = []
    for aid in sorted(results):
        r = results[aid]
        if not (persona_abstained(r) or (isinstance(r, dict) and r.get("abstained"))):
            continue
        (no_data if _abstain_reason(r) == FUND_DATA_MISSING else no_rules).append(aid)
    return no_rules, no_data


def abstained_label(no_rules: List[str], no_data: List[str]) -> str:
    """Abstainers named by reason; counts per reason only when both occur.

    ``"rules not applicable to funds: a, b"`` or
    ``"14 rules not applicable to funds: ...; 3 fund technicals missing: ..."``.
    """
    both = bool(no_rules and no_data)
    parts = []
    for ids, why in ((no_rules, "rules not applicable to funds"),
                     (no_data, "fund technicals missing")):
        if ids:
            parts.append(f"{f'{len(ids)} ' if both else ''}{why}: {', '.join(ids)}")
    return "; ".join(parts)
