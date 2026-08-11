# -*- coding: utf-8 -*-
"""Test export module: Markdown, JSON, Evidence Pack, CLI integration."""

from __future__ import annotations

import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from augur.cli import main
from augur.export import (
    EXPORT_SCHEMA_VERSION,
    ReportExporter,
    _extract_claims_from_bundle,
    _extract_evidence_from_bundle,
    _load_run_bundle,
)
from augur.schemas.claim import Claim, ClaimClassification, ClaimStatus
from augur.schemas.evidence import EvidenceItem
from augur.schemas.run_bundle import (
    CoverageStats,
    RunBundle,
    RunManifest,
)
from augur.schemas.step_result import StepResult, StepStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_evidence_items():
    """A few evidence items for testing."""
    ev1 = EvidenceItem(
        evidence_id="ev_sec_edgar_abc123def456",
        source="sec_edgar",
        content_hash="abc123def456789012345678901234567890abcdef123456789012345678",
        instrument="AAPL",
        metric="pe_ratio",
        value=28.5,
        unit="ratio",
        effective_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        available_at=datetime(2025, 1, 16, tzinfo=timezone.utc),
        retrieved_at=datetime(2025, 1, 16, 12, 0, tzinfo=timezone.utc),
        coverage=0.95,
    )
    ev2 = EvidenceItem(
        evidence_id="ev_yfinance_abc789def012",
        source="yfinance",
        content_hash="abc789def0123456789012345678901234567890abcdef1234567890abcd",
        instrument="AAPL",
        metric="market_cap",
        value=3.2e12,
        unit="USD",
        effective_at=datetime(2025, 1, 16, tzinfo=timezone.utc),
        available_at=datetime(2025, 1, 16, tzinfo=timezone.utc),
        retrieved_at=datetime(2025, 1, 16, 12, 1, tzinfo=timezone.utc),
        coverage=1.0,
    )
    return [ev1, ev2]


@pytest.fixture
def sample_claims(sample_evidence_items):
    """Claims referencing the evidence items."""
    ev1, ev2 = sample_evidence_items
    c1 = Claim(
        claim_id="cl_abc123def456",
        text="AAPL PE ratio of 28.5 is below the 5-year average of 32.",
        persona_id="buffett",
        supports=[ev1.evidence_id],
        classification=ClaimClassification.INFERENCE,
        confidence=0.75,
        confidence_source="explicit_rule",
        status=ClaimStatus.ACTIVE,
    )
    c2 = Claim(
        claim_id="cl_abc789def012",
        text="AAPL market cap exceeds $3 trillion, indicating strong market position.",
        persona_id="munger",
        supports=[ev2.evidence_id],
        contradicts=[ev1.evidence_id],
        classification=ClaimClassification.FACT,
        confidence=0.90,
        confidence_source="explicit_rule",
        status=ClaimStatus.ACTIVE,
    )
    return [c1, c2]


@pytest.fixture
def sample_run_bundle(sample_claims, sample_evidence_items):
    """A complete RunBundle with step results, claims, and evidence inlined."""
    now = datetime.now(timezone.utc)
    manifest = RunManifest(
        input_snapshot_hash="abc123def456" * 4,
        config_version="1.0",
        model_version="1.0",
        code_version="10.15.0",
    )

    step1 = StepResult(
        step_id="run_AAPL_20250101T120000_abc12345_step1",
        step_name="fetch",
        status=StepStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        result={
            "price": 150.0,
            "pe": 28.5,
            "sector": "Technology",
            "evidence": [
                json.loads(ev.model_dump_json())
                for ev in sample_evidence_items
            ],
        },
        content_hash="abc123",
    )
    step2 = StepResult(
        step_id="run_AAPL_20250101T120000_abc12345_step2",
        step_name="analyze",
        status=StepStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        result={
            "buffett": {"agent_name": "Warren Buffett", "signal": "bullish", "score": 8.5},
            "claims": [
                json.loads(c.model_dump_json()) for c in sample_claims
            ],
        },
        content_hash="def456",
    )
    step3 = StepResult(
        step_id="run_AAPL_20250101T120000_abc12345_step3",
        step_name="consensus",
        status=StepStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        result={
            "signal": "bullish",
            "score": 8.2,
            "confidence": 0.72,
        },
        content_hash="ghi789",
    )

    return RunBundle(
        run_id="run_AAPL_20250101T120000_abc12345",
        created_at=now,
        manifest=manifest,
        step_results=[step1, step2, step3],
        coverage=CoverageStats(
            total_evidence=3,
            covered_evidence=3,
            missing_evidence=0,
            degraded_evidence=0,
            coverage_ratio=1.0,
        ),
        metadata={"ticker": "AAPL"},
    )


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# Tests: Markdown export
# ---------------------------------------------------------------------------


