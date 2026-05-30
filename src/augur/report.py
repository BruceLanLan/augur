# -*- coding: utf-8 -*-
"""
augur.report - 深度分析报告生成模块

将多Agent分析结果转化为结构化的中文Markdown深度分析报告。
"""

from datetime import datetime
from typing import Dict, List

from augur.personas.base import AgentResponse, MarketContext, SignalType


# ============ Agent主题分组 ============

THEME_GROUPS = {
    "价值投资": {
        "agents": ["buffett", "graham", "munger", "duan_yongping", "li_lu", "dan_bin", "zhang_lei"],
        "description": "价值投资视角，关注安全边际、内在价值与长期持有",
    },
    "成长投资": {
        "agents": ["cathie_wood", "fisher", "lynch", "aschenbrenner", "thiel"],
        "description": "成长投资视角，关注创新驱动、颠覆性技术与高增长潜力",
    },
    "风险与宏观": {
        "agents": ["dalio", "soros", "marks", "serenity"],
        "description": "宏观与风险管理视角，关注周期、风险溢价与尾部风险",
    },
    "技术与量化": {
        "agents": ["arps", "dayu"],
        "description": "技术分析与量化视角，关注价格行为、动量与资金流向",
    },
}


def _format_signal_chinese(signal_value: str) -> str:
    """将英文信号转换为中文标签。

    Args:
        signal_value: 信号字符串，如 'bullish', 'neutral', 'bearish', 'error'

    Returns:
        中文信号标签
    """
    mapping = {
        "bullish": "看多 🟢",
        "neutral": "中性 🟡",
        "bearish": "看空 🔴",
        "error": "错误 ⚠️",
    }
    return mapping.get(signal_value, signal_value)


def _format_signal_emoji(signal_value: str) -> str:
    """返回信号对应的纯emoji。"""
    mapping = {
        "bullish": "🟢",
        "neutral": "🟡",
        "bearish": "🔴",
        "error": "⚠️",
    }
    return mapping.get(signal_value, "")


def _format_agent_table(results: Dict[str, AgentResponse]) -> str:
    """生成Agent共识表格（Markdown格式）。

    Args:
        results: 所有Agent的分析结果

    Returns:
        Markdown表格字符串
    """
    lines = []
    lines.append("| Agent | 信号 | 评分 | 置信度 | 核心观点 |")
    lines.append("|-------|------|------|--------|----------|")

    for agent_id, response in sorted(results.items(), key=lambda x: x[1].score, reverse=True):
        signal_str = _format_signal_chinese(response.signal.value)
        score_str = f"{response.score:.1f}/10"
        confidence_str = f"{response.confidence:.0%}"
        reasoning_short = response.reasoning[:60] + "..." if len(response.reasoning) > 60 else response.reasoning
        lines.append(
            f"| {response.agent_name} | {signal_str} | {score_str} | {confidence_str} | {reasoning_short} |"
        )

    return "\n".join(lines)


