# -*- coding: utf-8 -*-
"""v14.1 backtest fidelity: production technical fields reach the replayed
MarketContext, and unknown forward returns are excluded rather than scored
as 0.0. Hermetic: fetch_history / EDGAR / the agent registry are patched."""

import math
import random
from pathlib import Path
from unittest.mock import patch

import pytest

from augur.backtest import (
    TECHNICALS_WINDOW,
    Backtester,
    BacktestRecord,
    generate_sample_data,
)
from augur.personas.base import AgentResponse, SignalType


def _tmp_bt(tmp_path: Path) -> Backtester:
    bt = Backtester()
    bt.RECORDS_DIR = tmp_path
    bt.RECORDS_FILE = tmp_path / "records.jsonl"
    return bt


class _SpyAgent:
    """Always neutral; remembers every MarketContext it was shown."""

    agent_id = "spy"

    def __init__(self):
        self.contexts = []

    def analyze(self, ctx):
        self.contexts.append(ctx)
        return AgentResponse(agent_id=self.agent_id, agent_name="Spy",
                             signal=SignalType.NEUTRAL, confidence=0.5, score=5.0,
                             reasoning="")


def _patch_agents(agent):
    return patch("augur.registry.AgentRegistry.get_all", return_value=[agent])


def _ohlc_prices(n: int, seed: int = 11):
    r = random.Random(seed)
    c = 100.0
    out = []
    for i in range(n):
        c *= math.exp(r.gauss(0.0005, 0.015))
        out.append({
            "date": f"2025-{1 + i // 28:02d}-{1 + i % 28:02d}" if i < 28 * 12 else f"2026-{i}",
            "open": c, "high": c * 1.012, "low": c * 0.988, "close": c, "volume": 1000,
        })
    return out


class TestMissingForwardReturns:
    def test_day_without_20d_return_is_skipped_not_a_neutral_hit(self, tmp_path):
        spy = _SpyAgent()
        hist = [{"date": f"2025-01-{d:02d}", "price": 100.0} for d in range(1, 8)]
        fwd = [{"date": h["date"], "return_5d": 0.01, "return_20d": 0.05, "return_60d": None}
               for h in hist[:5]]
        # last two days: horizon not reached (None) / no entry at all
        fwd.append({"date": hist[5]["date"], "return_5d": None, "return_20d": None,
                    "return_60d": None})
        with _patch_agents(spy):
            result = _tmp_bt(tmp_path).run_backtest("T", hist, fwd)
        assert result.dates == [h["date"] for h in hist[:5]]
        assert len(result.records) == 5
        # neutral vs a real +5% move is a miss; the unknown days never scored
        assert not any(r.hit for r in result.records)
        assert all(r.actual_return_60d is None for r in result.records)

    def test_ics_use_only_known_returns_per_horizon(self):
        recs = []
        for i in range(6):
            recs.append(BacktestRecord(
                date=f"d{i}", ticker="T", agent_id="a", signal="bullish", score=float(i),
                confidence=0.5, actual_return_5d=0.01 * i,
                actual_return_20d=0.02 * i,
                actual_return_60d=(0.03 * i if i < 3 else None), hit=True))
        ic = Backtester()._calculate_ics(recs)[0]
        assert ic.ic_5d == pytest.approx(1.0)
        assert ic.ic_20d == pytest.approx(1.0)
        # 3 known 60d values, perfectly ranked: still 1.0 (a 0.0 fill would break it)
        assert ic.ic_60d == pytest.approx(1.0)

    def test_none_returns_round_trip_through_records_file(self, tmp_path):
        bt = _tmp_bt(tmp_path)
        rec = BacktestRecord(date="2025-01-02", ticker="T", agent_id="a", signal="neutral",
                             score=5.0, confidence=0.5, actual_return_5d=0.01,
                             actual_return_20d=0.0, actual_return_60d=None)
        bt._save_records([rec])
        back = bt.load_records()[0]
        assert back.actual_return_60d is None
        assert back.actual_return_20d == 0.0

    def test_sample_data_has_no_zero_filled_returns(self):
        _, fwd = generate_sample_data("ZZZ", days=10)
        assert all(f["return_60d"] is not None for f in fwd)


