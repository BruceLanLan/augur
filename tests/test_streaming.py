# -*- coding: utf-8 -*-
"""Tests for augur.streaming - Real-time Price Streaming"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from augur.streaming import PriceStreamer, DEFAULT_TICKERS, _SEED_PRICES, _fetch_yfinance_prices


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


def test_price_streamer_apply_random_walk():
    """Test that price updates produce valid data with random walk."""
    streamer = PriceStreamer(tickers=["AAPL"])
    initial_price = streamer._prices["AAPL"]["price"]

    update = streamer._apply_random_walk("AAPL")
    assert update["ticker"] == "AAPL"
    assert update["price"] > 0
    assert isinstance(update["change"], float)
    assert isinstance(update["change_pct"], float)
    # Price should be within 2% of initial
    assert abs(update["price"] - initial_price) / initial_price <= 0.02


def test_price_streamer_initialize_prices():
    """Test that initial prices are set from base prices."""
    streamer = PriceStreamer(tickers=["AAPL", "NVDA"])
    assert streamer._prices["AAPL"]["price"] == _SEED_PRICES["AAPL"]
    assert streamer._prices["NVDA"]["price"] == _SEED_PRICES["NVDA"]


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


# --- Round 5 additions: tick, reconnect, callback error, backoff, dedup ---


def test_streaming_tick_updates_all_tickers():
    """A single _update_prices tick should produce one update per ticker with valid fields."""
    async def _run():
        streamer = PriceStreamer(tickers=["AAPL", "MSFT"], interval=0.01)
        updates = await streamer._update_prices()
        assert len(updates) == 2
        tickers_seen = {u["ticker"] for u in updates}
        assert tickers_seen == {"AAPL", "MSFT"}
        for u in updates:
            assert u["source"] in ("live", "mock")
            assert u["price"] > 0
            assert "timestamp" in u
            assert u["volume"] > 0

    asyncio.run(_run())


def test_streaming_tick_persists_into_get_current_prices():
    """A tick should refresh the in-memory price cache exposed via get_current_prices()."""
    async def _run():
        streamer = PriceStreamer(tickers=["AAPL"], interval=0.01)
        before_ts = streamer.get_current_prices()[0]["timestamp"]
        # Force a tiny sleep so the timestamp is observably different after the tick
        await asyncio.sleep(0.01)
        await streamer._update_prices()
        after = streamer.get_current_prices()[0]
        assert after["ticker"] == "AAPL"
        assert "timestamp" in after
        assert isinstance(after["price"], float)
        assert after["timestamp"] >= before_ts, "tick should refresh the timestamp"

    asyncio.run(_run())


def test_streaming_reconnect_after_disconnect():
    """A client that disconnects should be able to reconnect with a fresh WebSocket."""
    async def _run():
        streamer = PriceStreamer()
        old_ws = AsyncMock()
        new_ws = AsyncMock()

        assert await streamer.connect(old_ws) is True
        assert streamer.client_count == 1

        await streamer.disconnect(old_ws)
        assert streamer.client_count == 0

        # Reconnect with a different WebSocket object
        assert await streamer.connect(new_ws) is True
        assert streamer.client_count == 1
        assert new_ws in streamer._clients
        assert old_ws not in streamer._clients

        await streamer.disconnect(new_ws)

    asyncio.run(_run())


def test_streaming_callback_error_does_not_propagate():
    """A send_text exception in one client must not break broadcast to other clients."""
    async def _run():
        streamer = PriceStreamer()
        good_a = AsyncMock()
        bad = AsyncMock()
        bad.send_text.side_effect = RuntimeError("client went away")
        good_b = AsyncMock()

        for ws in (good_a, bad, good_b):
            await streamer.connect(ws)
        assert streamer.client_count == 3

        # Broadcast must swallow the error from `bad` and still deliver to good_*
        await streamer.broadcast({"type": "price_update", "prices": [], "ts": 1.0})

        good_a.send_text.assert_called_once()
        good_b.send_text.assert_called_once()
        # The failing client should have been pruned from the set
        assert streamer.client_count == 2
        assert bad not in streamer._clients

    asyncio.run(_run())


def test_streaming_backoff_throttles_real_fetches():
    """_update_prices should not invoke yfinance more than once per `interval` seconds."""
    async def _run():
        streamer = PriceStreamer(tickers=["AAPL"], interval=60.0)
        # Force the throttle window to look "fresh" so the first tick tries yfinance
        streamer._last_real_fetch = 0.0

        # Return a non-empty dict so _update_prices actually advances the throttle
        # window (it only does so when at least one ticker came back as a real price).
        with patch(
            "augur.streaming._fetch_yfinance_prices",
            return_value={"AAPL": 211.0},
        ) as fake:
            # First call: elapsed > interval -> should call yfinance once
            await streamer._update_prices()
            assert fake.call_count == 1
            assert streamer._last_real_fetch > 0.0, "successful fetch should stamp the throttle"

            # Second call immediately after: elapsed < interval -> throttled
            await streamer._update_prices()
            assert fake.call_count == 1, "second tick within interval should be throttled"

            # Move the clock forward past the interval -> should call again
            streamer._last_real_fetch = time.time() - 120.0
            await streamer._update_prices()
            assert fake.call_count == 2

    asyncio.run(_run())


def test_streaming_dedups_repeat_connect_for_same_websocket():
    """Connecting the same WebSocket object twice should not double-count it."""
    async def _run():
        streamer = PriceStreamer()
        ws = AsyncMock()

        assert await streamer.connect(ws) is True
        assert streamer.client_count == 1

        # Re-connecting the same instance should be a no-op (Set semantics)
        assert await streamer.connect(ws) is True
        assert streamer.client_count == 1, "duplicate connect should be deduped"

        # And a disconnect of that single instance should empty the set
        await streamer.disconnect(ws)
        assert streamer.client_count == 0

    asyncio.run(_run())
