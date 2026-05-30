# -*- coding: utf-8 -*-
"""
augur.errors - Standard error response helpers

Provides consistent error formatting for both API and CLI contexts.
"""

from datetime import datetime, timezone


def error_response(
    detail: str,
    suggestion: str = "",
    code: str = "UNKNOWN_ERROR",
) -> dict:
    """Generate a standard error response dict.

    Args:
        detail: Human-readable error description.
        suggestion: Actionable suggestion for the user.
        code: Machine-readable error code.

    Returns:
        Dict with consistent error structure.
    """
    return {
        "status": "error",
        "detail": detail,
        "suggestion": suggestion,
        "code": code,
    }


def api_error_response(
    detail: str,
    suggestion: str = "",
    code: str = "UNKNOWN_ERROR",
    path: str = "",
) -> dict:
    """Generate a standard API error response with timestamp and path.

    Args:
        detail: Human-readable error description.
        suggestion: Actionable suggestion for the user.
        code: Machine-readable error code.
        path: Request path that triggered the error.

    Returns:
        Dict with consistent API error structure.
    """
    return {
        "status": "error",
        "detail": detail,
        "suggestion": suggestion,
        "code": code,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "path": path,
    }


# Common error messages with actionable suggestions
ERRORS = {
    "network_timeout": error_response(
        detail="Network request timed out",
        suggestion="Check your internet connection and try again. If using a proxy, verify proxy settings.",
        code="NETWORK_TIMEOUT",
    ),
    "missing_yfinance": error_response(
        detail="yfinance package is not installed",
        suggestion="Install with: pip install 'augur-agents[data]'  (core features still work without it)",
        code="MISSING_DEPENDENCY",
    ),
    "missing_apscheduler": error_response(
        detail="APScheduler package is not installed",
        suggestion="Install with: pip install 'augur-agents[cron]'  (manual cron-run still works without it)",
        code="MISSING_DEPENDENCY",
    ),
    "missing_telegram": error_response(
        detail="python-telegram-bot package is not installed",
        suggestion="Install with: pip install 'augur-agents[telegram]'  (CLI and API still work without it)",
        code="MISSING_DEPENDENCY",
    ),
    "missing_slack": error_response(
        detail="slack-bolt package is not installed",
        suggestion="Install with: pip install 'augur-agents[slack]'  (CLI and API still work without it)",
        code="MISSING_DEPENDENCY",
    ),
    "invalid_input": error_response(
        detail="Invalid input parameters",
        suggestion="Check the command help with --help for valid options and formats.",
        code="INVALID_INPUT",
    ),
    "rate_limited": error_response(
        detail="API rate limit exceeded",
        suggestion="Wait a few minutes before retrying. Consider reducing request frequency.",
        code="RATE_LIMITED",
    ),
    "persona_not_found": error_response(
        detail="Specified persona not found",
        suggestion="Run 'augur list-personas' to see all available persona IDs.",
        code="PERSONA_NOT_FOUND",
    ),
}
