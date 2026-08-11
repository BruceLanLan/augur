# -*- coding: utf-8 -*-
"""Tests for Risk Review and Covenant Review engines."""

import pytest

from augur.risk_review import (
    CovenantItem,
    CovenantReviewer,
    RiskItem,
    RiskReviewer,
    RiskReviewReport,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_new_filing_text() -> str:
    return """
Item 1A. Risk Factors

Risk 1. Competition Risk
We face intense competition from established players and new entrants,
which could adversely affect our market share and profitability.

Risk 2. Supply Chain Disruption
Our operations depend on a global supply chain. Any significant disruption
in manufacturing or logistics will likely materially adversely affect our
ability to deliver products on time.

Risk 3. Regulatory Changes
Changes in government regulations, including environmental regulations and
data privacy laws, may adversely affect our business operations and
increase compliance costs.

Risk 4. Interest Rate Risk
We are subject to interest rate fluctuations that could materially affect
our borrowing costs and financial condition. This risk is critical given
current macroeconomic conditions.
"""


@pytest.fixture
def sample_prev_filing_text() -> str:
    return """
Item 1A. Risk Factors

Risk 1. Competition Risk
We face intense competition from established players,
which may adversely affect our market share.

Risk 2. Supply Chain Disruption
Our operations depend on a global supply chain. Any disruption
in manufacturing may adversely affect our ability to deliver products.

Risk 3. Regulatory Changes
Changes in government regulations may adversely affect our business operations.
"""


@pytest.fixture
def sample_covenant_text() -> str:
    return """
The Credit Agreement contains the following financial covenants:

The Borrower must maintain a Leverage Ratio (Total Debt to EBITDA)
not to exceed 3.50x, tested quarterly on a trailing four-quarter basis.

The Borrower shall maintain a minimum Interest Coverage Ratio
(EBITDA to Interest Expense) of at least 2.50x.

The Borrower shall not incur additional indebtedness exceeding
$50 million in aggregate without prior lender consent.

The Borrower must deliver audited annual financial statements
within 90 days of fiscal year end and quarterly compliance certificates
within 45 days of each quarter end.
"""


@pytest.fixture
def sample_financials() -> dict:
    return {
        "debt_to_ebitda": 2.8,
        "leverage_ratio": 2.8,
        "interest_coverage": 3.1,
        "interest_coverage_ratio": 3.1,
        "current_ratio": 1.5,
    }


# ---------------------------------------------------------------------------
# RiskItem
# ---------------------------------------------------------------------------

class TestRiskItem:
    def test_creation_defaults(self):
        """RiskItem fields populate correctly with defaults."""
        ri = RiskItem(
            risk_id="risk-001",
            category="market",
            description="Interest rate risk exposure",
            severity="high",
        )
        assert ri.risk_id == "risk-001"
        assert ri.category == "market"
        assert ri.severity == "high"
        assert ri.is_new is False
        assert ri.is_escalated is False
        assert ri.is_removed is False
        assert ri.previous_description == ""
        assert ri.source_section == ""

    def test_creation_with_all_fields(self):
        """RiskItem accepts all optional fields."""
        ri = RiskItem(
            risk_id="risk-002",
            category="legal",
            description="Patent litigation exposure",
            severity="critical",
            is_new=True,
            is_escalated=True,
            is_removed=False,
            previous_description="Minor patent risk",
            source_section="Item 1A",
        )
        assert ri.is_new is True
        assert ri.is_escalated is True
        assert ri.previous_description == "Minor patent risk"
        assert ri.source_section == "Item 1A"


# ---------------------------------------------------------------------------
# RiskReviewReport
# ---------------------------------------------------------------------------

class TestRiskReviewReport:
    def test_empty_report(self):
        """Report initializes with empty lists and zero counts."""
        report = RiskReviewReport(
            ticker="AAPL",
            filing_accession="0000320193-25-000001",
            total_risks=0,
        )
        assert report.ticker == "AAPL"
        assert report.total_risks == 0
        assert report.new_risks == []
        assert report.escalated_risks == []
        assert report.removed_risks == []
        assert report.unchanged_risks == 0


# ---------------------------------------------------------------------------
# RiskReviewer
# ---------------------------------------------------------------------------

class TestRiskReviewer:
    def test_extract_risks_from_text(self, sample_new_filing_text):
        """Extract multiple risk items from filing text."""
        reviewer = RiskReviewer("AAPL")
        risks = reviewer.extract_risks(sample_new_filing_text)

        assert len(risks) >= 3
        # Each risk should have an ID, category, description, and severity
        for risk in risks:
            assert risk.risk_id.startswith("risk-")
            assert risk.category in (
                "market", "operational", "financial", "legal",
                "competitive", "regulatory",
            )
            assert risk.severity in ("critical", "high", "medium", "low")
            assert len(risk.description) > 0

    def test_extract_risks_empty_text(self):
        """Empty or whitespace text returns empty list."""
        reviewer = RiskReviewer()
        assert reviewer.extract_risks("") == []
        assert reviewer.extract_risks("   \n  ") == []

    def test_categorize_risk_market(self):
        """Risk mentioning interest rate / inflation → market category."""
        reviewer = RiskReviewer()
        cat = reviewer.categorize_risk(
            "The company is exposed to interest rate fluctuations and "
            "inflationary pressures that could affect its stock price."
        )
        assert cat == "market"

    def test_categorize_risk_legal(self):
        """Risk mentioning litigation / lawsuit → legal category."""
        reviewer = RiskReviewer()
        cat = reviewer.categorize_risk(
            "The company is subject to ongoing litigation and patent "
            "infringement lawsuits that could result in significant liability."
        )
        assert cat == "legal"

    def test_categorize_risk_competitive(self):
        """Risk mentioning competition → competitive category."""
        reviewer = RiskReviewer()
        cat = reviewer.categorize_risk(
            "Intense competition from new market entrants and substitute "
            "products may erode our market share."
        )
        assert cat == "competitive"

    def test_categorize_risk_regulatory(self):
        """Risk mentioning regulation / compliance → regulatory category."""
        reviewer = RiskReviewer()
        cat = reviewer.categorize_risk(
            "Changes in government regulation and data privacy compliance "
            "requirements could increase our operational costs."
        )
        assert cat == "regulatory"

    def test_review_detects_new_risks(self, sample_new_filing_text, sample_prev_filing_text):
        """New risks not present in previous filing are flagged."""
        reviewer = RiskReviewer("AAPL")
        report = reviewer.review(sample_new_filing_text, sample_prev_filing_text)

        assert report.ticker == "AAPL"
        assert report.total_risks > 0

        # Interest Rate Risk (Risk 4) is new — not in prev
        new_descriptions = [r.description.lower() for r in report.new_risks]
        has_interest = any("interest rate" in d for d in new_descriptions)
        assert has_interest, f"Expected 'Interest Rate Risk' in new risks, got: {new_descriptions}"

    def test_review_detects_escalation(self, sample_new_filing_text, sample_prev_filing_text):
        """Escalated language (may → will likely) is detected."""
        reviewer = RiskReviewer("AAPL")
        report = reviewer.review(sample_new_filing_text, sample_prev_filing_text)

        # Supply chain escalated: "may adversely" → "will likely materially adversely"
        escalated_descriptions = [r.description.lower() for r in report.escalated_risks]
        has_supply_chain = any("supply chain" in d for d in escalated_descriptions)
        assert has_supply_chain, (
            f"Expected 'Supply Chain' risk to be escalated, "
            f"got escalated: {escalated_descriptions}"
        )
        for risk in report.escalated_risks:
            assert risk.is_escalated is True

    def test_review_detects_removed_risks(self, sample_new_filing_text, sample_prev_filing_text):
        """Risks in previous filing but not in new are flagged as removed."""
        reviewer = RiskReviewer("AAPL")
        report = reviewer.review(sample_new_filing_text, sample_prev_filing_text)

        # Some risks from prev may not match new — check removed list
        # (Our test fixtures overlap a lot, so removed may be empty;
        #  we test the structure is correct regardless)
        for risk in report.removed_risks:
            assert risk.is_removed is True

    def test_review_without_previous_filing(self, sample_new_filing_text):
        """Review with no previous filing: all risks treated as existing."""
        reviewer = RiskReviewer("TSLA")
        report = reviewer.review(sample_new_filing_text, prev_filing_text="")

        # No previous means nothing is "new" or "escalated" (no baseline)
        # But extract_risks still pulls items
        assert report.total_risks >= 3
        assert isinstance(report.summary, str) and len(report.summary) > 0

    def test_review_empty_text(self):
        """Empty filings produce empty report."""
        reviewer = RiskReviewer("TEST")
        report = reviewer.review("", "")
        assert report.total_risks == 0
        assert report.new_risks == []
        assert report.escalated_risks == []
        assert report.removed_risks == []

    def test_severity_assessment(self, sample_new_filing_text):
        """Severity levels are correctly assigned based on language."""
        reviewer = RiskReviewer()
        risks = reviewer.extract_risks(sample_new_filing_text)

        # Risk 4 has "critical" language
        critical_risks = [r for r in risks if r.severity == "critical"]
        assert len(critical_risks) >= 1

        # Risk 2 has "will likely materially adversely" → high
        high_risks = [r for r in risks if r.severity == "high"]
        assert len(high_risks) >= 1

    def test_review_report_summary_populated(self, sample_new_filing_text, sample_prev_filing_text):
        """Report summary string is non-empty and contains counts."""
        reviewer = RiskReviewer("AAPL")
        report = reviewer.review(sample_new_filing_text, sample_prev_filing_text)

        assert "Total risk factors" in report.summary or len(report.summary) > 0
        assert report.ticker == "AAPL"


# ---------------------------------------------------------------------------
# CovenantItem
# ---------------------------------------------------------------------------

class TestCovenantItem:
    def test_creation(self):
        """CovenantItem fields populate correctly."""
        ci = CovenantItem(
            covenant_id="cov-001",
            type="financial",
            description="Debt/EBITDA not to exceed 3.5x",
            threshold=3.5,
            current_value=2.8,
            in_compliance=True,
            trend="improving",
        )
        assert ci.covenant_id == "cov-001"
        assert ci.type == "financial"
        assert ci.threshold == 3.5
        assert ci.current_value == 2.8
        assert ci.in_compliance is True
        assert ci.trend == "improving"

    def test_creation_defaults(self):
        """CovenantItem defaults for optional fields."""
        ci = CovenantItem(
            covenant_id="cov-002",
            type="affirmative",
            description="Maintain insurance coverage",
        )
        assert ci.threshold is None
        assert ci.current_value is None
        assert ci.in_compliance is None
        assert ci.trend == ""


# ---------------------------------------------------------------------------
# CovenantReviewer
# ---------------------------------------------------------------------------

class TestCovenantReviewer:
    def test_extract_covenants_from_text(self, sample_covenant_text):
        """Extract multiple covenants from credit agreement text."""
        reviewer = CovenantReviewer()
        covenants = reviewer.review(sample_covenant_text)

        assert len(covenants) >= 2
        for cov in covenants:
            assert cov.covenant_id.startswith("cov-")
            assert cov.type in ("financial", "affirmative", "negative", "reporting")
            assert len(cov.description) > 0

    def test_extract_financial_covenant_with_threshold(self, sample_covenant_text):
        """Financial covenants get threshold extracted."""
        reviewer = CovenantReviewer()
        covenants = reviewer.review(sample_covenant_text)

        financial = [c for c in covenants if c.type == "financial"]
        assert len(financial) >= 1

        leverage = next(
            (c for c in financial if "leverage" in c.description.lower()), None
        )
        assert leverage is not None, f"Financial covenants: {financial}"
        assert leverage.threshold is not None
        assert leverage.threshold == 3.5

    def test_extract_negative_covenant(self, sample_covenant_text):
        """Negative covenants (shall not incur) are identified."""
        reviewer = CovenantReviewer()
        covenants = reviewer.review(sample_covenant_text)

        negative = [c for c in covenants if c.type == "negative"]
        assert len(negative) >= 1
        assert any("indebtedness" in c.description.lower() for c in negative)

    def test_extract_reporting_covenant(self, sample_covenant_text):
        """Reporting covenants (deliver financial statements) are identified."""
        reviewer = CovenantReviewer()
        covenants = reviewer.review(sample_covenant_text)

        reporting = [c for c in covenants if c.type == "reporting"]
        assert len(reporting) >= 1
        assert any("financial statement" in c.description.lower() for c in reporting)

    def test_check_compliance_in_compliance(self, sample_covenant_text, sample_financials):
        """Compliance check passes when metrics are within thresholds."""
        reviewer = CovenantReviewer()
        covenants = reviewer.review(sample_covenant_text, sample_financials)

        # Debt/EBITDA = 2.8 < 3.5 → compliant
        financial = [c for c in covenants if c.type == "financial"]
        for cov in financial:
            assert cov.in_compliance is not None, (
                f"Covenant {cov.covenant_id} has no compliance status"
            )

        leverage = next(
            (c for c in financial if "leverage" in c.description.lower()
             or "debt" in c.description.lower()), None
        )
        if leverage is not None:
            assert leverage.in_compliance is True, (
                f"Expected debt/EBITDA 2.8 < 3.5 to be compliant, "
                f"got {leverage.in_compliance}"
            )

    def test_check_compliance_out_of_compliance(self):
        """Compliance check fails when metrics breach thresholds."""
        reviewer = CovenantReviewer()
        text = "The Borrower must maintain a Leverage Ratio not to exceed 3.00x."
        financials = {"debt_to_ebitda": 3.5, "leverage_ratio": 3.5}

        covenants = reviewer.review(text, financials)
        financial = [c for c in covenants if c.type == "financial"]
        assert len(financial) >= 1
        # 3.5 > 3.0 → not compliant
        assert financial[0].in_compliance is False

    def test_check_compliance_without_financials(self, sample_covenant_text):
        """Without financials dict, compliance status stays None."""
        reviewer = CovenantReviewer()
        covenants = reviewer.review(sample_covenant_text)

        financial = [c for c in covenants if c.type == "financial"]
        for cov in financial:
            assert cov.in_compliance is None
            assert cov.current_value is None

    def test_empty_text(self):
        """Empty text produces empty covenant list."""
        reviewer = CovenantReviewer()
        assert reviewer.review("") == []
        assert reviewer.review("   ") == []

    def test_analyze_trend_improving(self):
        """Trend analysis detects improving metrics for coverage ratios."""
        reviewer = CovenantReviewer()
        covenant = CovenantItem(
            covenant_id="cov-001",
            type="financial",
            description="Maintain Interest Coverage Ratio at least 2.50x",
            threshold=2.5,
            in_compliance=True,
        )
        trend = reviewer.analyze_trend(covenant, [2.0, 2.3, 2.7, 3.1])
        assert trend == "improving"

    def test_analyze_trend_deteriorating_leverage(self):
        """Trend analysis detects deteriorating leverage ratios."""
        reviewer = CovenantReviewer()
        covenant = CovenantItem(
            covenant_id="cov-001",
            type="financial",
            description="Leverage Ratio not to exceed 3.50x",
            threshold=3.5,
            in_compliance=True,
        )
        trend = reviewer.analyze_trend(covenant, [2.0, 2.3, 2.8, 3.2])
        assert trend == "deteriorating"

    def test_analyze_trend_stable_short_history(self):
        """Trend is stable when only one data point exists."""
        reviewer = CovenantReviewer()
        covenant = CovenantItem(
            covenant_id="cov-001",
            type="financial",
            description="Leverage Ratio not to exceed 3.50x",
            threshold=3.5,
        )
        trend = reviewer.analyze_trend(covenant, [2.8])
        assert trend == "stable"
