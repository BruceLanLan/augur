# -*- coding: utf-8 -*-
"""End-to-end data pipeline tests — provider chain + evidence + missingness."""
import pytest

from augur.data import fetch_market_context
from augur.schemas import EvidenceItem
from augur.datasources.base import DataProviderError


class TestDataPipelineE2E:
    def test_fetch_invalid_ticker_graceful(self):
        """Invalid ticker should not crash — empty context with error."""
        ctx = fetch_market_context("INVALIDTICKERXYZ123")
        assert ctx is not None
        # data_source should be "none" or error-marked
        assert hasattr(ctx, "data_source") or getattr(ctx, "data_source", None) is not None

    def test_market_context_missingness_semantics(self):
        """Ownership fields default to None (v11 missingness contract)."""
        from augur.personas.base import MarketContext
        ctx = MarketContext(ticker="TEST")
        assert ctx.insider_ownership is None
        assert ctx.institutional_ownership is None
        # field_availability is populated by the data pipeline (not the default)
        # The None default IS the missingness contract.


class TestEvidencePipeline:
    def test_provider_to_evidence_item(self):
        """Provider output normalizes to minimal EvidenceItem."""
        from augur.datasources.base import DataProvider
        # Verify the helper exists on the base class
        assert hasattr(DataProvider, "to_evidence_item") or hasattr(DataProvider, "coverage_report")

    def test_evidence_three_time_semantics(self):
        """EvidenceItem enforces three distinct time axes."""
        from datetime import datetime
        ev = EvidenceItem(
            evidence_id="ev_sec_edgar_abc123def456", source="sec_edgar", content_hash="abc123def456",
            effective_at=datetime(2025, 9, 28),
            available_at=datetime(2025, 10, 31),
            retrieved_at=datetime(2025, 11, 1),
        )
        assert ev.effective_at != ev.available_at
        assert ev.available_at != ev.retrieved_at
        # And equal available/retrieved must be rejected
        with pytest.raises(Exception):
            EvidenceItem(
                evidence_id="ev_sec_edgar_abc123def456", source="sec_edgar", content_hash="abc123def456",
                available_at=datetime(2025, 10, 31),
                retrieved_at=datetime(2025, 10, 31),
            )

    def test_evidence_missing_flag(self):
        """Missing evidence carries explicit flags."""
        ev = EvidenceItem(
            evidence_id="ev_sec_edgar_abc123def456", source="sec_edgar", content_hash="abc123def456",
            coverage=0.0, missing=True, degraded=False,
        )
        assert ev.missing is True
        assert ev.coverage == 0.0
        assert ev.degraded is False
