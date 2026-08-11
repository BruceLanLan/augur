# -*- coding: utf-8 -*-
"""Tests for ResearchInbox."""

import pytest

from augur.research_inbox import InboxItem, ResearchInbox


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def inbox(tmp_path):
    """Return a fresh ResearchInbox in a per-test temp directory."""
    return ResearchInbox(data_dir=tmp_path)


@pytest.fixture
def earnings_item():
    return InboxItem(
        item_id="ib_earn001",
        item_type="earnings_event",
        ticker="AAPL",
        title="AAPL Q4 2025 Earnings",
        description="Upcoming earnings for AAPL (Q4 2025) on 2025-11-01",
        priority="high",
        created_at="2025-10-25T10:00:00",
    )


@pytest.fixture
def filing_delta_item():
    return InboxItem(
        item_id="ib_fd001",
        item_type="filing_delta",
        ticker="MSFT",
        title="MSFT Filing Delta: significant_changes",
        description="Material changes detected in MSFT filing",
        priority="high",
        created_at="2025-10-26T10:00:00",
    )


@pytest.fixture
def low_priority_item():
    return InboxItem(
        item_id="ib_low001",
        item_type="thesis_review",
        ticker="TSLA",
        title="TSLA Thesis Review",
        description="Thesis review for TSLA",
        priority="low",
        created_at="2025-10-24T10:00:00",
    )


# ---------------------------------------------------------------------------
# InboxItem
# ---------------------------------------------------------------------------

class TestInboxItem:
    def test_creation(self):
        item = InboxItem(
            item_id="ib_test001",
            item_type="earnings_event",
            ticker="AAPL",
            title="Test Title",
            description="Test description",
            priority="high",
            created_at="2025-10-25T10:00:00",
        )
        assert item.item_id == "ib_test001"
        assert item.item_type == "earnings_event"
        assert item.ticker == "AAPL"
        assert item.priority == "high"
        assert item.dismissed is False
        assert item.action_link == ""

    def test_defaults(self):
        item = InboxItem(
            item_id="x",
            item_type="risk_alert",
            ticker="TEST",
            title="T",
            description="D",
            priority="low",
            created_at="2025-01-01T00:00:00",
        )
        assert item.dismissed is False
        assert item.action_link == ""

    def test_dismissed_field(self):
        item = InboxItem(
            item_id="x", item_type="earnings_event", ticker="T",
            title="T", description="D", priority="high",
            created_at="2025-01-01T00:00:00", dismissed=True,
        )
        assert item.dismissed is True


# ---------------------------------------------------------------------------
# ResearchInbox — add / list / dismiss / count_unread
# ---------------------------------------------------------------------------

class TestResearchInboxAddList:
    def test_add_and_list(self, inbox, earnings_item):
        inbox.add(earnings_item)
        items = inbox.list()
        assert len(items) == 1
        assert items[0].item_id == "ib_earn001"

    def test_list_filter_by_ticker(self, inbox, earnings_item, filing_delta_item):
        inbox.add(earnings_item)      # AAPL
        inbox.add(filing_delta_item)  # MSFT
        aapl_items = inbox.list(ticker="AAPL")
        assert len(aapl_items) == 1
        assert aapl_items[0].ticker == "AAPL"

    def test_list_filter_by_priority(self, inbox, earnings_item, low_priority_item):
        inbox.add(earnings_item)      # high
        inbox.add(low_priority_item)  # low
        high_items = inbox.list(priority="high")
        assert len(high_items) == 1
        assert high_items[0].priority == "high"

    def test_list_sort_order(self, inbox, earnings_item, low_priority_item, filing_delta_item):
        # Add in mixed order
        inbox.add(low_priority_item)    # low, 2025-10-24
        inbox.add(earnings_item)        # high, 2025-10-25
        inbox.add(filing_delta_item)    # high, 2025-10-26
        items = inbox.list()
        # high priority first, within high newest first
        assert items[0].priority == "high"
        # filing_delta_item has newer created_at than earnings_item
        assert items[0].item_id == "ib_fd001"  # 2025-10-26
        assert items[1].item_id == "ib_earn001"  # 2025-10-25
        assert items[2].priority == "low"

    def test_dismiss(self, inbox, earnings_item, filing_delta_item):
        inbox.add(earnings_item)
        inbox.add(filing_delta_item)
        assert inbox.count_unread() == 2

        inbox.dismiss("ib_earn001")
        assert inbox.count_unread() == 1

        items = inbox.list()
        assert len(items) == 1
        assert items[0].item_id == "ib_fd001"

    def test_count_unread(self, inbox, earnings_item, filing_delta_item, low_priority_item):
        assert inbox.count_unread() == 0
        inbox.add(earnings_item)
        inbox.add(filing_delta_item)
        inbox.add(low_priority_item)
        assert inbox.count_unread() == 3
        inbox.dismiss("ib_fd001")
        assert inbox.count_unread() == 2

    def test_list_limit(self, inbox, earnings_item, filing_delta_item, low_priority_item):
        inbox.add(earnings_item)
        inbox.add(filing_delta_item)
        inbox.add(low_priority_item)
        items = inbox.list(limit=2)
        assert len(items) == 2

    def test_auto_generate_id(self, inbox):
        item = InboxItem(
            item_id="",  # empty → auto-generated
            item_type="risk_alert",
            ticker="TSLA",
            title="Risk Alert",
            description="Something happened",
            priority="high",
            created_at="2025-10-27T10:00:00",
        )
        generated_id = inbox.add(item)
        assert generated_id.startswith("ib_")
        assert len(generated_id) == 11  # ib_ + 8 hex

        items = inbox.list()
        assert len(items) == 1
        assert items[0].item_id == generated_id


