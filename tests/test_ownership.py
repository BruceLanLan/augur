# -*- coding: utf-8 -*-
"""Tests for augur.ownership (C05 Insider Cluster Review + C06 Institutional Ownership Delta)."""

import pytest

from augur.ownership import (
    InsiderAnalyzer,
    InsiderCluster,
    InsiderTrade,
    InstitutionPosition,
    OwnershipAnalyzer,
    OwnershipDelta,
)


# ============================================================================
# C05 — Insider Cluster Review
# ============================================================================


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_buys() -> list:
    """Two distinct insiders buying the same ticker — a cluster."""
    return [
        InsiderTrade(
            ticker="AAPL", person="Tim Cook", role="CEO",
            transaction_date="2025-06-15", type="buy",
            shares=10000, price=185.0, value=1_850_000.0,
        ),
        InsiderTrade(
            ticker="AAPL", person="Luca Maestri", role="CFO",
            transaction_date="2025-06-18", type="buy",
            shares=5000, price=186.0, value=930_000.0,
        ),
    ]


@pytest.fixture
def sample_sells() -> list:
    """Two distinct insiders selling the same ticker — a cluster."""
    return [
        InsiderTrade(
            ticker="AAPL", person="Tim Cook", role="CEO",
            transaction_date="2025-06-15", type="sell",
            shares=10000, price=185.0, value=1_850_000.0,
        ),
        InsiderTrade(
            ticker="AAPL", person="Jeff Williams", role="COO",
            transaction_date="2025-06-18", type="sell",
            shares=8000, price=186.0, value=1_488_000.0,
        ),
    ]


@pytest.fixture
def sample_mixed() -> list:
    """Cluster buying AND cluster selling — mixed assessment."""
    return [
        InsiderTrade(
            ticker="MSFT", person="Satya Nadella", role="CEO",
            transaction_date="2025-06-10", type="buy",
            shares=5000, price=420.0, value=2_100_000.0,
        ),
        InsiderTrade(
            ticker="MSFT", person="Amy Hood", role="CFO",
            transaction_date="2025-06-12", type="buy",
            shares=3000, price=422.0, value=1_266_000.0,
        ),
        InsiderTrade(
            ticker="MSFT", person="Brad Smith", role="President",
            transaction_date="2025-06-14", type="sell",
            shares=4000, price=421.0, value=1_684_000.0,
        ),
        InsiderTrade(
            ticker="MSFT", person="Judson Althoff", role="EVP",
            transaction_date="2025-06-16", type="sell",
            shares=2000, price=423.0, value=846_000.0,
        ),
    ]


@pytest.fixture
def single_trader() -> list:
    """A single insider trading — no cluster."""
    return [
        InsiderTrade(
            ticker="GOOGL", person="Sundar Pichai", role="CEO",
            transaction_date="2025-07-01", type="buy",
            shares=2000, price=175.0, value=350_000.0,
        ),
    ]


# ---------------------------------------------------------------------------
# InsiderTrade
# ---------------------------------------------------------------------------

class TestInsiderTrade:
    def test_creation(self):
        trade = InsiderTrade(
            ticker="AAPL", person="Tim Cook", role="CEO",
            transaction_date="2025-06-15", type="buy",
            shares=10000, price=185.0, value=1_850_000.0,
        )
        assert trade.ticker == "AAPL"
        assert trade.person == "Tim Cook"
        assert trade.type == "buy"
        assert trade.shares == 10000
        assert trade.value == 1_850_000.0

    def test_sell_trade(self):
        trade = InsiderTrade(
            ticker="NVDA", person="Jensen Huang", role="CEO",
            transaction_date="2025-07-20", type="sell",
            shares=5000, price=800.0, value=4_000_000.0,
        )
        assert trade.type == "sell"
        assert trade.value == 4_000_000.0


# ---------------------------------------------------------------------------
# InsiderCluster
# ---------------------------------------------------------------------------

class TestInsiderCluster:
    def test_creation_defaults(self):
        cluster = InsiderCluster(
            ticker="AAPL", period_days=90,
            total_buys=2, total_sells=0,
            net_value=2_780_000.0,
        )
        assert cluster.ticker == "AAPL"
        assert cluster.period_days == 90
        assert cluster.total_buys == 2
        assert cluster.total_sells == 0
        assert cluster.assessment == "no_activity"  # default
        assert cluster.participants == []

    def test_creation_cluster_buying(self):
        cluster = InsiderCluster(
            ticker="AAPL", period_days=90,
            total_buys=2, total_sells=0,
            net_value=2_780_000.0,
            participants=["Luca Maestri", "Tim Cook"],
            assessment="cluster_buying",
        )
        assert cluster.assessment == "cluster_buying"
        assert len(cluster.participants) == 2


