# -*- coding: utf-8 -*-
"""
SorosAgent - George Soros 反身性理论
"""

from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class SorosAgent(BaseAgent):
    """George Soros - 反身性理论"""

    def __init__(self):
        super().__init__(
            agent_id="soros",
            name="George Soros",
            identity="""反身性理论大师，强调市场偏见与价格趋势之间的双向反馈回路。
                        市场参与者的偏见影响价格，价格变化又强化偏见，直到趋势自我颠覆。""",
            philosophy=["反身性", "市场偏见", "趋势加速", "自我颠覆"],
            scoring_weights={
                "market_bias": 0.20,
                "trend_reinforcement": 0.20,
                "inflection_condition": 0.20,
                "liquidity": 0.20,
                "exit_signal": 0.20,
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
            },
            biases={
                "reflexivity": True,
                "macro_driven": True,
                "high_beta_preference": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是George Soros，反身性理论的创造者。
反身性理论：市场参与者的偏见（认知缺陷）影响价格，价格变化反过来又强化偏见，
形成自我强化的趋势，直到趋势与现实偏差过大而自我颠覆。

核心原则：
1. 寻找强烈的市场主流偏见
2. 判断偏见是否处于自我强化阶段（价格上涨→更多买入）
3. 识别颠覆该偏见的潜在触发因素
4. "我比别人更不理性，所以我能预见到大众的疯狂"

名言：
- "Markets are always biased in one direction or another"
- "When I see a bubble forming, I rush in to buy, adding fuel to the fire"
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Soros反身性分析"""
        bullish_th = self.thresholds.get("bullish_threshold", 7.0)
        bearish_th = self.thresholds.get("bearish_threshold", 4.0)
        factors = {}

        # 1. 市场偏见识别 (0-10): PE偏高=强烈偏见存在
        bias_score = 5
        if context.pe > 40:
            bias_score += 3  # 高PE=强烈乐观偏见
        elif context.pe > 25:
            bias_score += 1
        elif context.pe < 15 and context.pe > 0:
            bias_score -= 2  # 低PE=悲观偏见
        # 高波动率也反映偏见
        if context.volatility_20d > 0.30:
            bias_score += 1
        factors["market_bias"] = min(max(bias_score, 0), 10)

        # 2. 趋势强化阶段 (0-10): 高增长+动能=自我强化
        reinforce_score = 5
        if context.revenue_growth > 0.50:
            reinforce_score += 3  # 超高成长=强化阶段
        elif context.revenue_growth > 0.20:
            reinforce_score += 1
        if context.macd > context.macd_signal:
            reinforce_score += 2  # MACD金叉=动能强化
        factors["trend_reinforcement"] = min(max(reinforce_score, 0), 10)

        # 3. 拐点条件 (0-10): 是否存在反转触发因素
        inflection_score = 5
        if context.rsi > 75:
            inflection_score -= 3  # 超买=拐点风险
        elif context.rsi < 30:
            inflection_score += 3  # 超卖=反弹可能
        if context.price_vs_52w_high > -5:
            inflection_score -= 2  # 接近高点=颠覆风险高
        elif context.price_vs_52w_high < -30:
            inflection_score += 2  # 深度超卖=反身性上行
        factors["inflection_condition"] = min(max(inflection_score, 0), 10)

        # 4. 流动性条件 (0-10): 宏观流动性
        liquidity_score = 5
        if context.market_cap > 100:
            liquidity_score += 2  # 大市值=流动性充裕
        if context.beta_1y > 1.2:
            liquidity_score += 1  # 高beta=宏观驱动
        elif context.beta_1y < 0.5:
            liquidity_score -= 1  # 低beta=宏观影响小
        if context.short_interest > 0.10:
            liquidity_score += 2  # 高空头=轧空潜力
        factors["liquidity"] = min(max(liquidity_score, 0), 10)

        # 5. 退出信号 (0-10): 趋势是否开始自我矛盾
        exit_score = 5
        if context.rsi > 80:
            exit_score -= 3  # 极度超买=退出信号
        elif context.rsi < 25:
            exit_score += 3  # 极度超卖=入场信号
        if context.macd_histogram < 0 and context.macd > 0:
            exit_score -= 2  # MACD顶部背离
        factors["exit_signal"] = min(max(exit_score, 0), 10)

        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.85, 0.5 + factors["trend_reinforcement"] / 20)

        key_findings = []
        risks = []

        if context.revenue_growth > 0.50:
            key_findings.append(f"收入增速{context.revenue_growth*100:.0f}%，趋势强化阶段")
        if context.rsi > 75:
            risks.append(f"RSI={context.rsi:.0f}，超买信号，趋势自我颠覆风险")
        if context.pe > 40:
            key_findings.append(f"PE={context.pe:.1f}，市场乐观偏见强烈，反身性趋势形成中")

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**市场偏见强度: {factors['market_bias']:.1f}/10**
- PE: {context.pe:.1f} {'（高估值=强烈偏见）' if context.pe > 30 else ''}
- 20日波动率: {context.volatility_20d*100:.1f}%

**趋势强化阶段: {factors['trend_reinforcement']:.1f}/10**
- 收入增速: {context.revenue_growth*100:.1f}% {'✓ 强化中' if context.revenue_growth > 0.30 else ''}
- MACD: {'金叉' if context.macd > context.macd_signal else '死叉'}

**拐点条件: {factors['inflection_condition']:.1f}/10**
- RSI: {context.rsi:.1f} {'⚠️ 超买' if context.rsi > 75 else '⚠️ 超卖' if context.rsi < 30 else '中性'}
- 距52周高点: {context.price_vs_52w_high:.1f}%

**流动性条件: {factors['liquidity']:.1f}/10**
- 市值: {context.market_cap:.1f}B
- Beta: {context.beta_1y:.2f}

**退出信号: {factors['exit_signal']:.1f}/10**
- MACD柱: {context.macd_histogram:.3f}

**综合评分: {total_score:.1f}/10**
反身性判断：{'趋势仍在自我强化' if avg_score >= bullish_th else '接近自我颠覆拐点' if avg_score <= bearish_th else '趋势中性'}
"""

        # 模型适用性：Soros反身性需要RSI+动量数据；无技术信号时难以判断偏见强度
        if context.rsi > 0 and context.price_vs_52w_high != 0:
            coverage_confidence = 0.9
        elif context.rsi > 0:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.4  # 无动量信号，反身性框架缺乏锚点

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
