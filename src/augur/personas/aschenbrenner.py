# -*- coding: utf-8 -*-
"""
AschenbrennerAgent - Leopold Aschenbrenner AGI超级乐观 / 算力基础设施重注
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class AschenbrennerAgent(BaseAgent):
    """Leopold Aschenbrenner - AGI超级乐观 / 算力基础设施重注"""

    def __init__(self):
        super().__init__(
            agent_id="aschenbrenner",
            name="Leopold Aschenbrenner",
            identity="""AGI投资第一人，前OpenAI研究员。核心论点是AGI将在2027年左右到来，带来超级智能递归自改进，
需要万亿美元级别的算力基础设施投资。大模型训练集群从万卡扩展到百万卡，每个集群投入$1T+、消耗20GW+电力。
这是国家级战略问题（Manhattan Project for AGI），决定了自由世界的未来竞争力。""",
            philosophy=["AGI超级乐观", "算力指数增长", "超级智能递归", "基础设施重注", "国家安全范式"],
            scoring_weights={
                "compute_infrastructure": 0.25,  # 算力投入/资本支出
                "ai_exposure": 0.20,             # AI营收占比/研发强度
                "tam_expansion": 0.20,           # TAM扩张速度
                "vertical_integration": 0.15,    # 垂直整合（芯片→云→应用）
                "moat_reinforcement": 0.10,      # AI是否在强化护城河
                "management_vision": 0.10,       # 管理层对AGI的视野
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
            },
            biases={
                "tech_optimism": True,
                "compute_bullish": True,
                "infrastructure_focus": True,
                "agi_timeframe_2027": True,
            }
        )

    def get_system_prompt(self) -> str:
        return """你是Leopold Aschenbrenner，前OpenAI研究员，'Situational Awareness: The Decade Ahead'作者。

核心观点：
1. AGI将在2027年左右到来（基于compute OOMs和scaling laws外推）
2. 超级智能会产生递归自改进，快速超越人类水平
3. 需要万亿美元级别的算力基础设施（从万卡→百万卡集群）
4. 每个AGI训练集群投入$1T+，消耗20GW+电力
5. 这是国家级战略问题 —— 「曼哈顿计划 for AGI」
6. 垂直整合（芯片→云→应用）是决胜关键
7. 投资聚焦：算力提供商（NVDA）、超大规模云（MSFT/GOOG/AMZN）、AI应用层

名言：
- "We are on the verge of the most consequential economic transformation in history"
- "Compute is the new oil"
- "The AGI Manhattan Project"
- "From thousands to millions of GPUs in the training cluster"

