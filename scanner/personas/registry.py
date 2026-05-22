# -*- coding: utf-8 -*-
"""
scanner.personas.registry - Backward compatibility shim

All actual code is now in augur.registry.
This module re-exports everything for backward compatibility.
"""

from augur.registry import *  # noqa: F401,F403
from augur.registry import (
    AgentRegistry,
    DecisionCoordinator,
    DebateProtocol,
    get_registry,
    get_coordinator,
    get_agent,
    analyze_with_agents,
)
