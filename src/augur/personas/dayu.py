# -*- coding: utf-8 -*-
"""
DayuAgent (大宇) — 币圈"看准+重仓"投资人格

大宇（@BTCdayu）投资体系核心：
  1. 信息优势：够准、够多、够快
  2. 看准+重仓：1.0求快 → 2.0求稳 → 3.0均衡
  3. 三线程理论：信息轮 × 决策轮 × 心态轮
  4. 情绪/动量投机 + 稳定币研究 + 赛道分析
  5. 三重仓位管理：核心(ETH/BTC) + 高风险(~10%) + 稳定币

适用场景：
  - Crypto/数字资产分析（传统框架无法覆盖）
  - Meme/情绪驱动标的
  - 早期项目/新叙事判断
  - 极高波动环境
  - 小资金快速成长策略
"""

from typing import Dict
from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType


class DayuAgent(BaseAgent):
    """大宇 — 币圈看准+重仓投资体系"""

    def __init__(self):
        super().__init__(
            agent_id="dayu",
            name="大宇 (BTCdayu)",
            identity="""币圈顶级投资者，"看准+重仓"体系创始人。
从300元出租屋起步实现财富自由，31万+粉丝。
进化路径：K线 → 基本面 → 情绪/NFT → 视野/VC → 信息差系统。
核心能力：信息优势(够准/够多/够快) + 情绪判断 + 赛道分析。""",
            philosophy=["看准+重仓", "信息优势", "情绪判断", "稳定币研究", "三线程理论"],
            scoring_weights={
                "momentum_sentiment": 0.30,   # 动量+情绪
                "information_edge": 0.20,     # 信息优势
                "risk_capital": 0.20,         # 仓位管理
                "narrative_timing": 0.15,     # 叙事时机
                "crypto_valuation": 0.10,     # 币圈估值
                "stablecoin_signal": 0.05,    # 稳定币信号
            },
            thresholds={
                "bullish_threshold": 7.0,
                "bearish_threshold": 4.0,
                "volume_surge_min": 3.0,          # 成交量放大倍数
                "sentiment_positive_min": 0.6,     # 正面情绪阈值
                "price_vs_sma50_gap_max": 30,      # 高于50日均线最大%
                "max_single_position_pct": 10,     # 单仓上限%
                "stablecore_position_pct": 60,     # 核心仓位下限%
            },
            biases={
                "prefers_crypto_narrative": True,
                "momentum_over_value": True,
                "small_cap_preference": True,
                "contrarian_at_extremes": True,
                "stablecoin_focus": True,
            }
        )

    def analyze(self, context: MarketContext) -> AgentResponse:
        """大宇风格分析 — 币圈特有框架"""
        factors = {}
        sector = (context.sector or "").lower()
        industry = (context.industry or "").lower()

        # ============ 1. 动量+情绪分析 (权重最大) ============
        momentum_score = self._score_momentum_sentiment(context)
        factors["momentum_sentiment"] = momentum_score

        # ============ 2. 信息优势判断 ============
        info_score = self._score_information_edge(context, sector)
        factors["information_edge"] = info_score

        # ============ 3. 仓位风险评估 ============
        risk_score = self._score_risk_capital(context)
        factors["risk_capital"] = risk_score

        # ============ 4. 叙事时机 ============
        narrative_score = self._score_narrative_timing(context, sector, industry)
        factors["narrative_timing"] = narrative_score

        # ============ 5. 币圈估值框架 ============
        crypto_val_score = self._score_crypto_valuation(context)
        factors["crypto_valuation"] = crypto_val_score

        # ============ 6. 稳定币信号 ============
        stablecoin_score = self._score_stablecoin_signal(context, sector)
        factors["stablecoin_signal"] = stablecoin_score

        # 综合评分
        total_score = sum(factors[k] * self.scoring_weights.get(k, 0) for k in factors)
        total_score = max(0.0, min(10.0, total_score))
        avg_score = sum(factors.values()) / len(factors)
        signal = self._calculate_signal(avg_score)

        # 置信度：基于信息充分性和波动率
        info_completeness = sum(1 for v in [
            context.volume, context.rsi, context.change_pct,
            context.revenue_growth
        ] if v and v > 0) / 4
        confidence = min(0.90, 0.4 + info_completeness * 0.3 + avg_score / 25)

        # 大宇特别指标：高风险仓位比例建议
        max_dd = context.max_drawdown or 0
        suggested_high_risk_pct = self._compute_high_risk_position(avg_score, max_dd)

        # 生成推理
        reasoning = self._generate_reasoning(context, factors, total_score, suggested_high_risk_pct)

        # 关键发现与风险
        key_findings, risks = self._generate_findings_risks(context, factors)

        # 模型适用性：大宇框架适合有交易量+有波动的标的
        if context.volume > 0 and context.change_pct != 0:
            coverage_confidence = 1.0
        elif context.volume > 0:
            coverage_confidence = 0.7
        else:
            coverage_confidence = 0.4

        metadata = {
            "factors": factors,
            "philosophy": self.philosophy,
            "suggested_high_risk_position_pct": suggested_high_risk_pct,
        }

        return AgentResponse(
            agent_id=self.agent_id,
            agent_name=self.name,
            signal=signal,
            confidence=confidence,
            score=total_score,
            reasoning=reasoning,
            key_findings=key_findings,
            risks=risks,
            metadata=metadata,
            coverage_confidence=coverage_confidence,
        )

    # ============ 因子评分方法 ============

    def _score_momentum_sentiment(self, ctx: MarketContext) -> float:
        """动量+情绪评分 (0-10)"""
        score = 5.0

        # 价格动量
        if ctx.change_pct > 20:
            score += 3
        elif ctx.change_pct > 10:
            score += 2.5
        elif ctx.change_pct > 5:
            score += 2
        elif ctx.change_pct > 2:
            score += 1
        elif ctx.change_pct < -20:
            score -= 3
        elif ctx.change_pct < -10:
            score -= 2
        elif ctx.change_pct < -5:
            score -= 1

        # RSI动量
        rsi = ctx.rsi
        if 60 <= rsi <= 75:
            score += 2  # 健康动量
        elif 50 <= rsi < 60:
            score += 1
        elif rsi > 80:
            score -= 1  # 过热
        elif rsi < 30:
            score -= 1  # 超卖(大宇不抄底)

        # MACD
        if ctx.macd > ctx.macd_signal:
            score += 1

        # 价格相对均线
        if ctx.price > ctx.sma50 > 0:
            gap = (ctx.price - ctx.sma50) / ctx.sma50 * 100
            if gap < 30:
                score += 1  # 健康趋势
            elif gap > 60:
                score -= 1  # 偏离过远

        if ctx.price > ctx.sma20 > 0:
            score += 0.5

        return min(max(score, 0), 10)

    def _score_information_edge(self, ctx: MarketContext, sector: str) -> float:
        """信息优势评分 — 寻找信息差空间"""
        score = 5.0

        # 机构关注度 (低=信息差大)
        inst_own = ctx.institutional_ownership or 0
        if inst_own < 15:
            score += 2  # 低机构覆盖 = 信息差机会
        elif inst_own < 30:
            score += 1

        # 内部人持有 (高=信心)
        insider = ctx.insider_ownership or 0
        if insider > 30:
            score += 2
        elif insider > 15:
            score += 1

        # 小市值弹性
        mc = ctx.market_cap or 0
        if mc > 0 and mc < 0.5:        # < $500M (billions unit)
            score += 2.5  # 超小市值 = 最大弹性
        elif mc < 2.0:                 # < $2B
            score += 1.5
        elif mc < 10.0:                # < $10B
            score += 0.5
        elif mc > 200.0:               # > $200B 超级大盘
            score -= 2    # 弹性有限

        # 亏损/未盈利=可能早期机会(币圈特色)
        pe = ctx.pe or 0
        if pe == 0 or pe < 0:
            score += 1

        # 高增长=有故事可讲
        rev_growth = ctx.revenue_growth or 0
        if rev_growth > 0.50:
            score += 2
        elif rev_growth > 0.20:
            score += 1

        return min(max(score, 0), 10)

    def _score_risk_capital(self, ctx: MarketContext) -> float:
        """仓位风险评估 — 大宇的归零不痛心原则"""
        score = 5.0

        vol = ctx.volatility_20d or 0
        max_dd = ctx.max_drawdown or 0

        # 波动率
        if vol > 60:
            score -= 3  # 超高波动 = 不适合重仓
        elif vol > 40:
            score -= 2
        elif vol > 25:
            score -= 1
        elif vol < 15:
            score += 1  # 低波动 = 可重仓
        elif vol < 10:
            score += 2

        # 最大回撤
        if max_dd > 40:
            score -= 2
        elif max_dd > 25:
            score -= 1
        elif max_dd < 10:
            score += 1

        # 做空压力
        short_int = ctx.short_interest or 0
        if short_int > 30:
            score -= 2  # 高做空 = 多空对决风险
        elif short_int > 15:
            score -= 1

        # 流动性
        if ctx.current_ratio > 0:
            if ctx.current_ratio < 0.5:
                score -= 1
            elif ctx.current_ratio > 2:
                score += 1

        return min(max(score, 0), 10)

    def _score_narrative_timing(self, ctx: MarketContext, sector: str, industry: str) -> float:
        """叙事时机评分 — 大宇的赛道分析框架"""
        score = 5.0

        # 高速增长=叙事坚强
        rev_growth = ctx.revenue_growth or 0
        if rev_growth > 0.80:
            score += 3
        elif rev_growth > 0.40:
            score += 2
        elif rev_growth > 0.15:
            score += 1

        # 大宇偏好赛道
        narrative_sectors = ["technology", "communication_services"]
        if sector in narrative_sectors:
            score += 1.5

        # 未盈利但高PS = 叙事驱动(币圈特色)
        pe = ctx.pe or 0
        ps = ctx.ps or 0
        if (pe == 0 or pe < 0) and ps > 5:
            score += 1  # 叙事驱动型标的

        # 低位启动信号
        vs_52w_low = ctx.price_vs_52w_low or 100
        if vs_52w_low < 15:
            score += 1  # 接近52周低点=可能启动

        # 高动量确认
        vs_52w_high = ctx.price_vs_52w_high or 0
        if vs_52w_high > -20:
            score += 0.5  # 在52周高附近=趋势确认

        return min(max(score, 0), 10)

    def _score_crypto_valuation(self, ctx: MarketContext) -> float:
        """币圈特有估值框架 — 不看PE看PS/PB/FCF"""
        score = 5.0

        ps = ctx.ps or 0
        pb = ctx.pb or 0
        fcf = ctx.fcf or 0

        # PS估值 (币圈更看重PS)
        if ps > 0:
            if ps < 3:
                score += 3
            elif ps < 8:
                score += 2
            elif ps < 15:
                score += 1
            elif ps > 100:
                score -= 2

        # PB估值
        if pb > 0:
            if pb < 2:
                score += 1.5
            elif pb < 5:
                score += 0.5
            elif pb > 20:
                score -= 1

        # 有现金流 = 质量加分
        if fcf > 0:
            score += 2
            if ctx.revenue and ctx.market_cap:
                fcf_yield = fcf / ctx.market_cap
                if fcf_yield > 0.03:
                    score += 1

        # 负债率
        debt = ctx.debt_ratio or 0
        if debt > 0.80:
            score -= 2
        elif debt > 0.60:
            score -= 1
        elif debt < 0.20:
            score += 1

        return min(max(score, 0), 10)

    def _score_stablecoin_signal(self, ctx: MarketContext, sector: str) -> float:
        """稳定币/基础设施信号 — 大宇最独特的研究领域"""
        score = 5.0

        # 高毛利 = 平台/基础设施逻辑
        gm = ctx.gross_margins or 0
        if gm > 0.70:
            score += 2
        elif gm > 0.50:
            score += 1

        # 高运营利润率 = 护城河
        om = ctx.operating_margins or 0
        if om > 0.30:
            score += 1.5
        elif om > 0.15:
            score += 1

        # 高增长 + 高毛利 + 正FCF = 稳定币级标的
        rev_growth = ctx.revenue_growth or 0
        dayu_fcf = ctx.fcf or 0
        if rev_growth > 0.10 and dayu_fcf > 0 and gm > 0.50:
            score += 2

        # 金融科技/稳定币赛道偏好
        if sector in ["financial_services"]:
            score += 1

        return min(max(score, 0), 10)

    def _compute_high_risk_position(self, avg_score: float, max_dd: float) -> float:
        """计算建议的高风险仓位比例（大宇10% rule)"""
        base = 10.0  # 基准10%
        if avg_score >= 8:
            base = 15.0  # 高确信度可到15%
        elif avg_score <= 4:
            base = 2.0   # 低确信度只放2%
        # 回撤惩罚
        if max_dd > 30:
            base *= 0.5
        return round(base, 1)

    def _generate_reasoning(self, ctx: MarketContext, factors: Dict,
                            total_score: float, suggested_pos: float) -> str:
        change_str = f"{ctx.change_pct:+.1f}%" if ctx.change_pct else "N/A"
        rsi_str = f"{ctx.rsi:.0f}" if ctx.rsi else "N/A"
        mc_str = f"${ctx.market_cap:.1f}B" if ctx.market_cap else "N/A"
        pe_str = f"{ctx.pe:.1f}" if ctx.pe else "N/A"

        return f"""## {self.name} Analysis for {ctx.ticker}

**动量+情绪: {factors['momentum_sentiment']:.1f}/10**
- 涨跌幅: {change_str} | RSI: {rsi_str} | 市值: {mc_str}
- {'✓ 健康动量' if factors['momentum_sentiment'] >= 6 else '✗ 动量偏弱'}

**信息优势: {factors['information_edge']:.1f}/10**
- PE: {pe_str} | 营收增速: {f'{ctx.revenue_growth*100:.0f}%' if ctx.revenue_growth else 'N/A'}
- 机构持股: {f'{ctx.institutional_ownership:.1f}%' if ctx.institutional_ownership else 'N/A'}

**仓位风险: {factors['risk_capital']:.1f}/10**
- 20日波动: {f'{ctx.volatility_20d:.1f}%' if ctx.volatility_20d else 'N/A'}
- 最大回撤: {f'{ctx.max_drawdown:.1f}%' if ctx.max_drawdown else 'N/A'}
- 建议高风险仓位: ≤{suggested_pos}%（大宇10%原则）

**叙事时机: {factors['narrative_timing']:.1f}/10**
**币圈估值: {factors['crypto_valuation']:.1f}/10**
**稳定币信号: {factors['stablecoin_signal']:.1f}/10**

**综合评分: {total_score:.1f}/10**
**三线程建议:**
- 🌀 信息轮: {'优势明显' if factors['information_edge'] >= 6 else '信息不足'}
- ⚙️ 决策轮: {'看准' if factors['momentum_sentiment'] >= 6 else '观望'}
- ❤️ 心态轮: {'可重仓' if factors['risk_capital'] >= 6 else '轻仓参与'}

投资哲学：看准+重仓 · 信息优势 · 情绪判断
"""

    def _generate_findings_risks(self, ctx: MarketContext, factors: Dict):
        findings = []
        risks = []

        # 动量强势
        if factors["momentum_sentiment"] >= 7:
            findings.append(
                f"动量强劲(RSI={ctx.rsi:.0f}, 涨跌{ctx.change_pct:+.1f}%)"
            )
        if factors["information_edge"] >= 7:
            findings.append("信息差空间大：低机构覆盖/高增长/小市值")

        # 大宇特色发现
        if factors["momentum_sentiment"] >= 6 and factors["risk_capital"] >= 6:
            findings.append("🏆 看准+重仓信号：动量强且风险可控，适合重点参与")

        vol = ctx.volatility_20d or 0
        if vol > 40:
            risks.append(f"⚠️ 超高波动({vol:.0f}%)，大宇建议：只拿归零不心痛的小仓位")
        if factors["momentum_sentiment"] >= 8 and factors["risk_capital"] <= 4:
            risks.append("🔥 追高风险警告：动量极高但回撤/波动过大")

        max_dd = ctx.max_drawdown or 0
        if max_dd > 30:
            risks.append(f"📉 回撤已达{max_dd:.0f}%，大宇原则：不抄底，等右侧确认")

        # 过热警告
        if factors["momentum_sentiment"] >= 8 and ctx.rsi and ctx.rsi > 75:
            risks.append("🔄 全员看多/RSI过热 → 大宇逆向思维：分批止盈")

        # 缺少关键字段
        if not ctx.volume:
            risks.append("缺少成交量数据 — 大宇无法判断动量真实性")

        return findings[:5], risks[:3]
