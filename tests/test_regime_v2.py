# -*- coding: utf-8 -*-
"""P2-3: regime detector v2 (hysteresis + point-in-time macro features).

Offline, deterministic tests against synthetic VIX/SPY series — no network.
"""

from unittest.mock import patch

from augur.consensus import macro_features as mf


def _bull_spy_series(n: int, start: float = 100.0, step: float = 1.0):
    """Steadily rising closes; trend becomes "bull" once the 10-day SMA warms up."""
    return [start + step * i for i in range(n)]


class TestClassifyRegimeHysteresis:
    def test_single_day_vix_spike_does_not_flip_regime(self):
        n = 26
        spy = _bull_spy_series(n)
        vix = [15.0] * n
        vix[20] = 27.0  # one-day spike, back to 15 the next day

        # Let BULL_LOW_VOL get accepted first (trend warms up at idx 9, needs
        # confirm_days=3 to actually flip from the initial SIDEWAYS seed).
        result = mf.classify_regime(vix, spy, end_idx=18)
        assert result["regime"] == "BULL_LOW_VOL"

        # The single-day spike at idx 20 never persists 3 days, so it must
        # never be accepted, even right after the spike.
        result_after_spike = mf.classify_regime(vix, spy, end_idx=22)
        assert result_after_spike["regime"] == "BULL_LOW_VOL"
        assert result_after_spike["regime"] != "BULL_HIGH_VOL"

    def test_persistent_vix_regime_change_is_accepted(self):
        n = 26
        spy = _bull_spy_series(n)
        vix = [15.0] * n
        vix[20] = 27.0
        vix[21] = 27.0
        vix[22] = 27.0  # three consecutive days >= confirm_days

        result = mf.classify_regime(vix, spy, end_idx=22)
        assert result["regime"] == "BULL_HIGH_VOL"

    def test_oscillation_between_two_non_accepted_states_never_flips(self):
        n = 26
        spy = _bull_spy_series(n)
        vix = [15.0] * n
        # Alternate every day starting at idx 18: low, high, low, high, low...
        for i in range(18, 24):
            vix[i] = 27.0 if (i % 2 == 0) else 15.0

        # BULL_LOW_VOL should already be accepted by idx 17 (trend warmed up
        # at idx 9, three confirm days later it's accepted).
        baseline = mf.classify_regime(vix, spy, end_idx=17)
        assert baseline["regime"] == "BULL_LOW_VOL"

        # No single raw value repeats long enough to win the dwell scan, so
        # the accepted regime must not change through the oscillation.
        result = mf.classify_regime(vix, spy, end_idx=23)
        assert result["regime"] == "BULL_LOW_VOL"

    def test_no_lookahead_future_data_does_not_affect_past_classification(self):
        n = 30
        spy = _bull_spy_series(n)
        vix = [15.0] * n
        vix[20] = 27.0
        vix[21] = 27.0
        vix[22] = 27.0
        # Wild future swings after end_idx=22 must not matter.
        for i in range(23, n):
            vix[i] = 99.0 if i % 2 == 0 else 5.0

        full = mf.classify_regime(vix, spy, end_idx=22)
        truncated = mf.classify_regime(vix[:23], spy[:23], end_idx=22)
        assert full["regime"] == truncated["regime"] == "BULL_HIGH_VOL"

    def test_empty_or_out_of_range_falls_back_to_default(self):
        assert mf.classify_regime([], [], end_idx=0)["regime"] == "SIDEWAYS"
        assert mf.classify_regime([15.0], [100.0], end_idx=5)["regime"] == "SIDEWAYS"


class TestFetchMacroFeatures:
    def test_skip_fetch_env_returns_defaults(self, monkeypatch):
        monkeypatch.setenv("AUGUR_SKIP_MACRO_FETCH", "1")
        features = mf.fetch_macro_features()
        assert features["regime"] == "SIDEWAYS"
        assert "vix" in features and "trend" in features and "regime_raw" in features

    def test_live_snapshot_is_cached_but_historical_lookups_are_not(self, monkeypatch):
        monkeypatch.delenv("AUGUR_SKIP_MACRO_FETCH", raising=False)
        mf.clear_macro_cache()
        calls = []

        def fake_macro_from_market(date_str=None):
            calls.append(date_str)
            return {"vix": 20.0, "trend": "sideways", "regime": "SIDEWAYS", "regime_raw": "SIDEWAYS"}

        with patch.object(mf, "_macro_from_market", side_effect=fake_macro_from_market):
            mf.fetch_macro_features(None)
            mf.fetch_macro_features(None)  # should hit cache, no new call
            mf.fetch_macro_features("2020-03-20")
            mf.fetch_macro_features("2020-03-20")  # historical lookups never cache

        assert calls.count(None) == 1
        assert calls.count("2020-03-20") == 2
        mf.clear_macro_cache()

    def test_yfinance_unavailable_falls_back_to_defaults(self, monkeypatch):
        monkeypatch.delenv("AUGUR_SKIP_MACRO_FETCH", raising=False)
        mf.clear_macro_cache()
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = None
            features = mf.fetch_macro_features()
        assert "vix" in features
        assert "regime" in features
        mf.clear_macro_cache()
