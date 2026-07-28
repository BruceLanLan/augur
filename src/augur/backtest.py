# -*- coding: utf-8 -*-
"""
augur.backtest - 历史回测系统 + Agent IC 实盘追踪

功能:
  - 回放历史数据给所有18位Agent
  - 记录预测信号与评分
  - 对比实际价格走势
  - 计算每位Agent的IC (Information Coefficient)
  - 追踪累积表现
  - 提供排行榜与报告
"""

import json
import logging
import math
import random
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ============ Data Classes ============

@dataclass
class BacktestRecord:
    """单条预测记录"""
    date: str
    ticker: str
    agent_id: str
    signal: str           # bullish / neutral / bearish
    score: float          # 0-10
    confidence: float     # 0-1
    actual_return_5d: float = 0.0
    actual_return_20d: float = 0.0
    actual_return_60d: float = 0.0
    hit: bool = False     # 预测是否正确
    # "live" (real yfinance history), "demo" (generate_sample_data synthetic
    # data), or "unknown" (legacy records persisted before this field existed,
    # or any direct run_backtest() caller that didn't specify). Leaderboard
    # aggregation defaults to live-only so a synthetic record can never be
    # silently blended into a number presented as a real track record.
    data_source: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BacktestRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AgentIC:
    """Agent IC追踪"""
    agent_id: str
    total_predictions: int = 0
    correct_predictions: int = 0
    ic_5d: float = 0.0
    ic_20d: float = 0.0
    ic_60d: float = 0.0
    hit_rate: float = 0.0
    avg_score_when_right: float = 0.0
    avg_score_when_wrong: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BacktestResult:
    """完整回测结果"""
    ticker: str
    dates: List[str] = field(default_factory=list)
    records: List[BacktestRecord] = field(default_factory=list)
    agent_ics: List[AgentIC] = field(default_factory=list)
    consensus_ic: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "dates": self.dates,
            "records": [r.to_dict() for r in self.records],
            "agent_ics": [a.to_dict() for a in self.agent_ics],
            "consensus_ic": self.consensus_ic,
            "summary": self.summary,
        }


# ============ Backtester ============

