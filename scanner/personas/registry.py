# -*- coding: utf-8 -*-
"""
Agent人格系统 — 注册中心与协调器

包含:
  - AgentRegistry (Agent注册中心)
  - DecisionCoordinator (多Agent协调器)
  - DebateProtocol (Agent间辩论协议)
  - 全局实例和快捷函数
"""

from typing import Dict, List, Optional, Any
from threading import RLock
from pathlib import Path

from scanner.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType, DebateMessage


# ============ AgentRegistry - Agent注册中心 ============

class AgentRegistry:
    """Agent注册中心 - 管理和发现Agent"""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._lock = RLock()
        self._register_default_agents()

    def _register_default_agents(self):
        """注册默认Agent"""
        from scanner.personas.buffett import BuffettAgent
        from scanner.personas.graham import GrahamAgent
        from scanner.personas.lynch import LynchAgent
        from scanner.personas.dalio import DalioAgent
        from scanner.personas.munger import MungerAgent
        from scanner.personas.soros import SorosAgent
        from scanner.personas.marks import MarksAgent
        from scanner.personas.cathie_wood import CathieWoodAgent
        from scanner.personas.fisher import FisherAgent
        from scanner.personas.arps import ArpsAgent
        from scanner.personas.aschenbrenner import AschenbrennerAgent
        from scanner.personas.dayu import DayuAgent
        from scanner.personas.thiel import ThielAgent

        agents = [
            BuffettAgent(), GrahamAgent(), LynchAgent(), DalioAgent(), MungerAgent(),
            SorosAgent(), MarksAgent(), CathieWoodAgent(), FisherAgent(), ArpsAgent(),
            AschenbrennerAgent(),
            DayuAgent(),
            ThielAgent(),
        ]
        for agent in agents:
            self._agents[agent.agent_id] = agent
        self._register_yaml_personas()

    def _register_yaml_personas(self):
        """Auto-load YAML personas from personas/custom/ next to repo root."""
        try:
            from scanner.persona_loader import load_personas_from_dir
            custom_dir = Path(__file__).parent.parent.parent / "personas" / "custom"
            if custom_dir.exists():
                for agent in load_personas_from_dir(custom_dir):
                    self._agents[agent.agent_id] = agent
        except Exception:
            pass

    def register(self, agent: BaseAgent) -> bool:
        """注册Agent"""
        with self._lock:
            self._agents[agent.agent_id] = agent
            return True

    def unregister(self, agent_id: str) -> bool:
        """注销Agent"""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
            return False

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """获取Agent"""
        return self._agents.get(agent_id)

    def get_all(self) -> List[BaseAgent]:
        """获取所有Agent"""
        return list(self._agents.values())

    def list_agents(self) -> List[Dict]:
        """列出所有Agent信息"""
        return [agent.to_dict() for agent in self._agents.values()]


# ============ DecisionCoordinator - 多Agent协调器 ============

