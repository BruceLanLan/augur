# -*- coding: utf-8 -*-
"""
augur.questions — Open Questions Queue & Research Template Library (E04 + E05).

E04 — Open Questions Queue
    ``ResearchQuestion`` dataclass and ``QuestionQueue`` for tracking
    open research questions with ticker-scoped listing, answering,
    staleness marking, and open-count queries.

E05 — Research Template Library
    ``ResearchTemplate`` dataclass and ``TemplateLibrary`` for managing
    reusable research workflow templates with Jinja2-style prompt rendering
    and a set of built-in templates (earnings-deep-dive, quick-screening,
    thesis-review, filing-review).

Usage::

    from augur.questions import (
        ResearchQuestion,
        QuestionQueue,
        ResearchTemplate,
        TemplateLibrary,
    )

    queue = QuestionQueue()
    qid = queue.add(ResearchQuestion(
        question_id="", ticker="AAPL",
        question="Is services growth sustainable?",
        context="Apple revenue mix shifting",
        created_at="2026-01-15T10:00:00Z",
    ))
    count = queue.get_open_count("AAPL")
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================================
# E04 — Open Questions Queue
# ============================================================================


@dataclass
class ResearchQuestion:
    """A single research question tracked in the open-questions queue.

    Attributes:
        question_id: Unique identifier (``q_{hash[:8]}``), auto-generated
            by ``QuestionQueue.add()`` when empty.
        ticker: Instrument ticker (e.g. ``"AAPL"``).
        question: The research question (e.g. *"Is the services growth
            sustainable above 15%?"*).
        context: Why this question matters (rationale).
        created_at: ISO-8601 timestamp when the question was created.
        status: Lifecycle state — ``"open"``, ``"answered"``, or ``"stale"``.
        answered_by_run_id: The ``run_id`` that answered this question, if any.
        answer: The answer text, populated when the question is resolved.
        answer_confidence: Confidence level — ``"high"``, ``"medium"``, or
            ``"low"``.
    """

    question_id: str       # q_{hash[:8]}
    ticker: str
    question: str           # "Is the services growth sustainable above 15%?"
    context: str            # why this matters
    created_at: str
    status: str = "open"   # "open" | "answered" | "stale"
    answered_by_run_id: Optional[str] = None
    answer: str = ""
    answer_confidence: str = ""  # "high" | "medium" | "low"


@dataclass
class QuestionQueue:
    """In-memory queue of :class:`ResearchQuestion` items.

    Scoped by ticker — each method that takes a *ticker* argument
    normalises it to uppercase for consistent lookups.

    Parameters:
        questions: Optional initial list of questions to seed the queue.
    """

    _questions: List[ResearchQuestion] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_id(ticker: str, question: str, created_at: str) -> str:
        raw = f"{ticker.upper()}:{question}:{created_at}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:8]
        return f"q_{h}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, question: ResearchQuestion) -> str:
        """Add a question to the queue.

        If *question.question_id* is empty, an id is auto-generated from
        ``ticker`` + ``question`` + ``created_at``.

        Returns:
            The question's ``question_id``.
        """
        if not question.question_id:
            question.question_id = self._generate_id(
                question.ticker, question.question, question.created_at
            )
        self._questions.append(question)
        return question.question_id

    def list(
        self,
        ticker: str,
        status: str = "open",
    ) -> List[ResearchQuestion]:
        """List questions filtered by *ticker* and *status*.

        Args:
            ticker: Instrument ticker (case-insensitive).
            status: Filter by status (default ``"open"``).

        Returns:
            Matching questions in insertion order.
        """
        t = ticker.upper()
        return [
            q
            for q in self._questions
            if q.ticker.upper() == t and q.status == status
        ]

    def answer(
        self,
        question_id: str,
        run_id: str,
        answer: str,
        confidence: str,
    ) -> None:
        """Record an answer for a question, transitioning it to ``"answered"``.

        Args:
            question_id: The question to answer.
            run_id: The ``run_id`` that produced the answer.
            answer: The answer text.
            confidence: ``"high"``, ``"medium"``, or ``"low"``.
        """
        for q in self._questions:
            if q.question_id == question_id:
                q.status = "answered"
                q.answered_by_run_id = run_id
                q.answer = answer
                q.answer_confidence = confidence
                return

    def mark_stale(self, question_id: str) -> None:
        """Mark a question as ``"stale"``.

        Args:
            question_id: The question to mark stale.
        """
        for q in self._questions:
            if q.question_id == question_id:
                q.status = "stale"
                return

    def get_open_count(self, ticker: str) -> int:
        """Return the number of open questions for *ticker*.

        Args:
            ticker: Instrument ticker (case-insensitive).

        Returns:
            Count of questions with status ``"open"``.
        """
        t = ticker.upper()
        return sum(
            1
            for q in self._questions
            if q.ticker.upper() == t and q.status == "open"
        )


# ============================================================================
# E05 — Research Template Library
# ============================================================================


@dataclass
class ResearchTemplate:
    """A reusable research workflow template.

    Attributes:
        template_id: Unique identifier (e.g. ``"earnings-deep-dive"``).
        name: Human-readable name (e.g. ``"Earnings Deep Dive"``).
        description: One-paragraph summary of what this template does.
        steps: Ordered workflow step names (e.g. ``["fetch", "analyze"]``).
        required_skills: Skill names this template depends on.
        prompt_template: A Jinja2-style template string with ``{{ var }}``
            placeholders.
        category: Optional grouping label for ``list_by_category()``.
    """

    template_id: str
    name: str               # "Earnings Deep Dive", "IPO Analysis"
    description: str
    steps: List[str]        # workflow step names
    required_skills: List[str]
    prompt_template: str    # Jinja2-style template
    category: str = ""      # grouping label for list_by_category


@dataclass
class TemplateLibrary:
    """In-memory registry of :class:`ResearchTemplate` items.

    On initialisation the library auto-registers four built-in templates:
    ``earnings-deep-dive``, ``quick-screening``, ``thesis-review``, and
    ``filing-review``.
    """

    _templates: Dict[str, ResearchTemplate] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._register_builtins()

    # ------------------------------------------------------------------
    # Built-in templates
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        """Register the four built-in research templates."""
        self.register(
            ResearchTemplate(
                template_id="earnings-deep-dive",
                name="Earnings Deep Dive",
                description=(
                    "A comprehensive earnings analysis workflow: fetch data, "
                    "run multi-agent analysis, compute consensus, and convene "
                    "a committee review."
                ),
                steps=["fetch", "analyze", "consensus", "committee"],
                required_skills=["earnings_prep", "consensus"],
                prompt_template=(
                    "Analyze {{ ticker }} earnings for {{ fiscal_period }}.\n"
                    "Focus areas: {{ focus_areas }}.\n"
                    "Thresholds: revenue growth > {{ revenue_threshold }}%, "
                    "margin > {{ margin_threshold }}%."
                ),
                category="earnings",
            )
        )
        self.register(
            ResearchTemplate(
                template_id="quick-screening",
                name="Quick Screening",
                description=(
                    "A lightweight screening workflow using only the value "
                    "school of analysis: fetch data and run a single-pass "
                    "analysis."
                ),
                steps=["fetch", "analyze"],
                required_skills=["value"],
                prompt_template=(
                    "Screen {{ ticker }} for value characteristics.\n"
                    "Key metrics: P/E < {{ pe_max }}, P/B < {{ pb_max }}, "
                    "D/E < {{ de_max }}.\n"
                    "Minimum market cap: ${{ min_market_cap }}B."
                ),
                category="screening",
            )
        )
        self.register(
            ResearchTemplate(
                template_id="thesis-review",
                name="Thesis Review",
                description=(
                    "Compare two RunBundles to identify thesis deltas: "
                    "what changed, what stayed the same, and whether the "
                    "original thesis still holds."
                ),
                steps=["compare", "delta", "conclusion"],
                required_skills=["thesis", "consensus"],
                prompt_template=(
                    "Compare thesis for {{ ticker }} between run "
                    "{{ baseline_run_id }} and {{ candidate_run_id }}.\n"
                    "Baseline thesis: {{ baseline_thesis }}\n"
                    "Candidate thesis: {{ candidate_thesis }}\n"
                    "Evaluate: has the thesis meaningfully changed?"
                ),
                category="review",
            )
        )
        self.register(
            ResearchTemplate(
                template_id="filing-review",
                name="Filing Review",
                description=(
                    "Analyse a new SEC filing using the filing-delta skill "
                    "to detect material changes from the previous filing."
                ),
                steps=["fetch_filing", "delta", "assess"],
                required_skills=["filing_delta"],
                prompt_template=(
                    "Review {{ ticker }} filing {{ accession_number }} "
                    "({% if is_amendment %}amendment to {{ original_filing }}"
                    "{% else %}new filing{% endif %}).\n"
                    "Compare against previous filing and flag material "
                    "changes in: {{ focus_sections }}."
                ),
                category="review",
            )
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, template: ResearchTemplate) -> None:
        """Register a research template, overwriting any existing entry
        with the same ``template_id``.

        Args:
            template: The template to register.
        """
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> ResearchTemplate:
        """Retrieve a template by id.

        Args:
            template_id: The template identifier.

        Returns:
            The matching :class:`ResearchTemplate`.

        Raises:
            KeyError: If *template_id* is not registered.
        """
        return self._templates[template_id]

    def list_by_category(self, category: str) -> List[ResearchTemplate]:
        """List all templates whose ``category`` matches (case-insensitive).

        Args:
            category: The category label to filter by.

        Returns:
            Matching templates in registration order.
        """
        cat = category.lower()
        return [
            t for t in self._templates.values() if t.category.lower() == cat
        ]

    def render(self, template_id: str, context: dict) -> str:
        """Fill a template's ``prompt_template`` with *context* values.

        Supports Jinja2-style ``{{ var }}`` placeholders.  Variables in
        the template that are missing from *context* are left as-is (the
        placeholder is not replaced).  Jinja2 control-flow tags such as
        ``{% if ... %}`` are passed through unmodified.

        Args:
            template_id: The template to render.
            context: Mapping of variable names to string values.

        Returns:
            The rendered prompt string.

        Raises:
            KeyError: If *template_id* is not registered.
        """
        tmpl = self.get(template_id)
        source = tmpl.prompt_template

        def _replacer(match: re.Match) -> str:
            var_name = match.group(1).strip()
            if var_name in context:
                return str(context[var_name])
            return match.group(0)  # leave unknown vars as-is

        return re.sub(r"\{\{\s*(\w+)\s*\}\}", _replacer, source)
