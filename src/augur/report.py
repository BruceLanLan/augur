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


# ============ Agent投资框架描述 ============

AGENT_PHILOSOPHY = {
    "buffett": "护城河+可预测盈利+FCF",
    "graham": "安全边际+净资产折价+低PE",
    "munger": "优质企业+合理价格+长期持有",
    "duan_yongping": "商业模式+管理层+确定性溢价",
    "li_lu": "价值+成长复合+中国市场洞察",
    "dan_bin": "时间玫瑰+消费龙头+长坡厚雪",
    "zhang_lei": "长期结构性价值+产业链研究+护城河演化",
    "cathie_wood": "颠覆性创新+指数型增长+5年愿景",
    "fisher": "成长股投资+管理层评估+行业领导力",
    "lynch": "PEG选股+生活观察+十倍股猎手",
    "aschenbrenner": "AI超级周期+算力增长+技术奇点投资",
    "thiel": "垄断型创新+从0到1+逆向思维",
    "dalio": "全天候配置+宏观周期+风险平价",
    "soros": "反身性理论+宏观趋势+市场情绪博弈",
    "marks": "周期意识+风险控制+逆向投资",
    "serenity": "波动率管理+尾部风险对冲+系统性风控",
    "arps": "技术形态+动量因子+量价分析",
    "dayu": "量化模型+资金流向+统计套利",
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


def _clean_reasoning_for_table(reasoning: str) -> str:
    """清理reasoning文本用于表格显示：移除Markdown标题、换行、多余空白、修复浮点数。"""
    import re
    # Remove markdown headers (## Title)
    text = re.sub(r'^#{1,4}\s+.*$', '', reasoning, flags=re.MULTILINE)
    # Remove bold markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Fix floating point display issues (e.g., 3.5999999999999996 -> 3.6)
    def _fix_float(m):
        try:
            return f"{float(m.group(0)):.1f}"
        except ValueError:
            return m.group(0)
    text = re.sub(r'\d+\.\d{4,}', _fix_float, text)
    # Collapse multiple newlines/spaces
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    # Remove leading dash/bullet items formatting
    text = re.sub(r'^\s*[-•]\s*', '', text)
    text = text.strip()
    # Truncate
    if len(text) > 80:
        text = text[:77] + "..."
    return text


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
        reasoning_short = _clean_reasoning_for_table(response.reasoning)
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

        # 投资框架描述
        philosophy = AGENT_PHILOSOPHY.get(agent_id, "")
        if philosophy:
            lines.append(f"- **投资框架**: {philosophy}")

        if response.reasoning:
            import re as _re
            reasoning_text = response.reasoning
            # Remove markdown headers from reasoning
            reasoning_text = _re.sub(r'^#{1,4}\s+.*$', '', reasoning_text, flags=_re.MULTILINE)
            # Fix floating point display
            def _fix_float_inline(m):
                try:
                    return f"{float(m.group(0)):.1f}"
                except ValueError:
                    return m.group(0)
            reasoning_text = _re.sub(r'\d+\.\d{4,}', _fix_float_inline, reasoning_text)
            reasoning_text = reasoning_text.strip()
            if len(reasoning_text) > 500:
                reasoning_text = reasoning_text[:497] + "..."
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


def _format_disagreement_section(results: Dict[str, AgentResponse]) -> str:
    """生成分歧焦点区段，展示多空分歧及原因。

    Args:
        results: 所有Agent的分析结果

    Returns:
        Markdown格式的分歧焦点区段
    """
    lines = []
    lines.append("## 分歧焦点")
    lines.append("")

    valid_results = {k: v for k, v in results.items() if v.signal != SignalType.ERROR}
    if not valid_results:
        lines.append("*暂无有效Agent结果，无法生成分歧分析*")
        lines.append("")
        return "\n".join(lines)

    bullish_agents = {k: v for k, v in valid_results.items() if v.signal == SignalType.BULLISH}
    bearish_agents = {k: v for k, v in valid_results.items() if v.signal == SignalType.BEARISH}
    neutral_agents = {k: v for k, v in valid_results.items() if v.signal == SignalType.NEUTRAL}

    if not bullish_agents or (not bearish_agents and not neutral_agents):
        lines.append("*当前分析结果高度一致，暂无显著分歧*")
        lines.append("")
        return "\n".join(lines)

    # 分歧概览
    lines.append("### 多空阵营对比")
    lines.append("")
    lines.append("| 阵营 | Agent数量 | 代表人物 | 核心逻辑 |")
    lines.append("|------|-----------|----------|----------|")

    # 看多阵营
    bull_names = sorted(bullish_agents.values(), key=lambda x: x.score, reverse=True)
    bull_rep = ", ".join(r.agent_name for r in bull_names[:3])
    bull_themes = set()
    for agent_id in list(bullish_agents.keys())[:3]:
        for theme, info in THEME_GROUPS.items():
            if agent_id in info["agents"]:
                bull_themes.add(theme)
                break
    bull_theme_str = "/".join(bull_themes) if bull_themes else "多维度"
    lines.append(f"| 🟢 看多 | {len(bullish_agents)} | {bull_rep} | {bull_theme_str}视角看好 |")

    # 看空阵营
    if bearish_agents:
        bear_names = sorted(bearish_agents.values(), key=lambda x: x.score)
        bear_rep = ", ".join(r.agent_name for r in bear_names[:3])
        bear_themes = set()
        for agent_id in list(bearish_agents.keys())[:3]:
            for theme, info in THEME_GROUPS.items():
                if agent_id in info["agents"]:
                    bear_themes.add(theme)
                    break
        bear_theme_str = "/".join(bear_themes) if bear_themes else "多维度"
        lines.append(f"| 🔴 看空 | {len(bearish_agents)} | {bear_rep} | {bear_theme_str}视角谨慎 |")

    # 中性阵营
    if neutral_agents:
        neut_names = sorted(neutral_agents.values(), key=lambda x: x.score, reverse=True)
        neut_rep = ", ".join(r.agent_name for r in neut_names[:3])
        lines.append(f"| 🟡 中性 | {len(neutral_agents)} | {neut_rep} | 观望等待更多信号 |")

    lines.append("")

    # 分歧原因分析
    lines.append("### 分歧原因")
    lines.append("")

    # Identify different investment schools in conflict
    value_bulls = [v for k, v in bullish_agents.items() if k in THEME_GROUPS.get("价值投资", {}).get("agents", [])]
    growth_bulls = [v for k, v in bullish_agents.items() if k in THEME_GROUPS.get("成长投资", {}).get("agents", [])]
    risk_bears = [v for k, v in bearish_agents.items() if k in THEME_GROUPS.get("风险与宏观", {}).get("agents", [])]
    risk_neutrals = [v for k, v in neutral_agents.items() if k in THEME_GROUPS.get("风险与宏观", {}).get("agents", [])]

    if value_bulls and (risk_bears or risk_neutrals):
        lines.append("- **价值派 vs 风控派**: 价值投资者认为当前估值具备安全边际，而风控派关注周期风险与尾部事件")

    if growth_bulls and bearish_agents:
        lines.append("- **成长派 vs 保守派**: 成长投资者看好未来增长空间与创新前景，保守派认为估值已充分反映预期")

    # Score spread analysis
    all_scores = [v.score for v in valid_results.values()]
    if all_scores:
        score_spread = max(all_scores) - min(all_scores)
        if score_spread >= 3:
            lines.append(f"- **评分分歧度**: 最高分 {max(all_scores):.1f} vs 最低分 {min(all_scores):.1f}，分差达 {score_spread:.1f} 分，反映投资理念根本性差异")
        elif score_spread >= 1.5:
            lines.append(f"- **评分分歧度**: 分差 {score_spread:.1f} 分，属于中度分歧，主要来自对估值合理性的不同判断")

    if not value_bulls and not growth_bulls and not risk_bears and not risk_neutrals:
        lines.append("- 各Agent基于不同投资框架得出了不同结论，体现了多角度分析的价值")

    lines.append("")
    return "\n".join(lines)


def _format_bull_bear_debate(results: Dict[str, AgentResponse]) -> str:
    """生成多空辩论区段，展示TOP 3看多和TOP 3看空/中性Agent的核心论点。

    Args:
        results: 所有Agent的分析结果

    Returns:
        Markdown格式的多空辩论区段
    """
    lines = []
    lines.append("## 多空辩论")
    lines.append("")

    valid_results = {k: v for k, v in results.items() if v.signal != SignalType.ERROR}
    if not valid_results:
        lines.append("*暂无有效Agent结果，无法生成辩论*")
        lines.append("")
        return "\n".join(lines)

    # Sort by score to get top bulls and bears
    sorted_by_score = sorted(valid_results.items(), key=lambda x: x[1].score, reverse=True)

    # Top 3 bullish (highest score)
    top_bulls = sorted_by_score[:3]
    # Top 3 bearish (lowest score)
    top_bears = sorted_by_score[-3:]
    # Reverse bears so lowest is first
    top_bears = list(reversed(top_bears))

    lines.append("### 🟢 多方论点 (最看好的3位大师)")
    lines.append("")

    for agent_id, response in top_bulls:
        philosophy = AGENT_PHILOSOPHY.get(agent_id, "")
        philosophy_str = f" [{philosophy}]" if philosophy else ""
        signal_str = _format_signal_emoji(response.signal.value)
        lines.append(f"**{response.agent_name}**{philosophy_str} {signal_str} {response.score:.1f}/10")

        reasoning_short = _clean_reasoning_for_table(response.reasoning)
        lines.append(f"- {reasoning_short}")

        if response.key_findings:
            for finding in response.key_findings[:2]:
                lines.append(f"- {finding}")
        lines.append("")

    lines.append("### 🔴 空方论点 (最谨慎的3位大师)")
    lines.append("")

    for agent_id, response in top_bears:
        philosophy = AGENT_PHILOSOPHY.get(agent_id, "")
        philosophy_str = f" [{philosophy}]" if philosophy else ""
        signal_str = _format_signal_emoji(response.signal.value)
        lines.append(f"**{response.agent_name}**{philosophy_str} {signal_str} {response.score:.1f}/10")

        reasoning_short = _clean_reasoning_for_table(response.reasoning)
        lines.append(f"- {reasoning_short}")

        if response.risks:
            for risk in response.risks[:2]:
                lines.append(f"- 风险: {risk}")
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
        # market_cap is in billions USD
        if context.market_cap >= 1000:
            cap_str = f"${context.market_cap / 1000:.2f}万亿"
        elif context.market_cap >= 1:
            cap_str = f"${context.market_cap:.1f}B"
        else:
            cap_str = f"${context.market_cap * 1000:.0f}M"
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
            lines.append(f"| ROE | {context.roe * 100:.1f}% |")
        if context.roa:
            lines.append(f"| ROA | {context.roa * 100:.1f}% |")
        if context.gross_margins:
            lines.append(f"| 毛利率 | {context.gross_margins * 100:.1f}% |")
        if context.operating_margins:
            lines.append(f"| 营业利润率 | {context.operating_margins * 100:.1f}% |")
        lines.append("")

    # 成长指标
    has_growth = any([context.revenue_growth, context.earnings_growth])
    if has_growth:
        lines.append("### 成长性")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        if context.revenue_growth:
            lines.append(f"| 营收增长率 | {context.revenue_growth * 100:.1f}% |")
        if context.earnings_growth:
            lines.append(f"| 盈利增长率 | {context.earnings_growth * 100:.1f}% |")
        lines.append("")

    # 财务健康
    has_health = any([context.debt_ratio, context.current_ratio, context.fcf])
    if has_health:
        lines.append("### 财务健康")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        if context.debt_ratio:
            lines.append(f"| 负债率 | {context.debt_ratio * 100:.1f}% |")
        if context.current_ratio:
            lines.append(f"| 流动比率 | {context.current_ratio:.2f} |")
        if context.fcf:
            # fcf is in billions USD
            if abs(context.fcf) >= 1000:
                fcf_str = f"${context.fcf / 1000:.2f}万亿"
            elif abs(context.fcf) >= 1:
                fcf_str = f"${context.fcf:.1f}B"
            else:
                fcf_str = f"${context.fcf * 1000:.0f}M"
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
    lines.append("> 以下为 **18位大师加权共识建议**，综合多维度投资框架得出的集体决策，非任何单一投资者观点。")
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

    # ============ 执行摘要（18位大师共识裁决） ============
    sections.append("## 18位大师共识裁决（执行摘要）")
    sections.append("")

    signal_str = _format_signal_chinese(consensus.signal.value)
    position_sizing = consensus.metadata.get("position_sizing", {})
    position_pct = position_sizing.get("position_pct", consensus.metadata.get("position_pct", 0))

    # 信号分布统计
    valid_results = {k: v for k, v in results.items() if v.signal != SignalType.ERROR}
    bullish_count = sum(1 for r in valid_results.values() if r.signal == SignalType.BULLISH)
    bearish_count = sum(1 for r in valid_results.values() if r.signal == SignalType.BEARISH)
    neutral_count = sum(1 for r in valid_results.values() if r.signal == SignalType.NEUTRAL)

    sections.append("### 投资委员会综合评分")
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

    # ============ 分歧焦点 ============
    sections.append(_format_disagreement_section(results))
    sections.append("---")
    sections.append("")

    # ============ 多空辩论 ============
    sections.append(_format_bull_bear_debate(results))
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
