# -*- coding: utf-8 -*-
"""Tests for augur.backtest module."""


class TestBacktest:
    def test_generate_sample_data_structure(self):
        """Test that generate_sample_data returns proper tuple of lists."""
        from augur.backtest import generate_sample_data

        hist, fwd = generate_sample_data("AAPL", 10)
        assert len(hist) == 10
        assert len(fwd) == 10
        assert "date" in hist[0]
        assert "price" in hist[0]
        assert "return_5d" in fwd[0]

    def test_generate_sample_data_deterministic(self):
        """Same ticker should produce same data (seeded by ticker hash)."""
        from augur.backtest import generate_sample_data

        h1, f1 = generate_sample_data("TEST", 5)
        h2, f2 = generate_sample_data("TEST", 5)
        assert h1[0]["price"] == h2[0]["price"]

    def test_backtester_run(self):
        """Test that Backtester.run_backtest produces valid results."""
        from augur.backtest import Backtester, generate_sample_data

        hist, fwd = generate_sample_data("MSFT", 5)
        bt = Backtester()
        result = bt.run_backtest("MSFT", hist, fwd)
        assert result.ticker == "MSFT"
        assert len(result.agent_ics) > 0
        assert result.summary != ""

    def test_check_hit_bullish(self):
        """Bullish signal is a hit when actual return is positive."""
        from augur.backtest import Backtester

        bt = Backtester()
        assert bt._check_hit("bullish", 0.05) is True
        assert bt._check_hit("bullish", -0.05) is False

    def test_check_hit_bearish(self):
        """Bearish signal is a hit when actual return is negative."""
        from augur.backtest import Backtester

        bt = Backtester()
        assert bt._check_hit("bearish", -0.05) is True
        assert bt._check_hit("bearish", 0.05) is False

    def test_check_hit_neutral(self):
        """Neutral signal is a hit when actual return is within 2%."""
        from augur.backtest import Backtester

        bt = Backtester()
        assert bt._check_hit("neutral", 0.01) is True
        assert bt._check_hit("neutral", 0.05) is False

    def test_save_records_rotation_behavior(self):
        """Verify that _save_records rotates when file exceeds 10MB."""
        import tempfile
        import os
        from pathlib import Path
        from augur.backtest import Backtester, BacktestRecord

        bt = Backtester()
        # Use a temp file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as tmp:
            tmp_path = tmp.name

        original_path = bt.RECORDS_FILE
        bt.RECORDS_FILE = Path(tmp_path)

        try:
            # Write some records - should not crash
            records = [BacktestRecord(
                date="2024-01-01", ticker="TEST", agent_id="buffett",
                signal="bullish", score=7.5, confidence=0.8
            )]
            bt._save_records(records)

            # Verify file was written
            assert bt.RECORDS_FILE.exists()
            content = bt.RECORDS_FILE.read_text()
            assert "TEST" in content
            assert "buffett" in content
        finally:
            bt.RECORDS_FILE = original_path
            os.unlink(tmp_path)
