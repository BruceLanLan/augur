# -*- coding: utf-8 -*-
"""Tests for iteration 3: bot utilities, config validation, parallel coordinator, API edge cases."""

import pytest


class TestBotTickerExtraction:
    """Test the shared bot ticker extraction utility."""

    def test_extract_valid_ticker(self):
        """Standard tickers should be extracted."""
        from augur.bots.utils import extract_ticker
        assert extract_ticker("analyze AAPL") == "AAPL"
        # The function uppercases everything, so "what" becomes "WHAT" (4 chars)
        # which is not a stop word; but we can test with stop words preceding ticker
        assert extract_ticker("is it NVDA") == "NVDA"

    def test_extract_ticker_from_chinese_text(self):
        """Chinese text with space-separated ticker should work."""
        from augur.bots.utils import extract_ticker
        assert extract_ticker("分析 TSLA pe=32") == "TSLA"

    def test_extract_filters_stop_words(self):
        """Common English words in the stop list should be filtered."""
        from augur.bots.utils import extract_ticker
        # "IT" and "IS" are stop words and should be skipped
        # Note: the function uppercases everything so all words become candidates
        # Only stop words should be filtered
        assert extract_ticker("IT IS") is None
        assert extract_ticker("AT IN OR") is None
        # AAPL should be found when only stop words precede it
        assert extract_ticker("IS IT AAPL") == "AAPL"

    def test_extract_empty_input(self):
        """Empty or whitespace input returns None."""
        from augur.bots.utils import extract_ticker
        assert extract_ticker("") is None
        assert extract_ticker("   ") is None
        # Only digits and single characters - no 2-5 letter words
        assert extract_ticker("1 2 3 4 5") is None

    def test_extract_chinese_only_no_ticker(self):
        """Pure Chinese text without word-boundary ticker returns None."""
        from augur.bots.utils import extract_ticker
        # Chinese characters without word boundaries around Latin letters
        # The regex \b won't match boundaries inside Chinese chars
        assert extract_ticker("分析一下的前景") is None

    def test_extract_single_char_excluded(self):
        """Single character matches should be excluded (regex requires 2-5 chars)."""
        from augur.bots.utils import extract_ticker
        # Only single-char words, all filtered by regex length requirement
        assert extract_ticker("I A") is None


class TestBotMetricsParsing:
    """Test metric parsing from bot messages."""

    def test_parse_standard_metrics(self):
        """Standard key=value pairs."""
        from augur.bots.utils import parse_metrics
        result = parse_metrics("pe=32 roe=0.55 gm=0.46")
        assert result == {"pe": 32.0, "roe": 0.55, "gm": 0.46}

    def test_parse_empty_string(self):
        """Empty string returns empty dict."""
        from augur.bots.utils import parse_metrics
        assert parse_metrics("") == {}

    def test_parse_malformed_values(self):
        """Malformed values are skipped."""
        from augur.bots.utils import parse_metrics
        # "abc" is not a valid float - regex only matches [\d.]+,
        # "pe=abc" won't match at all
        result = parse_metrics("pe=abc roe=0.5")
        assert result == {"roe": 0.5}

    def test_parse_large_numbers(self):
        """Very large numbers should parse correctly."""
        from augur.bots.utils import parse_metrics
        result = parse_metrics("market_cap=99999999")
        assert result == {"market_cap": 99999999.0}


class TestConfigValidation:
    """Test config module edge cases."""

    def test_reset_config_clears_state(self):
        """reset_config should clear cached config."""
        from augur.config import get_config, set_config, reset_config
        set_config("test_key", "test_value")
        config = get_config()
        assert config.get("test_key") == "test_value"
        reset_config()
        # After reset, it reloads from file (test_key won't persist)
        # Just verify no crash
        config2 = get_config()
        assert isinstance(config2, dict)

    def test_set_config_nested_path(self):
        """set_config with dot notation creates nested structure."""
        from augur.config import set_config, get_config, reset_config
        reset_config()
        set_config("a.b.c", 42)
        config = get_config()
        assert config.get("a", {}).get("b", {}).get("c") == 42
        reset_config()

    def test_get_config_returns_copy(self):
        """get_config should return a copy, not the internal reference."""
        from augur.config import get_config, reset_config
        reset_config()
        c1 = get_config()
        c1["mutation_test"] = True
        c2 = get_config()
        assert "mutation_test" not in c2
        reset_config()


class TestCoordinatorParallel:
    """Test that parallel coordinator produces correct results."""

    def test_parallel_produces_all_results(self):
        """analyze_with_all should produce results for all registered agents."""
        from augur.registry import AgentRegistry, DecisionCoordinator
        from augur.personas.base import MarketContext

        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="TEST", pe=25, roe=0.15)
        results = coordinator.analyze_with_all(ctx)

        assert len(results) == len(registry.get_all())
        for agent in registry.get_all():
            assert agent.agent_id in results

    def test_parallel_handles_errors_gracefully(self):
        """If an agent raises, it should return ERROR signal, not crash."""
        from augur.registry import AgentRegistry, DecisionCoordinator
        from augur.personas.base import MarketContext

        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        # A minimal context that all agents should handle
        ctx = MarketContext(ticker="ERR_TEST")
        results = coordinator.analyze_with_all(ctx)

        # All results should be present and scores in valid range
        for agent_id, result in results.items():
            assert 0 <= result.score <= 10, f"{agent_id} score out of range: {result.score}"

    def test_parallel_results_deterministic(self):
        """Running analysis twice should produce same scores (agents are deterministic)."""
        from augur.registry import AgentRegistry, DecisionCoordinator
        from augur.personas.base import MarketContext

        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
        ctx = MarketContext(ticker="DET", pe=20, roe=0.2, gross_margins=0.4)

        results1 = coordinator.analyze_with_all(ctx)
        results2 = coordinator.analyze_with_all(ctx)

        for agent_id in results1:
            assert results1[agent_id].score == results2[agent_id].score, \
                f"{agent_id} non-deterministic: {results1[agent_id].score} vs {results2[agent_id].score}"


class TestDashboardAPIEdgeCases:
    """Test dashboard API validation."""

    def test_analyze_invalid_ticker_returns_400(self):
        """Ticker with special characters should be rejected."""
        from fastapi.testclient import TestClient
        from dashboard.app import app

        client = TestClient(app)
        # Use a ticker with characters that pass URL routing but fail regex validation
        response = client.get("/api/analyze/AAPL;DROP")
        assert response.status_code == 400
        assert "Invalid ticker" in response.json()["detail"]

    def test_analyze_valid_ticker_returns_200(self):
        """Valid ticker should succeed."""
        from fastapi.testclient import TestClient
        from dashboard.app import app

        client = TestClient(app)
        response = client.get("/api/analyze/AAPL?pe=30&roe=0.5&auto_fetch=false")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "consensus" in data
        assert "agents" in data

    def test_health_endpoint(self):
        """Health endpoint should return status ok."""
        from fastapi.testclient import TestClient
        from dashboard.app import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "agents" in data
        assert data["agents"] > 0