def _format_theme_section(theme_name: str, agent_ids: List[str], results: Dict[str, AgentResponse]) -> str:
    """生成主题分组分析区段。

    Args:
        theme_name: 主题名称
        agent_ids: 该主题下的Agent ID列表
        results: 所有Agent的分析结果

    Returns:
        Markdown格式的主题分析区段
    """
    lines = []
    theme_info = THEME_GROUPS.get(theme_name, {})
    description = theme_info.get("description", "")

    lines.append(f"### {theme_name}")
    if description:
        lines.append(f"> {description}")
    lines.append("")

    # 筛选本主题中有结果的Agent
    theme_results = {aid: results[aid] for aid in agent_ids if aid in results}

    if not theme_results:
        lines.append("*该主题下暂无Agent分析结果*")
        lines.append("")
        return "\n".join(lines)

    # 信号统计
    bullish_count = sum(1 for r in theme_results.values() if r.signal == SignalType.BULLISH)
    bearish_count = sum(1 for r in theme_results.values() if r.signal == SignalType.BEARISH)
    neutral_count = sum(1 for r in theme_results.values() if r.signal == SignalType.NEUTRAL)
    avg_score = sum(r.score for r in theme_results.values()) / len(theme_results) if theme_results else 0

    lines.append(f"**主题共识**: 看多 {bullish_count} / 中性 {neutral_count} / 看空 {bearish_count} | 平均评分: {avg_score:.1f}/10")
    lines.append("")

    # 每个Agent的详细分析
    for agent_id, response in theme_results.items():
        if response.signal == SignalType.ERROR:
            lines.append(f"**{response.agent_name}**: ⚠️ 分析失败 - {response.reasoning[:100]}")
            lines.append("")
            continue

        signal_str = _format_signal_chinese(response.signal.value)
        lines.append(f"**{response.agent_name}** ({signal_str}, {response.score:.1f}/10, 置信度 {response.confidence:.0%})")
        lines.append("")

        if response.reasoning:
            reasoning_text = response.reasoning[:500] + "..." if len(response.reasoning) > 500 else response.reasoning
            lines.append(f"- **核心逻辑**: {reasoning_text}")

        if response.key_findings:
            lines.append("- **关键发现**:")
            for finding in response.key_findings[:5]:
                lines.append(f"  - {finding}")

        if response.risks:
            lines.append("- **风险提示**:")
            for risk in response.risks[:3]:
                lines.append(f"  - {risk}")

        lines.append("")

    return "\n".join(lines)


def _format_financial_overview(context: MarketContext) -> str:
    """生成财务概览区段。

    Args:
        context: 市场上下文数据

    Returns:
        Markdown格式的财务概览
    """
    lines = []
    lines.append("## 财务概览")
    lines.append("")

    # 基本估值指标
    lines.append("### 估值指标")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")

    if context.price:
        lines.append(f"| 当前价格 | ${context.price:.2f} |")
    if context.market_cap:
        if context.market_cap >= 1e12:
            cap_str = f"${context.market_cap / 1e12:.2f}万亿"
        elif context.market_cap >= 1e9:
            cap_str = f"${context.market_cap / 1e9:.2f}亿"
        elif context.market_cap >= 1e6:
            cap_str = f"${context.market_cap / 1e6:.2f}百万"
        else:
            cap_str = f"${context.market_cap:.0f}"
        lines.append(f"| 市值 | {cap_str} |")
    if context.pe:
        lines.append(f"| 市盈率 (PE) | {context.pe:.1f}x |")
    if context.pb:
        lines.append(f"| 市净率 (PB) | {context.pb:.2f}x |")
    if context.ps:
        lines.append(f"| 市销率 (PS) | {context.ps:.2f}x |")

    lines.append("")

    # 盈利能力指标
    has_profitability = any([context.roe, context.roa, context.gross_margins, context.operating_margins])
    if has_profitability:
        lines.append("### 盈利能力")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        if context.roe:
            lines.append(f"| ROE | {context.roe:.1f}% |")
        if context.roa:
            lines.append(f"| ROA | {context.roa:.1f}% |")
        if context.gross_margins:
            lines.append(f"| 毛利率 | {context.gross_margins:.1f}% |")
        if context.operating_margins:
            lines.append(f"| 营业利润率 | {context.operating_margins:.1f}% |")
        lines.append("")

    # 成长指标
    has_growth = any([context.revenue_growth, context.earnings_growth])
    if has_growth:
        lines.append("### 成长性")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        if context.revenue_growth:
            lines.append(f"| 营收增长率 | {context.revenue_growth:.1f}% |")
        if context.earnings_growth:
            lines.append(f"| 盈利增长率 | {context.earnings_growth:.1f}% |")
        lines.append("")

    # 财务健康
    has_health = any([context.debt_ratio, context.current_ratio, context.fcf])
    if has_health:
        lines.append("### 财务健康")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        if context.debt_ratio:
            lines.append(f"| 负债率 | {context.debt_ratio:.1f}% |")
        if context.current_ratio:
            lines.append(f"| 流动比率 | {context.current_ratio:.2f} |")
        if context.fcf:
            if abs(context.fcf) >= 1e9:
                fcf_str = f"${context.fcf / 1e9:.2f}亿"
            elif abs(context.fcf) >= 1e6:
                fcf_str = f"${context.fcf / 1e6:.2f}百万"
            else:
                fcf_str = f"${context.fcf:.0f}"
            lines.append(f"| 自由现金流 | {fcf_str} |")
        lines.append("")

    # 行业信息
    if context.sector or context.industry:
        lines.append("### 行业定位")
        lines.append("")
        if context.sector:
            lines.append(f"- **所属板块**: {context.sector}")
        if context.industry:
            lines.append(f"- **细分行业**: {context.industry}")
        lines.append("")

    return "\n".join(lines)


