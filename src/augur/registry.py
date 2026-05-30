# -*- coding: utf-8 -*-
"""
Agent Registry and Decision Coordinator

Contains:
  - AgentRegistry (Agent registration center)
  - DecisionCoordinator (Multi-agent coordinator)
  - DebateProtocol (Agent debate protocol)
  - Global instances and convenience functions
"""

import logging
import time
from typing import Dict, List, Optional, Any
from threading import RLock
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType, DebateMessage


# ============ AgentRegistry ============

class AgentRegistry:
    """Agent registration center - manages and discovers agents"""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._lock = RLock()
        self._register_default_agents()

    def _register_default_agents(self):
        """Register default agents"""
        from augur.personas.buffett import BuffettAgent
        from augur.personas.graham import GrahamAgent
        from augur.personas.lynch import LynchAgent
        from augur.personas.dalio import DalioAgent
        from augur.personas.munger import MungerAgent
        from augur.personas.soros import SorosAgent
        from augur.personas.marks import MarksAgent
        from augur.personas.cathie_wood import CathieWoodAgent
        from augur.personas.fisher import FisherAgent
        from augur.personas.arps import ArpsAgent
        from augur.personas.aschenbrenner import AschenbrennerAgent
        from augur.personas.dayu import DayuAgent
        from augur.personas.thiel import ThielAgent
        from augur.personas.duan_yongping import DuanYongpingAgent
        from augur.personas.zhang_lei import ZhangLeiAgent
        from augur.personas.li_lu import LiLuAgent
        from augur.personas.dan_bin import DanBinAgent
        from augur.personas.serenity import SerenityAgent

        agents = [
            BuffettAgent(), GrahamAgent(), LynchAgent(), DalioAgent(), MungerAgent(),
            SorosAgent(), MarksAgent(), CathieWoodAgent(), FisherAgent(), ArpsAgent(),
            AschenbrennerAgent(),
            DayuAgent(),
            ThielAgent(),
            DuanYongpingAgent(), ZhangLeiAgent(), LiLuAgent(), DanBinAgent(),
            SerenityAgent(),
        ]
        for agent in agents:
            self._agents[agent.agent_id] = agent
        self._register_yaml_personas()

    def _register_yaml_personas(self):
        """Auto-load YAML personas from personas/custom/ next to repo root."""
        try:
            from augur.persona_loader import load_personas_from_dir
            # Try multiple locations for custom personas
            candidates = [
                Path(__file__).parent.parent.parent / "personas" / "custom",
                Path.cwd() / "personas" / "custom",
            ]
            for custom_dir in candidates:
                if custom_dir.exists():
                    for agent in load_personas_from_dir(custom_dir):
                        if agent.agent_id not in self._agents:  # never overwrite built-in Python personas
                            self._agents[agent.agent_id] = agent
                    break
        except Exception:
            pass

    def register(self, agent: BaseAgent) -> bool:
        """Register an agent"""
        with self._lock:
            self._agents[agent.agent_id] = agent
            return True

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent"""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
            return False

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID"""
        return self._agents.get(agent_id)

    def get_all(self) -> List[BaseAgent]:
        """Get all agents"""
        return list(self._agents.values())

    def list_agents(self) -> List[Dict]:
        """List all agents info"""
        return [agent.to_dict() for agent in self._agents.values()]


# ============ DecisionCoordinator ============

