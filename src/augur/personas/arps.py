# -*- coding: utf-8 -*-
"""
ArpsAgent - Crypto/Gold专属 链上数据+实际利率框架
"""

from augur.personas.base import BaseAgent, MarketContext, AgentResponse


class ArpsAgent(BaseAgent):
    """Crypto/Gold专属 - 链上数据+实际利率框架"""

    def __init__(self):
        super().__init__(
            agent_id="arps",
            name="ARPS Crypto/Gold",
            identity="""加密货币和黄金专属分析框架，基于实际利率、法币贬值、避险需求、
                        链上数据（用宏观代理替代）。在法币信用危机和通胀环境下受益最大。""",
            philosophy=["实际利率", "法币贬值", "避险需求", "链上先行指标"],
            scoring_weights={
                "macro_background": 0.20,
                "relative_valuation": 0.20,
                "momentum_signal": 0.30,
                "liquidity_risk": 0.30,
            },
            thresholds={
                "bullish_threshold": 6.5,
                "bearish_threshold": 4.0,
            },
            biases={
                "inflation_hedge": True,
                "alternative_asset": True,
                "momentum_driven": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是ARPS框架（Alternative Risk Premium System）分析师，专注加密货币和黄金分析。

核心框架：
1. 实际利率（名义利率-通胀）是黄金/BTC的最重要驱动：实际利率↓ → 黄金/BTC↑
2. 链上指标（MVRV、NVT、交易所余额）是加密领先指标
3. 相对于法币的购买力保值需求在高通胀时代凸显
4. BTC/Gold相关性：在Risk-Off时黄金↑，BTC有时同向

分析维度：
- 宏观背景：实际利率方向（高beta+高IV=避险需求高）
- 链上/技术动量：momentum_signal + RSI
- 流动性风险：市值 + beta + iv
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """ARPS链上+实际利率分析"""
        factors = {}

        # 1. 宏观背景 (0-10): 实际利率代理
        # beta < 0.5 AND iv > 0.3 = 避险需求高 = 黄金/crypto受益
        macro_score = 5
        iv_proxy = context.volatility_20d if context.volatility_20d > 0 else 0.20
        beta_proxy = context.beta_1y if context.beta_1y > 0 else 1.0

        if beta_proxy < 0.5 and iv_proxy > 0.30:
            macro_score = 9  # 低相关+高恐慌=避险需求爆发
        elif beta_proxy < 0.8 and iv_proxy > 0.25:
            macro_score = 7
        elif beta_proxy > 1.5:
            macro_score = 3  # 高相关=风险资产属性强，避险特征弱
        # 距高点回撤也是宏观信号
        if context.price_vs_52w_high < -20:
            macro_score = max(macro_score - 1, 0)  # 深度回撤时谨慎
        factors["macro_background"] = min(max(macro_score, 0), 10)

        # 2. 相对估值 (0-10): 与传统资产的独立性
        rel_val_score = 5
        if beta_proxy < 0.3:
            rel_val_score = 9  # 接近独立资产类别
        elif beta_proxy < 0.6:
            rel_val_score = 7
        elif beta_proxy > 1.2:
            rel_val_score = 3  # 与风险资产高度相关
        # PE极低或无PE（加密/黄金无PE）时加分
        if context.pe == 0 or context.pe < 0:
            rel_val_score += 1  # 无传统估值锚定=独立资产
        factors["relative_valuation"] = min(max(rel_val_score, 0), 10)

        # 3. 动量信号 (0-10): 技术面趋势
        momentum_score = 5
        if context.macd > context.macd_signal:
            momentum_score += 2  # MACD金叉
        if context.price > context.sma20:
            momentum_score += 1
        if context.price > context.sma50:
            momentum_score += 1
        if context.rsi > 50 and context.rsi < 70:
            momentum_score += 1  # RSI健康上行区间
        elif context.rsi > 75:
            momentum_score -= 2  # 超买
        elif context.rsi < 30:
            momentum_score -= 1  # 超卖
        if context.macd_histogram > 0:
            momentum_score += 1
        factors["momentum_signal"] = min(max(momentum_score, 0), 10)

        # 4. 流动性风险 (0-10, 越高越好)
        liq_risk_score = 5
        if context.market_cap > 100:
            liq_risk_score += 3  # 大市值=流动性充足
        elif context.market_cap > 10:
            liq_risk_score += 1
        elif context.market_cap < 1:
            liq_risk_score -= 3  # 小市值=流动性风险高
        if iv_proxy > 0.50:
            liq_risk_score -= 2  # 极高波动=流动性风险
        elif iv_proxy > 0.35:
            liq_risk_score -= 1
        factors["liquidity_risk"] = min(max(liq_risk_score, 0), 10)


        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.75, 0.4 + factors["momentum_signal"] / 20)

        key_findings = []
        risks = []

        if factors["macro_background"] >= 8:
            key_findings.append("宏观避险需求高，实际利率压力大，黄金/Crypto受益环境")
        if factors["momentum_signal"] >= 7:
            key_findings.append("技术动量强，MACD金叉+价格在均线上方")
        if factors["liquidity_risk"] <= 3:
            risks.append("市值偏小或波动率极高，流动性风险不可忽视")
        if beta_proxy > 1.5:
            risks.append(f"Beta={beta_proxy:.2f}，与风险资产高度相关，避险属性弱")

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**宏观背景(实际利率代理): {factors['macro_background']}/10**
- Beta: {beta_proxy:.2f} {'✓ 低相关' if beta_proxy < 0.6 else '⚠️ 风险资产属性'}
- 波动率(IV代理): {iv_proxy*100:.1f}%
- {'✓ 避险需求高环境' if factors['macro_background'] >= 7 else '⚠️ 避险需求一般'}

**相对估值(独立性): {factors['relative_valuation']}/10**
- Beta: {beta_proxy:.2f} {'（接近独立资产类别）' if beta_proxy < 0.5 else '（与权益相关性高）'}

**动量信号: {factors['momentum_signal']}/10**
- MACD: {'金叉 ✓' if context.macd > context.macd_signal else '死叉 ✗'}
- RSI: {context.rsi:.1f}
- 价格 vs SMA20: {'✓' if context.price > context.sma20 else '✗'}
- 价格 vs SMA50: {'✓' if context.price > context.sma50 else '✗'}

**流动性风险: {factors['liquidity_risk']}/10**
- 市值: {context.market_cap:.1f}B {'✓ 充足' if context.market_cap > 10 else '⚠️ 偏低'}
- 波动率: {iv_proxy*100:.1f}%

**综合评分: {total_score:.1f}/10**
ARPS结论：{'适合配置，避险+动量双确认' if avg_score >= self.thresholds.get('bullish_threshold', 6.5) else '需谨慎，流动性或宏观支撑不足' if avg_score <= self.thresholds.get('bearish_threshold', 4.0) else '中性，等待更清晰信号'}
"""

        # 模型适用性：ARPS纯技术+动量框架，需要完整技术指标
        if context.rsi > 0 and context.sma50 > 0 and context.macd != 0:
            coverage_confidence = 1.0
        elif context.rsi > 0 or context.macd != 0:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.4  # 无技术数据，动量信号缺失

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
    # instead of ``analyze`` (whose liquidity rule reads company market cap,
    # which for funds is AUM, and whose beta is not populated for funds).
    # ------------------------------------------------------------------
    def analyze_fund(self, context: MarketContext) -> AgentResponse:
        """ARPS 的基金读数：技术动量 + 长期趋势 + 波动率环境 + 基金流动性。

        流动性用 ETF 画像（规模、成交额、买卖价差），不用公司市值；
        基金数据不提供 beta，因此不做避险属性判断。
        """
        from augur.etf import FUND_READING_BASIS, fund_signal, profile_num
        from augur.personas.base import SignalType

        if self._fund_technicals_missing(context, need_macd=True):
            return self._fund_not_applicable(context, reason="fund_data_missing")

        factors = {}
        price = context.price
        vol = context.volatility_20d if context.volatility_20d > 0 else 0.0

        # 1. 动量信号（与股票规则相同，纯技术）
        momentum = 5
        if context.macd > context.macd_signal:
            momentum += 2
        if context.sma20 > 0 and price > context.sma20:
            momentum += 1
        if price > context.sma50:
            momentum += 1
        if 50 < context.rsi < 70:
            momentum += 1
        elif context.rsi > 75:
            momentum -= 2
        elif context.rsi < 30:
            momentum -= 1
        if context.macd_histogram > 0:
            momentum += 1
        factors["momentum_signal"] = min(max(momentum, 0), 10)

        # 2. 长期趋势：价格与 200 日均线、50/200 日均线排列
        long_trend = 5
        long_trend += 2 if price > context.sma200 else -2
        long_trend += 1 if context.sma50 > context.sma200 else -1
        factors["long_trend"] = min(max(long_trend, 0), 10)

        # 3. 波动率环境：极高波动不利于趋势配置
        if vol <= 0:
            vol_score = 5
        elif vol > 0.50:
            vol_score = 2
        elif vol > 0.35:
            vol_score = 4
        elif vol < 0.20:
            vol_score = 7
        else:
            vol_score = 5
        factors["volatility_regime"] = vol_score

        # 4. 基金流动性（越高越好）：规模、成交额、买卖价差
        aum = profile_num(context, "aum_usd_bn")
        dollar_volume = profile_num(context, "dollar_volume")
        spread = profile_num(context, "spread_pct")
        liq = 5
        if aum is not None and aum > 0:
            if aum > 10:
                liq += 2
            elif aum > 1:
                liq += 1
            elif aum < 0.1:
                liq -= 3
        if dollar_volume is not None and dollar_volume > 0:
            if dollar_volume > 1e8:
                liq += 1
            elif dollar_volume < 1e6:
                liq -= 2
        if spread is not None and spread > 0.5:
            liq -= 2
        factors["liquidity_risk"] = min(max(liq, 0), 10)

        weights = {"momentum_signal": 0.35, "long_trend": 0.25,
                   "volatility_regime": 0.20, "liquidity_risk": 0.20}
        score = sum(factors[k] * w for k, w in weights.items())
        signal = SignalType(fund_signal(score))
        confidence = min(0.75, 0.4 + factors["momentum_signal"] / 20)

        key_findings = []
        risks = []
        if factors["momentum_signal"] >= 7:
            key_findings.append("基金读数：技术动量强，MACD金叉且价格在短中期均线上方")
        elif factors["momentum_signal"] <= 3:
            risks.append("基金读数：技术动量弱，MACD死叉且价格在短中期均线下方")
        if factors["long_trend"] >= 7:
            key_findings.append("基金读数：价格在200日均线上方，长期趋势向上")
        elif factors["long_trend"] <= 3:
            risks.append("基金读数：价格在200日均线下方，长期趋势向下")
        if factors["volatility_regime"] <= 2:
            risks.append(f"基金读数：20日波动率 {vol * 100:.1f}%，极高波动")
        if factors["liquidity_risk"] <= 3:
            risks.append("基金读数：规模小、成交清淡或价差偏宽，流动性风险不可忽视")
        if not key_findings and not risks:
            key_findings.append("基金读数：动量与趋势信号中性")

        aum_txt = f"${aum:,.2f}B" if aum is not None else "未知"
        dv_txt = f"${dollar_volume / 1e6:,.0f}M" if dollar_volume is not None else "未知"
        spread_txt = f"{spread:.3f}%" if spread is not None else "未知"
        verdict = ("趋势配置条件具备" if signal == SignalType.BULLISH
                   else "趋势或流动性不支持配置" if signal == SignalType.BEARISH else "中性，等待更清晰信号")
        reasoning = f"""## {self.name} 基金读数 for {context.ticker}


**动量信号: {factors['momentum_signal']}/10**
- MACD: {'金叉 ✓' if context.macd > context.macd_signal else '死叉 ✗'}，RSI: {context.rsi:.1f}
- 价格 vs SMA20: {'✓' if price > context.sma20 else '✗'}，价格 vs SMA50: {'✓' if price > context.sma50 else '✗'}

**长期趋势: {factors['long_trend']}/10**
- 价格 vs SMA200: {'✓' if price > context.sma200 else '✗'}，SMA50 vs SMA200: {'✓' if context.sma50 > context.sma200 else '✗'}

**波动率环境: {factors['volatility_regime']}/10**
- 20日波动率: {vol * 100:.1f}%

**基金流动性: {factors['liquidity_risk']}/10**
- 规模: {aum_txt}，日均成交额: {dv_txt}，买卖价差: {spread_txt}

**基金读数评分: {score:.1f}/10**
ARPS结论：{verdict}
依据：仅技术指标、市场状态与 ETF 画像；不使用公司市值，基金数据无 beta，不做避险属性判断。
"""
        coverage = 1.0 if context.macd != 0 and vol > 0 else 0.7

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