# ---------------------------------------------------------------------------
# InsiderAnalyzer.detect_clusters
# ---------------------------------------------------------------------------

class TestInsiderAnalyzerDetectClusters:
    def test_cluster_buying(self, sample_buys):
        analyzer = InsiderAnalyzer()
        cluster = analyzer.detect_clusters(sample_buys)
        assert cluster.ticker == "AAPL"
        assert cluster.total_buys == 2
        assert cluster.total_sells == 0
        assert cluster.net_value > 0
        assert cluster.assessment == "cluster_buying"
        assert len(cluster.participants) == 2

    def test_cluster_selling(self, sample_sells):
        analyzer = InsiderAnalyzer()
        cluster = analyzer.detect_clusters(sample_sells)
        assert cluster.ticker == "AAPL"
        assert cluster.total_buys == 0
        assert cluster.total_sells == 2
        assert cluster.net_value < 0
        assert cluster.assessment == "cluster_selling"

    def test_mixed(self, sample_mixed):
        analyzer = InsiderAnalyzer()
        cluster = analyzer.detect_clusters(sample_mixed)
        assert cluster.ticker == "MSFT"
        assert cluster.total_buys == 2
        assert cluster.total_sells == 2
        assert cluster.assessment == "mixed"

    def test_no_activity_single_trader(self, single_trader):
        analyzer = InsiderAnalyzer()
        cluster = analyzer.detect_clusters(single_trader)
        assert cluster.assessment == "no_activity"
        assert cluster.total_buys == 1
        assert cluster.total_sells == 0

    def test_empty_trades(self):
        analyzer = InsiderAnalyzer()
        cluster = analyzer.detect_clusters([])
        assert cluster.ticker == ""
        assert cluster.assessment == "no_activity"
        assert cluster.net_value == 0.0

    def test_window_days_preserved(self, sample_buys):
        analyzer = InsiderAnalyzer()
        cluster = analyzer.detect_clusters(sample_buys, window_days=30)
        assert cluster.period_days == 30


# ---------------------------------------------------------------------------
# InsiderAnalyzer.compute_sentiment
# ---------------------------------------------------------------------------

class TestInsiderAnalyzerComputeSentiment:
    def test_all_buys(self, sample_buys):
        analyzer = InsiderAnalyzer()
        sentiment = analyzer.compute_sentiment(sample_buys)
        assert sentiment == pytest.approx(1.0, abs=0.01)

    def test_all_sells(self, sample_sells):
        analyzer = InsiderAnalyzer()
        sentiment = analyzer.compute_sentiment(sample_sells)
        assert sentiment == pytest.approx(-1.0, abs=0.01)

    def test_mixed_sentiment(self, sample_mixed):
        analyzer = InsiderAnalyzer()
        sentiment = analyzer.compute_sentiment(sample_mixed)
        # buys: 2_100_000 + 1_266_000 = 3_366_000
        # sells: 1_684_000 + 846_000 = 2_530_000
        # net = 836_000, total = 5_896_000
        # sentiment = 836_000 / 5_896_000 ≈ 0.1418
        assert 0.0 < sentiment < 0.5

    def test_empty_sentiment(self):
        analyzer = InsiderAnalyzer()
        sentiment = analyzer.compute_sentiment([])
        assert sentiment == 0.0

    def test_clamped_to_range(self):
        """Ensure sentiment never exceeds [-1.0, 1.0]."""
        analyzer = InsiderAnalyzer()
        trades = [
            InsiderTrade(
                ticker="TSLA", person="Elon Musk", role="CEO",
                transaction_date="2025-01-01", type="buy",
                shares=1, price=1.0, value=1.0,
            ),
            InsiderTrade(
                ticker="TSLA", person="Robyn Denholm", role="Chair",
                transaction_date="2025-01-01", type="sell",
                shares=1, price=1.0, value=1e9,  # extreme sell
            ),
        ]
        sentiment = analyzer.compute_sentiment(trades)
        assert -1.0 <= sentiment <= 1.0


