# -*- coding: utf-8 -*-
"""
Tests for augur.report - 深度分析报告生成模块
"""

import pytest

from augur.personas.base import AgentResponse, MarketContext, SignalType
from augur.report import (
    generate_report,
    _format_signal_chinese,
    _format_agent_table,
    _format_theme_section,
    THEME_GROUPS,
)


def _make_agent_response(agent_id, agent_name, signal=SignalType.BULLISH, score=7.5, confidence=0.8):
    """Helper to create a test AgentResponse."""
    return AgentResponse(
        agent_id=agent_id,
        agent_name=agent_name,
        signal=signal,
        confidence=confidence,
        score=score,
        reasoning=f"{agent_name} analysis reasoning for the stock",
        key_findings=[f"{agent_name} finding 1", f"{agent_name} finding 2"],
        risks=[f"{agent_name} risk 1"],
    )


def _make_full_results():
    """Create a full set of 18 agent results for testing."""
    agents = [
        ("buffett", "Warren Buffett", SignalType.BULLISH, 8.0, 0.85),
        ("graham", "Benjamin Graham", SignalType.BULLISH, 7.5, 0.80),
        ("munger", "Charlie Munger", SignalType.BULLISH, 7.8, 0.82),
        ("duan_yongping", "Duan Yongping", SignalType.BULLISH, 7.2, 0.75),
        ("li_lu", "Li Lu", SignalType.BULLISH, 7.0, 0.78),
        ("dan_bin", "Dan Bin", SignalType.NEUTRAL, 6.5, 0.70),
        ("cathie_wood", "Cathie Wood", SignalType.BULLISH, 8.5, 0.88),
        ("fisher", "Philip Fisher", SignalType.BULLISH, 7.8, 0.82),
        ("lynch", "Peter Lynch", SignalType.BULLISH, 8.0, 0.85),
        ("aschenbrenner", "Leopold Aschenbrenner", SignalType.BULLISH, 8.2, 0.86),
        ("thiel", "Peter Thiel", SignalType.BULLISH, 7.5, 0.80),
        ("dalio", "Ray Dalio", SignalType.NEUTRAL, 6.0, 0.72),
        ("soros", "George Soros", SignalType.NEUTRAL, 5.5, 0.65),
        ("marks", "Howard Marks", SignalType.BEARISH, 4.5, 0.70),
        ("serenity", "Serenity", SignalType.NEUTRAL, 5.8, 0.68),
        ("arps", "Martin Arps", SignalType.BULLISH, 7.0, 0.75),
        ("dayu", "Dayu", SignalType.NEUTRAL, 6.2, 0.70),
        ("zhang_lei", "Zhang Lei", SignalType.BULLISH, 7.5, 0.80),
    ]
    results = {}
    for agent_id, name, signal, score, confidence in agents:
        results[agent_id] = _make_agent_response(agent_id, name, signal, score, confidence)
    return results


def _make_consensus():
    """Create a consensus AgentResponse for testing."""
    consensus = AgentResponse(
        agent_id="consensus",
        agent_name="Multi-Agent Consensus",
        signal=SignalType.BULLISH,
        confidence=0.82,
        score=7.3,
        reasoning="Consensus from 18 agents",
        key_findings=["Strong fundamentals", "Good growth potential", "Reasonable valuation"],
        risks=["Market volatility", "Competition risk"],
    )
    consensus.metadata["position_sizing"] = {
        "position_pct": 5.0,
        "signal": "bullish",
        "score": 7.3,
        "confidence": 0.82,
        "rationale": "half-Kelly: 5.0% (score=7.3, conf=82%)",
    }
    consensus.metadata["position_pct"] = 5.0
    return consensus


def _make_full_context():
    """Create a full MarketContext for testing."""
    return MarketContext(
        ticker="AAPL",
        price=185.50,
        market_cap=2.8e12,
        pe=28.5,
        pb=45.2,
        ps=7.8,
        roe=160.0,
        roa=28.5,
        gross_margins=45.6,
        operating_margins=30.2,
        revenue_growth=8.5,
        earnings_growth=12.3,
        debt_ratio=65.0,
        current_ratio=1.02,
        fcf=95e9,
        sector="Technology",
        industry="Consumer Electronics",
    )


