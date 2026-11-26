# -*- coding: utf-8 -*-
"""
Agent人格系统 — 基类与类型定义

包含:
  - SignalType (Enum)
  - AgentResponse (dataclass)
  - MarketContext (dataclass)
  - DebateMessage (dataclass)
  - BaseAgent (基类)
  - DebateProtocol (辩论协议)
"""

import functools
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


# ============ 类型定义 ============

class SignalType(Enum):
    """信号类型"""
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    ERROR = "error"


@dataclass
class AgentResponse:
    """Agent分析结果"""
    agent_id: str
    agent_name: str
    signal: SignalType
    confidence: float  # 0-1
    score: float       # 0-10
    reasoning: str
    key_findings: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 扩展: 风险调整后指标
    risk_adjusted_score: float = 0  # 卡尔马比率调整后评分
    alpha: float = 0               # 阿尔法
    beta: float = 1.0             # 贝塔
    coverage_confidence: float = 1.0  # 模型适用性置信度，1.0=完全适用

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "signal": self.signal.value,
            "confidence": self.confidence,
            "score": self.score,
            "reasoning": self.reasoning,
            "key_findings": self.key_findings,
            "risks": self.risks,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "risk_adjusted_score": self.risk_adjusted_score,
            "alpha": self.alpha,
            "beta": self.beta,
            "coverage_confidence": self.coverage_confidence,
        }


