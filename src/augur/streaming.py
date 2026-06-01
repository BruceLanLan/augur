# -*- coding: utf-8 -*-
"""
augur.streaming - Real-time Price Streaming via WebSocket

Provides a PriceStreamer class that periodically generates mock price data
and broadcasts to connected WebSocket clients. Manages client lifecycle
with automatic start/stop based on connection count.

Architecture:
    - PriceStreamer: Core streaming service with asyncio event loop integration
    - Generates random-walk price updates for configurable ticker list
    - Broadcasts JSON payloads to all connected WebSocket clients
    - Auto-stops when the last client disconnects (resource cleanup)

Usage:
    streamer = PriceStreamer(tickers=["AAPL", "NVDA"], interval=30.0)
    await streamer.connect(websocket)
    await streamer.start()
    # ... later ...
    await streamer.disconnect(websocket)  # auto-stops if last client

Configuration:
    - tickers: List of symbols to stream (default: 15 major tickers)
    - interval: Seconds between price updates (default: 60)

Error Handling:
    - Gracefully handles WebSocket disconnects during broadcast
    - Catches asyncio.CancelledError in streaming loop for clean shutdown
    - Tolerates individual client send failures without stopping the stream
"""

import asyncio
import json
import random
import time
from typing import Dict, List, Set, Any

from fastapi import WebSocket


# Default tickers to stream
DEFAULT_TICKERS = [
    "AAPL", "NVDA", "MSFT", "GOOGL", "TSLA", "META", "AMZN",
    "BRK.B", "JPM", "V", "PDD", "BIDU", "AMD", "INTC", "QCOM",
]

# Base prices for mock data generation
_BASE_PRICES: Dict[str, float] = {
    "AAPL": 210.50,
    "NVDA": 135.20,
    "MSFT": 445.80,
    "GOOGL": 178.30,
    "TSLA": 248.60,
    "META": 520.40,
    "AMZN": 195.70,
    "BRK.B": 428.90,
    "JPM": 205.10,
    "V": 285.60,
    "PDD": 128.40,
    "BIDU": 98.50,
    "AMD": 165.30,
    "INTC": 32.80,
    "QCOM": 175.20,
}


class PriceStreamer:
    """
    Real-time price streaming service.

    Generates mock price updates and broadcasts them to connected
    WebSocket clients. In production, this would integrate with
    a real market data provider (e.g., yfinance, polygon.io).
    """

    def __init__(self, tickers: List[str] = None, interval: float = 60.0, max_clients: int = 100):
        """
        Initialize the PriceStreamer.

        Args:
            tickers: List of ticker symbols to stream. Defaults to DEFAULT_TICKERS.
            interval: Update interval in seconds. Defaults to 60.
            max_clients: Maximum number of concurrent WebSocket clients. Defaults to 100.
        """
        self.tickers = tickers or DEFAULT_TICKERS
        self.interval = interval
        self.max_clients = max_clients
        self._clients: Set[WebSocket] = set()
        self._running = False
        self._task = None
        self._prices: Dict[str, Dict[str, Any]] = {}
        self._initialize_prices()

    def _initialize_prices(self):
        """Initialize prices with base values."""
        for ticker in self.tickers:
            base = _BASE_PRICES.get(ticker, 100.0 + random.uniform(-20, 80))
            self._prices[ticker] = {
                "ticker": ticker,
                "price": base,
                "change": 0.0,
                "change_pct": 0.0,
                "volume": random.randint(1_000_000, 50_000_000),
                "timestamp": time.time(),
            }

    def _generate_price_update(self, ticker: str) -> Dict[str, Any]:
        """Generate a mock price update with random walk."""
        current = self._prices.get(ticker, {})
        prev_price = current.get("price", 100.0)

        # Random walk: -2% to +2% change
        change_pct = random.gauss(0, 0.005)  # Normal distribution
        change_pct = max(-0.02, min(0.02, change_pct))
        new_price = prev_price * (1 + change_pct)
        new_price = round(new_price, 2)
        change = round(new_price - prev_price, 2)

        update = {
            "ticker": ticker,
            "price": new_price,
            "change": change,
            "change_pct": round(change_pct * 100, 2),
            "volume": random.randint(1_000_000, 50_000_000),
            "timestamp": time.time(),
        }
        self._prices[ticker] = update
        return update

    def get_current_prices(self) -> List[Dict[str, Any]]:
        """Get current price snapshot for all tickers."""
        return list(self._prices.values())

    async def connect(self, websocket: WebSocket):
        """Register a new WebSocket client. Rejects if at max capacity."""
        if len(self._clients) >= self.max_clients:
            # Reject connection if at capacity to prevent memory leaks
            return
        self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket client. Stop streamer if no clients remain."""
        self._clients.discard(websocket)
        if not self._clients and self._running:
            await self.stop()

    async def broadcast(self, data: Dict[str, Any]):
        """Broadcast data to all connected clients."""
        if not self._clients:
            return
        message = json.dumps(data)
        disconnected = set()
        for client in self._clients.copy():
            try:
                await client.send_text(message)
            except (RuntimeError, ConnectionError, OSError):
                # WebSocket disconnected or closed unexpectedly
                disconnected.add(client)
            except Exception:
                # Catch any other WebSocket-related errors gracefully
                disconnected.add(client)
        self._clients -= disconnected

    async def _stream_loop(self):
        """Main streaming loop that generates and broadcasts price updates."""
        while self._running:
            try:
                updates = []
                for ticker in self.tickers:
                    update = self._generate_price_update(ticker)
                    updates.append(update)

                payload = {
                    "type": "price_update",
                    "prices": updates,
                    "timestamp": time.time(),
                }
                await self.broadcast(payload)
            except asyncio.CancelledError:
                break
            except Exception:
                # Gracefully handle any error in the streaming loop
                pass
            await asyncio.sleep(self.interval)

    async def start(self):
        """Start the streaming loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._stream_loop())

    async def stop(self):
        """Stop the streaming loop."""
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
        """Check if the streamer is currently running."""
        return self._running

    @property
    def client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self._clients)