class TestFormatSignalChinese:
    """Test _format_signal_chinese helper."""

    def test_bullish(self):
        result = _format_signal_chinese("bullish")
        assert "看多" in result

    def test_bearish(self):
        result = _format_signal_chinese("bearish")
        assert "看空" in result

    def test_neutral(self):
        result = _format_signal_chinese("neutral")
        assert "中性" in result

    def test_error(self):
        result = _format_signal_chinese("error")
        assert "错误" in result

    def test_unknown_signal(self):
        result = _format_signal_chinese("unknown")
        assert result == "unknown"


class TestGenerateReportBasic:
    """Test generate_report returns valid content."""

    def test_generate_report_basic(self):
        """Verify it returns non-empty markdown with Chinese content."""
        context = _make_full_context()
        results = _make_full_results()
        consensus = _make_consensus()

        report = generate_report("AAPL", context, results, consensus)

        assert report
        assert len(report) > 100
        # Should contain Chinese characters
        assert any("\u4e00" <= ch <= "\u9fff" for ch in report)
        # Should be markdown (has headers)
        assert "# " in report

    def test_generate_report_has_all_sections(self):
        """Check for all section headers."""
        context = _make_full_context()
        results = _make_full_results()
        consensus = _make_consensus()

        report = generate_report("AAPL", context, results, consensus)

        # Check for major section headers
        assert "深度分析报告" in report
        assert "巴菲特裁决" in report
        assert "Agent共识分析表" in report
        assert "分主题深度分析" in report
        assert "财务概览" in report
        assert "风险矩阵" in report
        assert "仓位建议" in report
        assert "免责声明" in report

    def test_generate_report_agent_table(self):
        """Verify agent table has all agents."""
        context = _make_full_context()
        results = _make_full_results()
        consensus = _make_consensus()

        report = generate_report("AAPL", context, results, consensus)

        # All 18 agents should be mentioned in the report
        for agent_id, response in results.items():
            assert response.agent_name in report

    def test_generate_report_contains_ticker(self):
        """Verify ticker appears in the title."""
        context = MarketContext(ticker="TSLA")
        results = {"buffett": _make_agent_response("buffett", "Warren Buffett")}
        consensus = _make_consensus()

        report = generate_report("TSLA", context, results, consensus)

        assert "TSLA" in report
        assert "TSLA 深度分析报告" in report

    def test_generate_report_minimal_context(self):
        """Works with just a ticker name (minimal context)."""
        context = MarketContext(ticker="XYZ")
        results = {"buffett": _make_agent_response("buffett", "Warren Buffett")}
        consensus = AgentResponse(
            agent_id="consensus",
            agent_name="Multi-Agent Consensus",
            signal=SignalType.NEUTRAL,
            confidence=0.5,
            score=5.0,
            reasoning="Limited data",
        )

        report = generate_report("XYZ", context, results, consensus)

        assert report
        assert "XYZ" in report
        assert "深度分析报告" in report
        # Should still have section headers
        assert "巴菲特裁决" in report
        assert "Agent共识分析表" in report


class TestFormatAgentTable:
    """Test _format_agent_table helper."""

    def test_table_has_header(self):
        results = {"buffett": _make_agent_response("buffett", "Warren Buffett")}
        table = _format_agent_table(results)

        assert "| Agent |" in table
        assert "| 信号 |" in table
        assert "| 评分 |" in table

    def test_table_contains_all_agents(self):
        results = _make_full_results()
        table = _format_agent_table(results)

        for agent_id, response in results.items():
            assert response.agent_name in table

    def test_table_empty_results(self):
        table = _format_agent_table({})
        # Should still have headers but no data rows
        assert "| Agent |" in table


class TestFormatThemeSection:
    """Test _format_theme_section helper."""

    def test_value_theme(self):
        results = _make_full_results()
        section = _format_theme_section("价值投资", THEME_GROUPS["价值投资"]["agents"], results)

        assert "价值投资" in section
        assert "Warren Buffett" in section
        assert "Benjamin Graham" in section

    def test_theme_with_no_matching_agents(self):
        results = {"buffett": _make_agent_response("buffett", "Warren Buffett")}
        section = _format_theme_section("技术与量化", ["arps", "dayu", "zhang_lei"], results)

        assert "技术与量化" in section
        assert "暂无" in section

    def test_theme_with_error_agent(self):
        results = {
            "buffett": AgentResponse(
                agent_id="buffett",
                agent_name="Warren Buffett",
                signal=SignalType.ERROR,
                confidence=0,
                score=0,
                reasoning="Analysis failed: timeout",
            )
        }
        section = _format_theme_section("价值投资", ["buffett"], results)

        assert "分析失败" in section