class TestProductionTechnicalsInReplay:
    def test_run_backtest_passes_all_technical_fields(self, tmp_path):
        spy = _SpyAgent()
        day = {"date": "2025-01-02", "price": 100.0, "rsi": 41.0, "macd": 0.5,
               "macd_signal": 0.7, "macd_histogram": -0.2, "sma20": 101.0,
               "sma50": 103.0, "atr": 2.5, "volatility_20d": 0.31}
        hist = [dict(day, date=f"2025-01-{d:02d}") for d in range(2, 8)]
        fwd = [{"date": h["date"], "return_5d": 0.0, "return_20d": 0.01, "return_60d": 0.02}
               for h in hist]
        with _patch_agents(spy):
            _tmp_bt(tmp_path).run_backtest("T", hist, fwd)
        ctx = spy.contexts[0]
        for k in ("rsi", "macd", "macd_signal", "macd_histogram", "sma20", "sma50",
                  "atr", "volatility_20d"):
            assert getattr(ctx, k) == day[k], k

    def test_live_backtest_uses_warmed_up_production_window(self, tmp_path):
        from augur.data import calculate_technicals

        days = 10
        prices = _ohlc_prices(days + 60 + TECHNICALS_WINDOW + 40)
        bt = _tmp_bt(tmp_path)
        captured = {}

        def fake_run(ticker, hist, fwd, data_source="unknown"):
            captured["hist"], captured["fwd"] = hist, fwd

        with patch("augur.data.fetch_history", return_value=prices), \
             patch("augur.consensus.edgar_fundamentals.fetch_edgar_fundamentals",
                   return_value={"pe": 20.0}), \
             patch.object(bt, "run_backtest", side_effect=fake_run):
            bt.run_live_backtest("T", days=days)

        hist, fwd = captured["hist"], captured["fwd"]
        assert len(hist) == days
        used = prices[-(days + 60 + TECHNICALS_WINDOW - 1):]
        first = TECHNICALS_WINDOW - 1  # first backtested bar has a full window behind it
        assert hist[0]["date"] == used[first]["date"]
        expected = calculate_technicals(used[:first + 1])
        for k in ("rsi", "macd", "macd_signal", "sma20", "sma50", "atr", "volatility_20d"):
            assert hist[0][k] == expected[k], k
        assert hist[0]["atr"] > 0 and hist[0]["volatility_20d"] > 0
        assert all(f["return_60d"] is not None for f in fwd)

    def test_live_backtest_short_history_marks_unknown_horizons(self, tmp_path):
        prices = _ohlc_prices(40)
        bt = _tmp_bt(tmp_path)
        captured = {}

        def fake_run(ticker, hist, fwd, data_source="unknown"):
            captured["fwd"] = fwd

        with patch("augur.data.fetch_history", return_value=prices), \
             patch("augur.consensus.edgar_fundamentals.fetch_edgar_fundamentals",
                   return_value={"pe": 20.0}), \
             patch.object(bt, "run_backtest", side_effect=fake_run):
            bt.run_live_backtest("T", days=30)

        fwd = captured["fwd"]
        assert all(f["return_60d"] is None for f in fwd)
        assert any(f["return_20d"] is None for f in fwd)
        assert all(f["return_5d"] is not None for f in fwd)

    def test_replay_records_carry_production_technicals(self):
        from augur.backtest import _REPLAY_RECORD_FIELDS, fetch_ticker_replay_records
        from augur.data import calculate_technicals

        prices = _ohlc_prices(150)
        start = prices[100]["date"]
        with patch("augur.data.fetch_history", return_value=prices), \
             patch("augur.consensus.edgar_fundamentals.fetch_edgar_fundamentals",
                   return_value={"pe": 20.0}):
            recs = fetch_ticker_replay_records("T", start, prices[110]["date"])
        assert recs and recs[0]["date"] == start
        expected = calculate_technicals(prices[100 - TECHNICALS_WINDOW + 1:101])
        for k in ("macd_signal", "macd_histogram", "atr", "volatility_20d", "sma50"):
            assert k in _REPLAY_RECORD_FIELDS
            assert recs[0][k] == expected[k], k
