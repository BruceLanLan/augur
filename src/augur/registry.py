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
import math
import time
from datetime import datetime
from typing import Dict, List, Optional
from threading import RLock
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeoutError

from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType, DebateMessage

logger = logging.getLogger(__name__)

# ============ v8: Learning + Sentiment singletons ============
_singleton_lock = RLock()
_learning_engine = None
_sentiment_analyzer = None

def _get_learning_engine():
    global _learning_engine
    with _singleton_lock:
        if _learning_engine is None:
            from augur.learning import LearningEngine
            _learning_engine = LearningEngine()
        return _learning_engine


def _check_and_record_outcomes(le, ticker: str) -> None:
    """
    For any unresolved predictions on `ticker` older than 30 days,
    fetch the actual price change via yfinance and call record_outcome().
    Runs silently — never raises.
    """
    try:
        cutoff = time.time() - 30 * 86400
        pending = [
            p for p in le._predictions
            if p.get("ticker") == ticker
            and p.get("outcome") is None
            and p.get("timestamp", 0) <= cutoff
        ]
        if not pending:
            return

        # Fetch 35-day history to cover the 30-day window
        from augur.data import fetch_history
        hist = fetch_history(ticker, period="2mo")
        if not hist or len(hist) < 5:
            return

        closes_by_ts = {h.get("date"): h.get("close") for h in hist if h.get("close")}
        if not closes_by_ts:
            return

        sorted_closes = sorted(closes_by_ts.items())   # [(date_str, price), ...]
        last_close = sorted_closes[-1][1]
        if not last_close:
            return

        # Use ~30-day return (closest available bar to 30 days ago vs latest)
        target_ts = time.time() - 30 * 86400
        ref_close = sorted_closes[0][1]
        for date_str, close in sorted_closes:
            try:
                bar_ts = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
            except ValueError:
                continue
            if bar_ts <= target_ts:
                ref_close = close
        if not ref_close or ref_close == 0:
            return
        actual_return = (last_close - ref_close) / ref_close
        le.record_outcome(ticker, actual_return, min_age_days=30)
    except Exception:
        pass


def _get_sentiment_analyzer():
    global _sentiment_analyzer
    with _singleton_lock:
        if _sentiment_analyzer is None:
            from augur.sentiment import SentimentAnalyzer
            _sentiment_analyzer = SentimentAnalyzer()
        return _sentiment_analyzer


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
        """Auto-load YAML personas from personas/custom/ next to repo root.

        Surface errors via logging so silent persona load failures are visible
        to operators. Per-file failures are already logged inside
        ``load_personas_from_dir``; we only log top-level (import / dir discovery)
        failures here.
        """
        try:
            from augur.persona_loader import load_personas_from_dir
            # Try multiple locations for custom personas
            candidates = [
                Path(__file__).parent.parent.parent / "personas" / "custom",
                Path.cwd() / "personas" / "custom",
            ]
            for custom_dir in candidates:
                if custom_dir.exists():
                    loaded = 0
                    for agent in load_personas_from_dir(custom_dir):
                        with self._lock:
                            if agent.agent_id not in self._agents:  # never overwrite built-in Python personas
                                self._agents[agent.agent_id] = agent
                                loaded += 1
                    if loaded:
                        logger.info(
                            "Loaded %d YAML persona(s) from %s", loaded, custom_dir
                        )
                    break
        except Exception as exc:  # pragma: no cover - defensive top-level guard
            logger.error(
                "Failed to register YAML personas: %s: %s",
                type(exc).__name__, exc,
                exc_info=True,
            )

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
        with self._lock:
            return self._agents.get(agent_id)

    def get_all(self) -> List[BaseAgent]:
        """Get all agents"""
        with self._lock:
            return list(self._agents.values())

    def list_agents(self) -> List[Dict]:
        """List all agents info"""
        with self._lock:
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

    def analyze_with_all(
        self,
        context: MarketContext,
        enabled_personas: Optional[List[str]] = None,
    ) -> Dict[str, AgentResponse]:
        """Analyze with all agents in parallel using ThreadPoolExecutor.

        When ``enabled_personas`` is non-empty, only those agent IDs are run.
        An empty list or ``None`` runs every registered agent.
        """
        t0 = time.perf_counter()
        results = {}
        agents = self.registry.get_all()
        if enabled_personas:
            allowed = set(enabled_personas)
            agents = [a for a in agents if a.agent_id in allowed]

        if not agents:
            self._last_analysis_ms = 0.0
            return results

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
                    except (TimeoutError, FutureTimeoutError):
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
        """Compute consensus signal with industry weighting."""
        from augur.consensus.engine import ConsensusEngine
        return ConsensusEngine().compute(
            results,
            ticker=ticker,
            date_str=date_str,
            context=context,
            analysis_ms=self._last_analysis_ms,
        )

    def add_debate_message(self, msg: DebateMessage) -> None:
        """Add a debate message to the history."""
        self._debate_history.append(msg)

    def get_debate_history(self) -> List[DebateMessage]:
        """Get debate history"""
        return self._debate_history

    def run_debate(
        self,
        context: MarketContext,
        rounds: int = 2,
        initial_results: Optional[Dict[str, AgentResponse]] = None,
        enabled_personas: Optional[List[str]] = None,
    ) -> Dict[str, AgentResponse]:
        """
        Run multi-round debate

        Args:
            context: Market context
            rounds: Number of debate rounds
            initial_results: Optional pre-computed agent responses to debate from
            enabled_personas: When initial_results is None, filter agents for first round

        Returns:
            Final agent positions
        """
        if initial_results is not None:
            current_results = initial_results
        else:
            current_results = self.analyze_with_all(context, enabled_personas=enabled_personas)

        for round_num in range(rounds - 1):
            debate_summary = self._build_debate_summary(current_results)

            for agent_id, result in current_results.items():
                if result.signal == SignalType.ERROR:
                    continue
                dissent = self._find_disagreement(current_results, agent_id)
                result.key_findings.append(
                    f"[Debate {round_num+1}] {debate_summary.splitlines()[0]}; "
                    f"considering {dissent} viewpoint"
                )

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
    with _singleton_lock:
        if _global_registry is None:
            _global_registry = AgentRegistry()
        return _global_registry


def get_coordinator() -> DecisionCoordinator:
    """Get global coordinator"""
    global _global_coordinator
    with _singleton_lock:
        if _global_coordinator is None:
            _global_coordinator = DecisionCoordinator(get_registry())
        return _global_coordinator


def get_agent(agent_id: str) -> Optional[BaseAgent]:
    """Get a specific agent"""
    return get_registry().get(agent_id)


def analyze_with_agents(context: MarketContext) -> Dict[str, AgentResponse]:
    """Analyze with all agents"""
    return get_coordinator().analyze_with_all(context)
