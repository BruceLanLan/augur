# -*- coding: utf-8 -*-
"""
augur.report - 深度分析报告生成模块

将18位投资大师（多Agent）的分析结果融合为一份专业的、投行/研究机构级别的
中文Markdown深度分析报告。

设计原则：
  1. **多大师融合** —— 报告综合全部18位大师的独立视角，以"投资委员会"集体
     裁决的中性口吻呈现，绝不偏向任何单一大师。
  2. **专业深度** —— 模块化结构（执行摘要 / 评分总表 / 分流派深度分析 /
     多空辩论 / 分歧焦点 / 财务概览 / 共识与风险矩阵 / 仓位建议 / 免责声明）。
  3. **纯数据格式化** —— 仅基于已有的Agent评分数据与MarketContext，不调用任何
     外部API或LLM。
  4. **单位正确** —— roe/margins/growth/debt_ratio 等为小数（*100 显示为%），
     market_cap/fcf 以十亿美元为单位（自动换算为 $X.XXB / 万亿）。
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple

from augur.personas.base import AgentResponse, MarketContext, SignalType


# ============ Agent主题分组（四大投资流派） ============

THEME_GROUPS = {
    "价值投资": {
        "agents": ["buffett", "graham", "munger", "duan_yongping", "li_lu", "dan_bin", "zhang_lei"],
        "description": "价值投资视角，关注安全边际、内在价值、护城河与长期持有",
        "lens": "估值是否便宜、企业质地是否优秀、是否值得长期持有",
    },
    "成长投资": {
        "agents": ["cathie_wood", "fisher", "lynch", "aschenbrenner", "thiel"],
        "description": "成长投资视角，关注创新驱动、颠覆性技术、行业空间与高增长潜力",
        "lens": "增长的持续性、创新护城河、行业天花板与成长定价",
    },
    "风险与宏观": {
        "agents": ["dalio", "soros", "marks", "serenity"],
        "description": "宏观与风险管理视角，关注经济周期、风险溢价、市场情绪与尾部风险",
        "lens": "周期位置、风险收益是否对称、尾部与宏观冲击",
    },
    "技术与量化": {
        "agents": ["arps", "dayu"],
        "description": "技术分析与量化视角，关注价格行为、动量、资金流向与统计规律",
        "lens": "趋势与动量、量价结构、资金流与统计边际",
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


# ============ 基础格式化工具 ============

def _format_signal_chinese(signal_value: str) -> str:
    """将英文信号转换为中文标签（带emoji）。"""
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


def _fix_floats(text: str) -> str:
    """修复文本中的浮点数显示问题（3.5999999 -> 3.6）。"""
    def _repl(m):
        try:
            return f"{float(m.group(0)):.1f}"
        except ValueError:
            return m.group(0)
    return re.sub(r'\d+\.\d{4,}', _repl, text)


def _strip_markdown(text: str) -> str:
    """去除reasoning中的Markdown标题/加粗/列表符号，便于内联或表格展示。"""
    # 去除 Markdown 标题（## xxx）
    text = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)
    # 去除加粗标记
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # 修复浮点数
    text = _fix_floats(text)
    return text


def _clean_reasoning_for_table(reasoning: str, max_len: int = 80) -> str:
    """清理reasoning文本用于表格显示：移除Markdown标题、换行、多余空白、修复浮点数。"""
    text = _strip_markdown(reasoning or "")
    # 合并换行与多余空白
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    # 去除前导项目符号
    text = re.sub(r'^\s*[-•]\s*', '', text)
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len - 3] + "..."
    return text


def _clean_reasoning_inline(reasoning: str, max_len: int = 500) -> str:
    """清理reasoning用于内联段落展示（保留较长内容）。"""
    text = _strip_markdown(reasoning or "").strip()
    if len(text) > max_len:
        text = text[:max_len - 3] + "..."
    return text


# ============ 数据聚合工具（实现"18位大师融合"） ============

def _valid_results(results: Dict[str, AgentResponse]) -> Dict[str, AgentResponse]:
    """过滤掉ERROR信号的Agent。"""
    return {k: v for k, v in results.items() if v.signal != SignalType.ERROR}


def _signal_counts(results: Dict[str, AgentResponse]) -> Tuple[int, int, int, int]:
    """统计信号分布，返回 (看多, 中性, 看空, 有效总数)。"""
    valid = _valid_results(results)
    bull = sum(1 for r in valid.values() if r.signal == SignalType.BULLISH)
    bear = sum(1 for r in valid.values() if r.signal == SignalType.BEARISH)
    neut = sum(1 for r in valid.values() if r.signal == SignalType.NEUTRAL)
    return bull, neut, bear, len(valid)


def _score_to_grade(score: float) -> Tuple[str, str]:
    """将综合评分映射为评级字母与中文标签。"""
    if score >= 8.5:
        return "A+", "卓越机会"
    if score >= 7.5:
        return "A", "优秀标的"
    if score >= 6.5:
        return "B+", "良好（偏积极）"
    if score >= 5.5:
        return "B", "中性（可观察）"
    if score >= 4.5:
        return "C", "中性偏谨慎"
    if score >= 3.0:
        return "D", "谨慎回避"
    return "E", "高风险回避"


def _consensus_strength(results: Dict[str, AgentResponse]) -> Tuple[str, float]:
    """评估共识强度：返回 (描述, 多数派占比)。"""
    bull, neut, bear, total = _signal_counts(results)
    if total == 0:
        return "无有效数据", 0.0
    majority = max(bull, neut, bear)
    pct = majority / total
    if pct >= 0.7:
        return "高度一致", pct
    if pct >= 0.5:
        return "中度共识", pct
    return "显著分歧", pct


def _score_stats(results: Dict[str, AgentResponse]) -> Tuple[float, float, float, float]:
    """返回有效评分的 (最低, 最高, 均值, 标准差)。"""
    scores = [r.score for r in _valid_results(results).values()]
    if not scores:
        return 0.0, 0.0, 0.0, 0.0
    mn, mx = min(scores), max(scores)
    mean = sum(scores) / len(scores)
    var = sum((s - mean) ** 2 for s in scores) / len(scores)
    return mn, mx, mean, var ** 0.5


def _aggregate_items(results: Dict[str, AgentResponse], attr: str) -> List[Tuple[str, List[str]]]:
    """聚合所有大师提到的风险/发现，按提及频次降序返回 [(item, [agent_names])]。"""
    bag: Dict[str, List[str]] = {}
    for response in _valid_results(results).values():
        for item in getattr(response, attr, []) or []:
            norm = (item or "").strip()
            if not norm:
                continue
            bag.setdefault(norm, []).append(response.agent_name)
    return sorted(bag.items(), key=lambda x: len(x[1]), reverse=True)


def _agent_theme(agent_id: str) -> str:
    """返回某个Agent所属的投资流派名称。"""
    for theme, info in THEME_GROUPS.items():
        if agent_id in info["agents"]:
            return theme
    return "其他"


def _dominant_themes(agent_ids: List[str]) -> List[str]:
    """返回一组Agent中出现的流派（去重，按出现顺序）。"""
    seen: List[str] = []
    for aid in agent_ids:
        theme = _agent_theme(aid)
        if theme not in seen:
            seen.append(theme)
    return seen


# ============ 报告区段：执行摘要 ============

def _format_executive_summary(
    ticker: str,
    context: MarketContext,
    results: Dict[str, AgentResponse],
    consensus: AgentResponse,
) -> str:
    """生成执行摘要（投资委员会综合裁决）。

    以中性的"投资委员会"口吻呈现18位大师的集体裁决，融合全部视角，不偏向任一大师。
    """
    lines: List[str] = []
    lines.append("## 投资委员会综合裁决（执行摘要）")
    lines.append("")

    bull, neut, bear, total = _signal_counts(results)
    grade, grade_label = _score_to_grade(consensus.score)
    strength_desc, strength_pct = _consensus_strength(results)
    signal_str = _format_signal_chinese(consensus.signal.value)

    position_sizing = consensus.metadata.get("position_sizing", {}) or {}
    position_pct = position_sizing.get("position_pct", consensus.metadata.get("position_pct", 0)) or 0

    # —— 综合评级卡 ——
    lines.append("### 综合评级卡")
    lines.append("")
    lines.append("| 维度 | 委员会裁决 |")
    lines.append("|------|------------|")
    lines.append(f"| **综合信号** | {signal_str} |")
    lines.append(f"| **综合评分** | {consensus.score:.1f}/10 （评级 {grade} · {grade_label}） |")
    lines.append(f"| **置信度** | {consensus.confidence:.0%} |")
    lines.append(f"| **共识强度** | {strength_desc}（{strength_pct:.0%} 大师持多数派观点） |")
    lines.append(f"| **多空分布** | 🟢看多 {bull} · 🟡中性 {neut} · 🔴看空 {bear}（共 {total} 位有效裁决） |")
    lines.append(f"| **建议仓位** | {position_pct:.1f}%（18位大师加权 · 半Kelly） |")
    if context.price:
        lines.append(f"| **当前价格** | ${context.price:.2f} |")
    lines.append(f"| **参与大师** | {len(results)} 位（覆盖价值 / 成长 / 宏观风险 / 技术量化四大流派） |")
    lines.append("")

    # —— 信号分布条 ——
    if total > 0:
        bar = "🟢" * bull + "🟡" * neut + "🔴" * bear
        lines.append(f"**信号分布**：{bar}")
        lines.append("")

    # —— 一句话裁决（融合多空两端 + 关键分歧） ——
    lines.append("### 一句话裁决")
    lines.append("")
    lines.append(_build_verdict_sentence(ticker, results, consensus, grade, grade_label, strength_desc))
    lines.append("")

    # —— 委员会综合论述（中性融合口吻） ——
    if consensus.reasoning:
        lines.append("### 委员会综合论述")
        lines.append("")
        lines.append(_clean_reasoning_inline(consensus.reasoning, max_len=600))
        lines.append("")

    # —— 集体共识要点 ——
    findings = _aggregate_items(results, "key_findings")
    if findings:
        lines.append("**集体共识要点**（按提及大师数排序）：")
        for item, agents in findings[:5]:
            tag = f"（{len(agents)}位提及）" if len(agents) > 1 else ""
            lines.append(f"- {item} {tag}".rstrip())
        lines.append("")
    elif consensus.key_findings:
        lines.append("**关键发现**：")
        for finding in consensus.key_findings[:5]:
            lines.append(f"- {finding}")
        lines.append("")

    return "\n".join(lines)


def _build_verdict_sentence(
    ticker: str,
    results: Dict[str, AgentResponse],
    consensus: AgentResponse,
    grade: str,
    grade_label: str,
    strength_desc: str,
) -> str:
    """构造融合多空两端的一句话裁决。"""
    bull, neut, bear, total = _signal_counts(results)
    valid = _valid_results(results)

    # 看多阵营主导流派
    bull_ids = [k for k, v in valid.items() if v.signal == SignalType.BULLISH]
    bear_ids = [k for k, v in valid.items() if v.signal == SignalType.BEARISH]
    bull_themes = _dominant_themes(bull_ids)
    bear_themes = _dominant_themes(bear_ids)

    # 最高频风险
    risks = _aggregate_items(results, "risks")
    top_risk = risks[0][0] if risks else ""

    parts: List[str] = []
    parts.append(
        f"经18位大师投资委员会综合评议，**{ticker}** 获 **{_format_signal_chinese(consensus.signal.value)}** "
        f"裁决，综合评分 **{consensus.score:.1f}/10（{grade}级·{grade_label}）**，委员会内部呈"
        f"**{strength_desc}**。"
    )

    if bull and (bear or neut):
        bull_theme_str = "、".join(bull_themes[:2]) if bull_themes else "多个流派"
        if bear:
            bear_theme_str = "、".join(bear_themes[:2]) if bear_themes else "风险派"
            parts.append(
                f"{bull} 位大师（以{bull_theme_str}为主）看多，{bear} 位（以{bear_theme_str}为主）"
                f"持谨慎态度，{neut} 位中性观望。"
            )
        else:
            parts.append(f"{bull} 位大师（以{bull_theme_str}为主）看多，其余 {neut} 位保持中性。")
    elif bull and not bear and not neut:
        parts.append(f"全部 {bull} 位有效裁决一致看多，分歧极小。")
    elif total > 0:
        parts.append(f"看多 {bull} / 中性 {neut} / 看空 {bear}，结论需结合下文分流派逻辑研判。")

    if top_risk:
        parts.append(f"委员会最集中的担忧是「{_clean_reasoning_for_table(top_risk, 40)}」。")

    return "".join(parts)


# ============ 报告区段：18位大师评分总表 ============

def _format_agent_table(results: Dict[str, AgentResponse]) -> str:
    """生成18位大师评分总表（Markdown格式），含流派与投资框架。"""
    lines: List[str] = []
    lines.append("| 大师 | 流派 | 信号 | 评分 | 置信度 | 投资框架 | 核心一句话 |")
    lines.append("|------|------|------|------|--------|----------|------------|")

    # 按评分降序，ERROR 排最后
    def _sort_key(item):
        return (item[1].signal == SignalType.ERROR, -item[1].score)

    for agent_id, response in sorted(results.items(), key=_sort_key):
        theme = _agent_theme(agent_id)
        signal_str = _format_signal_chinese(response.signal.value)
        score_str = f"{response.score:.1f}/10"
        confidence_str = f"{response.confidence:.0%}"
        philosophy = AGENT_PHILOSOPHY.get(agent_id, "—")
        reasoning_short = _clean_reasoning_for_table(response.reasoning, 60)
        lines.append(
            f"| {response.agent_name} | {theme} | {signal_str} | {score_str} | "
            f"{confidence_str} | {philosophy} | {reasoning_short} |"
        )

    return "\n".join(lines)


# ============ 报告区段：分流派深度分析 ============

def _format_theme_section(theme_name: str, agent_ids: List[str], results: Dict[str, AgentResponse]) -> str:
    """生成主题（流派）分组深度分析区段。"""
    lines: List[str] = []
    theme_info = THEME_GROUPS.get(theme_name, {})
    description = theme_info.get("description", "")
    lens = theme_info.get("lens", "")

    lines.append(f"### {theme_name}")
    if description:
        lines.append(f"> {description}")
    lines.append("")

    theme_results = {aid: results[aid] for aid in agent_ids if aid in results}

    if not theme_results:
        lines.append("*该流派下暂无大师分析结果*")
        lines.append("")
        return "\n".join(lines)

    valid_theme = {k: v for k, v in theme_results.items() if v.signal != SignalType.ERROR}
    bullish_count = sum(1 for r in valid_theme.values() if r.signal == SignalType.BULLISH)
    bearish_count = sum(1 for r in valid_theme.values() if r.signal == SignalType.BEARISH)
    neutral_count = sum(1 for r in valid_theme.values() if r.signal == SignalType.NEUTRAL)
    avg_score = sum(r.score for r in valid_theme.values()) / len(valid_theme) if valid_theme else 0

    if lens:
        lines.append(f"**关注焦点**：{lens}")
        lines.append("")
    lines.append(
        f"**流派共识**：🟢看多 {bullish_count} / 🟡中性 {neutral_count} / 🔴看空 {bearish_count}"
        f" | 平均评分 {avg_score:.1f}/10"
    )

    # 流派裁决（融合该派内部观点）
    verdict = _theme_verdict(bullish_count, neutral_count, bearish_count, avg_score)
    lines.append(f"**流派裁决**：{verdict}")
    lines.append("")

    for agent_id, response in theme_results.items():
        if response.signal == SignalType.ERROR:
            lines.append(f"**{response.agent_name}**：⚠️ 分析失败 — {_clean_reasoning_for_table(response.reasoning, 100)}")
            lines.append("")
            continue

        signal_str = _format_signal_chinese(response.signal.value)
        lines.append(f"**{response.agent_name}** ({signal_str}, {response.score:.1f}/10, 置信度 {response.confidence:.0%})")
        lines.append("")

        philosophy = AGENT_PHILOSOPHY.get(agent_id, "")
        if philosophy:
            lines.append(f"- **投资框架**：{philosophy}")

        if response.reasoning:
            lines.append(f"- **核心逻辑**：{_clean_reasoning_inline(response.reasoning, 500)}")

        if response.key_findings:
            lines.append("- **关键发现**：")
            for finding in response.key_findings[:5]:
                lines.append(f"  - {finding}")

        if response.risks:
            lines.append("- **风险提示**：")
            for risk in response.risks[:3]:
                lines.append(f"  - {risk}")

        lines.append("")

    return "\n".join(lines)


def _theme_verdict(bull: int, neut: int, bear: int, avg_score: float) -> str:
    """根据流派内部信号分布生成一句裁决。"""
    total = bull + neut + bear
    if total == 0:
        return "本流派暂无有效裁决。"
    if bull and not bear:
        if neut:
            return f"本流派整体偏积极，但仍有 {neut} 位保持中性，分歧在于估值与时机。"
        return "本流派内部高度一致看多。"
    if bear and not bull:
        return "本流派整体偏谨慎，警示风险大于机会。"
    if bull and bear:
        return f"本流派内部出现明显对立（{bull} 看多 vs {bear} 看空），是全报告分歧的重要来源。"
    return "本流派整体中性，倾向观望等待更明确信号。"


# ============ 报告区段：多空辩论 ============

def _format_bull_bear_debate(results: Dict[str, AgentResponse]) -> str:
    """生成多空辩论区段：TOP3看多 vs TOP3看空/最谨慎，对比核心论点。"""
    lines: List[str] = []
    lines.append("## 多空辩论")
    lines.append("")

    valid_results = _valid_results(results)
    if not valid_results:
        lines.append("*暂无有效大师结果，无法生成辩论*")
        lines.append("")
        return "\n".join(lines)

    sorted_by_score = sorted(valid_results.items(), key=lambda x: x[1].score, reverse=True)
    top_bulls = sorted_by_score[:3]

    bearish_agents = [(k, v) for k, v in valid_results.items() if v.signal == SignalType.BEARISH]
    bearish_agents.sort(key=lambda x: x[1].score)
    neutral_agents = [(k, v) for k, v in valid_results.items() if v.signal == SignalType.NEUTRAL]
    neutral_agents.sort(key=lambda x: x[1].score)

    top_bears: List[Tuple[str, AgentResponse]] = []
    top_bears.extend(bearish_agents[:3])
    if len(top_bears) < 3:
        top_bears.extend(neutral_agents[: 3 - len(top_bears)])
    if len(top_bears) < 3:
        used_ids = {k for k, _ in top_bears}
        remaining = [(k, v) for k, v in sorted_by_score if k not in used_ids]
        remaining.reverse()
        for item in remaining:
            if len(top_bears) >= 3:
                break
            top_bears.append(item)

    has_actual_bearish = any(v.signal == SignalType.BEARISH for _, v in top_bears)

    lines.append("### 🟢 多方论点（最看好的3位大师）")
    lines.append("")
    for agent_id, response in top_bulls:
        lines.extend(_debate_block(agent_id, response, side="bull"))

    if has_actual_bearish:
        lines.append("### 🔴 空方论点（最谨慎的3位大师）")
    else:
        lines.append("### 🟡 最谨慎方（评分最低的3位大师）")
    lines.append("")
    for agent_id, response in top_bears:
        lines.extend(_debate_block(agent_id, response, side="bear"))

    # 辩论焦点小结
    if top_bulls and top_bears:
        bull_lead = top_bulls[0][1]
        bear_lead = top_bears[0][1]
        spread = bull_lead.score - bear_lead.score
        lines.append("### 辩论焦点")
        lines.append("")
        lines.append(
            f"多方旗手 **{bull_lead.agent_name}**（{bull_lead.score:.1f}/10）与"
            f"谨慎方代表 **{bear_lead.agent_name}**（{bear_lead.score:.1f}/10）评分相差 "
            f"**{spread:.1f}** 分，分歧本质是「成长/质地溢价」与「估值/周期风险」之间的取舍。"
        )
        lines.append("")

    return "\n".join(lines)


def _debate_block(agent_id: str, response: AgentResponse, side: str) -> List[str]:
    """生成单个大师在辩论中的论点块。"""
    lines: List[str] = []
    philosophy = AGENT_PHILOSOPHY.get(agent_id, "")
    philosophy_str = f" [{philosophy}]" if philosophy else ""
    signal_str = _format_signal_emoji(response.signal.value)
    lines.append(f"**{response.agent_name}**{philosophy_str} {signal_str} {response.score:.1f}/10")
    lines.append(f"- {_clean_reasoning_for_table(response.reasoning, 120)}")
    if side == "bull":
        for finding in (response.key_findings or [])[:2]:
            lines.append(f"- 论据：{finding}")
    else:
        for risk in (response.risks or [])[:2]:
            lines.append(f"- 风险：{risk}")
    lines.append("")
    return lines


# ============ 报告区段：分歧焦点 ============

def _format_disagreement_section(results: Dict[str, AgentResponse]) -> str:
    """生成分歧焦点区段，展示多空分歧及原因（报告最有价值的部分）。"""
    lines: List[str] = []
    lines.append("## 分歧焦点")
    lines.append("")

    valid_results = _valid_results(results)
    if not valid_results:
        lines.append("*暂无有效大师结果，无法生成分歧分析*")
        lines.append("")
        return "\n".join(lines)

    bullish_agents = {k: v for k, v in valid_results.items() if v.signal == SignalType.BULLISH}
    bearish_agents = {k: v for k, v in valid_results.items() if v.signal == SignalType.BEARISH}
    neutral_agents = {k: v for k, v in valid_results.items() if v.signal == SignalType.NEUTRAL}

    if not bullish_agents or (not bearish_agents and not neutral_agents):
        lines.append("*当前分析结果高度一致，暂无显著分歧*")
        lines.append("")
        return "\n".join(lines)

    # —— 多空阵营对比 ——
    lines.append("### 多空阵营对比")
    lines.append("")
    lines.append("| 阵营 | 大师数量 | 代表人物 | 主导流派/态度 |")
    lines.append("|------|----------|----------|----------------|")

    bull_names = sorted(bullish_agents.values(), key=lambda x: x.score, reverse=True)
    bull_rep = ", ".join(r.agent_name for r in bull_names[:3])
    bull_theme_str = "/".join(_dominant_themes(list(bullish_agents.keys())[:3])) or "多维度"
    lines.append(f"| 🟢 看多 | {len(bullish_agents)} | {bull_rep} | {bull_theme_str}视角看好 |")

    if bearish_agents:
        bear_names = sorted(bearish_agents.values(), key=lambda x: x.score)
        bear_rep = ", ".join(r.agent_name for r in bear_names[:3])
        bear_theme_str = "/".join(_dominant_themes(list(bearish_agents.keys())[:3])) or "多维度"
        lines.append(f"| 🔴 看空 | {len(bearish_agents)} | {bear_rep} | {bear_theme_str}视角谨慎 |")

    if neutral_agents:
        neut_names = sorted(neutral_agents.values(), key=lambda x: x.score, reverse=True)
        neut_rep = ", ".join(r.agent_name for r in neut_names[:3])
        lines.append(f"| 🟡 中性 | {len(neutral_agents)} | {neut_rep} | 观望等待更多信号 |")

    lines.append("")

    # —— 分歧原因 ——
    lines.append("### 分歧原因")
    lines.append("")

    value_bulls = [v for k, v in bullish_agents.items() if k in THEME_GROUPS["价值投资"]["agents"]]
    growth_bulls = [v for k, v in bullish_agents.items() if k in THEME_GROUPS["成长投资"]["agents"]]
    risk_bears = [v for k, v in bearish_agents.items() if k in THEME_GROUPS["风险与宏观"]["agents"]]

    if len(value_bulls) >= 2 and len(risk_bears) >= 1:
        lines.append("- **价值派 vs 风控派**：价值投资者认为当前估值具备安全边际，而风控派关注周期位置与尾部事件")
    if len(growth_bulls) >= 2 and len(bearish_agents) >= 1:
        lines.append("- **成长派 vs 保守派**：成长投资者看好未来增长空间与创新前景，保守派认为估值已充分反映预期")

    mn, mx, mean, std = _score_stats(results)
    score_spread = mx - mn
    if score_spread >= 3:
        lines.append(
            f"- **评分分歧度（极大）**：最高分 {mx:.1f} vs 最低分 {mn:.1f}，分差达 {score_spread:.1f} 分"
            f"（标准差 {std:.1f}），反映投资理念的根本性差异"
        )
    elif score_spread >= 1.5:
        lines.append(
            f"- **评分分歧度（中度）**：分差 {score_spread:.1f} 分（标准差 {std:.1f}），"
            f"主要来自对估值合理性的不同判断"
        )
    else:
        lines.append(f"- **评分分歧度（较小）**：分差仅 {score_spread:.1f} 分，各派对内在价值的判断较为接近")

    if not value_bulls and not growth_bulls and not risk_bears:
        lines.append("- 各大师基于不同投资框架得出了不同结论，体现了多角度分析的价值")

    lines.append("")

    # —— 最大分歧维度 ——
    lines.append("### 最大分歧维度")
    lines.append("")
    lines.append(_biggest_contention(bullish_agents, bearish_agents, neutral_agents, score_spread))
    lines.append("")

    return "\n".join(lines)


def _biggest_contention(bullish, bearish, neutral, score_spread: float) -> str:
    """识别并描述最大的分歧维度。"""
    if bullish and bearish:
        return (
            "**估值合理性**是当前最大分歧点：乐观阵营认为企业质地/成长足以消化当前估值，"
            "谨慎阵营则认为价格已透支预期、安全边际不足。这一分歧决定了仓位是否应当现在建立。"
        )
    if bullish and neutral and not bearish:
        return (
            "**入场时机**是当前最大分歧点：看多方主张当下即可配置，中性方倾向等待更优价格或更明确的"
            "基本面催化，二者对方向判断一致、仅在时机上存在差异。"
        )
    if score_spread >= 3:
        return "**投资框架差异**导致评分高度离散，不同流派对同一标的给出了截然不同的定价结论。"
    return "各流派结论较为接近，分歧主要体现在仓位力度与持有周期等执行层面。"


# ============ 报告区段：财务概览 ============

def _format_market_cap(value: float) -> str:
    """格式化市值/现金流（输入单位：十亿美元）。"""
    if abs(value) >= 1000:
        return f"${value / 1000:.2f}万亿"
    if abs(value) >= 1:
        return f"${value:.2f}B"
    return f"${value * 1000:.0f}M"


def _valuation_comment(pe: float) -> str:
    """根据PE给出估值定性评估。"""
    if pe <= 0:
        return ""
    if pe > 40:
        return "估值偏高（成长预期已充分定价）"
    if pe >= 20:
        return "估值合理偏高"
    if pe >= 12:
        return "估值处于合理区间"
    return "估值偏低（可能存在价值或价值陷阱）"


def _format_financial_overview(context: MarketContext) -> str:
    """生成财务概览区段（单位正确：比率小数*100显示为%，市值十亿换算）。"""
    lines: List[str] = []
    lines.append("## 财务概览")
    lines.append("")

    # —— 估值指标 ——
    lines.append("### 估值指标")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    if context.price:
        lines.append(f"| 当前价格 | ${context.price:.2f} |")
    if context.market_cap:
        lines.append(f"| 市值 | {_format_market_cap(context.market_cap)} |")
    if context.pe:
        comment = _valuation_comment(context.pe)
        comment_str = f"（{comment}）" if comment else ""
        lines.append(f"| 市盈率 (PE) | {context.pe:.1f}x{comment_str} |")
    if context.pb:
        lines.append(f"| 市净率 (PB) | {context.pb:.2f}x |")
    if context.ps:
        lines.append(f"| 市销率 (PS) | {context.ps:.2f}x |")
    lines.append("")

    # —— 盈利能力 ——
    if any([context.roe, context.roa, context.gross_margins, context.operating_margins]):
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

    # —— 成长性 ——
    if any([context.revenue_growth, context.earnings_growth]):
        lines.append("### 成长性")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        if context.revenue_growth:
            lines.append(f"| 营收增长率 | {context.revenue_growth * 100:.1f}% |")
        if context.earnings_growth:
            lines.append(f"| 盈利增长率 | {context.earnings_growth * 100:.1f}% |")
        lines.append("")

    # —— 财务健康 ——
    if any([context.debt_ratio, context.current_ratio, context.fcf]):
        lines.append("### 财务健康")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        if context.debt_ratio:
            lines.append(f"| 负债率 | {context.debt_ratio * 100:.1f}% |")
        if context.current_ratio:
            lines.append(f"| 流动比率 | {context.current_ratio:.2f} |")
        if context.fcf:
            lines.append(f"| 自由现金流 | {_format_market_cap(context.fcf)} |")
        lines.append("")

    # —— 行业定位 ——
    if context.sector or context.industry:
        lines.append("### 行业定位")
        lines.append("")
        if context.sector:
            lines.append(f"- **所属板块**：{context.sector}")
        if context.industry:
            lines.append(f"- **细分行业**：{context.industry}")
        lines.append("")

    return "\n".join(lines)


# ============ 报告区段：共识与风险矩阵 ============

def _format_risk_matrix(results: Dict[str, AgentResponse]) -> str:
    """生成共识与风险矩阵区段：汇总所有大师的共识优势与风险，按提及频次排序。"""
    lines: List[str] = []
    lines.append("## 共识与风险矩阵")
    lines.append("")

    # —— 共识优势（key_findings 按频次） ——
    findings = _aggregate_items(results, "key_findings")
    if findings:
        lines.append("### 共识优势（多位大师认同的亮点）")
        lines.append("")
        lines.append("| 共识要点 | 提及次数 | 提出者 |")
        lines.append("|----------|----------|--------|")
        for item, agents in findings[:10]:
            item_short = item[:80] + "..." if len(item) > 80 else item
            agents_str = ", ".join(agents[:3])
            if len(agents) > 3:
                agents_str += f" 等{len(agents)}位"
            lines.append(f"| {item_short} | {len(agents)} | {agents_str} |")
        lines.append("")

    # —— 风险矩阵（risks 按频次） ——
    lines.append("### 风险矩阵（按提及频次排序）")
    lines.append("")
    risks = _aggregate_items(results, "risks")
    if not risks:
        lines.append("*暂无显著风险提示*")
        lines.append("")
        return "\n".join(lines)

    lines.append("| 风险因素 | 提及次数 | 提出者 |")
    lines.append("|----------|----------|--------|")
    for risk, agents in risks[:15]:
        risk_short = risk[:80] + "..." if len(risk) > 80 else risk
        agents_str = ", ".join(agents[:3])
        if len(agents) > 3:
            agents_str += f" 等{len(agents)}位"
        lines.append(f"| {risk_short} | {len(agents)} | {agents_str} |")

    lines.append("")
    return "\n".join(lines)


# ============ 报告区段：仓位建议 ============

def _format_position_recommendation(consensus: AgentResponse) -> str:
    """生成仓位建议区段（明确标注为18位大师加权共识 + Kelly说明）。"""
    lines: List[str] = []
    lines.append("## 仓位建议")
    lines.append("")
    lines.append("> 以下为 **18位大师加权共识建议**，综合多维度投资框架得出的集体决策，非任何单一投资者观点。")
    lines.append("")

    position_sizing = consensus.metadata.get("position_sizing", {}) or {}
    position_pct = position_sizing.get("position_pct", consensus.metadata.get("position_pct", 0)) or 0
    signal_str = _format_signal_chinese(consensus.signal.value)
    grade, grade_label = _score_to_grade(consensus.score)

    lines.append("| 项目 | 内容 |")
    lines.append("|------|------|")
    lines.append(f"| **综合信号** | {signal_str} |")
    lines.append(f"| **综合评分** | {consensus.score:.1f}/10（{grade}级·{grade_label}） |")
    lines.append(f"| **置信度** | {consensus.confidence:.0%} |")
    lines.append(f"| **建议仓位** | {position_pct:.1f}% |")
    if position_sizing.get("rationale"):
        lines.append(f"| **仓位逻辑** | {position_sizing['rationale']} |")
    lines.append("")

    # —— Kelly 计算说明 ——
    lines.append("### Kelly仓位计算说明")
    lines.append("")
    lines.append(
        "仓位基于 **半Kelly公式** 由18位大师的加权评分与置信度共同推导："
        "评分越高、置信度越高则建议仓位越大，并对全Kelly做减半处理以控制回撤。"
    )
    lines.append("")
    if consensus.signal == SignalType.BULLISH:
        lines.append(f"- 看多信号：建议配置 **{position_pct:.1f}%** 仓位")
        lines.append(f"- 评分 {consensus.score:.1f}/10 + 置信度 {consensus.confidence:.0%} → 风险收益可控")
        lines.append("- 建议分批建仓（如 4:3:3），并设置基于基本面恶化的减仓信号")
    elif consensus.signal == SignalType.BEARISH:
        lines.append("- 看空信号：建议 **不建仓** 或 **减仓**")
        lines.append("- 等待更明确的入场信号与安全边际")
    else:
        lines.append(f"- 中性信号：建议 **观望** 或 **轻仓**（{position_pct:.1f}%）")
        lines.append("- 等待方向明确（估值回落或基本面催化）后再加仓")

    lines.append("")
    return "\n".join(lines)


# ============ 主入口 ============

def generate_report(
    ticker: str,
    context: MarketContext,
    results: Dict[str, AgentResponse],
    consensus: AgentResponse,
) -> str:
    """生成中文Markdown深度分析报告（融合18位投资大师视角的专业研报）。

    Args:
        ticker: 股票代码
        context: 市场上下文数据
        results: 所有Agent的分析结果 Dict[agent_id, AgentResponse]
        consensus: 共识分析结果

    Returns:
        完整的Markdown格式深度分析报告字符串
    """
    sections: List[str] = []

    # ============ 标题与元数据 ============
    sections.append(f"# {ticker} 深度分析报告")
    sections.append("")
    sections.append(f"> **分析日期**：{datetime.now().strftime('%Y年%m月%d日')}")
    sections.append("> **分析方法**：18位投资大师共识分析框架（多流派融合的投资委员会决策系统）")
    sections.append("> **数据来源**：公开市场数据")
    sections.append("")
    sections.append("---")
    sections.append("")

    # ============ 1. 执行摘要（投资委员会综合裁决） ============
    sections.append(_format_executive_summary(ticker, context, results, consensus))
    sections.append("---")
    sections.append("")

    # ============ 2. 18位大师评分总表 ============
    bull, neut, bear, _ = _signal_counts(results)
    sections.append("## 18位大师评分总表")
    sections.append("")
    sections.append(f"信号分布：🟢 看多 {bull} | 🟡 中性 {neut} | 🔴 看空 {bear}")
    sections.append("")
    sections.append(_format_agent_table(results))
    sections.append("")
    sections.append("---")
    sections.append("")

    # ============ 3. 分流派深度分析 ============
    sections.append("## 分主题深度分析")
    sections.append("")
    sections.append("> 下文按价值派 / 成长派 / 宏观风险派 / 技术量化派四大流派，"
                    "分别呈现各派大师的独立逻辑与投资框架。")
    sections.append("")
    for theme_name, theme_info in THEME_GROUPS.items():
        sections.append(_format_theme_section(theme_name, theme_info["agents"], results))
    sections.append("---")
    sections.append("")

    # ============ 4. 多空辩论 ============
    sections.append(_format_bull_bear_debate(results))
    sections.append("---")
    sections.append("")

    # ============ 5. 分歧焦点 ============
    sections.append(_format_disagreement_section(results))
    sections.append("---")
    sections.append("")

    # ============ 6. 财务概览 ============
    sections.append(_format_financial_overview(context))
    sections.append("---")
    sections.append("")

    # ============ 7. 共识与风险矩阵 ============
    sections.append(_format_risk_matrix(results))
    sections.append("---")
    sections.append("")

    # ============ 8. 仓位建议 ============
    sections.append(_format_position_recommendation(consensus))

    # ============ 9. 免责声明 ============
    sections.append("---")
    sections.append("")
    sections.append("## 免责声明")
    sections.append("")
    sections.append(
        "本报告由18位投资大师人格化分析框架自动生成，所述各位大师视角均为受其公开投资理念"
        "启发的分析框架，**不代表任何真实人物对本标的的真实观点**。本分析仅供教育与研究用途，"
        "不构成投资建议。所有投资均有风险，请在做出投资决策前咨询合格的财务顾问。"
    )
    sections.append("")

    return "\n".join(sections)
