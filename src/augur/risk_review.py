# -*- coding: utf-8 -*-
"""
Risk Review — structured risk-factor review and covenant compliance analysis.

Identifies new, removed, and escalated risk factors between consecutive
SEC filings, and evaluates covenant compliance against financial data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Risk Review Models
# ---------------------------------------------------------------------------

@dataclass
class RiskItem:
    """A single risk factor extracted from a filing."""

    risk_id: str
    category: str           # "market" | "operational" | "financial" | "legal" | "competitive" | "regulatory"
    description: str
    severity: str           # "critical" | "high" | "medium" | "low"
    is_new: bool = False
    is_escalated: bool = False  # 措辞升级 (e.g. "may" → "will likely")
    is_removed: bool = False
    previous_description: str = ""
    source_section: str = ""    # "Item 1A", etc.


@dataclass
class RiskReviewReport:
    """Complete risk-factor review report comparing two filings."""

    ticker: str
    filing_accession: str
    total_risks: int
    new_risks: List[RiskItem] = field(default_factory=list)
    escalated_risks: List[RiskItem] = field(default_factory=list)
    removed_risks: List[RiskItem] = field(default_factory=list)
    unchanged_risks: int = 0
    critical_risks: List[RiskItem] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Risk Reviewer
# ---------------------------------------------------------------------------

class RiskReviewer:
    """Review and compare risk factors between SEC filings.

    Extracts risk items from filing text, categorizes them, and compares
    against a previous filing to identify new, removed, and escalated risks.
    """

    # Severity keywords ordered from most to least severe
    _SEVERITY_PATTERNS = [
        (re.compile(r'\b(critical|severe|could\s+materially\s+adversely|existential|catastrophic)\b', re.IGNORECASE), "critical"),
        (re.compile(r'\b(significant(?:ly)?\s+adversely|substantial\s+adverse|serious|major|material(?:ly)?\s+adversely)\b', re.IGNORECASE), "high"),
        (re.compile(r'\b(could\s+adversely|may\s+adversely|might\s+adversely|moderate)\b', re.IGNORECASE), "medium"),
    ]

    # Escalation keyword pairs: tentative → definite
    _ESCALATION_PAIRS = [
        ("may", "will"),
        ("might", "will"),
        ("could", "likely"),
        ("possible", "probable"),
        ("uncertain", "expected"),
        ("potential", "anticipated"),
        ("may adversely", "will adversely"),
        ("could adversely", "will likely adversely"),
        ("could", "is expected to"),
        ("subject to", "exposed to"),
    ]

    # Category keyword mappings
    _CATEGORY_KEYWORDS = {
        "market": [
            "market condition", "interest rate", "inflation", "recession",
            "commodity price", "currency exchange", "stock price",
            "market volatility", "economic downturn", "economic condition",
            "demand fluctuation", "pricing pressure", "market disruption",
        ],
        "operational": [
            "supply chain", "manufacturing", "production", "logistics",
            "information technology", "cybersecurity", "system failure",
            "data breach", "business continuity", "key personnel",
            "labor", "workforce", "retention", "outsourcing",
            "infrastructure", "capacity constraint", "quality control",
        ],
        "financial": [
            "liquidity", "credit", "debt", "leverage", "cash flow",
            "impairment", "write-down", "goodwill", "tax rate",
            "capital requirement", "financing", "refinancing",
            "credit rating", "counterparty", "default",
            "pension", "hedging", "derivative",
        ],
        "legal": [
            "litigation", "lawsuit", "litigate", "legal proceeding",
            "intellectual property", "patent", "trademark", "copyright",
            "contractual dispute", "indemnification", "liability",
            "settlement", "arbitration", "class action",
        ],
        "competitive": [
            "competition", "competitor", "competitive pressure",
            "market share", "industry consolidation", "disruptive technology",
            "new entrant", "substitute product", "pricing competition",
            "competitive advantage", "barriers to entry",
        ],
        "regulatory": [
            "regulation", "regulatory", "compliance", "government",
            "legislation", "policy change", "trade restriction",
            "tariff", "export control", "antitrust", "environmental regulation",
            "data privacy", "gdpr", "sec", "fda", "epa",
            "licensing", "permit", "sanction", "anti-corruption",
        ],
    }

    def __init__(self, ticker: str = ""):
        self._ticker = ticker.upper()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(
        self,
        new_filing_text: str,
        prev_filing_text: str = "",
        filing_accession: str = "",
        source_section: str = "Item 1A",
    ) -> RiskReviewReport:
        """Compare risk factors between two filings and produce a review report.

        Args:
            new_filing_text: Full text (or risk-factor section) of the newer filing.
            prev_filing_text: Full text (or risk-factor section) of the older filing.
            filing_accession: SEC accession number for the new filing.
            source_section: Section identifier (e.g. "Item 1A").

        Returns:
            A RiskReviewReport summarizing all changes.
        """
        new_risks = self.extract_risks(new_filing_text)
        prev_risks = self.extract_risks(prev_filing_text) if prev_filing_text else []

        # Index previous risks by (normalised) description for matching
        prev_index = self._index_risks(prev_risks)

        classified: List[RiskItem] = []
        new_risk_items: List[RiskItem] = []
        escalated: List[RiskItem] = []
        removed: List[RiskItem] = []

        matched_prev_ids = set()

        for risk in new_risks:
            match = self._find_match(risk, prev_index)
            if match is None:
                # No match in previous filing → new risk
                risk.is_new = True
                new_risk_items.append(risk)
                classified.append(risk)
            else:
                matched_prev_ids.add(match.risk_id)
                # Check for escalation
                risk.previous_description = match.description
                if self._is_escalated(risk.description, match.description):
                    risk.is_escalated = True
                    escalated.append(risk)
                classified.append(risk)

        # Risks in previous filing but not in new → removed
        for prev_risk in prev_risks:
            if prev_risk.risk_id not in matched_prev_ids:
                prev_risk.is_removed = True
                removed.append(prev_risk)

        unchanged = len(classified) - len(new_risk_items) - len(escalated)

        # Critical risks
        critical = [r for r in classified if r.severity == "critical"]

        report = RiskReviewReport(
            ticker=self._ticker,
            filing_accession=filing_accession,
            total_risks=len(classified),
            new_risks=new_risk_items,
            escalated_risks=escalated,
            removed_risks=removed,
            unchanged_risks=max(unchanged, 0),
            critical_risks=critical,
            summary=self._build_summary(
                len(classified), len(new_risk_items), len(escalated),
                len(removed), len(critical),
            ),
        )
        return report

    def extract_risks(self, filing_text: str) -> List[RiskItem]:
        """Extract risk items from a filing text.

        Splits the risk-factor section into individual risk paragraphs,
        then categorizes and scores each one.

        Args:
            filing_text: Raw filing text or risk-factor section.

        Returns:
            List of RiskItem objects extracted from the text.
        """
        if not filing_text or not filing_text.strip():
            return []

        # Split into risk paragraphs using common section delimiters
        paragraphs = self._split_into_risks(filing_text)
        risks: List[RiskItem] = []

        for i, para in enumerate(paragraphs):
            text = para.strip()
            if not text or len(text) < 30:
                continue

            # Extract a concise description (first sentence or first 200 chars)
            description = self._extract_description(text)
            category = self.categorize_risk(text)
            severity = self._assess_severity(text)

            risks.append(RiskItem(
                risk_id=f"risk-{i + 1:03d}",
                category=category,
                description=description,
                severity=severity,
                source_section="Item 1A",
            ))

        return risks

    def categorize_risk(self, description: str) -> str:
        """Classify a risk description into a category.

        Uses keyword matching across six categories:
        market, operational, financial, legal, competitive, regulatory.

        Args:
            description: The risk description text.

        Returns:
            One of: "market", "operational", "financial", "legal",
            "competitive", "regulatory".
        """
        text_lower = description.lower()
        scores: Dict[str, int] = {}

        for category, keywords in self._CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if not scores:
            return "operational"  # Default category

        return max(scores, key=lambda k: scores[k])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_into_risks(self, text: str) -> List[str]:
        """Split risk-factor text into individual risk paragraphs."""
        # Common patterns that separate risks in SEC filings
        # Risk item numbers like "(1)", "Risk 1:", bullet points, or blank lines
        # Also handles "Item 1A. Risk Factors" header

        # First, try to split by numbered/bulleted risk items
        patterns = [
            r'\n\s*(?:Risk\s*(?:Factor\s*)?\d+[\.:\)])',  # "Risk Factor 1." or "Risk 1:"
            r'\n\s*\(\d+\)\s',                              # "(1) ..."
            r'\n\s*\d+\.[\s]+(?=[A-Z])',                    # "1. Competition..."
            r'\n\s*[•\-\*]\s+(?=[A-Z])',                    # Bullet points
            r'\n\s*(?:Item\s+1A|Risk\s+Factors)',           # Section header
        ]

        for pattern in patterns:
            parts = re.split(pattern, text)
            if len(parts) > 1:
                # If first part is a header/intro, drop it
                clean_parts = [p.strip() for p in parts if len(p.strip()) > 30]
                if clean_parts:
                    return clean_parts

        # Fallback: split by double newlines
        parts = re.split(r'\n\s*\n', text)
        return [p.strip() for p in parts if len(p.strip()) > 30]

    def _extract_description(self, text: str) -> str:
        """Extract a concise description from risk text."""
        # Try to get the first complete sentence
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if sentences:
            # Use first 1-2 sentences, capped at 300 chars
            desc = ""
            for s in sentences[:2]:
                if len(desc) + len(s) <= 300:
                    desc += s + " "
                else:
                    break
            desc = desc.strip()
            if desc:
                return desc

        # Fallback: first 200 chars
        return text[:200].strip()

    def _assess_severity(self, text: str) -> str:
        """Assess severity from risk language."""
        for pattern, severity in self._SEVERITY_PATTERNS:
            if pattern.search(text):
                return severity
        return "low"

    def _index_risks(self, risks: List[RiskItem]) -> Dict[str, RiskItem]:
        """Build a lookup index for previous risks by normalised key."""
        index: Dict[str, RiskItem] = {}
        for risk in risks:
            key = self._normalize(risk.description)
            if key:
                index[key] = risk
        return index

    def _find_match(
        self,
        risk: RiskItem,
        prev_index: Dict[str, RiskItem],
    ) -> Optional[RiskItem]:
        """Find a matching risk in the previous filing's index."""
        key = self._normalize(risk.description)
        if key and key in prev_index:
            return prev_index[key]

        # Fuzzy: check for substantial overlap
        for prev_key, prev_risk in prev_index.items():
            if self._overlap_score(key, prev_key) > 0.5:
                return prev_risk

        return None

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for comparison: lowercase, strip punctuation."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Keep first 100 chars as a fingerprint
        return text[:100]

    @staticmethod
    def _overlap_score(a: str, b: str) -> float:
        """Compute word-level Jaccard overlap between two strings."""
        if not a or not b:
            return 0.0
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _is_escalated(self, new_desc: str, prev_desc: str) -> bool:
        """Check whether risk language has escalated in severity."""
        new_lower = new_desc.lower()
        prev_lower = prev_desc.lower()

        for tentative, definite in self._ESCALATION_PAIRS:
            # Previous used tentative language, new uses definite
            if tentative in prev_lower and definite in new_lower:
                # Check that the tentative term was replaced (not just both present)
                if tentative not in new_lower:
                    return True

        # Also check: severity increased between descriptions
        new_sev = self._assess_severity(new_desc)
        prev_sev = self._assess_severity(prev_desc)
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        if severity_order.get(new_sev, 0) > severity_order.get(prev_sev, 0):
            return True

        return False

    @staticmethod
    def _build_summary(
        total: int,
        new_count: int,
        escalated_count: int,
        removed_count: int,
        critical_count: int,
    ) -> str:
        """Build a human-readable summary string."""
        parts = [f"Total risk factors: {total}"]
        if new_count:
            parts.append(f"{new_count} new risk(s) identified")
        if escalated_count:
            parts.append(f"{escalated_count} risk(s) with escalated language")
        if removed_count:
            parts.append(f"{removed_count} risk(s) removed from prior filing")
        if critical_count:
            parts.append(f"{critical_count} critical risk(s)")
        return ". ".join(parts) + "."


