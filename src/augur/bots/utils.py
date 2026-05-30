# -*- coding: utf-8 -*-
"""
Shared utilities for Augur bot integrations.

Common helpers for ticker extraction, metric parsing, and validation
used across Telegram, Slack, WeChat, and Lark bots.
"""

import re
from typing import Optional, Dict


# Common stop words that match [A-Z]{1,5} but are not tickers
STOP_WORDS = frozenset({
    'I', 'A', 'IT', 'AT', 'AM', 'AN', 'AS', 'BE', 'BY', 'DO', 'GO',
    'IF', 'IN', 'IS', 'ME', 'MY', 'NO', 'OF', 'ON', 'OR', 'SO', 'TO',
    'UP', 'US', 'WE', 'HE', 'OK', 'THE', 'AND', 'BUT', 'FOR', 'NOT',
    'YOU', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT',
})


def extract_ticker(text: str) -> Optional[str]:
    """Extract ticker symbol from text, filtering out common stop words.

    Finds the first 2-5 character uppercase word that is not a common
    English stop word. Single-character matches are skipped entirely.

    Args:
        text: Input text to search for ticker symbols.

    Returns:
        Extracted ticker symbol or None if not found.
    """
    # Find all potential ticker matches (2-5 uppercase letters)
    candidates = re.findall(r'\b([A-Z]{2,5})\b', text.upper())
    for candidate in candidates:
        if candidate not in STOP_WORDS:
            return candidate
    return None


def parse_metrics(text: str) -> Dict[str, float]:
    """Parse key=value metric pairs from text.

    Shared across all bots for consistent metric extraction.

    Args:
        text: Input text containing key=value pairs.

    Returns:
        Dictionary mapping metric names to float values.
    """
    metrics = {}
    for match in re.finditer(r"(\w+)=([\d.]+)", text):
        key = match.group(1).strip().lower()
        try:
            metrics[key] = float(match.group(2))
        except ValueError:
            pass
    return metrics