# ---------------------------------------------------------------------------
# ResearchInbox — generate_from_events
# ---------------------------------------------------------------------------

class TestResearchInboxGenerateFromEvents:
    def test_generates_earnings_event_items(self, inbox):
        class MockEarningsEvent:
            ticker = "AAPL"
            event_date = "2025-11-01"
            fiscal_period = "Q4 2025"

        new_items = inbox.generate_from_events(
            earnings_events=[MockEarningsEvent()],
        )
        assert len(new_items) == 1
        assert new_items[0].item_type == "earnings_event"
        assert new_items[0].ticker == "AAPL"
        assert new_items[0].priority == "high"
        assert new_items[0].item_id.startswith("ib_")

    def test_generates_filing_delta_items(self, inbox):
        class MockFilingDelta:
            ticker = "MSFT"
            overall_assessment = "significant_changes"
            new_accession = "acc_123"

        new_items = inbox.generate_from_events(
            filing_deltas=[MockFilingDelta()],
        )
        assert len(new_items) == 1
        assert new_items[0].item_type == "filing_delta"
        assert new_items[0].priority == "high"

    def test_generates_thesis_review_items(self, inbox):
        class MockThesisReview:
            ticker = "TSLA"
            status = "needs_review"

        new_items = inbox.generate_from_events(
            thesis_reviews=[MockThesisReview()],
        )
        assert len(new_items) == 1
        assert new_items[0].item_type == "thesis_review"
        assert new_items[0].priority == "medium"

    def test_no_duplicates_on_second_call(self, inbox):
        class MockEarningsEvent:
            ticker = "AAPL"
            event_date = "2025-11-01"
            fiscal_period = "Q4 2025"

        first = inbox.generate_from_events(
            earnings_events=[MockEarningsEvent()],
        )
        assert len(first) == 1
        assert inbox.count_unread() == 1

        second = inbox.generate_from_events(
            earnings_events=[MockEarningsEvent()],
        )
        assert len(second) == 0
        assert inbox.count_unread() == 1

    def test_multiple_event_types(self, inbox):
        class MockEarningsEvent:
            ticker = "AAPL"
            event_date = "2025-11-01"
            fiscal_period = "Q4 2025"

        class MockFilingDelta:
            ticker = "MSFT"
            overall_assessment = "minor_changes"
            new_accession = "acc_456"

        class MockThesisReview:
            ticker = "TSLA"
            status = "pending"

        new_items = inbox.generate_from_events(
            earnings_events=[MockEarningsEvent()],
            filing_deltas=[MockFilingDelta()],
            thesis_reviews=[MockThesisReview()],
        )
        assert len(new_items) == 3
        types = {it.item_type for it in new_items}
        assert types == {"earnings_event", "filing_delta", "thesis_review"}
        assert inbox.count_unread() == 3

    def test_filing_delta_priority_mapping(self, inbox):
        class MockFilingDeltaHigh:
            ticker = "A"
            overall_assessment = "significant_changes"
            new_accession = "a1"

        class MockFilingDeltaMed:
            ticker = "B"
            overall_assessment = "minor_changes"
            new_accession = "b1"

        class MockFilingDeltaLow:
            ticker = "C"
            overall_assessment = "no_material_changes"
            new_accession = "c1"

        items = inbox.generate_from_events(
            filing_deltas=[
                MockFilingDeltaMed(),
                MockFilingDeltaLow(),
                MockFilingDeltaHigh(),
            ],
        )
        priorities = {it.priority for it in items}
        assert priorities == {"high", "medium", "low"}
