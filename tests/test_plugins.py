# -*- coding: utf-8 -*-
"""Tests for augur.plugins - Plugin System"""

import pytest
from augur.plugins import PluginBase, PluginManager, PluginInfo


class MockPlugin(PluginBase):
    name = "mock_plugin"
    version = "1.0.0"
    description = "A mock plugin for testing"

    def __init__(self):
        self.activated = False
        self.deactivated = False

    def activate(self):
        self.activated = True

    def deactivate(self):
        self.deactivated = True


class AnotherPlugin(PluginBase):
    name = "another_plugin"
    version = "2.0.0"
    description = "Another test plugin"


class TestPluginBase:
    def test_plugin_base_defaults(self):
        """PluginBase has default attributes."""
        p = PluginBase()
        assert p.name == "unnamed_plugin"
        assert p.version == "0.1.0"
        assert p.description == ""

    def test_plugin_base_activate_deactivate(self):
        """PluginBase activate/deactivate are no-ops."""
        p = PluginBase()
        p.activate()
        p.deactivate()


class TestPluginManager:
    def test_load_plugins_returns_list(self):
        """load_plugins returns a list (may be empty if no entry_points)."""
        manager = PluginManager()
        result = manager.load_plugins()
        assert isinstance(result, list)
        assert manager.is_loaded()

    def test_register_plugin(self):
        """register_plugin adds a plugin manually."""
        manager = PluginManager()
        plugin = MockPlugin()
        info = manager.register_plugin(plugin)
        assert info.name == "mock_plugin"
        assert info.version == "1.0.0"
        assert info.active is False

    def test_list_plugins(self):
        """list_plugins returns all registered plugins."""
        manager = PluginManager()
        manager.register_plugin(MockPlugin())
        manager.register_plugin(AnotherPlugin())
        plugins = manager.list_plugins()
        assert len(plugins) == 2
        names = [p.name for p in plugins]
        assert "mock_plugin" in names
        assert "another_plugin" in names

    def test_get_plugin(self):
        """get_plugin retrieves a specific plugin by name."""
        manager = PluginManager()
        manager.register_plugin(MockPlugin())
        info = manager.get_plugin("mock_plugin")
        assert info is not None
        assert info.name == "mock_plugin"

    def test_get_plugin_not_found(self):
        """get_plugin returns None for unknown name."""
        manager = PluginManager()
        assert manager.get_plugin("nonexistent") is None

    def test_activate_plugin(self):
        """activate_plugin calls plugin.activate()."""
        manager = PluginManager()
        plugin = MockPlugin()
        manager.register_plugin(plugin)
        result = manager.activate_plugin("mock_plugin")
        assert result is True
        assert plugin.activated is True
        info = manager.get_plugin("mock_plugin")
        assert info.active is True

    def test_deactivate_plugin(self):
        """deactivate_plugin calls plugin.deactivate()."""
        manager = PluginManager()
        plugin = MockPlugin()
        manager.register_plugin(plugin)
        manager.activate_plugin("mock_plugin")
        result = manager.deactivate_plugin("mock_plugin")
        assert result is True
        assert plugin.deactivated is True
        info = manager.get_plugin("mock_plugin")
        assert info.active is False

    def test_activate_nonexistent(self):
        """activate_plugin returns False for unknown plugin."""
        manager = PluginManager()
        assert manager.activate_plugin("nope") is False

    def test_activate_failure_returns_false(self):
        """activate_plugin returns False when plugin.activate() raises."""
        class BrokenPlugin(PluginBase):
            name = "broken"
            version = "0.0.1"
            description = "raises on activate"

            def activate(self):
                raise RuntimeError("activate failed")

        manager = PluginManager()
        manager.register_plugin(BrokenPlugin())
        assert manager.activate_plugin("broken") is False
        assert manager.get_plugin("broken").active is False

    def test_load_plugins_marks_loaded_once(self):
        """Repeated load_plugins calls are idempotent for is_loaded."""
        manager = PluginManager()
        manager.load_plugins()
        assert manager.is_loaded()
        again = manager.load_plugins()
        assert isinstance(again, list)
        assert manager.is_loaded()
