# -*- coding: utf-8 -*-
"""
scanner.personas - Backward compatibility shim

All actual code is now in augur.personas.
This module re-exports everything for backward compatibility.
"""

from augur.personas.base import (
    SignalType,
    AgentResponse,
    MarketContext,
    DebateMessage,
    BaseAgent,
)

from augur.registry import (
    AgentRegistry,
    DecisionCoordinator,
    DebateProtocol,
    get_registry,
    get_coordinator,
    get_agent,
    analyze_with_agents,
)

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

__all__ = [
    # Types
    "SignalType", "AgentResponse", "MarketContext", "DebateMessage",
    # Base class
    "BaseAgent",
    # Registry + coordination
    "AgentRegistry", "DecisionCoordinator", "DebateProtocol",
    # Convenience functions
    "get_registry", "get_coordinator", "get_agent", "analyze_with_agents",
    # Concrete agents
    "BuffettAgent", "GrahamAgent", "LynchAgent", "DalioAgent",
    "MungerAgent", "SorosAgent", "MarksAgent", "CathieWoodAgent",
    "FisherAgent", "ArpsAgent", "AschenbrennerAgent",
]
