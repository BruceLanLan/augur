# -*- coding: utf-8 -*-
"""
augur.adapters.openbb_adapter — OpenBB Optional Adapter (G01)

Schema-only adapter: defines the mapping from OpenBB provider output to
augur's canonical EvidenceItem.  Does **not** import OpenBB at module
level; all OpenBB references are guarded by ``try/except ImportError`` so
that the module loads and degrades gracefully when OpenBB is not installed.

Concepts
--------
OpenBBMetamodel
    A field-name mapping table that translates OpenBB output keys into
    EvidenceItem-compatible field names and metadata.
to_evidence_item(openbb_output)
    Converts a dict-shaped OpenBB result into a fully validated
    ``EvidenceItem`` (or returns ``None`` when the input is insufficient).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from augur.schemas.evidence import EvidenceItem, generate_evidence_id

# ---------------------------------------------------------------------------
# OpenBBMetamodel — field-name mapping table
# ---------------------------------------------------------------------------

_OPENBB_FIELD_MAP: Dict[str, Dict[str, Any]] = {
    # OpenBB key           -> EvidenceItem fields
    "symbol":               {"metric": "symbol",           "unit": None,       "currency": None},
    "name":                 {"metric": "company_name",     "unit": None,       "currency": None},
    "price":                {"metric": "price",            "unit": None,       "currency": "USD"},
    "market_cap":           {"metric": "market_cap",       "unit": None,       "currency": "USD"},
    "volume":               {"metric": "volume",           "unit": "shares",   "currency": None},
    "pe_ratio":             {"metric": "pe_ratio",         "unit": None,       "currency": None},
    "eps":                  {"metric": "eps",              "unit": None,       "currency": "USD"},
    "beta":                 {"metric": "beta",             "unit": None,       "currency": None},
    "dividend_yield":       {"metric": "dividend_yield",   "unit": None,       "currency": None},
    "return_on_equity":     {"metric": "return_on_equity", "unit": None,       "currency": None},
    "debt_to_equity":       {"metric": "debt_to_equity",   "unit": None,       "currency": None},
    "revenue":              {"metric": "revenue",          "unit": None,       "currency": "USD"},
    "net_income":           {"metric": "net_income",       "unit": None,       "currency": "USD"},
    "free_cash_flow":       {"metric": "free_cash_flow",   "unit": None,       "currency": "USD"},
    "sector":               {"metric": "sector",           "unit": None,       "currency": None},
    "industry":             {"metric": "industry",         "unit": None,       "currency": None},
    "country":              {"metric": "country",          "unit": None,       "currency": None},
    "currency":             {"metric": "reporting_currency","unit": None,      "currency": None},
    "exchange":             {"metric": "exchange",         "unit": None,       "currency": None},
}


class OpenBBMetamodel:
    """Field-name mapping table between OpenBB output and EvidenceItem.

    Each entry maps an OpenBB output key (e.g. ``"pe_ratio"``) to the
    corresponding EvidenceItem ``metric`` name plus optional ``unit`` and
    ``currency`` hints.

    Usage::

        meta = OpenBBMetamodel()
        info = meta.lookup("pe_ratio")  # -> {"metric": "pe_ratio", ...}
    """

    def __init__(self) -> None:
        self._map: Dict[str, Dict[str, Any]] = dict(_OPENBB_FIELD_MAP)

    def lookup(self, openbb_key: str) -> Optional[Dict[str, Any]]:
        """Return the EvidenceItem field metadata for *openbb_key*, or None."""
        return self._map.get(openbb_key)

    def known_keys(self) -> list:
        """Return every OpenBB key with a known mapping."""
        return list(self._map.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._map

    def __len__(self) -> int:
        return len(self._map)

    def __repr__(self) -> str:
        return f"<OpenBBMetamodel {len(self._map)} mappings>"


# ---------------------------------------------------------------------------
# Graceful import guard
# ---------------------------------------------------------------------------

def is_openbb_available() -> bool:
    """Return True when the ``openbb`` package is importable."""
    try:
        import openbb  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# to_evidence_item
# ---------------------------------------------------------------------------

def to_evidence_item(
    openbb_output: Dict[str, Any],
    *,
    ticker: Optional[str] = None,
    effective_at: Optional[datetime] = None,
    available_at: Optional[datetime] = None,
) -> Optional[EvidenceItem]:
    """Convert an OpenBB-flavoured output dict into an EvidenceItem.

    Parameters
    ----------
    openbb_output:
        A dict whose keys are OpenBB field names (e.g. ``"symbol"``,
        ``"pe_ratio"``) and values are the corresponding data points.
        Typically comes from ``openbb.equity.fundamental.metrics(...)`` or
        similar.
    ticker:
        Ticker / instrument override.  When omitted the adapter tries to
        read ``openbb_output["symbol"]``.
    effective_at:
        When the data became effective (e.g. fiscal quarter-end).
    available_at:
        When the data became publicly available.

    Returns
    -------
    EvidenceItem or None
        A fully validated EvidenceItem when at least one recognised field
        is present; ``None`` when the input dict is empty or contains no
        recognised keys.
    """
    if not openbb_output:
        return None

    metamodel = OpenBBMetamodel()
    recognised: Dict[str, Any] = {}
    for key, value in openbb_output.items():
        if key in metamodel:
            recognised[key] = value

    if not recognised:
        return None

    # -- resolve instrument --------------------------------------------------
    instrument = ticker or openbb_output.get("symbol")
    symbol = openbb_output.get("symbol") or ticker

    # -- pick the first recognised key as the primary metric -----------------
    primary_key = next(iter(recognised))
    primary_meta = metamodel.lookup(primary_key) or {}
    primary_value = recognised[primary_key]

    # -- build content hash --------------------------------------------------
    source = "openbb"
    content_str = f"{source}:{instrument}:{primary_key}:{primary_value}"
    content_hash = hashlib.sha256(content_str.encode()).hexdigest()

    retrieved_at = datetime.now(timezone.utc)

    # -- numeric value -------------------------------------------------------
    numeric_value: Optional[float] = None
    if isinstance(primary_value, (int, float)) and not isinstance(primary_value, bool):
        numeric_value = float(primary_value)

    return EvidenceItem(
        evidence_id=generate_evidence_id(source, content_hash),
        source=source,
        source_locator=f"openbb://{symbol}" if symbol else None,
        content_hash=content_hash,
        instrument=instrument,
        metric=primary_meta.get("metric"),
        value=numeric_value,
        unit=primary_meta.get("unit"),
        currency=primary_meta.get("currency"),
        effective_at=effective_at,
        available_at=available_at,
        retrieved_at=retrieved_at,
        transform_version="openbb-adapter-1.0",
        schema_version="1.0",
        code_version=None,
        coverage=1.0,
        missing=False,
        degraded=False,
        license=None,
        redistribution_allowed=True,
        metadata={
            "openbb_keys": list(recognised.keys()),
            "openbb_raw": {k: str(v) for k, v in recognised.items()},
        },
    )


# ---------------------------------------------------------------------------
# Graceful-degradation sentinel (G01)
# ---------------------------------------------------------------------------

try:
    import openbb  # noqa: F401
    _OPENBB_INSTALLED = True
except ImportError:
    _OPENBB_INSTALLED = False
    # The adapter functions above remain callable even without OpenBB
    # because they only consume dicts — the caller would have obtained
    # the dict from OpenBB (or a mock) separately.
