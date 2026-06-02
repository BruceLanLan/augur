# -*- coding: utf-8 -*-
"""
augur.plugins - Plugin System

Provides a plugin architecture for extending Augur functionality.
Plugins are discovered via setuptools entry_points (group 'augur.plugins').
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import importlib.metadata


class PluginBase:
    """Base class for all Augur plugins.

    Subclass this and implement activate()/deactivate() to create a plugin.
    Register via setuptools entry_points group 'augur.plugins'.
    """

    name: str = "unnamed_plugin"
    version: str = "0.1.0"
    description: str = ""

    def activate(self) -> None:
        """Called when the plugin is activated."""
        pass

    def deactivate(self) -> None:
        """Called when the plugin is deactivated."""
        pass


@dataclass
class PluginInfo:
    """Information about a registered plugin."""
    name: str
    version: str
    description: str
    active: bool = False
    instance: Optional[object] = None


class PluginManager:
    """Manages plugin discovery, registration, and lifecycle.

    Discovers plugins via setuptools entry_points group 'augur.plugins'.
    """

    ENTRY_POINT_GROUP = "augur.plugins"

    def __init__(self):
        self._plugins: Dict[str, PluginInfo] = {}
        self._loaded: bool = False

    def load_plugins(self) -> List[PluginInfo]:
        """Discover and load all installed plugins via entry_points.

        Returns list of loaded PluginInfo objects.
        """
        discovered = []
        try:
            if hasattr(importlib.metadata, 'entry_points'):
                eps = importlib.metadata.entry_points()
                if hasattr(eps, "select"):
                    group_eps = eps.select(group=self.ENTRY_POINT_GROUP)
                else:
                    group_eps = eps.get(self.ENTRY_POINT_GROUP, [])
        except Exception:
            group_eps = []

        for ep in group_eps:
            try:
                plugin_cls = ep.load()
                instance = plugin_cls()
                info = PluginInfo(
                    name=getattr(instance, 'name', ep.name),
                    version=getattr(instance, 'version', '0.0.0'),
                    description=getattr(instance, 'description', ''),
                    active=False,
                    instance=instance,
                )
                self._plugins[info.name] = info
                discovered.append(info)
            except Exception:
                pass

        self._loaded = True
        return discovered

    def register_plugin(self, plugin: PluginBase) -> PluginInfo:
        """Manually register a plugin instance."""
        info = PluginInfo(
            name=plugin.name,
            version=plugin.version,
            description=plugin.description,
            active=False,
            instance=plugin,
        )
        self._plugins[info.name] = info
        return info

    def activate_plugin(self, name: str) -> bool:
        """Activate a registered plugin by name."""
        info = self._plugins.get(name)
        if not info or not info.instance:
            return False
        try:
            info.instance.activate()
            info.active = True
            return True
        except Exception:
            return False

    def deactivate_plugin(self, name: str) -> bool:
        """Deactivate a registered plugin by name."""
        info = self._plugins.get(name)
        if not info or not info.instance:
            return False
        try:
            info.instance.deactivate()
            info.active = False
            return True
        except Exception:
            return False

    def list_plugins(self) -> List[PluginInfo]:
        """Return list of all registered plugins."""
        return list(self._plugins.values())

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Get a specific plugin by name."""
        return self._plugins.get(name)

    def is_loaded(self) -> bool:
        """Check if plugins have been loaded."""
        return self._loaded