# ---------------------------------------------------------------------------
# Covenant Review Models
# ---------------------------------------------------------------------------

@dataclass
class CovenantItem:
    """A single financial covenant extracted from a credit agreement or filing."""

    covenant_id: str
    type: str               # "financial" | "affirmative" | "negative" | "reporting"
    description: str
    threshold: Optional[float] = None   # e.g. debt/EBITDA < 3.5x
    current_value: Optional[float] = None
    in_compliance: Optional[bool] = None
    trend: str = ""         # "improving" | "stable" | "deteriorating"


# ---------------------------------------------------------------------------
# Covenant Reviewer
# ---------------------------------------------------------------------------

class CovenantReviewer:
    """Extract and evaluate covenant compliance from filing text and financials.

    Parses covenant descriptions from credit-agreement references in filings
    and checks current compliance against provided financial data.
    """

    # Known covenant patterns
    _COVENANT_PATTERNS = [
        # Financial covenants
        (re.compile(
            r'(debt[-\s]to[-\s](?:ebitda|equity)|leverage\s*ratio|'
            r'interest\s*coverage|fixed\s*charge\s*coverage|'
            r'current\s*ratio|debt\s*service\s*coverage)',
            re.IGNORECASE,
        ), "financial"),
        # Affirmative covenants
        (re.compile(
            r'(maintain|preserve|keep\s*in\s*good\s*standing|'
            r'comply\s*with\s*laws|pay\s*taxes|insure|'
            r'furnish\s*financial\s*statement)',
            re.IGNORECASE,
        ), "affirmative"),
        # Negative covenants
        (re.compile(
            r'(shall\s*not|cannot|restricted\s*from|prohibited\s*from|'
            r'limitation\s*on|restriction\s*on|'
            r'incur\s*additional\s*debt|pay\s*dividend|'
            r'make\s*acquisition|sell\s*asset|merge|'
            r'change\s*of\s*control)',
            re.IGNORECASE,
        ), "negative"),
        # Reporting covenants
        (re.compile(
            r'(deliver\s*(?:audited|quarterly|monthly)\s*financial|'
            r'compliance\s*certificate|notice\s*of\s*default|'
            r'report\s*(?:quarterly|annually)|'
            r'provide\s*(?:financial|compliance)\s*(?:statement|report))',
            re.IGNORECASE,
        ), "reporting"),
    ]

    # Threshold extraction: "not exceed 3.5x", "less than 2.0", "minimum of 1.25"
    _THRESHOLD_PATTERN = re.compile(
        r'(?:not\s+exceed|less\s+than|greater\s+than|minimum\s+of|'
        r'maximum\s+of|at\s+least|not\s+less\s+than|not\s+greater\s+than|'
        r'below|above|maintain\s+(?:a\s+)?(?:minimum\s+)?)'
        r'\s*([\d]+\.?[\d]*)\s*x?',
        re.IGNORECASE,
    )

    def review(
        self,
        filing_text: str,
        financials: Optional[Dict[str, float]] = None,
    ) -> List[CovenantItem]:
        """Extract covenants from filing text and check compliance.

        Args:
            filing_text: Filing text (credit agreement, MD&A, or full filing).
            financials: Dict mapping metric names to current values
                        (e.g. {"debt_to_ebitda": 2.8, "current_ratio": 1.5}).

        Returns:
            List of CovenantItem objects with compliance status.
        """
        covenants = self._extract_covenants(filing_text)

        if financials:
            covenants = self.check_compliance(covenants, financials)

        return covenants

    def check_compliance(
        self,
        covenants: List[CovenantItem],
        financials: Dict[str, float],
    ) -> List[CovenantItem]:
        """Check covenant compliance against current financial data.

        Args:
            covenants: List of CovenantItem objects to evaluate.
            financials: Dict mapping metric names to current values.

        Returns:
            The same covenant list with in_compliance and current_value populated.
        """
        # Map covenant types/descriptions to financial keys
        metric_map = self._build_metric_map(financials)

        for covenant in covenants:
            if covenant.type != "financial":
                # Non-financial covenants are reported as compliant by default
                # unless specific evidence of breach is found
                covenant.in_compliance = True
                continue

            # Find matching financial metric
            matched_value = self._match_financial_metric(covenant, metric_map)
            if matched_value is not None:
                covenant.current_value = matched_value
                covenant.in_compliance = self._evaluate_threshold(
                    covenant.threshold, matched_value, covenant.description,
                )
            else:
                # Cannot determine without data
                covenant.in_compliance = None

        return covenants

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_covenants(self, text: str) -> List[CovenantItem]:
        """Parse covenant items from filing text."""
        if not text or not text.strip():
            return []

        covenants: List[CovenantItem] = []
        seen_descriptions = set()

        for pattern, ctype in self._COVENANT_PATTERNS:
            for match in pattern.finditer(text):
                # Extract context: find enclosing sentence boundaries
                before = text[:match.start()]
                sentence_start = 0
                for delim in ('. ', '.\n', ': ', ':\n'):
                    pos = before.rfind(delim)
                    if pos > sentence_start:
                        sentence_start = pos + len(delim)

                end = min(len(text), match.end() + 300)
                after = text[match.end():end]
                for delim in ('. ', '.\n'):
                    pos = after.find(delim)
                    if pos > 20:
                        end = match.end() + pos + 1
                        break

                context = text[sentence_start:end].strip()

                # Clean up context to a readable description
                description = self._clean_context(context)

                # Deduplicate
                norm = self._normalize(description)
                if norm in seen_descriptions:
                    continue
                seen_descriptions.add(norm)

                # Try to extract a numerical threshold — search the
                # 300-char window right after the match for tighter scoping
                window = text[match.start():min(len(text), match.end() + 300)]
                threshold = self._extract_threshold(window)
                if threshold is None:
                    threshold = self._extract_threshold(context)

                covenants.append(CovenantItem(
                    covenant_id=f"cov-{len(covenants) + 1:03d}",
                    type=ctype,
                    description=description,
                    threshold=threshold,
                ))

        return covenants

    @staticmethod
    def _clean_context(text: str) -> str:
        """Clean extracted context into a readable description."""
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Truncate to reasonable length
        if len(text) > 250:
            # Try to break at sentence boundary
            truncated = text[:250]
            last_period = max(truncated.rfind('.'), truncated.rfind(';'))
            if last_period > 100:
                text = truncated[:last_period + 1]
            else:
                text = truncated + "..."
        return text

    @staticmethod
    def _extract_threshold(text: str) -> Optional[float]:
        """Extract a numerical threshold from covenant text."""
        pattern = re.compile(
            r'(?:not\s+(?:to\s+)?exceed|less\s+than|greater\s+than|minimum\s+of|'
            r'maximum\s+of|at\s+least|not\s+less\s+than|not\s+greater\s+than|'
            r'below|above|maintain\s+(?:a\s+)?(?:minimum\s+)?)'
            r'\s*([\d]+\.?[\d]*)\s*x?',
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    @staticmethod
    def _build_metric_map(financials: Dict[str, float]) -> Dict[str, float]:
        """Build a normalised metric name → value map."""
        metric_map: Dict[str, float] = {}
        for key, value in financials.items():
            normalised = key.lower().replace('_', ' ').replace('-', ' ')
            normalised = re.sub(r'\s+', ' ', normalised).strip()
            metric_map[normalised] = value
            # Also add without spaces
            metric_map[normalised.replace(' ', '')] = value
        return metric_map

    def _match_financial_metric(
        self,
        covenant: CovenantItem,
        metric_map: Dict[str, float],
    ) -> Optional[float]:
        """Match a covenant description to a financial metric value."""
        desc_lower = covenant.description.lower()

        # Common metric name aliases
        aliases = {
            "debt to ebitda": ["debt to ebitda", "debttoebitda", "leverage ratio", "leverageratio", "total debt to ebitda"],
            "debt to equity": ["debt to equity", "debttoequity", "d e ratio"],
            "interest coverage": ["interest coverage", "interestcoverage", "interest coverage ratio", "ebit interest"],
            "current ratio": ["current ratio", "currentratio", "working capital ratio"],
            "fixed charge coverage": ["fixed charge coverage", "fixedchargecoverage", "fixed charge coverage ratio"],
            "debt service coverage": ["debt service coverage", "debtservicecoverage", "dscr"],
        }

        for base_name, alias_list in aliases.items():
            if base_name.replace(' ', '') in desc_lower.replace(' ', ''):
                for alias in alias_list:
                    if alias in metric_map:
                        return metric_map[alias]
                    # Also check if covenant description mentions the metric
                    if alias.replace(' ', '') in desc_lower.replace(' ', ''):
                        # Try all values in metric_map
                        for mk, mv in metric_map.items():
                            if mk.replace(' ', '').startswith(alias.replace(' ', '')[:5]):
                                return mv

        # Broad search: any metric key that appears in the description
        for mk, mv in metric_map.items():
            if len(mk) > 5 and mk in desc_lower.replace(' ', ''):
                return mv

        return None

    def _evaluate_threshold(
        self,
        threshold: Optional[float],
        current: float,
        description: str,
    ) -> Optional[bool]:
        """Evaluate whether current value satisfies the covenant threshold."""
        if threshold is None:
            return None

        desc_lower = description.lower()

        # "must not exceed", "less than", "below", "maximum of" → value must be ≤ threshold
        if any(phrase in desc_lower for phrase in [
            "not exceed", "not to exceed", "less than", "below", "maximum of",
            "not greater than", "not be greater",
        ]):
            return current <= threshold

        # "must be at least", "greater than", "above", "minimum of" → value must be ≥ threshold
        if any(phrase in desc_lower for phrase in [
            "at least", "greater than", "above", "minimum of",
            "not less than", "not be less",
        ]):
            return current >= threshold

        # Default: assume "not exceed" for leverage ratios, "at least" for coverage ratios
        if any(term in desc_lower for term in ["leverage", "debt to", "debtto"]):
            return current <= threshold
        if any(term in desc_lower for term in ["coverage", "current ratio"]):
            return current >= threshold

        return None

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for deduplication."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:120]

    def analyze_trend(
        self,
        covenant: CovenantItem,
        historical_values: List[float],
    ) -> str:
        """Analyze the trend of a covenant metric over time.

        Args:
            covenant: The covenant to analyze.
            historical_values: Ordered list of past values (oldest first).

        Returns:
            One of: "improving", "stable", "deteriorating".
        """
        if len(historical_values) < 2:
            return "stable"

        recent = historical_values[-2:]
        if covenant.threshold is not None and covenant.in_compliance is not None:
            # Determine if higher or lower is better based on covenant language
            desc_lower = covenant.description.lower()
            higher_is_better = any(phrase in desc_lower for phrase in [
                "at least", "greater than", "above", "minimum of",
                "not less than", "coverage", "current ratio",
            ])

            if higher_is_better:
                if recent[1] > recent[0] * 1.02:
                    return "improving"
                elif recent[1] < recent[0] * 0.98:
                    return "deteriorating"
            else:
                if recent[1] < recent[0] * 0.98:
                    return "improving"
                elif recent[1] > recent[0] * 1.02:
                    return "deteriorating"

        return "stable"


# ---------------------------------------------------------------------------
# SEC EDGAR source: the two most recent 10-K risk-factor sections
# ---------------------------------------------------------------------------

_RISK_SECTION_START = r"Item\s+1A\.?"
_RISK_SECTION_ENDS = (r"Item\s+1B\.?", r"Item\s+1C\.?", r"Item\s+2\.?")


def _filing_html_to_text(html: str) -> str:
    """Convert filing HTML to text with one blank line between blocks.

    Inline markup (``<span>``, ``<sup>®</sup>``…) must not break lines, and
    block elements must: RiskReviewer splits risks on blank lines.
    """
    import html as _html

    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|table|h[1-6])\s*>", "\n\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    text = _html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_risk_factor_section(text: str) -> str:
    """Return the body of Item 1A.

    Filings mention "Item 1A." in the table of contents and in
    cross-references as well as at the real heading. For each "Item 1B/1C/2"
    boundary take the *closest* preceding "Item 1A" (so a cross-reference in
    Item 1 cannot swallow the whole business section), then keep the longest
    such span — table-of-contents pairs are only a line apart.
    """
    starts = [m.start() for m in re.finditer(_RISK_SECTION_START, text, re.IGNORECASE)]
    ends = sorted(m.start() for pat in _RISK_SECTION_ENDS for m in re.finditer(pat, text, re.IGNORECASE))
    best = (0, 0)
    for end in ends:
        start = max((s_ for s_ in starts if s_ < end), default=None)
        if start is not None and end - start > best[1] - best[0]:
            best = (start, end)
    return text[best[0]:best[1]].strip()


