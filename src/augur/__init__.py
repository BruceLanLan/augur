# -*- coding: utf-8 -*-
"""
augur - Multi-agent investment analysis system

Provides 18 investor persona agents with consensus decision making.
"""

__version__ = "7.5.0"

from augur.personas.base import (
    BaseAgent,
    MarketContext,
    AgentResponse,
    SignalType,
    DebateMessage,
)
from augur.registry import (
    AgentRegistry,
    DecisionCoordinator,
    DebateProtocol,
)

__all__ = [
    "BaseAgent",
    "MarketContext",
    "AgentResponse",
    "SignalType",
    "DebateMessage",
    "AgentRegistry",
    "DecisionCoordinator",
    "DebateProtocol",
]
