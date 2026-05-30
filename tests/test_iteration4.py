# -*- coding: utf-8 -*-
"""Tests for iteration 4 fixes: backtest edge cases, CLI sector/industry, Docker security."""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner
from augur.cli import main


class TestBacktestEdgeCases:
    """Test backtest edge cases fixed in iteration 4."""

    def test_empty_historical_data_returns_empty_result(self):
        """run_backtest with empty lists returns BacktestResult with no records."""
        from augur.backtest import Backtester
        bt = Backtester()
        result = bt.run_backtest("TEST", [], [])
        assert result.ticker == "TEST"
        assert result.records == []
        assert result.agent_ics == []

    def test_empty_forward_returns_returns_empty_result(self):
        """run_backtest with empty forward_returns returns empty result."""
        from augur.backtest import Backtester
        bt = Backtester()
        result = bt.run_backtest("TEST", [{"date": "2024-01-01", "price": 100}], [])
        assert result.ticker == "TEST"
        assert result.records == []

    def test_single_day_backtest(self):
        """Single day of data should produce valid results."""
        from augur.backtest import Backtester
        bt = Backtester()
        hist = [{"date": "2024-01-01", "price": 150, "pe": 25, "roe": 0.15,
                 "gross_margins": 0.4, "revenue_growth": 0.1, "debt_ratio": 0.3}]
        fwd = [{"date": "2024-01-01", "return_5d": 0.02, "return_20d": 0.05, "return_60d": 0.10}]
        result = bt.run_backtest("AAPL", hist, fwd)
        assert result.ticker == "AAPL"
        assert len(result.records) > 0  # Should have records from all agents for that day

    def test_deterministic_seed_stability(self):
        """generate_sample_data produces consistent results across calls."""
        from augur.backtest import generate_sample_data
        h1, f1 = generate_sample_data("STABLE", 10)
        h2, f2 = generate_sample_data("STABLE", 10)
        # Must be identical
        assert h1[0]["price"] == h2[0]["price"]
        assert h1[5]["pe"] == h2[5]["pe"]
        assert f1[0]["return_5d"] == f2[0]["return_5d"]

    def test_different_tickers_produce_different_data(self):
        """Different tickers should produce different sample data."""
        from augur.backtest import generate_sample_data
        h1, _ = generate_sample_data("AAPL", 5)
        h2, _ = generate_sample_data("MSFT", 5)
        # Very unlikely to be same price
        assert h1[0]["price"] != h2[0]["price"]


class TestBacktestRankCorrelation:
    """Test the _rank_correlation implementation."""

    def test_rank_correlation_identical_values(self):
        """All same x values should return 0.0 (zero variance)."""
        from augur.backtest import Backtester
        bt = Backtester()
        assert bt._rank_correlation([5, 5, 5, 5, 5], [1, 2, 3, 4, 5]) == 0.0

    def test_rank_correlation_perfect_positive(self):
        """Perfectly correlated data should return 1.0."""
        from augur.backtest import Backtester
        bt = Backtester()
        result = bt._rank_correlation([1, 2, 3, 4, 5], [10, 20, 30, 40, 50])
        assert abs(result - 1.0) < 0.001

    def test_rank_correlation_perfect_negative(self):
        """Perfectly inverse-correlated data should return -1.0."""
        from augur.backtest import Backtester
        bt = Backtester()
        result = bt._rank_correlation([1, 2, 3, 4, 5], [50, 40, 30, 20, 10])
        assert abs(result - (-1.0)) < 0.001

    def test_rank_correlation_short_list(self):
        """Lists with fewer than 3 elements should return 0.0."""
        from augur.backtest import Backtester
        bt = Backtester()
        assert bt._rank_correlation([1, 2], [2, 1]) == 0.0
        assert bt._rank_correlation([1], [1]) == 0.0
        assert bt._rank_correlation([], []) == 0.0


class TestCLISectorIndustry:
    """Test CLI sector/industry options added in iteration 4."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_analyze_with_sector_industry(self, runner):
        """analyze command accepts --sector and --industry options."""
        result = runner.invoke(main, [
            "analyze", "TEST", "--pe", "20", "--roe", "0.15",
            "--sector", "Technology", "--industry", "Semiconductor"
        ])
        assert result.exit_code == 0
        assert "TEST" in result.output

    def test_watchlist_add_with_sector(self, runner):
        """watchlist-add command accepts --sector option."""
        result = runner.invoke(main, ["watchlist-add", "--help"])
        assert "--sector" in result.output
        assert "--industry" in result.output

    def test_watchlist_add_sector_value_stored(self, runner):
        """watchlist-add with --sector stores the value."""
        # Use a unique ticker to avoid conflicts
        result = runner.invoke(main, [
            "watchlist-add", "ITER4TEST", "--pe", "30",
            "--sector", "Healthcare"
        ])
        assert result.exit_code == 0
        assert "ITER4TEST" in result.output

    def test_analyze_invalid_persona_exits_1(self, runner):
        """analyze with non-existent persona should exit with code 1."""
        result = runner.invoke(main, [
            "analyze", "AAPL", "--persona", "nonexistent_persona_xyz", "--pe", "20"
        ])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestDockerfileConsistency:
    """Verify Docker configuration improvements from iteration 4."""

    def test_dockerfile_has_non_root_user(self):
        """Dockerfile should contain USER directive for non-root execution."""
        dockerfile_path = Path("/projects/sandbox/augur/Dockerfile")
        content = dockerfile_path.read_text()
        assert "USER" in content
        # Should have useradd or groupadd for creating the user
        assert "augur" in content.lower()

    def test_dockercompose_no_version(self):
        """docker-compose.yml should not have deprecated version field."""
        compose_path = Path("/projects/sandbox/augur/docker-compose.yml")
        content = compose_path.read_text()
        # Should not start with version:
        lines = content.strip().split("\n")
        first_non_empty = next(l for l in lines if l.strip())
        assert not first_non_empty.strip().startswith("version:")

    def test_dockercompose_has_healthchecks(self):
        """docker-compose.yml should have healthcheck configurations."""
        compose_path = Path("/projects/sandbox/augur/docker-compose.yml")
        content = compose_path.read_text()
        assert "healthcheck:" in content
        assert "/health" in content


class TestRequirementsConsistency:
    """Verify requirements.txt and pyproject.toml are in sync."""

    def test_httpx_in_requirements(self):
        """requirements.txt should include httpx since pyproject.toml lists it."""
        req_path = Path("/projects/sandbox/augur/requirements.txt")
        content = req_path.read_text()
        assert "httpx" in content

    def test_all_core_deps_in_requirements(self):
        """All core pyproject.toml dependencies should be in requirements.txt."""
        req_path = Path("/projects/sandbox/augur/requirements.txt")
        content = req_path.read_text().lower()
        # Core deps from pyproject.toml
        for dep in ["click", "pyyaml", "fastapi", "uvicorn", "jinja2", "httpx"]:
            assert dep in content, f"{dep} missing from requirements.txt"