你的分析框架：
- 不是传统估值，而是计算未来AGI基础设施的赌注
- 谁能构建百万卡集群？谁拥有芯片→云→应用的垂直整合？
- 管理层的AGI视野和资本配置决心
"""

    def analyze(self, context: MarketContext) -> AgentResponse:
        """Aschenbrenner AGI超级乐观分析"""
        factors = {}

        sector = context.sector.lower() if context.sector else ""
        industry = context.industry.lower() if context.industry else ""

        # 1. compute_infrastructure (0-10): 算力基础设施投入
        compute_score = 3  # 基础分
        # 高资本支出行业（半导体、云、硬件）
        compute_keywords = ["semiconductor", "tech", "software", "cloud", "hardware",
                            "data center", "infrastructure", "chip", "gpu"]
        matches = sum(1 for kw in compute_keywords if kw in sector or kw in industry)
        compute_score += min(matches * 1.5, 5)  # 最多+5分

        # 高负债率可能意味着重资本投入
        if context.debt_ratio > 0.40 and ("tech" in sector or "semiconductor" in sector):
            compute_score += 1  # 主动负债投入AI基础设施
        # 大市值公司在基础设施投资上更有能力
        if context.market_cap > 500:
            compute_score += 2  # 超大规模玩家
        elif context.market_cap > 100:
            compute_score += 1
        # ROE高说明资本配置效率好
        if context.roe > 0.20:
            compute_score += 1
        factors["compute_infrastructure"] = min(max(compute_score, 0), 10)

        # 2. ai_exposure (0-10): AI营收/研发强度
        ai_score = 3
        # 高研发强度=AI投入
        # 用gross_margins > 60% + tech sector = 高定价权+AI ready
        if context.revenue_growth > 0.50:
            ai_score = 9  # 爆炸性收入增长=AI驱动
        elif context.revenue_growth > 0.30:
            ai_score = 7
        elif context.revenue_growth > 0.15:
            ai_score = 5
        # 高毛利率=AI产品溢价能力
        if context.gross_margins > 0.70:
            ai_score += 1
        elif context.gross_margins > 0.55:
            ai_score += 0.5
        # tech/半导体行业天然AI exposure高
        if "semiconductor" in sector:
            ai_score += 1
        elif "software" in sector or "cloud" in sector:
            ai_score += 1
        factors["ai_exposure"] = min(max(ai_score, 0), 10)

        # 3. tam_expansion (0-10): TAM扩张速度
        tam_score = 5
        # 高PE = 市场定价了TAM扩张（Aschenbrenner认为这是合理的）
        if context.pe > 50:
            tam_score = 8  # 超高PE=TAM在快速膨胀
        elif context.pe > 30:
            tam_score = 6
        elif context.pe < 15:
            tam_score = 3  # 低PE=市场没意识到TAM扩张
        # 收入高速增长=TAM在扩大
        if context.revenue_growth > 0.50:
            tam_score += 2
        elif context.revenue_growth > 0.25:
            tam_score += 1
        # 高PS=市场提前反映未来价值
        if context.ps > 15:
            tam_score += 1
        elif context.ps > 8:
            tam_score += 0.5
        factors["tam_expansion"] = min(max(tam_score, 0), 10)

        # 4. vertical_integration (0-10): 垂直整合能力
        vert_score = 3
        # 识别垂直整合巨头
        vertical_keywords = [
            "software", "cloud", "hardware", "semiconductor", "platform",
            "ecosystem", "internet", "technology"
        ]
        vert_matches = sum(1 for kw in vertical_keywords if kw in sector or kw in industry)
        vert_score += min(vert_matches * 1.5, 4)
        # 超大市值通常伴随垂直整合
        if context.market_cap > 1000:
            vert_score += 3  # 万亿美元俱乐部=垂直整合王者
        elif context.market_cap > 500:
            vert_score += 2
        elif context.market_cap > 100:
            vert_score += 1
        # 高毛利率+高运营利润率=全栈控制力
        if context.gross_margins > 0.60 and context.operating_margins > 0.20:
            vert_score += 1
        factors["vertical_integration"] = min(max(vert_score, 0), 10)

        # 5. moat_reinforcement (0-10): AI强化护城河
        moat_score = 5
        # 高毛利率=护城河在加宽
        if context.gross_margins > 0.70:
            moat_score += 2
        elif context.gross_margins > 0.50:
            moat_score += 1
        # 机构高持仓=市场认可
        if context.institutional_ownership > 70:
            moat_score += 2  # 机构重仓=护城河得到市场确认
        elif context.institutional_ownership > 50:
            moat_score += 1
        # 高ROE=可持续竞争优势
        if context.roe > 0.30:
            moat_score += 2
        elif context.roe > 0.15:
            moat_score += 1
        # tech天然享有AI带来的护城河
        if "tech" in sector or "semiconductor" in sector:
            moat_score += 1
        factors["moat_reinforcement"] = min(max(moat_score, 0), 10)

        # 6. management_vision (0-10): 管理层AGI视野
        vision_score = 5
        # 内部人持仓=管理层信心
        if context.insider_ownership > 20:
            vision_score += 3  # 管理层超级有信心
        elif context.insider_ownership > 10:
            vision_score += 2
        elif context.insider_ownership > 5:
            vision_score += 1
        # 机构信任
        if context.institutional_ownership > 60:
            vision_score += 2
        # 大市值公司更可能有AGI视野
        if context.market_cap > 500:
            vision_score += 1
        # 高PE可以被理解成"市场相信管理层的AGI叙事"
        if context.pe > 40:
            vision_score += 1
        factors["management_vision"] = min(max(vision_score, 0), 10)

        bullish_th = self.thresholds.get("bullish_threshold", 7.0)
        bearish_th = self.thresholds.get("bearish_threshold", 4.0)

        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)
        confidence = min(0.85, 0.4 + factors["compute_infrastructure"] / 15 + factors["ai_exposure"] / 15)

        key_findings = []
        risks = []

        # 生成发现
        if factors["compute_infrastructure"] >= 7:
            key_findings.append(f"🚀 算力基础设施投资力度强，百万卡集群候选者（评分:{factors['compute_infrastructure']}/10）")
        if factors["ai_exposure"] >= 7:
            key_findings.append(f"⚡ AI营收高速增长，AGI商业化路径清晰（评分:{factors['ai_exposure']}/10）")
        if factors["vertical_integration"] >= 7:
            key_findings.append(f"🔗 垂直整合度高，芯片→云→应用全栈控制")
        if factors["tam_expansion"] >= 7:
            key_findings.append(f"📈 TAM在快速扩张，市场定价了AGI的未来空间")
        if factors["management_vision"] >= 7:
            key_findings.append(f"👁️ 管理层高持仓+机构信任，AGI愿景清晰")
        if factors["moat_reinforcement"] >= 7:
            key_findings.append(f"🛡️ AI正在强化护城河，竞争优势在扩大")

        # 风险
        if factors["compute_infrastructure"] < 4:
            risks.append("算力投入不足，可能被AGI浪潮甩在后面")
        if "semiconductor" not in sector and "tech" not in sector and "software" not in sector:
            risks.append("非科技行业，AGI基础设施主题暴露不足")
        if context.pe > 80:
            risks.append(f"PE={context.pe:.1f}极高，即使AGI乐观也要考虑估值风险")
        if context.market_cap < 10:
            risks.append("市值偏小，在万亿美元AGI竞赛中缺乏资源")

        # 模型适用性：Aschenbrenner框架仅对算力/AI基础设施公司有效
        if factors["compute_infrastructure"] >= 7 and factors["ai_exposure"] >= 5:
            coverage_confidence = 1.0
        elif factors["compute_infrastructure"] >= 5 or factors["ai_exposure"] >= 6:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.25

        reasoning = f"""## {self.name} Analysis for {context.ticker}