class TestMarkdownExport:
    """Markdown export tests."""

    def test_to_markdown_contains_expected_content(self, sample_run_bundle):
        """Markdown output should contain run_id, ticker, steps, and claims."""
        exporter = ReportExporter()
        md = exporter.to_markdown(sample_run_bundle)

        assert "Augur Analysis Report" in md
        assert "run_AAPL_20250101T120000_abc12345" in md
        assert "AAPL" in md
        assert "## Step Results" in md
        assert "fetch" in md
        assert "analyze" in md
        assert "consensus" in md
        assert "## Claims" in md
        assert "cl_abc123def456" in md
        assert "cl_abc789def012" in md
        assert "## Evidence" in md
        assert "ev_sec_edgar_abc123def456" in md
        assert "ev_yfinance_abc789def012" in md
        assert "## Provenance" in md
        assert "1.0" in md

    def test_to_markdown_with_custom_template(self, sample_run_bundle):
        """Custom Jinja2 template should be rendered correctly."""
        exporter = ReportExporter()
        custom_tmpl = "# Custom Report: {{ bundle.run_id }}\n\nTicker: {{ bundle.metadata.ticker }}"
        md = exporter.to_markdown(sample_run_bundle, template=custom_tmpl)

        assert md.startswith("# Custom Report: run_AAPL_20250101T120000_abc12345")
        assert "Ticker: AAPL" in md

    def test_to_markdown_no_claims_or_evidence(self):
        """Markdown export should work even with empty claims/evidence."""
        now = datetime.now(timezone.utc)
        bundle = RunBundle(
            run_id="run_TEST_20250101T120000_abc12345",
            created_at=now,
            manifest=RunManifest(
                input_snapshot_hash="a" * 64,
                config_version="1.0",
                model_version="1.0",
                code_version="1.0",
            ),
            step_results=[
                StepResult(
                    step_id="run_TEST_20250101T120000_abc12345_step1",
                    step_name="fetch",
                    status=StepStatus.FAILURE,
                    started_at=now,
                    result={"error": "network timeout"},
                    diagnostics="Connection refused",
                )
            ],
            coverage=CoverageStats(
                total_evidence=1,
                covered_evidence=0,
                missing_evidence=1,
                coverage_ratio=0.0,
            ),
        )

        exporter = ReportExporter()
        md = exporter.to_markdown(bundle)

        assert "run_TEST" in md
        assert "fetch" in md
        assert "FAILURE" in md or "failure" in md
        assert "Connection refused" in md
        # Should still render without claims/evidence
        assert "## Provenance" in md


# ---------------------------------------------------------------------------
# Tests: JSON export
# ---------------------------------------------------------------------------


class TestJSONExport:
    """JSON export tests."""

    def test_to_json_round_trip(self, sample_run_bundle):
        """JSON export should be valid JSON and contain all expected keys."""
        exporter = ReportExporter()
        json_str = exporter.to_json(sample_run_bundle)

        data = json.loads(json_str)

        assert data["export_schema_version"] == EXPORT_SCHEMA_VERSION
        assert "export_timestamp" in data
        assert "run_bundle" in data
        assert data["run_bundle"]["run_id"] == "run_AAPL_20250101T120000_abc12345"
        assert "claims" in data
        assert len(data["claims"]) == 2
        assert "evidence_items" in data
        assert len(data["evidence_items"]) == 2

    def test_to_json_contains_claim_ids(self, sample_run_bundle):
        """JSON export claims should match input claims."""
        exporter = ReportExporter()
        json_str = exporter.to_json(sample_run_bundle)
        data = json.loads(json_str)

        claim_ids = {c["claim_id"] for c in data["claims"]}
        assert "cl_abc123def456" in claim_ids
        assert "cl_abc789def012" in claim_ids

    def test_to_json_contains_evidence_ids(self, sample_run_bundle):
        """JSON export evidence should match input evidence."""
        exporter = ReportExporter()
        json_str = exporter.to_json(sample_run_bundle)
        data = json.loads(json_str)

        ev_ids = {e["evidence_id"] for e in data["evidence_items"]}
        assert "ev_sec_edgar_abc123def456" in ev_ids
        assert "ev_yfinance_abc789def012" in ev_ids


# ---------------------------------------------------------------------------
# Tests: Evidence Pack
# ---------------------------------------------------------------------------


