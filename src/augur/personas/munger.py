# -*- coding: utf-8 -*-
"""
MungerAgent - Charlie Munger 逆向投资/心理学
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class MungerAgent(BaseAgent):
    """Charlie Munger - 逆向投资/心理学"""

    def __init__(self):
        super().__init__(
            agent_id="munger",
            name="Charlie Munger",
            identity="""逆向投资大师，强调心理学误判、超级选择性、耐心等待、
                        Lollapalooza效应。偏好反共识思维。""",
            philosophy=["逆向投资", "心理学误判", "Lollapalooza", "超级选择性"],
            scoring_weights={
                "contra_bet": 0.30,        # 逆向程度
                "psychological": 0.25,    # 心理因素
                "selection_rigor": 0.25,  # 选择严格性
                "moat_durability": 0.20,  # 护城河持久性
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
                "roe_min": 0.15,
            },
            biases={
                "contrarian": True,
                "patience_orientation": True,
                "multi_model_thinking": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Munger风格分析"""
        factors = {}
        bullish_threshold = self.thresholds.get("bullish_threshold", 7.0)
        bearish_threshold = self.thresholds.get("bearish_threshold", 4.0)
        roe_min = self.thresholds.get("roe_min", 0.15)

        # 行业专属权重调整（Munger偏好简单易懂的业务）
        sector = context.sector.lower() if context.sector else ""
        if "consumer" in sector or "retail" in sector:
            contra_multiplier = 1.2   # 消费：Munger最爱（可口可乐）
            moat_multiplier = 1.2
        elif "financ" in sector or "bank" in sector or "insur" in sector:
            contra_multiplier = 1.1   # 金融：Munger擅长
            moat_multiplier = 1.1
        elif "biotech" in sector or "pharma" in sector:
            contra_multiplier = 0.8   # 生物医药：复杂，Munger回避
            moat_multiplier = 0.9
        elif "tech" in sector or "software" in sector:
            contra_multiplier = 0.9
            moat_multiplier = 1.1   # 科技护城河可能很宽
        else:
            contra_multiplier = 1.0
            moat_multiplier = 1.0

        # 1. 逆向程度
        contra_score = 5
        if context.price_vs_52w_high < -30:  # 跌超30%
            contra_score += 4  # 深度超卖，可能是逆向机会
        elif context.price_vs_52w_high < -20:
            contra_score += 2

        if context.institutional_ownership < 30:
            contra_score += 1  # 机构低持股，可能被忽视

        if context.rsi < 35:
            contra_score += 2  # 技术超卖
        factors["contra_bet"] = min(max(contra_score * contra_multiplier, 0), 10)

        # 2. 心理因素 - 波动率作为市场情绪代理
        psych_score = 5
        if context.price and context.atr/context.price*100 > 3:
            psych_score += 2  # 高波动反映恐惧
        if context.price_vs_52w_low < 10:  # 接近低点
            psych_score += 1
        factors["psychological"] = min(max(psych_score, 0), 10)

        # 3. 选择严格性 - 用PE和增长匹配度
        rigor_score = 5
        if context.pe > 0 and context.earnings_growth > 0:
            peg = context.pe / (context.earnings_growth * 100)
            if peg < 1.5:
                rigor_score += 3  # 增长被低估
        if context.roe > roe_min:
            rigor_score += 2  # ROE达标
        factors["selection_rigor"] = min(max(rigor_score, 0), 10)

        # 4. 护城河持久性
        moat_score = 5
        if context.gross_margins > 0.40:
            moat_score += 3
        if context.debt_ratio < 0.50:
            moat_score += 2
        factors["moat_durability"] = min(max(moat_score * moat_multiplier, 0), 10)

        total_score = sum(factors.values()) / len(factors)
        if total_score >= bullish_threshold:
            signal = SignalType.BULLISH
        elif total_score <= bearish_threshold:
            signal = SignalType.BEARISH
        else:
            signal = SignalType.NEUTRAL
        confidence = 0.5 + (factors["contra_bet"] - 5) / 20

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**逆向程度: {factors['contra_bet']}/10**
- 距52周高点: {context.price_vs_52w_high:.1f}% {'✓ 超卖' if context.price_vs_52w_high < -20 else ''}
- 机构持股: {context.institutional_ownership:.1f}% {'低持股' if context.institutional_ownership < 30 else ''}
- RSI: {context.rsi:.1f}

**心理因素: {factors['psychological']}/10**
- ATR/价格: {f"{context.atr/context.price*100:.2f}%" if context.price else "N/A"}
- 距52周低点: {context.price_vs_52w_low:.1f}%

**选择严格性: {factors['selection_rigor']}/10**
- ROE: {context.roe*100:.1f}% {'✓' if context.roe > roe_min else '✗'}
- PEG: {context.pe/(context.earnings_growth*100) if context.pe and context.earnings_growth else 'N/A'}

**护城河持久性: {factors['moat_durability']}/10**
- 毛利率: {context.gross_margins*100:.1f}%
- 负债率: {context.debt_ratio*100:.1f}%

**综合评分: {total_score:.1f}/10**
投资哲学：{' + '.join(self.philosophy[:2])}
"""

        key_findings = []
        risks = []

        if factors["contra_bet"] >= 7:
            key_findings.append("深度逆向机会")
        if context.price_vs_52w_high < -30:
            key_findings.append("距高点跌超30%，可能过度悲观")

        # 模型适用性：Munger专注质量+护城河，需要ROE和FCF可见
        if context.roe > 0.10 and context.fcf > 0:
            coverage_confidence = 1.0
        elif context.gross_margins > 0.30:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.4  # 质量指标缺失，逆向博弈框架受限

        return AgentResponse(
            agent_id=self.agent_id,
            agent_name=self.name,
            signal=signal,
            confidence=min(0.90, confidence),
            score=total_score,
            reasoning=reasoning,
            key_findings=key_findings,
            risks=risks,
            metadata={"factors": factors, "philosophy": self.philosophy},
            coverage_confidence=coverage_confidence,
        )