class TestEdgeCases:
    """Test edge cases for report generation."""

    def test_empty_results(self):
        """Empty results should still produce a valid report."""
        context = MarketContext(ticker="EMPTY")
        results = {}
        consensus = AgentResponse(
            agent_id="consensus",
            agent_name="Multi-Agent Consensus",
            signal=SignalType.NEUTRAL,
            confidence=0,
            score=0,
            reasoning="No results",
        )

        report = generate_report("EMPTY", context, results, consensus)

        assert report
        assert "EMPTY" in report
        assert "深度分析报告" in report

    def test_all_error_agents(self):
        """All-error agents should still produce a valid report."""
        context = MarketContext(ticker="ERR")
        results = {
            "buffett": AgentResponse(
                agent_id="buffett",
                agent_name="Warren Buffett",
                signal=SignalType.ERROR,
                confidence=0,
                score=0,
                reasoning="API timeout",
            ),
            "graham": AgentResponse(
                agent_id="graham",
                agent_name="Benjamin Graham",
                signal=SignalType.ERROR,
                confidence=0,
                score=0,
                reasoning="Data unavailable",
            ),
        }
        consensus = AgentResponse(
            agent_id="consensus",
            agent_name="Multi-Agent Consensus",
            signal=SignalType.NEUTRAL,
            confidence=0,
            score=0,
            reasoning="All agents failed",
        )

        report = generate_report("ERR", context, results, consensus)

        assert report
        assert "ERR" in report

    def test_missing_position_sizing(self):
        """Missing position_sizing metadata should not crash."""
        context = MarketContext(ticker="TEST")
        results = {"buffett": _make_agent_response("buffett", "Warren Buffett")}
        consensus = AgentResponse(
            agent_id="consensus",
            agent_name="Multi-Agent Consensus",
            signal=SignalType.BULLISH,
            confidence=0.75,
            score=7.0,
            reasoning="Test consensus",
        )
        # No position_sizing in metadata

        report = generate_report("TEST", context, results, consensus)

        assert report
        assert "仓位建议" in report


class TestCLIReportCommand:
    """Test CLI report command."""

    def test_report_help(self):
        from click.testing import CliRunner
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["report", "--help"])
        assert result.exit_code == 0
        assert "TICKER" in result.output
        assert "--output" in result.output

    def test_report_runs_with_metrics(self):
        from click.testing import CliRunner
        from augur.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["report", "AAPL", "--pe", "25", "--roe", "0.55"])
        assert result.exit_code == 0
        assert "AAPL" in result.output
        assert "深度分析报告" in result.output

    def test_report_save_to_file(self):
        import tempfile
        import os
        from click.testing import CliRunner
        from augur.cli import main
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            tmppath = f.name
        try:
            result = runner.invoke(main, ["report", "MSFT", "--pe", "30", "--output", tmppath])
            assert result.exit_code == 0
            assert "保存" in result.output or tmppath in result.output
            # File should exist and contain report
            with open(tmppath, 'r') as f:
                content = f.read()
            assert "MSFT" in content
            assert "深度分析报告" in content
        finally:
            os.unlink(tmppath)


class TestReportAPIEndpoint:
    """Test /api/report/ endpoint."""

    def test_report_endpoint(self):
        """Test the report API endpoint returns correct structure."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from fastapi.testclient import TestClient
        from dashboard.app import app

        client = TestClient(app)
        response = client.get("/api/report/AAPL?pe=25&auto_fetch=false")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["ticker"] == "AAPL"
        assert "report" in data
        assert "深度分析报告" in data["report"]
        assert "timestamp" in data

    def test_report_endpoint_invalid_ticker(self):
        """Test the report API endpoint rejects invalid tickers."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from fastapi.testclient import TestClient
        from dashboard.app import app

        client = TestClient(app)
        response = client.get("/api/report/INVALID!!!TICKER")
        assert response.status_code == 400
