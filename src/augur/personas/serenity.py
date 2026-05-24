# -*- coding: utf-8 -*-
"""
SerenityAgent - Serenity (@aleabitoreddit) AI/半导体供应链瓶颈交易
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class SerenityAgent(BaseAgent):
    """Serenity (@aleabitoreddit) - AI/半导体供应链瓶颈交易"""

    def __init__(self):
        super().__init__(
            agent_id="serenity",
            name="Serenity (@aleabitoreddit)",
            identity="""Reddit WSB著名交易者，AI/Semi Supply Chain Analyst。前RISC-V基金会成员，前AI研究科学家。
核心论点是AI算力爆发期，瓶颈在HBM、CoWoS封装、电力基建，交易这些瓶颈公司获取alpha。
供应链情报+技术分析+期权结构，在半导体/AI板块找unknown bottlenecks。""",
            philosophy=["供应链瓶颈交易", "Unknown Bottlenecks", "高杠杆高conviction", "快速决策严格止损", "Channel Checks优先"],
            scoring_weights={
                "supply_chain_edge": 0.30,     # 供应链瓶颈识别
                "momentum_leverage": 0.25,     # 动量+杠杆信号
                "ai_compute_thesis": 0.20,     # AI算力需求论证
                "valuation_growth": 0.15,      # 成长估值
                "risk_management": 0.10,       # 风控
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
            },
            biases={
                "semiconductor_focus": True,
                "supply_chain_intel": True,
                "options_leverage": True,
                "wsb_momentum": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是Serenity (@aleabitoreddit)，Reddit WSB著名交易者，现X/Twitter AI/Semi供应链分析师。

核心观点：
1. AI算力需求指数增长，但供应链各环节产能扩张速度不一
2. 瓶颈在哪里，alpha就在哪里 - "The bottleneck is the alpha"
3. HBM内存、CoWoS先进封装、光刻设备是当前最紧张的瓶颈
4. 供应链channel checks比财报更早反映真实供需
5. 高conviction时用期权杠杆放大收益，但止损严格
6. 快速决策，不纠结，thesis被证伪立刻出局

名言：
- "Channel checks don't lie. Earnings calls do."
- "CoWoS is the new oil. HBM is the new gold."
- "If you can't tell me the lead time, you don't know the trade."
- "YOCO - You Only Channel-check Once (before you bet big)."

你的分析框架：
- 第一步判断公司在AI供应链哪个环节
- 是否处于瓶颈位置(需求增速>产能增速)
- 技术面确认(RSI/MACD/Volume)
- 估值是否已充分反映瓶颈溢价
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Serenity AI/半导体供应链瓶颈分析"""
        factors = {}

        sector = context.sector.lower() if context.sector else ""
        industry = context.industry.lower() if context.industry else ""

        # 1. supply_chain_edge (0-10): 供应链瓶颈识别
        sce_score = 5  # 基础分
        # 半导体/技术行业天然优势
        semi_keywords = ["semiconductor", "chip", "gpu", "memory", "foundry",
                         "equipment", "eda", "packaging", "hbm"]
        tech_keywords = ["data center", "networking", "infrastructure", "hardware"]
        semi_matches = sum(1 for kw in semi_keywords if kw in sector or kw in industry)
        tech_matches = sum(1 for kw in tech_keywords if kw in sector or kw in industry)
        sce_score += min(semi_matches * 2, 4)
        sce_score += min(tech_matches * 1, 2)

        # 高毛利率表明定价权/瓶颈位置
        if context.gross_margins > 0.60:
            sce_score += 2
        elif context.gross_margins > 0.50:
            sce_score += 1

        # 非半导体/科技行业扣分
        if "semiconductor" not in sector and "tech" not in sector and "hardware" not in sector:
            sce_score -= 3

        factors["supply_chain_edge"] = min(max(sce_score, 0), 10)

        # 2. momentum_leverage (0-10): 动量+杠杆信号
        mom_score = 5  # 基础分
        # RSI 50-75 = 健康上升趋势
        rsi = context.rsi_14
        if 50 <= rsi <= 75:
            mom_score += 2  # 完美动量区间
        elif 40 <= rsi < 50:
            mom_score += 1  # 即将上穿
        elif rsi > 75:
            mom_score -= 1  # 超买风险
        elif rsi < 30:
            mom_score -= 2  # 超卖，不追跌

        # MACD > Signal = 动量向上
        if context.macd > context.macd_signal:
            mom_score += 2
        else:
            mom_score -= 1

        # 价格接近52周高点 = 突破模式
        if context.price_to_52w_high > 0.90:
            mom_score += 1
        elif context.price_to_52w_high < 0.70:
            mom_score -= 1

        factors["momentum_leverage"] = min(max(mom_score, 0), 10)

        # 3. ai_compute_thesis (0-10): AI算力需求论证
        ai_score = 5  # 基础分
        # 高收入增速 = AI需求驱动
        if context.revenue_growth > 0.50:
            ai_score += 3  # 爆炸性增长 = AI算力直接受益
        elif context.revenue_growth > 0.30:
            ai_score += 2
        elif context.revenue_growth > 0.15:
            ai_score += 1
        elif context.revenue_growth < 0:
            ai_score -= 2

        # 半导体行业天然AI相关
        if "semiconductor" in sector:
            ai_score += 2
        elif "tech" in sector or "software" in sector:
            ai_score += 1

        # 高资本支出 = AI基建投入
        if context.debt_ratio > 30 and ("semiconductor" in sector or "tech" in sector):
            ai_score += 1  # 主动负债扩产

        factors["ai_compute_thesis"] = min(max(ai_score, 0), 10)

        # 4. valuation_growth (0-10): 成长估值
        val_score = 5  # 基础分
        # PS < 20 且高增速 = 可接受估值
        if context.ps < 10 and context.revenue_growth > 0.20:
            val_score += 3  # 低估值+高增速 = 完美
        elif context.ps < 15 and context.revenue_growth > 0.20:
            val_score += 2
        elif context.ps < 20 and context.revenue_growth > 0.15:
            val_score += 1
        elif context.ps > 25:
            val_score -= 2  # 估值过高
        elif context.ps > 20:
            val_score -= 1

        # PE合理性
        if context.pe < 30 and context.revenue_growth > 0.20:
            val_score += 1  # 低PE+高增速
        elif context.pe > 60:
            val_score -= 1  # PE过高

        # 高收入增速本身加分
        if context.revenue_growth > 0.30:
            val_score += 1

        factors["valuation_growth"] = min(max(val_score, 0), 10)

        # 5. risk_management (0-10): 风控
        risk_score = 5  # 基础分
        # 波动率适中
        rsi = context.rsi_14
        if 30 <= rsi <= 70:
            risk_score += 1  # 波动率可控

        # 回撤风险
        if context.max_drawdown:
            max_dd = abs(context.max_drawdown)
            if max_dd < 0.20:
                risk_score += 2  # 低回撤
            elif max_dd < 0.30:
                risk_score += 1
            elif max_dd > 0.50:
                risk_score -= 2  # 高回撤风险

        # 负债率
        if context.debt_ratio < 30:
            risk_score += 2  # 低负债 = 财务健康
        elif context.debt_ratio < 50:
            risk_score += 1
        elif context.debt_ratio > 70:
            risk_score -= 2  # 高负债风险

        factors["risk_management"] = min(max(risk_score, 0), 10)

        # 计算总分
        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.85, 0.4 + factors["supply_chain_edge"] / 15 + factors["momentum_leverage"] / 15)

        key_findings = []
        risks = []

        # 生成发现
        if factors["supply_chain_edge"] >= 7:
            key_findings.append(f"🔗 供应链瓶颈位置明确，定价权强（评分:{factors['supply_chain_edge']}/10）")
        if factors["momentum_leverage"] >= 7:
            key_findings.append(f"📈 动量信号强烈，RSI/MACD配合良好（评分:{factors['momentum_leverage']}/10）")
        if factors["ai_compute_thesis"] >= 7:
            key_findings.append(f"⚡ AI算力需求直接受益，增速验证thesis（评分:{factors['ai_compute_thesis']}/10）")
        if factors["valuation_growth"] >= 7:
            key_findings.append(f"💎 估值合理+高增速，PEG attractive（评分:{factors['valuation_growth']}/10）")
        if factors["risk_management"] >= 7:
            key_findings.append(f"🛡️ 风控指标健康，回撤可控（评分:{factors['risk_management']}/10）")

        # 风险
        if factors["supply_chain_edge"] < 4:
            risks.append("不在AI供应链核心位置，缺乏瓶颈逻辑")
        if factors["momentum_leverage"] < 4:
            risks.append("动量走弱，RSI/MACD不支持，不适合杠杆入场")
        if "semiconductor" not in sector and "tech" not in sector:
            risks.append("非半导体/科技行业，供应链瓶颈框架适用性低")
        if context.ps > 25:
            risks.append(f"PS={context.ps:.1f}过高，瓶颈溢价可能已被充分定价")
        if context.rsi_14 > 80:
            risks.append(f"RSI={context.rsi_14:.0f}严重超买，短期回调风险大")

        # 模型适用性
        if factors["supply_chain_edge"] >= 7 and factors["ai_compute_thesis"] >= 5:
            coverage_confidence = 1.0
        elif factors["supply_chain_edge"] >= 5 or factors["ai_compute_thesis"] >= 6:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.25

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**供应链瓶颈识别: {factors['supply_chain_edge']}/10** (权重{self.scoring_weights['supply_chain_edge']:.0%})
- 行业: {context.sector} / {context.industry}
- 毛利率: {context.gross_margins*100:.1f}% {'(定价权强)' if context.gross_margins > 0.60 else ''}
- 瓶颈判断: {'核心瓶颈位置' if factors['supply_chain_edge'] >= 7 else '非核心瓶颈' if factors['supply_chain_edge'] < 4 else '潜在瓶颈'}

