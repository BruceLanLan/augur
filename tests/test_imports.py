# -*- coding: utf-8 -*-
"""Test that both augur.* and scanner.* imports work."""

import pytest


class TestAugurImports:
    """Test augur package imports."""

    def test_import_base_types(self):
        from augur.personas.base import SignalType, AgentResponse, MarketContext, DebateMessage, BaseAgent
        assert SignalType.BULLISH.value == "bullish"
        assert MarketContext is not None

    def test_import_registry(self):
        from augur.registry import AgentRegistry, DecisionCoordinator, DebateProtocol
        assert AgentRegistry is not None
        assert DecisionCoordinator is not None

    def test_import_top_level(self):
        from augur import BaseAgent, MarketContext, AgentResponse, SignalType
        from augur import AgentRegistry, DecisionCoordinator
        assert BaseAgent is not None

    def test_import_persona_loader(self):
        from augur.persona_loader import YamlAgent, load_persona_yaml, load_personas_from_dir
        assert YamlAgent is not None

    def test_import_config(self):
        from augur.config import get_config, set_config, save_config
        assert callable(get_config)

    def test_import_cli(self):
        from augur.cli import main
        assert callable(main)

    def test_import_mcp_server(self):
        from augur import mcp_server
        assert hasattr(mcp_server, 'create_server')
        assert hasattr(mcp_server, 'run_server')

    def test_import_api(self):
        from augur.api import app
        assert app is not None

    def test_import_soul(self):
        from augur.soul import SoulInjector
        assert SoulInjector is not None

    def test_import_coordinator(self):
        from augur.coordinator import DecisionCoordinator, DebateProtocol
        assert DecisionCoordinator is not None

    def test_import_all_agents(self):
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
        assert BuffettAgent is not None
        assert DanBinAgent is not None


class TestBackwardCompat:
    """Test scanner.* backward compatibility shims."""

    def test_scanner_base(self):
        from scanner.personas.base import SignalType, AgentResponse, MarketContext, DebateMessage, BaseAgent
        assert SignalType.BEARISH.value == "bearish"

    def test_scanner_registry(self):
        from scanner.personas.registry import AgentRegistry, DecisionCoordinator, DebateProtocol
        assert AgentRegistry is not None

    def test_scanner_persona_loader(self):
        from scanner.persona_loader import YamlAgent, load_persona_yaml
        assert YamlAgent is not None

    def test_scanner_init(self):
        from scanner import BaseAgent, MarketContext, AgentRegistry
        assert BaseAgent is not None

    def test_scanner_personas_init(self):
        from scanner.personas import BuffettAgent, GrahamAgent
        assert BuffettAgent is not None

    def test_scanner_agent_shims(self):
        from scanner.personas.buffett import BuffettAgent
        from scanner.personas.graham import GrahamAgent
        from scanner.personas.dalio import DalioAgent
        from scanner.personas.munger import MungerAgent
        from scanner.personas.soros import SorosAgent
        assert BuffettAgent is not None
        assert SorosAgent is not None
