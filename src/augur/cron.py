# -*- coding: utf-8 -*-
"""
augur.cron - Scheduled watchlist analysis

Reads watchlist from ~/.augur/watchlist.yaml, runs consensus analysis
on all tickers, and sends results to configured notification channels.

Configuration (~/.augur/watchlist.yaml):
  watchlist:
    - ticker: AAPL
      pe: 32
      roe: 0.55
      gross_margins: 0.46
    - ticker: NVDA
      pe: 45
      roe: 0.85

  schedule:
    cron: "0 9 * * 1-5"
    timezone: "Asia/Shanghai"

  notifications:
    telegram:
      enabled: true
      chat_id: "YOUR_CHAT_ID"
      token: "YOUR_BOT_TOKEN"
    alert_threshold: 3

CLI commands:
  augur cron-run       - Run watchlist analysis once
  augur cron-start     - Start scheduler daemon
  augur watchlist-add  - Add ticker to watchlist
  augur watchlist-show - Show current watchlist
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

WATCHLIST_PATH = Path.home() / ".augur" / "watchlist.yaml"

DEFAULT_CONFIG = {
    "watchlist": [],
    "schedule": {
        "cron": "0 9 * * 1-5",
        "timezone": "Asia/Shanghai",
    },
    "notifications": {
        "telegram": {
            "enabled": False,
            "chat_id": "",
            "token": "",
        },
        "alert_threshold": 3,
    },
}


def _ensure_config_dir():
    """Ensure ~/.augur/ directory exists."""
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_watchlist() -> dict:
    """Load watchlist configuration from ~/.augur/watchlist.yaml."""
    if not WATCHLIST_PATH.exists():
        return DEFAULT_CONFIG.copy()

    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Merge with defaults
    merged = DEFAULT_CONFIG.copy()
    merged.update(config)
    return merged


def save_watchlist(config: dict):
    """Save watchlist configuration to ~/.augur/watchlist.yaml."""
    _ensure_config_dir()
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def add_to_watchlist(ticker: str, metrics: Optional[Dict[str, float]] = None):
    """Add a ticker to the watchlist.

    Args:
        ticker: Stock ticker symbol
        metrics: Optional dict of metrics (pe, roe, gross_margins, etc.)
    """
    config = load_watchlist()
    watchlist = config.get("watchlist", [])

    # Check if ticker already exists
    for item in watchlist:
        if item.get("ticker", "").upper() == ticker.upper():
            # Update existing entry
            if metrics:
                item.update(metrics)
            return config

    # Add new entry
    entry = {"ticker": ticker.upper()}
    if metrics:
        entry.update(metrics)
    watchlist.append(entry)
    config["watchlist"] = watchlist

    save_watchlist(config)
    return config


def remove_from_watchlist(ticker: str) -> bool:
    """Remove a ticker from the watchlist."""
    config = load_watchlist()
    watchlist = config.get("watchlist", [])

    original_len = len(watchlist)
    watchlist = [w for w in watchlist if w.get("ticker", "").upper() != ticker.upper()]

    if len(watchlist) == original_len:
        return False

    config["watchlist"] = watchlist
    save_watchlist(config)
    return True


def run_watchlist_analysis() -> List[Dict[str, Any]]:
    """Run consensus analysis on all watchlist tickers.

    Returns:
        List of analysis results with ticker, consensus, and individual results.
    """
    from augur.personas.base import MarketContext
    from augur.registry import AgentRegistry, DecisionCoordinator
    from augur.bots.telegram_bot import format_consensus_message

    config = load_watchlist()
    watchlist = config.get("watchlist", [])

    if not watchlist:
        print("Watchlist is empty. Add tickers with: augur watchlist-add TICKER")
        return []

    registry = AgentRegistry()
    coordinator = DecisionCoordinator(registry)
    all_results = []

    for item in watchlist:
        ticker = item.get("ticker", "")
        if not ticker:
            continue

        print(f"Analyzing {ticker}...")

        # Build context from watchlist metrics
        ctx_kwargs = {"ticker": ticker.upper()}
        for key in ["pe", "pb", "roe", "gross_margins", "revenue_growth",
                    "debt_ratio", "fcf", "market_cap", "price"]:
            if key in item:
                ctx_kwargs[key] = item[key]

        ctx = MarketContext(**ctx_kwargs)
        results = coordinator.analyze_with_all(ctx)
        consensus = coordinator.get_consensus(results, ticker=ticker, context=ctx)

        analysis = {
            "ticker": ticker,
            "consensus": consensus,
            "results": results,
            "message": format_consensus_message(ticker, consensus, results),
        }
        all_results.append(analysis)

        print(f"  {ticker}: {consensus.signal.value.upper()} ({consensus.score:.1f}/10)")

    # Send notifications
    _send_notifications(config, all_results)

    return all_results


def _send_notifications(config: dict, results: List[Dict[str, Any]]):
    """Send analysis results to configured notification channels."""
    notifications = config.get("notifications", {})
    threshold = notifications.get("alert_threshold", 0)

    # Telegram notifications
    tg_config = notifications.get("telegram", {})
    if tg_config.get("enabled") and tg_config.get("chat_id") and tg_config.get("token"):
        _send_telegram_notifications(tg_config, results, threshold)


def _send_telegram_notifications(
    tg_config: dict, results: List[Dict[str, Any]], threshold: float
):
    """Send results to Telegram chat."""
    try:
        import asyncio
        from telegram import Bot
    except ImportError:
        print("Warning: python-telegram-bot not installed. Skipping Telegram notifications.")
        print("Install with: pip install 'augur-agents[telegram]'")
        return

    token = tg_config["token"]
    chat_id = tg_config["chat_id"]
    bot = Bot(token=token)

    async def _send():
        for analysis in results:
            message = analysis["message"]
            try:
                await bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                print(f"  Failed to send Telegram notification for {analysis['ticker']}: {e}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_send())
        else:
            loop.run_until_complete(_send())
    except RuntimeError:
        asyncio.run(_send())


def start_scheduler():
    """Start the APScheduler daemon for periodic watchlist analysis."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("Error: apscheduler is not installed.")
        print("Install with: pip install 'augur-agents[cron]'")
        print("  or: pip install apscheduler>=3.10.0")
        raise SystemExit(1)

    config = load_watchlist()
    schedule = config.get("schedule", {})
    cron_expr = schedule.get("cron", "0 9 * * 1-5")
    timezone = schedule.get("timezone", "Asia/Shanghai")

    # Parse cron expression (minute hour day month day_of_week)
    parts = cron_expr.split()
    if len(parts) != 5:
        print(f"Error: Invalid cron expression: {cron_expr}")
        print("Expected format: 'minute hour day month day_of_week'")
        print("Example: '0 9 * * 1-5' (weekdays at 9:00 AM)")
        raise SystemExit(1)

    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=timezone,
    )

    scheduler = BlockingScheduler(timezone=timezone)
    scheduler.add_job(run_watchlist_analysis, trigger, id="augur_watchlist")

    print(f"\U0001f989 Augur Cron Scheduler started!")
    print(f"   Schedule: {cron_expr} ({timezone})")
    print(f"   Watchlist: {len(config.get('watchlist', []))} tickers")
    print(f"   Config: {WATCHLIST_PATH}")
    print("")
    print("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")
