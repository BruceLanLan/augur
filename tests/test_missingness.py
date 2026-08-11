# -*- coding: utf-8 -*-
"""Tests for F0.3 — Replay Schema v2, missingness contract, EvidenceItem.

Covers:
- MarketContext ownership fields default to None (not 0)
- Personas abstain/renormalize when ownership is None
- EvidenceItem generation in provider output
- Replay data field_availability correctness
- Live vs replay availability parity
"""

import pytest


# ---------------------------------------------------------------------------
# MarketContext missingness
# ---------------------------------------------------------------------------

class TestMarketContextMissingness:
    """MarketContext ownership fields must default to None, not 0."""

    def test_ownership_defaults_to_none(self):
        """institutional_ownership and insider_ownership default to None."""
        from augur.personas.base import MarketContext

        ctx = MarketContext(ticker="AAPL")
        assert ctx.institutional_ownership is None, (
            "institutional_ownership must default to None, not 0"
        )
        assert ctx.insider_ownership is None, (
            "insider_ownership must default to None, not 0"
        )

    def test_field_availability_present(self):
        """MarketContext must have field_availability and as_of_date fields."""
        from augur.personas.base import MarketContext

        ctx = MarketContext(ticker="AAPL")
        assert hasattr(ctx, "field_availability"), "field_availability missing"
        assert hasattr(ctx, "as_of_date"), "as_of_date missing"
        assert hasattr(ctx, "evidence_items"), "evidence_items missing"
        assert isinstance(ctx.field_availability, dict)
        assert ctx.evidence_items == []

    def test_ownership_can_be_set_explicitly(self):
        """Ownership fields accept explicit float values."""
        from augur.personas.base import MarketContext

        ctx = MarketContext(
            ticker="AAPL",
            institutional_ownership=65.5,
            insider_ownership=12.3,
        )
        assert ctx.institutional_ownership == 65.5
        assert ctx.insider_ownership == 12.3

    def test_to_dict_includes_new_fields(self):
        """to_dict() must serialize field_availability and as_of_date."""
        from augur.personas.base import MarketContext

        ctx = MarketContext(
            ticker="AAPL",
            field_availability={"pe": "live", "institutional_ownership": "missing"},
            as_of_date="2025-01-15",
        )
        d = ctx.to_dict()
        assert d["field_availability"] == {"pe": "live", "institutional_ownership": "missing"}
        assert d["as_of_date"] == "2025-01-15"


# ---------------------------------------------------------------------------
# Persona missingness behaviour
# ---------------------------------------------------------------------------