class DecisionCoordinator:
    """
    Multi-agent decision coordinator

    Coordinates analysis from multiple agents, forms consensus or reports dissent.
    """

    def __init__(self, registry: AgentRegistry = None):
        self.registry = registry or get_registry()
        self._debate_history: List[DebateMessage] = []
        self._last_analysis_ms: float = 0.0

    def analyze_with_all(self, context: MarketContext) -> Dict[str, AgentResponse]:
        """Analyze with all agents in parallel using ThreadPoolExecutor."""
        t0 = time.perf_counter()
        results = {}
        agents = self.registry.get_all()

        try:
            with ThreadPoolExecutor(max_workers=min(len(agents), 8)) as executor:
                future_to_agent = {
                    executor.submit(self._analyze_single, agent, context): agent
                    for agent in agents
                }
                for future in as_completed(future_to_agent):
                    agent = future_to_agent[future]
                    try:
                        results[agent.agent_id] = future.result(timeout=30)
                    except TimeoutError:
                        results[agent.agent_id] = AgentResponse(
                            agent_id=agent.agent_id,
                            agent_name=agent.name,
                            signal=SignalType.ERROR,
                            confidence=0,
                            score=0,
                            reasoning="Analysis timed out"
                        )
                    except Exception as e:
                        err_msg = str(e).split('\n', 1)[0][:200]
                        results[agent.agent_id] = AgentResponse(
                            agent_id=agent.agent_id,
                            agent_name=agent.name,
                            signal=SignalType.ERROR,
                            confidence=0,
                            score=0,
                            reasoning=f"Analysis failed: {err_msg}"
                        )
        except Exception:
            # Fallback to sequential if threading fails
            for agent in agents:
                results[agent.agent_id] = self._analyze_single(agent, context)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        # NOTE: _last_analysis_ms is stored on the instance and read by get_consensus.
        # Under concurrent requests on a singleton coordinator, this value may reflect
        # a different request's analysis time. This is acceptable because the timing is
        # informational telemetry (not a correctness concern). The consensus_ms value
        # in get_consensus is always accurate since it uses a local variable.
        self._last_analysis_ms = elapsed_ms
        logger.debug("analyze_with_all completed in %.1fms", elapsed_ms)
        return results

    def _analyze_single(self, agent: 'BaseAgent', context: MarketContext) -> AgentResponse:
        """Analyze with a single agent, handling exceptions."""
        try:
            return agent.analyze(context)
        except Exception as e:
            err_msg = str(e).split('\n', 1)[0][:200]
            return AgentResponse(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                signal=SignalType.ERROR,
                confidence=0,
                score=0,
                reasoning=f"Analysis failed: {err_msg}"
            )

    def get_consensus(self, results: Dict[str, AgentResponse], ticker: str = "", date_str: str = None, context: MarketContext = None) -> AgentResponse:
        """Compute consensus signal with industry weighting"""
        t0_consensus = time.perf_counter()
        if not results:
            return AgentResponse(
                agent_id="consensus",
                agent_name="Consensus",
                signal=SignalType.NEUTRAL,
                confidence=0,
                score=0,
                reasoning="No results"
            )

        # --- Industry-aware weights ---
        weights = {}
        regime = None
        if ticker:
            try:
                from scanner.industry_matrix import detect_industry, get_agent_weights
                industry, _ = detect_industry(ticker)
                matrix_file = Path(__file__).parent.parent / "feedback" / "industry_matrix.json"
                trained = {}
                if matrix_file.exists():
                    import json as _j
                    trained = _j.loads(matrix_file.read_text())
                weights = get_agent_weights(industry, trained)
            except Exception as e:
                logger.debug("Module not available: %s", e)
                pass

        # --- Regime-aware weight adjustment ---
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
        except Exception as e:
            logger.debug("Module not available: %s", e)
            regime = None

        # --- Correlation diversity penalty ---
        corr_matrix = {}
        try:
            corr_file = Path(__file__).parent.parent / "feedback" / "agent_correlation.json"
            if corr_file.exists():
                import json as _j
                corr_matrix = _j.loads(corr_file.read_text()).get("correlation_matrix", {})
        except Exception:
            pass

        # --- Signal counting and scoring ---
        signal_counts = {SignalType.BULLISH: 0.0, SignalType.NEUTRAL: 0.0, SignalType.BEARISH: 0.0}
        total_score = 0.0
        total_weight = 0.0
        total_confidence = 0.0
        all_findings = []
        all_risks = []
        adjusted_weights = {}

        # Global optimized weights as default base
        global_weights = {}
        try:
            _gw_file = Path(__file__).parent.parent / "feedback" / "weights.json"
            if _gw_file.exists():
                import json as _j
                global_weights = _j.loads(_gw_file.read_text()).get("consensus_weights", {})
                if not global_weights:
                    global_weights = _j.loads(_gw_file.read_text())
        except Exception:
            pass

        # Rolling IC dynamic weight override
        rolling_ic_weights = {}
        try:
            from scanner.rolling_ic import load_rolling_ic_weights
            rolling_ic_weights = load_rolling_ic_weights() or {}
        except Exception:
            pass

        for agent_id, response in results.items():
            if weights and agent_id in weights:
                w = weights[agent_id]
            else:
                w = global_weights.get(agent_id, 1.0 / len(results))

            if rolling_ic_weights and agent_id in rolling_ic_weights:
                w = 0.5 * w + 0.5 * rolling_ic_weights[agent_id]

            w *= response.coverage_confidence

            # Diversity penalty
            penalty = 1.0
            if corr_matrix:
                for processed_agent in adjusted_weights.keys():
                    corr = corr_matrix.get(agent_id, {}).get(processed_agent, 0)
                    if corr > 0.7:
                        penalty *= (1.0 - (corr - 0.7))

            adjusted_w = w * penalty
            adjusted_weights[agent_id] = adjusted_w

            if response.signal in signal_counts:
                signal_counts[response.signal] += adjusted_w
            total_score += response.score * adjusted_w
            total_confidence += response.confidence * adjusted_w
            total_weight += adjusted_w
            all_findings.extend(response.key_findings)
            all_risks.extend(response.risks)

        # Normalize
        if total_weight > 0:
            total_score /= total_weight
            total_confidence /= total_weight
        else:
            total_score = 0.0
            total_confidence = 0.0

        # Weighted majority vote
        consensus_signal = max(signal_counts, key=signal_counts.get)

        # Regime note
        regime_note = ""
        if regime:
            regime_labels = {
                "BULL_LOW_VOL": "Bull Low Vol", "BULL_HIGH_VOL": "Bull High Vol",
                "BEAR_LOW_VOL": "Bear Low Vol", "BEAR_HIGH_VOL": "Bear High Vol",
                "SIDEWAYS": "Sideways",
            }
            regime_label = regime_labels.get(regime, regime)
            regime_note = f" | Regime: {regime_label}"

        # --- Probability calibration ---
        calibrated_confidence = min(0.95, total_confidence)
        try:
            from scanner.probability_calibrator import calibrate_confidence
            calibrated_confidence = calibrate_confidence(total_score, calibrated_confidence, "consensus")
        except Exception:
            pass

        # --- Meta-model blending ---
        try:
            from scanner.meta_model import MetaModel
            mm = MetaModel.load()
            if mm is not None:
                agent_scores_dict = {aid: resp.score for aid, resp in results.items()}
                mm_score = mm.predict(agent_scores_dict)
                total_score = 0.5 * total_score + 0.5 * mm_score
        except Exception as e:
            logger.debug("Module not available: %s", e)
            pass

        result = AgentResponse(
            agent_id="consensus",
            agent_name="Multi-Agent Consensus",
            signal=consensus_signal,
            confidence=calibrated_confidence,
            score=total_score,
            reasoning=f"Consensus from {len(results)} agents{regime_note}",
            key_findings=all_findings[:5],
            risks=all_risks[:3],
        )

        # --- Risk Manager veto ---
        ctx_for_risk = context  # initialise outside try so Kelly block can access it
        try:
            from scanner.risk_manager import RiskManager
            if ctx_for_risk is None:
                for r in results.values():
                    meta_ctx = r.metadata.get("context")
                    if meta_ctx and hasattr(meta_ctx, "ticker"):
                        ctx_for_risk = meta_ctx
                        break
            if ctx_for_risk is None:
                beta = 1.0
                for r in results.values():
                    if r.beta and r.beta != 1.0:
                        beta = r.beta
                    break
                ctx_for_risk = MarketContext(ticker=ticker or "UNKNOWN", beta_1y=beta)
            vix = regime_features.get("vix") if regime_features else None
            rm = RiskManager()
            verdict = rm.evaluate(ctx_for_risk, result, results, regime=regime, vix=vix)
            result = rm.apply_veto(result, verdict)
        except Exception as e:
            logger.debug("Module not available: %s", e)
            pass

        # --- Kelly position sizing (simplified half-Kelly) ---
        try:
            sig = result.signal.value
            score = result.score
            conf = result.confidence
            # Half-Kelly: f = 0.5 * (p - (1-p)/b) clamped to 0-20%
            if sig == "bullish" and score >= 5:
                # edge = (score - 5) / 5  maps [5,10] → [0,1]
                edge = max(0, (score - 5) / 5)
                full_kelly = edge * conf
                pct = min(20.0, round(full_kelly * 0.5 * 100, 1))
            elif sig == "bearish":
                pct = 0.0
            else:
                pct = max(0.0, round((conf - 0.5) * 3.0, 1))

            position = {
                "position_pct": pct,
                "signal": sig,
                "score": round(score, 2),
                "confidence": round(conf, 3),
                "rationale": f"half-Kelly: {pct:.1f}% (score={score:.1f}, conf={conf:.0%})",
            }
            result.metadata["position_sizing"] = position
            result.metadata["position_pct"] = pct
        except Exception:
            pass

        if regime_features:
            result.metadata["regime_features"] = regime_features

        # 10x multi-factor overlay
        try:
            from scanner.ten_x_screener import attach_ten_x_to_consensus
            attach_ten_x_to_consensus(result, context, results)
        except Exception:
            pass

        # --- Adversarial overheating check ---
        valid_results = {k: v for k, v in results.items() if v.signal != SignalType.ERROR}
        if valid_results and sum(1 for r in valid_results.values() if r.signal == SignalType.BULLISH) == len(valid_results):
            result.risks.append("All agents bullish - historically this consensus often means overvaluation")
            for r in valid_results.values():
                meta_ctx = r.metadata.get("context")
                if meta_ctx and hasattr(meta_ctx, "pe") and meta_ctx.pe > 30:
                    result.risks.append(f"PE={meta_ctx.pe:.1f}, valuation elevated - consider stop-loss")
                    break

        # Clamp final score to valid range [0, 10]
        result.score = max(0.0, min(10.0, result.score))

        # --- Timing metadata ---
        consensus_ms = (time.perf_counter() - t0_consensus) * 1000
        logger.debug("get_consensus completed in %.1fms", consensus_ms)
        result.metadata["timing_ms"] = {
            "analysis_ms": self._last_analysis_ms,
            "consensus_ms": consensus_ms,
        }

        return result
        """Add a debate message"""
        self._debate_history.append(msg)

    def get_debate_history(self) -> List[DebateMessage]:
        """Get debate history"""
        return self._debate_history

    def run_debate(self, context: MarketContext, rounds: int = 2) -> Dict[str, AgentResponse]:
        """
        Run multi-round debate

        Args:
            context: Market context
            rounds: Number of debate rounds

        Returns:
            Final agent positions
        """
        current_results = self.analyze_with_all(context)

        for round_num in range(rounds - 1):
            debate_summary = self._build_debate_summary(current_results)

            for agent_id, result in current_results.items():
                if result.signal == SignalType.ERROR:
                    continue
                dissent = self._find_disagreement(current_results, agent_id)
                result.key_findings.append(f"[Debate {round_num+1}] Considering {dissent} viewpoint")

        # Minority report
        valid_results = {k: v for k, v in current_results.items() if v.signal != SignalType.ERROR}
        bearish_agents = [aid for aid, r in valid_results.items() if r.signal == SignalType.BEARISH]
        if 1 <= len(bearish_agents) <= 2 and len(valid_results) >= 4:
            minority_report = {
                "minority_agents": bearish_agents,
                "minority_report": "Minority dissent: " + "; ".join(
                    current_results[aid].reasoning[:200] for aid in bearish_agents
                )
            }
            for r in current_results.values():
                r.metadata["minority_report"] = minority_report

        return current_results

    def _build_debate_summary(self, results: Dict[str, AgentResponse]) -> str:
        """Build debate summary"""
        lines = ["=== Agent Positions ==="]
        for agent_id, result in results.items():
            if result.signal != SignalType.ERROR:
                lines.append(f"{result.agent_name}: {result.signal.value} ({result.score:.1f}/10)")
        return "\n".join(lines)

    def _find_disagreement(self, results: Dict[str, AgentResponse], agent_id: str) -> str:
        """Find the agent with maximum disagreement"""
        target = results.get(agent_id)
        if not target:
            return "other agents"

        max_diff = 0
        max_diff_agent = "other agents"

        for other_id, other in results.items():
            if other_id == agent_id or other.signal == SignalType.ERROR:
                continue
            diff = abs(target.score - other.score)
            if diff > max_diff:
                max_diff = diff
                max_diff_agent = other.agent_name

        return max_diff_agent


