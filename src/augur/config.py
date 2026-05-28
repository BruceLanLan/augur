# -*- coding: utf-8 -*-
"""
augur.config - Runtime configuration management

Loads from ~/.augur/config.yaml if exists, else falls back to config/agents.yaml.
Provides get_config(), set_config(), save_config() API.
"""

import threading
from pathlib import Path
from typing import Any, Dict, Optional
import copy

_config: Optional[Dict[str, Any]] = None
_config_path: Optional[Path] = None
_lock = threading.RLock()  # protect shared config state


def _find_config_file() -> Path:
    """Find config file: ~/.augur/config.yaml > config/agents.yaml (repo relative)"""
    user_config = Path.home() / ".augur" / "config.yaml"
    if user_config.exists():
        return user_config

    # Try relative to package source (repo root)
    candidates = [
        Path(__file__).parent.parent.parent / "config" / "agents.yaml",
        Path.cwd() / "config" / "agents.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Default to user config path (will be created on save)
    return user_config


def _load_config() -> Dict[str, Any]:
    """Load config from YAML file."""
    global _config, _config_path
    _config_path = _find_config_file()

    if _config_path.exists():
        try:
            import yaml
            _config = yaml.safe_load(_config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            _config = {}
    else:
        _config = {}

    return _config


def get_config() -> Dict[str, Any]:
    """Get the full configuration dictionary (thread-safe)."""
    global _config
    with _lock:
        if _config is None:
            _load_config()
        return copy.deepcopy(_config)


def set_config(key: str, value: Any) -> None:
    """Set a configuration value (dot-notation supported: 'per_agent.buffett'). Thread-safe."""
    global _config
    with _lock:
        if _config is None:
            _load_config()
        keys = key.split(".")
        target = _config
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value


def save_config() -> Path:
    """Save current config to ~/.augur/config.yaml. Thread-safe. Returns path saved to."""
    global _config, _config_path
    with _lock:
        if _config is None:
            _load_config()
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("pyyaml is required: pip install pyyaml") from exc
        save_path = Path.home() / ".augur" / "config.yaml"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(yaml.dump(_config, default_flow_style=False, allow_unicode=True), encoding="utf-8")
        _config_path = save_path
        return save_path


def reset_config() -> None:
    """Reset in-memory config (forces reload on next get_config). Thread-safe."""
    global _config, _config_path
    with _lock:
        _config = None
        _config_path = None
