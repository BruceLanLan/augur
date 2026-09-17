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
from typing import Callable, Dict, List, Optional

import jsonschema


# ---------------------------------------------------------------------------
# Name format: kebab.case dotted segments, each segment [a-z][a-z0-9-]*
# ---------------------------------------------------------------------------
_CAP_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)*$")


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
        handler: Callable that implements the capability.
        budget_ms: Soft budget — the expected maximum execution time.
        timeout_ms: Hard timeout — execution is aborted after this.
        network_domains: Domains the handler contacts; checked against a
            skill's ``permissions.network_domains`` before execution.
        resources: Local resources the handler reads (e.g. ``runs.read``);
            checked against ``permissions.resources``.
    """

    __slots__ = (
        "name", "description", "input_schema", "output_schema",
        "handler", "budget_ms", "timeout_ms", "network_domains", "resources",
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
        network_domains: Optional[List[str]] = None,
        resources: Optional[List[str]] = None,
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
        self.network_domains = list(network_domains or [])
        self.resources = list(resources or [])

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


def reset_capability_registry() -> None:
    """Reset the singleton (for test isolation)."""
    global _registry
    with _registry_lock:
        _registry = None


# ---------------------------------------------------------------------------
# Built-in capabilities
# ---------------------------------------------------------------------------

def _register_builtin_capabilities(reg: CapabilityRegistry) -> None:
    """Register every capability the built-in skills use.

    Implementations live in :mod:`augur.skills.handlers`; each wraps an
    existing Augur function. (Until 2026-09-17 this registered six schemas
    whose handlers all returned ``{"stub": True}``.)
    """
    from augur.skills.handlers import CAPABILITIES

    for name, spec in sorted(CAPABILITIES.items()):
        reg.register(Capability(
            name=name,
            description=spec["description"],
            input_schema=spec["input_schema"],
            output_schema=spec.get("output_schema", {"type": "object"}),
            handler=spec["handler"],
            budget_ms=spec.get("timeout_ms", 30_000) // 2,
            timeout_ms=spec.get("timeout_ms", 30_000),
            network_domains=spec.get("network_domains"),
            resources=spec.get("resources"),
        ))
