# -*- coding: utf-8 -*-
"""
scanner.personas.base - Backward compatibility shim

All actual code is now in augur.personas.base.
This module re-exports everything for backward compatibility.
"""

from augur.personas.base import *  # noqa: F401,F403
from augur.personas.base import SignalType, AgentResponse, MarketContext, DebateMessage, BaseAgent