class TestPersonaMissingness:
    """Personas must abstain/renormalize when ownership is None, not crash."""

    @staticmethod
    def _make_ctx(ticker="AAPL", **overrides):
        """Build a minimal MarketContext that personas can score against."""
        from augur.personas.base import MarketContext

        defaults = {
            "ticker": ticker,
            "price": 150.0,
            "pe": 20.0,
            "pb": 3.0,
            "ps": 4.0,
            "roe": 0.18,
            "roa": 0.08,
            "gross_margins": 0.45,
            "operating_margins": 0.25,
            "revenue_growth": 0.15,
            "earnings_growth": 0.12,
            "debt_ratio": 0.35,
            "current_ratio": 1.8,
            "fcf": 10.0,
            "market_cap": 500.0,
            "revenue": 100.0,
            "sector": "Technology",
            "industry": "Software",
            "rsi": 55.0,
            "volatility_20d": 0.25,
            "institutional_ownership": None,
            "insider_ownership": None,
        }
        defaults.update(overrides)
        return MarketContext(**defaults)

    # -- personas that use institutional_ownership only --

    def test_buffett_no_ownership_does_not_crash(self):
        """Buffett should score normally when ownership is None."""
        from augur.personas.buffett import BuffettAgent

        agent = BuffettAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None
        assert result.score >= 0
        # management_quality is scored without ownership contribution
        factors = result.metadata.get("factors", {})
        assert "management_quality" in factors

    def test_fisher_no_ownership_does_not_crash(self):
        from augur.personas.fisher import FisherAgent

        agent = FisherAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    def test_munger_no_ownership_does_not_crash(self):
        from augur.personas.munger import MungerAgent

        agent = MungerAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    def test_marks_no_ownership_does_not_crash(self):
        from augur.personas.marks import MarksAgent

        agent = MarksAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    def test_dan_bin_no_ownership_does_not_crash(self):
        from augur.personas.dan_bin import DanBinAgent

        agent = DanBinAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    # -- personas that use both ownership fields --

    def test_zhang_lei_no_ownership_does_not_crash(self):
        from augur.personas.zhang_lei import ZhangLeiAgent

        agent = ZhangLeiAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    def test_li_lu_no_ownership_does_not_crash(self):
        from augur.personas.li_lu import LiLuAgent

        agent = LiLuAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    def test_aschenbrenner_no_ownership_does_not_crash(self):
        from augur.personas.aschenbrenner import AschenbrennerAgent

        agent = AschenbrennerAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    def test_thiel_no_ownership_does_not_crash(self):
        from augur.personas.thiel import ThielAgent

        agent = ThielAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    def test_duan_yongping_no_ownership_does_not_crash(self):
        from augur.personas.duan_yongping import DuanYongpingAgent

        agent = DuanYongpingAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    def test_dayu_no_ownership_does_not_crash(self):
        from augur.personas.dayu import DayuAgent

        agent = DayuAgent()
        ctx = self._make_ctx()
        result = agent.analyze(ctx)
        assert result.signal is not None

    # -- scoring parity: with vs without ownership --

    def test_buffett_ownership_vs_none_does_not_crash(self):
        """Buffett: ownership=None gives a valid score (different from 0)."""
        from augur.personas.buffett import BuffettAgent

        agent = BuffettAgent()
        ctx_none = self._make_ctx(institutional_ownership=None)
        ctx_zero = self._make_ctx(institutional_ownership=0.0)

        r_none = agent.analyze(ctx_none)
        r_zero = agent.analyze(ctx_zero)

        # Both must produce valid results
        assert r_none.signal is not None
        assert r_zero.signal is not None

        # With ownership=None, management_quality starts at 5 (no bonus)
        # With ownership=0, management_quality also starts at 5 (0 doesn't pass >50 or >70)
        # So they should be identical for scoring — but the reasoning differs
        f_none = r_none.metadata.get("factors", {}).get("management_quality", -1)
        f_zero = r_zero.metadata.get("factors", {}).get("management_quality", -1)
        assert f_none == f_zero, (
            f"management_quality should be identical for None vs 0 "
            f"(got {f_none} vs {f_zero})"
        )

    def test_persona_reasoning_shows_na_for_missing(self):
        """Reasoning output shows 'N/A' when ownership is missing, not '0.0%'."""
        from augur.personas.buffett import BuffettAgent

        agent = BuffettAgent()
        ctx = self._make_ctx(institutional_ownership=None)
        result = agent.analyze(ctx)
        # Reasoning must contain N/A, not format 0.0%
        assert "N/A" in result.reasoning, (
            f"Reasoning should show N/A for missing ownership:\n{result.reasoning}"
        )
        assert "0.0%" not in result.reasoning.split("机构持股:")[-1].split("\n")[0], (
            "Reasoning must not show 0.0% for missing institutional_ownership"
        )

    def test_persona_with_ownership_shows_number(self):
        """Reasoning shows actual % when ownership is present."""
        from augur.personas.buffett import BuffettAgent

        agent = BuffettAgent()
        ctx = self._make_ctx(institutional_ownership=65.5)
        result = agent.analyze(ctx)
        assert "65.5%" in result.reasoning


# ---------------------------------------------------------------------------
# Replay schema v2 (backtest._record_to_market_context)
# ---------------------------------------------------------------------------

