# -*- coding: utf-8 -*-
"""Tests for Capability and CapabilityRegistry."""

import pytest

from augur.capability import (
    Capability,
    CapabilityRegistry,
    get_capability_registry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cap(name: str = "test.echo") -> Capability:
    return Capability(
        name=name,
        description="Echo capability for testing.",
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
        output_schema={"type": "string"},
        handler=lambda **kw: kw,
    )


# ---------------------------------------------------------------------------
# Registry — register / get / list_all
# ---------------------------------------------------------------------------

class TestRegistryBasic:
    def test_register_and_get(self):
        reg = CapabilityRegistry()
        cap = _make_cap("test.echo")
        reg.register(cap)
        assert reg.get("test.echo") is cap

    def test_get_unknown_raises_key_error(self):
        reg = CapabilityRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_list_all_initially_empty(self):
        reg = CapabilityRegistry()
        assert reg.list_all() == []

    def test_list_all_after_registration(self):
        reg = CapabilityRegistry()
        reg.register(_make_cap("a.one"))
        reg.register(_make_cap("b.two"))
        assert reg.list_all() == ["a.one", "b.two"]

    def test_duplicate_registration_raises(self):
        reg = CapabilityRegistry()
        reg.register(_make_cap("dup.test"))
        with pytest.raises(ValueError, match="already registered"):
            reg.register(_make_cap("dup.test"))


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------

class TestCapabilityName:
    @pytest.mark.parametrize("name", [
        "sec.filings.read",
        "fundamentals.snapshot",
        "a.b",
        "a",
        "a-b.c-d",
        "runs.compare",
    ])
    def test_valid_names(self, name):
        cap = Capability(
            name=name, description="desc",
            input_schema={}, output_schema={},
            handler=lambda: None,
        )
        assert cap.name == name

    @pytest.mark.parametrize("name", [
        "",
        "UpperCase",
        "has space",
        ".starts.with.dot",
        "ends.with.dot.",
        "double..dot",
        "1starts.with.digit",
        "-starts.with.hyphen",
    ])
    def test_invalid_names(self, name):
        with pytest.raises(ValueError, match="Invalid capability name"):
            Capability(
                name=name, description="desc",
                input_schema={}, output_schema={},
                handler=lambda: None,
            )


# ---------------------------------------------------------------------------
# validate_request
# ---------------------------------------------------------------------------

class TestValidateRequest:
    def test_valid_params(self):
        reg = CapabilityRegistry()
        reg.register(_make_cap("test.echo"))
        errors = reg.validate_request("test.echo", {"message": "hello"})
        assert errors == []

    def test_missing_required(self):
        reg = CapabilityRegistry()
        reg.register(_make_cap("test.echo"))
        errors = reg.validate_request("test.echo", {})
        assert len(errors) >= 1

    def test_wrong_type(self):
        reg = CapabilityRegistry()
        reg.register(_make_cap("test.echo"))
        errors = reg.validate_request("test.echo", {"message": 123})
        assert len(errors) >= 1

    def test_unknown_capability_raises(self):
        reg = CapabilityRegistry()
        with pytest.raises(KeyError):
            reg.validate_request("nonexistent", {})


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_capability_registry_returns_same_instance(self):
        r1 = get_capability_registry()
        r2 = get_capability_registry()
        assert r1 is r2

    def test_singleton_has_builtin_capabilities(self):
        reg = get_capability_registry()
        names = reg.list_all()
        expected = [
            "earnings.collect_evidence",
            "fundamentals.snapshot",
            "market.price_history",
            "report.earnings_dossier",
            "runs.compare",
            "sec.filings.read",
        ]
        assert names == expected


# ---------------------------------------------------------------------------
# Capability fields
# ---------------------------------------------------------------------------

class TestCapabilityFields:
    def test_budget_and_timeout_defaults(self):
        cap = _make_cap()
        assert cap.budget_ms == 10_000
        assert cap.timeout_ms == 30_000

    def test_budget_and_timeout_custom(self):
        cap = Capability(
            name="test.custom",
            description="desc",
            input_schema={}, output_schema={},
            handler=lambda: None,
            budget_ms=500,
            timeout_ms=1_000,
        )
        assert cap.budget_ms == 500
        assert cap.timeout_ms == 1_000

    def test_repr(self):
        cap = _make_cap("test.echo")
        assert repr(cap) == "Capability('test.echo')"
