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

from typing import Dict, List, Any
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
    institutional_ownership: float = 0
    insider_ownership: float = 0
    price_vs_52w_high: float = 0
    price_vs_52w_low: float = 0
    sector: str = ""
    industry: str = ""

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
            from scanner.agent_hyperparams import load_optimized_thresholds
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
