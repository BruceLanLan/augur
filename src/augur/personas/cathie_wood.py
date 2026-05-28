# -*- coding: utf-8 -*-
"""
CathieWoodAgent - Cathie Wood 破坏式创新
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class CathieWoodAgent(BaseAgent):
    """Cathie Wood - 破坏式创新"""

    def __init__(self):
        super().__init__(
            agent_id="cathie_wood",
            name="Cathie Wood",
            identity="""破坏式创新投资大师，ARK Invest创始人。专注于5年维度的颠覆性技术，
                        相信AI、基因组、区块链、自动驾驶、太空将重塑全球经济格局。
                        传统估值在此失效，应用Wright定律和S曲线分析。""",
            philosophy=["破坏式创新", "Wright定律", "S曲线", "5年视野"],
            scoring_weights={
                "disruption_score": 0.30,
                "ark_framework": 0.25,
                "innovation_diffusion": 0.20,
                "tam_size": 0.15,
                "tech_risk": 0.10,
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
            },
            biases={
                "tech_optimism": True,
                "long_duration": True,
                "disruptive_preference": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是Cathie Wood，ARK Invest创始人，破坏式创新投资理念倡导者。

核心理念：
1. 颠覆性技术以指数级速度降低成本（Wright定律：累计产量每翻倍，成本下降15-25%）
2. S曲线：技术采用率从5%到15%是最快阶段，此时是最佳投资时机
3. 传统DCF估值会系统性低估颠覆者，因为无法预测TAM扩张
4. 5大创新平台：AI/机器学习、基因组、区块链、自动驾驶、多维打印

名言：
- "If we are right, the opportunities are enormous"
- "Innovation is deflationary"
- "We fish where others are not"
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """CathieWood破坏式创新分析"""
        bullish_th = self.thresholds.get("bullish_threshold", 7.0)
        bearish_th = self.thresholds.get("bearish_threshold", 4.0)
        factors = {}

        # 1. 破坏性技术评分 (0-10): 行业+描述判断
        sector = context.sector.lower() if context.sector else ""
        industry = context.industry.lower() if context.industry else ""

        disrupt_score = 3  # 基础分
        # ARK 5大平台判断
        ark_keywords = ["tech", "software", "semiconductor", "ai", "biotech", "genomic",
                        "gene", "blockchain", "crypto", "autonomous", "electric", "space",
                        "robot", "fintech", "cloud", "cyber", "health", "medical"]
        matches = sum(1 for kw in ark_keywords if kw in sector or kw in industry)
        disrupt_score += min(matches * 2, 6)  # 每个匹配+2分，最多6分
        # 高毛利率=技术溢价存在
        if context.gross_margins > 0.60:
            disrupt_score += 1
        factors["disruption_score"] = min(max(disrupt_score, 0), 10)

        # 2. ARK框架验证 (0-10): 5年年化>15%的可能性
        # 用revenue_growth的Wright定律估算
        ark_score = 4
        if context.revenue_growth > 0.50:
            ark_score = 9  # >50%增速 → 5年可能10x
        elif context.revenue_growth > 0.30:
            ark_score = 7
        elif context.revenue_growth > 0.15:
            ark_score = 5
        elif context.revenue_growth > 0:
            ark_score = 3
        factors["ark_framework"] = ark_score

        # 3. 创新扩散曲线 (0-10): S曲线哪个阶段
        diffusion_score = 5
        if context.revenue_growth > 0.50:
            diffusion_score = 9  # 早期快速扩张
        elif context.revenue_growth > 0.30:
            diffusion_score = 7  # 加速阶段
        elif context.revenue_growth > 0.15:
            diffusion_score = 5  # 成长中期
        elif context.revenue_growth < 0.10:
            diffusion_score = 2  # 成熟/衰退
        factors["innovation_diffusion"] = diffusion_score

        # 4. 市场空间TAM (0-10)
        tam_score = 5
        if context.ps > 0:
            if context.ps < 5 and context.revenue_growth > 0.30:
                tam_score = 8  # 低PS+高增长=TAM扩张早期
            elif context.ps > 30:
                tam_score = 3  # 高PS=TAM已充分定价
        if context.market_cap < 10:
            tam_score += 1  # 小市值=TAM未被充分认识
        factors["tam_size"] = min(max(tam_score, 0), 10)

        # 5. 技术风险 (0-10, 越高越好=风险越低)
        tech_risk_score = 5
        if context.gross_margins > 0.60:
            tech_risk_score += 3  # 高毛利=护城河
        if context.debt_ratio < 0.40:
            tech_risk_score += 2  # 低负债=可持续创新
        elif context.debt_ratio > 0.70:
            tech_risk_score -= 2
        factors["tech_risk"] = min(max(tech_risk_score, 0), 10)

        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.80, 0.4 + factors["disruption_score"] / 20)

        key_findings = []
        risks = []

        if factors["disruption_score"] >= 7:
            key_findings.append(f"核心破坏性技术属性强（行业:{context.sector}）")
        if context.revenue_growth > 0.30:
            key_findings.append(f"收入增速{context.revenue_growth*100:.0f}%，S曲线快速扩张期")
        if factors["disruption_score"] < 5:
            risks.append("行业属性非ARK核心覆盖范围，破坏性有限")
        if context.ps > 25:
            risks.append(f"PS={context.ps:.1f}偏高，高增长预期已充分定价")

        # 5年目标价估算（Wright定律）
        five_yr_target = context.price * (1 + context.revenue_growth) ** 5 if context.revenue_growth > 0 else 0

        # 模型适用性：ARK框架对非颠覆性行业失效
        if factors["disruption_score"] >= 7:
            coverage_confidence = 1.0
        elif factors["disruption_score"] >= 5:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.35

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**破坏性技术评分: {factors['disruption_score']}/10**
- 行业: {context.sector} / {context.industry}
- 毛利率: {context.gross_margins*100:.1f}% {'✓ 技术溢价' if context.gross_margins > 0.60 else ''}

**ARK框架 (5年年化>15%可能性): {factors['ark_framework']}/10**
- 当前收入增速: {context.revenue_growth*100:.1f}%
- Wright定律5年目标价估算: ${five_yr_target:.0f} {'(+' + f'{(five_yr_target/context.price-1)*100:.0f}%' + ')' if five_yr_target and context.price else ''}

**创新扩散曲线: {factors['innovation_diffusion']}/10**
- {'🚀 S曲线早期快速扩张' if context.revenue_growth > 0.50 else '📈 成长加速中' if context.revenue_growth > 0.30 else '📊 成熟稳定'}

**市场空间TAM: {factors['tam_size']}/10**
- PS: {context.ps:.1f}
- 市值: {context.market_cap:.1f}B

**技术风险: {factors['tech_risk']}/10**
- 毛利率: {context.gross_margins*100:.1f}%
- 负债率: {context.debt_ratio*100:.1f}%

**综合评分: {total_score:.1f}/10**
破坏式创新结论：{'重仓颠覆者，5年视野' if avg_score >= bullish_th else '创新叙事不足，观望' if avg_score <= bearish_th else '中性，等待S曲线加速'}
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
