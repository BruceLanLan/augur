# -*- coding: utf-8 -*-
"""v14.1: a prediction made after the exchange close enters at the next
session's close, not at the close it already saw (learning.py entry rule)."""
from datetime import datetime, timedelta, timezone

from augur.learning import LearningEngine, _entry_reference


def _utc(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()


def _daily(start, n):
    d0 = datetime.strptime(start, "%Y-%m-%d")
    return [((d0 + timedelta(days=i)).strftime("%Y-%m-%d"), 100.0 + i) for i in range(n)]


def _resolve(tmp_path, ticker, when_utc):
    le = LearningEngine(weights_path=tmp_path / "w.json")
    le._predictions.append({
        "ticker": ticker, "agent_id": "buffett", "signal": "bullish", "score": 7.0,
        "confidence": 0.6, "timestamp": _utc(when_utc), "date": when_utc[:10],
        "outcome": None,
    })
    assert le.resolve_from_prices(ticker, _daily("2026-01-01", 240),
                                  now=_utc("2026-08-30 12:00")) == 1
    p = le._predictions[0]
    return p["entry_date"], p["exit_date"]


def test_us_after_close_enters_next_session(tmp_path):
    # 22:00 UTC = 17:00 EST, after the 16:00 close: that close already printed
    assert _resolve(tmp_path, "AAPL", "2026-01-05 22:00") == ("2026-01-06", "2026-02-05")


def test_us_during_session_enters_same_day(tmp_path):
    assert _resolve(tmp_path, "AAPL", "2026-01-05 15:00") == ("2026-01-05", "2026-02-04")


def test_us_after_close_respects_dst(tmp_path):
    # 20:30 UTC = 16:30 EDT in July (after close); in January it would be 15:30 EST
    assert _resolve(tmp_path, "AAPL", "2026-07-06 20:30")[0] == "2026-07-07"
    assert _resolve(tmp_path / "b", "AAPL", "2026-01-06 20:30")[0] == "2026-01-06"


def test_hk_uses_exchange_local_day_and_close(tmp_path):
    # 23:00 UTC Jan 5 = 07:00 HKT Jan 6, before the HK open: entry is Jan 6's
    # close (the legacy UTC-day rule picked Jan 5's, already 15h old).
    assert _resolve(tmp_path, "0700.HK", "2026-01-05 23:00")[0] == "2026-01-06"
    # 09:00 UTC = 17:00 HKT, after the 16:00 close
    assert _resolve(tmp_path / "b", "0700.HK", "2026-01-05 09:00")[0] == "2026-01-06"
    # 05:00 UTC = 13:00 HKT, during the session
    assert _resolve(tmp_path / "c", "0700.HK", "2026-01-05 05:00")[0] == "2026-01-05"


def test_a_share_close_is_15_00(tmp_path):
    # 07:30 UTC = 15:30 CST, after the 15:00 Shanghai close
    assert _resolve(tmp_path, "600519.SS", "2026-01-05 07:30")[0] == "2026-01-06"


def test_no_timestamp_keeps_legacy_day():
    assert _entry_reference({"ticker": "AAPL", "date": "2026-01-05"}) == ("2026-01-05", False)


def test_after_close_exit_not_known_yet_stays_pending(tmp_path):
    le = LearningEngine(weights_path=tmp_path / "w.json")
    le._predictions.append({
        "ticker": "AAPL", "agent_id": "buffett", "signal": "bullish", "score": 7.0,
        "confidence": 0.6, "timestamp": _utc("2026-01-05 22:00"), "outcome": None,
    })
    # exit needs the first close after Feb 4; on Feb 4 itself it is not known
    assert le.resolve_from_prices("AAPL", _daily("2026-01-01", 240),
                                  now=_utc("2026-02-04 23:00")) == 0
    assert le.resolve_from_prices("AAPL", _daily("2026-01-01", 240),
                                  now=_utc("2026-02-05 23:00")) == 1
