# -*- coding: utf-8 -*-
"""
Capability Registry — minimal typed-capability store with budget/timeout control.

Public API:
    Capability           — named capability descriptor
    CapabilityRegistry   — singleton registry
    get_capability_registry() -> CapabilityRegistry
"""

from __future__ import annotations

import re
import threading
from typing import Any, Callable, Dict, List

import jsonschema


# ---------------------------------------------------------------------------
# Name format: kebab.case dotted segments, each segment [a-z][a-z0-9-]*
# ---------------------------------------------------------------------------
_CAP_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*$")


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------

class Capability:
    """A named, typed, budget/timeout-controlled capability descriptor.

    Attributes:
        name: Dotted kebab-case identifier (e.g. ``"sec.filings.read"``).
        description: Human-readable one-liner.
        input_schema: JSON Schema dict for input parameters.
        output_schema: JSON Schema dict for the return value.
        handler: Callable that implements the capability (may be a stub).
        budget_ms: Soft budget — the expected maximum execution time.
        timeout_ms: Hard timeout — execution is aborted after this.
    """

    __slots__ = (
        "name", "description", "input_schema", "output_schema",
        "handler", "budget_ms", "timeout_ms",
    )

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict,
        output_schema: dict,
        handler: Callable,
        budget_ms: int = 10_000,
        timeout_ms: int = 30_000,
    ) -> None:
        if not _CAP_NAME_RE.match(name):
            raise ValueError(
                f"Invalid capability name {name!r}: must be dotted kebab-case "
                f"(e.g. 'sec.filings.read')"
            )
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.handler = handler
        self.budget_ms = budget_ms
        self.timeout_ms = timeout_ms

    def __repr__(self) -> str:
        return f"Capability({self.name!r})"


# ---------------------------------------------------------------------------
# CapabilityRegistry (singleton)
# ---------------------------------------------------------------------------

class CapabilityRegistry:
    """Thread-safe singleton registry of named capabilities.

    Usage::

        reg = get_capability_registry()
        reg.register(Capability(...))
        cap = reg.get("sec.filings.read")
        errors = reg.validate_request("sec.filings.read", {"ticker": "AAPL"})
    """

    def __init__(self) -> None:
        self._capabilities: Dict[str, Capability] = {}
        self._lock = threading.RLock()

    # -- registration --------------------------------------------------------

    def register(self, cap: Capability) -> None:
        """Register a capability.  Raises ``ValueError`` on duplicate name."""
        with self._lock:
            if cap.name in self._capabilities:
                raise ValueError(
                    f"Capability {cap.name!r} is already registered"
                )
            self._capabilities[cap.name] = cap

    # -- lookup --------------------------------------------------------------

    def get(self, name: str) -> Capability:
        """Return the capability registered under *name*.

        Raises ``KeyError`` if no capability with that name exists.
        """
        with self._lock:
            return self._capabilities[name]

    def list_all(self) -> List[str]:
        """Return the names of every registered capability."""
        with self._lock:
            return sorted(self._capabilities.keys())

    # -- validation ----------------------------------------------------------

    def validate_request(self, name: str, params: dict) -> List[str]:
        """Validate *params* against *name*'s input_schema.

        Returns a list of error message strings (empty ⇒ valid).
        """
        cap = self.get(name)  # raises KeyError if unknown
        validator = jsonschema.Draft7Validator(cap.input_schema)
        return [err.message for err in validator.iter_errors(params)]


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_registry: CapabilityRegistry | None = None
_registry_lock = threading.RLock()


def get_capability_registry() -> CapabilityRegistry:
    """Return the process-wide singleton ``CapabilityRegistry``."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = CapabilityRegistry()
            _register_builtin_capabilities(_registry)
        return _registry


# ---------------------------------------------------------------------------
# Built-in capabilities (stub handlers)
# ---------------------------------------------------------------------------

def _stub_handler(**kwargs: Any) -> dict:
    """Placeholder handler — not invoked in tests of the registry itself."""
    return {"stub": True}


def _register_builtin_capabilities(reg: CapabilityRegistry) -> None:
    """Register the initial set of built-in capabilities."""

    builtins: list[dict] = [
        {
            "name": "sec.filings.read",
            "description": "Read an SEC filing by ticker and accession number.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "accession": {"type": "string"},
                },
                "required": ["ticker", "accession"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "filing_text": {"type": "string"},
                    "filing_date": {"type": "string"},
                },
                "required": ["filing_text", "filing_date"],
            },
        },
        {
            "name": "fundamentals.snapshot",
            "description": "Get a point-in-time fundamentals snapshot for a ticker.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "as_of": {"type": "string", "format": "date"},
                },
                "required": ["ticker"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "market_cap": {"type": "number"},
                    "pe_ratio": {"type": "number"},
                    "revenue_growth": {"type": "number"},
                },
            },
        },
        {
            "name": "market.price_history",
            "description": "Fetch historical price data for a ticker.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
                "required": ["ticker", "start_date", "end_date"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "prices": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string"},
                                "close": {"type": "number"},
                            },
                        },
                    },
                },
            },
        },
        {
            "name": "runs.compare",
            "description": "Compare two RunBundles and surface diffs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "run_a": {"type": "string", "description": "Run ID A"},
                    "run_b": {"type": "string", "description": "Run ID B"},
                },
                "required": ["run_a", "run_b"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "diffs": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
        {
            "name": "earnings.collect_evidence",
            "description": "Collect earnings evidence (maps to workflow fetch phase).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "event_id": {"type": "string"},
                    "as_of": {"type": "string", "format": "date"},
                },
                "required": ["ticker", "event_id", "as_of"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "evidence_items": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
        {
            "name": "report.earnings_dossier",
            "description": "Generate an earnings research dossier (maps to analyze+consensus phases).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["ticker", "evidence"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "dossier": {"type": "object"},
                    "evidence_manifest": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["run_id", "dossier", "evidence_manifest"],
            },
        },
    ]

    for spec in builtins:
        reg.register(Capability(
            name=spec["name"],
            description=spec["description"],
            input_schema=spec["input_schema"],
            output_schema=spec["output_schema"],
            handler=_stub_handler,
        ))