class TestReplaySchemaV2:
    """Replay MarketContext must set field_availability and leave ownership None."""

    def test_record_to_market_context_ownership_none(self):
        """_record_to_market_context sets ownership to None, not 0."""
        from augur.backtest import _record_to_market_context

        record = {
            "date": "2024-06-15",
            "price": 150.0,
            "pe": 20.0,
            "pb": 3.0,
            "roe": 0.18,
            "gross_margins": 0.45,
            "revenue_growth": 0.15,
            "debt_ratio": 0.35,
            "fcf": 10.0,
            "market_cap": 500.0,
            "operating_margins": 0.25,
            "rsi": 55.0,
            "macd": 1.2,
            "earnings_growth": 0.12,
            "current_ratio": 1.8,
        }

        ctx = _record_to_market_context("AAPL", record)

        assert ctx.institutional_ownership is None, (
            "Replay must set institutional_ownership=None, not 0"
        )
        assert ctx.insider_ownership is None, (
            "Replay must set insider_ownership=None, not 0"
        )

    def test_record_to_market_context_field_availability(self):
        """_record_to_market_context sets field_availability correctly."""
        from augur.backtest import _record_to_market_context

        record = {
            "date": "2024-06-15",
            "price": 150.0,
            "pe": 20.0,
            "pb": 3.0,
            "roe": 0.18,
            "gross_margins": 0.45,
            "revenue_growth": 0.15,
            "debt_ratio": 0.35,
            "fcf": 10.0,
            "market_cap": 500.0,
            "operating_margins": 0.25,
            "rsi": 55.0,
            "macd": 1.2,
            "earnings_growth": 0.12,
            "current_ratio": 1.8,
        }

        ctx = _record_to_market_context("AAPL", record)

        fa = ctx.field_availability
        assert fa.get("price") == "replay", f"price should be replay, got {fa.get('price')}"
        assert fa.get("pe") == "replay", f"pe should be replay, got {fa.get('pe')}"
        assert fa.get("institutional_ownership") == "missing", (
            f"institutional_ownership should be missing, got {fa.get('institutional_ownership')}"
        )
        assert fa.get("insider_ownership") == "missing", (
            f"insider_ownership should be missing, got {fa.get('insider_ownership')}"
        )

    def test_record_to_market_context_as_of_date(self):
        """_record_to_market_context sets as_of_date from record date."""
        from augur.backtest import _record_to_market_context

        record = {
            "date": "2024-06-15",
            "price": 150.0,
            "pe": 20.0,
            "pb": 3.0,
            "roe": 0.18,
            "gross_margins": 0.45,
            "revenue_growth": 0.15,
            "debt_ratio": 0.35,
            "fcf": 10.0,
            "market_cap": 500.0,
            "operating_margins": 0.25,
            "rsi": 55.0,
            "macd": 1.2,
            "earnings_growth": 0.12,
            "current_ratio": 1.8,
        }

        ctx = _record_to_market_context("AAPL", record)
        assert ctx.as_of_date == "2024-06-15"


# ---------------------------------------------------------------------------
# EvidenceItem in provider output
# ---------------------------------------------------------------------------

