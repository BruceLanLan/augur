# -*- coding: utf-8 -*-
"""
ThielAgent - Peter Thiel 从0到1垄断投资框架
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class ThielAgent(BaseAgent):
    """Peter Thiel - 从0到1垄断投资 / 逆向思维"""

    def __init__(self):
        super().__init__(
            agent_id="thiel",
            name="Peter Thiel",
            identity="""PayPal联合创始人、Palantir联合创始人、Founders Fund管理合伙人。
硅谷最知名的逆向思维投资者，早期投资Facebook（首个外部投资者，2万变10亿）。
著作《从0到1》(Zero to One) — 从0到1的创新 vs 从1到n的复制。
寻找垄断型企业而非竞争型企业，当所有人不看好时敢于下重注。""",
            philosophy=["从0到1垄断", "逆向思维", "技术驱动", "创始人偏好", "长期持有"],
            scoring_weights={
                "monopoly_power": 0.30,    # 垄断能力 - 从0到1
                "contrarian_timing": 0.25, # 逆向时机
                "founder_quality": 0.20,   # 创始人质量
                "technology_moat": 0.15,   # 技术护城河
                "long_term_bet": 0.10,     # 长期押注
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
            },
            biases={
                "contrarian_by_nature": True,
                "prefers_monopoly": True,
                "founder_focused": True,
                "long_time_horizon": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是Peter Thiel，《从0到1》作者，PayPal和Palantir联合创始人，Founders Fund管理合伙人。

核心理念：
1. 从0到1：寻找垄断型企业而不是竞争型企业
2. 逆向思维：当所有人不看好的时候敢于下重注
3. 技术驱动：偏好深科技、硬科技
4. 创始人偏好：看重创始人的独特性和决心
5. 长期持有：眼光要长，不追短期风口

名言：
- "Competition is for losers"
- "What important truth do very few people agree with you on?"
- "The single most powerful pattern I have noticed is that successful people find value in unexpected places"
- "All happy companies are different: each one earns a monopoly by solving a unique problem"
- "We wanted flying cars, instead we got 140 characters"

你的分析框架：
- 这家公司是在从0到1的创新，还是在从1到n的复制？
- 它是否在小市场建立了垄断地位？
- 市场共识是什么样的——你在逆向押注吗？
- 创始人是否足够独特和坚定？
- 技术护城河是否足够深？
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Peter Thiel 从0到1垄断投资分析"""
        factors = {}

        sector = context.sector.lower() if context.sector else ""
        industry = context.industry.lower() if context.industry else ""

        # 1. monopoly_power (0-10): 垄断能力
        monopoly_score = 3  # 基础分

        # 高毛利率 = 定价权 = 潜在的垄断
        if context.gross_margins > 0.80:
            monopoly_score += 4  # 超强定价权
        elif context.gross_margins > 0.60:
            monopoly_score += 3
        elif context.gross_margins > 0.40:
            monopoly_score += 1

        # 高运营利润率 = 规模效应
        if context.operating_margins > 0.30:
            monopoly_score += 2
        elif context.operating_margins > 0.20:
            monopoly_score += 1

        # 高ROE = 竞争优势
        if context.roe > 0.30:
            monopoly_score += 2
        elif context.roe > 0.20:
            monopoly_score += 1

        # tech/软件天然更容易产生垄断（网络效应）
        if "software" in sector or "platform" in industry:
            monopoly_score += 2
        elif "tech" in sector or "technology" in sector:
            monopoly_score += 1

        factors["monopoly_power"] = min(max(monopoly_score, 0), 10)

        # 2. contrarian_timing (0-10): 逆向时机
        contrarian_score = 5  # 基础分（中性）

        # 低PE = 市场不看好 = 可能的逆向机会
        if context.pe < 15 and context.pe > 0:
            contrarian_score += 3  # 被低估/被忽略
        elif context.pe < 25:
            contrarian_score += 1
        elif context.pe > 50:
            contrarian_score -= 1  # 太热了，不是Thiel的菜

        # 低PS说明无人问津
        if context.ps < 2 and context.ps > 0:
            contrarian_score += 2

        # 低机构持有 = 华尔街还没发现
        if context.institutional_ownership < 30:
            contrarian_score += 2
        elif context.institutional_ownership < 50:
            contrarian_score += 1

        # 低内部人持有 = 没人看好（逆向判断：可能市场对的）
        if context.insider_ownership < 2:
            contrarian_score -= 1

        # 小市值 = 更多逆向空间
        if context.market_cap < 5e9:
            contrarian_score += 2
        elif context.market_cap < 50e9:
            contrarian_score += 1

        factors["contrarian_timing"] = min(max(contrarian_score, 0), 10)

        # 3. founder_quality (0-10): 创始人质量（通过可观察指标代理）
        founder_score = 5

        # 高内部人持有 = 创始人/管理层下注
        if context.insider_ownership > 30:
            founder_score += 3  # 创始人全力下注
        elif context.insider_ownership > 15:
            founder_score += 2
        elif context.insider_ownership > 5:
            founder_score += 1

        # 高毛利率+高增长 = 创始人有产品vision
        if context.gross_margins > 0.60 and context.revenue_growth > 0.20:
            founder_score += 2

        # tech/科技公司更可能有创始人文化
        if "software" in sector or "technology" in sector:
            founder_score += 1

        # 低负债 = 创始人不愿稀释控制权
        if context.debt_ratio < 20:
            founder_score += 1
        elif context.debt_ratio > 60:
            founder_score -= 1

        factors["founder_quality"] = min(max(founder_score, 0), 10)

        # 4. technology_moat (0-10): 技术护城河
        tech_score = 3

        # 高研发强度代理
        # 高毛利率本身就暗示技术/品牌护城河
        if context.gross_margins > 0.80:
            tech_score += 3  # 极强技术护城河
        elif context.gross_margins > 0.60:
            tech_score += 2
        elif context.gross_margins > 0.40:
            tech_score += 1

        # 高收入增长 = 技术正在颠覆
        if context.revenue_growth > 0.50:
            tech_score += 3  # 爆炸性增长=技术突破
        elif context.revenue_growth > 0.25:
            tech_score += 2
        elif context.revenue_growth > 0.10:
            tech_score += 1

        # tech/半导体/生物技术 = 深科技
        deep_tech_keywords = ["semiconductor", "biotech", "ai", "software",
                              "hardware", "cloud", "defense", "space",
                              "crypto", "blockchain", "healthcare"]
        matches = sum(1 for kw in deep_tech_keywords if kw in sector or kw in industry)
        tech_score += min(matches * 1.5, 3)

        # FCF = 技术可以自我造血
        if context.fcf > 0:
            tech_score += 1

        factors["technology_moat"] = min(max(tech_score, 0), 10)

        # 5. long_term_bet (0-10): 长期押注价值
        long_score = 5

        # 收入高速增长 = 长期故事
        if context.revenue_growth > 0.30:
            long_score += 3
        elif context.revenue_growth > 0.15:
            long_score += 2
        elif context.revenue_growth > 0.05:
            long_score += 1

        # 高毛利率 = 可扩展的长期商业模式
        if context.gross_margins > 0.70:
            long_score += 2
        elif context.gross_margins > 0.50:
            long_score += 1

        # FCF支持长期发展
        if context.fcf > 0 and context.fcf > context.market_cap * 0.02:
            long_score += 2  # FCF > 2%市值
        elif context.fcf > 0:
            long_score += 1

        # 高内部人持有 = 长期愿景
        if context.insider_ownership > 20:
            long_score += 1

        # 大市值 = 已经验证了长期商业模式
        if context.market_cap > 100e9:
            long_score += 1

        factors["long_term_bet"] = min(max(long_score, 0), 10)

        bullish_th = self.thresholds.get("bullish_threshold", 7.0)
        bearish_th = self.thresholds.get("bearish_threshold", 4.0)

        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.85, 0.4 + factors["monopoly_power"] / 15 + factors["contrarian_timing"] / 15)

        key_findings = []
        risks = []

        # 生成发现
        if factors["monopoly_power"] >= 7:
            key_findings.append(f"👑 垄断型企业特征显著，定价权强（评分:{factors['monopoly_power']}/10）")
        if factors["contrarian_timing"] >= 7:
            key_findings.append(f"🔥 逆向时机成熟，市场忽略了这个机会（评分:{factors['contrarian_timing']}/10）")
        if factors["founder_quality"] >= 7:
            key_findings.append(f"👨‍💼 创始人高度commit，内部人持仓强劲（评分:{factors['founder_quality']}/10）")
        if factors["technology_moat"] >= 7:
            key_findings.append(f"🛡️ 技术护城河深厚，难以被复制（评分:{factors['technology_moat']}/10）")
        if factors["long_term_bet"] >= 7:
            key_findings.append(f"📡 长期押注价值高，商业模式可持续（评分:{factors['long_term_bet']}/10）")

        # 风险
        if factors["monopoly_power"] < 4:
            risks.append("竞争环境激烈，缺乏垄断特征——Thiel只会投垄断型企业")
        if factors["contrarian_timing"] < 3:
            risks.append("市场已经过度关注此标的，缺乏逆向投资机会")
        if factors["founder_quality"] < 4:
            risks.append("创始人参与度低或管理层缺乏独特性，不符合Thiel标准")
        if factors["technology_moat"] < 3:
            risks.append("技术护城河薄弱，容易被复制——不是从0到1的生意")
        if context.pe > 80 and context.revenue_growth < 0.10:
            risks.append("高PE+低增长=市场已经定价了长期故事，Thiel不喜欢已经在共识中的标的")
        if "software" not in sector and "tech" not in sector and "technology" not in sector:
            risks.append("非科技行业，Thiel框架最佳适用场景是科技/垄断型企业")

        # 模型适用性：Thiel框架对高毛利+高增长公司最佳
        if factors["monopoly_power"] >= 6 and factors["technology_moat"] >= 5:
            coverage_confidence = 1.0
        elif factors["monopoly_power"] >= 5 or factors["technology_moat"] >= 5:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.3

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**垄断能力: {factors['monopoly_power']}/10** (权重{self.scoring_weights['monopoly_power']:.0%})
- 毛利率: {context.gross_margins*100:.1f}% {'👑 垄断定价权' if context.gross_margins > 0.70 else ''}
- 运营利润率: {context.operating_margins*100:.1f}%
- ROE: {context.roe*100:.1f}%
- 行业: {context.sector} / {context.industry}

