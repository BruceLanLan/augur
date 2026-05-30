# -*- coding: utf-8 -*-
"""
FisherAgent - Philip Fisher 成长股质地
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class FisherAgent(BaseAgent):
    """Philip Fisher - 成长股质地"""

    def __init__(self):
        super().__init__(
            agent_id="fisher",
            name="Philip Fisher",
            identity="""成长股投资开创者，强调Scuttlebutt调研法（走访行业关系网络），
                        管理层质量、研发投入、销售组织、利润率持续性比财务数字更重要。
                        买入伟大公司，长期持有20年。""",
            philosophy=["Scuttlebutt", "管理层质量", "利润率持续性", "长期持有"],
            scoring_weights={
                "scuttlebutt": 0.20,
                "management_quality": 0.20,
                "sales_organization": 0.20,
                "margin_sustainability": 0.20,
                "growth_durability": 0.20,
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
                "roe_min": 0.15,
            },
            biases={
                "quality_growth": True,
                "long_term": True,
                "management_focused": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是Philip Fisher，《怎样选择成长股》作者，成长股投资之父。

核心理念：
1. Scuttlebutt方法：通过供应商、竞争对手、客户、前员工了解公司真实情况
2. 管理层诚信和能力是最重要的非财务指标
3. 利润率的持续提升是伟大公司的标志
4. 仅当公司基本面恶化时才卖出，绝不因短期下跌卖出

名言：
- "I don't want a lot of good investments; I want a few outstanding ones"
- "The stock market is filled with individuals who know the price of everything, but the value of nothing"
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Fisher Scuttlebutt成长股分析"""
        factors = {}

        # 1. Scuttlebutt信号代理 (0-10)
        # 用revenue_growth稳定性 + gross_margins趋势代理员工/客户满意度
        scutt_score = 5
        if context.gross_margins > 0.50:
            scutt_score += 3  # 高毛利=客户忠诚=pricing power
        elif context.gross_margins > 0.35:
            scutt_score += 1
        if context.revenue_growth > 0.15:
            scutt_score += 2  # 稳定增长=客户持续复购
        factors["scuttlebutt"] = min(max(scutt_score, 0), 10)

        # 2. 管理层质量代理 (0-10)
        # R&D强度代理（若无数据则用高毛利率+低负债代理优秀资本配置）
        mgmt_score = 5
        roe_min = self.thresholds.get("roe_min", 0.15)
        roe_strong = roe_min + 0.05
        if context.roe > roe_strong:
            mgmt_score += 3  # 高ROE=优秀资本配置
        elif context.roe > roe_min:
            mgmt_score += 1
        if context.debt_ratio < 0.40:
            mgmt_score += 2  # 低负债=保守财务管理
        elif context.debt_ratio > 0.70:
            mgmt_score -= 2
        if context.institutional_ownership > 60:
            mgmt_score += 1  # 机构认可管理层
        factors["management_quality"] = min(max(mgmt_score, 0), 10)

        # 3. 销售组织力 (0-10)
        # 收入增速稳定性 + 毛利率
        sales_score = 5
        if context.revenue_growth > 0.25:
            sales_score += 4  # 强销售组织=高速增长
        elif context.revenue_growth > 0.10:
            sales_score += 2
        elif context.revenue_growth < 0:
            sales_score -= 2
        if context.operating_margins > 0.20:
            sales_score += 1  # 高营业利润=销售效率高
        factors["sales_organization"] = min(max(sales_score, 0), 10)

        # 4. 利润率持续性 (0-10)
        margin_score = 5
        if context.gross_margins > 0.50:
            margin_score += 4  # 强定价权
        elif context.gross_margins > 0.35:
            margin_score += 2
        elif context.gross_margins < 0.20:
            margin_score -= 2
        if context.operating_margins > 0.15:
            margin_score += 1
        factors["margin_sustainability"] = min(max(margin_score, 0), 10)

        # 5. 成长持续性 (0-10)
        growth_dur_score = 5
        if context.earnings_growth > 0.20:
            growth_dur_score += 3
        elif context.earnings_growth > 0.10:
            growth_dur_score += 1
        elif context.earnings_growth < 0:
            growth_dur_score -= 2
        if context.fcf > 0:
            growth_dur_score += 2  # 有自由现金流=可持续
        factors["growth_durability"] = min(max(growth_dur_score, 0), 10)

        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.85, 0.5 + factors["margin_sustainability"] / 20)

        key_findings = []
        risks = []

        if context.gross_margins > 0.50:
            key_findings.append(f"毛利率{context.gross_margins*100:.0f}%，强定价权和客户忠诚")
        if context.roe > roe_min + 0.05:
            key_findings.append(f"ROE={context.roe*100:.0f}%，管理层资本配置能力突出(>{roe_min*100:.0f}%)")
        if context.revenue_growth < 0.10:
            risks.append(f"收入增速仅{context.revenue_growth*100:.0f}%，成长持续性存疑")
        if context.gross_margins < 0.25:
            risks.append("毛利率偏低，定价权不足，非Fisher理想标的")

        roe_strong = roe_min + 0.05
        reasoning = f"""## {self.name} Analysis for {context.ticker}

**Scuttlebutt信号: {factors['scuttlebutt']}/10**
- 毛利率(客户忠诚代理): {context.gross_margins*100:.1f}% {'✓' if context.gross_margins > 0.40 else '✗'}
- 收入增速稳定性: {context.revenue_growth*100:.1f}%

**管理层质量: {factors['management_quality']}/10**
- ROE: {context.roe*100:.1f}% {'✓ 优秀' if context.roe > roe_strong else '一般'}
- 负债率: {context.debt_ratio*100:.1f}% {'✓ 保守' if context.debt_ratio < 0.40 else '偏高'}

**销售组织力: {factors['sales_organization']}/10**
- 收入增速: {context.revenue_growth*100:.1f}%
- 营业利润率: {context.operating_margins*100:.1f}%

**利润率持续性: {factors['margin_sustainability']}/10**
- 毛利率: {context.gross_margins*100:.1f}% {'✓ 强定价权' if context.gross_margins > 0.50 else ''}
- 营业利润率: {context.operating_margins*100:.1f}%

**成长持续性: {factors['growth_durability']}/10**
- 盈利增速: {context.earnings_growth*100:.1f}%
- FCF: {'正向 ✓' if context.fcf > 0 else '负向 ✗'}

**综合评分: {total_score:.1f}/10**
Fisher结论：{'值得长期持有20年' if avg_score >= self.thresholds.get('bullish_threshold', 7.0) else '尚不达标，持续观察' if avg_score > self.thresholds.get('bearish_threshold', 4.0) else '不符合成长股质地要求'}
"""

        # 模型适用性：Fisher需要成长性数据（收入增长+毛利率）可见
        if context.revenue_growth > 0 and context.gross_margins > 0 and context.earnings_growth >= 0:
            coverage_confidence = 1.0
        elif context.revenue_growth > 0 or context.earnings_growth > 0:
            coverage_confidence = 0.6
        else:
            coverage_confidence = 0.4  # 无成长数据，15点检验缺乏量化支撑

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
