# -*- coding: utf-8 -*-
"""
augur.config - Runtime configuration management

Loads from ~/.augur/config.yaml if exists, else falls back to config/agents.yaml.
Provides get_config(), set_config(), save_config() API.
"""

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import copy

logger = logging.getLogger(__name__)

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
        except Exception as e:
            logger.warning("Failed to load config from %s: %s", _config_path, e)
            _config = {}
        if not isinstance(_config, dict):
            logger.warning("Config file %s did not parse as dict (got %s), using empty config", _config_path, type(_config).__name__)
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
            warnings = validate_config(_config)
            for w in warnings:
                logger.warning("Config validation: %s", w)
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
                if k in target:
                    logger.warning("Overwriting non-dict value at '%s' with nested dict", '.'.join(keys[:keys.index(k)+1]))
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


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate config structure and return a list of warning strings.

    Checks:
    - 'defaults' is a dict if present
    - 'per_agent' is a dict of strings if present
    - 'available_models' is a dict of lists if present

    Returns:
        List of warning messages (empty if all valid).
    """
    warnings: List[str] = []

    if "defaults" in config:
        if not isinstance(config["defaults"], dict):
            warnings.append(
                f"'defaults' should be a dict, got {type(config['defaults']).__name__}"
            )

    if "per_agent" in config:
        if not isinstance(config["per_agent"], dict):
            warnings.append(
                f"'per_agent' should be a dict, got {type(config['per_agent']).__name__}"
            )
        else:
            for key, val in config["per_agent"].items():
                if not isinstance(val, str):
                    warnings.append(
                        f"'per_agent.{key}' should be a string, got {type(val).__name__}"
                    )

    if "available_models" in config:
        if not isinstance(config["available_models"], dict):
            warnings.append(
                f"'available_models' should be a dict, got {type(config['available_models']).__name__}"
            )
        else:
            for key, val in config["available_models"].items():
                if not isinstance(val, list):
                    warnings.append(
                        f"'available_models.{key}' should be a list, got {type(val).__name__}"
                    )

    return warnings