**动量杠杆信号: {factors['momentum_leverage']}/10** (权重{self.scoring_weights['momentum_leverage']:.0%})
- RSI(14): {context.rsi_14:.1f} {'(健康上升)' if 50 <= context.rsi_14 <= 75 else '(超买警告)' if context.rsi_14 > 75 else ''}
- MACD vs Signal: {'动量向上' if context.macd > context.macd_signal else '动量向下'}
- 52周高点距离: {context.price_to_52w_high*100:.1f}%

**AI算力需求: {factors['ai_compute_thesis']}/10** (权重{self.scoring_weights['ai_compute_thesis']:.0%})
- 收入增速: {context.revenue_growth*100:.1f}%
- 行业: {context.sector}
- AI受益判断: {'直接受益' if factors['ai_compute_thesis'] >= 7 else '间接受益' if factors['ai_compute_thesis'] >= 5 else '关联度低'}

**成长估值: {factors['valuation_growth']}/10** (权重{self.scoring_weights['valuation_growth']:.0%})
- PS: {context.ps:.1f} {'(合理)' if context.ps < 15 else '(偏高)' if context.ps > 20 else ''}
- PE: {context.pe:.1f}
- 收入增速: {context.revenue_growth*100:.1f}%

**风险管理: {factors['risk_management']}/10** (权重{self.scoring_weights['risk_management']:.0%})
- 负债率: {context.debt_ratio:.1f}%
- RSI区间: {'可控' if 30 <= context.rsi_14 <= 70 else '需注意'}

**综合评分: {total_score:.1f}/10**
**供应链瓶颈交易结论: {'🚀 Full send - 供应链瓶颈+动量确认，高conviction入场' if avg_score >= self.thresholds.get('bullish_threshold', 7.0) else '⚠️ No edge - 无明确瓶颈逻辑或动量不支持' if avg_score <= self.thresholds.get('bearish_threshold', 4.0) else '⏳ Watching - 等待供应链数据确认或技术面突破'}**
"""

        return AgentResponse(
            agent_id=self.agent_id,
            agent_name=self.name,
            signal=signal,
            confidence=confidence,
            score=total_score,
            reasoning=reasoning,
            key_findings=key_findings,
            risks=risks,
            metadata={"factors": factors, "philosophy": self.philosophy},
            coverage_confidence=coverage_confidence,
        )
