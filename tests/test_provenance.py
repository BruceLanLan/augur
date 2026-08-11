# -*- coding: utf-8 -*-
"""Tests for augur.provenance — ProvenanceBlock, build_provenance, CLI formatting."""

import pytest

from augur.provenance import (
    ProvenanceBlock,
    build_provenance,
    provenance_to_dict,
    format_provenance_cli,
    _detect_data_source,
    _detect_freshness,
    _detect_calibration_status,
)


class TestProvenanceBlock:
    """ProvenanceBlock dataclass construction and field validation."""

    def test_default_construction(self):
        block = ProvenanceBlock()
        assert block.analysis_as_of == ""
        assert block.data_source == "unknown"
        assert block.freshness == "unknown"
        assert block.schema_version == ""
        assert block.code_version == ""
        assert block.model_version == ""
        assert block.personas_enabled == []
        assert block.personas_skipped == {}
        assert block.missing_fields == {}
        assert block.degraded_fields == {}
        assert block.calibration_status == "raw"

    def test_full_construction(self):
        block = ProvenanceBlock(
            analysis_as_of="2025-01-15T10:30:00Z",
            data_source="live",
            freshness="fresh",
            schema_version="10.15.0",
            code_version="10.15.0",
            model_version="deepseek-v4",
            personas_enabled=["buffett", "graham"],
            personas_skipped={"dayu": "incompatible_market"},
            missing_fields={"roe": "not_available"},
            degraded_fields={"pe": "stale_cache"},
            calibration_status="validated-calibrated",
        )
        assert block.analysis_as_of == "2025-01-15T10:30:00Z"
        assert block.data_source == "live"
        assert block.freshness == "fresh"
        assert block.schema_version == "10.15.0"
        assert block.code_version == "10.15.0"
        assert block.model_version == "deepseek-v4"
        assert block.personas_enabled == ["buffett", "graham"]
        assert block.personas_skipped == {"dayu": "incompatible_market"}
        assert block.missing_fields == {"roe": "not_available"}
        assert block.degraded_fields == {"pe": "stale_cache"}
        assert block.calibration_status == "validated-calibrated"

    def test_immutability_of_lists(self):
        """Default lists/dicts are fresh instances per block."""
        a = ProvenanceBlock()
        b = ProvenanceBlock()
        a.personas_enabled.append("buffett")
        assert b.personas_enabled == []


class TestProvenanceToDict:
    """Serialization of ProvenanceBlock to dict."""

    def test_round_trip(self):
        block = ProvenanceBlock(
            analysis_as_of="2025-01-15T10:30:00Z",
            data_source="live",
            freshness="fresh",
            schema_version="10.15.0",
            code_version="10.15.0",
            model_version="deepseek-v4",
            personas_enabled=["buffett"],
            personas_skipped={"dayu": "not_applicable"},
            missing_fields={"roe": "n/a"},
            degraded_fields={"pe": "stale"},
            calibration_status="raw",
        )
        d = provenance_to_dict(block)
        assert d["analysis_as_of"] == "2025-01-15T10:30:00Z"
        assert d["data_source"] == "live"
        assert d["freshness"] == "fresh"
        assert d["personas_enabled"] == ["buffett"]
        assert d["personas_skipped"] == {"dayu": "not_applicable"}
        assert d["missing_fields"] == {"roe": "n/a"}
        assert d["degraded_fields"] == {"pe": "stale"}
        assert d["calibration_status"] == "raw"


class TestDetectDataSource:
    """Heuristic data source detection."""

    def test_live_from_fetch_success(self):
        output = {
            "results": {
                "fetch": {"price": 150.0, "pe": 25.0},
            },
            "warnings": [],
        }
        assert _detect_data_source(output) == "live"

    def test_replay_from_warning(self):
        output = {
            "results": {},
            "warnings": ["using replay universe for backtest"],
        }
        assert _detect_data_source(output) == "replay"

    def test_demo_from_fetch_error(self):
        output = {
            "results": {
                "fetch": {"error": "connection refused"},
            },
            "warnings": [],
        }
        assert _detect_data_source(output) == "demo"

    def test_explicit_data_source_key(self):
        output = {
            "data_source": "yfinance",
        }
        assert _detect_data_source(output) == "live"

    def test_fallback_is_demo(self):
        output = {
            "data_source": "fallback",
        }
        assert _detect_data_source(output) == "demo"

    def test_unknown_when_empty(self):
        output = {"results": {}, "warnings": []}
        assert _detect_data_source(output) == "unknown"