# ============ DebateProtocol ============

class DebateProtocol:
    """Agent debate protocol"""

    def __init__(self, coordinator: DecisionCoordinator):
        self.coordinator = coordinator
        self.debate_rounds = 0

    def initiate_debate(self, context: MarketContext, topic: str = "investment_decision") -> Dict[str, AgentResponse]:
        """Initiate a debate"""
        self.debate_rounds += 1
        initial_positions = self.coordinator.analyze_with_all(context)
        messages = self._generate_debate_messages(initial_positions, topic)
        final_positions = self._collect_responses(context, messages)
        return final_positions

    def _generate_debate_messages(self, positions: Dict[str, AgentResponse], topic: str) -> List[DebateMessage]:
        """Generate debate messages"""
        messages = []
        for agent_id, position in positions.items():
            if position.signal == SignalType.ERROR:
                continue
            msg = DebateMessage(
                from_agent=position.agent_name,
                topic=topic,
                content=f"My position is {position.signal.value} ({position.score:.1f}/10): {position.reasoning[:200]}..."
            )
            messages.append(msg)
            self.coordinator.add_debate_message(msg)
        return messages

    def _collect_responses(self, context: MarketContext, messages: List[DebateMessage]) -> Dict[str, AgentResponse]:
        """Collect agent responses to debate"""
        return self.coordinator.analyze_with_all(context)

    def get_debate_summary(self) -> str:
        """Get debate summary"""
        history = self.coordinator.get_debate_history()
        if not history:
            return "No debate records"
        lines = [f"Debate rounds: {self.debate_rounds}", "=" * 40]
        for msg in history[-5:]:
            lines.append(f"[{msg.from_agent}] {msg.content[:100]}...")
        return "\n".join(lines)


# ============ Global instances and convenience functions ============

_global_registry: Optional[AgentRegistry] = None
_global_coordinator: Optional[DecisionCoordinator] = None


def get_registry() -> AgentRegistry:
    """Get global agent registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry


def get_coordinator() -> DecisionCoordinator:
    """Get global coordinator"""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = DecisionCoordinator(get_registry())
    return _global_coordinator


def get_agent(agent_id: str) -> Optional[BaseAgent]:
    """Get a specific agent"""
    return get_registry().get(agent_id)


def analyze_with_agents(context: MarketContext) -> Dict[str, AgentResponse]:
    """Analyze with all agents"""
    return get_coordinator().analyze_with_all(context)
