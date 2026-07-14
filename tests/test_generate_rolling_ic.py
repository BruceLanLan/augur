# -*- coding: utf-8 -*-
"""Tests for the pure logic in scripts/generate_rolling_ic.py (B1 from
docs/FUTURE_DIRECTIONS_BRAINSTORM_2026-07.md).

Only ic_to_weight() and aggregate_overall_ic() are covered -- both are pure
functions with no network calls. main()'s real EDGAR/yfinance pull is
exercised manually, same convention as every other scripts/*.py research
script in this project (regime_weight_oos.py, generate_agent_correlation.py,
factor_attribution.py -- none have pytest coverage for their main()).
"""

import importlib.util
import sys
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_rolling_ic.py"
_spec = importlib.util.spec_from_file_location("generate_rolling_ic", _SCRIPT_PATH)
gen = importlib.util.module_from_spec(_spec)
sys.modules["generate_rolling_ic"] = gen
_spec.loader.exec_module(gen)


class TestIcToWeight:
    def test_zero_ic_maps_to_center_weight(self):
        assert gen.ic_to_weight(0.0) == 0.5

    def test_positive_ic_increases_weight(self):
        assert gen.ic_to_weight(0.1) > gen.ic_to_weight(0.0)

    def test_negative_ic_decreases_weight(self):
        assert gen.ic_to_weight(-0.1) < gen.ic_to_weight(0.0)

    def test_strongly_negative_ic_floors_at_point_one(self):
        assert gen.ic_to_weight(-10.0) == 0.1

    def test_strongly_positive_ic_ceils_at_three(self):
        assert gen.ic_to_weight(10.0) == 3.0

    def test_matches_learning_engine_clamp_bounds(self):
        # Same [0.1, 3.0] clamp as LearningEngine's own IC-derived weight
        # (src/augur/learning.py), by design -- see module docstring.
        for ic in [-5, -1, -0.5, 0, 0.5, 1, 5]:
            w = gen.ic_to_weight(ic)
            assert 0.1 <= w <= 3.0


class TestAggregateOverallIc:
    def test_single_regime_returns_its_own_ic(self):
        per_agent_by_regime = {"SIDEWAYS": {"buffett": 0.08}}
        per_regime = {"SIDEWAYS": {"n_days": 50}}
        result = gen.aggregate_overall_ic(per_agent_by_regime, per_regime)
        assert result == {"buffett": 0.08}

    def test_weighted_average_across_two_regimes(self):
        per_agent_by_regime = {
            "SIDEWAYS": {"buffett": 0.10},
            "BULL_LOW_VOL": {"buffett": 0.00},
        }
        per_regime = {
            "SIDEWAYS": {"n_days": 75},
            "BULL_LOW_VOL": {"n_days": 25},
        }
        result = gen.aggregate_overall_ic(per_agent_by_regime, per_regime)
        # (0.10*75 + 0.00*25) / 100 = 0.075
        assert result["buffett"] == 0.075

    def test_agent_missing_from_some_regimes_still_aggregated(self):
        per_agent_by_regime = {
            "SIDEWAYS": {"buffett": 0.10, "graham": 0.05},
            "BULL_LOW_VOL": {"buffett": 0.20},  # graham has no data this regime
        }
        per_regime = {
            "SIDEWAYS": {"n_days": 50},
            "BULL_LOW_VOL": {"n_days": 50},
        }
        result = gen.aggregate_overall_ic(per_agent_by_regime, per_regime)
        assert result["buffett"] == 0.15  # (0.10*50 + 0.20*50) / 100
        assert result["graham"] == 0.05  # only present in SIDEWAYS -> its own value

    def test_empty_input_returns_empty(self):
        assert gen.aggregate_overall_ic({}, {}) == {}

    def test_zero_total_days_avoids_division_by_zero(self):
        per_agent_by_regime = {"SIDEWAYS": {"buffett": 0.10}}
        per_regime = {"SIDEWAYS": {"n_days": 0}}
        result = gen.aggregate_overall_ic(per_agent_by_regime, per_regime)
        assert result == {"buffett": 0.0}