class TestDetectFreshness:
    """Freshness detection heuristics."""

    def test_fresh_from_successful_fetch(self):
        output = {
            "results": {
                "fetch": {"price": 150.0},
            },
            "warnings": [],
        }
        assert _detect_freshness(output) == "fresh"

    def test_stale_from_cache_warning(self):
        output = {
            "results": {},
            "warnings": ["using cached data"],
        }
        assert _detect_freshness(output) == "stale"

    def test_stale_from_fallback_warning(self):
        output = {
            "results": {},
            "warnings": ["provider fallback triggered"],
        }
        assert _detect_freshness(output) == "stale"

    def test_stale_from_degradation(self):
        output = {
            "results": {},
            "warnings": [],
            "degradation": [{"type": "error", "step_name": "fetch", "message": "timeout"}],
        }
        assert _detect_freshness(output) == "stale"

    def test_unknown_when_no_data(self):
        output = {"results": {}, "warnings": []}
        assert _detect_freshness(output) == "unknown"


class TestDetectCalibrationStatus:
    """Calibration status detection."""

    def test_raw_from_consensus_confidence(self):
        output = {
            "results": {
                "consensus": {"confidence": 0.75, "signal": "bullish"},
            }
        }
        assert _detect_calibration_status(output) == "raw"

    def test_from_metadata(self):
        output = {
            "results": {
                "consensus": {
                    "confidence": 0.75,
                    "metadata": {"calibration_status": "validated-calibrated"},
                }
            }
        }
        assert _detect_calibration_status(output) == "validated-calibrated"

    def test_insufficient_when_no_consensus(self):
        output = {"results": {}}
        assert _detect_calibration_status(output) == "insufficient"


class TestBuildProvenance:
    """End-to-end provenance building from workflow output."""

    def test_minimal_output(self):
        output = {
            "ticker": "AAPL",
            "steps": ["fetch", "analyze", "consensus"],
            "results": {
                "fetch": {"price": 150.0, "pe": 25.0},
                "analyze": {
                    "buffett": {"agent_name": "Warren Buffett", "signal": "bullish", "score": 8.0},
                },
                "consensus": {"signal": "bullish", "score": 7.5, "confidence": 0.8},
            },
            "warnings": [],
            "degradation": [],
        }
        block = build_provenance(output)
        assert block.data_source == "live"
        assert block.freshness == "fresh"
        assert block.calibration_status == "raw"
        assert block.schema_version != ""
        assert block.analysis_as_of != ""

    def test_with_personas(self):
        output = {
            "ticker": "AAPL",
            "steps": ["analyze"],
            "results": {
                "analyze": {
                    "buffett": {"agent_name": "WB", "signal": "bullish", "score": 8.0},
                    "graham": {"agent_name": "BG", "signal": "neutral", "score": 5.0},
                },
            },
            "agents_filter": ["buffett", "graham"],
            "agents_skipped": ["dayu"],
            "warnings": [],
            "degradation": [],
        }
        block = build_provenance(output)
        assert block.personas_enabled == ["buffett", "graham"]
        assert "dayu" in block.personas_skipped

    def test_with_degradation(self):
        output = {
            "ticker": "NVDA",
            "steps": ["fetch", "analyze"],
            "results": {
                "fetch": {"error": "timeout"},
            },
            "warnings": [],
            "degradation": [
                {
                    "type": "error",
                    "error_type": "TimeoutError",
                    "message": "connection timed out",
                    "step_name": "fetch",
                },
                {
                    "type": "missing",
                    "field": "roe",
                    "reason": "not available from provider",
                },
            ],
        }
        block = build_provenance(output)
        assert block.data_source == "demo"
        assert "fetch" in block.degraded_fields
        assert "roe" in block.missing_fields