# ============================================================================
# C06 — Institutional Ownership Delta
# ============================================================================


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def prev_positions() -> list:
    return [
        InstitutionPosition(
            institution="Berkshire Hathaway", ticker="AAPL",
            shares=905_000_000, value=170_000_000_000, pct_of_portfolio=45.0,
            filing_date="2025-05-15", quarter_end="2025-03-31",
        ),
        InstitutionPosition(
            institution="Renaissance Technologies", ticker="AAPL",
            shares=5_000_000, value=940_000_000, pct_of_portfolio=1.2,
            filing_date="2025-05-15", quarter_end="2025-03-31",
        ),
        InstitutionPosition(
            institution="Bridgewater Associates", ticker="AAPL",
            shares=2_000_000, value=376_000_000, pct_of_portfolio=0.8,
            filing_date="2025-05-14", quarter_end="2025-03-31",
        ),
        # This one will be exited
        InstitutionPosition(
            institution="Scion Asset Management", ticker="AAPL",
            shares=500_000, value=94_000_000, pct_of_portfolio=3.5,
            filing_date="2025-05-15", quarter_end="2025-03-31",
        ),
    ]


@pytest.fixture
def curr_positions() -> list:
    return [
        InstitutionPosition(
            institution="Berkshire Hathaway", ticker="AAPL",
            shares=800_000_000, value=148_000_000_000, pct_of_portfolio=42.0,
            filing_date="2025-08-15", quarter_end="2025-06-30",
        ),
        InstitutionPosition(
            institution="Renaissance Technologies", ticker="AAPL",
            shares=5_500_000, value=1_020_000_000, pct_of_portfolio=1.4,
            filing_date="2025-08-15", quarter_end="2025-06-30",
        ),
        InstitutionPosition(
            institution="Bridgewater Associates", ticker="AAPL",
            shares=1_800_000, value=334_000_000, pct_of_portfolio=0.7,
            filing_date="2025-08-14", quarter_end="2025-06-30",
        ),
        # New position
        InstitutionPosition(
            institution="Pershing Square", ticker="AAPL",
            shares=3_000_000, value=556_000_000, pct_of_portfolio=5.0,
            filing_date="2025-08-15", quarter_end="2025-06-30",
        ),
    ]


# ---------------------------------------------------------------------------
# InstitutionPosition
# ---------------------------------------------------------------------------

class TestInstitutionPosition:
    def test_creation(self):
        pos = InstitutionPosition(
            institution="Berkshire Hathaway", ticker="AAPL",
            shares=905_000_000, value=170_000_000_000, pct_of_portfolio=45.0,
            filing_date="2025-05-15", quarter_end="2025-03-31",
        )
        assert pos.institution == "Berkshire Hathaway"
        assert pos.ticker == "AAPL"
        assert pos.shares == 905_000_000
        assert pos.quarter_end == "2025-03-31"


# ---------------------------------------------------------------------------
# OwnershipDelta
# ---------------------------------------------------------------------------

class TestOwnershipDelta:
    def test_creation(self):
        delta = OwnershipDelta(
            ticker="AAPL",
            previous_quarter="2025-03-31",
            current_quarter="2025-06-30",
            net_institutional_flow=-100_000_000.0,
        )
        assert delta.ticker == "AAPL"
        assert delta.previous_quarter == "2025-03-31"
        assert delta.current_quarter == "2025-06-30"
        assert delta.net_institutional_flow == -100_000_000.0
        assert delta.new_positions == []
        assert delta.exited_positions == []


# ---------------------------------------------------------------------------
# OwnershipAnalyzer.compare
# ---------------------------------------------------------------------------

