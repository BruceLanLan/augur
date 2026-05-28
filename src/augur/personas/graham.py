# -*- coding: utf-8 -*-
"""
GrahamAgent - Benjamin Graham 深度价值/安全边际
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class GrahamAgent(BaseAgent):
    """Benjamin Graham - 深度价值/安全边际"""

    def __init__(self):
        super().__init__(
            agent_id="graham",
            name="Benjamin Graham",
            identity="""深度价值投资之父，强调清算价值、安全边际、低PE、
                        强资产负债表。偏好困境公司和高防御性。""",
            philosophy=["安全边际", "清算价值", "低PE", "资产负债表强度"],
            scoring_weights={
                "valuation": 0.35,      # 估值（PE/PB）
                "margin_of_safety": 0.25,  # 安全边际
                "balance_sheet": 0.20,  # 资产负债表
                "earnings_stability": 0.20,  # 盈利稳定性
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
                "pe_max": 15,
                "pb_max": 1.5,
                "current_ratio_min": 2.0,
            },
            biases={
                "deep_value_orientation": True,
                "cigar_but_stocks": True,
                "statistical_value": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Graham风格分析"""
        factors = {}

        pe_max = self.thresholds.get("pe_max", 15)
        pb_max = self.thresholds.get("pb_max", 1.5)
        current_ratio_min = self.thresholds.get("current_ratio_min", 2.0)

        # 行业专属权重调整
        sector = context.sector.lower() if context.sector else ""
        if "bank" in sector or "financ" in sector or "insur" in sector:
            val_multiplier = 1.4   # 金融业：PE/PB最重要
            bs_multiplier = 0.8
        elif "reit" in sector or "real estate" in sector:
            val_multiplier = 1.3
            bs_multiplier = 0.9
        elif "tech" in sector or "software" in sector:
            val_multiplier = 0.7   # 科技：PE通常高，调低权重
            bs_multiplier = 1.2
        elif "energy" in sector or "util" in sector:
            val_multiplier = 1.2
            bs_multiplier = 1.1
        else:
            val_multiplier = 1.0
            bs_multiplier = 1.0

        # 1. 估值 (0-10)
        val_score = 0
        if context.pe > 0:
            if context.pe <= pe_max * 0.67:
                val_score = 10
            elif context.pe <= pe_max:
                val_score = 7
            elif context.pe <= pe_max * 1.33:
                val_score = 5
            elif context.pe <= pe_max * 2:
                val_score = 3
            else:
                val_score = 1
        factors["valuation"] = min(val_score * val_multiplier, 10)

        # 2. 安全边际 (0-10) - PB作为主要指标
        mos_score = 5
        if context.pb > 0:
            if context.pb <= pb_max * 0.67:
                mos_score = 10
            elif context.pb <= pb_max:
                mos_score = 7
            elif context.pb <= pb_max * 1.33:
                mos_score = 5
            elif context.pb <= pb_max * 2:
                mos_score = 3
            else:
                mos_score = 1
        factors["margin_of_safety"] = mos_score

        # 3. 资产负债表 (0-10)
        bs_score = 5
        if context.current_ratio >= current_ratio_min:
            bs_score += 3
        elif context.current_ratio >= current_ratio_min * 0.75:
            bs_score += 1
        if context.debt_ratio < 0.50:
            bs_score += 2
        elif context.debt_ratio > 0.70:
            bs_score -= 2
        factors["balance_sheet"] = min(bs_score * bs_multiplier, 10)

        # 4. 盈利稳定性 (0-10)
        earn_score = 5
        if context.revenue_growth > 0:
            earn_score += 2
        if context.earnings_growth > 0:
            earn_score += 2
        if context.debt_ratio < 0.50:
            earn_score += 1
        factors["earnings_stability"] = min(earn_score, 10)

        # 计算综合评分 - 只使用factors中存在的因子
        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.90, 0.5 + factors["margin_of_safety"] / 20)

        # 生成推理
        reasoning = self._generate_reasoning(context, factors, total_score)

        # 关键发现
        key_findings = []
        risks = []

        if context.pe <= pe_max and context.pe > 0:
            key_findings.append(f"PE偏低({context.pe:.1f})，符合Graham标准(≤{pe_max})")
        if context.pb <= pb_max and context.pb > 0:
            key_findings.append(f"PB偏低({context.pb:.2f})，资产价值被低估(≤{pb_max})")
        if context.current_ratio >= current_ratio_min:
            key_findings.append(f"流动比率优秀({context.current_ratio:.1f})")
        if context.debt_ratio > 0.70:
            risks.append(f"负债率偏高({context.debt_ratio*100:.0f}%)")

        # 模型适用性：Graham需要清晰的PE+PB+流动比率
        if context.pe > 0 and context.pb > 0 and context.current_ratio > 0:
            coverage_confidence = 1.0
        elif context.pe > 0:
            coverage_confidence = 0.6
        else:
            coverage_confidence = 0.3  # 亏损或高增长股，Graham安全边际框架失效

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
        pe_max = self.thresholds.get("pe_max", 15)
        pb_max = self.thresholds.get("pb_max", 1.5)
        current_ratio_min = self.thresholds.get("current_ratio_min", 2.0)
        pe_str = f'{context.pe:.1f}' if context.pe and context.pe > 0 else 'N/A'
        pb_str = f'{context.pb:.2f}' if context.pb and context.pb > 0 else 'N/A'
        ps_str = f'{context.ps:.2f}' if context.ps and context.ps > 0 else 'N/A'
        cr_str = f'{context.current_ratio:.2f}' if context.current_ratio else 'N/A'
        qr_str = f'{context.quick_ratio:.2f}' if context.quick_ratio else 'N/A'

        return f"""## {self.name} Analysis for {context.ticker}

**估值: {factors['valuation']}/10**
- PE: {pe_str} {'✓ 达标' if context.pe and context.pe <= pe_max else '✗ 偏高'}
- PS: {ps_str}

**安全边际: {factors['margin_of_safety']}/10**
- P/B: {pb_str} {'✓ 达标' if context.pb and context.pb <= pb_max else '✗'}

**资产负债表: {factors['balance_sheet']}/10**
- 流动比率: {cr_str} {'✓' if context.current_ratio and context.current_ratio >= current_ratio_min else '✗'}
- 速动比率: {qr_str}
- 负债率: {context.debt_ratio*100:.1f}% {'✓ 低负债' if context.debt_ratio and context.debt_ratio < 0.50 else '✗ 偏高'}

**盈利稳定性: {factors['earnings_stability']}/10**
- 收入增长: {context.revenue_growth*100:.1f}%
- 盈利增长: {context.earnings_growth*100:.1f}%

**综合评分: {total_score:.1f}/10**
投资哲学：{' + '.join(self.philosophy[:2])}
"""
