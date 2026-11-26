# -*- coding: utf-8 -*-
"""
SorosAgent - George Soros 反身性理论
"""

from augur.personas.base import BaseAgent, MarketContext, AgentResponse


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

    # ------------------------------------------------------------------
    # v14.1 fund path: called by the BaseAgent guard for ETF / fund contexts
    # instead of ``analyze`` (whose PE / revenue-growth / market-cap rules are
    # company rules).
    # ------------------------------------------------------------------
    def analyze_fund(self, context: MarketContext) -> AgentResponse:
        """Soros 反身性的基金读数：顺势看趋势是否在自我强化，再看是否过热。

        只用价格、均线、MACD、RSI、成交量与 ETF 溢价折价。
        """
        from augur.etf import FUND_READING_BASIS, fund_signal, profile_num
        from augur.personas.base import SignalType

        if self._fund_technicals_missing(context, need_macd=True):
            return self._fund_not_applicable(context, reason="fund_data_missing")

        factors = {}
        price, sma50, sma200 = context.price, context.sma50, context.sma200
        premium = profile_num(context, "premium_pct")

        # 1. 趋势强化：价格与 50/200 日均线的排列 + MACD
        trend = 5
        trend += 1 if price > sma50 else -1
        trend += 1 if price > sma200 else -1
        trend += 2 if sma50 > sma200 else -2
        trend += 1 if context.macd > context.macd_signal else -1
        factors["trend_reinforcement"] = min(max(trend, 0), 10)

        # 2. 动能加速：MACD 柱与短期均线
        # （放量方向需要当日涨跌幅，基金上下文里没有可靠来源，不使用）
        accel = 5
        accel += 2 if context.macd_histogram > 0 else -2
        if context.sma20 > 0:
            accel += 1 if price > context.sma20 else -1
        factors["momentum_acceleration"] = min(max(accel, 0), 10)

        # 3. 拐点条件（与股票规则相同，纯技术）
        inflection = 5
        if context.rsi > 75:
            inflection -= 3
        elif context.rsi < 30:
            inflection += 3
        if context.price_vs_52w_high > -5:
            inflection -= 2
        elif context.price_vs_52w_high < -30:
            inflection += 2
        factors["inflection_condition"] = min(max(inflection, 0), 10)

        # 4. 退出信号：极度超买 / MACD 顶部背离 / 人群溢价追入
        exit_score = 5
        if context.rsi > 80:
            exit_score -= 3
        elif context.rsi < 25:
            exit_score += 3
        if context.macd_histogram < 0 and context.macd > 0:
            exit_score -= 2
        if premium is not None and premium > 1.0:
            exit_score -= 1
        factors["exit_signal"] = min(max(exit_score, 0), 10)

        weights = {"trend_reinforcement": 0.35, "momentum_acceleration": 0.25,
                   "inflection_condition": 0.20, "exit_signal": 0.20}
        score = sum(factors[k] * w for k, w in weights.items())
        signal = SignalType(fund_signal(score))
        confidence = min(0.75, 0.4 + abs(factors["trend_reinforcement"] - 5) / 15)

        key_findings = []
        risks = []
        if factors["trend_reinforcement"] >= 8:
            key_findings.append("基金读数：价格在50/200日均线上方且均线多头排列，趋势在自我强化")
        elif factors["trend_reinforcement"] <= 2:
            risks.append("基金读数：价格在50/200日均线下方且均线空头排列，下行趋势在自我强化")
        elif factors["trend_reinforcement"] <= 4:
            risks.append("基金读数：价格跌破中长期均线或MACD死叉，趋势在走弱")
        if factors["momentum_acceleration"] <= 3:
            risks.append("基金读数：MACD柱为负且价格在20日均线下方，下行动能在加速")
        elif factors["momentum_acceleration"] >= 7:
            key_findings.append("基金读数：MACD柱为正且价格在20日均线上方，上行动能在加速")
        if context.rsi > 75:
            risks.append(f"基金读数：RSI={context.rsi:.0f}，超买，趋势有自我颠覆风险")
        elif context.rsi < 30:
            key_findings.append(f"基金读数：RSI={context.rsi:.0f}，超卖，悲观偏见可能过度")
        if premium is not None and premium > 1.0:
            risks.append(f"基金读数：溢价 {premium:+.2f}%，人群在高于净值追入")
        if not key_findings and not risks:
            key_findings.append("基金读数：趋势信号混杂，未见明确的自我强化")

        premium_txt = f"{premium:+.2f}%" if premium is not None else "未知"
        verdict = ("趋势仍在自我强化" if signal == SignalType.BULLISH
                   else "趋势向下或接近自我颠覆" if signal == SignalType.BEARISH else "趋势中性")
        reasoning = f"""## {self.name} 基金读数 for {context.ticker}


**趋势强化: {factors['trend_reinforcement']}/10**
- 价格 vs SMA50: {'✓' if price > sma50 else '✗'}，价格 vs SMA200: {'✓' if price > sma200 else '✗'}
- SMA50 vs SMA200: {'多头排列' if sma50 > sma200 else '空头排列'}
- MACD: {'金叉' if context.macd > context.macd_signal else '死叉'}

**动能加速: {factors['momentum_acceleration']}/10**
- MACD柱: {context.macd_histogram:.3f}

**拐点条件: {factors['inflection_condition']}/10**
- RSI: {context.rsi:.1f}，距52周高点: {context.price_vs_52w_high:.1f}%

**退出信号: {factors['exit_signal']}/10**
- 溢价/折价: {premium_txt}

**基金读数评分: {score:.1f}/10**
反身性判断：{verdict}
依据：仅技术指标、市场状态与 ETF 画像；公司规则（PE、收入增速、市值）不用于基金。
"""
        coverage = 0.9 if context.macd != 0 else 0.7

        return AgentResponse(
            agent_id=self.agent_id,
            agent_name=self.name,
            signal=signal,
            confidence=confidence,
            score=score,
            reasoning=reasoning,
            key_findings=key_findings,
            risks=risks,
            metadata={"factors": factors, "philosophy": self.philosophy,
                      "fund_reading": True, "fund_basis": FUND_READING_BASIS},
            coverage_confidence=coverage,
        )