class TestOwnershipAnalyzerCompare:
    def test_new_positions_detected(self, prev_positions, curr_positions):
        analyzer = OwnershipAnalyzer()
        delta = analyzer.compare(prev_positions, curr_positions)
        assert len(delta.new_positions) == 1
        assert delta.new_positions[0].institution == "Pershing Square"

    def test_exited_positions_detected(self, prev_positions, curr_positions):
        analyzer = OwnershipAnalyzer()
        delta = analyzer.compare(prev_positions, curr_positions)
        assert len(delta.exited_positions) == 1
        assert delta.exited_positions[0].institution == "Scion Asset Management"

    def test_increased_positions_detected(self, prev_positions, curr_positions):
        analyzer = OwnershipAnalyzer()
        delta = analyzer.compare(prev_positions, curr_positions)
        # Renaissance: 5_000_000 -> 5_500_000, +10 %
        assert len(delta.increased_positions) == 1
        assert delta.increased_positions[0]["institution"] == "Renaissance Technologies"
        assert delta.increased_positions[0]["change_pct"] == pytest.approx(10.0)

    def test_decreased_positions_detected(self, prev_positions, curr_positions):
        analyzer = OwnershipAnalyzer()
        delta = analyzer.compare(prev_positions, curr_positions)
        # Berkshire: 905_000_000 -> 800_000_000, -11.60 %
        # Bridgewater: 2_000_000 -> 1_800_000, -10.00 %
        assert len(delta.decreased_positions) >= 1
        berk = next(
            d for d in delta.decreased_positions
            if d["institution"] == "Berkshire Hathaway"
        )
        assert berk["change_pct"] < -5.0

    def test_net_institutional_flow(self, prev_positions, curr_positions):
        analyzer = OwnershipAnalyzer()
        delta = analyzer.compare(prev_positions, curr_positions)
        # Common positions: Berk -105M, Ren +500K, Bridge -200K = -104.7M
        # New: Pershing +3M, Exited: Scion -500K → net ≈ -102.2M
        assert delta.net_institutional_flow < 0  # net selling

    def test_empty_inputs(self):
        analyzer = OwnershipAnalyzer()
        delta = analyzer.compare([], [])
        assert delta.ticker == ""
        assert delta.net_institutional_flow == 0.0
        assert delta.new_positions == []
        assert delta.exited_positions == []

    def test_quarter_labels_inferred(self, prev_positions, curr_positions):
        analyzer = OwnershipAnalyzer()
        delta = analyzer.compare(prev_positions, curr_positions)
        assert delta.previous_quarter == "2025-03-31"
        assert delta.current_quarter == "2025-06-30"

    def test_no_change_below_threshold(self):
        """Institutions with tiny share changes should not appear in
        increased/decreased lists."""
        prev = [
            InstitutionPosition(
                institution="Test Fund", ticker="XYZ",
                shares=100_000, value=10_000_000, pct_of_portfolio=1.0,
                filing_date="2025-05-15", quarter_end="2025-03-31",
            ),
        ]
        curr = [
            InstitutionPosition(
                institution="Test Fund", ticker="XYZ",
                shares=100_001, value=10_000_100, pct_of_portfolio=1.0,
                filing_date="2025-08-15", quarter_end="2025-06-30",
            ),
        ]
        analyzer = OwnershipAnalyzer()
        delta = analyzer.compare(prev, curr)
        # 1 extra share out of 100_000 = 0.001% → below threshold
        assert delta.increased_positions == []
        assert delta.decreased_positions == []


# ---------------------------------------------------------------------------
# OwnershipAnalyzer.top_holders
# ---------------------------------------------------------------------------

class TestOwnershipAnalyzerTopHolders:
    def test_returns_top_n(self, prev_positions):
        analyzer = OwnershipAnalyzer()
        top = analyzer.top_holders(prev_positions, limit=2)
        assert len(top) == 2
        assert top[0].institution == "Berkshire Hathaway"  # 905M shares
        assert top[1].institution == "Renaissance Technologies"  # 5M shares

    def test_respects_limit(self, prev_positions):
        analyzer = OwnershipAnalyzer()
        top = analyzer.top_holders(prev_positions, limit=1)
        assert len(top) == 1
        assert top[0].shares == 905_000_000

    def test_limit_exceeds_list_size(self, prev_positions):
        analyzer = OwnershipAnalyzer()
        top = analyzer.top_holders(prev_positions, limit=50)
        assert len(top) == len(prev_positions)  # all returned


class TestFetchInsiderTrades:
    def test_maps_form4_rows_and_passes_as_of_date(self, monkeypatch):
        import augur.consensus.edgar_insider as edgar_insider
        from augur.ownership import fetch_insider_trades

        calls = []

        def fake(ticker, as_of_date):
            calls.append((ticker, as_of_date))
            return [
                {"reporting_owner_cik": "0001", "transaction_date": "2026-09-01", "code": "P", "shares": 10, "price": 5.0},
                {"reporting_owner_cik": "0002", "transaction_date": "2026-09-02", "code": "S", "shares": None, "price": 7.0},
            ]

        monkeypatch.setattr(edgar_insider, "_fetch_form4_transactions", fake)
        trades = fetch_insider_trades("aapl", "2026-09-10")
        assert calls == [("AAPL", "2026-09-10")]
        assert [(t.ticker, t.person, t.type, t.value) for t in trades] == [
            ("AAPL", "0001", "buy", 50.0),
            ("AAPL", "0002", "sell", 0.0),
        ]
