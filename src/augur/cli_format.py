# -*- coding: utf-8 -*-
"""
augur.cli_format - CLI output formatting helpers

Provides color, table, icon, and box formatting that respects --no-color mode.
"""

import os
import re

# ANSI color codes
_COLORS = {
    "green": "\033[32m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

# Signal icons: emoji vs text
_SIGNAL_ICONS = {
    "bullish": ("🟢", "[BUY]"),
    "bearish": ("🔴", "[SELL]"),
    "neutral": ("🟡", "[HOLD]"),
    "strong_buy": ("🟢🟢", "[STRONG BUY]"),
    "strong_sell": ("🔴🔴", "[STRONG SELL]"),
}


def _is_no_color() -> bool:
    """Check if color output is disabled via environment variable."""
    return os.environ.get("NO_COLOR", "") != ""


def color_text(text: str, color: str) -> str:
    """Apply ANSI color to text, respecting no-color mode.

    Args:
        text: The text to colorize.
        color: Color name (green, red, yellow, blue, cyan, magenta, bold, dim).

    Returns:
        Colored text string, or plain text if no-color mode is active.
    """
    if _is_no_color():
        return text
    code = _COLORS.get(color, "")
    if not code:
        return text
    return f"{code}{text}{_COLORS['reset']}"


def signal_icon(signal: str) -> str:
    """Return an appropriate icon for a signal value.

    Args:
        signal: Signal string (bullish, bearish, neutral, etc.)

    Returns:
        Emoji icon or text marker depending on no-color mode.
    """
    key = signal.lower().replace(" ", "_")
    pair = _SIGNAL_ICONS.get(key, ("*", f"[{signal.upper()}]"))
    if _is_no_color():
        return pair[1]
    return pair[0]


def format_table(headers: list, rows: list, col_sep: str = " | ") -> str:
    """Format data as an aligned table with dynamic column widths.

    Args:
        headers: List of column header strings.
        rows: List of lists (each inner list is a row of values).
        col_sep: Separator between columns.

    Returns:
        Formatted table string with aligned columns.
    """
    if not rows:
        return ""

    # Calculate column widths from headers and data
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Build header line
    header_line = col_sep.join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
    separator = "-" * len(header_line)

    # Build data lines
    lines = [header_line, separator]
    for row in rows:
        line = col_sep.join(
            str(cell).ljust(widths[i]) if i < len(widths) else str(cell)
            for i, cell in enumerate(row)
        )
        lines.append(line)

    return "\n".join(lines)


def format_box(lines: list, title: str = "") -> str:
    """Format lines inside a bordered box.

    Args:
        lines: List of strings to display inside the box.
        title: Optional title for the top border.

    Returns:
        Box-formatted string.
    """
    if not lines:
        return ""

    # Strip ANSI for width calculation
    ansi_escape = re.compile(r"\033\[[0-9;]*m")

    def visible_len(s):
        return len(ansi_escape.sub("", s))

    max_width = max(visible_len(line) for line in lines)
    if title:
        max_width = max(max_width, len(title) + 2)

    # Build box
    if title:
        fill = max(0, max_width - len(title) - 3)
        top = f"+-- {title} " + "-" * fill + "+"
    else:
        top = "+" + "-" * (max_width + 2) + "+"

    bottom = "+" + "-" * (max_width + 2) + "+"

    box_lines = [top]
    for line in lines:
        padding = max_width - visible_len(line)
        box_lines.append(f"| {line}{' ' * padding} |")
    box_lines.append(bottom)

    return "\n".join(box_lines)


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    return re.compile(r"\033\[[0-9;]*m").sub("", text)


def strip_emoji(text: str) -> str:
    """Remove emoji characters from text when in no-color mode."""
    # Remove common emoji ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F700-\U0001F77F"  # alchemical
        "\U0001F780-\U0001F7FF"  # geometric
        "\U0001F800-\U0001F8FF"  # supplemental arrows
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended
        "\U00002702-\U000027B0"  # dingbats
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U0000200D"  # zero width joiner
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text).strip()


def clean_output(text: str) -> str:
    """Clean text for output: strip emoji if no-color mode is active."""
    if _is_no_color():
        return strip_emoji(text)
    return text
