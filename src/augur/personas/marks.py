# -*- coding: utf-8 -*-
"""
MarksAgent - Howard Marks 市场情绪钟摆
"""

from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class MarksAgent(BaseAgent):
    """Howard Marks - 市场情绪钟摆"""

    def __init__(self):
        super().__init__(
            agent_id="marks",
            name="Howard Marks",
            identity="""市场情绪钟摆理论大师，强调风险与价格成正比，恐惧时买入、贪婪时卖出。
                        二阶思维：多数人的判断已经反映在价格里，需要超越共识。""",
            philosophy=["情绪钟摆", "二阶思维", "风险定价", "困境资产"],
            scoring_weights={
                "pendulum_position": 0.25,
                "risk_pricing": 0.25,
                "second_level_thinking": 0.25,
                "distressed_discount": 0.25,
            },
            thresholds={
                "bullish_threshold": 6.5,
                "bearish_threshold": 4.0,
            },
            biases={
                "contrarian": True,
                "risk_focused": True,
                "distressed_preference": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是Howard Marks，Oaktree Capital联合创始人，情绪钟摆理论创始人。

核心理念：
1. 市场情绪在恐惧和贪婪之间摆动，绝不会停在中间
2. 风险不是波动，而是永久亏损的可能性——当资产价格偏高时风险最大
3. 二阶思维：问"别人认为X，但我认为Y，因为Z"
4. 最好的买入时机是大多数人害怕买入时

名言：
- "Being too far ahead of your time is indistinguishable from being wrong"
- "The most dangerous thing is to buy when things are at their best"
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Marks情绪钟摆分析"""
        factors = {}

        # 1. 情绪钟摆位置 (0-10): 判断当前在恐惧端还是贪婪端
        # PE与历史均值比较（用25作为全市场历史均值代理）
        hist_pe_avg = 25.0
        pendulum_score = 5
        if context.pe > 0:
            pe_ratio = context.pe / hist_pe_avg
            if pe_ratio < 0.60:  # PE < 历史40%分位
                pendulum_score = 9  # 钟摆在恐惧端（好买点）
            elif pe_ratio < 0.80:
                pendulum_score = 7
            elif pe_ratio > 1.40:  # PE > 历史140%分位
                pendulum_score = 2  # 钟摆在贪婪端（危险）
            elif pe_ratio > 1.20:
                pendulum_score = 4
        # RSI辅助
        if context.rsi < 30:
            pendulum_score = min(pendulum_score + 2, 10)
        elif context.rsi > 70:
            pendulum_score = max(pendulum_score - 2, 0)
        factors["pendulum_position"] = pendulum_score

        # 2. 风险定价 (0-10): 低IV+高PE=风险被低估=危险；高IV+低PE=机会
        risk_price_score = 5
        # 用volatility_20d代理隐含波动率
        iv_proxy = context.volatility_20d if context.volatility_20d > 0 else 0.20
        if iv_proxy > 0.35 and (context.pe < 20 or context.pe == 0):
            risk_price_score = 9  # 高恐慌+低估值=风险被高估=机会
        elif iv_proxy < 0.15 and context.pe > 30:
            risk_price_score = 2  # 低恐慌+高估值=风险被低估=危险
        elif iv_proxy > 0.25:
            risk_price_score += 2
        elif iv_proxy < 0.20:
            risk_price_score -= 2
        factors["risk_pricing"] = min(max(risk_price_score, 0), 10)

        # 3. 二阶思维 (0-10): 多数人的判断是否已反映在价格里
        second_level_score = 5
        if context.short_interest > 0.10:
            second_level_score += 3  # 高空头=共识做空=可能反向
        if context.institutional_ownership > 75:
            second_level_score -= 2  # 机构高持股=共识看多=已定价
        elif context.institutional_ownership < 30:
            second_level_score += 2  # 机构低持股=被忽视
        if context.price_vs_52w_high < -25:
            second_level_score += 2  # 深度回撤=市场悲观=逆向机会
        factors["second_level_thinking"] = min(max(second_level_score, 0), 10)

        # 4. 困境折价 (0-10): 高质量资产是否在打折出售
        distressed_score = 5
        if context.pb > 0:
            if context.pb < 1.0 and context.roe > 0.10:
                distressed_score = 9  # PB<1且ROE正 = 优质困境
            elif context.pb < 1.5 and context.gross_margins > 0.30:
                distressed_score = 7
            elif context.pb > 4.0:
                distressed_score = 2
        if context.debt_ratio > 0.80:
            distressed_score -= 2  # 高负债降低质量
        factors["distressed_discount"] = min(max(distressed_score, 0), 10)

        bullish_th = self.thresholds.get("bullish_threshold", 6.5)
        bearish_th = self.thresholds.get("bearish_threshold", 4.0)

        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.85, 0.5 + factors["risk_pricing"] / 20)

        key_findings = []
        risks = []

        if factors["pendulum_position"] >= 7:
            key_findings.append("情绪钟摆偏向恐惧端，历史上的买入良机")
        if factors["risk_pricing"] >= 8:
            key_findings.append("风险溢价偏高，市场高估了风险")
        if factors["pendulum_position"] <= 3:
            risks.append("情绪钟摆偏向贪婪端，风险未被充分定价")
        if context.pe > 35:
            risks.append(f"PE={context.pe:.1f}偏高，二阶思维提示当心过度乐观")

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**情绪钟摆位置: {factors['pendulum_position']}/10**
- PE: {context.pe:.1f} vs 历史均值 {hist_pe_avg} {'（恐惧端）' if context.pe < hist_pe_avg*0.8 else '（贪婪端）' if context.pe > hist_pe_avg*1.3 else '（中性）'}
- RSI: {context.rsi:.1f}

**风险定价: {factors['risk_pricing']}/10**
- 波动率代理(IV): {context.volatility_20d*100:.1f}%
- {'⚠️ 低恐慌+高估值=危险' if context.volatility_20d < 0.20 and context.pe > 30 else '✓ 风险溢价合理'}

**二阶思维: {factors['second_level_thinking']}/10**
- 空头比例: {context.short_interest*100:.1f}%
- 机构持股: {context.institutional_ownership:.1f}%
- 距52周高点: {context.price_vs_52w_high:.1f}%

**困境折价: {factors['distressed_discount']}/10**
- P/B: {context.pb:.2f}
- ROE: {context.roe*100:.1f}%

**综合评分: {total_score:.1f}/10**
钟摆判断：{'恐惧端 — 买入区间' if avg_score >= self.thresholds.get('bullish_threshold', 6.5) else '贪婪端 — 谨慎' if avg_score <= self.thresholds.get('bearish_threshold', 4.0) else '中性区间'}
"""

        # 模型适用性：Marks周期/情绪框架，需要波动率+估值+情绪数据
        if context.volatility_20d > 0 and (context.pe > 0 or context.rsi > 0):
            coverage_confidence = 1.0
        elif context.rsi > 0 or context.short_interest > 0:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.5  # 无市场情绪信号，周期判断受限

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
