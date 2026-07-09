# -*- coding: utf-8 -*-
"""Tests for augur.consensus.edgar_guidance (EDGAR Phase 4: LLM management guidance).

All offline / deterministic. Per docs/superpowers/specs/2026-07-03-edgar-fundamentals-design.md
§4's own test list: LLM calls are always mocked (cost/network reasons), never real.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from augur.consensus import edgar_guidance as eg


# ── Synthetic filing text fixtures ──────────────────────────────────────

def _synthetic_10k_text():
    """Mirrors the real structure confirmed against AAPL's 2024 10-K:
    short TOC/cross-reference mentions of "Item 7." early, then the real
    section (thousands of chars) much later, ending at "Item 7A."."""
    toc = "Item 7.\nManagement's Discussion and Analysis\n19\n"
    cross_ref = "discussed further in Item 7 of this Form 10-K under the heading blah\n"
    real_section = (
        "Item 7.    Management's Discussion and Analysis of Financial Condition and Results of Operations\n"
        + ("Revenue grew due to strong iPhone demand. " * 200)
        + "\nEnd of MD&A.\n"
    )
    tail = "Item 7A.    Quantitative and Qualitative Disclosures About Market Risk\nVaR analysis follows.\n"
    return toc + cross_ref + real_section + tail


def _synthetic_10q_text():
    toc = "Item 2.\nManagement's Discussion and Analysis\n19\nItem 3.\nMarket Risk\n25\n"
    real_section = (
        "Item 2.    Management's Discussion and Analysis of Financial Condition and Results of Operations\n"
        + ("Quarterly revenue increased year over year. " * 150)
        + "\nEnd of MD&A.\n"
    )
    tail = "Item 3.    Quantitative and Qualitative Disclosures About Market Risk\nDetails follow.\n"
    part_ii = "Item 2.\nUnregistered Sales of Equity Securities\nNone.\nItem 3.\nDefaults Upon Senior Securities\nNone.\n"
    return toc + real_section + tail + part_ii


# ── _extract_mdna_section ───────────────────────────────────────────────

class TestExtractMdnaSection:
    def test_10k_finds_real_section_not_toc(self):
        text = _synthetic_10k_text()
        section = eg._extract_mdna_section(text, "10-K")
        assert section is not None
        assert section.startswith("Item 7.")
        assert "Revenue grew due to strong iPhone demand." in section
        assert "Item 7A." not in section
        # TOC entry text is much shorter than the real section
        assert len(section) > 1000

    def test_10q_finds_part_i_not_part_ii(self):
        text = _synthetic_10q_text()
        section = eg._extract_mdna_section(text, "10-Q")
        assert section is not None
        assert "Quarterly revenue increased" in section
        assert "Unregistered Sales" not in section

    def test_unknown_form_returns_none(self):
        assert eg._extract_mdna_section(_synthetic_10k_text(), "8-K") is None

    def test_missing_start_marker_returns_none(self):
        assert eg._extract_mdna_section("no items here at all", "10-K") is None

    def test_missing_end_marker_returns_none(self):
        assert eg._extract_mdna_section("Item 7. some text but no closing item", "10-K") is None

    def test_truncates_to_max_chars(self):
        huge = "Item 7.    " + ("x" * 100_000) + "\nItem 7A. end\n"
        section = eg._extract_mdna_section(huge, "10-K")
        assert section is not None
        assert len(section) <= eg._MAX_MDNA_CHARS


# ── _html_to_text ────────────────────────────────────────────────────────

class TestHtmlToText:
    def test_strips_tags_and_collapses_whitespace(self):
        html = "<html><body><p>Item 7.</p>\n\n<p>  Some text  </p></body></html>"
        text = eg._html_to_text(html)
        assert "<p>" not in text
        assert "Item 7." in text
        assert "Some text" in text


# ── fetch_management_guidance: disabled / unavailable paths ─────────────

class TestFetchManagementGuidanceGating:
    def test_disabled_by_default_makes_no_network_calls(self, monkeypatch):
        monkeypatch.delenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", raising=False)
        with patch("augur.consensus.edgar_fundamentals._get_client") as mock_get_client:
            result = eg.fetch_management_guidance("AAPL")
        assert result["available"] is False
        assert "disabled" in result["reason"]
        mock_get_client.assert_not_called()

    def test_enabled_but_llm_unavailable(self, monkeypatch):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "1")
        with patch("augur.llm_client.is_llm_available", return_value=False):
            with patch("augur.consensus.edgar_fundamentals._get_client") as mock_get_client:
                result = eg.fetch_management_guidance("AAPL")
        assert result["available"] is False
        assert "LLM backend unavailable" in result["reason"]
        mock_get_client.assert_not_called()

    def test_enabled_llm_available_but_bs4_missing(self, monkeypatch):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "1")
        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.optional_deps.is_available", return_value=False):
            with patch("augur.consensus.edgar_fundamentals._get_client") as mock_get_client:
                result = eg.fetch_management_guidance("AAPL")
        assert result["available"] is False
        assert "beautifulsoup4" in result["reason"]
        mock_get_client.assert_not_called()

    @pytest.mark.parametrize("truthy", ["1", "true", "TRUE", "yes", "Yes"])
    def test_truthy_env_values_enable(self, monkeypatch, truthy):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", truthy)
        assert eg._is_enabled() is True

    @pytest.mark.parametrize("falsy", ["", "0", "false", "no"])
    def test_falsy_env_values_disable(self, monkeypatch, falsy):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", falsy)
        assert eg._is_enabled() is False

    def test_no_cik_found(self, monkeypatch):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "1")
        mock_client = MagicMock()
        mock_client.get_cik.return_value = None
        with patch("augur.llm_client.is_llm_available", return_value=True):
            with patch("augur.consensus.edgar_fundamentals._get_client", return_value=mock_client):
                result = eg.fetch_management_guidance("NOTAREALTICKER")
        assert result["available"] is False
        assert "no EDGAR CIK" in result["reason"]

    def test_no_10k_or_10q_found(self, monkeypatch):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "1")
        mock_client = MagicMock()
        mock_client.get_cik.return_value = 320193
        mock_client.get_submissions.return_value = {
            "filings": {"recent": {"form": ["8-K"], "accessionNumber": ["x"], "primaryDocument": ["y"], "filingDate": ["2025-01-01"]}}
        }
        with patch("augur.llm_client.is_llm_available", return_value=True):
            with patch("augur.consensus.edgar_fundamentals._get_client", return_value=mock_client):
                result = eg.fetch_management_guidance("AAPL")
        assert result["available"] is False
        assert "no 10-K/10-Q" in result["reason"]


# ── fetch_management_guidance: success + caching ─────────────────────────

def _mock_submissions():
    return {
        "filings": {
            "recent": {
                "form": ["10-K", "10-Q"],
                "accessionNumber": ["0000320193-24-000123", "0000320193-24-000050"],
                "primaryDocument": ["aapl-20240928.htm", "aapl-20240630.htm"],
                "filingDate": ["2024-11-01", "2024-08-01"],
            }
        }
    }


def _mock_llm_response(sentiment="positive", guidance=None, risk="Supply chain risk noted."):
    payload = {
        "outlook_sentiment": sentiment,
        "outlook_summary": "Management is optimistic about upcoming product cycles.",
        "guidance_numbers": guidance or ["Revenue expected to grow low double digits next quarter."],
        "risk_notes": risk,
    }
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    return resp


class TestFetchManagementGuidanceSuccess:
    def _setup_client(self):
        mock_client = MagicMock()
        mock_client.get_cik.return_value = 320193
        mock_client.get_submissions.return_value = _mock_submissions()
        mock_client.get_filing_document.return_value = "<html><body>" + _synthetic_10k_text() + "</body></html>"
        return mock_client

    def test_full_success_path(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "1")
        monkeypatch.setattr(eg, "_CACHE_DIR", tmp_path)
        mock_client = self._setup_client()
        mock_llm_client = MagicMock()
        mock_llm_client.chat.completions.create.return_value = _mock_llm_response()

        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.llm_client._get_client", return_value=mock_llm_client), \
             patch("augur.consensus.edgar_fundamentals._get_client", return_value=mock_client):
            result = eg.fetch_management_guidance("AAPL")

        assert result["available"] is True
        assert result["form"] == "10-K"
        assert result["accession_number"] == "0000320193-24-000123"
        assert result["outlook_sentiment"] == "positive"
        assert result["cache_hit"] is False
        assert len(result["guidance_numbers"]) == 1
        mock_llm_client.chat.completions.create.assert_called_once()

    def test_cache_hit_skips_llm_and_document_fetch(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "1")
        monkeypatch.setattr(eg, "_CACHE_DIR", tmp_path)
        mock_client = self._setup_client()
        mock_llm_client = MagicMock()
        mock_llm_client.chat.completions.create.return_value = _mock_llm_response()

        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.llm_client._get_client", return_value=mock_llm_client), \
             patch("augur.consensus.edgar_fundamentals._get_client", return_value=mock_client):
            first = eg.fetch_management_guidance("AAPL")
            assert first["cache_hit"] is False
            mock_client.get_filing_document.reset_mock()

            second = eg.fetch_management_guidance("AAPL")

        assert second["cache_hit"] is True
        assert second["outlook_sentiment"] == "positive"
        mock_client.get_filing_document.assert_not_called()
        # Only one real extraction call across both invocations.
        mock_llm_client.chat.completions.create.assert_called_once()

    def test_malformed_document_fetch_returns_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "1")
        monkeypatch.setattr(eg, "_CACHE_DIR", tmp_path)
        mock_client = self._setup_client()
        mock_client.get_filing_document.return_value = None

        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.consensus.edgar_fundamentals._get_client", return_value=mock_client):
            result = eg.fetch_management_guidance("AAPL")
        assert result["available"] is False
        assert "failed to fetch filing document" in result["reason"]

    def test_no_mdna_section_found_returns_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "1")
        monkeypatch.setattr(eg, "_CACHE_DIR", tmp_path)
        mock_client = self._setup_client()
        mock_client.get_filing_document.return_value = "<html><body>nothing relevant here</body></html>"

        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.consensus.edgar_fundamentals._get_client", return_value=mock_client):
            result = eg.fetch_management_guidance("AAPL")
        assert result["available"] is False
        assert "could not locate MD&A" in result["reason"]


# ── _call_llm_extraction ──────────────────────────────────────────────────

class TestCallLlmExtraction:
    def test_parses_valid_json_response(self):
        mock_llm_client = MagicMock()
        mock_llm_client.chat.completions.create.return_value = _mock_llm_response(sentiment="negative")
        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.llm_client._get_client", return_value=mock_llm_client):
            result = eg._call_llm_extraction("some mdna text", "AAPL")
        assert result["outlook_sentiment"] == "negative"
        assert isinstance(result["guidance_numbers"], list)

    def test_invalid_sentiment_falls_back_to_neutral(self):
        mock_llm_client = MagicMock()
        mock_llm_client.chat.completions.create.return_value = _mock_llm_response(sentiment="very bullish!!")
        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.llm_client._get_client", return_value=mock_llm_client):
            result = eg._call_llm_extraction("some mdna text", "AAPL")
        assert result["outlook_sentiment"] == "neutral"

    def test_non_list_guidance_numbers_falls_back_to_empty(self):
        payload = {
            "outlook_sentiment": "positive", "outlook_summary": "x",
            "guidance_numbers": "not a list", "risk_notes": "",
        }
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
        mock_llm_client = MagicMock()
        mock_llm_client.chat.completions.create.return_value = resp
        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.llm_client._get_client", return_value=mock_llm_client):
            result = eg._call_llm_extraction("some mdna text", "AAPL")
        assert result["guidance_numbers"] == []

    def test_llm_unavailable_returns_none(self):
        with patch("augur.llm_client.is_llm_available", return_value=False):
            assert eg._call_llm_extraction("text", "AAPL") is None

    def test_malformed_json_response_returns_none(self):
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content="not json at all"))]
        mock_llm_client = MagicMock()
        mock_llm_client.chat.completions.create.return_value = resp
        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.llm_client._get_client", return_value=mock_llm_client):
            result = eg._call_llm_extraction("text", "AAPL")
        assert result is None

    def test_exception_during_call_returns_none(self):
        mock_llm_client = MagicMock()
        mock_llm_client.chat.completions.create.side_effect = RuntimeError("network down")
        with patch("augur.llm_client.is_llm_available", return_value=True), \
             patch("augur.llm_client._get_client", return_value=mock_llm_client):
            result = eg._call_llm_extraction("text", "AAPL")
        assert result is None


# ── Cache path helpers ─────────────────────────────────────────────────────

class TestCacheHelpers:
    def test_cache_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eg, "_CACHE_DIR", tmp_path)
        payload = {"available": True, "outlook_sentiment": "neutral"}
        eg._save_cached_guidance("0000320193-24-000123", payload)
        loaded = eg._load_cached_guidance("0000320193-24-000123")
        assert loaded == payload

    def test_cache_miss_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eg, "_CACHE_DIR", tmp_path)
        assert eg._load_cached_guidance("nonexistent-accession") is None

    def test_cache_path_strips_dashes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eg, "_CACHE_DIR", tmp_path)
        path = eg._guidance_cache_path("0000320193-24-000123")
        assert path.name == "guidance_000032019324000123.json"
