# -*- coding: utf-8 -*-
"""
scanner.persona_loader - Backward compatibility shim

All actual code is now in augur.persona_loader.
This module re-exports everything for backward compatibility.
"""

from augur.persona_loader import *  # noqa: F401,F403
from augur.persona_loader import YamlAgent, load_persona_yaml, load_personas_from_dir
