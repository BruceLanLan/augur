# -*- coding: utf-8 -*-
"""Tests for augur.plugins - Plugin System"""

import pytest
import importlib.metadata as importlib_metadata
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


class TestPluginEntryPointDiscovery:
    """Tests for entry-point-based plugin discovery."""

    def test_load_plugins_with_mocked_entry_points(self, monkeypatch):
        """load_plugins discovers plugins via entry_points and registers them."""
        from unittest.mock import MagicMock

        class _FakeEP:
            def __init__(self, name, cls):
                self.name = name
                self._cls = cls

            def load(self):
                return self._cls

        class EntryPointPlugin(PluginBase):
            name = "ep_plugin"
            version = "0.5.0"
            description = "from entry_point"

        fake_eps = [_FakeEP("ep_plugin", EntryPointPlugin)]
        fake_collection = MagicMock()
        fake_collection.select.return_value = fake_eps
        monkeypatch.setattr(
            importlib_metadata, "entry_points", lambda *a, **kw: fake_collection
        )

        manager = PluginManager()
        discovered = manager.load_plugins()

        assert len(discovered) == 1
        assert discovered[0].name == "ep_plugin"
        assert discovered[0].version == "0.5.0"
        assert manager.is_loaded() is True
        assert manager.get_plugin("ep_plugin") is not None

    def test_load_plugins_skips_failing_entry_point(self, monkeypatch):
        """An entry_point that raises during load() is silently skipped."""
        from unittest.mock import MagicMock

        class _BadEP:
            name = "bad"
            def load(self):
                raise ImportError("nope")

        class _GoodEP:
            name = "good"
            def load(self):
                return GoodPlugin

        class GoodPlugin(PluginBase):
            name = "good_plugin"
            version = "1.2.3"
            description = "ok"

        fake_eps = [_BadEP(), _GoodEP()]
        fake_collection = MagicMock()
        fake_collection.select.return_value = fake_eps
        monkeypatch.setattr(
            importlib_metadata, "entry_points", lambda *a, **kw: fake_collection
        )

        manager = PluginManager()
        discovered = manager.load_plugins()

        assert len(discovered) == 1
        assert discovered[0].name == "good_plugin"
        assert manager.get_plugin("bad") is None
        assert manager.get_plugin("good_plugin") is not None

    def test_load_plugins_uses_fallback_api(self, monkeypatch):
        """Older importlib.metadata returns dict; load_plugins still works."""
        fake_dict = {"augur.plugins": []}

        monkeypatch.setattr(
            importlib_metadata, "entry_points", lambda *a, **kw: fake_dict
        )
        # Force hasattr(eps, "select") == False path
        manager = PluginManager()
        discovered = manager.load_plugins()
        assert discovered == []
        assert manager.is_loaded() is True

    def test_load_plugins_swallows_metadata_errors(self, monkeypatch):
        """If entry_points() itself raises, load_plugins returns []. """

        def _raise(*a, **kw):
            raise OSError("metadata broken")

        monkeypatch.setattr(importlib_metadata, "entry_points", _raise)
        manager = PluginManager()
        discovered = manager.load_plugins()
        assert discovered == []
        assert manager.is_loaded() is True


class TestPluginRegistry:
    """Tests for the in-memory plugin registry semantics."""

    def test_register_plugin_overwrites_same_name(self):
        """register_plugin with the same name overwrites the previous entry."""
        manager = PluginManager()
        p1 = MockPlugin()
        p2 = MockPlugin()  # same name
        manager.register_plugin(p1)
        manager.register_plugin(p2)
        assert len(manager.list_plugins()) == 1
        # latest instance wins
        assert manager.get_plugin("mock_plugin").instance is p2

    def test_deactivate_nonexistent_returns_false(self):
        """deactivate_plugin returns False for an unknown plugin name."""
        manager = PluginManager()
        assert manager.deactivate_plugin("ghost") is False

    def test_deactivate_failure_returns_false(self):
        """deactivate_plugin returns False when plugin.deactivate() raises."""
        class Crashy(PluginBase):
            name = "crashy"
            version = "0.0.1"
            description = ""
            def deactivate(self):
                raise RuntimeError("boom")

        manager = PluginManager()
        manager.register_plugin(Crashy())
        manager.activate_plugin("crashy")
        # Even if activated=true was set, deactivate raising flips it back to False
        # only if the manager catches the exception; here the exception is caught.
        result = manager.deactivate_plugin("crashy")
        assert result is False


class TestPluginHotReload:
    """Tests for hot-reload style behavior (re-load + re-register)."""

    def test_hot_reload_replaces_existing_instance(self):
        """Re-registering under the same name yields a fresh instance."""
        manager = PluginManager()
        old = MockPlugin()
        manager.register_plugin(old)
        manager.activate_plugin("mock_plugin")
        assert manager.get_plugin("mock_plugin").instance is old

        new = MockPlugin()
        manager.register_plugin(new)
        info = manager.get_plugin("mock_plugin")
        # new instance wins
        assert info.instance is new
        # active flag is reset to False on re-register
        assert info.active is False

    def test_hot_reload_preserves_is_loaded_flag(self):
        """Calling load_plugins again does not unset is_loaded()."""
        manager = PluginManager()
        manager.load_plugins()
        assert manager.is_loaded()
        manager.load_plugins()
        assert manager.is_loaded() is True

    def test_hot_reload_full_lifecycle(self):
        """After reload, activate/deactivate still work on the new instance."""
        manager = PluginManager()
        manager.register_plugin(MockPlugin())
        # simulate hot-reload by replacing the instance
        fresh = MockPlugin()
        manager.register_plugin(fresh)

        assert manager.activate_plugin("mock_plugin") is True
        assert fresh.activated is True
        assert manager.get_plugin("mock_plugin").active is True

        assert manager.deactivate_plugin("mock_plugin") is True
        assert fresh.deactivated is True
        assert manager.get_plugin("mock_plugin").active is False
