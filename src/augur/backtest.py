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
    ) -> BacktestResult:
        """
        Run backtest: replay historical data through all agents.

        Args:
            ticker: Stock ticker
            historical_data: List of daily market contexts (dicts with metrics)
            forward_returns: List of forward returns for each date
                             Each dict has: date, return_5d, return_20d, return_60d

        Returns:
            BacktestResult with all records and IC calculations
        """
        if not historical_data or not forward_returns:
            return BacktestResult(ticker=ticker.upper())

        from augur.registry import AgentRegistry, DecisionCoordinator
        from augur.personas.base import MarketContext

        registry = AgentRegistry()
        coordinator = DecisionCoordinator(registry)
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

    def _calculate_ics(self, records: List[BacktestRecord]) -> List[AgentIC]:
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

    def _save_records(self, records: List[BacktestRecord]):
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

    def get_ic_report(self, agent_id: Optional[str] = None) -> List[AgentIC]:
        """Get IC from saved records"""
        records = self.load_records(agent_id=agent_id)
        if not records:
            return []
        return self._calculate_ics(records)

    def get_leaderboard(self) -> List[AgentIC]:
        """Get IC leaderboard sorted by IC 20d"""
        records = self.load_records()
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

            historical_data.append({
                "date": date_str,
                "price": day["close"],
                "rsi": technicals.get("rsi", 50),
                "macd": technicals.get("macd", 0),
                "sma20": technicals.get("sma20", 0),
                "sma50": technicals.get("sma50", 0),
            })

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

        return self.run_backtest(ticker, historical_data, forward_returns)


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
