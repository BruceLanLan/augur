# -*- coding: utf-8 -*-
"""
SerenityAgent - Serenity (@aleabitoreddit) 供应链卡脖子逆向工程交易

基于真实X/Twitter数据:
- 352K+ followers, 30K+ paid subscribers
- 核心方法论: Bottom-Up Supply Chain Reverse Engineering (Chokepoint Theory)
- 核心标的: $AXTI, $RPI, $SIVE, Soitec, $VLN, $NBIS, $AAOI, $EWY
- 期权策略: IV Expansion
- 地缘叠加: 半导体供应链物理与地缘政治地图
"""

from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class SerenityAgent(BaseAgent):
    """Serenity (@aleabitoreddit) - 供应链卡脖子逆向工程交易"""

    def __init__(self):
        super().__init__(
            agent_id="serenity",
            name="Serenity (@aleabitoreddit)",
            identity="""Reddit WSB传奇交易者(AleaBito)转X平台，352K+粉丝，30K+付费订阅者。
前RISC-V基金会成员，前AI研究科学家，Nature论文作者。
核心方法论: 自下而上供应链逆向工程(Chokepoint Theory)。
从GPU集群出发层层解构，找到物理不可替代、华尔街无覆盖的微型股卡脖子垄断者。
核心覆盖: 硅光子CPO($SIVE/Soitec/FOCI)、光互联($AAOI/$AXTI)、NeoCloud($NBIS/$CIFR/$IREN)。
利用IV expansion在催化剂前布局期权获取超额收益。""",
            philosophy=[
                "供应链卡脖子逆向工程(Chokepoint Theory)",
                "Own Compute - 拥有算力是逃离底层唯一机会",
                "自下而上(Bottom-Up)而非自上而下(Top-Down)",
                "IV Expansion期权策略",
                "华尔街制度性盲区套利",
                "对抗性AI论证(Red Team)",
            ],
            scoring_weights={
                "supply_chain_bottleneck": 0.30,  # 卡脖子识别
                "options_iv_momentum": 0.25,      # IV expansion + 动量
                "ai_compute_demand": 0.20,        # AI算力需求/NeoCloud
                "geopolitical_catalyst": 0.15,    # 地缘催化剂
                "risk_sizing": 0.10,              # 风险仓位管理
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
            },
            biases={
                "bottom_up_reverse_engineering": True,
                "small_cap_chokepoint": True,
                "iv_expansion_options": True,
                "geopolitical_overlay": True,
                "anti_consensus": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是Serenity (@aleabitoreddit)，Reddit WSB传奇交易者，现X平台最大付费订阅金融账号(352K粉丝/30K付费)。

核心方法论 - Chokepoint Theory (卡脖子逆向工程):
1. 从GPU超算集群出发，自下而上层层解构AI供应链
2. 找到物理层面不可替代、被极少数企业垄断的超微型组件或原材料
3. 这些卡脖子点市值极小(<$1B)，华尔街因合规限制无法覆盖
4. 一旦供应中断，整个下游AI产业集群物理瘫痪
5. 比喻: "霍尔木兹海峡" / "怀石料理中无人注意的紫苏叶"

核心投资主线:
- 硅光子/CPO: 光进铜退不可逆 -> DFB激光器(Sivers) -> SOI衬底(Soitec) -> MBE设备(Riber)
- NeoCloud: AI Capex溢出到GPU专用云($NBIS/$CIFR/$IREN)，季度营收可能10倍爆发
- 光互联底层: InP基板($AXTI)、光模块($AAOI)
- 人形机器人: 稀土/减速器/执行器的中国垄断风险

期权策略:
- "Your portfolio would have doubled in a week off IV expansion"
- 低IV时布局，催化剂驱动IV暴涨，期权翻倍即使标的涨幅有限
- 交易周期8个月到1年，约1.4x杠杆

地缘叠加:
- "Iran War is about to end. Markets probably even better for Europe/Taiwan/Korean"
- 全球半导体卡脖子物理与地缘政治地图(跨美/台/欧/日)
- CHIPS法案拨款、出口管制变化是核心催化剂

风格:
- "The only chance to escape the permanent underclass is in the next 5 years. By owning compute."
- "This is how you get hundreds of % in return, not value investing in Paypal."
- WSB meme文化 + 物理学级供应链分析的极端反差
- 发布前用AI做Red Team论证

你的分析框架:
- 第一步: 这家公司是不是供应链中物理不可替代的卡脖子点?
- 第二步: 华尔街是否因制度性限制(市值/地域)而无法覆盖?
- 第三步: IV是否处于低位? 催化剂时间线?
- 第四步: 地缘/政策催化剂方向?
- 第五步: 用AI做对手盘验证，检验替代方案威胁
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Serenity 供应链卡脖子逆向工程分析"""
        factors = {}

        sector = context.sector.lower() if context.sector else ""
        industry = context.industry.lower() if context.industry else ""

        # 1. supply_chain_bottleneck (0-10): 卡脖子识别
        # 核心: 物理不可替代 + 市值小 + 华尔街无覆盖
        scb_score = 5  # 基础分

        # 半导体/光子学/材料行业天然优势
        chokepoint_keywords = ["semiconductor", "photonics", "optical", "laser",
                               "substrate", "epitax", "wafer", "crystal",
                               "rare earth", "magnet", "chemical"]
        infra_keywords = ["data center", "cloud", "networking", "interconnect",
                          "fiber", "optic"]
        semi_keywords = ["chip", "gpu", "memory", "foundry", "equipment",
                         "packaging", "hbm"]

        choke_matches = sum(1 for kw in chokepoint_keywords if kw in sector or kw in industry)
        infra_matches = sum(1 for kw in infra_keywords if kw in sector or kw in industry)
        semi_matches = sum(1 for kw in semi_keywords if kw in sector or kw in industry)

        scb_score += min(choke_matches * 2, 4)
        scb_score += min(infra_matches * 1.5, 3)
        scb_score += min(semi_matches * 1, 2)

        # 高毛利率 = 定价权/垄断位置 (Serenity loves 63%+ gross margins like VLN/NVDA)
        if context.gross_margins > 0.63:
            scb_score += 2  # NVDA/VLN级毛利 = 卡脖子确认
        elif context.gross_margins > 0.50:
            scb_score += 1

        # 小市值加分 (Serenity偏好<$1B的隐形垄断者)
        if hasattr(context, 'market_cap') and context.market_cap:
            if context.market_cap < 1:
                scb_score += 2  # 微型股 = 研究真空
            elif context.market_cap < 5:
                scb_score += 1

        # 非相关行业扣分
        if not any(kw in sector or kw in industry for kw in
                   chokepoint_keywords + infra_keywords + semi_keywords +
                   ["tech", "hardware", "robot", "energy", "defense"]):
            scb_score -= 4

        factors["supply_chain_bottleneck"] = min(max(scb_score, 0), 10)

        # 2. options_iv_momentum (0-10): IV Expansion + 动量信号
        iv_score = 5  # 基础分

        # RSI: Serenity偏好有动量但未过热
        rsi = context.rsi
        if 50 <= rsi <= 70:
            iv_score += 2  # 健康上升动量
        elif 40 <= rsi < 50:
            iv_score += 1  # 即将启动
        elif rsi > 80:
            iv_score -= 2  # 散户已蜂拥 = IV高位 = crush风险
        elif rsi > 70:
            iv_score -= 1  # IV可能已高

        # MACD动量确认
        if context.macd > context.macd_signal:
            iv_score += 2
        else:
            iv_score -= 1

        # 价格接近52周高点 = 突破模式(Serenity likes momentum)
        if (1.0 + context.price_vs_52w_high / 100) > 0.90:
            iv_score += 1
        elif (1.0 + context.price_vs_52w_high / 100) < 0.60:
            iv_score -= 1  # 深度回调，可能是底部机会但IV不确定

        factors["options_iv_momentum"] = min(max(iv_score, 0), 10)

        # 3. ai_compute_demand (0-10): AI算力需求 / NeoCloud溢出
        ai_score = 5  # 基础分

        # 高收入增速 = AI需求验证 (RPI 58%, NeoCloud 7-14x)
        if context.revenue_growth > 1.0:
            ai_score += 4  # NeoCloud级爆发(>100%)
        elif context.revenue_growth > 0.50:
            ai_score += 3  # RPI级增速(55-58%)
        elif context.revenue_growth > 0.30:
            ai_score += 2
        elif context.revenue_growth > 0.15:
            ai_score += 1
        elif context.revenue_growth < 0:
            ai_score -= 2

        # 行业相关性
        ai_related = ["semiconductor", "data center", "cloud", "gpu", "optical",
                      "networking", "photonics", "ai", "compute"]
        if any(kw in sector or kw in industry for kw in ai_related):
            ai_score += 2
        elif "tech" in sector or "hardware" in sector:
            ai_score += 1

        factors["ai_compute_demand"] = min(max(ai_score, 0), 10)

        # 4. geopolitical_catalyst (0-10): 地缘催化剂
        geo_score = 5  # 基础分

        # 半导体/国防/稀土受地缘催化
        geo_sensitive = ["semiconductor", "defense", "rare earth", "nuclear",
                         "aerospace", "chip", "optical", "laser"]
        geo_matches = sum(1 for kw in geo_sensitive if kw in sector or kw in industry)
        geo_score += min(geo_matches * 1.5, 3)

        # 非美国市场标的(欧/台/韩/日)有地缘折价消除空间
        # 目前通过行业关键词间接判断
        intl_keywords = ["european", "taiwan", "korea", "japan", "sweden", "france"]
        if any(kw in industry.lower() for kw in intl_keywords):
            geo_score += 2  # 国际卡脖子标的，地缘折价消除潜力

        # 高增速 + 半导体 = CHIPS法案受益潜力
        if context.revenue_growth > 0.30 and "semiconductor" in sector:
            geo_score += 1

        factors["geopolitical_catalyst"] = min(max(geo_score, 0), 10)

        # 5. risk_sizing (0-10): 风险仓位管理
        risk_score = 5  # 基础分

        # 现金充裕/低负债 = 安全 (VLN: $93.5M cash, zero debt)
        if context.debt_ratio < 0.20:
            risk_score += 3  # VLN级: 零负债 + 巨额现金
        elif context.debt_ratio < 0.40:
            risk_score += 2
        elif context.debt_ratio < 0.60:
            risk_score += 1
        elif context.debt_ratio > 0.80:
            risk_score -= 2

        # 回撤风险 (Serenity能承受15-25%单日回撤)
        if context.max_drawdown:
            max_dd = abs(context.max_drawdown)
            if max_dd < 0.25:
                risk_score += 2
            elif max_dd < 0.40:
                risk_score += 1
            elif max_dd > 0.60:
                risk_score -= 2

        # RSI极端值 = 流动性踩踏风险
        if context.rsi > 85:
            risk_score -= 2  # 散户蜂拥，踩踏风险极高
        elif context.rsi < 20:
            risk_score -= 1  # 恐慌抛售中

        factors["risk_sizing"] = min(max(risk_score, 0), 10)

        # 计算总分
        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.85, 0.4 + factors["supply_chain_bottleneck"] / 15 + factors["options_iv_momentum"] / 15)

        key_findings = []
        risks = []

        # 生成发现
        if factors["supply_chain_bottleneck"] >= 7:
            key_findings.append(f"🔗 卡脖子位置确认: 物理不可替代的供应链垄断者（评分:{factors['supply_chain_bottleneck']}/10）")
        if factors["options_iv_momentum"] >= 7:
            key_findings.append(f"📈 IV Expansion机会: 动量向上+催化剂窗口（评分:{factors['options_iv_momentum']}/10）")
        if factors["ai_compute_demand"] >= 7:
            key_findings.append(f"⚡ AI算力直接受益: NeoCloud级增速验证（评分:{factors['ai_compute_demand']}/10）")
        if factors["geopolitical_catalyst"] >= 7:
            key_findings.append(f"🌍 地缘催化剂: CHIPS法案/出口管制/风险折价消除（评分:{factors['geopolitical_catalyst']}/10）")
        if factors["risk_sizing"] >= 7:
            key_findings.append(f"🛡️ 财务健康: 低负债高现金，流动性风险可控（评分:{factors['risk_sizing']}/10）")

        # 风险
        if factors["supply_chain_bottleneck"] < 4:
            risks.append("非供应链卡脖子位置，缺乏物理不可替代性逻辑")
        if factors["options_iv_momentum"] < 4:
            risks.append("动量走弱或IV过高，IV crush风险大")
        if factors["risk_sizing"] < 4:
            risks.append("高负债或高回撤，流动性踩踏风险")
        if not any(kw in sector or kw in industry for kw in
                   ["semiconductor", "tech", "hardware", "optical", "data center", "cloud", "defense"]):
            risks.append("非AI供应链相关行业，Chokepoint Theory框架适用性低")
        if context.rsi > 80:
            risks.append(f"RSI={context.rsi:.0f}严重超买，散户已蜂拥，踩踏风险极高")
        if context.ps > 25:
            risks.append(f"PS={context.ps:.1f}过高，卡脖子溢价可能已被充分定价")

        # 模型适用性
        if factors["supply_chain_bottleneck"] >= 7 and factors["ai_compute_demand"] >= 5:
            coverage_confidence = 1.0
        elif factors["supply_chain_bottleneck"] >= 5 or factors["ai_compute_demand"] >= 6:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.25

        reasoning = f"""## {self.name} Chokepoint Analysis for {context.ticker}

**卡脖子识别: {factors['supply_chain_bottleneck']}/10** (权重{self.scoring_weights['supply_chain_bottleneck']:.0%})
- 行业: {context.sector} / {context.industry}
- 毛利率: {context.gross_margins*100:.1f}% {'(垄断级定价权)' if context.gross_margins > 0.63 else '(强定价权)' if context.gross_margins > 0.50 else ''}
- 卡脖子判断: {'物理不可替代的供应链垄断者' if factors['supply_chain_bottleneck'] >= 7 else '非卡脖子位置' if factors['supply_chain_bottleneck'] < 4 else '潜在瓶颈，需验证替代方案'}

**IV Expansion + 动量: {factors['options_iv_momentum']}/10** (权重{self.scoring_weights['options_iv_momentum']:.0%})
- RSI(14): {context.rsi:.1f} {'(健康动量)' if 50 <= context.rsi <= 70 else '(超买=IV crush风险)' if context.rsi > 80 else ''}
- MACD vs Signal: {'动量向上' if context.macd > context.macd_signal else '动量向下'}
- 52周高点距离: {(1.0 + context.price_vs_52w_high / 100)*100:.1f}%

**AI算力需求/NeoCloud: {factors['ai_compute_demand']}/10** (权重{self.scoring_weights['ai_compute_demand']:.0%})
- 收入增速: {context.revenue_growth*100:.1f}% {'(NeoCloud级爆发)' if context.revenue_growth > 1.0 else '(RPI级增速)' if context.revenue_growth > 0.50 else ''}
- 行业: {context.sector}
- AI受益判断: {'GPU算力溢出直接受益' if factors['ai_compute_demand'] >= 7 else '间接受益' if factors['ai_compute_demand'] >= 5 else '关联度低'}

**地缘催化剂: {factors['geopolitical_catalyst']}/10** (权重{self.scoring_weights['geopolitical_catalyst']:.0%})
- 地缘敏感度: {'高(半导体/国防/稀土)' if factors['geopolitical_catalyst'] >= 7 else '中' if factors['geopolitical_catalyst'] >= 5 else '低'}
- CHIPS法案/出口管制受益: {'是' if context.revenue_growth > 0.30 and 'semiconductor' in sector else '待观察'}

**风险管理: {factors['risk_sizing']}/10** (权重{self.scoring_weights['risk_sizing']:.0%})
- 负债率: {context.debt_ratio*100:.1f}% {'(VLN级: 近零负债)' if context.debt_ratio < 0.20 else ''}
- 回撤承受: {'可控' if factors['risk_sizing'] >= 6 else '需警惕流动性踩踏'}

**综合评分: {total_score:.1f}/10**
**Chokepoint Verdict: {'🚀 Full send - 物理不可替代的卡脖子+IV expansion窗口+地缘催化' if avg_score >= self.thresholds.get('bullish_threshold', 7.0) else '⚠️ No edge - 非卡脖子位置或已被市场充分定价' if avg_score <= self.thresholds.get('bearish_threshold', 4.0) else '⏳ Watching - 需验证物理替代方案威胁或等待催化剂窗口'}**
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