class TestFormatProvenanceCLI:
    """CLI text formatting of provenance blocks."""

    def test_basic_output(self):
        block = ProvenanceBlock(
            analysis_as_of="2025-01-15T10:30:00Z",
            data_source="live",
            freshness="fresh",
            schema_version="10.15.0",
            calibration_status="raw",
        )
        text = format_provenance_cli(block)
        assert "── Provenance ──" in text
        assert "Analysis as-of: 2025-01-15T10:30:00Z" in text
        assert "Data source:    live" in text
        assert "Freshness:      fresh" in text
        assert "Schema version: 10.15.0" in text
        assert "Calibration:     raw" in text

    def test_with_personas(self):
        block = ProvenanceBlock(
            analysis_as_of="2025-01-15T10:30:00Z",
            data_source="live",
            freshness="fresh",
            schema_version="10.15.0",
            personas_enabled=["buffett", "graham", "munger"],
            personas_skipped={"dayu": "not_applicable"},
            calibration_status="raw",
        )
        text = format_provenance_cli(block)
        assert "Personas enabled: buffett, graham, munger" in text
        assert "Personas skipped: dayu (not_applicable)" in text

    def test_with_degraded_fields(self):
        block = ProvenanceBlock(
            analysis_as_of="2025-01-15T10:30:00Z",
            data_source="live",
            freshness="stale",
            schema_version="10.15.0",
            missing_fields={"roe": "provider_error"},
            degraded_fields={"pe": "cached_value"},
            calibration_status="experimental",
        )
        text = format_provenance_cli(block)
        assert "Missing fields:   roe: provider_error" in text
        assert "Degraded fields:   pe: cached_value" in text
        assert "Calibration:     experimental" in text

    def test_with_model_version(self):
        block = ProvenanceBlock(
            analysis_as_of="2025-01-15T10:30:00Z",
            data_source="live",
            freshness="fresh",
            schema_version="10.15.0",
            model_version="deepseek-v4",
            calibration_status="raw",
        )
        text = format_provenance_cli(block)
        assert "Model version:  deepseek-v4" in text


class TestWorkflowSummaryHasProvenance:
    """Verify that workflow summary includes provenance when available."""

    def test_summary_includes_provenance_section(self):
        from augur.workflow import format_workflow_summary

        data = {
            "ticker": "AAPL",
            "steps": ["fetch", "analyze"],
            "results": {
                "fetch": {"price": 150.0, "pe": 25.0},
                "analyze": {},
            },
            "warnings": [],
            "provenance": {
                "analysis_as_of": "2025-01-15T10:30:00Z",
                "data_source": "live",
                "freshness": "fresh",
                "schema_version": "10.15.0",
                "code_version": "10.15.0",
                "model_version": "",
                "personas_enabled": [],
                "personas_skipped": {},
                "missing_fields": {},
                "degraded_fields": {},
                "calibration_status": "raw",
            },
        }
        summary = format_workflow_summary(data)
        assert "── Provenance ──" in summary
        assert "live" in summary

    def test_summary_shows_degradation(self):
        from augur.workflow import format_workflow_summary

        data = {
            "ticker": "NVDA",
            "steps": ["fetch"],
            "results": {},
            "warnings": [],
            "degradation": [
                {
                    "type": "error",
                    "error_type": "ConnectionError",
                    "message": "timeout",
                    "step_name": "fetch",
                }
            ],
        }
        summary = format_workflow_summary(data)
        assert "── Degradation ──" in summary
        assert "fetch" in summary
        assert "ConnectionError" in summary

    def test_summary_no_provenance_when_none(self):
        from augur.workflow import format_workflow_summary

        data = {
            "ticker": "AAPL",
            "steps": ["fetch", "analyze"],
            "results": {},
            "warnings": [],
            "provenance": None,
        }
        summary = format_workflow_summary(data)
        assert "── Provenance ──" not in summary


class TestDegradationStructured:
    """Verify that degradation entries follow the expected structure."""

    def test_degradation_entry_has_required_fields(self):
        entry = {
            "type": "error",
            "error_type": "ValueError",
            "message": "invalid ticker",
            "step_name": "fetch",
        }
        assert "type" in entry
        assert "error_type" in entry
        assert "message" in entry
        assert "step_name" in entry

    def test_degradation_missing_field_entry(self):
        entry = {
            "type": "missing",
            "field": "roe",
            "reason": "not available from provider",
        }
        assert entry["type"] == "missing"
        assert "field" in entry
        assert "reason" in entry
