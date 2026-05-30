# -*- coding: utf-8 -*-
"""
ZhangLeiAgent - 张磊 长期结构性价值投资
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class ZhangLeiAgent(BaseAgent):
    """张磊 (高瓴资本) - 长期结构性价值投资"""

    def __init__(self):
        super().__init__(
            agent_id="zhang_lei",
            name="张磊 (Zhang Lei)",
            identity="""高瓴资本创始人。长期结构性价值投资者，寻找10年级别的结构性变化受益者。
                        核心理念：在正确的赛道上，以合理价格买最好的公司，做时间的朋友。
                        不仅是财务投资者，更注重帮助企业创造价值（创造价值，而非只发现价值）。""",
            philosophy=["长期结构性机会", "研究驱动", "创造价值", "做时间的朋友", "赛道优先"],
            scoring_weights={
                "structural_opportunity": 0.30,  # 结构性机会/赛道
                "business_model_quality": 0.25,  # 商业模式质量
                "management_excellence": 0.20,   # 管理层卓越程度
                "competitive_moat": 0.15,        # 竞争护城河
                "valuation_fairness": 0.10,      # 估值公平性
            },
            thresholds={
                "bullish_threshold": 6.8,
                "bearish_threshold": 4.0,
                "revenue_growth_min": 0.15,
                "gross_margin_min": 0.30,
                "roe_min": 0.12,
                "pe_max": 50,
            },
            biases={
                "prefers_platform_businesses": True,
                "china_growth_focused": True,
                "growth_over_value": True,
                "strategic_partner_mindset": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        factors = {}

        sector = (context.sector or "").lower()
        industry = (context.industry or "").lower()

        # 结构性机会判断（行业加成）
        structural_multiplier = 1.0
        if any(k in sector for k in ["technology", "software", "internet", "biotech", "health"]):
            structural_multiplier = 1.3  # 高成长赛道
        elif any(k in sector for k in ["consumer", "retail"]):
            structural_multiplier = 1.1  # 消费升级
        elif any(k in sector for k in ["energy", "utilities", "material"]):
            structural_multiplier = 0.8  # 传统行业

        # 1. 结构性机会 (0-10)
        # 赛道够大且处于增长期是张磊的第一优先级
        struct_score = 4.0
        if context.revenue_growth > 0.15:
            struct_score += 2.0
        if context.revenue_growth > 0.30:
            struct_score += 1.5
        if context.revenue_growth > 0.50:
            struct_score += 1.0
        # 市值反映TAM信心
        if context.market_cap > 10:  # $10B+
            struct_score += 1.0
        if context.market_cap > 50:  # $50B+
            struct_score += 0.5
        factors["structural_opportunity"] = max(0, min(struct_score * structural_multiplier, 10))

        # 2. 商业模式质量 (0-10)
        # 轻资产、高ROE、强FCF = 高质量商业模式
        biz_score = 4.0
        if context.gross_margins > 0.40:
            biz_score += 2.0
        if context.gross_margins > 0.60:
            biz_score += 1.0
        if context.operating_margins > 0.15:
            biz_score += 1.5
        if context.fcf > 0:
            biz_score += 1.5
        if context.roe > 0.20:
            biz_score += 1.0
        # 负利润但高增速的早期平台容忍度更高
        if context.operating_margins < 0 and context.revenue_growth > 0.40:
            biz_score -= 0.5  # 轻度惩罚（早期平台可接受）
        elif context.operating_margins < -0.20:
            biz_score -= 2.0  # 严重亏损
        factors["business_model_quality"] = max(0, min(biz_score, 10))

        # 3. 管理层卓越程度 (0-10)
        mgmt_score = 5.0
        # 内部人持股：创始人控制 = 长期视野
        if context.insider_ownership > 20:
            mgmt_score += 2.0
        elif context.insider_ownership > 10:
            mgmt_score += 1.0
        if context.institutional_ownership > 40:
            mgmt_score += 1.5
        # 资本配置效率
        if context.roe > 0.25:
            mgmt_score += 1.5
        elif context.roe > 0.15:
            mgmt_score += 0.5
        factors["management_excellence"] = max(0, min(mgmt_score, 10))

        # 4. 竞争护城河 (0-10)
        moat_score = 4.0
        if context.gross_margins > 0.35:
            moat_score += 1.5
        if context.gross_margins > 0.55:
            moat_score += 1.5
        # 高增长中维持高毛利 = 真实护城河
        if context.revenue_growth > 0.20 and context.gross_margins > 0.40:
            moat_score += 2.0
        if context.operating_margins > 0.20:
            moat_score += 1.0
        if context.debt_ratio < 0.40:
            moat_score += 0.5
        factors["competitive_moat"] = max(0, min(moat_score, 10))

        # 5. 估值公平性 (0-10)
        # 张磊愿意付成长溢价，但不愿意为不确定性买单
        val_score = 5.0
        pe_max = self.thresholds.get("pe_max", 50)
        if context.pe > 0:
            if context.pe < pe_max * 0.5:
                val_score += 3.0
            elif context.pe < pe_max:
                val_score += 1.5
            elif context.pe < pe_max * 1.5:
                val_score -= 0.5
            else:
                val_score -= 2.5
        # PEG 视角：高增长可容纳更高PE
        if context.pe > 0 and context.revenue_growth > 0:
            peg_like = context.pe / (context.revenue_growth * 100)
            if peg_like < 1.5:
                val_score += 1.0
            elif peg_like > 3.0:
                val_score -= 1.0
        factors["valuation_fairness"] = max(0, min(val_score, 10))

        # 综合评分
        total_score = sum(
            factors[k] * self.scoring_weights[k]
            for k in factors
        )
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.88, 0.45 + factors["structural_opportunity"] / 25 + factors["competitive_moat"] / 40)

        reasoning = self._generate_reasoning(context, factors, total_score)

        key_findings = []
        risks = []

        if factors["structural_opportunity"] >= 7:
            key_findings.append(f"结构性机会明确：营收增速{context.revenue_growth*100:.0f}%，处于高增长赛道")
        if factors["business_model_quality"] >= 7:
            key_findings.append(f"商业模式优质：毛利率{context.gross_margins*100:.0f}%，FCF正向")
        if factors["management_excellence"] >= 7:
            key_findings.append(f"管理层卓越：创始人持股{context.insider_ownership:.1f}%，ROE{context.roe*100:.0f}%")
        if context.revenue_growth < 0.10:
            risks.append("增速不足，结构性机会可能已过峰值")
        if context.operating_margins < -0.15 and context.revenue_growth < 0.30:
            risks.append("亏损+低增速组合，商业模式有效性存疑")
        if factors["valuation_fairness"] < 4:
            risks.append("估值过高，即使在长期成长框架下安全边际不足")

        coverage_confidence = 1.0
        if context.revenue_growth < 0:
            coverage_confidence = 0.7  # 衰退期企业不在张磊框架内

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

**核心问题：这是10年级别的结构性机会吗？**

**结构性机会: {factors['structural_opportunity']:.1f}/10**
- 营收增速: {context.revenue_growth*100:.1f}% {'✓ 高成长' if context.revenue_growth > 0.20 else '⚠️' if context.revenue_growth > 0.10 else '✗'}
- 市值规模: ${context.market_cap:.1f}B

**商业模式质量: {factors['business_model_quality']:.1f}/10**
- 毛利率: {gross_pct:.1f}%
- 营业利润率: {context.operating_margins*100:.1f}%
- FCF: {context.fcf:,.0f} {'✓' if context.fcf > 0 else '✗'}

**管理层卓越度: {factors['management_excellence']:.1f}/10**
- 内部人持股: {context.insider_ownership:.1f}%
- ROE: {context.roe*100:.1f}%

**竞争护城河: {factors['competitive_moat']:.1f}/10**

**估值公平性: {factors['valuation_fairness']:.1f}/10**
- PE: {pe_str}

**综合评分: {total_score:.1f}/10**
高瓴判断：{"✓ 值得做时间的朋友。" if total_score >= self.thresholds.get("bullish_threshold", 7.0) else "⚠️ 赛道对但需等更好价格。" if total_score >= self.thresholds.get("bearish_threshold", 4.0) else "✗ 赛道不够大或护城河不够宽。"}
"""