def group_risk_paragraphs(section: str) -> str:
    """Merge each risk heading with the body paragraphs that follow it.

    10-K risk factors are a short heading sentence (no terminal period, or a
    one-line summary) followed by one or more body paragraphs. Returns the
    section with exactly one blank line between complete risk factors.
    """
    # Running page headers/footers ("Apple Inc. | 2025 Form 10-K | 6") and
    # bare page numbers leak into the text between blocks; left in, they
    # differ by year and show up as spurious new/removed risks.
    footer = re.compile(r"(?i)^[^\n]{0,80}\|\s*(19|20)\d\d\s+form\s+10-k\s*\|\s*\d+\s*|^\d{1,3}$")
    paragraphs = []
    for p in section.split("\n\n"):
        lines = [ln for ln in p.split("\n") if ln.strip() and not footer.match(ln.strip())]
        p = footer.sub("", " ".join(lines)).strip()
        if p:
            paragraphs.append(p)
    if not paragraphs:
        return ""
    if re.match(r"(?i)item\s+1a", paragraphs[0]):
        paragraphs = paragraphs[1:]
    flat = [" ".join(p.split()) for p in paragraphs]
    groups: List[List[str]] = []
    for i, para in enumerate(flat):
        nxt = flat[i + 1] if i + 1 < len(flat) else ""
        sentences = len(re.findall(r"[.!?](\s|$)", para))
        # A heading is one short statement introducing a longer body.
        is_heading = bool(nxt) and len(para) <= 350 and sentences <= 2 and len(para) < len(nxt)
        if is_heading or not groups:
            groups.append([para])
        else:
            groups[-1].append(para)
    # A heading with no body is a sub-section title ("Macroeconomic and
    # Industry Risks"), not a risk factor.
    return "\n\n".join(" ".join(g) for g in groups if len(g) > 1 or len(g[0]) > 400)