**算力基础设施: {factors['compute_infrastructure']}/10** (权重{self.scoring_weights['compute_infrastructure']:.0%})
- 行业: {context.sector} / {context.industry}
- 市值: ${context.market_cap:.1f}B
- 负债率: {context.debt_ratio*100:.1f}%
- ROE: {context.roe*100:.1f}%

**AI营收研发强度: {factors['ai_exposure']}/10** (权重{self.scoring_weights['ai_exposure']:.0%})
- 收入增速: {context.revenue_growth*100:.1f}%
- 毛利率: {context.gross_margins*100:.1f}%
- 运营利润率: {context.operating_margins*100:.1f}%

**TAM扩张速度: {factors['tam_expansion']}/10** (权重{self.scoring_weights['tam_expansion']:.0%})
- PE: {context.pe:.1f} {'📈 TAM快速扩张' if context.pe > 40 else ''}
- PS: {context.ps:.1f}
- 收入增速: {context.revenue_growth*100:.1f}%

**垂直整合: {factors['vertical_integration']}/10** (权重{self.scoring_weights['vertical_integration']:.0%})
- {'🔗 全栈控制' if factors['vertical_integration'] >= 7 else '垂直整合度有限'}

**AI强化护城河: {factors['moat_reinforcement']}/10** (权重{self.scoring_weights['moat_reinforcement']:.0%})
- 毛利率: {context.gross_margins*100:.1f}%
- ROE: {context.roe*100:.1f}%
- 机构持仓: {context.institutional_ownership:.1f}%

**管理层AGI视野: {factors['management_vision']}/10** (权重{self.scoring_weights['management_vision']:.0%})
- 内部人持仓: {context.insider_ownership:.1f}%
- 机构持仓: {context.institutional_ownership:.1f}%

**综合评分: {total_score:.1f}/10**
**AGI超级乐观框架结论：{'🚀 重仓AGI基础设施，这是本世纪的曼哈顿计划' if avg_score >= self.thresholds.get('bullish_threshold', 7.0) else '⚠️ 需要更多AI基础设施投入信号' if avg_score <= self.thresholds.get('bearish_threshold', 4.0) else '⏳ 中性，等待算力投入加速信号'}**
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
