# -*- coding: utf-8 -*-
"""
LiLuAgent - 李录 深度价值·安全边际·新兴市场
"""

from typing import Dict, List
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class LiLuAgent(BaseAgent):
    """李录 (喜马拉雅资本) - 深度价值投资，安全边际优先"""

    def __init__(self):
        super().__init__(
            agent_id="li_lu",
            name="李录 (Li Lu)",
            identity="""喜马拉雅资本创始人，查理·芒格称其为"中国的芒格"。
                        格雷厄姆-巴菲特-芒格价值投资体系的中国实践者。
                        核心原则：在能力圈内，以显著折价于内在价值的价格买入有护城河的优质公司。
                        对中国和亚洲新兴市场有独特的深度理解。""",
            philosophy=["安全边际", "能力圈", "深度研究", "护城河", "耐心等待"],
            scoring_weights={
                "intrinsic_value_discount": 0.30,  # 折价于内在价值
                "competitive_position": 0.25,       # 竞争地位/护城河
                "financial_soundness": 0.20,        # 财务健全
                "management_quality": 0.15,         # 管理层质量
                "industry_tailwinds": 0.10,         # 行业顺风
            },
            thresholds={
                "bullish_threshold": 6.5,
                "bearish_threshold": 3.5,
                "pe_max": 25,
                "pb_max": 3.0,
                "roe_min": 0.12,
                "debt_ratio_max": 0.60,
                "margin_of_safety_min": 0.25,
            },
            biases={
                "requires_margin_of_safety": True,
                "prefers_undervalued": True,
                "emerging_market_expertise": True,
                "concentrated_portfolio": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        factors = {}

        sector = (context.sector or "").lower()

        # 行业特性调整
        if "financ" in sector or "bank" in sector:
            value_multiplier = 1.3
            growth_multiplier = 0.7
        elif "energy" in sector or "material" in sector:
            value_multiplier = 1.2
            growth_multiplier = 0.8
        elif "technology" in sector or "software" in sector:
            value_multiplier = 0.8
            growth_multiplier = 1.1
        else:
            value_multiplier = 1.0
            growth_multiplier = 1.0

        # 1. 折价于内在价值 (0-10)
        # 李录核心：当前价格是否提供了足够的安全边际
        discount_score = 4.0
        pe_max = self.thresholds.get("pe_max", 25)
        pb_max = self.thresholds.get("pb_max", 3.0)

        if context.pe > 0:
            if context.pe < pe_max * 0.5:
                discount_score += 3.5  # 极度低估
            elif context.pe < pe_max * 0.7:
                discount_score += 2.5
            elif context.pe < pe_max:
                discount_score += 1.0
            elif context.pe < pe_max * 1.5:
                discount_score -= 0.5
            else:
                discount_score -= 2.5  # 明显高估

        if context.pb > 0:
            if context.pb < 1.0:
                discount_score += 2.0  # 低于净资产
            elif context.pb < pb_max * 0.5:
                discount_score += 1.0
            elif context.pb > pb_max * 2:
                discount_score -= 1.5

        if context.fcf > 0 and context.market_cap > 0:
            fcf_yield = context.fcf / context.market_cap
            if fcf_yield > 0.08:
                discount_score += 1.5  # 高FCF收益率
            elif fcf_yield > 0.05:
                discount_score += 0.5

        factors["intrinsic_value_discount"] = max(0, min(discount_score * value_multiplier, 10))

        # 2. 竞争地位/护城河 (0-10)
        # 李录：不只看估值，护城河决定折价能否持续
        competitive_score = 4.0
        if context.gross_margins > 0.30:
            competitive_score += 1.5
        if context.gross_margins > 0.50:
            competitive_score += 1.5
        roe_min = self.thresholds.get("roe_min", 0.12)
        if context.roe > roe_min:
            competitive_score += 1.5
        if context.roe > 0.20:
            competitive_score += 1.0
        if context.operating_margins > 0.15:
            competitive_score += 1.0
        if context.revenue_growth > 0.05:
            competitive_score += 0.5
        factors["competitive_position"] = max(0, min(competitive_score, 10))

        # 3. 财务健全 (0-10)
        # 李录：财务保守是长期持有的基础
        finance_score = 5.0
        if context.debt_ratio < 0.30:
            finance_score += 2.5
        elif context.debt_ratio < 0.50:
            finance_score += 1.0
        elif context.debt_ratio > 0.70:
            finance_score -= 2.5
        if context.current_ratio > 2.0:
            finance_score += 1.5
        elif context.current_ratio > 1.2:
            finance_score += 0.5
        elif context.current_ratio < 1.0:
            finance_score -= 1.5
        if context.fcf > 0:
            finance_score += 1.0
        factors["financial_soundness"] = max(0, min(finance_score, 10))

        # 4. 管理层质量 (0-10)
        mgmt_score = 5.0
        if context.insider_ownership > 15:
            mgmt_score += 2.0
        if context.institutional_ownership > 40:
            mgmt_score += 1.5
        # ROE稳定性代理：当前ROE作为历史一致性指标
        if context.roe > 0.15:
            mgmt_score += 1.5
        if context.roe > 0.25:
            mgmt_score += 0.5
        factors["management_quality"] = max(0, min(mgmt_score, 10))

        # 5. 行业顺风 (0-10)
        tailwind_score = 5.0
        if context.revenue_growth > 0.10:
            tailwind_score += 2.0
        elif context.revenue_growth > 0.05:
            tailwind_score += 1.0
        elif context.revenue_growth < 0:
            tailwind_score -= 2.0
        # 新兴市场/亚洲主题加分
        if context.earnings_growth > 0.10:
            tailwind_score += 1.5
        if context.gross_margins > 0.35 and context.revenue_growth > 0.08:
            tailwind_score += 1.0
        factors["industry_tailwinds"] = max(0, min(tailwind_score * growth_multiplier, 10))

        # 综合评分
        total_score = sum(
            factors[k] * self.scoring_weights[k]
            for k in factors
        )
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.92, 0.50 + factors["intrinsic_value_discount"] / 20 + factors["competitive_position"] / 40)

        reasoning = self._generate_reasoning(context, factors, total_score)

        key_findings = []
        risks = []

        if factors["intrinsic_value_discount"] >= 7:
            pe_str = f"PE={context.pe:.1f}" if context.pe > 0 else "盈利指标低"
            key_findings.append(f"价格显著低于内在价值：{pe_str}，安全边际充足")
        if factors["competitive_position"] >= 7:
            key_findings.append(f"竞争地位强：毛利率{context.gross_margins*100:.0f}%，ROE{context.roe*100:.0f}%")
        if factors["financial_soundness"] >= 7:
            key_findings.append(f"财务稳健：负债率{context.debt_ratio*100:.0f}%，流动比{context.current_ratio:.2f}")
        if context.pe > 30:
            risks.append(f"估值偏高(PE={context.pe:.0f})，安全边际不足，与李录偏好相悖")
        if context.debt_ratio > 0.60:
            risks.append(f"负债率{context.debt_ratio*100:.0f}%偏高，财务风险需关注")
        if context.fcf < 0 and context.roe < 0.10:
            risks.append("无FCF+低ROE，内在价值难以评估")

        coverage_confidence = 1.0
        if context.pe <= 0 and context.pb <= 0 and context.fcf <= 0:
            coverage_confidence = 0.4  # 无基本面数据，无法评估安全边际

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

    def _generate_reasoning(self, context: MarketContext, factors: Dict, total_score: float) -> str:
        pe_str = f"{context.pe:.1f}" if context.pe and context.pe > 0 else "N/A"
        pb_str = f"{context.pb:.2f}" if context.pb and context.pb > 0 else "N/A"
        gross_pct = context.gross_margins * 100 if context.gross_margins else 0

        return f"""## {self.name} 分析 — {context.ticker}

**核心问题：安全边际足够吗？护城河真实吗？**

**折价于内在价值: {factors['intrinsic_value_discount']:.1f}/10**
- PE: {pe_str} {'✓ 低估' if context.pe > 0 and context.pe < 20 else '⚠️ 偏高' if context.pe > 30 else ''}
- PB: {pb_str} {'✓ 破净' if context.pb > 0 and context.pb < 1 else ''}
- FCF收益率: {f"{context.fcf/context.market_cap*100:.2f}%" if context.fcf and context.market_cap else "N/A"}

**竞争地位: {factors['competitive_position']:.1f}/10**
- 毛利率: {gross_pct:.1f}%
- ROE: {context.roe*100:.1f}% {'✓' if context.roe > 0.12 else '✗'}

**财务健全: {factors['financial_soundness']:.1f}/10**
- 负债率: {context.debt_ratio*100:.1f}% {'✓' if context.debt_ratio < 0.50 else '⚠️'}
- 流动比: {context.current_ratio:.2f}

**管理层质量: {factors['management_quality']:.1f}/10**
- 内部人持股: {context.insider_ownership:.1f}%

**行业顺风: {factors['industry_tailwinds']:.1f}/10**
- 营收增速: {context.revenue_growth*100:.1f}%

**综合评分: {total_score:.1f}/10**
李录判断：{'✓ 安全边际充足，护城河真实，值得持有。' if total_score >= 6.5 else '⚠️ 部分条件不满足，等待更好价格。' if total_score >= 4.5 else '✗ 安全边际不足或护城河存疑。'}
"""