class DecisionCoordinator:
    """
    多Agent决策协调器

    协调多个Agent的分析，形成共识或报告分歧
    """

    def __init__(self, registry: AgentRegistry = None):
        self.registry = registry or AgentRegistry()
        self._debate_history: List[DebateMessage] = []

    def analyze_with_all(self, context: MarketContext) -> Dict[str, AgentResponse]:
        """使用所有Agent分析"""
        results = {}
        for agent in self.registry.get_all():
            try:
                results[agent.agent_id] = agent.analyze(context)
            except Exception as e:
                results[agent.agent_id] = AgentResponse(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    signal=SignalType.ERROR,
                    confidence=0,
                    score=0,
                    reasoning=f"分析失败: {e}"
                )
        return results

    def get_consensus(self, results: Dict[str, AgentResponse], ticker: str = "", date_str: str = None, context: MarketContext = None) -> AgentResponse:
        """计算共识信号，支持行业加权"""
        if not results:
            return AgentResponse(
                agent_id="consensus",
                agent_name="Consensus",
                signal=SignalType.NEUTRAL,
                confidence=0,
                score=0,
                reasoning="无结果"
            )

        # 获取行业感知权重
        weights = {}
        regime = None
        if ticker:
            try:
                from scanner.industry_matrix import detect_industry, get_agent_weights
                industry, _ = detect_industry(ticker)
                matrix_file = Path(__file__).parent.parent.parent / "feedback" / "industry_matrix.json"
                trained = {}
                if matrix_file.exists():
                    import json as _j
                    trained = _j.loads(matrix_file.read_text())
                weights = get_agent_weights(industry, trained)
            except Exception:
                pass

        # 市场机制感知权重调整
        regime_features = {}
        try:
            from scanner.regime_weights import detect_regime, apply_regime_weights
            from scanner.macro_features import fetch_macro_features

            regime = detect_regime(date_str)
            regime_features = fetch_macro_features(date_str)
            if regime_features.get("regime"):
                regime = regime_features["regime"]
            if regime and weights:
                weights = apply_regime_weights(weights, regime)
            # V5: ML regime router overlay
            try:
                from scanner.regime_router import RegimeRouter
                router = RegimeRouter()
                router_weights = router.get_weights(regime=regime, features=regime_features)
                if router_weights:
                    for agent_id in weights:
                        if agent_id in router_weights:
                            weights[agent_id] = (weights[agent_id] + router_weights[agent_id]) / 2
                    total_rw = sum(weights.values())
                    if total_rw > 0:
                        weights = {k: v / total_rw for k, v in weights.items()}
            except Exception:
                pass
        except Exception:
            regime = None

        # 加载相关性矩阵 (P1 优化: 多样性惩罚)
        corr_matrix = {}
        try:
            corr_file = Path(__file__).parent.parent.parent / "feedback" / "agent_correlation.json"
            if corr_file.exists():
                import json as _j
                corr_matrix = _j.loads(corr_file.read_text()).get("correlation_matrix", {})
        except Exception:
            pass

        # 统计信号 (加权 + 多样性调整)
        signal_counts = {SignalType.BULLISH: 0.0, SignalType.NEUTRAL: 0.0, SignalType.BEARISH: 0.0}
        total_score = 0.0
        total_weight = 0.0
        total_confidence = 0.0
        all_findings = []
        all_risks = []
        weighted_findings = []
        
        adjusted_weights = {}

        # 获取全局优化权重作为默认底座
        global_weights = {}
        try:
            _gw_file = Path(__file__).parent.parent.parent / "feedback" / "weights.json"
            if _gw_file.exists():
                import json as _j
                global_weights = _j.loads(_gw_file.read_text()).get("consensus_weights", {})
                if not global_weights:
                    global_weights = _j.loads(_gw_file.read_text()) # fallback format
        except Exception:
            pass

        # 滚动 IC 动态权重覆盖
        rolling_ic_weights = {}
        try:
            from scanner.rolling_ic import load_rolling_ic_weights
            rolling_ic_weights = load_rolling_ic_weights() or {}
        except Exception:
            pass

        for agent_id, response in results.items():
            # 获取该 Agent 初始权重 (行业矩阵 > 全局优化 > 等权)
            if weights and agent_id in weights:
                w = weights[agent_id]
            else:
                w = global_weights.get(agent_id, 1.0 / len(results))

            # 滚动 IC 覆盖：与当前权重取均值，使动态权重逐步生效
            if rolling_ic_weights and agent_id in rolling_ic_weights:
                w = 0.5 * w + 0.5 * rolling_ic_weights[agent_id]

            # coverage_confidence 降权：模型适用性低时减少影响力
            w *= response.coverage_confidence

            # 多样性惩罚 (P1)
            penalty = 1.0
            if corr_matrix:
                for processed_agent in adjusted_weights.keys():
                    corr = corr_matrix.get(agent_id, {}).get(processed_agent, 0)
                    if corr > 0.7:
                        penalty *= (1.0 - (corr - 0.7)) # 惩罚因子

            adjusted_w = w * penalty
            adjusted_weights[agent_id] = adjusted_w

            if response.signal in signal_counts:
                signal_counts[response.signal] += adjusted_w
            total_score += response.score * adjusted_w
            total_confidence += response.confidence * adjusted_w
            total_weight += adjusted_w
            all_findings.extend(response.key_findings)
            all_risks.extend(response.risks)
            
            # 记录加权发现
            if response.key_findings:
                weighted_findings.append((adjusted_w, response.agent_name, response.key_findings[0]))

        # 归一化
        if total_weight > 0:
            total_score /= total_weight
            total_confidence /= total_weight

        # 加权多数决
        consensus_signal = max(signal_counts, key=signal_counts.get)

        # 构建推理说明
        regime_note = ""
        if regime:
            regime_labels = {
                "BULL_LOW_VOL": "牛市低波动", "BULL_HIGH_VOL": "牛市高波动",
                "BEAR_LOW_VOL": "熊市低波动", "BEAR_HIGH_VOL": "熊市高波动",
                "SIDEWAYS": "震荡市",
            }
            regime_label = regime_labels.get(regime, regime)
            regime_note = f" | 市场机制: {regime_label}"

        # P2: 概率校准 (Probability Calibration)
        calibrated_confidence = min(0.95, total_confidence)
        try:
            from scanner.probability_calibrator import calibrate_confidence
            calibrated_confidence = calibrate_confidence(total_score, calibrated_confidence, "consensus")
        except Exception:
            pass

        # Meta-model score blending (50/50 when model is loaded)
        try:
            from scanner.meta_model import MetaModel
            mm = MetaModel.load()
            if mm is not None:
                agent_scores_dict = {aid: resp.score for aid, resp in results.items()}
                mm_score = mm.predict(agent_scores_dict)
                total_score = 0.5 * total_score + 0.5 * mm_score
        except Exception:
            pass

        result = AgentResponse(
            agent_id="consensus",
            agent_name="多Agent共识",
            signal=consensus_signal,
            confidence=calibrated_confidence,
            score=total_score,
            reasoning=f"基于{len(results)}个Agent的共识分析{regime_note}",
            key_findings=all_findings[:5],
            risks=all_risks[:3],
        )

        # V5: Risk Manager veto layer
        try:
            from scanner.risk_manager import RiskManager
            ctx_for_risk = context
            if ctx_for_risk is None:
                for r in results.values():
                    meta_ctx = r.metadata.get("context")
                    if meta_ctx and hasattr(meta_ctx, "ticker"):
                        ctx_for_risk = meta_ctx
                        break
            if ctx_for_risk is None:
                beta = 1.0
                max_dd = 0.0
                for r in results.values():
                    if r.beta and r.beta != 1.0:
                        beta = r.beta
                    factors = r.metadata.get("factors", {})
                    if factors:
                        break
                ctx_for_risk = MarketContext(ticker=ticker or "UNKNOWN", beta_1y=beta, max_drawdown=max_dd)
            vix = regime_features.get("vix") if regime_features else None
            rm = RiskManager()
            verdict = rm.evaluate(
                ctx_for_risk, result, results, regime=regime, vix=vix
            )
            result = rm.apply_veto(result, verdict)
        except Exception:
            pass

        # V5: Kelly position sizing (drawdown-aware payoff ratio from context)
        try:
            from scanner.kelly_sizer import compute_position_size
            max_dd_pct = 0.0
            if ctx_for_risk is not None:
                max_dd_pct = abs(getattr(ctx_for_risk, "max_drawdown", 0) or 0)
                if max_dd_pct <= 1.0:
                    max_dd_pct *= 100.0
            position = compute_position_size(
                result.score,
                result.confidence,
                signal=result.signal.value,
                max_drawdown_pct=max_dd_pct,
            )
            verdict = result.metadata.get("risk_verdict", {})
            cap = verdict.get("position_cap_pct", 100)
            if cap < 100 and position["position_pct"] > cap:
                position["position_pct"] = cap
                position["rationale"] += f" (capped at {cap}%)"
            result.metadata["position_sizing"] = position
            result.metadata["position_pct"] = position.get("position_pct", 0)
        except Exception:
            pass

        if regime_features:
            result.metadata["regime_features"] = regime_features

        # V5: 10x multi-factor overlay (optional metadata)
        try:
            from scanner.ten_x_screener import attach_ten_x_to_consensus
            attach_ten_x_to_consensus(result, context, results)
        except Exception:
            pass

        # 对抗性校验：全员看多时触发过热警告
        valid_results = {k: v for k, v in results.items() if v.signal != SignalType.ERROR}
        if valid_results and sum(1 for r in valid_results.values() if r.signal == SignalType.BULLISH) == len(valid_results):
            result.risks.append("⚠️ 全员看多警告：所有Agent一致看多，历史上此类共识往往意味着估值偏高")
            ctx_pe = list(valid_results.values())[0].metadata.get("factors", {})
            # 尝试从第一个结果获取PE信息
            for r in valid_results.values():
                meta_ctx = r.metadata.get("context")
                if meta_ctx and hasattr(meta_ctx, "pe") and meta_ctx.pe > 30:
                    result.risks.append(f"⚠️ 当前PE={meta_ctx.pe:.1f}，估值偏高，建议谨慎设置止损")
                    break

        return result

    def add_debate_message(self, msg: DebateMessage):
        """添加辩论消息"""
        self._debate_history.append(msg)

    def get_debate_history(self) -> List[DebateMessage]:
        """获取辩论历史"""
        return self._debate_history

    def run_debate(self, context: MarketContext, rounds: int = 2) -> Dict[str, AgentResponse]:
        """
        运行多轮辩论

        参数:
            context: 市场上下文
            rounds: 辩论轮数

        返回:
            各Agent最终立场
        """
        # 第1轮：各自独立分析
        current_results = self.analyze_with_all(context)

        for round_num in range(rounds - 1):
            # 构建辩论摘要
            debate_summary = self._build_debate_summary(current_results)

            # 每个Agent根据其他Agent的观点调整立场
            for agent_id, result in current_results.items():
                if result.signal == SignalType.ERROR:
                    continue

                # 找到分歧最大的Agent
                dissent = self._find_disagreement(current_results, agent_id)

                # 更新结果（元胞自动机风格）
                result.key_findings.append(f"[辩论{round_num+1}] 考虑{dissent}观点")

        # 少数派报告（5:1 或 4:1 时）
        valid_results = {k: v for k, v in current_results.items() if v.signal != SignalType.ERROR}
        bearish_agents = [aid for aid, r in valid_results.items() if r.signal == SignalType.BEARISH]
        if 1 <= len(bearish_agents) <= 2 and len(valid_results) >= 4:
            minority_report = {
                "minority_agents": bearish_agents,
                "minority_report": "少数派反对意见: " + "; ".join(
                    current_results[aid].reasoning[:200] for aid in bearish_agents
                )
            }
            for r in current_results.values():
                r.metadata["minority_report"] = minority_report

        return current_results

    def _build_debate_summary(self, results: Dict[str, AgentResponse]) -> str:
        """构建辩论摘要"""
        lines = ["=== Agent观点摘要 ==="]
        for agent_id, result in results.items():
            if result.signal != SignalType.ERROR:
                lines.append(f"{result.agent_name}: {result.signal.value} ({result.score:.1f}/10)")
        return "\n".join(lines)

    def _find_disagreement(self, results: Dict[str, AgentResponse], agent_id: str) -> str:
        """找到与当前Agent分歧最大的Agent"""
        target = results.get(agent_id)
        if not target:
            return "其他Agent"

        max_diff = 0
        max_diff_agent = "其他Agent"

        for other_id, other in results.items():
            if other_id == agent_id or other.signal == SignalType.ERROR:
                continue
            diff = abs(target.score - other.score)
            if diff > max_diff:
                max_diff = diff
                max_diff_agent = other.agent_name

        return max_diff_agent


