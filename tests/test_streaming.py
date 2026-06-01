# -*- coding: utf-8 -*-
"""Tests for augur.streaming - Real-time Price Streaming"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from augur.streaming import PriceStreamer, DEFAULT_TICKERS, _BASE_PRICES


def test_price_streamer_init():
    """Test PriceStreamer initialization with default tickers."""
    streamer = PriceStreamer()
    assert streamer.tickers == DEFAULT_TICKERS
    assert streamer.interval == 60.0
    assert streamer.is_running is False
    assert streamer.client_count == 0


def test_price_streamer_custom_tickers():
    """Test PriceStreamer with custom tickers and interval."""
    custom = ["AAPL", "MSFT"]
    streamer = PriceStreamer(tickers=custom, interval=30.0)
    assert streamer.tickers == custom
    assert streamer.interval == 30.0


def test_price_streamer_get_current_prices():
    """Test getting current prices returns all tickers."""
    streamer = PriceStreamer()
    prices = streamer.get_current_prices()
    assert len(prices) == len(DEFAULT_TICKERS)
    for p in prices:
        assert "ticker" in p
        assert "price" in p
        assert "change" in p
        assert "change_pct" in p
        assert "timestamp" in p
        assert p["price"] > 0


def test_price_streamer_generate_price_update():
    """Test that price updates produce valid data with random walk."""
    streamer = PriceStreamer(tickers=["AAPL"])
    initial_price = streamer._prices["AAPL"]["price"]

    update = streamer._generate_price_update("AAPL")
    assert update["ticker"] == "AAPL"
    assert update["price"] > 0
    assert isinstance(update["change"], float)
    assert isinstance(update["change_pct"], float)
    # Price should be within 2% of initial
    assert abs(update["price"] - initial_price) / initial_price <= 0.02


def test_price_streamer_initialize_prices():
    """Test that initial prices are set from base prices."""
    streamer = PriceStreamer(tickers=["AAPL", "NVDA"])
    assert streamer._prices["AAPL"]["price"] == _BASE_PRICES["AAPL"]
    assert streamer._prices["NVDA"]["price"] == _BASE_PRICES["NVDA"]


def test_price_streamer_connect_disconnect():
    """Test WebSocket client connection and disconnection."""
    async def _run():
        streamer = PriceStreamer()
        mock_ws = AsyncMock()
        await streamer.connect(mock_ws)
        assert streamer.client_count == 1
        await streamer.disconnect(mock_ws)
        assert streamer.client_count == 0

    asyncio.run(_run())


def test_price_streamer_broadcast():
    """Test broadcasting to connected clients."""
    async def _run():
        streamer = PriceStreamer()
        mock_ws = AsyncMock()
        await streamer.connect(mock_ws)
        await streamer.broadcast({"type": "test", "data": "hello"})
        mock_ws.send_text.assert_called_once()

    asyncio.run(_run())


def test_price_streamer_broadcast_removes_disconnected():
    """Test that disconnected clients are cleaned up during broadcast."""
    async def _run():
        streamer = PriceStreamer()
        mock_ws = AsyncMock()
        mock_ws.send_text.side_effect = Exception("disconnected")
        await streamer.connect(mock_ws)
        assert streamer.client_count == 1
        await streamer.broadcast({"type": "test"})
        assert streamer.client_count == 0

    asyncio.run(_run())
