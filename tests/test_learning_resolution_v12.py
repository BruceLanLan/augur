"""v12: each prediction resolves at its own horizon (learning schema 2)."""
import json
import time
from datetime import datetime, timedelta, timezone

from augur.learning import LearningEngine


def _ts(day):
    return datetime.strptime(day, "%Y-%m-%d").replace(hour=9, tzinfo=timezone.utc).timestamp()


def _closes(start, n, f):
    d0 = datetime.strptime(start, "%Y-%m-%d")
    return [((d0 + timedelta(days=i)).strftime("%Y-%m-%d"), f(i)) for i in range(n)]


def _engine(tmp_path):
    return LearningEngine(weights_path=tmp_path / "w.json")


def _add(le, day, agent="buffett", signal="bullish", score=7.0):
    le.record_prediction("AAPL", agent, signal, score, 0.6)
    p = le._predictions[-1]
    p["timestamp"] = _ts(day) + 7  # 09:00:07, like the cron
    p["date"] = day


def test_predictions_on_different_days_get_their_own_returns(tmp_path):
    le = _engine(tmp_path)
    _add(le, "2026-01-01")
    _add(le, "2026-01-11", agent="munger")
    closes = _closes("2026-01-01", 120, lambda i: 100.0 + i)  # +1/day
    n = le.resolve_from_prices("AAPL", closes, now=_ts("2026-04-01"))
    assert n == 2
    out = {p["agent_id"]: p for p in le._predictions}
    assert abs(out["buffett"]["outcome"] - (130 - 100) / 100) < 1e-9
    assert abs(out["munger"]["outcome"] - (140 - 110) / 110) < 1e-9
    assert out["munger"]["exit_date"] == "2026-02-10"


def test_no_lookahead_and_horizon_boundary_is_by_day(tmp_path):
    le = _engine(tmp_path)
    _add(le, "2026-01-01")
    closes = _closes("2026-01-01", 120, lambda i: 100.0 + i)
    # 09:00:00 on day 30: timestamp is 7s short of 30*86400 but the day has come.
    assert le.resolve_from_prices("AAPL", closes, now=_ts("2026-01-31")) == 1
    le2 = _engine(tmp_path / "b")
    _add(le2, "2026-01-01")
    assert le2.resolve_from_prices("AAPL", closes, now=_ts("2026-01-30")) == 0


def test_old_predictions_never_age_out(tmp_path):
    le = _engine(tmp_path)
    _add(le, "2026-01-01")
    closes = _closes("2025-12-01", 200, lambda i: 50.0 + i)
    assert le.resolve_from_prices("AAPL", closes, now=_ts("2026-05-01")) == 1


def test_missing_history_stays_pending(tmp_path):
    le = _engine(tmp_path)
    _add(le, "2026-01-01")
    closes = _closes("2026-01-01", 10, lambda i: 100.0)
    assert le.resolve_from_prices("AAPL", closes, now=_ts("2026-04-01")) == 0
    assert le.pending_count == 1


def test_same_day_reanalysis_keeps_one_prediction(tmp_path):
    le = _engine(tmp_path)
    for score in (6.0, 7.0, 8.0):
        le.record_prediction("AAPL", "buffett", "bullish", score, 0.5, dedupe_day=True)
    assert le.pending_count == 1
    assert le._predictions[0]["score"] == 8.0


def test_outcomes_log_is_append_only_and_matches_accuracy(tmp_path):
    le = _engine(tmp_path)
    for i in range(150):
        day = (datetime(2025, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d")
        _add(le, day, agent=f"a{i % 3}")
    closes = _closes("2025-01-01", 260, lambda i: 100.0 + (i % 7))
    assert le.resolve_from_prices("AAPL", closes, now=_ts("2026-01-01")) == 150
    lines = le.outcomes_path.read_text().splitlines()
    assert len(lines) == 150
    assert sum(a["total_predictions"] for a in le.get_accuracy().values()) == 150


def test_batch_writes_once(tmp_path, monkeypatch):
    le = _engine(tmp_path)
    calls = []
    orig = le._save_weights
    monkeypatch.setattr(le, "_save_weights", lambda: (calls.append(1), orig()))
    with le.batch():
        for i in range(18):
            le.record_prediction("AAPL", f"a{i}", "neutral", 5.0, 0.5)
    assert len(calls) == 1
    assert LearningEngine(weights_path=tmp_path / "w.json").pending_count == 18


def test_v1_file_drops_misattributed_outcomes_keeps_pending(tmp_path):
    path = tmp_path / "w.json"
    path.write_text(json.dumps({
        "weights": {"buffett": 0.9},
        "accuracy": {"buffett": {"correct": 20, "total": 25, "ic_sum": 1.0, "ic_count": 25}},
        "predictions": [
            {"ticker": "AAPL", "agent_id": "buffett", "signal": "bullish", "score": 7,
             "confidence": 0.5, "timestamp": time.time() - 90 * 86400, "outcome": 0.0513},
            {"ticker": "AAPL", "agent_id": "buffett", "signal": "bullish", "score": 7,
             "confidence": 0.5, "timestamp": time.time() - 40 * 86400, "outcome": None},
        ],
    }))
    le = LearningEngine(weights_path=path)
    assert le.pending_count == 1
    assert le.prediction_count == 1
    assert le.get_accuracy() == {} and le.get_weights() == {}
    le.record_prediction("MSFT", "buffett", "neutral", 5.0, 0.5)
    assert json.loads(path.read_text())["schema"] == 2