@dataclass
class MarketContext:
    """市场上下文 - 包含所有Agent分析所需的数据"""
    ticker: str
    price: float = 0
    change_pct: float = 0
    market_cap: float = 0
    pe: float = 0
    pb: float = 0
    ps: float = 0
    fcf: float = 0
    revenue: float = 0
    revenue_growth: float = 0
    earnings_growth: float = 0
    gross_margins: float = 0
    operating_margins: float = 0
    roe: float = 0
    roa: float = 0
    debt_ratio: float = 0
    current_ratio: float = 0
    quick_ratio: float = 0
    institutional_ownership: Optional[float] = None
    insider_ownership: Optional[float] = None
    price_vs_52w_high: float = 0
    price_vs_52w_low: float = 0
    sector: str = ""
    industry: str = ""
    business_summary: str = ""  # yfinance longBusinessSummary，用于判断公司真实业务

    # ---- data provenance / missingness ----
    field_availability: Dict[str, str] = field(default_factory=dict)
    # ^ per-field availability status: "live" | "replay" | "missing" | "unknown"
    as_of_date: Optional[str] = None
    # ^ snapshot date of the data (ISO format); None when not known
    evidence_items: List[Any] = field(default_factory=list)
    # ^ minimal EvidenceItem list attached after provider fetch

    # 技术指标
    volume: float = 0           # 成交量
    rsi: float = 50
    macd: float = 0
    macd_signal: float = 0
    macd_histogram: float = 0
    bb_upper: float = 0
    bb_middle: float = 0
    bb_lower: float = 0
    sma20: float = 0
    sma50: float = 0
    atr: float = 0
    stoch_k: float = 50
    stoch_d: float = 50

    # 南向资金（港股）
    southbound_hold_pct: float = 0

    # ============ 新增: 专业风险指标 ============
    # 波动率指标
    volatility_20d: float = 0    # 20日波动率
    volatility_60d: float = 0    # 60日波动率
    volatility_252d: float = 0   # 年化波动率

    # 风险调整收益
    sharpe_ratio: float = 0      # 夏普比率
    sortino_ratio: float = 0      # 索提诺比率
    calmar_ratio: float = 0       # 卡尔马比率
    information_ratio: float = 0   # 信息比率
    max_drawdown: float = 0       # 最大回撤

    # VAR指标
    var_95: float = 0           # 95% VAR
    cvar_95: float = 0          # 条件VAR

    # 相对表现
    alpha_1y: float = 0         # 1年阿尔法
    beta_1y: float = 1.0         # 1年贝塔
    correlation_market: float = 0 # 与市场相关性

    # 资金流指标
    fund_flow_1m: float = 0      # 1个月资金流
    short_interest: float = 0    # 做空利息

    # Kronos K-line prediction fields
    kronos_prediction_5d: float = 0.0      # 5日预测变化%
    kronos_prediction_20d: float = 0.0     # 20日预测变化%
    kronos_prediction_60d: float = 0.0     # 60日预测变化%
    kronos_confidence: float = 0.0         # 预测置信度 0-1
    kronos_trend: str = ""                 # 'up'|'down'|'sideways'
    kronos_signal: str = ""                # 'strong'|'moderate'|'weak'

    # MCP data enrichment fields
    industry_peers: list = field(default_factory=list)   # 行业同行列表
    mcp_metrics: dict = field(default_factory=dict)       # MCP 附加指标

    # ============ 新增: 公司元信息 / 行情扩展 ============
    company_name: str = ""        # 公司全称
    currency: str = ""            # 计价货币
    exchange: str = ""            # 交易所
    day_open: float = 0           # 今日开盘
    day_high: float = 0           # 今日最高
    day_low: float = 0            # 今日最低
    fifty_two_week_high: float = 0  # 52周最高（绝对值）
    fifty_two_week_low: float = 0   # 52周最低（绝对值）
    avg_volume: float = 0         # 平均成交量
    sma200: float = 0             # 200日均线

    # ============ 新增: 估值 / 盈利扩展 ============
    forward_pe: float = 0         # 远期市盈率
    peg_ratio: float = 0          # PEG
    eps: float = 0                # 每股收益（TTM）
    forward_eps: float = 0        # 远期每股收益
    profit_margins: float = 0     # 净利率（0-1 小数）
    ebitda: float = 0             # EBITDA（十亿 USD）
    enterprise_value: float = 0   # 企业价值（十亿 USD）
    total_cash: float = 0         # 现金及等价物（十亿 USD）
    total_debt: float = 0         # 总负债（十亿 USD）

    # ============ 新增: 股息 ============
    dividend_yield: float = 0     # 股息率（0-1 小数）
    dividend_rate: float = 0      # 每股年度股息（货币单位）
    payout_ratio: float = 0       # 派息率（0-1 小数）

    # ============ 新增: 分析师一致预期（华尔街共识，可作参考维度）============
    target_mean_price: float = 0  # 分析师目标均价
    target_high_price: float = 0  # 目标最高价
    target_low_price: float = 0   # 目标最低价
    recommendation_key: str = ""  # 评级关键词 strong_buy/buy/hold/sell
    num_analyst_opinions: int = 0  # 覆盖分析师数量

    # ============ v14: 资产类型 / 基金画像 / 货币 ============
    asset_type: str = "equity"    # "equity" | "etf" | "fund"
    etf: Dict = field(default_factory=dict)  # 基金画像，键见 augur.etf
    financial_currency: str = ""  # 财报货币（可能与交易货币 currency 不同）
    fx_rate_usd: float = 0.0      # 交易货币兑美元汇率，0 = 未知

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> dict:
        """转换为字典，包含所有字段"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


@dataclass
class DebateMessage:
    """辩论消息"""
    from_agent: str
    to_agent: str = "all"
    topic: str = ""
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


# ============ BaseAgent - 人格基类 ============

class BaseAgent:
    """
    Agent人格基类

    每个Agent拥有人格特征：
    1. identity - 身份描述（ Buffett/Graham/Lynch等）
    2. philosophy - 投资哲学关键词
    3. scoring_weights - 因子权重
    4. thresholds - 判断阈值
    5. biases - 认知偏差倾向
    """

    def __init_subclass__(cls, **kwargs):
        """Wrap every subclass ``analyze`` with the fund-abstention guard.

        This is the single choke point for ETF / fund contexts: callers reach
        personas through many paths (registry, MCP, dashboard, bots,
        backtests) that all end in ``agent.analyze(ctx)``. Only classes that
        define ``analyze`` themselves are wrapped, so inheritance never
        double-wraps; the original is kept as ``analyze.__wrapped__``.
        """
        super().__init_subclass__(**kwargs)
        raw = cls.__dict__.get("analyze")
        if raw is None or not callable(raw) or getattr(raw, "_augur_fund_guard", False):
            return

        @functools.wraps(raw)
        def analyze(self, context, *args, **kw):
            from augur.etf import FUND_APPLICABLE_PERSONAS, is_fund
            if not is_fund(context):
                return raw(self, context, *args, **kw)
            if getattr(self, "agent_id", "") not in FUND_APPLICABLE_PERSONAS:
                return self._fund_not_applicable(context)
            # v14.1: a persona with a dedicated fund path (``analyze_fund``)
            # reads only technical / macro / ETF-profile fields; one without
            # (dalio) runs its own rules, which are already technical-only.
            fund_path = getattr(self, "analyze_fund", None)
            resp = fund_path(context) if callable(fund_path) else raw(self, context, *args, **kw)
            if isinstance(resp, AgentResponse) and not resp.metadata.get("not_applicable"):
                resp.metadata["fund_reading"] = True
                resp.metadata.setdefault("asset_type", str(getattr(context, "asset_type", "") or "fund").lower())
            return resp

        analyze._augur_fund_guard = True
        cls.analyze = analyze

    def _fund_not_applicable(self, context: "MarketContext", reason: str = "fund") -> AgentResponse:
        """Neutral abstention returned for funds instead of running company rules.

        ``reason="fund"``: the persona's rules are company rules.
        ``reason="fund_data_missing"``: the persona has a fund path but the
        technical inputs it needs (price, moving averages) are missing.
        """
        name = getattr(self, "name", "") or getattr(self, "agent_id", "")
        asset_type = str(getattr(context, "asset_type", "") or "fund").lower()
        if reason == "fund_data_missing":
            text = f"基金数据不足：{name} 的基金读数需要价格与均线等技术指标，当前缺失，不参与评分。"
        else:
            text = f"不适用于基金：{name} 的规则基于公司财务，{asset_type.upper()} 不参与评分。"
        return AgentResponse(
            agent_id=getattr(self, "agent_id", ""),
            agent_name=name,
            signal=SignalType.NEUTRAL,
            confidence=0.0,
            score=5.0,
            reasoning=text,
            coverage_confidence=0.0,
            metadata={"not_applicable": True, "reason": reason, "asset_type": asset_type},
        )

    @staticmethod
    def _fund_technicals_missing(context: "MarketContext", need_macd: bool = False) -> bool:
        """True when a fund context lacks the minimum technical inputs.

        ``rsi`` defaults to 50 and cannot signal absence, so the zero
        sentinels of price and the 50/200-day averages are used instead.
        With ``need_macd``, MACD line, signal and histogram all at 0 also
        count as missing (they come from price history, which can fail
        while the quote still arrives).
        """
        price = getattr(context, "price", 0) or 0
        sma50 = getattr(context, "sma50", 0) or 0
        sma200 = getattr(context, "sma200", 0) or 0
        if not (price > 0 and sma50 > 0 and sma200 > 0):
            return True
        if need_macd and not any(
            getattr(context, k, 0) for k in ("macd", "macd_signal", "macd_histogram")
        ):
            return True
        return False

    def __init__(
        self,
        agent_id: str,
        name: str,
        identity: str,
        philosophy: List[str],
        scoring_weights: Dict[str, float],
        thresholds: Dict[str, float],
        biases: Dict[str, Any] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.identity = identity
        self.philosophy = philosophy
        self.scoring_weights = scoring_weights
        self.thresholds = thresholds
        self.biases = biases or {}
        self._merge_saved_thresholds()

    def _merge_saved_thresholds(self):
        """V5: overlay optimized thresholds from feedback/agent_hyperparams.json."""
        try:
            from augur.agent_hyperparams import load_optimized_thresholds
            saved = load_optimized_thresholds(self.agent_id)
            if saved:
                self.thresholds.update(saved)
        except Exception:
            pass

    def analyze(self, context: MarketContext) -> AgentResponse:
        """分析市场上下文并返回结果"""
        raise NotImplementedError

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return f"""你是一个{self.name}风格的投资者。
人格定义：{self.identity}
投资哲学：{', '.join(self.philosophy)}

核心原则：
1. 关注{self.philosophy[0] if self.philosophy else '价值'}
2. 使用具体数字而非形容词
3. 长期思维，避免短期波动

分析输出格式：
## Signal: bullish/neutral/bearish
## Score: X/10
## Key Findings: 具体发现
## Risks: 风险因素
"""

    def _get_factor_score(self, factor: str, value: float, thresholds: Dict[str, float]) -> float:
        """根据阈值计算机因子评分 (0-10)"""
        return 5.0  # 默认中性

    def _calculate_signal(self, avg_score: float) -> SignalType:
        """根据评分计算信号"""
        bullish_threshold = self.thresholds.get("bullish_threshold", 7.0)
        bearish_threshold = self.thresholds.get("bearish_threshold", 4.0)

        if avg_score >= bullish_threshold:
            return SignalType.BULLISH
        elif avg_score <= bearish_threshold:
            return SignalType.BEARISH
        else:
            return SignalType.NEUTRAL

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "identity": self.identity,
            "philosophy": self.philosophy,
            "scoring_weights": self.scoring_weights,
            "thresholds": self.thresholds,
        }
