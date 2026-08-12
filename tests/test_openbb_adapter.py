# -*- coding: utf-8 -*-
"""
Tests for augur.adapters.openbb_adapter (G01 — OpenBB Optional Adapter).

Covers:
  - OpenBBMetamodel: lookup, known_keys, __contains__, __len__
  - to_evidence_item: happy path, empty input, unrecognised keys, missing instrument
  - is_openbb_available: returns bool (does not crash)
  - Graceful degradation: module-level _OPENBB_INSTALLED flag
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from augur.adapters.openbb_adapter import (
    OpenBBMetamodel,
    _OPENBB_INSTALLED,
    is_openbb_available,
    to_evidence_item,
)
from augur.schemas.evidence import EvidenceItem


# ---------------------------------------------------------------------------
# OpenBBMetamodel
# ---------------------------------------------------------------------------

class TestOpenBBMetamodel:
    """Tests for the field-name mapping table."""

    def test_lookup_known_key(self):
        """A recognised OpenBB key returns metadata dict."""
        meta = OpenBBMetamodel()
        result = meta.lookup("pe_ratio")
        assert result is not None
        assert result["metric"] == "pe_ratio"
        assert result["unit"] is None

    def test_lookup_unknown_key(self):
        """An unrecognised key returns None."""
        meta = OpenBBMetamodel()
        assert meta.lookup("nonexistent_field") is None

    def test_contains(self):
        """__contains__ returns True for known keys, False for unknown."""
        meta = OpenBBMetamodel()
        assert "pe_ratio" in meta
        assert "market_cap" in meta
        assert "made_up_key" not in meta

    def test_len_and_known_keys(self):
        """len() and known_keys() reflect the mapping table size."""
        meta = OpenBBMetamodel()
        keys = meta.known_keys()
        assert len(meta) == len(keys)
        assert len(meta) > 10  # we have at least 10 mappings
        assert "symbol" in keys
        assert "pe_ratio" in keys

    def test_repr(self):
        """__repr__ includes the mapping count."""
        meta = OpenBBMetamodel()
        r = repr(meta)
        assert "OpenBBMetamodel" in r
        assert str(len(meta)) in r


# ---------------------------------------------------------------------------
# to_evidence_item
# ---------------------------------------------------------------------------

class TestToEvidenceItem:
    """Tests for the OpenBB-output → EvidenceItem conversion."""

    def test_happy_path_single_field(self):
        """A dict with one recognised field produces a valid EvidenceItem."""
        output = {"symbol": "AAPL", "pe_ratio": 28.5}
        item = to_evidence_item(output)
        assert item is not None
        assert isinstance(item, EvidenceItem)
        assert item.source == "openbb"
        assert item.instrument == "AAPL"
        assert item.metric == "pe_ratio"
        assert item.value == 28.5

    def test_empty_input_returns_none(self):
        """Empty dict → None."""
        assert to_evidence_item({}) is None

    def test_no_recognised_keys_returns_none(self):
        """A dict whose keys are all unrecognised → None."""
        assert to_evidence_item({"foo": 1, "bar": 2}) is None

    def test_ticker_override(self):
        """Explicit ticker overrides symbol inference."""
        output = {"pe_ratio": 15.0}
        item = to_evidence_item(output, ticker="MSFT")
        assert item is not None
        assert item.instrument == "MSFT"
        # source_locator should still use available symbol
        assert item.source_locator is None  # no symbol in output

    def test_evidence_id_format(self):
        """EvidenceItem id follows ev_{source}_{hash[:12]}."""
        output = {"symbol": "TSLA", "beta": 1.8}
        item = to_evidence_item(output)
        assert item is not None
        assert item.evidence_id.startswith("ev_openbb_")
        assert len(item.evidence_id.split("_")[-1]) == 12

    def test_non_numeric_value_handled(self):
        """String values produce value=None (not numeric)."""
        output = {"symbol": "AAPL", "sector": "Technology"}
        item = to_evidence_item(output)
        assert item is not None
        assert item.metric == "sector"
        assert item.value is None  # string → not numeric

    def test_metadata_carries_openbb_raw(self):
        """metadata dict captures the recognised keys and raw values."""
        output = {"symbol": "GOOG", "pe_ratio": 22.0, "beta": 1.05}
        item = to_evidence_item(output)
        assert item is not None
        assert "openbb_keys" in item.metadata
        assert "openbb_raw" in item.metadata
        assert set(item.metadata["openbb_keys"]) == {"symbol", "pe_ratio", "beta"}

    def test_datetime_fields_populated(self):
        """effective_at / available_at / retrieved_at are set correctly."""
        eff = datetime(2024, 3, 31, tzinfo=timezone.utc)
        avl = datetime(2024, 4, 15, tzinfo=timezone.utc)
        output = {"symbol": "NVDA", "market_cap": 1_200_000_000_000}
        item = to_evidence_item(output, effective_at=eff, available_at=avl)
        assert item is not None
        assert item.effective_at == eff
        assert item.available_at == avl
        assert item.retrieved_at is not None
        # retrieved_at must differ from available_at (model validator)
        assert item.retrieved_at != item.available_at


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """Module loads and functions work without OpenBB installed."""

    def test_is_openbb_available_returns_bool(self):
        """is_openbb_available() returns a boolean without raising."""
        result = is_openbb_available()
        assert isinstance(result, bool)

    def test_openbb_installed_flag_exists(self):
        """_OPENBB_INSTALLED is a bool (True/False)."""
        assert isinstance(_OPENBB_INSTALLED, bool)

    def test_adapter_works_without_openbb_import(self):
        """Core functions work with plain dicts — no OpenBB import needed."""
        # The adapter only consumes dicts, so it works regardless of OpenBB presence.
        output = {"symbol": "TEST", "pe_ratio": 10.0}
        item = to_evidence_item(output)
        assert item is not None
        assert item.source == "openbb"
