# -*- coding: utf-8 -*-
"""
Tests for augur.report - 深度分析报告生成模块（专业多大师融合报告）
"""

import pytest

from augur.personas.base import AgentResponse, MarketContext, SignalType
from augur.report import (
    generate_report,
    _format_signal_chinese,
    _format_agent_table,
    _format_theme_section,
    _format_disagreement_section,
    _format_bull_bear_debate,
    _format_financial_overview,
    _format_risk_matrix,
    _format_executive_summary,
    _score_to_grade,
    _format_market_cap,
    _clean_reasoning_for_table,
    THEME_GROUPS,
    AGENT_PHILOSOPHY,
)


def _make_agent_response(agent_id, agent_name, signal=SignalType.BULLISH, score=7.5, confidence=0.8,
                         reasoning=None, key_findings=None, risks=None):
    """Helper to create a test AgentResponse."""
    return AgentResponse(
        agent_id=agent_id,
        agent_name=agent_name,
        signal=signal,
        confidence=confidence,
        score=score,
        reasoning=reasoning if reasoning is not None else f"{agent_name} analysis reasoning for the stock",
        key_findings=key_findings if key_findings is not None else [f"{agent_name} finding 1", f"{agent_name} finding 2"],
        risks=risks if risks is not None else [f"{agent_name} risk 1"],
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
    """Create a full MarketContext for testing.

    NOTE: ratios (roe/margins/growth/debt_ratio) are DECIMALS as produced by data.py
    (yfinance convention), and market_cap/fcf are in BILLIONS of USD.
    """
    return MarketContext(
        ticker="AAPL",
        price=185.50,
        market_cap=2800.0,      # $2.8 trillion (in billions)
        pe=28.5,
        pb=45.2,
        ps=7.8,
        roe=1.60,               # 160%
        roa=0.285,              # 28.5%
        gross_margins=0.456,    # 45.6%
        operating_margins=0.302,  # 30.2%
        revenue_growth=0.085,   # 8.5%
        earnings_growth=0.123,  # 12.3%
        debt_ratio=0.65,        # 65%
        current_ratio=1.02,
        fcf=95.0,               # $95 billion
        sector="Technology",
        industry="Consumer Electronics",
    )


class TestFormatSignalChinese:
    """Test _format_signal_chinese helper."""

    def test_bullish(self):
        assert "看多" in _format_signal_chinese("bullish")

    def test_bearish(self):
        assert "看空" in _format_signal_chinese("bearish")

    def test_neutral(self):
        assert "中性" in _format_signal_chinese("neutral")

    def test_error(self):
        assert "错误" in _format_signal_chinese("error")

    def test_unknown_signal(self):
        assert _format_signal_chinese("unknown") == "unknown"


class TestGenerateReportBasic:
    """Test generate_report returns valid content."""

    def test_generate_report_basic(self):
        report = generate_report("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert report
        assert len(report) > 100
        assert any("\u4e00" <= ch <= "\u9fff" for ch in report)
        assert "# " in report

    def test_generate_report_has_all_sections(self):
        """Check for all professional module headers."""
        report = generate_report("AAPL", _make_full_context(), _make_full_results(), _make_consensus())

        # 1. 执行摘要 — neutral committee framing
        assert "投资委员会综合裁决" in report
        assert "执行摘要" in report
        # 2. 18位大师评分总表
        assert "18位大师评分总表" in report
        # 3. 分主题深度分析
        assert "分主题深度分析" in report
        # 4. 多空辩论
        assert "多空辩论" in report
        # 5. 分歧焦点
        assert "分歧焦点" in report
        # 6. 财务概览
        assert "财务概览" in report
        # 7. 共识与风险矩阵
        assert "共识与风险矩阵" in report
        assert "风险矩阵" in report
        # 8. 仓位建议
        assert "仓位建议" in report
        # 9. 免责声明
        assert "免责声明" in report
        assert "深度分析报告" in report

    def test_no_single_master_bias_in_title(self):
        """Executive summary must NOT be named after Buffett or any single master."""
        report = generate_report("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "巴菲特裁决" not in report
        assert "巴菲特的裁决" not in report
        # The verdict heading should be the neutral committee one
        assert "投资委员会综合裁决（执行摘要）" in report

    def test_all_four_themes_present(self):
        """Report must fuse all four investment schools."""
        report = generate_report("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "价值投资" in report
        assert "成长投资" in report
        assert "风险与宏观" in report
        assert "技术与量化" in report

    def test_generate_report_consensus_recommendation(self):
        report = generate_report("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "18位大师加权共识建议" in report

    def test_generate_report_agent_table_all_agents(self):
        """All 18 masters must appear (no master is dropped or over-weighted)."""
        results = _make_full_results()
        report = generate_report("AAPL", _make_full_context(), results, _make_consensus())
        for agent_id, response in results.items():
            assert response.agent_name in report

    def test_generate_report_contains_ticker(self):
        context = MarketContext(ticker="TSLA")
        results = {"buffett": _make_agent_response("buffett", "Warren Buffett")}
        report = generate_report("TSLA", context, results, _make_consensus())
        assert "TSLA" in report
        assert "TSLA 深度分析报告" in report

    def test_generate_report_minimal_context(self):
        context = MarketContext(ticker="XYZ")
        results = {"buffett": _make_agent_response("buffett", "Warren Buffett")}
        consensus = AgentResponse(
            agent_id="consensus", agent_name="Multi-Agent Consensus",
            signal=SignalType.NEUTRAL, confidence=0.5, score=5.0, reasoning="Limited data",
        )
        report = generate_report("XYZ", context, results, consensus)
        assert report
        assert "XYZ" in report
        assert "深度分析报告" in report
        assert "投资委员会综合裁决" in report
        assert "18位大师评分总表" in report

    def test_kelly_explanation_present(self):
        report = generate_report("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "Kelly" in report
        assert "半Kelly" in report


class TestUnitsCorrectness:
    """Verify percentage/currency units render correctly (the key bug to avoid)."""

    def test_roe_decimal_renders_as_percent(self):
        """roe=0.60 (decimal) must show as 60.0%, NOT 0.6%."""
        ctx = MarketContext(ticker="T", roe=0.60)
        section = _format_financial_overview(ctx)
        assert "60.0%" in section
        # The buggy "0.6%" must not appear for ROE
        assert "| ROE | 0.6% |" not in section

    def test_gross_margins_decimal_renders_as_percent(self):
        ctx = MarketContext(ticker="T", gross_margins=0.456)
        section = _format_financial_overview(ctx)
        assert "45.6%" in section

    def test_revenue_growth_decimal_renders_as_percent(self):
        ctx = MarketContext(ticker="T", revenue_growth=0.085)
        section = _format_financial_overview(ctx)
        assert "8.5%" in section

    def test_market_cap_trillion(self):
        """market_cap in billions: 2800 -> $2.80万亿."""
        assert _format_market_cap(2800.0) == "$2.80万亿"

    def test_market_cap_billions(self):
        assert _format_market_cap(95.0) == "$95.00B"

    def test_market_cap_millions(self):
        assert _format_market_cap(0.5) == "$500M"

    def test_market_cap_in_report(self):
        ctx = _make_full_context()
        report = generate_report("AAPL", ctx, _make_full_results(), _make_consensus())
        assert "$2.80万亿" in report
        # Raw trillion value must NOT leak
        assert "2800000000000" not in report

    def test_fcf_billions_in_report(self):
        ctx = _make_full_context()
        section = _format_financial_overview(ctx)
        assert "$95.00B" in section


class TestFloatPrecision:
    """Verify floating point noise is cleaned up."""

    def test_clean_reasoning_fixes_float_noise(self):
        text = "评分为 3.5999999999999996 分，护城河强"
        cleaned = _clean_reasoning_for_table(text, max_len=200)
        assert "3.6" in cleaned
        assert "3.5999999999999996" not in cleaned

    def test_report_no_long_float_noise(self):
        results = _make_full_results()
        results["buffett"] = _make_agent_response(
            "buffett", "Warren Buffett",
            reasoning="内在价值倍数为 2.7000000000000002 倍，安全边际充足",
        )
        report = generate_report("AAPL", _make_full_context(), results, _make_consensus())
        assert "2.7000000000000002" not in report


class TestMarkdownCleaning:
    """Verify markdown headers in reasoning don't pollute the table."""

    def test_table_strips_markdown_headers(self):
        results = {
            "buffett": _make_agent_response(
                "buffett", "Warren Buffett",
                reasoning="## 护城河分析\n会员制护城河极宽，续费率高",
            )
        }
        table = _format_agent_table(results)
        # The "##" markdown header must be stripped in the table cell
        assert "##" not in table

    def test_clean_reasoning_removes_headers(self):
        cleaned = _clean_reasoning_for_table("## 标题\n正文内容", max_len=200)
        assert "##" not in cleaned
        assert "正文内容" in cleaned


class TestScoreGrade:
    """Test the grade mapping."""

    def test_grade_high(self):
        grade, label = _score_to_grade(8.6)
        assert grade == "A+"

    def test_grade_mid(self):
        grade, label = _score_to_grade(7.0)
        assert grade == "B+"

    def test_grade_low(self):
        grade, label = _score_to_grade(3.5)
        assert grade == "D"

    def test_grade_appears_in_report(self):
        report = generate_report("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        # consensus score 7.3 -> B+
        assert "B+" in report


class TestFormatAgentTable:
    """Test _format_agent_table helper."""

    def test_table_has_header(self):
        table = _format_agent_table({"buffett": _make_agent_response("buffett", "Warren Buffett")})
        assert "| 大师 |" in table
        assert "| 信号 |" in table
        assert "| 评分 |" in table
        assert "| 投资框架 |" in table

    def test_table_contains_all_agents(self):
        results = _make_full_results()
        table = _format_agent_table(results)
        for agent_id, response in results.items():
            assert response.agent_name in table

    def test_table_shows_theme_and_philosophy(self):
        results = _make_full_results()
        table = _format_agent_table(results)
        # Buffett's theme and philosophy keyword
        assert "价值投资" in table
        assert "护城河" in table

    def test_table_empty_results(self):
        table = _format_agent_table({})
        assert "| 大师 |" in table


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
        section = _format_theme_section("技术与量化", ["arps", "dayu"], results)
        assert "技术与量化" in section
        assert "暂无" in section

    def test_zhang_lei_in_value_theme(self):
        results = _make_full_results()
        section = _format_theme_section("价值投资", THEME_GROUPS["价值投资"]["agents"], results)
        assert "Zhang Lei" in section
        tech_section = _format_theme_section("技术与量化", THEME_GROUPS["技术与量化"]["agents"], results)
        assert "Zhang Lei" not in tech_section

    def test_theme_with_error_agent(self):
        results = {
            "buffett": AgentResponse(
                agent_id="buffett", agent_name="Warren Buffett", signal=SignalType.ERROR,
                confidence=0, score=0, reasoning="Analysis failed: timeout",
            )
        }
        section = _format_theme_section("价值投资", ["buffett"], results)
        assert "分析失败" in section

    def test_theme_includes_agent_philosophy(self):
        results = _make_full_results()
        section = _format_theme_section("价值投资", THEME_GROUPS["价值投资"]["agents"], results)
        assert "投资框架" in section
        assert "护城河" in section

    def test_theme_has_verdict(self):
        results = _make_full_results()
        section = _format_theme_section("价值投资", THEME_GROUPS["价值投资"]["agents"], results)
        assert "流派裁决" in section


class TestDisagreementSection:
    """Test _format_disagreement_section helper."""

    def test_disagreement_with_mixed_signals(self):
        section = _format_disagreement_section(_make_full_results())
        assert "分歧焦点" in section
        assert "多空阵营对比" in section
        assert "看多" in section

    def test_disagreement_all_bullish(self):
        results = {
            "buffett": _make_agent_response("buffett", "Warren Buffett", SignalType.BULLISH, 8.0, 0.85),
            "graham": _make_agent_response("graham", "Benjamin Graham", SignalType.BULLISH, 7.5, 0.80),
        }
        section = _format_disagreement_section(results)
        assert "分歧焦点" in section
        assert "高度一致" in section

    def test_disagreement_empty_results(self):
        section = _format_disagreement_section({})
        assert "分歧焦点" in section
        assert "暂无" in section

    def test_disagreement_shows_score_spread(self):
        section = _format_disagreement_section(_make_full_results())
        assert "分歧度" in section

    def test_disagreement_shows_biggest_contention(self):
        section = _format_disagreement_section(_make_full_results())
        assert "最大分歧维度" in section


class TestBullBearDebate:
    """Test _format_bull_bear_debate helper."""

    def test_debate_has_both_sides(self):
        section = _format_bull_bear_debate(_make_full_results())
        assert "多空辩论" in section
        assert "多方论点" in section
        assert "空方论点" in section

    def test_debate_shows_top_3_bulls(self):
        section = _format_bull_bear_debate(_make_full_results())
        assert "Cathie Wood" in section  # highest score (8.5)

    def test_debate_shows_top_3_bears(self):
        section = _format_bull_bear_debate(_make_full_results())
        assert "Howard Marks" in section  # lowest score (4.5), the only bearish

    def test_debate_empty_results(self):
        section = _format_bull_bear_debate({})
        assert "多空辩论" in section
        assert "暂无" in section

    def test_debate_includes_philosophy(self):
        section = _format_bull_bear_debate(_make_full_results())
        assert "[" in section  # philosophy shown in brackets

    def test_debate_has_focus_summary(self):
        section = _format_bull_bear_debate(_make_full_results())
        assert "辩论焦点" in section


class TestExecutiveSummaryFusion:
    """Test the executive summary fuses all 18 masters without bias."""

    def test_summary_mentions_committee(self):
        summary = _format_executive_summary("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "投资委员会" in summary

    def test_summary_shows_signal_distribution(self):
        summary = _format_executive_summary("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "多空分布" in summary
        assert "看多" in summary
        assert "看空" in summary

    def test_summary_shows_grade(self):
        summary = _format_executive_summary("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "评级" in summary

    def test_summary_one_line_verdict(self):
        summary = _format_executive_summary("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "一句话裁决" in summary

    def test_summary_consensus_strength(self):
        summary = _format_executive_summary("AAPL", _make_full_context(), _make_full_results(), _make_consensus())
        assert "共识强度" in summary


class TestConsensusRiskMatrix:
    """Test the consensus and risk matrix aggregation."""

    def test_risk_matrix_sorted_by_frequency(self):
        """A risk mentioned by 3 masters should rank above one mentioned once."""
        results = {
            "buffett": _make_agent_response("buffett", "Warren Buffett", risks=["高估值风险", "竞争加剧"]),
            "graham": _make_agent_response("graham", "Benjamin Graham", risks=["高估值风险"]),
            "munger": _make_agent_response("munger", "Charlie Munger", risks=["高估值风险"]),
            "dalio": _make_agent_response("dalio", "Ray Dalio", risks=["宏观衰退"]),
        }
        section = _format_risk_matrix(results)
        assert "风险矩阵" in section
        # The most-mentioned risk should appear with count 3
        lines = section.split("\n")
        valuation_line = [ln for ln in lines if "高估值风险" in ln][0]
        assert "| 3 |" in valuation_line

    def test_risk_matrix_consensus_strengths(self):
        section = _format_risk_matrix(_make_full_results())
        assert "共识优势" in section

    def test_risk_matrix_empty_risks(self):
        results = {
            "buffett": _make_agent_response("buffett", "Warren Buffett", risks=[], key_findings=[]),
        }
        section = _format_risk_matrix(results)
        assert "风险矩阵" in section


class TestEdgeCases:
    """Test edge cases for report generation."""

    def test_empty_results(self):
        context = MarketContext(ticker="EMPTY")
        consensus = AgentResponse(
            agent_id="consensus", agent_name="Multi-Agent Consensus",
            signal=SignalType.NEUTRAL, confidence=0, score=0, reasoning="No results",
        )
        report = generate_report("EMPTY", context, {}, consensus)
        assert report
        assert "EMPTY" in report
        assert "深度分析报告" in report

    def test_all_error_agents(self):
        context = MarketContext(ticker="ERR")
        results = {
            "buffett": AgentResponse(agent_id="buffett", agent_name="Warren Buffett",
                                     signal=SignalType.ERROR, confidence=0, score=0, reasoning="API timeout"),
            "graham": AgentResponse(agent_id="graham", agent_name="Benjamin Graham",
                                    signal=SignalType.ERROR, confidence=0, score=0, reasoning="Data unavailable"),
        }
        consensus = AgentResponse(agent_id="consensus", agent_name="Multi-Agent Consensus",
                                  signal=SignalType.NEUTRAL, confidence=0, score=0, reasoning="All agents failed")
        report = generate_report("ERR", context, results, consensus)
        assert report
        assert "ERR" in report

    def test_missing_position_sizing(self):
        context = MarketContext(ticker="TEST")
        results = {"buffett": _make_agent_response("buffett", "Warren Buffett")}
        consensus = AgentResponse(agent_id="consensus", agent_name="Multi-Agent Consensus",
                                  signal=SignalType.BULLISH, confidence=0.75, score=7.0, reasoning="Test consensus")
        report = generate_report("TEST", context, results, consensus)
        assert report
        assert "仓位建议" in report

    def test_negative_or_zero_metrics_skipped(self):
        """Zero/empty metrics should be skipped gracefully without crashing."""
        ctx = MarketContext(ticker="ZERO", pe=0, roe=0, market_cap=0, gross_margins=0)
        section = _format_financial_overview(ctx)
        assert "财务概览" in section


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
            with open(tmppath, 'r') as f:
                content = f.read()
            assert "MSFT" in content
            assert "深度分析报告" in content
        finally:
            os.unlink(tmppath)


class TestReportAPIEndpoint:
    """Test /api/report/ endpoint."""

    def test_report_endpoint(self):
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
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        response = client.get("/api/report/INVALID!!!TICKER")
        assert response.status_code == 400

    def test_report_post_endpoint(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from fastapi.testclient import TestClient
        from dashboard.app import app
        client = TestClient(app)
        response = client.get("/api/analyze/AAPL?pe=25&auto_fetch=false")
        assert response.status_code == 200
        analysis_data = response.json()
        response = client.post("/api/report/AAPL", json=analysis_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["ticker"] == "AAPL"
        assert "report" in data
        assert "深度分析报告" in data["report"]
        assert data["data_source"] == "cached"