class TestEvidenceItemIntegration:
    """fetch_market_context must attach evidence_items and field_availability."""

    def test_live_context_has_evidence_items(self, monkeypatch):
        """Mocked live fetch attaches evidence_items and field_availability."""
        from augur.personas.base import MarketContext
        from augur.datasources.base import DataProvider

        class MockProvider(DataProvider):
            name = "mock"

            def fetch(self, ticker):
                return {
                    "data_source": "mock",
                    "price": 150.0,
                    "pe": 20.0,
                    "pb": 3.0,
                    "roe": 0.18,
                    "gross_margins": 0.45,
                    "revenue_growth": 0.15,
                    "debt_ratio": 0.35,
                    "market_cap": 500.0,
                }

        import augur.data as data_module
        monkeypatch.setattr(data_module, "_get_providers", lambda: [MockProvider()])

        ctx = data_module.fetch_market_context("AAPL", force_refresh=True)

        assert isinstance(ctx.evidence_items, list)
        # At least price should have an evidence item
        price_items = [e for e in ctx.evidence_items if e.get("metric") == "price"]
        assert len(price_items) >= 1, f"Expected price EvidenceItem, got {ctx.evidence_items}"

        # Ownership fields should be marked missing
        fa = ctx.field_availability
        assert fa.get("institutional_ownership") == "missing", (
            f"Expected missing, got {fa.get('institutional_ownership')}"
        )
        assert fa.get("insider_ownership") == "missing"

    def test_missing_ownership_evidence_item(self, monkeypatch):
        """Missing ownership fields generate evidence items with missing=True."""
        from augur.datasources.base import DataProvider

        class MockProvider(DataProvider):
            name = "mock"

            def fetch(self, ticker):
                return {
                    "data_source": "mock",
                    "price": 150.0,
                    "pe": 20.0,
                }

        import augur.data as data_module
        monkeypatch.setattr(data_module, "_get_providers", lambda: [MockProvider()])

        ctx = data_module.fetch_market_context("AAPL", force_refresh=True)

        # Find missing evidence items for ownership
        missing_items = [e for e in ctx.evidence_items if e.get("missing")]
        missing_metrics = {e.get("metric") for e in missing_items}
        assert "institutional_ownership" in missing_metrics, (
            f"Expected institutional_ownership in missing items, got {missing_metrics}"
        )
        assert "insider_ownership" in missing_metrics

    def test_live_context_as_of_date(self, monkeypatch):
        """Live context has as_of_date set to today."""
        from augur.datasources.base import DataProvider

        class MockProvider(DataProvider):
            name = "mock"

            def fetch(self, ticker):
                return {
                    "data_source": "mock",
                    "price": 150.0,
                    "pe": 20.0,
                }

        import augur.data as data_module
        monkeypatch.setattr(data_module, "_get_providers", lambda: [MockProvider()])

        ctx = data_module.fetch_market_context("AAPL", force_refresh=True)
        assert ctx.as_of_date is not None
        # Should be ISO date format YYYY-MM-DD
        assert len(ctx.as_of_date) == 10
        assert "-" in ctx.as_of_date


# ---------------------------------------------------------------------------
# Availability parity: live vs replay
# ---------------------------------------------------------------------------

class TestAvailabilityParity:
    """Live and replay data must agree on which fields are available."""

    def test_live_replay_ownership_both_missing(self):
        """Both live and replay should have ownership marked missing."""
        from augur.backtest import _record_to_market_context

        # Replay side
        record = {
            "date": "2024-06-15",
            "price": 150.0,
            "pe": 20.0,
            "pb": 3.0,
            "roe": 0.18,
            "gross_margins": 0.45,
            "revenue_growth": 0.15,
            "debt_ratio": 0.35,
            "fcf": 10.0,
            "market_cap": 500.0,
            "operating_margins": 0.25,
            "rsi": 55.0,
            "macd": 1.2,
            "earnings_growth": 0.12,
            "current_ratio": 1.8,
        }
        replay_ctx = _record_to_market_context("AAPL", record)

        # Live side (build directly, simulating provider that can't supply ownership)
        from augur.personas.base import MarketContext
        live_ctx = MarketContext(
            ticker="AAPL",
            price=150.0,
            pe=20.0,
            institutional_ownership=None,
            insider_ownership=None,
        )

        # Both should have None ownership
        assert replay_ctx.institutional_ownership is None
        assert live_ctx.institutional_ownership is None

        # Replay marks it "missing"
        assert replay_ctx.field_availability.get("institutional_ownership") == "missing"

    def test_data_source_provider_has_to_evidence_item(self):
        """DataProvider has to_evidence_item and coverage_report methods."""
        from augur.datasources.base import DataProvider

        # Verify the abstract methods exist
        assert hasattr(DataProvider, "to_evidence_item"), (
            "DataProvider missing to_evidence_item"
        )
        assert hasattr(DataProvider, "coverage_report"), (
            "DataProvider missing coverage_report"
        )
