# -*- coding: utf-8 -*-
"""
DanBinAgent - 但斌 品牌护城河·时代β·消费成长
"""

from typing import Dict, List
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class DanBinAgent(BaseAgent):
    """但斌 (东方港湾) - 品牌护城河·享受时代β"""

    def __init__(self):
        super().__init__(
            agent_id="dan_bin",
            name="但斌 (Dan Bin)",
            identity="""东方港湾投资创始人，中国"茅台投资者"代表人物。
                        核心理念：找到伟大企业，享受时代的β；持有品牌护城河公司，不轻易卖出。
                        专注中国消费升级、互联网平台、医疗消费等结构性主题。""",
            philosophy=["时代β", "品牌护城河", "消费升级", "长期持有", "不要和伟大的公司分开"],
            scoring_weights={
                "brand_moat": 0.30,           # 品牌护城河
                "pricing_power": 0.25,         # 定价权
                "growth_franchise": 0.20,      # 成长特许权
                "china_structural_theme": 0.15, # 中国结构性主题
                "valuation_acceptability": 0.10, # 估值可接受度
            },
            thresholds={
                "bullish_threshold": 6.5,
                "bearish_threshold": 3.8,
                "gross_margin_min": 0.35,
                "roe_min": 0.15,
                "pe_max": 45,
            },
            biases={
                "prefers_brand_consumer": True,
                "china_market_focus": True,
                "avoids_commodity": True,
                "emotional_attachment_to_quality": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        factors = {}

        sector = (context.sector or "").lower()
        industry = (context.industry or "").lower()

        # 行业β加成（但斌偏好消费+互联网）
        brand_multiplier = 1.0
        if any(k in sector for k in ["consumer", "beverage", "food", "luxury"]):
            brand_multiplier = 1.3
        elif any(k in sector for k in ["communication", "internet", "technology"]):
            brand_multiplier = 1.2
        elif any(k in sector for k in ["health", "medical"]):
            brand_multiplier = 1.1
        elif any(k in sector for k in ["material", "energy", "commodity"]):
            brand_multiplier = 0.6  # 商品无品牌

        # 1. 品牌护城河 (0-10)
        # 但斌核心：消费者是否愿意为品牌付溢价
        brand_score = 4.0
        if context.gross_margins > 0.40:
            brand_score += 2.0  # 高毛利 = 有品牌溢价
        if context.gross_margins > 0.60:
            brand_score += 1.5
        if context.gross_margins > 0.75:
            brand_score += 1.0  # 极致品牌（茅台级别）
        if context.roe > 0.20:
            brand_score += 1.5  # 高ROE = 有真实护城河
        if context.roe > 0.30:
            brand_score += 0.5
        # 品牌消费行业加成
        brand_score *= brand_multiplier
        factors["brand_moat"] = max(0, min(brand_score, 10))

        # 2. 定价权 (0-10)
        # 能否在不失去客户的情况下持续提价
        pricing_score = 4.0
        # 高毛利率趋势 = 有定价权
        if context.gross_margins > 0.45:
            pricing_score += 3.0
        elif context.gross_margins > 0.35:
            pricing_score += 1.5
        elif context.gross_margins < 0.20:
            pricing_score -= 2.0  # 低毛利无定价权
        if context.operating_margins > 0.20:
            pricing_score += 2.0
        elif context.operating_margins > 0.10:
            pricing_score += 1.0
        # 收入增长中保持高毛利 = 定价权验证
        if context.revenue_growth > 0.10 and context.gross_margins > 0.40:
            pricing_score += 1.0
        factors["pricing_power"] = max(0, min(pricing_score, 10))

        # 3. 成长特许权 (0-10)
        # 但斌偏好高品质增长（不是廉价增长）
        growth_score = 4.0
        if context.revenue_growth > 0.12:
            growth_score += 1.5
        if context.revenue_growth > 0.25:
            growth_score += 1.5
        if context.earnings_growth > 0.15:
            growth_score += 1.5
        if context.fcf > 0:
            growth_score += 1.5  # 有现金流支撑的增长
        # 高增长+高毛利 = 质量成长
        if context.revenue_growth > 0.15 and context.gross_margins > 0.40:
            growth_score += 1.0
        factors["growth_franchise"] = max(0, min(growth_score, 10))

        # 4. 中国结构性主题 (0-10)
        # 中国消费升级、医疗、互联网受益程度
        china_score = 5.0
        # 消费品行业 = 直接受益
        if any(k in sector for k in ["consumer", "health", "communication"]):
            china_score += 2.0
        # 市值规模 = 市场认可度
        if context.market_cap > 5:
            china_score += 1.0
        if context.market_cap > 20:
            china_score += 0.5
        if context.institutional_ownership > 40:
            china_score += 1.0
        if context.revenue_growth > 0.10:
            china_score += 0.5
        factors["china_structural_theme"] = max(0, min(china_score, 10))

        # 5. 估值可接受度 (0-10)
        # 但斌愿意为品牌付溢价，但不是无限溢价
        val_score = 5.0
        pe_max = self.thresholds.get("pe_max", 45)
        if context.pe > 0:
            if context.pe < pe_max * 0.5:
                val_score += 3.0
            elif context.pe < pe_max * 0.8:
                val_score += 1.5
            elif context.pe < pe_max:
                val_score += 0.5
            elif context.pe < pe_max * 1.5:
                val_score -= 1.0  # 贵但还在但斌接受范围
            else:
                val_score -= 2.5  # 太贵了
        if context.fcf > 0 and context.market_cap > 0:
            fcf_yield = context.fcf / context.market_cap
            if fcf_yield > 0.03:
                val_score += 1.0
        factors["valuation_acceptability"] = max(0, min(val_score, 10))

        # 综合评分
        total_score = sum(
            factors[k] * self.scoring_weights[k]
            for k in factors
        )
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.85, 0.45 + factors["brand_moat"] / 25 + factors["pricing_power"] / 50)

        reasoning = self._generate_reasoning(context, factors, total_score)

        key_findings = []
        risks = []

        if factors["brand_moat"] >= 7:
            key_findings.append(f"品牌护城河强：毛利率{context.gross_margins*100:.0f}%，ROE{context.roe*100:.0f}%")
        if factors["pricing_power"] >= 7:
            key_findings.append(f"定价权强：高毛利+增速组合，消费者愿意付溢价")
        if factors["growth_franchise"] >= 7:
            key_findings.append(f"高质量成长：营收增速{context.revenue_growth*100:.0f}%且FCF正向")
        if context.gross_margins < 0.25:
            risks.append("毛利率过低，缺乏品牌护城河，非但斌偏好标的")
        if context.pe > 60:
            risks.append(f"估值过高(PE={context.pe:.0f})，即使是好公司也超出合理范围")
        if "material" in sector or "energy" in sector:
            risks.append("商品属性强，缺乏品牌定价权，不在但斌核心框架内")

        coverage_confidence = 1.0
        if context.gross_margins < 0.20 or "material" in sector:
            coverage_confidence = 0.5  # 商品/低毛利，框架适用性弱

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
        gross_pct = context.gross_margins * 100 if context.gross_margins else 0

        return f"""## {self.name} 分析 — {context.ticker}

**核心问题：这是值得享受时代β的伟大公司吗？**

**品牌护城河: {factors['brand_moat']:.1f}/10**
- 毛利率: {gross_pct:.1f}% {'✓ 品牌溢价明显' if context.gross_margins > 0.40 else '⚠️' if context.gross_margins > 0.25 else '✗ 无明显品牌溢价'}
- ROE: {context.roe*100:.1f}% {'✓' if context.roe > 0.15 else '✗'}

**定价权: {factors['pricing_power']:.1f}/10**
- 营业利润率: {context.operating_margins*100:.1f}%

**成长特许权: {factors['growth_franchise']:.1f}/10**
- 营收增速: {context.revenue_growth*100:.1f}%
- 盈利增速: {context.earnings_growth*100:.1f}%
- FCF: {context.fcf:,.0f} {'✓' if context.fcf > 0 else '✗'}

**中国结构性主题: {factors['china_structural_theme']:.1f}/10**
- 机构持股: {context.institutional_ownership:.1f}%

**估值可接受度: {factors['valuation_acceptability']:.1f}/10**
- PE: {pe_str}

**综合评分: {total_score:.1f}/10**
但斌判断：{"✓ 伟大公司，不要和它分开太早。" if total_score >= self.thresholds.get("bullish_threshold", 6.5) else "⚠️ 有品牌但需等更好价格。" if total_score >= self.thresholds.get("bearish_threshold", 3.8) else "✗ 缺乏品牌护城河或赛道不对。"}
"""