def fetch_10k_risk_sections(ticker: str, client=None) -> Dict[str, str]:
    """Fetch Item 1A from the two most recent 10-K filings on SEC EDGAR.

    Returns ``{"new_text", "prev_text", "new_accession", "new_filed",
    "prev_accession", "prev_filed"}``; ``prev_*`` are empty when only one
    10-K exists. Raises ``LookupError`` when nothing usable is found.
    """
    if client is None:
        from augur.consensus.edgar_fundamentals import _get_client

        client = _get_client()
    cik = client.get_cik(ticker)
    if cik is None:
        raise LookupError(f"{ticker.upper()} has no SEC CIK (non-US listing or not an XBRL filer)")
    submissions = client.get_submissions(cik) or {}
    try:
        recent = submissions["filings"]["recent"]
        rows = list(zip(recent["form"], recent["accessionNumber"], recent["primaryDocument"], recent["filingDate"]))
    except (KeyError, TypeError):
        raise LookupError(f"could not read SEC submissions for {ticker.upper()}")
    tenks = [r for r in rows if r[0] == "10-K"][:2]
    if not tenks:
        raise LookupError(f"no 10-K filings found for {ticker.upper()}")

    sections = []
    for _form, accession, document, filed in tenks:
        html = client.get_filing_document(cik, accession, document)
        section = group_risk_paragraphs(extract_risk_factor_section(_filing_html_to_text(html))) if html else ""
        sections.append((section, accession, filed))
    if not sections[0][0]:
        raise LookupError(f"could not locate Item 1A in {ticker.upper()} 10-K {tenks[0][1]}")
    prev = sections[1] if len(sections) > 1 else ("", "", "")
    return {
        "new_text": sections[0][0], "new_accession": sections[0][1], "new_filed": sections[0][2],
        "prev_text": prev[0], "prev_accession": prev[1], "prev_filed": prev[2],
    }