**逆向时机: {factors['contrarian_timing']}/10** (权重{self.scoring_weights['contrarian_timing']:.0%})
- PE: {context.pe:.1f} {'📉 被忽略' if context.pe < 20 else '📈 过热' if context.pe > 50 else ''}
- PS: {context.ps:.1f}
- 机构持仓: {context.institutional_ownership:.1f}%
- 内部人持仓: {context.insider_ownership:.1f}%

**创始人质量: {factors['founder_quality']}/10** (权重{self.scoring_weights['founder_quality']:.0%})
- 内部人持仓: {context.insider_ownership:.1f}% {'👨‍💼 强力下注' if context.insider_ownership > 20 else ''}
- 毛利率+增长: {context.gross_margins*100:.1f}% / {context.revenue_growth*100:.1f}%
- 负债率: {context.debt_ratio:.1f}%

**技术护城河: {factors['technology_moat']}/10** (权重{self.scoring_weights['technology_moat']:.0%})
- 收入增速: {context.revenue_growth*100:.1f}%
- 毛利率: {context.gross_margins*100:.1f}%
- FCF: {'正向 ✓' if context.fcf > 0 else '负向 ✗'}

**长期押注: {factors['long_term_bet']}/10** (权重{self.scoring_weights['long_term_bet']:.0%})
- 收入增速: {context.revenue_growth*100:.1f}%
- 毛利率: {context.gross_margins*100:.1f}%
- 市值: ${context.market_cap/1e9:.1f}B

**综合评分: {total_score:.1f}/10**
**Peter Thiel从0到1框架结论：{'🚀 垄断型企业！从0到1的创新，值得重仓' if avg_score >= self.thresholds.get('bullish_threshold', 7.0) else '⚠️ 这更像从1到n的复制生意' if avg_score <= self.thresholds.get('bearish_threshold', 4.0) else '⏳ 需要更多垄断信号——你相信什么别人不相信的真相？'}**"""

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
