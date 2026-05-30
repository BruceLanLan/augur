# -*- coding: utf-8 -*-
"""
BuffettAgent - Warren Buffett 护城河价值投资
"""

from typing import Dict, List
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class BuffettAgent(BaseAgent):
    """Warren Buffett - 护城河价值投资"""

    def __init__(self):
        super().__init__(
            agent_id="buffett",
            name="Warren Buffett",
            identity="""价值投资大师，强调经济护城河、可预测盈利、财务稳健、
                        优质管理层和合理估值。偏好长期持有优质企业。""",
            philosophy=["护城河", "owner earnings", "安全边际", "优质管理层"],
            scoring_weights={
                "moat": 0.30,           # 护城河宽度
                "earnings_predictability": 0.25,  # 盈利可预测性
                "financial_strength": 0.20,       # 财务实力
                "management_quality": 0.15,       # 管理质量
                "valuation": 0.10,               # 估值合理性
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
                "pe_max": 25,
                "roe_min": 0.15,
                "debt_ratio_max": 0.50,
                "current_ratio_min": 1.5,
            },
            biases={
                "prefers_quality": True,
                "long_term_orientation": True,
                "avoid_zombie_companies": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Buffett风格分析"""
        factors = {}

        # 行业专属权重调整
        sector = context.sector.lower() if context.sector else ""
        industry = context.industry.lower() if context.industry else ""
        if "tech" in sector or "software" in sector or "semiconductor" in sector:
            growth_multiplier = 1.5
            value_multiplier = 0.7
        elif "bank" in sector or "financ" in sector or "insur" in sector:
            growth_multiplier = 0.8
            value_multiplier = 1.3
        elif "reit" in sector or "real estate" in sector:
            growth_multiplier = 0.8
            value_multiplier = 1.4
        elif "biotech" in sector or "pharma" in sector or "health" in sector:
            growth_multiplier = 1.3
            value_multiplier = 0.8
        elif "energy" in sector or "oil" in sector or "gas" in sector:
            growth_multiplier = 0.9
            value_multiplier = 1.2
        else:
            growth_multiplier = 1.0
            value_multiplier = 1.0

        # 1. 护城河分析 (0-10)
        moat_score = 0
        if context.gross_margins > 0.40:
            moat_score += 3
        if context.gross_margins > 0.60:
            moat_score += 2
        if context.operating_margins > 0.20:
            moat_score += 2
        if context.revenue_growth > 0.10:
            moat_score += 2
        roe_min = self.thresholds.get("roe_min", 0.15)
        if context.roe > roe_min:
            moat_score += 1
        factors["moat"] = min(max(moat_score * growth_multiplier, 0), 10)

        # 2. 盈利可预测性 (0-10)
        earnings_score = 5
        if context.revenue_growth > 0:
            earnings_score += 3
        if context.fcf > 0:
            earnings_score += 2
        factors["earnings_predictability"] = min(max(earnings_score, 0), 10)

        # 3. 财务实力 (0-10)
        finance_score = 5
        if context.debt_ratio < 0.50:
            finance_score += 3
        elif context.debt_ratio > 0.80:
            finance_score -= 3
        if context.current_ratio > 1.5:
            finance_score += 2
        factors["financial_strength"] = min(max(finance_score, 0), 10)

        # 4. 管理质量 (0-10)
        mgmt_score = 5
        if context.institutional_ownership > 50:
            mgmt_score += 3
        if context.institutional_ownership > 70:
            mgmt_score += 2
        factors["management_quality"] = min(max(mgmt_score, 0), 10)

        # 5. 估值 (0-10)
        val_score = 5
        pe_max = self.thresholds.get("pe_max", 25)
        if context.pe > 0:
            if context.pe < pe_max * 0.6:
                val_score += 3
            elif context.pe < pe_max:
                val_score += 1
            elif context.pe > pe_max * 2:
                val_score -= 2
        if context.fcf > 0 and context.market_cap > 0:
            fcf_yield = context.fcf / context.market_cap
            if fcf_yield > 0.05:
                val_score += 2
        factors["valuation"] = min(max(val_score * value_multiplier, 0), 10)

        # 计算综合评分 - 只使用factors中存在的因子
        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.95, 0.5 + factors["moat"] / 20)

        # 生成推理
        reasoning = self._generate_reasoning(context, factors, total_score)

        # 关键发现
        key_findings = []
        risks = []

        if factors["moat"] >= 7:
            key_findings.append(f"护城河强大：毛利率{context.gross_margins*100:.0f}%, ROE{context.roe*100:.0f}%")
        if factors["valuation"] >= 7 and context.pe > 0:
            key_findings.append(f"估值吸引：PE {context.pe:.1f}")
        if context.debt_ratio > 0.70:
            risks.append(f"负债率偏高({context.debt_ratio*100:.0f}%)")
        if context.pe > 80:
            risks.append(f"估值极高(PE={context.pe:.0f})")

        # 模型适用性：Buffett护城河框架需要可见的盈利能力和FCF
        if context.fcf > 0 and context.pe > 0 and context.pe < 100:
            coverage_confidence = 1.0
        elif context.pe > 0 or context.revenue > 0:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.4  # 无盈利/FCF，估值框架失效

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
        pe_str = f'{context.pe:.1f}' if context.pe and context.pe > 0 else 'N/A'
        gross_pct = context.gross_margins * 100 if context.gross_margins else 0
        roe_pct = context.roe * 100 if context.roe else 0

        return f"""## {self.name} Analysis for {context.ticker}

**护城河 (Moat): {factors['moat']}/10**
- 毛利率: {gross_pct:.1f}% {'✓' if context.gross_margins > 0.4 else '✗'}
- 营业利润率: {context.operating_margins*100:.1f}%
- ROE: {roe_pct:.1f}% {'✓' if context.roe > 0.15 else '✗'}

**盈利可预测性: {factors['earnings_predictability']}/10**
**财务实力: {factors['financial_strength']}/10**
- 负债率: {context.debt_ratio*100:.1f}% {'✓' if context.debt_ratio < 0.50 else '✗'}
- 流动比率: {context.current_ratio:.2f}

**管理质量: {factors['management_quality']}/10**
- 机构持股: {context.institutional_ownership:.1f}%

**估值: {factors['valuation']}/10**
- PE: {pe_str}
- FCF收益率: {f"{context.fcf/context.market_cap*100:.2f}%" if context.fcf and context.market_cap else "N/A"}

**综合评分: {total_score:.1f}/10**
投资哲学：{' + '.join(self.philosophy[:2])}
"""
