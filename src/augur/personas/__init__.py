# -*- coding: utf-8 -*-
"""
augur.personas - Agent persona system package

Provides:
  - Type definitions: SignalType, AgentResponse, MarketContext, DebateMessage
  - Base class: BaseAgent
  - 18 concrete agents
"""

from augur.personas.base import (
    SignalType,
    AgentResponse,
    MarketContext,
    DebateMessage,
    BaseAgent,
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
from augur.personas.dayu import DayuAgent
from augur.personas.thiel import ThielAgent
from augur.personas.duan_yongping import DuanYongpingAgent
from augur.personas.zhang_lei import ZhangLeiAgent
from augur.personas.li_lu import LiLuAgent
from augur.personas.dan_bin import DanBinAgent

__all__ = [
    # Types
    "SignalType", "AgentResponse", "MarketContext", "DebateMessage",
    # Base class
    "BaseAgent",
    # Concrete agents
    "BuffettAgent", "GrahamAgent", "LynchAgent", "DalioAgent",
    "MungerAgent", "SorosAgent", "MarksAgent", "CathieWoodAgent",
    "FisherAgent", "ArpsAgent", "AschenbrennerAgent",
    "DayuAgent", "ThielAgent", "DuanYongpingAgent",
    "ZhangLeiAgent", "LiLuAgent", "DanBinAgent",
]