def _format_risk_matrix(results: Dict[str, AgentResponse]) -> str:
    """生成风险矩阵区段。

    Args:
        results: 所有Agent的分析结果

    Returns:
        Markdown格式的风险矩阵
    """
    lines = []
    lines.append("## 风险矩阵")
    lines.append("")

    # 收集所有Agent的风险
    all_risks: Dict[str, List[str]] = {}
    for agent_id, response in results.items():
        if response.signal == SignalType.ERROR:
            continue
        for risk in response.risks:
            if risk not in all_risks:
                all_risks[risk] = []
            all_risks[risk].append(response.agent_name)

    if not all_risks:
        lines.append("*暂无显著风险提示*")
        lines.append("")
        return "\n".join(lines)

    # 按提及次数排序
    sorted_risks = sorted(all_risks.items(), key=lambda x: len(x[1]), reverse=True)

    lines.append("| 风险因素 | 提及次数 | 提出者 |")
    lines.append("|----------|----------|--------|")

    for risk, agents in sorted_risks[:15]:
        risk_short = risk[:80] + "..." if len(risk) > 80 else risk
        agents_str = ", ".join(agents[:3])
        if len(agents) > 3:
            agents_str += f" 等{len(agents)}位"
        lines.append(f"| {risk_short} | {len(agents)} | {agents_str} |")

    lines.append("")
    return "\n".join(lines)


def _format_position_recommendation(consensus: AgentResponse) -> str:
    """生成仓位建议区段。

    Args:
        consensus: 共识结果

    Returns:
        Markdown格式的仓位建议
    """
    lines = []
    lines.append("## 仓位建议")
    lines.append("")

    position_sizing = consensus.metadata.get("position_sizing", {})
    position_pct = position_sizing.get("position_pct", consensus.metadata.get("position_pct", 0))

    signal_str = _format_signal_chinese(consensus.signal.value)

    lines.append("| 项目 | 内容 |")
    lines.append("|------|------|")
    lines.append(f"| **综合信号** | {signal_str} |")
    lines.append(f"| **综合评分** | {consensus.score:.1f}/10 |")
    lines.append(f"| **置信度** | {consensus.confidence:.0%} |")
    lines.append(f"| **建议仓位** | {position_pct:.1f}% |")

    if position_sizing.get("rationale"):
        lines.append(f"| **仓位逻辑** | {position_sizing['rationale']} |")

    lines.append("")

    # Kelly sizing 说明
    lines.append("### Kelly仓位计算")
    lines.append("")
    if consensus.signal == SignalType.BULLISH:
        lines.append(f"- 基于半Kelly公式计算，建议配置 **{position_pct:.1f}%** 仓位")
        lines.append(f"- 评分 {consensus.score:.1f}/10 + 置信度 {consensus.confidence:.0%} = 风险可控")
    elif consensus.signal == SignalType.BEARISH:
        lines.append("- 看空信号，建议 **不建仓** 或 **减仓**")
        lines.append("- 等待更明确的入场信号")
    else:
        lines.append(f"- 中性信号，建议 **观望** 或 **轻仓** ({position_pct:.1f}%)")
        lines.append("- 等待方向明确后再加仓")

    lines.append("")
    return "\n".join(lines)