class Backtester:
    """历史回测引擎"""

    RECORDS_DIR = Path.home() / ".augur" / "backtest"
    RECORDS_FILE = RECORDS_DIR / "records.jsonl"

    def __init__(self):
        self.RECORDS_DIR.mkdir(parents=True, exist_ok=True)

    def run_backtest(
        self,
        ticker: str,
        historical_data: List[Dict],
        forward_returns: List[Dict],
        data_source: str = "unknown",
    ) -> "BacktestResult":
        """
        Run backtest: replay historical data through all agents.

        Args:
            ticker: Stock ticker
            historical_data: List of daily market contexts (dicts with metrics)
            forward_returns: List of forward returns for each date
                             Each dict has: date, return_5d, return_20d, return_60d
            data_source: Tag stamped on every persisted BacktestRecord —
                         "live" or "demo" for callers that know which they're
                         feeding in (run_live_backtest / generate_sample_data
                         callers), left as "unknown" for direct/legacy
                         callers. Only "live"-tagged records count toward
                         get_leaderboard()/get_ic_report() by default.

        Returns:
            BacktestResult with all records and IC calculations
        """
        if not historical_data or not forward_returns:
            return BacktestResult(ticker=ticker.upper())

        # Graceful degradation: require at least 5 data points for a meaningful backtest
        if len(historical_data) < 5:
            return BacktestResult(
                ticker=ticker.upper(),
                summary="Insufficient data (fewer than 5 data points for meaningful backtest)",
            )

        from augur.registry import AgentRegistry
        from augur.personas.base import MarketContext

        registry = AgentRegistry()
        agents = registry.get_all()

        records: List[BacktestRecord] = []
        dates: List[str] = []

        # Build forward return lookup
        fwd_lookup = {fr["date"]: fr for fr in forward_returns}

        for day_data in historical_data:
            date_str = day_data.get("date", "")
            if not date_str:
                continue
            dates.append(date_str)

            # Get forward returns for this date
            fwd = fwd_lookup.get(date_str, {})
            ret_5d = fwd.get("return_5d", 0.0)
            ret_20d = fwd.get("return_20d", 0.0)
            ret_60d = fwd.get("return_60d", 0.0)

            # Build MarketContext from day data
            ctx_kwargs = {"ticker": ticker.upper()}
            for k in ["price", "pe", "pb", "roe", "gross_margins", "revenue_growth",
                       "debt_ratio", "fcf", "market_cap", "operating_margins",
                       "rsi", "macd", "earnings_growth", "current_ratio"]:
                if k in day_data:
                    ctx_kwargs[k] = day_data[k]
            ctx = MarketContext(**ctx_kwargs)

            # Run each agent
            for agent in agents:
                try:
                    result = agent.analyze(ctx)
                    signal = result.signal.value
                    hit = self._check_hit(signal, ret_20d)

                    record = BacktestRecord(
                        date=date_str,
                        ticker=ticker.upper(),
                        agent_id=agent.agent_id,
                        signal=signal,
                        score=result.score,
                        confidence=result.confidence,
                        actual_return_5d=ret_5d,
                        actual_return_20d=ret_20d,
                        actual_return_60d=ret_60d,
                        hit=hit,
                        data_source=data_source,
                    )
                    records.append(record)
                except Exception:
                    pass

        # Calculate ICs
        agent_ics = self._calculate_ics(records)

        # Calculate consensus IC
        consensus_ic = self._calculate_consensus_ic(records, dates, ticker, historical_data, forward_returns)

        # Generate summary
        summary = self._generate_summary(agent_ics, consensus_ic, ticker)

        # Save records
        self._save_records(records)

        return BacktestResult(
            ticker=ticker.upper(),
            dates=dates,
            records=records,
            agent_ics=agent_ics,
            consensus_ic=consensus_ic,
            summary=summary,
        )

    def _check_hit(self, signal: str, actual_return: float) -> bool:
        """Check if prediction was correct based on 20-day forward returns.

        The 0.02 (2%) threshold for neutral is intentional: since actual_return
        represents the cumulative 20-day forward return (not a single daily return),
        a move of less than 2% over 20 trading days is reasonably considered "flat".
        """
        if signal == "bullish" and actual_return > 0:
            return True
        elif signal == "bearish" and actual_return < 0:
            return True
        elif signal == "neutral" and abs(actual_return) < 0.02:
            return True
        return False

    def _calculate_ics(self, records: List["BacktestRecord"]) -> List["AgentIC"]:
        """Calculate IC for each agent using Spearman rank correlation"""
        # Group by agent
        agent_records: Dict[str, List[BacktestRecord]] = {}
        for r in records:
            if r.agent_id not in agent_records:
                agent_records[r.agent_id] = []
            agent_records[r.agent_id].append(r)

        agent_ics = []
        for agent_id, recs in agent_records.items():
            total = len(recs)
            correct = sum(1 for r in recs if r.hit)
            hit_rate = correct / total if total > 0 else 0.0

            # Scores when right vs wrong
            right_scores = [r.score for r in recs if r.hit]
            wrong_scores = [r.score for r in recs if not r.hit]
            avg_right = sum(right_scores) / len(right_scores) if right_scores else 0.0
            avg_wrong = sum(wrong_scores) / len(wrong_scores) if wrong_scores else 0.0

            # IC: Spearman rank correlation between signal score and actual returns
            # Convert signals to numeric: bullish=1, neutral=0, bearish=-1
            signal_scores = []
            for r in recs:
                if r.signal == "bullish":
                    signal_scores.append(r.score)
                elif r.signal == "bearish":
                    signal_scores.append(-r.score)
                else:
                    signal_scores.append(0)

            returns_5d = [r.actual_return_5d for r in recs]
            returns_20d = [r.actual_return_20d for r in recs]
            returns_60d = [r.actual_return_60d for r in recs]

            ic_5d = self._rank_correlation(signal_scores, returns_5d)
            ic_20d = self._rank_correlation(signal_scores, returns_20d)
            ic_60d = self._rank_correlation(signal_scores, returns_60d)

            agent_ics.append(AgentIC(
                agent_id=agent_id,
                total_predictions=total,
                correct_predictions=correct,
                ic_5d=round(ic_5d, 4),
                ic_20d=round(ic_20d, 4),
                ic_60d=round(ic_60d, 4),
                hit_rate=round(hit_rate, 4),
                avg_score_when_right=round(avg_right, 2),
                avg_score_when_wrong=round(avg_wrong, 2),
            ))

        # Sort by IC 20d descending
        agent_ics.sort(key=lambda x: x.ic_20d, reverse=True)
        return agent_ics

    def _rank_correlation(self, x: List[float], y: List[float]) -> float:
        """Simple Spearman rank correlation implementation"""
        n = len(x)
        if n < 3:
            return 0.0

        def _rank(data):
            """Assign ranks (1-indexed, average for ties)"""
            indexed = sorted(enumerate(data), key=lambda t: t[1])
            ranks = [0.0] * n
            i = 0
            while i < n:
                j = i
                while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                    j += 1
                avg_rank = (i + j) / 2.0 + 1.0
                for k in range(i, j + 1):
                    ranks[indexed[k][0]] = avg_rank
                i = j + 1
            return ranks

        rank_x = _rank(x)
        rank_y = _rank(y)

        # Pearson correlation on ranks
        mean_x = sum(rank_x) / n
        mean_y = sum(rank_y) / n

        cov = sum((rank_x[i] - mean_x) * (rank_y[i] - mean_y) for i in range(n))
        var_x = sum((rank_x[i] - mean_x) ** 2 for i in range(n))
        var_y = sum((rank_y[i] - mean_y) ** 2 for i in range(n))

        denom = math.sqrt(var_x * var_y)
        if denom == 0:
            return 0.0
        return cov / denom

    def _calculate_consensus_ic(
        self,
        records: List[BacktestRecord],
        dates: List[str],
        ticker: str,
        historical_data: List[Dict],
        forward_returns: List[Dict],
    ) -> float:
        """Calculate consensus IC (average weighted score vs actual return)"""
        # Group records by date and compute consensus score per date
        date_records: Dict[str, List[BacktestRecord]] = {}
        for r in records:
            if r.date not in date_records:
                date_records[r.date] = []
            date_records[r.date].append(r)

        fwd_lookup = {fr["date"]: fr for fr in forward_returns}

        consensus_scores = []
        actual_returns = []

        for date_str in dates:
            recs = date_records.get(date_str, [])
            if not recs:
                continue
            # Consensus = average signal-adjusted score
            total = 0.0
            for r in recs:
                if r.signal == "bullish":
                    total += r.score
                elif r.signal == "bearish":
                    total -= r.score
            avg = total / len(recs)
            consensus_scores.append(avg)

            fwd = fwd_lookup.get(date_str, {})
            actual_returns.append(fwd.get("return_20d", 0.0))

        return round(self._rank_correlation(consensus_scores, actual_returns), 4)

    def _generate_summary(self, agent_ics: List[AgentIC], consensus_ic: float, ticker: str) -> str:
        """Generate text summary of backtest results"""
        if not agent_ics:
            return f"{ticker} 回测无有效数据"

        top_agents = agent_ics[:3]
        bottom_agents = agent_ics[-3:] if len(agent_ics) > 3 else []

        lines = [
            f"=== {ticker} 历史回测报告 ===",
            f"共识IC(20d): {consensus_ic:.4f}",
            f"Agent总数: {len(agent_ics)}",
            "",
            "--- TOP 3 Agent (按IC 20d) ---",
        ]
        for a in top_agents:
            lines.append(
                f"  {a.agent_id:20s} IC={a.ic_20d:.4f} 命中率={a.hit_rate:.1%} "
                f"正确时均分={a.avg_score_when_right:.1f}"
            )

        if bottom_agents:
            lines.append("")
            lines.append("--- BOTTOM 3 Agent ---")
            for a in bottom_agents:
                lines.append(
                    f"  {a.agent_id:20s} IC={a.ic_20d:.4f} 命中率={a.hit_rate:.1%}"
                )

        avg_hit = sum(a.hit_rate for a in agent_ics) / len(agent_ics)
        lines.append("")
        lines.append(f"平均命中率: {avg_hit:.1%}")

        return "\n".join(lines)

    def _save_records(self, records: List[BacktestRecord]) -> None:
        """Persist records to ~/.augur/backtest/records.jsonl (with rotation)."""
        self.RECORDS_DIR.mkdir(parents=True, exist_ok=True)

        # Rotate if file exceeds 10MB
        if self.RECORDS_FILE.exists():
            try:
                file_size = self.RECORDS_FILE.stat().st_size
                if file_size > 10 * 1024 * 1024:  # 10MB
                    # Keep last 5000 records using deque for memory efficiency
                    with open(self.RECORDS_FILE, "r", encoding="utf-8") as f:
                        tail = deque(f, maxlen=5000)
                    with open(self.RECORDS_FILE, "w", encoding="utf-8") as f:
                        f.writelines(tail)
            except Exception:
                # best-effort rotation; file integrity handled by single-writer assumption
                pass

        with open(self.RECORDS_FILE, "a", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    def load_records(
        self,
        ticker: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[BacktestRecord]:
        """Load records with optional filtering"""
        if not self.RECORDS_FILE.exists():
            return []

        records = []
        with open(self.RECORDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if ticker and d.get("ticker", "").upper() != ticker.upper():
                        continue
                    if agent_id and d.get("agent_id") != agent_id:
                        continue
                    records.append(BacktestRecord.from_dict(d))
                except (json.JSONDecodeError, TypeError):
                    continue
        return records

    def get_ic_report(self, agent_id: Optional[str] = None, live_only: bool = True) -> List[AgentIC]:
        """Get IC from saved records.

        live_only=True (default) excludes "demo"/"unknown" records so a
        synthetic backtest run can never quietly move a number that's
        presented to the user as real historical performance. Pass
        live_only=False to see the IC across everything ever persisted,
        demo included (e.g. for debugging/inspection).
        """
        records = self.load_records(agent_id=agent_id)
        if live_only:
            records = [r for r in records if r.data_source == "live"]
        if not records:
            return []
        return self._calculate_ics(records)

    def get_leaderboard(self, live_only: bool = True) -> List[AgentIC]:
        """Get IC leaderboard sorted by IC 20d.

        live_only=True (default): only "live"-tagged records count, so
        historical demo-mode records already on disk (and any legacy
        records predating this field) can't silently blend fake data into
        a leaderboard presented as a real track record. See get_ic_report.
        """
        records = self.load_records()
        if live_only:
            records = [r for r in records if r.data_source == "live"]
        if not records:
            return []
        return self._calculate_ics(records)

    def run_live_backtest(self, ticker: str, days: int = 60) -> BacktestResult:
        """
        Run backtest using real historical data from yfinance.

        Args:
            ticker: Stock ticker
            days: Number of days to backtest

        Returns:
            BacktestResult with all records and IC calculations
        """
        from augur.data import fetch_history, calculate_technicals
        from augur.consensus.edgar_fundamentals import fetch_edgar_fundamentals

        # Fetch enough history for forward returns (days + 60)
        total_period = days + 70
        period_map = {
            60: "6mo",
            120: "1y",
            180: "1y",
            250: "2y",
        }
        # Pick the smallest period that covers our needs
        period = "1y"
        for threshold, p in sorted(period_map.items()):
            if total_period <= threshold:
                period = p
                break
        else:
            period = "2y"

        prices = fetch_history(ticker, period=period)
        if not prices or len(prices) < days + 5:
            raise ValueError(f"Insufficient data for {ticker}: got {len(prices)} days, need at least {days + 5}")

        # Build historical_data and forward_returns
        # Use last `days + 60` entries, backtest on first `days`
        if len(prices) > days + 60:
            prices = prices[-(days + 60):]

        actual_days = min(days, len(prices) - 5)
        historical_data = []
        forward_returns = []

        for i in range(actual_days):
            day = prices[i]
            date_str = day["date"]

            # Calculate technicals from prices up to this point
            history_slice = prices[:i + 1]
            technicals = calculate_technicals(history_slice) if len(history_slice) >= 5 else {}

            day_record = {
                "date": date_str,
                "price": day["close"],
                "rsi": technicals.get("rsi", 50),
                "macd": technicals.get("macd", 0),
                "sma20": technicals.get("sma20", 0),
                "sma50": technicals.get("sma50", 0),
            }

            # Point-in-time fundamentals: only what would actually have been
            # filed/available as of this historical date, sourced from real
            # SEC EDGAR filing dates (see edgar_fundamentals module
            # docstring for the look-ahead-guard rationale). A day with no
            # as-of-available annual statement yet is dropped entirely below
            # rather than silently zero-filled, since a silent zero is
            # indistinguishable from "this company has no fundamentals" and
            # would reintroduce the null-by-construction bug this exists to fix.
            pit = fetch_edgar_fundamentals(ticker, date_str, price=day["close"])
            if pit.get("insufficient"):
                continue
            for k, v in pit.items():
                day_record[k] = v

            historical_data.append(day_record)

            # Forward returns
            ret_5d = 0.0
            ret_20d = 0.0
            ret_60d = 0.0
            if i + 5 < len(prices):
                ret_5d = (prices[i + 5]["close"] / prices[i]["close"]) - 1
            if i + 20 < len(prices):
                ret_20d = (prices[i + 20]["close"] / prices[i]["close"]) - 1
            if i + 60 < len(prices):
                ret_60d = (prices[i + 60]["close"] / prices[i]["close"]) - 1

            forward_returns.append({
                "date": date_str,
                "return_5d": round(ret_5d, 5),
                "return_20d": round(ret_20d, 5),
                "return_60d": round(ret_60d, 5),
            })

        return self.run_backtest(ticker, historical_data, forward_returns, data_source="live")


# ============ Demo Data Generator ============

def generate_sample_data(ticker: str = "AAPL", days: int = 30) -> Tuple[List[Dict], List[Dict]]:
    """
    Generate simulated historical data for demo/backtest.

    Returns:
        (historical_data, forward_returns) tuple
    """
    rng = random.Random(sum(ord(c) for c in ticker) % 10000)

    base_price = 150.0 + rng.uniform(-50, 100)
    base_pe = 20 + rng.uniform(5, 30)
    base_roe = 0.10 + rng.uniform(0.05, 0.30)
    base_gm = 0.30 + rng.uniform(0.05, 0.25)
    base_rg = 0.05 + rng.uniform(-0.05, 0.20)

    historical_data = []
    forward_returns = []
    prices = []

    # Generate price series (days + 60 for forward returns)
    total_days = days + 60
    trend = rng.choice([-0.0003, 0.0005, 0.0002])
    vol = 0.015 + rng.uniform(0, 0.01)

    current_price = base_price
    for i in range(total_days):
        daily_return = trend + rng.gauss(0, vol)
        current_price *= (1 + daily_return)
        prices.append(current_price)

    start_date = datetime.now() - timedelta(days=days + 60)

    for i in range(days):
        date_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")

        # Add some noise to metrics each day
        noise = rng.uniform(-0.1, 0.1)
        day_price = prices[i]
        day_pe = base_pe * (1 + noise * 0.3)
        day_roe = base_roe * (1 + noise * 0.2)
        day_gm = base_gm * (1 + noise * 0.1)
        day_rg = base_rg * (1 + noise * 0.5)

        historical_data.append({
            "date": date_str,
            "price": round(day_price, 2),
            "pe": round(day_pe, 1),
            "pb": round(day_pe * day_roe, 2),  # PB ≈ PE × ROE (Du Pont)
            "roe": round(day_roe, 3),
            "gross_margins": round(day_gm, 3),
            "revenue_growth": round(day_rg, 3),
            "debt_ratio": round(0.3 + rng.uniform(-0.1, 0.2), 3),
            "fcf": round(day_price * 0.03 * (1 + noise), 2),
            "market_cap": round(day_price * 1e9 * rng.uniform(0.8, 1.5) / 1e9, 1),
            "rsi": round(50 + rng.gauss(0, 15), 1),
            "macd": round(rng.gauss(0, 2), 3),
        })

        # Forward returns
        ret_5d = (prices[i + 5] / prices[i] - 1) if i + 5 < len(prices) else 0.0
        ret_20d = (prices[i + 20] / prices[i] - 1) if i + 20 < len(prices) else 0.0
        ret_60d = (prices[i + 60] / prices[i] - 1) if i + 60 < len(prices) else 0.0

        forward_returns.append({
            "date": date_str,
            "return_5d": round(ret_5d, 5),
            "return_20d": round(ret_20d, 5),
            "return_60d": round(ret_60d, 5),
        })

    return historical_data, forward_returns


# ============ P2-4: Cross-sectional regime-weight OOS validation ============
#
# Why this section exists (and why it is NOT a per-ticker time-series IC):
# free annual fundamentals only update once per fiscal year per ticker, so a
# per-ticker time series of value-agent scores is a near-constant step
# function for most of the year (see Task 3 axis-check: within-ticker score
# stdev ~0.2-2.0 vs a ~10-point persistent cross-ticker gap for marks/graham).
# Reweighting a near-constant signal cannot move a per-ticker rank-IC -- it
# only adds a constant offset. The only axis on which "trust value agents
# more in a bear regime" can actually be tested is the CROSS-SECTIONAL one:
# on a single day, across many tickers, does ranking by the regime-weighted
# consensus correlate better with subsequent 20d returns than ranking by a
# flat equal-weight consensus? This section builds exactly that, once per
# day, bucketed by the regime that was in force on that day.
#
# Must use ``apply_regime_weights(weights, regime)`` -- NOT
# ``RegimeRouter().get_weights(regime)``, which silently zeroes every agent
# not named in ``_REGIME_ADJUSTMENTS[regime]``. ``apply_regime_weights``
# instead multiplies the full base-weight dict by each agent's adjustment
# (default 1.0 for agents not named) and renormalizes, which is the correct
# semantics for "reweight a consensus that already includes everyone".


def build_date_to_regime(start: str, end: str) -> Dict[str, str]:
    """Precompute a ``date_str -> regime`` map for ``[start, end]``, once.

    Does exactly one network pull of VIX + SPY daily closes for the whole
    range, then classifies every date using the same trailing-window pattern
    as the live path (mirrors ``scripts/regime_backtest_v2.py``'s
    ``fetch_aligned_series`` + ``new_regime_series``). This must NOT be done
    by calling ``fetch_macro_features(date_str)`` once per (ticker, date)
    pair -- that function does a fresh, uncached network fetch on every
    historical call by design, which would be catastrophically slow and
    likely rate-limited across a multi-ticker, multi-year backtest.
    """
    import pandas as pd
    import yfinance as yf

    from augur.consensus.macro_features import classify_regime

    # Pad the start backwards so the trailing window has enough warm-up data
    # to classify the very first requested date correctly (mirrors the live
    # path's ~95 calendar day lookback in macro_features._macro_from_market).
    start_dt = datetime.strptime(start, "%Y-%m-%d") - timedelta(days=130)
    start_padded = start_dt.strftime("%Y-%m-%d")

    vix_hist = yf.Ticker("^VIX").history(start=start_padded, end=end)
    spy_hist = yf.Ticker("SPY").history(start=start_padded, end=end)
    if vix_hist is None or spy_hist is None or len(vix_hist) == 0 or len(spy_hist) == 0:
        return {}

    vix_hist = vix_hist.copy()
    spy_hist = spy_hist.copy()
    vix_hist.index = pd.to_datetime(vix_hist.index.date)
    spy_hist.index = pd.to_datetime(spy_hist.index.date)
    common = vix_hist.index.intersection(spy_hist.index).sort_values()

    dates = [d.strftime("%Y-%m-%d") for d in common]
    vix_closes = vix_hist.loc[common, "Close"].tolist()
    spy_closes = spy_hist.loc[common, "Close"].tolist()

    # Trailing window matching the live path (LIVE_TRADING_WINDOW in
    # scripts/regime_backtest_v2.py / ~95 calendar days in macro_features).
    live_window = 65
    date_to_regime: Dict[str, str] = {}
    for i, d in enumerate(dates):
        if d < start or d > end:
            continue
        lo = max(0, i - live_window + 1)
        window_vix = vix_closes[lo:i + 1]
        window_spy = spy_closes[lo:i + 1]
        result = classify_regime(window_vix, window_spy, end_idx=len(window_vix) - 1)
        date_to_regime[d] = result["regime"]

    return date_to_regime


def fetch_ticker_replay_records(
    ticker: str,
    start: str,
    end: str,
    period: str = "5y",
) -> List[Dict]:
    """Build a list of per-day records for ``ticker`` spanning ``[start, end]``.

    Unlike ``run_live_backtest``, this fetches a long period directly (no
    "2y" period_map cap) so multi-year cross-sectional analysis is actually
    reachable -- EDGAR annual filings typically cover back to ~2011 for
    established large caps (yfinance-derived point-in-time fundamentals
    only reached ~2022; see edgar_fundamentals module docstring). Each
    record has: date, price, rsi, macd, pe, pb, roe, gross_margins,
    operating_margins, revenue_growth, earnings_growth, debt_ratio,
    market_cap, actual_return_20d. Days with insufficient point-in-time
    fundamentals, or without a realized 20-day forward return yet, are
    dropped (not zero-filled) -- see ``fetch_edgar_fundamentals`` and the
    realized-return note below.

    ``period`` is a yfinance lookback window measured from *today* (the
    day this function actually runs), not from ``end`` -- found the hard
    way running scripts/regime_weight_oos_2018_2020.py (2026-07-28): the
    default "5y" silently returned zero price history and therefore zero
    records for every ticker when ``end`` was 2020-12-31, because 5 years
    back from a 2026 run date never reaches 2020. For any ``end`` more
    than ``period`` in the past, pass a longer ``period`` (e.g. "max") or
    this function will quietly produce empty results with no error.
    """
    from augur.data import fetch_history, calculate_technicals
    from augur.consensus.edgar_fundamentals import fetch_edgar_fundamentals

    prices = fetch_history(ticker, period=period)
    if not prices:
        return []

    records: List[Dict] = []

    for i, day in enumerate(prices):
        date_str = day["date"]
        if date_str < start or date_str > end:
            continue
        # Realized-return filter: a day whose +20 trading day neighbor
        # doesn't exist yet has return_20d implicitly 0, which is not a real
        # "flat" return -- it is "we don't know yet". Since every ticker in
        # a shared universe has the same trailing ~20 days unrealized, that
        # would land on the same dates for everyone and produce a
        # degenerate (all-equal-y) cross-sectional IC. Drop instead.
        if i + 20 >= len(prices):
            continue

        history_slice = prices[:i + 1]
        technicals = calculate_technicals(history_slice) if len(history_slice) >= 5 else {}

        pit = fetch_edgar_fundamentals(ticker, date_str, price=day["close"])
        if pit.get("insufficient"):
            continue

        record = {
            "date": date_str,
            "price": day["close"],
            "rsi": technicals.get("rsi", 50),
            "macd": technicals.get("macd", 0),
        }
        for k, v in pit.items():
            record[k] = v
        record["actual_return_20d"] = (prices[i + 20]["close"] / day["close"]) - 1
        records.append(record)

    return records


# Fields fetch_ticker_replay_records() records can populate onto a
# MarketContext for historical replay. Shared by _signed_agent_scores and
# _record_to_market_context so there is exactly one place to update when
# adding a field -- see _record_to_market_context's docstring for the real
# bug this exact kind of two-copies drift already caused once
# (insider_ownership/institutional_ownership never being added here).
_REPLAY_RECORD_FIELDS = (
    "price", "pe", "pb", "roe", "gross_margins", "revenue_growth",
    "debt_ratio", "fcf", "market_cap", "operating_margins",
    "rsi", "macd", "earnings_growth", "current_ratio",
)


def _signed_agent_scores(ticker: str, record: Dict, agents) -> Dict[str, float]:
    """Run every agent on one (ticker, day) record, return signed scores.

    Signed-score convention (must match ``Backtester._calculate_consensus_ic``
    exactly, so flat and regime-weighted consensus differ ONLY by weighting,
    never by a drifted scoring convention): bullish -> +score,
    bearish -> -score, neutral -> 0.
    """
    from augur.personas.base import MarketContext

    ctx_kwargs = {"ticker": ticker.upper()}
    for k in _REPLAY_RECORD_FIELDS:
        if k in record:
            ctx_kwargs[k] = record[k]
    ctx = MarketContext(**ctx_kwargs)

    scores: Dict[str, float] = {}
    for agent in agents:
        try:
            result = agent.analyze(ctx)
            if result.signal.value == "bullish":
                scores[agent.agent_id] = result.score
            elif result.signal.value == "bearish":
                scores[agent.agent_id] = -result.score
            else:
                scores[agent.agent_id] = 0.0
        except Exception:
            continue
    return scores


def compute_cross_sectional_regime_ic(
    records_by_ticker: Dict[str, List[Dict]],
    date_to_regime: Dict[str, str],
    min_tickers_per_day: int = 5,
    bootstrap_resamples: int = 1000,
    bootstrap_block_size: int = 7,
    seed: int = 42,
) -> Dict:
    """Cross-sectional, per-day, regime-bucketed IC comparison.

    For each calendar date present in >= ``min_tickers_per_day`` tickers'
    record lists: compute every agent's signed score for every ticker on
    that date, build (a) a flat equal-weight consensus and (b) an
    ``apply_regime_weights``-reweighted consensus (using that date's
    regime), then rank-correlate each consensus across tickers against
    ``actual_return_20d`` (Spearman, via ``Backtester._rank_correlation``).
    Per-day ICs are then bucketed by regime and averaged.

    Returns a dict with:
      - "per_regime": {regime: {"flat_ic_mean", "regime_ic_mean", "delta",
          "n_days"}}
      - "per_agent_by_regime": {regime: {agent_id: mean_cross_sectional_ic}} --
          diagnostic: per-agent daily cross-sectional IC averaged by regime.
          Tells you whether the agents upweighted in that regime actually
          predicted better cross-sectionally, not just whether they were
          more bullish/bearish on average.
      - "bear_high_vol_bootstrap": {"delta_mean", "ci_low", "ci_high",
          "n_days", "n_blocks"} or None if BEAR_HIGH_VOL has zero days.
      - "n_days_total", "n_days_skipped_thin": diagnostics.
    """
    import random as _random

    from augur.registry import AgentRegistry
    from augur.consensus.regime_weights import apply_regime_weights

    registry = AgentRegistry()
    agents = registry.get_all()
    agent_ids = [a.agent_id for a in agents]
    base_weights = {aid: 1.0 / len(agent_ids) for aid in agent_ids}

    bt = Backtester()

    # Build date -> {ticker: record} for tickers that have data on that date.
    dates_to_ticker_records: Dict[str, Dict[str, Dict]] = {}
    for ticker, records in records_by_ticker.items():
        for rec in records:
            dates_to_ticker_records.setdefault(rec["date"], {})[ticker] = rec

    daily_results = []  # list of dicts: date, regime, flat_ic, regime_ic, agent_scores_by_ticker
    n_skipped_thin = 0

    for date_str in sorted(dates_to_ticker_records.keys()):
        ticker_records = dates_to_ticker_records[date_str]
        if len(ticker_records) < min_tickers_per_day:
            n_skipped_thin += 1
            continue

        regime = date_to_regime.get(date_str, "SIDEWAYS")
        regime_weights = apply_regime_weights(dict(base_weights), regime)

        flat_scores = []
        regime_scores = []
        actual_returns = []
        # per_agent_scores[aid] and per_agent_returns[aid] are parallel lists:
        # both appended in the same ticker iteration order so _rank_correlation
        # across them gives each agent's cross-sectional IC for this day.
        per_agent_scores: Dict[str, List[float]] = {aid: [] for aid in agent_ids}
        per_agent_returns: Dict[str, List[float]] = {aid: [] for aid in agent_ids}

        for ticker, rec in ticker_records.items():
            agent_scores = _signed_agent_scores(ticker, rec, agents)
            if not agent_scores:
                continue
            flat_avg = sum(agent_scores.values()) / len(agent_scores)
            regime_avg = sum(
                agent_scores.get(aid, 0.0) * regime_weights.get(aid, 0.0)
                for aid in agent_ids
            )
            flat_scores.append(flat_avg)
            regime_scores.append(regime_avg)
            actual_returns.append(rec["actual_return_20d"])
            ret = rec["actual_return_20d"]
            for aid, sc in agent_scores.items():
                per_agent_scores.setdefault(aid, []).append(sc)
                per_agent_returns.setdefault(aid, []).append(ret)

        if len(flat_scores) < min_tickers_per_day:
            n_skipped_thin += 1
            continue

        flat_ic = bt._rank_correlation(flat_scores, actual_returns)
        regime_ic = bt._rank_correlation(regime_scores, actual_returns)

        # Per-agent cross-sectional IC: rank_corr(agent scores across tickers,
        # actual returns across same tickers). Requires >=3 tickers scored.
        per_agent_ic: Dict[str, float] = {}
        for aid in agent_ids:
            sc_list = per_agent_scores.get(aid, [])
            ret_list = per_agent_returns.get(aid, [])
            if len(sc_list) >= 3:
                per_agent_ic[aid] = bt._rank_correlation(sc_list, ret_list)
            else:
                per_agent_ic[aid] = 0.0

        daily_results.append({
            "date": date_str,
            "regime": regime,
            "flat_ic": flat_ic,
            "regime_ic": regime_ic,
            "delta": regime_ic - flat_ic,
            "per_agent_ic": per_agent_ic,
        })

    # --- Per-regime aggregation ---
    per_regime: Dict[str, Dict] = {}
    per_agent_by_regime: Dict[str, Dict[str, float]] = {}
    for row in daily_results:
        regime = row["regime"]
        bucket = per_regime.setdefault(regime, {"flat_ics": [], "regime_ics": [], "deltas": []})
        bucket["flat_ics"].append(row["flat_ic"])
        bucket["regime_ics"].append(row["regime_ic"])
        bucket["deltas"].append(row["delta"])

        agent_bucket = per_agent_by_regime.setdefault(regime, {})
        for aid, ic_val in row["per_agent_ic"].items():
            agent_bucket.setdefault(aid, []).append(ic_val)

    per_regime_summary: Dict[str, Dict] = {}
    for regime, bucket in per_regime.items():
        n = len(bucket["deltas"])
        per_regime_summary[regime] = {
            "flat_ic_mean": round(sum(bucket["flat_ics"]) / n, 4) if n else 0.0,
            "regime_ic_mean": round(sum(bucket["regime_ics"]) / n, 4) if n else 0.0,
            "delta_mean": round(sum(bucket["deltas"]) / n, 4) if n else 0.0,
            "n_days": n,
        }

    per_agent_by_regime_summary: Dict[str, Dict[str, float]] = {}
    for regime, agent_bucket in per_agent_by_regime.items():
        per_agent_by_regime_summary[regime] = {
            aid: round(sum(vals) / len(vals), 3) for aid, vals in agent_bucket.items() if vals
        }

    # --- BEAR_HIGH_VOL block bootstrap ---
    bear_rows = [row for row in daily_results if row["regime"] == "BEAR_HIGH_VOL"]
    bear_bootstrap = None
    if bear_rows:
        deltas = [row["delta"] for row in bear_rows]
        n = len(deltas)
        rng = _random.Random(seed)
        block = max(1, min(bootstrap_block_size, n))
        n_blocks_needed = max(1, math.ceil(n / block))
        boot_means = []
        for _ in range(bootstrap_resamples):
            sample: List[float] = []
            for _b in range(n_blocks_needed):
                start_idx = rng.randint(0, n - block) if n > block else 0
                sample.extend(deltas[start_idx:start_idx + block])
            sample = sample[:n]
            if sample:
                boot_means.append(sum(sample) / len(sample))
        boot_means.sort()
        if boot_means:
            lo_idx = int(0.05 * len(boot_means))
            hi_idx = min(len(boot_means) - 1, int(0.95 * len(boot_means)))
            # Regime is a market-wide label, not a per-ticker one: a wider
            # ticker universe adds cross-sectional breadth per day, never
            # more days. BEAR_HIGH_VOL days cluster into a handful of short,
            # autocorrelated market episodes (e.g. a single-week selloff),
            # so a small n_days here is not "a small sample of independent
            # observations" -- it can be just 1-2 *episodes* repeated across
            # consecutive days. A bootstrap CI computed on that is a
            # mechanical statistic, not evidence of statistical power, and
            # must be labeled as such rather than read as significance.
            low_power = n < 30
            bear_bootstrap = {
                "delta_mean": round(sum(deltas) / n, 4),
                "ci_low": round(boot_means[lo_idx], 4),
                "ci_high": round(boot_means[hi_idx], 4),
                "n_days": n,
                "n_blocks_per_resample": n_blocks_needed,
                "block_size": block,
                "low_power_warning": (
                    "n_days < 30 and BEAR_HIGH_VOL days cluster into a small number of "
                    "short market episodes (consecutive trading days within the same "
                    "selloff), not independent draws -- this CI is a mechanical "
                    "computation, not inferential evidence of statistical power. "
                    "Treat as directional only."
                    if low_power else None
                ),
            }

    return {
        "per_regime": per_regime_summary,
        "per_agent_by_regime": per_agent_by_regime_summary,
        "bear_high_vol_bootstrap": bear_bootstrap,
        "n_days_total": len(daily_results),
        "n_days_skipped_thin": n_skipped_thin,
    }


def _record_to_market_context(ticker: str, record: Dict):
    """Build a MarketContext from one fetch_ticker_replay_records() record.

    Deliberately a separate small helper from _signed_agent_scores' inline
    version rather than a shared function -- this keeps the new, less-tested
    factor-attribution path from risking a regression in the already-shipped
    regime-IC path by touching its control flow. The field list itself
    (``_REPLAY_RECORD_FIELDS``) IS shared between the two, though -- the two
    functions duplicating that literal is exactly what caused the gap
    documented below to go unnoticed, so the list itself is a single source
    of truth even though the surrounding function bodies stay separate.

    Known gap (found via a real factor_attribution.py run, 2026-07-14):
    ``insider_ownership`` and ``institutional_ownership`` are never in this
    field list, so every MarketContext built here has both at the
    MarketContext dataclass default (0) -- there is no free historical
    time series for ownership *percentage* the way there is for EDGAR
    fundamentals (this is a different EDGAR gap than
    insider_buying_signal/institutional_flow_signal, which track *trading
    activity*, not ownership %, and are separately not wired into any
    persona's factors -- see scripts/factor_attribution.py's docstring).
    Effect: every persona factor that branches on these two fields (11
    personas as of this writing: aschenbrenner, buffett, dan_bin, dayu,
    duan_yongping, fisher, li_lu, marks, munger, thiel, zhang_lei) silently
    collapses to whatever it reduces to with both pinned at 0 in every
    backtest-replay-based analysis (this function, _signed_agent_scores,
    and therefore compute_cross_sectional_regime_ic,
    compute_factor_cross_sectional_ic, regime_weight_oos.py,
    generate_agent_correlation.py, and generate_rolling_ic.py all inherit
    this). Concretely: li_lu's "management_quality" and zhang_lei's
    "management_excellence" both reduce to pure monotonic step functions of
    roe alone, which is why factor_attribution.py's 2026-07-14 full run
    found them bit-identical in rank-IC (Spearman only depends on rank, and
    monotonic transforms of the same underlying variable rank identically)
    -- a real, structural artifact of this gap, not independent validation
    of two different "management quality" signals. See
    docs/FACTOR_ATTRIBUTION_FINDINGS_2026-07.md for the full writeup.
    """
    from augur.personas.base import MarketContext

    ctx_kwargs = {"ticker": ticker.upper()}
    for k in _REPLAY_RECORD_FIELDS:
        if k in record:
            ctx_kwargs[k] = record[k]
    return MarketContext(**ctx_kwargs)


def compute_factor_cross_sectional_ic(
    records_by_ticker: Dict[str, List[Dict]],
    agents,
    min_tickers_per_day: int = 5,
    min_half_ic: float = 0.02,
) -> Dict:
    """Cross-sectional, per-day, per-factor IC across every persona's
    ``metadata["factors"]`` output.

    Reuses the same replay records as ``compute_cross_sectional_regime_ic``
    (see ``fetch_ticker_replay_records``): for each (ticker, date), builds
    one ``MarketContext`` and runs every agent once, collecting every
    numeric entry of ``result.metadata["factors"]`` namespaced as
    ``"{agent_id}.{factor_name}"`` (personas reuse factor names like
    "quality" or "value" for different formulas, so namespacing avoids
    silently averaging together two unrelated things). Each factor's daily
    cross-sectional values are rank-correlated (Spearman, via
    ``Backtester._rank_correlation``) against ``actual_return_20d`` and
    averaged across qualifying days (>= ``min_tickers_per_day`` tickers
    scored that day).

    Multiple-comparison guard: with on the order of a hundred factor keys
    (18 personas x ~4-6 factors each) tested against the same window, some
    will show a "significant" whole-window IC by chance alone -- this
    project has been burned by exactly this shape of false positive before
    (see docs/PROJECT_REVIEW_AND_ROADMAP_2026-07.md's regime-weights
    section). To guard against it cheaply, the qualifying days are split in
    half chronologically and each factor's IC is computed independently in
    each half. ``split_half_stable`` is True only when both halves have
    >= 3 days, both half-ICs meet ``min_half_ic`` in magnitude, and they
    agree in sign -- a factor that flips sign or vanishes between halves is
    still reported (never silently dropped) but flagged as unstable rather
    than presented as a finding.

    Returns:
      {"per_factor": {factor_key: {"ic_mean", "n_days", "first_half_ic",
          "second_half_ic", "split_half_stable"}},
       "n_days_total", "n_days_skipped_thin"}
    """
    bt = Backtester()

    dates_to_ticker_records: Dict[str, Dict[str, Dict]] = {}
    for ticker, records in records_by_ticker.items():
        for rec in records:
            dates_to_ticker_records.setdefault(rec["date"], {})[ticker] = rec

    qualifying_dates: List[str] = []
    per_factor_by_date: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    n_skipped_thin = 0

    for date_str in sorted(dates_to_ticker_records.keys()):
        ticker_records = dates_to_ticker_records[date_str]
        if len(ticker_records) < min_tickers_per_day:
            n_skipped_thin += 1
            continue
        qualifying_dates.append(date_str)

        factor_values: Dict[str, List[float]] = {}
        factor_returns: Dict[str, List[float]] = {}
        for ticker, rec in ticker_records.items():
            ctx = _record_to_market_context(ticker, rec)
            ret = rec["actual_return_20d"]
            for agent in agents:
                try:
                    result = agent.analyze(ctx)
                except Exception:
                    continue
                factors = (result.metadata or {}).get("factors") or {}
                for fname, fval in factors.items():
                    if isinstance(fval, bool) or not isinstance(fval, (int, float)):
                        continue
                    key = f"{agent.agent_id}.{fname}"
                    factor_values.setdefault(key, []).append(float(fval))
                    factor_returns.setdefault(key, []).append(ret)
        per_factor_by_date[date_str] = {"values": factor_values, "returns": factor_returns}

    n_days_total = len(qualifying_dates)
    half = n_days_total // 2
    first_half_dates = set(qualifying_dates[:half])
    second_half_dates = set(qualifying_dates[half:])

    all_ics: Dict[str, List[float]] = {}
    first_half_ics: Dict[str, List[float]] = {}
    second_half_ics: Dict[str, List[float]] = {}

    for date_str, bundle in per_factor_by_date.items():
        for key, values in bundle["values"].items():
            returns = bundle["returns"][key]
            if len(values) < min_tickers_per_day:
                continue
            ic = bt._rank_correlation(values, returns)
            all_ics.setdefault(key, []).append(ic)
            if date_str in first_half_dates:
                first_half_ics.setdefault(key, []).append(ic)
            elif date_str in second_half_dates:
                second_half_ics.setdefault(key, []).append(ic)

    per_factor: Dict[str, Dict] = {}
    for key, ics in all_ics.items():
        n_days = len(ics)
        ic_mean = sum(ics) / n_days if n_days else 0.0
        fh = first_half_ics.get(key, [])
        sh = second_half_ics.get(key, [])
        fh_mean = sum(fh) / len(fh) if fh else 0.0
        sh_mean = sum(sh) / len(sh) if sh else 0.0
        stable = (
            len(fh) >= 3 and len(sh) >= 3
            and abs(fh_mean) >= min_half_ic and abs(sh_mean) >= min_half_ic
            and (fh_mean > 0) == (sh_mean > 0)
        )
        per_factor[key] = {
            "ic_mean": round(ic_mean, 4),
            "n_days": n_days,
            "first_half_ic": round(fh_mean, 4),
            "second_half_ic": round(sh_mean, 4),
            "split_half_stable": stable,
        }

    return {
        "per_factor": per_factor,
        "n_days_total": n_days_total,
        "n_days_skipped_thin": n_skipped_thin,
    }
