# -*- coding: utf-8 -*-
"""
scanner — 多Agent分析引擎 (Personas Only)

仅包含 Agent Personas 系统，其他扫描模块按需扩展。
"""

from scanner.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType, DebateMessage
from scanner.personas.registry import AgentRegistry, DecisionCoordinator, DebateProtocol
from scanner.personas.arps import ArpsAgent
from scanner.personas.aschenbrenner import AschenbrennerAgent
from scanner.personas.buffett import BuffettAgent
from scanner.personas.cathie_wood import CathieWoodAgent
from scanner.personas.dalio import DalioAgent
from scanner.personas.dayu import DayuAgent
from scanner.personas.fisher import FisherAgent
from scanner.personas.graham import GrahamAgent
from scanner.personas.lynch import LynchAgent
from scanner.personas.marks import MarksAgent
from scanner.personas.munger import MungerAgent
from scanner.personas.soros import SorosAgent

__all__ = [
    "BaseAgent", "MarketContext", "AgentResponse", "SignalType", "DebateMessage",
    "AgentRegistry", "DecisionCoordinator", "DebateProtocol",
    "ArpsAgent", "AschenbrennerAgent", "BuffettAgent", "CathieWoodAgent",
    "DalioAgent", "DayuAgent", "FisherAgent", "GrahamAgent",
    "LynchAgent", "MarksAgent", "MungerAgent", "SorosAgent",
]
