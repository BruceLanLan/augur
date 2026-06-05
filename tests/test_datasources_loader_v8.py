# -*- coding: utf-8 -*-
"""
Tests for the data-source *loader* layer of augur.datasources.

augur/datasources/ is new in v8 and provides a multi-source data provider
abstraction (yfinance, finnhub, alphavantage, stooq). The "loader" here means
the functions that assemble the provider chain at runtime based on env-var
API keys (``default_providers`` / ``available_sources``), plus the small
behavioural contracts each provider must satisfy (e.g. refusing to call out
without a key, symbol normalisation for Stooq).

These tests focus on the *loader* surface that the existing test_datasources.py
does not cover:

  - default_providers() chain assembly under various env-var states
    (no keys, only finnhub, only alphavantage, both, whitespace-only)
  - available_sources() mirrors default_providers() ordering
  - Provider list ordering is stable and matches the documented priority
  - default_providers() returns fresh provider instances (no shared state)
  - Providers that need a key refuse to fetch() when none is configured
  - StooqProvider symbol mapping edge cases (lowercase, mixed case, dotless,
    already-suffixed, whitespace stripping)
  - DataProviderError is a normal Exception subclass usable in except blocks
"""

import os
from unittest.mock import patch

import pytest

from augur.datasources import (
    AlphaVantageProvider,
    DataProvider,
    DataProviderError,
    FinnhubProvider,
    StooqProvider,
    YFinanceProvider,
    available_sources,
    default_providers,
)


# Optional API key env vars that the loader consults
_FINNHUB_KEY = "FINNHUB_API_KEY"
_ALPHAVANTAGE_KEY = "ALPHAVANTAGE_API_KEY"


@pytest.fixture
def clean_api_keys(monkeypatch):
    """Ensure both optional API-key env vars are unset for the duration of a test."""
    monkeypatch.delenv(_FINNHUB_KEY, raising=False)
    monkeypatch.delenv(_ALPHAVANTAGE_KEY, raising=False)
    return monkeypatch


class TestProviderChainAssembly:
    """``default_providers`` / ``available_sources`` are the public loader API.

    They must dynamically compose the chain based on which optional API keys
    are present, with documented ordering:
        yfinance -> finnhub(?, if key) -> alphavantage(?, if key) -> stooq
    """

    def test_no_keys_returns_yfinance_and_stooq_only(self, clean_api_keys):
        providers = default_providers()
        names = [type(p).__name__ for p in providers]
        # yfinance is always first (primary), stooq always last (last-resort).
        assert names[0] == "YFinanceProvider"
        assert names[-1] == "StooqProvider"
        # No optional providers when no keys are set.
        assert "FinnhubProvider" not in names
        assert "AlphaVantageProvider" not in names
        # And the length matches expectation.
        assert names == ["YFinanceProvider", "StooqProvider"]

    def test_finnhub_key_adds_finnhub_between_yfinance_and_stooq(self, clean_api_keys):
        clean_api_keys.setenv(_FINNHUB_KEY, "test-finnhub-key")
        names = [type(p).__name__ for p in default_providers()]
        assert names == ["YFinanceProvider", "FinnhubProvider", "StooqProvider"]
        # Available sources must mirror the same chain.
        assert available_sources() == ["yfinance", "finnhub", "stooq"]

    def test_alphavantage_key_adds_alphavantage(self, clean_api_keys):
        clean_api_keys.setenv(_ALPHAVANTAGE_KEY, "test-av-key")
        names = [type(p).__name__ for p in default_providers()]
        assert names == ["YFinanceProvider", "AlphaVantageProvider", "StooqProvider"]
        assert available_sources() == ["yfinance", "alphavantage", "stooq"]

    def test_both_keys_yields_full_chain_in_documented_order(self, clean_api_keys):
        clean_api_keys.setenv(_FINNHUB_KEY, "f")
        clean_api_keys.setenv(_ALPHAVANTAGE_KEY, "a")
        names = [type(p).__name__ for p in default_providers()]
        # Order matters: yfinance (primary) -> finnhub -> alphavantage -> stooq (last resort)
        assert names == [
            "YFinanceProvider",
            "FinnhubProvider",
            "AlphaVantageProvider",
            "StooqProvider",
        ]
        assert available_sources() == ["yfinance", "finnhub", "alphavantage", "stooq"]

    def test_whitespace_only_keys_do_not_enable_optional_providers(self, clean_api_keys):
        """A key of all whitespace must not be treated as configured.

        The providers' is_configured() helpers call .strip() on the env value;
        whitespace-only must be rejected so we don't ship requests with an
        effectively-empty token.
        """
        clean_api_keys.setenv(_FINNHUB_KEY, "   ")
        clean_api_keys.setenv(_ALPHAVANTAGE_KEY, "\t\n")
        names = [type(p).__name__ for p in default_providers()]
        assert "FinnhubProvider" not in names
        assert "AlphaVantageProvider" not in names
        assert names == ["YFinanceProvider", "StooqProvider"]
        assert available_sources() == ["yfinance", "stooq"]

    def test_default_providers_returns_independent_instances(self, clean_api_keys):
        """Two calls must not share mutable state (provider.__init__ may set
        per-call config, e.g. cached api keys, request timeouts)."""
        a = default_providers()
        b = default_providers()
        # Same types and order
        assert [type(p).__name__ for p in a] == [type(p).__name__ for p in b]
        # But distinct object identities
        for p, q in zip(a, b):
            assert p is not q, "default_providers() must not return cached instances"


