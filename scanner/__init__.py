# -*- coding: utf-8 -*-
"""
scanner - Backward compatibility shim

All actual code is now in the augur package.
This module re-exports everything for backward compatibility.
"""

from augur.personas.base import BaseAgent, MarketContext, AgentResponse, SignalType, DebateMessage
from augur.registry import AgentRegistry, DecisionCoordinator, DebateProtocol
from augur.personas.arps import ArpsAgent
from augur.personas.aschenbrenner import AschenbrennerAgent
from augur.personas.buffett import BuffettAgent
from augur.personas.cathie_wood import CathieWoodAgent
from augur.personas.dalio import DalioAgent
from augur.personas.dayu import DayuAgent
from augur.personas.fisher import FisherAgent
from augur.personas.graham import GrahamAgent
from augur.personas.lynch import LynchAgent
from augur.personas.marks import MarksAgent
from augur.personas.munger import MungerAgent
from augur.personas.soros import SorosAgent
from augur.personas.thiel import ThielAgent
from augur.personas.duan_yongping import DuanYongpingAgent
from augur.personas.zhang_lei import ZhangLeiAgent
from augur.personas.li_lu import LiLuAgent
from augur.personas.dan_bin import DanBinAgent
from augur.personas.serenity import SerenityAgent

__all__ = [
    "BaseAgent", "MarketContext", "AgentResponse", "SignalType", "DebateMessage",
    "AgentRegistry", "DecisionCoordinator", "DebateProtocol",
    "ArpsAgent", "AschenbrennerAgent", "BuffettAgent", "CathieWoodAgent",
    "DalioAgent", "DayuAgent", "FisherAgent", "GrahamAgent",
    "LynchAgent", "MarksAgent", "MungerAgent", "SorosAgent",
    "ThielAgent", "DuanYongpingAgent", "ZhangLeiAgent",
    "LiLuAgent", "DanBinAgent", "SerenityAgent",
]
