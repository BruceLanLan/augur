# -*- coding: utf-8 -*-
"""Tests for scripts/_replay_universe.py -- the shared ticker universe and
date window extracted from 4 research scripts after a code review found
them duplicated byte-for-byte (2026-07-16 follow-up to the v10.15.0
release). Guards against the exact drift the extraction fixed: one
script's copy of UNIVERSE/START/END silently diverging from the others.
"""

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "scripts" / "_replay_universe.py"
_spec = importlib.util.spec_from_file_location("_replay_universe", _MODULE_PATH)
replay_universe = importlib.util.module_from_spec(_spec)
sys.modules["_replay_universe"] = replay_universe
_spec.loader.exec_module(replay_universe)

_SCRIPTS_USING_SHARED_UNIVERSE = [
    "regime_weight_oos.py",
    "generate_agent_correlation.py",
    "factor_attribution.py",
    "generate_rolling_ic.py",
]


class TestSharedConstants:
    def test_universe_has_37_tickers(self):
        assert len(replay_universe.UNIVERSE) == 37

    def test_universe_has_no_duplicate_tickers(self):
        assert len(set(replay_universe.UNIVERSE)) == len(replay_universe.UNIVERSE)

    def test_window_dates_are_well_formed(self):
        assert replay_universe.START == "2022-01-01"
        assert replay_universe.END == "2026-06-01"
        assert replay_universe.START < replay_universe.END


class TestEveryResearchScriptImportsTheSharedModule:
    """The whole point of the extraction: no script should define its own
    UNIVERSE/START/END list anymore -- every one of them must import from
    _replay_universe instead, or the next ticker fix will silently apply
    to only one script again."""

    def test_no_script_hardcodes_its_own_universe_list(self):
        for name in _SCRIPTS_USING_SHARED_UNIVERSE:
            source = (_REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
            assert "from _replay_universe import" in source, (
                f"{name} does not import from _replay_universe -- "
                f"does it define its own copy of UNIVERSE/START/END again?"
            )
            assert '"AAPL", "MSFT", "NVDA"' not in source, (
                f"{name} appears to hardcode its own ticker list literal"
            )

    def test_no_script_defines_a_conflicting_universe_literal(self):
        for name in _SCRIPTS_USING_SHARED_UNIVERSE:
            source = (_REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
            assert "UNIVERSE = [" not in source, (
                f"{name} still defines its own UNIVERSE = [...] literal"
            )
