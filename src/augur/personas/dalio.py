# -*- coding: utf-8 -*-
"""
DalioAgent - Ray Dalio 全球宏观/风险平价
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class DalioAgent(BaseAgent):
    """Ray Dalio - 全球宏观/风险平价"""

    def __init__(self):
        super().__init__(
            agent_id="dalio",
            name="Ray Dalio",
            identity="""全球宏观投资大师，强调资产分散、风险平价、周期分析、
                        杠杆套利。偏好通过衍生品对冲风险。""",
            philosophy=["风险平价", "全球宏观", "周期分析", "分散化"],
            scoring_weights={
                "macro_outlook": 0.30,     # 宏观前景
                "diversification": 0.25,   # 分散化程度
                "risk_adjusted": 0.25,    # 风险调整后收益
                "liquidity": 0.20,        # 流动性
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
            },
            biases={
                "macro_driven": True,
                "hedging_orientation": True,
                "all_weather": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Dalio风格分析 - 简化为技术指标+趋势"""
        bullish_th = self.thresholds.get("bullish_threshold", 7.0)
        bearish_th = self.thresholds.get("bearish_threshold", 4.0)
        factors = {}

        # 行业专属权重调整（Dalio偏好分散化，但对流动性敏感）
        sector = context.sector.lower() if context.sector else ""
        if "util" in sector or "reit" in sector or "real estate" in sector:
            stability_multiplier = 1.3   # 稳定板块：Dalio偏好
        elif "tech" in sector or "software" in sector:
            stability_multiplier = 0.85  # 科技：高波动需折扣
        elif "energy" in sector or "material" in sector or "commodity" in sector:
            stability_multiplier = 1.1   # 大宗：宏观驱动，Dalio擅长
        elif "financ" in sector or "bank" in sector:
            stability_multiplier = 0.9   # 金融：周期性强
        else:
            stability_multiplier = 1.0

        # 1. 宏观趋势 - 用价格位置代理
        macro_score = 5
        if context.price_vs_52w_high < -20:  # 距高点跌超20%
            macro_score += 3  # 宏观过度悲观
        elif context.price_vs_52w_high > -10:  # 距高点不到10%
            macro_score -= 2  # 充分定价
        if context.rsi < 30:
            macro_score += 2  # 超卖
        elif context.rsi > 70:
            macro_score -= 2  # 超买
        factors["macro_outlook"] = min(max(macro_score, 0), 10)

        # 2. 趋势强度
        trend_score = 5
        if context.macd > context.macd_signal:
            trend_score += 3
        if context.price > context.sma20:
            trend_score += 2
        if context.price > context.sma50:
            trend_score += 2
        else:
            trend_score -= 2
        factors["trend_strength"] = min(max(trend_score, 0), 10)

        # 3. 风险调整 - ATR作为波动率代理
        risk_score = 5
        if context.atr > 0 and context.price > 0:
            atr_pct = context.atr / context.price * 100
            if atr_pct < 2:
                risk_score += 3  # 低波动
            elif atr_pct > 5:
                risk_score -= 3  # 高波动
        factors["risk_adjusted"] = min(max(risk_score * stability_multiplier, 0), 10)

        # 4. 趋势动量
        momentum_score = 5
        if context.macd_histogram > 0:
            momentum_score += 3
        if context.stoch_k < 30:
            momentum_score += 2  # 超卖反弹可能
        elif context.stoch_k > 70:
            momentum_score -= 2  # 超买回调风险
        factors["momentum"] = min(max(momentum_score, 0), 10)

        # 计算综合评分
        total_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(total_score)
        confidence = 0.5 + (factors["trend_strength"] - 5) / 20

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**宏观前景: {factors['macro_outlook']}/10**
- 距52周高点: {context.price_vs_52w_high:.1f}%
- RSI: {context.rsi:.1f} {'超买' if context.rsi > 70 else '超卖' if context.rsi < 30 else '中性'}

**趋势强度: {factors['trend_strength']}/10**
- MACD: {context.macd:.2f} {'✓ 金叉' if context.macd > context.macd_signal else '✗ 死叉'}
- 价格 vs SMA20: {'✓' if context.price > context.sma20 else '✗'}
- 价格 vs SMA50: {'✓' if context.price > context.sma50 else '✗'}

**风险调整: {factors['risk_adjusted']}/10**
- ATR: {context.atr:.2f}
- ATR/价格: {f"{context.atr/context.price*100:.2f}%" if context.price else "N/A"}

**动量: {factors['momentum']}/10**
- Stochastic K: {context.stoch_k:.1f}

**综合评分: {total_score:.1f}/10**
宏观/风险平价结论：{'宏观顺风，可增配' if total_score >= bullish_th else '宏观逆风，降风险敞口' if total_score <= bearish_th else '中性，维持分散'}
投资哲学：{' + '.join(self.philosophy[:2])}
"""

        key_findings = []
        risks = []

        if factors["trend_strength"] >= 7:
            key_findings.append("上升趋势确认")
        if factors["macro_outlook"] >= 7:
            key_findings.append("宏观环境有利")
        if context.macd_histogram > 0:
            key_findings.append("MACD柱状图为正，动能向上")

        # 模型适用性：Dalio宏观+技术框架，技术指标越完整覆盖度越高
        if context.rsi > 0 and context.macd != 0 and context.sma50 > 0:
            coverage_confidence = 0.9
        elif context.rsi > 0 or context.sma50 > 0:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.5  # 无技术指标，仅宏观层面有效

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
