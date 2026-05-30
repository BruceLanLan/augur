# -*- coding: utf-8 -*-
"""
augur.optional_deps - Graceful degradation for optional dependencies

Provides consistent import checking and user-friendly error messages
when optional packages are not installed.
"""

import importlib
from typing import Tuple


# Registry: package_name -> (feature_description, install_extra)
OPTIONAL_DEPS_REGISTRY = {
    "yfinance": (
        "real-time market data fetching",
        "pip install 'augur-agents[data]'",
    ),
    "augur.data": (
        "real-time market data fetching",
        "pip install 'augur-agents[data]'",
    ),
    "apscheduler": (
        "scheduled watchlist analysis (cron daemon)",
        "pip install 'augur-agents[cron]'",
    ),
    "telegram": (
        "Telegram bot integration",
        "pip install 'augur-agents[telegram]'",
    ),
    "slack_bolt": (
        "Slack bot integration",
        "pip install 'augur-agents[slack]'",
    ),
    "slack_sdk": (
        "Slack bot integration",
        "pip install 'augur-agents[slack]'",
    ),
    "uvicorn": (
        "REST API server",
        "pip install 'augur-agents[api]'",
    ),
    "fastapi": (
        "REST API server",
        "pip install 'augur-agents[api]'",
    ),
}


def is_available(package_name: str) -> bool:
    """Check if a package is importable without raising.

    Args:
        package_name: The package/module name to check.

    Returns:
        True if importable, False otherwise.
    """
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False


def require_optional(
    package_name: str,
    feature_name: str = "",
    install_extra: str = "",
) -> None:
    """Verify a package is available; raise a clear error if not.

    Args:
        package_name: The package/module name to check.
        feature_name: Human-readable feature that needs this package.
        install_extra: The pip install command to install it.

    Raises:
        ImportError: With a user-friendly message including install instructions.
    """
    if is_available(package_name):
        return

    # Look up registry defaults if not provided
    if not feature_name or not install_extra:
        registry_entry = OPTIONAL_DEPS_REGISTRY.get(package_name)
        if registry_entry:
            if not feature_name:
                feature_name = registry_entry[0]
            if not install_extra:
                install_extra = registry_entry[1]

    # Build descriptive error message
    if not feature_name:
        feature_name = f"this feature"
    if not install_extra:
        install_extra = f"pip install {package_name}"

    msg = (
        f"Package '{package_name}' is required for {feature_name} but is not installed.\n"
        f"  Install with: {install_extra}\n"
        f"  Core commands (analyze, consensus, list-personas) still work without it."
    )
    raise ImportError(msg)


def get_install_hint(package_name: str) -> Tuple[str, str]:
    """Get the feature description and install command for a package.

    Args:
        package_name: The package/module name.

    Returns:
        Tuple of (feature_description, install_command).
    """
    entry = OPTIONAL_DEPS_REGISTRY.get(package_name)
    if entry:
        return entry
    return (f"functionality requiring {package_name}", f"pip install {package_name}")