# ============ DebateProtocol - Agent间辩论协议 ============

class DebateProtocol:
    """
    Agent辩论协议

    定义Agent之间的辩论规则和信息交换格式
    """

    def __init__(self, coordinator: DecisionCoordinator):
        self.coordinator = coordinator
        self.debate_rounds = 0

    def initiate_debate(self, context: MarketContext, topic: str = "investment_decision") -> Dict[str, AgentResponse]:
        """
        发起辩论

        参数:
            context: 市场上下文
            topic: 辩论主题

        返回:
            辩论后的Agent立场
        """
        self.debate_rounds += 1

        # 收集各方初始立场
        initial_positions = self.coordinator.analyze_with_all(context)

        # 生成辩论消息
        messages = self._generate_debate_messages(initial_positions, topic)

        # 让各方回应辩论
        final_positions = self._collect_responses(context, messages)

        return final_positions

    def _generate_debate_messages(self, positions: Dict[str, AgentResponse], topic: str) -> List[DebateMessage]:
        """生成辩论消息"""
        messages = []

        for agent_id, position in positions.items():
            if position.signal == SignalType.ERROR:
                continue

            msg = DebateMessage(
                from_agent=position.agent_name,
                topic=topic,
                content=f"我的立场是{position.signal.value}({position.score:.1f}/10): {position.reasoning[:200]}..."
            )
            messages.append(msg)
            self.coordinator.add_debate_message(msg)

        return messages

    def _collect_responses(self, context: MarketContext, messages: List[DebateMessage]) -> Dict[str, AgentResponse]:
        """收集Agent对辩论的回应"""
        # 简化：直接返回分析结果（实际可以加入更复杂的响应逻辑）
        return self.coordinator.analyze_with_all(context)

    def get_debate_summary(self) -> str:
        """获取辩论摘要"""
        history = self.coordinator.get_debate_history()
        if not history:
            return "暂无辩论记录"

        lines = [f"辩论轮次: {self.debate_rounds}", "=" * 40]
        for msg in history[-5:]:  # 最近5条
            lines.append(f"[{msg.from_agent}] {msg.content[:100]}...")

        return "\n".join(lines)


# ============ 全局实例和快捷函数 ============

_global_registry: Optional[AgentRegistry] = None
_global_coordinator: Optional[DecisionCoordinator] = None


def get_registry() -> AgentRegistry:
    """获取全局Agent注册中心"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry


def get_coordinator() -> DecisionCoordinator:
    """获取全局协调器"""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = DecisionCoordinator(get_registry())
    return _global_coordinator


def get_agent(agent_id: str) -> Optional[BaseAgent]:
    """获取指定Agent"""
    return get_registry().get(agent_id)


def analyze_with_agents(context: MarketContext) -> Dict[str, AgentResponse]:
    """使用所有Agent分析"""
    return get_coordinator().analyze_with_all(context)