class TestEvidencePack:
    """Evidence pack export tests."""

    def test_evidence_pack_creation(self, sample_run_bundle):
        """Evidence pack zip should contain manifest, run_bundle, and evidence files."""
        exporter = ReportExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = exporter.export_evidence_pack(
                sample_run_bundle, Path(tmpdir)
            )

            assert zip_path.exists()
            assert zip_path.suffix == ".zip"

            # Verify contents
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = set(zf.namelist())
                assert "manifest.json" in names
                assert "run_bundle.json" in names
                assert "evidence/ev_sec_edgar_abc123def456.json" in names
                assert "evidence/ev_yfinance_abc789def012.json" in names

                # Verify manifest content
                manifest = json.loads(zf.read("manifest.json"))
                assert manifest["run_id"] == "run_AAPL_20250101T120000_abc12345"
                assert manifest["export_schema_version"] == EXPORT_SCHEMA_VERSION
                assert manifest["num_evidence_items"] >= 2

    def test_evidence_pack_validation_all_resolvable(self, sample_run_bundle):
        """All referenced evidence IDs should resolve within the pack."""
        exporter = ReportExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = exporter.export_evidence_pack(
                sample_run_bundle, Path(tmpdir)
            )

            # Should not raise — validation passes
            with zipfile.ZipFile(zip_path, "r") as zf:
                for ev_id in ("ev_sec_edgar_abc123def456", "ev_yfinance_abc789def012"):
                    safe_name = f"evidence/{ev_id}.json"
                    assert safe_name in zf.namelist()

    def test_evidence_pack_with_extra_referenced_ids(self, sample_run_bundle, sample_claims):
        """Claims referencing evidence not in step results should still get placeholders."""
        # Add a claim referencing a non-existent evidence ID
        extra_claim = Claim(
            claim_id="cl_eeee00000001",
            text="Extra claim with missing evidence.",
            persona_id="dalio",
            supports=["ev_missing_source_aaaaaaaaaaaa"],
            classification=ClaimClassification.FACT,
            confidence=0.5,
            confidence_source="explicit_rule",
            status=ClaimStatus.ACTIVE,
        )

        # Inject into step result
        sample_run_bundle.step_results[1].result["claims"].append(
            json.loads(extra_claim.model_dump_json())
        )

        exporter = ReportExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = exporter.export_evidence_pack(
                sample_run_bundle, Path(tmpdir)
            )

            with zipfile.ZipFile(zip_path, "r") as zf:
                names = set(zf.namelist())
                # The missing evidence ID should get a placeholder file
                assert "evidence/ev_missing_source_aaaaaaaaaaaa.json" in names


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------


class TestExportErrors:
    """Error handling tests."""

    def test_missing_run_bundle_raises_file_not_found(self):
        """Loading a non-existent run_id should raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(data_dir=Path(tmpdir))
            with pytest.raises(FileNotFoundError) as exc_info:
                exporter.export_from_run_id(
                    "run_NONEXISTENT_20250101T120000_abc12345",
                    Path(tmpdir) / "out.md",
                    fmt="md",
                )
            assert "RunBundle not found" in str(exc_info.value)

    def test_invalid_format_raises_value_error(self, sample_run_bundle):
        """Unknown format should raise ValueError."""
        exporter = ReportExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError) as exc_info:
                exporter.export_from_run_id(
                    sample_run_bundle.run_id,
                    Path(tmpdir) / "out.xyz",
                    fmt="xyz",
                )
            assert "Unknown export format" in str(exc_info.value)

    def test_load_run_bundle_from_disk(self, sample_run_bundle):
        """Saving and loading a RunBundle should round-trip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            runs_dir = data_dir / "runs"
            runs_dir.mkdir(parents=True)

            # Write the bundle
            run_path = runs_dir / f"{sample_run_bundle.run_id}.json"
            run_path.write_text(
                sample_run_bundle.model_dump_json(indent=2), encoding="utf-8"
            )

            # Load it back
            loaded = _load_run_bundle(sample_run_bundle.run_id, data_dir)
            assert loaded.run_id == sample_run_bundle.run_id
            assert len(loaded.step_results) == 3

    def test_export_from_run_id_json(self, sample_run_bundle):
        """export_from_run_id with json format should write a .json file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            runs_dir = data_dir / "runs"
            runs_dir.mkdir(parents=True)

            run_path = runs_dir / f"{sample_run_bundle.run_id}.json"
            run_path.write_text(
                sample_run_bundle.model_dump_json(indent=2), encoding="utf-8"
            )

            exporter = ReportExporter(data_dir=data_dir)
            out_path = Path(tmpdir) / "report"
            result = exporter.export_from_run_id(
                sample_run_bundle.run_id, out_path, fmt="json"
            )

            assert result.suffix == ".json"
            assert result.exists()
            data = json.loads(result.read_text(encoding="utf-8"))
            assert "export_schema_version" in data


# ---------------------------------------------------------------------------
# Tests: CLI integration
# ---------------------------------------------------------------------------


class TestCLIExport:
    """CLI export command tests."""

    def test_export_command_registered(self, runner):
        """export command should be registered and show --help."""
        result = runner.invoke(main, ["export", "--help"])
        assert result.exit_code == 0
        assert "TICKER" in result.output
        assert "--run-id" in result.output
        assert "--format" in result.output

    def test_export_missing_run_id(self, runner):
        """export without --run-id should fail."""
        result = runner.invoke(main, ["export", "AAPL"])
        assert result.exit_code != 0  # click requires --run-id

    def test_export_invalid_format(self, runner):
        """export with invalid format should show error."""
        result = runner.invoke(main, [
            "export", "AAPL",
            "--run-id", "run_AAPL_20250101T120000_abc12345",
            "--format", "invalid-fmt",
        ])
        assert result.exit_code != 0

    def test_export_nonexistent_run(self, runner):
        """export with non-existent run_id should show error."""
        result = runner.invoke(main, [
            "export", "AAPL",
            "--run-id", "run_NONEXISTENT_99999999T999999_ffffffff",
            "--format", "md",
        ])
        assert result.exit_code != 0
        assert "Error" in result.output or "error" in result.output.lower()
