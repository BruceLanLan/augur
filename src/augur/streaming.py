# -*- coding: utf-8 -*-
"""
augur.streaming - Real-time Price Streaming via WebSocket

Fetches real prices from yfinance, falls back to random-walk when unavailable.

Architecture:
    - PriceStreamer: Core streaming service with asyncio event loop integration
    - _fetch_real_prices(): calls yfinance in a thread pool (non-blocking)
    - Auto-stops when the last client disconnects (resource cleanup)
    - Falls back to random-walk mock on any yfinance error

Configuration:
    - tickers: List of symbols to stream (default: 15 major tickers)
    - interval: Seconds between price updates (default: 60)
    - max_clients: Max concurrent WebSocket clients (default: 100)
"""

import asyncio
import json
import random
import time
from typing import Dict, List, Set, Any, Optional

from fastapi import WebSocket


DEFAULT_TICKERS = [
    "AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "META", "AMZN",
    "BRK-B", "JPM", "V", "PDD", "BIDU", "AMD", "INTC", "QCOM",
]

# Seed prices used on startup and as fallback reference
_SEED_PRICES: Dict[str, float] = {
    "AAPL": 210.50, "NVDA": 135.20, "MSFT": 445.80, "GOOGL": 178.30,
    "TSLA": 248.60, "META": 520.40, "AMZN": 195.70, "BRK-B": 428.90,
    "JPM": 205.10, "V": 285.60, "PDD": 128.40, "BIDU": 98.50,
    "AMD": 165.30, "INTC": 32.80, "QCOM": 175.20,
}


def _fetch_yfinance_prices(tickers: List[str]) -> Dict[str, float]:
    """Fetch current prices from yfinance. Returns {ticker: price} or {} on error."""
    try:
        import yfinance as yf
        symbols = " ".join(t.replace(".", "-") for t in tickers)
        data = yf.download(symbols, period="1d", interval="1m",
                           progress=False, auto_adjust=True)
        if data is None or data.empty:
            return {}

        prices: Dict[str, float] = {}
        # Multi-ticker: columns are MultiIndex (field, ticker)
        if hasattr(data.columns, "levels"):
            close = data["Close"] if "Close" in data else None
            if close is not None:
                for ticker in tickers:
                    sym = ticker.replace(".", "-")
                    if sym in close.columns:
                        val = close[sym].dropna().iloc[-1] if not close[sym].dropna().empty else None
                        if val:
                            prices[ticker] = round(float(val), 2)
        else:
            # Single ticker
            if "Close" in data.columns:
                val = data["Close"].dropna().iloc[-1] if not data["Close"].dropna().empty else None
                if val:
                    prices[tickers[0]] = round(float(val), 2)

        return prices
    except Exception:
        return {}


class PriceStreamer:
    """
    Real-time price streaming service.

    Fetches actual market prices via yfinance; on failure falls back to
    random-walk simulation so the WebSocket connection never drops.
    """

    def __init__(self, tickers: List[str] = None, interval: float = 60.0, max_clients: int = 100):
        self.tickers = tickers or DEFAULT_TICKERS
        self.interval = interval
        self.max_clients = max_clients
        self._clients: Set[WebSocket] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._prices: Dict[str, Dict[str, Any]] = {}
        self._last_real_fetch: float = 0.0
        self._initialize_prices()

    def _initialize_prices(self):
        """Seed with known base prices; real values will be fetched on first update."""
        for ticker in self.tickers:
            base = _SEED_PRICES.get(ticker, 100.0 + random.uniform(-20, 80))
            self._prices[ticker] = {
                "ticker": ticker,
                "price": base,
                "change": 0.0,
                "change_pct": 0.0,
                "volume": random.randint(1_000_000, 50_000_000),
                "source": "seed",
                "timestamp": time.time(),
            }

    def _apply_random_walk(self, ticker: str) -> Dict[str, Any]:
        """Small random-walk step on the current price — used as fallback."""
        current = self._prices.get(ticker, {})
        prev = current.get("price", _SEED_PRICES.get(ticker, 100.0))
        pct = random.gauss(0, 0.003)
        pct = max(-0.015, min(0.015, pct))
        new_price = round(prev * (1 + pct), 2)
        update = {
            "ticker": ticker,
            "price": new_price,
            "change": round(new_price - prev, 2),
            "change_pct": round(pct * 100, 2),
            "volume": random.randint(1_000_000, 50_000_000),
            "source": "mock",
            "timestamp": time.time(),
        }
        self._prices[ticker] = update
        return update

    async def _update_prices(self) -> List[Dict[str, Any]]:
        """
        Fetch real prices from yfinance in a thread pool.
        Falls back to random-walk for any ticker that fails.
        Real fetches are throttled to once per `interval` seconds.
        """
        loop = asyncio.get_event_loop()
        real_prices: Dict[str, float] = {}

        # Only call yfinance when enough time has elapsed
        if time.time() - self._last_real_fetch >= self.interval:
            try:
                real_prices = await loop.run_in_executor(
                    None, _fetch_yfinance_prices, self.tickers
                )
                if real_prices:
                    self._last_real_fetch = time.time()
            except Exception:
                pass

        updates = []
        for ticker in self.tickers:
            if ticker in real_prices:
                prev = self._prices.get(ticker, {}).get("price", real_prices[ticker])
                new_price = real_prices[ticker]
                change = round(new_price - prev, 2)
                change_pct = round((change / prev * 100) if prev else 0, 2)
                update = {
                    "ticker": ticker,
                    "price": new_price,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": random.randint(1_000_000, 50_000_000),
                    "source": "live",
                    "timestamp": time.time(),
                }
                self._prices[ticker] = update
            else:
                update = self._apply_random_walk(ticker)
            updates.append(update)

        return updates

    def get_current_prices(self) -> List[Dict[str, Any]]:
        return list(self._prices.values())

    async def connect(self, websocket: WebSocket):
        if len(self._clients) >= self.max_clients:
            return
        self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        self._clients.discard(websocket)
        if not self._clients and self._running:
            await self.stop()

    async def broadcast(self, data: Dict[str, Any]):
        if not self._clients:
            return
        message = json.dumps(data)
        disconnected = set()
        for client in self._clients.copy():
            try:
                await client.send_text(message)
            except Exception:
                disconnected.add(client)
        self._clients -= disconnected

    async def _stream_loop(self):
        while self._running:
            try:
                updates = await self._update_prices()
                payload = {
                    "type": "price_update",
                    "prices": updates,
                    "timestamp": time.time(),
                }
                await self.broadcast(payload)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            await asyncio.sleep(self.interval)

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._stream_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def client_count(self) -> int:
        return len(self._clients)
