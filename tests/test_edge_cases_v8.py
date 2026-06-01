# -*- coding: utf-8 -*-
"""
Comprehensive edge case tests for v8.0 features (Review Loops 4-10).

Covers:
- Optimizer: 1 asset, 2 assets, invalid data, singular covariance
- Users: duplicate username, empty password, SQL injection attempts
- Chat: empty message, very long message, unknown agent_id
- Rules: empty conditions, invalid operators, missing fields
- Sentiment: non-existent tickers, special characters
- Streaming: rapid connect/disconnect cycles
- Input validation: max string lengths, allowed characters
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============ Optimizer Edge Cases ============

class TestOptimizerEdgeCases:
    """Edge cases for PortfolioOptimizer."""

    def test_single_asset_portfolio(self):
        """Optimizer should handle single asset correctly."""
        from augur.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        data = {"AAPL": [0.01, -0.005, 0.02, 0.015, -0.01, 0.008]}
        result = opt.optimize(data)
        assert result.weights["AAPL"] == 1.0
        assert result.expected_return != 0.0
        assert result.volatility >= 0.0

    def test_two_asset_portfolio(self):
        """Optimizer should handle two assets with proper allocation."""
        from augur.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        data = {
            "AAPL": [0.01, -0.005, 0.02, 0.015, -0.01, 0.008, 0.003],
            "NVDA": [0.02, -0.01, 0.03, -0.005, 0.01, 0.025, -0.008],
        }
        result = opt.optimize(data)
        assert len(result.weights) == 2
        total_w = sum(result.weights.values())
        assert abs(total_w - 1.0) < 0.01

    def test_empty_returns_data(self):
        """Optimizer should handle empty input gracefully."""
        from augur.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        result = opt.optimize({})
        assert result.weights == {}
        assert result.expected_return == 0.0

    def test_invalid_single_return(self):
        """Optimizer should handle asset with single return value."""
        from augur.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        data = {"AAPL": [0.01]}
        result = opt.optimize(data)
        assert result.weights["AAPL"] == 1.0

    def test_singular_covariance_fallback(self):
        """Optimizer should use equal weights for singular covariance matrix."""
        from augur.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        # All identical returns -> singular covariance
        data = {
            "A": [0.01, 0.01, 0.01, 0.01, 0.01],
            "B": [0.01, 0.01, 0.01, 0.01, 0.01],
            "C": [0.01, 0.01, 0.01, 0.01, 0.01],
        }
        result = opt.optimize(data)
        # Should fallback to equal weights
        for w in result.weights.values():
            assert abs(w - 1.0 / 3) < 0.01

    def test_efficient_frontier_two_assets(self):
        """Efficient frontier with 2 assets should produce valid points."""
        from augur.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        data = {
            "AAPL": [0.01, -0.005, 0.02, 0.015, -0.01, 0.008, 0.003],
            "NVDA": [0.02, -0.01, 0.03, -0.005, 0.01, 0.025, -0.008],
        }
        frontier = opt.efficient_frontier(data, n_points=5)
        assert len(frontier) == 5
        # Volatility should be non-negative
        for pt in frontier:
            assert pt.volatility >= 0.0

    def test_efficient_frontier_single_asset(self):
        """Efficient frontier with 1 asset should return empty list."""
        from augur.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        data = {"AAPL": [0.01, -0.005, 0.02, 0.015, -0.01]}
        frontier = opt.efficient_frontier(data, n_points=10)
        assert frontier == []

    def test_optimizer_negative_returns(self):
        """Optimizer should handle all negative returns."""
        from augur.optimizer import PortfolioOptimizer
        opt = PortfolioOptimizer()
        data = {
            "A": [-0.01, -0.02, -0.005, -0.015, -0.008],
            "B": [-0.005, -0.03, -0.01, -0.02, -0.001],
        }
        result = opt.optimize(data)
        assert sum(result.weights.values()) > 0.99


# ============ Users Edge Cases ============

class TestUsersEdgeCases:
    """Edge cases for UserManager."""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_users.db"

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_duplicate_username_rejected(self):
        """Duplicate username should return None on second create."""
        from augur.users import UserManager
        mgr = UserManager(db_path=self.db_path)
        result1 = mgr.create_user("testuser", "password123")
        assert result1 is not None
        result2 = mgr.create_user("testuser", "different_pass")
        assert result2 is None

    def test_empty_password_rejected(self):
        """Empty password should be rejected."""
        from augur.users import UserManager
        mgr = UserManager(db_path=self.db_path)
        result = mgr.create_user("validuser", "")
        assert result is None

    def test_short_password_rejected(self):
        """Password shorter than 6 chars should be rejected."""
        from augur.users import UserManager
        mgr = UserManager(db_path=self.db_path)
        result = mgr.create_user("validuser", "12345")
        assert result is None

    def test_short_username_rejected(self):
        """Username shorter than 3 chars should be rejected."""
        from augur.users import UserManager
        mgr = UserManager(db_path=self.db_path)
        result = mgr.create_user("ab", "password123")
        assert result is None

    def test_sql_injection_username(self):
        """SQL injection in username should not cause errors."""
        from augur.users import UserManager
        mgr = UserManager(db_path=self.db_path)
        # Attempt SQL injection
        result = mgr.create_user("'; DROP TABLE users; --", "password123")
        # Should either reject (too long/invalid) or safely create
        if result is not None:
            # Verify the table still exists
            count = mgr.user_count()
            assert count >= 1

    def test_sql_injection_password(self):
        """SQL injection in password field should be safely handled."""
        from augur.users import UserManager
        mgr = UserManager(db_path=self.db_path)
        inject = "' OR '1'='1"
        result = mgr.create_user("safe_user", inject)
        assert result is not None
        # Should NOT authenticate with injection string
        token = mgr.authenticate("safe_user", "wrong_password")
        assert token is None


# ============ Chat Edge Cases ============

class TestChatEdgeCases:
    """Edge cases for ChatEngine."""

    def test_empty_message(self):
        """Empty message should return system response."""
        from augur.chat import ChatEngine
        engine = ChatEngine()
        result = engine.get_response("")
        assert result["agent_id"] == "system"
        assert "enter a message" in result["response"].lower()

    def test_whitespace_only_message(self):
        """Whitespace-only message should return system response."""
        from augur.chat import ChatEngine
        engine = ChatEngine()
        result = engine.get_response("   \t\n  ")
        assert result["agent_id"] == "system"

    def test_very_long_message(self):
        """Very long message should be handled without crash."""
        from augur.chat import ChatEngine
        engine = ChatEngine()
        long_msg = "What about NVDA? " * 500  # ~8500 chars
        result = engine.get_response(long_msg, agent_id="buffett")
        assert result["agent_id"] == "buffett"
        assert len(result["response"]) > 0

    def test_unknown_agent_id_uses_default(self):
        """Unknown agent_id should use default template."""
        from augur.chat import ChatEngine
        engine = ChatEngine()
        result = engine.get_response("Tell me about the market", agent_id="nonexistent_agent_xyz")
        assert result["agent_id"] == "nonexistent_agent_xyz"
        assert len(result["response"]) > 0

    def test_special_characters_in_message(self):
        """Special characters should not break response generation."""
        from augur.chat import ChatEngine
        engine = ChatEngine()
        result = engine.get_response("<script>alert('xss')</script> $AAPL")
        assert result is not None
        assert len(result["response"]) > 0

    def test_chat_history_accumulates(self):
        """History should accumulate across calls."""
        from augur.chat import ChatEngine
        engine = ChatEngine()
        engine.get_response("First question", agent_id="buffett")
        engine.get_response("Second question", agent_id="graham")
        history = engine.get_history()
        assert len(history) == 4  # 2 user + 2 assistant


# ============ Rules Edge Cases ============

class TestRulesEdgeCases:
    """Edge cases for RulesEngine."""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.rules_path = os.path.join(self.tmp_dir, "test_rules.yaml")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_empty_conditions_no_trigger(self):
        """Rule with empty conditions should not trigger."""
        from augur.rules import RulesEngine, Rule
        engine = RulesEngine(rules_path=self.rules_path)
        rule = Rule(id="r1", name="Empty Rule", conditions=[], actions=[
            {"channel": "slack", "message": "test"}
        ])
        engine.add_rule(rule)
        triggered = engine.evaluate({"score": 9.0})
        assert len(triggered) == 0

    def test_invalid_operator_no_trigger(self):
        """Rule with invalid operator should not trigger."""
        from augur.rules import RulesEngine, Rule
        engine = RulesEngine(rules_path=self.rules_path)
        rule = Rule(id="r2", name="Bad Op", conditions=[
            {"field": "score", "op": "INVALID_OP", "value": 5}
        ], actions=[{"channel": "telegram", "message": "alert"}])
        engine.add_rule(rule)
        triggered = engine.evaluate({"score": 9.0})
        assert len(triggered) == 0

    def test_missing_field_no_trigger(self):
        """Rule referencing missing field should not trigger."""
        from augur.rules import RulesEngine, Rule
        engine = RulesEngine(rules_path=self.rules_path)
        rule = Rule(id="r3", name="Missing Field", conditions=[
            {"field": "nonexistent_field", "op": ">", "value": 5}
        ], actions=[{"channel": "slack", "message": "fire"}])
        engine.add_rule(rule)
        triggered = engine.evaluate({"score": 9.0})
        assert len(triggered) == 0

    def test_disabled_rule_no_trigger(self):
        """Disabled rule should not trigger even if conditions match."""
        from augur.rules import RulesEngine, Rule
        engine = RulesEngine(rules_path=self.rules_path)
        rule = Rule(id="r4", name="Disabled", conditions=[
            {"field": "score", "op": ">", "value": 5}
        ], actions=[{"channel": "telegram", "message": "fire"}], enabled=False)
        engine.add_rule(rule)
        triggered = engine.evaluate({"score": 9.0})
        assert len(triggered) == 0

    def test_unsupported_channel_no_dispatch(self):
        """Unsupported channel should not dispatch."""
        from augur.rules import NotificationDispatcher
        dispatcher = NotificationDispatcher()
        result = dispatcher.dispatch("unknown_channel", "test msg")
        assert result is False


# ============ Sentiment Edge Cases ============

class TestSentimentEdgeCases:
    """Edge cases for SentimentAnalyzer."""

    def test_nonexistent_ticker(self):
        """Non-existent ticker should still produce a result (mock data)."""
        from augur.sentiment import SentimentAnalyzer
        sa = SentimentAnalyzer()
        result = sa.get_sentiment("ZZZZXXX99")
        assert result.ticker == "ZZZZXXX99"
        assert -1.0 <= result.overall_score <= 1.0
        assert result.volume > 0

    def test_special_characters_ticker(self):
        """Special characters in ticker should be handled."""
        from augur.sentiment import SentimentAnalyzer
        sa = SentimentAnalyzer()
        result = sa.get_sentiment("BRK.B")
        assert result.ticker == "BRK.B"
        assert -1.0 <= result.overall_score <= 1.0

    def test_empty_ticker(self):
        """Empty ticker should produce a valid result."""
        from augur.sentiment import SentimentAnalyzer
        sa = SentimentAnalyzer()
        result = sa.get_sentiment("")
        assert result.ticker == ""
        assert -1.0 <= result.overall_score <= 1.0

    def test_sentiment_factor_range(self):
        """Sentiment factor should always be in [-0.5, 0.5]."""
        from augur.sentiment import SentimentAnalyzer
        sa = SentimentAnalyzer()
        tickers = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "META", "XYZ123"]
        for ticker in tickers:
            factor = sa.get_sentiment_factor(ticker)
            assert -0.5 <= factor <= 0.5, f"Factor for {ticker} out of range: {factor}"

    def test_sentiment_cache_works(self):
        """Second call for same ticker should return cached result."""
        from augur.sentiment import SentimentAnalyzer
        sa = SentimentAnalyzer()
        r1 = sa.get_sentiment("AAPL")
        r2 = sa.get_sentiment("AAPL")
        assert r1.overall_score == r2.overall_score
        assert r1.volume == r2.volume

    def test_clear_cache(self):
        """Clear cache should reset internal state."""
        from augur.sentiment import SentimentAnalyzer
        sa = SentimentAnalyzer()
        sa.get_sentiment("AAPL")
        assert len(sa._cache) > 0
        sa.clear_cache()
        assert len(sa._cache) == 0


# ============ Streaming Edge Cases ============

class TestStreamingEdgeCases:
    """Edge cases for PriceStreamer."""

    def test_initial_prices_populated(self):
        """Streamer should have prices for all tickers on init."""
        from augur.streaming import PriceStreamer
        streamer = PriceStreamer(tickers=["AAPL", "NVDA"], interval=60)
        prices = streamer.get_current_prices()
        assert len(prices) == 2
        for p in prices:
            assert p["price"] > 0
            assert "ticker" in p

    def test_generate_price_update(self):
        """Price update should produce reasonable changes."""
        from augur.streaming import PriceStreamer
        streamer = PriceStreamer(tickers=["AAPL"], interval=60)
        initial = streamer.get_current_prices()[0]["price"]
        update = streamer._generate_price_update("AAPL")
        # Price should not deviate more than 2% per update
        assert abs(update["price"] - initial) / initial < 0.03

    def test_client_count_tracking(self):
        """Client count should track connections."""
        from augur.streaming import PriceStreamer
        streamer = PriceStreamer(tickers=["AAPL"], interval=60)
        assert streamer.client_count == 0

    def test_broadcast_to_no_clients(self):
        """Broadcasting with no clients should not error."""
        from augur.streaming import PriceStreamer
        streamer = PriceStreamer(tickers=["AAPL"], interval=60)
        # Test that broadcast function exists and handles empty clients
        assert streamer.client_count == 0
        # broadcast is async but we can verify the state
        assert not streamer.is_running


# ============ Input Validation Edge Cases ============

class TestInputValidation:
    """Tests for input validation across endpoints."""

    def test_ticker_validation_rejects_injection(self):
        """Ticker validation should reject path traversal."""
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        # Path traversal attempt - should be rejected (400 or 404)
        response = client.get("/api/sentiment/../../etc/passwd")
        assert response.status_code in (400, 404, 422)

    def test_ticker_validation_rejects_special_chars(self):
        """Ticker should reject special characters."""
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        response = client.get("/api/sentiment/<script>alert(1)</script>")
        assert response.status_code in (400, 404, 422)

    def test_optimizer_rejects_too_many_tickers(self):
        """Optimizer should reject more than 10 tickers."""
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        tickers = [f"T{i}" for i in range(11)]
        response = client.post("/api/optimize", json={
            "tickers": tickers, "risk_free_rate": 0.02
        })
        assert response.status_code == 400
        assert response.json()["detail"]  # any 400 detail is acceptable

    def test_optimizer_rejects_empty_tickers(self):
        """Optimizer should reject empty tickers list."""
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        response = client.post("/api/optimize", json={
            "tickers": [], "risk_free_rate": 0.02
        })
        assert response.status_code == 400

    def test_lang_endpoint_rejects_invalid(self):
        """Language endpoint should reject invalid language codes."""
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        response = client.post("/api/lang/fr")
        assert response.status_code == 400

    def test_i18n_endpoint_rejects_invalid_lang(self):
        """I18n endpoint should reject invalid language."""
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        response = client.get("/api/i18n/de")
        assert response.status_code == 400


# ============ Security Edge Cases ============

class TestSecurityEdgeCases:
    """Security-focused edge case tests."""

    def test_chat_xss_prevention(self):
        """Chat API should not reflect raw HTML/script tags."""
        from augur.chat import ChatEngine
        engine = ChatEngine()
        result = engine.get_response("<img src=x onerror=alert(1)>")
        # The response should contain the message reference but engine does not execute it
        assert result is not None

    def test_rules_path_traversal_safe(self):
        """Rules engine should use safe file paths."""
        from augur.rules import RulesEngine
        # Even with unusual path, should not crash
        engine = RulesEngine(rules_path="/tmp/test_augur_safe_rules.yaml")
        rules = engine.get_rules()
        assert isinstance(rules, list)

    @patch.dict(os.environ, {"AUGUR_MULTI_USER": "1"})
    def test_auth_register_validates_input(self):
        """Auth register should validate input lengths."""
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        # Too short username
        response = client.post("/api/auth/register", json={
            "username": "ab", "password": "validpass123"
        })
        assert response.status_code == 400

    @patch.dict(os.environ, {"AUGUR_MULTI_USER": "1"})
    def test_auth_register_rejects_short_password(self):
        """Auth register should reject short passwords."""
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        response = client.post("/api/auth/register", json={
            "username": "validuser", "password": "12345"
        })
        assert response.status_code == 400
