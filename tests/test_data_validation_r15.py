# -*- coding: utf-8 -*-
"""Round 15: tests for augur.data input-validation gaps.

Covers three regressions fixed in this round:

1. ``_normalize_ticker`` accepted tickers with leading or trailing ``.`` / ``-``
   (e.g. ``".AAPL"``, ``"AAPL."``, ``"-AAPL"``, ``"AAPL-"``) that the regex
   ``^[A-Z0-9.\\-]+$`` allows but that are never valid ticker symbols. They are
   now rejected with ``ValueError``.

2. ``fetch_market_context_batch`` accepted any value for ``max_workers`` and
   forwarded it to ``ThreadPoolExecutor``. A typo like ``max_workers=0`` (or
   negative, or a huge number) would either raise an obscure
   ``ValueError`` deep inside the executor or silently spawn thousands of
   threads. ``max_workers`` is now validated as an int in ``[1, 64]`` and
   rejected with a single ``INVALID`` entry carrying a ``data_error``.

3. ``_safe_float(True)`` returned ``1.0`` because ``bool`` is a subclass of
   ``int`` in Python. A bool sneaking into a price/market_cap field therefore
   produced a fake non-zero value instead of being treated as missing.
   ``_safe_float`` now returns ``0.0`` for any bool input.
"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _clean_data_cache():
    from augur import data as data_mod

    data_mod.clear_cache()
    data_mod._providers_cache = None
    yield
    data_mod.clear_cache()
    data_mod._providers_cache = None


# ---------------------------------------------------------------------------
# Gap #1: _normalize_ticker rejects leading/trailing '.' or '-'
# ---------------------------------------------------------------------------


class TestNormalizeTickerEdgePunctuation:
    """Tickers that pass the existing regex must still be rejected when they
    start or end with ``.`` or ``-`` (e.g. user typos from copy/paste)."""

    @pytest.mark.parametrize(
        "bad_ticker",
        [".AAPL", "AAPL.", "-AAPL", "AAPL-", ".", "-", "..AAPL", "AAPL-."],
    )
    def test_leading_or_trailing_punctuation_rejected(self, bad_ticker):
        from augur.data import _normalize_ticker

        # Note: some inputs (e.g. "..AAPL") are caught by an earlier rule
        # (consecutive dots) and raise a different ValueError message; we
        # only care that they are *rejected* with ValueError, not the exact
        # reason string.
        with pytest.raises(ValueError):
            _normalize_ticker(bad_ticker)

    def test_valid_tickers_with_internal_punctuation_still_accepted(self):
        from augur.data import _normalize_ticker

        # Sanity: real tickers like AAPL, BRK.B, 0700.HK, RDS-A must still work.
        assert _normalize_ticker("aapl") == "AAPL"
        assert _normalize_ticker("BRK.B") == "BRK.B"
        assert _normalize_ticker("0700.HK") == "0700.HK"
        assert _normalize_ticker("RDS-A") == "RDS-A"


# ---------------------------------------------------------------------------
# Gap #2: fetch_market_context_batch validates max_workers
# ---------------------------------------------------------------------------


class TestBatchMaxWorkersValidation:
    """``max_workers`` must be a positive int in a sane range; anything else
    is rejected with a single INVALID entry carrying a data_error, mirroring
    the existing non-list ``tickers`` UX."""

    @pytest.mark.parametrize("bad", [0, -1, -100, 65, 1000000, 1.5, None, "5"])
    def test_invalid_max_workers_returns_invalid_entry(self, bad):
        from augur.data import fetch_market_context_batch

        # Provide a valid tickers list so the failure is unambiguously about
        # max_workers, not tickers.
        result = fetch_market_context_batch(["AAPL"], max_workers=bad)
        assert list(result.keys()) == ["INVALID"]
        ctx = result["INVALID"]
        assert getattr(ctx, "data_source", None) == "error"
        assert "invalid max_workers" in getattr(ctx, "data_error", "")

    def test_bool_max_workers_rejected(self):
        """``True`` is an int in Python, but semantically it is not a worker
        count. ``isinstance(True, int)`` is True, so we need an explicit check."""
        from augur.data import fetch_market_context_batch

        result = fetch_market_context_batch(["AAPL"], max_workers=True)
        assert list(result.keys()) == ["INVALID"]
        assert "invalid max_workers" in result["INVALID"].data_error

    def test_valid_max_workers_proceeds(self, monkeypatch):
        """A correct max_workers must not trigger the validation path."""
        from augur.data import fetch_market_context_batch

        # Provide an empty list to avoid any provider call; we only need to
        # confirm the validation gate is passed (it returns {} for []).
        result = fetch_market_context_batch([], max_workers=4)
        assert result == {}


# ---------------------------------------------------------------------------
# Gap #3: _safe_float rejects bool
# ---------------------------------------------------------------------------


class TestSafeFloatRejectsBool:
    """``_safe_float(True)`` previously returned ``1.0`` because ``bool`` is
    an ``int`` subclass. It now returns ``0.0`` for any bool input."""

    @pytest.mark.parametrize("value", [True, False])
    def test_bool_returns_zero(self, value):
        from augur.data import _safe_float

        assert _safe_float(value) == 0.0

    def test_real_numeric_values_unchanged(self):
        from augur.data import _safe_float

        # Regression guard: the fix must not affect legitimate numeric inputs.
        assert _safe_float(3.14) == 3.14
        assert _safe_float(0) == 0.0
        assert _safe_float(42) == 42.0
        assert _safe_float("1.5") == 1.5
        assert _safe_float(None) == 0.0
        assert _safe_float(float("nan")) == 0.0
        assert _safe_float(float("inf")) == 0.0