class TestOptionalProviderKeyRequirement:
    """Optional providers must refuse to call out without a configured key,
    raising ``DataProviderError`` so the chain falls back to the next source."""

    def test_finnhub_fetch_without_key_raises(self, clean_api_keys):
        # Construct directly with an empty key to bypass env lookup.
        provider = FinnhubProvider(api_key="")
        with pytest.raises(DataProviderError):
            provider.fetch("AAPL")

    def test_alphavantage_fetch_without_key_raises(self, clean_api_keys):
        provider = AlphaVantageProvider(api_key="")
        with pytest.raises(DataProviderError):
            provider.fetch("AAPL")

    def test_finnhub_and_alphavantage_are_real_data_providers(self, clean_api_keys):
        # Sanity: optional providers must still satisfy the DataProvider
        # interface so they can sit in the chain alongside yfinance / stooq.
        assert isinstance(FinnhubProvider(api_key="k"), DataProvider)
        assert isinstance(AlphaVantageProvider(api_key="k"), DataProvider)
        assert FinnhubProvider(api_key="k").name == "finnhub"
        assert AlphaVantageProvider(api_key="k").name == "alphavantage"


class TestStooqSymbolNormalisation:
    """``StooqProvider._to_stooq_symbol`` is a pure function used as the
    loader-time mapping from a public ticker to the Stooq CSV symbol."""

    @pytest.mark.parametrize(
        "ticker,expected",
        [
            ("AAPL", "aapl.us"),                # US, no suffix -> append .us
            ("aapl", "aapl.us"),                # lowercase US -> still append .us
            ("TSLA", "tsla.us"),
            ("0700.HK", "0700.hk"),             # already-suffixed: lowercase
            ("600519.SS", "600519.ss"),         # A-share suffix preserved, lowercased
            ("  MSFT  ", "msft.us"),            # leading/trailing whitespace stripped
            ("BRK.B", "brk.b"),                 # share-class dot preserved
        ],
    )
    def test_to_stooq_symbol_mapping(self, ticker, expected):
        assert StooqProvider._to_stooq_symbol(ticker) == expected


class TestDataProviderErrorContract:
    """``DataProviderError`` is the signal the chain uses to fall back; it
    must be a regular ``Exception`` subclass (not, e.g., BaseException)."""

    def test_is_exception_subclass(self):
        assert issubclass(DataProviderError, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(DataProviderError):
            raise DataProviderError("boom")
        # And it must also be catchable as Exception
        try:
            raise DataProviderError("x")
        except Exception as exc:
            assert isinstance(exc, DataProviderError)
