# -*- coding: utf-8 -*-
"""
DuanYongpingAgent - 段永平 本分·做正确的事
"""

from typing import Dict, List
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class DuanYongpingAgent(BaseAgent):
    """段永平 - 本分·停止错误·极度集中"""

    def __init__(self):
        super().__init__(
            agent_id="duan_yongping",
            name="段永平 (Duan Yongping)",
            identity="""步步高创始人，极度集中的长期价值投资者。
                        核心哲学：本分（做正确的事）、Stop Doing Wrong Things、
                        看准后用能动用的钱全部投进去。只投自己真正理解的企业。""",
            philosophy=["本分", "Stop Doing Wrong Things", "极度集中", "能力圈", "长期持有"],
            scoring_weights={
                "business_clarity": 0.25,      # 商业模式清晰度
                "moat_quality": 0.30,           # 护城河质量
                "management_integrity": 0.20,   # 管理层本分/诚信
                "long_term_durability": 0.15,   # 长期持续性
                "valuation_reasonableness": 0.10, # 估值合理性
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
                "gross_margin_min": 0.35,
                "roe_min": 0.15,
                "debt_ratio_max": 0.60,
                "pe_max": 35,
            },
            biases={
                "prefers_consumer_tech": True,
                "avoids_complexity": True,
                "extreme_concentration": True,
                "very_long_hold": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        factors = {}

        sector = (context.sector or "").lower()

        # 1. 商业模式清晰度 (0-10)
        # 段永平核心：能否用1-2句话解释这门生意
        clarity_score = 5.0
        if context.revenue > 0 and context.gross_margins > 0:
            clarity_score += 1.5  # 有可见的盈利模式
        if context.fcf > 0:
            clarity_score += 2.0  # 产生真实现金流
        if context.pe > 0 and context.pe < 80:
            clarity_score += 1.0  # 估值可理解
        # 惩罚：负FCF + 高亏损 = 商业模式不清晰
        if context.fcf < 0 and context.revenue_growth < 0.20:
            clarity_score -= 2.5
        if context.operating_margins < -0.10:
            clarity_score -= 1.5
        factors["business_clarity"] = max(0, min(clarity_score, 10))

        # 2. 护城河质量 (0-10)
        # 段永平偏好：消费电子生态、品牌溢价、强转换成本
        moat_score = 4.0
        if context.gross_margins > 0.35:
            moat_score += 1.5
        if context.gross_margins > 0.50:
            moat_score += 1.5
        if context.roe > 0.20:
            moat_score += 2.0
        elif context.roe > 0.15:
            moat_score += 1.0
        if context.operating_margins > 0.20:
            moat_score += 1.5
        # 消费科技/苹果型企业加分
        if "consumer" in sector or "technology" in sector or "software" in sector:
            moat_score += 0.5
        # 高负债扣分（护城河真实但财务脆弱）
        if context.debt_ratio > 0.70:
            moat_score -= 1.5
        factors["moat_quality"] = max(0, min(moat_score, 10))

        # 3. 管理层本分/诚信 (0-10)
        # 段永平高度重视：管理层是否在做正确的事
        mgmt_score = 5.0
        if context.insider_ownership > 10:
            mgmt_score += 2.0  # 内部人持股高 = 利益一致
        if context.insider_ownership > 25:
            mgmt_score += 1.0
        if context.institutional_ownership > 50:
            mgmt_score += 1.5  # 机构认可
        # FCF转化率：衡量管理层资本配置能力
        if context.fcf > 0 and context.revenue > 0:
            fcf_margin = context.fcf / context.revenue
            if fcf_margin > 0.15:
                mgmt_score += 1.0
        factors["management_integrity"] = max(0, min(mgmt_score, 10))

        # 4. 长期持续性 (0-10)
        # 10年后这家公司仍然存在且更强大吗？
        durability_score = 5.0
        if context.revenue_growth > 0.10:
            durability_score += 1.5
        if context.revenue_growth > 0.20:
            durability_score += 1.0
        if context.debt_ratio < 0.40:
            durability_score += 1.5  # 低负债 = 能扛周期
        elif context.debt_ratio > 0.70:
            durability_score -= 2.0
        if context.current_ratio > 1.5:
            durability_score += 1.0
        # 高利润率 = 有护城河 = 能持续
        if context.gross_margins > 0.45 and context.operating_margins > 0.15:
            durability_score += 1.0
        factors["long_term_durability"] = max(0, min(durability_score, 10))

        # 5. 估值合理性 (0-10)
        # 段永平：不需要最低价，但要合理；宁可多付一点买最好的
        val_score = 5.0
        pe_max = self.thresholds.get("pe_max", 35)
        if context.pe > 0:
            if context.pe < pe_max * 0.6:
                val_score += 3.0  # 明显低估
            elif context.pe < pe_max:
                val_score += 1.5  # 合理
            elif context.pe < pe_max * 1.5:
                val_score -= 0.5  # 略贵但可接受（优质公司）
            else:
                val_score -= 2.5  # 明显高估
        if context.fcf > 0 and context.market_cap > 0:
            fcf_yield = context.fcf / context.market_cap
            if fcf_yield > 0.04:
                val_score += 1.5
            elif fcf_yield > 0.02:
                val_score += 0.5
        factors["valuation_reasonableness"] = max(0, min(val_score, 10))

        # 综合评分
        total_score = sum(
            factors[k] * self.scoring_weights[k]
            for k in factors
        )
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.90, 0.45 + factors["moat_quality"] / 20 + factors["business_clarity"] / 40)

        reasoning = self._generate_reasoning(context, factors, total_score)

        key_findings = []
        risks = []

        if factors["business_clarity"] >= 7:
            key_findings.append(f"商业模式清晰，FCF={context.fcf:,.0f}，可预测盈利")
        if factors["moat_quality"] >= 7:
            key_findings.append(f"护城河强：毛利率{context.gross_margins*100:.0f}%，ROE{context.roe*100:.0f}%")
        if factors["management_integrity"] >= 7:
            key_findings.append(f"管理层本分：内部人持股{context.insider_ownership:.1f}%")
        if context.fcf < 0:
            risks.append("负FCF：商业模式尚未证明可持续")
        if context.debt_ratio > 0.60:
            risks.append(f"负债率偏高({context.debt_ratio*100:.0f}%)，降低长期持续性")
        if context.pe > 50:
            risks.append(f"估值偏高(PE={context.pe:.0f})，安全边际不足")

        # 模型适用性：段永平框架需要清晰的盈利模式
        if context.fcf > 0 and context.gross_margins > 0.30:
            coverage_confidence = 1.0
        elif context.revenue > 0 and context.gross_margins > 0:
            coverage_confidence = 0.75
        else:
            coverage_confidence = 0.4  # 无法判断商业模式

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
        roe_pct = context.roe * 100 if context.roe else 0

        return f"""## {self.name} 分析 — {context.ticker}

**核心问题：这家公司在做正确的事吗？管理层本分吗？**

**商业模式清晰度: {factors['business_clarity']:.1f}/10**
- FCF: {context.fcf:,.0f} {'✓ 真实现金流' if context.fcf > 0 else '✗ 尚未产生现金流'}
- 营业利润率: {context.operating_margins*100:.1f}%

**护城河质量: {factors['moat_quality']:.1f}/10**
- 毛利率: {gross_pct:.1f}% {'✓' if context.gross_margins > 0.35 else '✗'}
- ROE: {roe_pct:.1f}% {'✓' if context.roe > 0.15 else '✗'}

**管理层本分: {factors['management_integrity']:.1f}/10**
- 内部人持股: {context.insider_ownership:.1f}%
- 机构持股: {context.institutional_ownership:.1f}%

**长期持续性: {factors['long_term_durability']:.1f}/10**
- 营收增速: {context.revenue_growth*100:.1f}%
- 负债率: {context.debt_ratio*100:.1f}% {'✓' if context.debt_ratio < 0.50 else '⚠️'}

**估值合理性: {factors['valuation_reasonableness']:.1f}/10**
- PE: {pe_str}
- FCF收益率: {f"{context.fcf/context.market_cap*100:.2f}%" if context.fcf and context.market_cap else "N/A"}

**综合评分: {total_score:.1f}/10**
段永平核心判断：{' ✓ 正确的事，看准可重仓。' if total_score >= 7 else ' ⚠️ 尚有疑虑，先弄清楚。' if total_score >= 5 else ' ✗ 有错误，停止是第一位的。'}
"""
