# -*- coding: utf-8 -*-
"""
LynchAgent - Peter Lynch 成长投资(GARP)
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse


class LynchAgent(BaseAgent):
    """Peter Lynch - 成长投资 GARP"""

    def __init__(self):
        super().__init__(
            agent_id="lynch",
            name="Peter Lynch",
            identity="""成长投资大师，强调PEG比率、盈利增长、业务可理解性、
                        十倍股寻找。偏好日常生活中能接触到的公司。""",
            philosophy=["PEG比率", "盈利增长", "业务可理解性", "十倍股"],
            scoring_weights={
                "growth": 0.30,            # 成长性
                "peg": 0.25,               # PEG合理性
                "quality": 0.25,           # 业务质量
                "understandability": 0.20,  # 可理解性
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
                "peg_max": 1.5,
                "growth_min": 0.15,
            },
            biases={
                "growth_orientation": True,
                "small_caps_preferred": False,
                "narrative_investing": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Lynch风格分析"""
        factors = {}

        try:
            from scanner.agent_hyperparams import load_optimized_thresholds
            opt = load_optimized_thresholds(self.agent_id)
            if opt:
                self.thresholds.update(opt)
        except Exception:
            pass

        # 行业专属权重调整
        sector = context.sector.lower() if context.sector else ""
        if "consumer" in sector or "retail" in sector or "restaurant" in sector:
            growth_multiplier = 1.3   # 消费：Lynch最偏好的行业
            peg_multiplier = 1.2
        elif "tech" in sector or "software" in sector:
            growth_multiplier = 1.2
            peg_multiplier = 0.9   # 科技PEG通常偏高
        elif "biotech" in sector or "health" in sector:
            growth_multiplier = 1.4
            peg_multiplier = 0.8   # 生物医药增长难预测
        elif "util" in sector or "energy" in sector:
            growth_multiplier = 0.7
            peg_multiplier = 1.1
        else:
            growth_multiplier = 1.0
            peg_multiplier = 1.0

        growth_min = self.thresholds.get("growth_min", 0.15)

        # 1. 成长性 (0-10) — growth_min tunes 10x-adjacent bar
        growth_score = 0
        if context.revenue_growth > growth_min + 0.05:
            growth_score += 5
        elif context.revenue_growth > growth_min:
            growth_score += 3
        elif context.revenue_growth > 0:
            growth_score += 1

        earn_bar = growth_min + 0.05 if growth_min < 0.15 else 0.15
        if context.earnings_growth > earn_bar:
            growth_score += 3
        elif context.earnings_growth > 0:
            growth_score += 1

        if context.gross_margins > 0.40:
            growth_score += 2
        factors["growth"] = min(growth_score * growth_multiplier, 10)

        peg_max = self.thresholds.get("peg_max", 1.5)

        # 2. PEG合理性 (0-10)
        peg_score = 5
        if context.pe > 0 and context.earnings_growth >= 0.01:
            peg = context.pe / (context.earnings_growth * 100)
            if peg < peg_max * 0.67:
                peg_score = 10
            elif peg < peg_max:
                peg_score = 7
            elif peg < peg_max * 1.33:
                peg_score = 5
            else:
                peg_score = 3
        factors["peg"] = min(peg_score * peg_multiplier, 10)

        # 3. 业务质量 (0-10)
        quality_score = 5
        if context.gross_margins > 0.40:
            quality_score += 3
        if context.gross_margins > 0.60:
            quality_score += 2
        if context.operating_margins > 0.20:
            quality_score += 2
        if context.roe > 0.15:
            quality_score += 1
        factors["quality"] = min(quality_score, 10)

        # 4. 可理解性 (0-10) - 用市值作为代理
        understand_score = 5
        if context.market_cap < 10:
            understand_score += 3
        elif context.market_cap > 100:
            understand_score -= 1
        factors["understandability"] = min(understand_score, 10)

        # 计算综合评分 - 只使用factors中存在的因子
        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.90, 0.5 + factors["growth"] / 20)

        # 生成推理
        reasoning = self._generate_reasoning(context, factors, total_score)

        # 关键发现
        key_findings = []
        risks = []

        if context.revenue_growth > growth_min + 0.05:
            key_findings.append(
                f"收入增长强劲({context.revenue_growth*100:.0f}%, bar>{growth_min*100:.0f}%)"
            )
        if context.earnings_growth > context.revenue_growth:
            key_findings.append("盈利增长超过收入增长（正向经营杠杆）")
        if context.pe > 0 and context.earnings_growth > 0:
            peg = context.pe / (context.earnings_growth * 100)
            if peg < peg_max:
                key_findings.append(f"PEG合理({peg:.2f}, ≤{peg_max})")

        # 模型适用性：Lynch GARP框架需要PEG可计算（有盈利+盈利增长）
        if context.pe > 0 and context.earnings_growth > 0:
            coverage_confidence = 1.0
        elif context.revenue_growth > 0:
            coverage_confidence = 0.6
        else:
            coverage_confidence = 0.4  # 无法计算PEG，成长框架受限

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
        peg_val = None
        if context.pe > 0 and context.earnings_growth > 0:
            peg_val = context.pe / (context.earnings_growth * 100)
        peg_str = f"{peg_val:.2f}" if peg_val else "N/A"
        pe_str = f'{context.pe:.1f}' if context.pe and context.pe > 0 else 'N/A'

        return f"""## {self.name} Analysis for {context.ticker}

**成长性: {factors['growth']}/10**
- 收入增长: {context.revenue_growth*100:.1f}% {'✓ 强劲' if context.revenue_growth > 0.20 else ''}
- 盈利增长: {context.earnings_growth*100:.1f}%
- 毛利率: {context.gross_margins*100:.1f}%

**PEG合理性: {factors['peg']}/10**
- PE: {pe_str}
- PEG: {peg_str} {'✓' if peg_val and peg_val < 1.5 else '✗'}

**业务质量: {factors['quality']}/10**
- 营业利润率: {context.operating_margins*100:.1f}%
- ROE: {context.roe*100:.1f}%

**可理解性: {factors['understandability']}/10**
- 市值: {context.market_cap:.1f}B
- 行业: {context.industry}

**综合评分: {total_score:.1f}/10**
投资哲学：{' + '.join(self.philosophy[:2])}
"""
