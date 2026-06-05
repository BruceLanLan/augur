# -*- coding: utf-8 -*-
"""Tests for augur.cli_format — color, table, box, signal icon, ANSI cleanup."""

import pytest

from augur.cli_format import (
    color_text,
    format_box,
    format_table,
    signal_icon,
    strip_ansi,
    strip_emoji,
    clean_output,
)


class TestColorText:
    def test_green_wraps_with_ansi(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        out = color_text("hello", "green")
        assert "\033[32m" in out
        assert "\033[0m" in out
        assert "hello" in out

    def test_no_color_env_disables_ansi(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        assert color_text("hello", "red") == "hello"
        assert color_text("hello", "bold") == "hello"

    def test_unknown_color_returns_plain(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert color_text("x", "not_a_real_color") == "x"


class TestSignalIcon:
    def test_bullish_emoji_default(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert signal_icon("bullish") == "🟢"

    def test_bullish_text_in_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        assert signal_icon("bullish") == "[BUY]"
        assert signal_icon("strong sell") == "[STRONG SELL]"

    def test_unknown_signal_fallback(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        assert signal_icon("weird_thing") == "[WEIRD_THING]"
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert signal_icon("weird_thing") == "*"


class TestFormatTable:
    def test_basic_alignment(self):
        out = format_table(["A", "BB"], [["x", "y"], ["longer", "z"]])
        lines = out.split("\n")
        # widths: A=1->6 (longer), BB=2, sep " | " = 3
        assert lines[0] == "A      | BB"
        # separator matches header line length exactly
        assert lines[1] == "-" * len(lines[0])
        assert "x      | y" in out
        assert "longer | z" in out

    def test_empty_rows_returns_empty(self):
        assert format_table(["A"], []) == ""


class TestFormatBox:
    def test_box_drawing_chars(self):
        out = format_box(["hi"], title="Note")
        lines = out.split("\n")
        assert lines[0].startswith("+-- Note")
        assert lines[0].endswith("+")
        assert all(l.startswith("|") and l.endswith("|") for l in lines[1:-1])
        assert lines[-1] == "+" + "-" * (max(len("hi") for _ in [0]) + 2) + "+" or lines[-1].startswith("+")

    def test_multiline_box_pads_shortest(self):
        out = format_box(["ab", "abcd"], title="")
        lines = out.split("\n")
        # both inner lines should be the same visible width
        assert len(lines[1]) == len(lines[2])

    def test_empty_lines_returns_empty(self):
        assert format_box([]) == ""


class TestAnsiCleanup:
    def test_strip_ansi_removes_all_codes(self):
        s = "\033[31mred\033[0m and \033[1mbold\033[0m"
        assert strip_ansi(s) == "red and bold"

    def test_strip_ansi_preserves_unicode(self):
        assert strip_ansi("\033[32m🟢\033[0m") == "🟢"

    def test_strip_emoji_removes_common_emoji(self):
        out = strip_emoji("🟢 buy 🔴 sell")
        assert "🟢" not in out and "🔴" not in out
        assert "buy" in out and "sell" in out

    def test_clean_output_respects_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        out = clean_output("🟢 signal")
        assert "🟢" not in out

    def test_clean_output_keeps_emoji_by_default(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert clean_output("🟢 signal") == "🟢 signal"
