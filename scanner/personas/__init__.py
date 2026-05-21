# -*- coding: utf-8 -*-
"""
scanner.personas — Agent人格系统 package

提供:
  - 类型定义: SignalType, AgentResponse, MarketContext, DebateMessage
  - 基类: BaseAgent
  - 注册中心: AgentRegistry
  - 协调器: DecisionCoordinator
  - 辩论协议: DebateProtocol
  - 11个具体Agent: BuffettAgent, GrahamAgent, LynchAgent, DalioAgent,
                    MungerAgent, SorosAgent, MarksAgent, CathieWoodAgent,
                    FisherAgent, ArpsAgent, AschenbrennerAgent
  - 快捷函数: get_registry, get_coordinator, get_agent, analyze_with_agents
"""

from scanner.personas.base import (
    SignalType,
    AgentResponse,
    MarketContext,
    DebateMessage,
    BaseAgent,
)

from scanner.personas.registry import (
    AgentRegistry,
    DecisionCoordinator,
    DebateProtocol,
    get_registry,
    get_coordinator,
    get_agent,
    analyze_with_agents,
)

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

__all__ = [
    # 类型
    "SignalType", "AgentResponse", "MarketContext", "DebateMessage",
    # 基类
    "BaseAgent",
    # 注册中心 + 协调
    "AgentRegistry", "DecisionCoordinator", "DebateProtocol",
    # 快捷函数
    "get_registry", "get_coordinator", "get_agent", "analyze_with_agents",
    # 具体Agent
    "BuffettAgent", "GrahamAgent", "LynchAgent", "DalioAgent",
    "MungerAgent", "SorosAgent", "MarksAgent", "CathieWoodAgent",
    "FisherAgent", "ArpsAgent", "AschenbrennerAgent",
]