def generate_report(
    ticker: str,
    context: MarketContext,
    results: Dict[str, AgentResponse],
    consensus: AgentResponse,
) -> str:
    """生成中文Markdown深度分析报告。

    Args:
        ticker: 股票代码
        context: 市场上下文数据
        results: 所有Agent的分析结果 Dict[agent_id, AgentResponse]
        consensus: 共识分析结果

    Returns:
        完整的Markdown格式深度分析报告字符串
    """
    sections = []

    # ============ 标题与元数据 ============
    sections.append(f"# {ticker} 深度分析报告")
    sections.append("")
    sections.append(f"> **分析日期**: {datetime.now().strftime('%Y年%m月%d日')}")
    sections.append(f"> **分析方法**: 18-Agent共识分析框架（多维度投资决策系统）")
    sections.append(f"> **数据来源**: 公开市场数据")
    sections.append("")
    sections.append("---")
    sections.append("")

    # ============ 执行摘要（巴菲特裁决） ============
    sections.append("## 巴菲特裁决（执行摘要）")
    sections.append("")

    signal_str = _format_signal_chinese(consensus.signal.value)
    position_sizing = consensus.metadata.get("position_sizing", {})
    position_pct = position_sizing.get("position_pct", consensus.metadata.get("position_pct", 0))

    # 信号分布统计
    valid_results = {k: v for k, v in results.items() if v.signal != SignalType.ERROR}
    bullish_count = sum(1 for r in valid_results.values() if r.signal == SignalType.BULLISH)
    bearish_count = sum(1 for r in valid_results.values() if r.signal == SignalType.BEARISH)
    neutral_count = sum(1 for r in valid_results.values() if r.signal == SignalType.NEUTRAL)

    sections.append("### 综合评分卡")
    sections.append("")
    sections.append("| 项目 | 结果 |")
    sections.append("|------|------|")
    sections.append(f"| **综合信号** | {signal_str} |")
    sections.append(f"| **综合评分** | {consensus.score:.1f}/10 |")
    sections.append(f"| **置信度** | {consensus.confidence:.0%} |")
    sections.append(f"| **建议仓位** | {position_pct:.1f}% |")
    sections.append(f"| **看多/中性/看空** | {bullish_count}/{neutral_count}/{bearish_count} |")
    sections.append(f"| **参与Agent数** | {len(results)} |")
    sections.append("")

    # 核心逻辑
    if consensus.reasoning:
        sections.append(f"**核心逻辑**: {consensus.reasoning}")
        sections.append("")

    if consensus.key_findings:
        sections.append("**关键发现**:")
        for finding in consensus.key_findings[:5]:
            sections.append(f"- {finding}")
        sections.append("")

    sections.append("---")
    sections.append("")

    # ============ Agent共识表 ============
    sections.append("## Agent共识分析表")
    sections.append("")
    sections.append(f"信号分布: 🟢 看多 {bullish_count} | 🟡 中性 {neutral_count} | 🔴 看空 {bearish_count}")
    sections.append("")
    sections.append(_format_agent_table(results))
    sections.append("")
    sections.append("---")
    sections.append("")

    # ============ 主题分析区段 ============
    sections.append("## 分主题深度分析")
    sections.append("")

    for theme_name, theme_info in THEME_GROUPS.items():
        agent_ids = theme_info["agents"]
        sections.append(_format_theme_section(theme_name, agent_ids, results))

    sections.append("---")
    sections.append("")

    # ============ 财务概览 ============
    sections.append(_format_financial_overview(context))
    sections.append("---")
    sections.append("")

    # ============ 风险矩阵 ============
    sections.append(_format_risk_matrix(results))
    sections.append("---")
    sections.append("")

    # ============ 仓位建议 ============
    sections.append(_format_position_recommendation(consensus))

    # ============ 免责声明 ============
    sections.append("---")
    sections.append("")
    sections.append("## 免责声明")
    sections.append("")
    sections.append("本分析仅供教育和研究用途，不构成投资建议。所有投资都有风险，请在做出投资决策前咨询合格的财务顾问。")
    sections.append("")

    return "\n".join(sections)
