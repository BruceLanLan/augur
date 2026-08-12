# -*- coding: utf-8 -*-
"""Tests for augur.questions — Open Questions Queue & Research Template Library."""

import pytest

from augur.questions import (
    QuestionQueue,
    ResearchQuestion,
    ResearchTemplate,
    TemplateLibrary,
)


# ============================================================================
# E04 — ResearchQuestion & QuestionQueue
# ============================================================================


class TestResearchQuestion:
    """Tests for the ResearchQuestion dataclass."""

    def test_create_with_defaults(self):
        """ResearchQuestion defaults: status="open", empty answer fields."""
        q = ResearchQuestion(
            question_id="q_abc12345",
            ticker="AAPL",
            question="Is services growth sustainable?",
            context="Revenue mix shift toward services",
            created_at="2026-01-15T10:00:00Z",
        )
        assert q.question_id == "q_abc12345"
        assert q.ticker == "AAPL"
        assert q.status == "open"
        assert q.answered_by_run_id is None
        assert q.answer == ""
        assert q.answer_confidence == ""

    def test_create_with_all_fields(self):
        """All fields populated explicitly."""
        q = ResearchQuestion(
            question_id="q_xyz",
            ticker="MSFT",
            question="Can Azure sustain 30% growth?",
            context="Cloud market saturation concerns",
            created_at="2026-02-01T08:00:00Z",
            status="answered",
            answered_by_run_id="run_001",
            answer="Likely yes, based on AI workload tailwinds",
            answer_confidence="high",
        )
        assert q.status == "answered"
        assert q.answered_by_run_id == "run_001"
        assert q.answer_confidence == "high"


class TestQuestionQueue:
    """Tests for the QuestionQueue."""

    @pytest.fixture
    def queue(self):
        return QuestionQueue()

    @pytest.fixture
    def sample_question(self):
        return ResearchQuestion(
            question_id="",
            ticker="AAPL",
            question="Is services growth sustainable?",
            context="Revenue mix shifting",
            created_at="2026-01-15T10:00:00Z",
        )

    # -- add ------------------------------------------------------------

    def test_add_generates_id(self, queue, sample_question):
        """add() auto-generates question_id when empty."""
        qid = queue.add(sample_question)
        assert qid.startswith("q_")
        assert len(qid) == 10  # "q_" + 8 hex chars
        assert sample_question.question_id == qid

    def test_add_preserves_existing_id(self, queue):
        """add() preserves an already-set question_id."""
        q = ResearchQuestion(
            question_id="q_manual01",
            ticker="TSLA",
            question="Margin trajectory?",
            context="Price cuts",
            created_at="2026-03-01T12:00:00Z",
        )
        qid = queue.add(q)
        assert qid == "q_manual01"

    def test_add_deterministic_id(self, queue):
        """Same inputs produce the same question_id."""
        q1 = ResearchQuestion(
            question_id="",
            ticker="AAPL",
            question="Same question",
            context="Same context",
            created_at="2026-01-01T00:00:00Z",
        )
        q2 = ResearchQuestion(
            question_id="",
            ticker="AAPL",
            question="Same question",
            context="Same context",
            created_at="2026-01-01T00:00:00Z",
        )
        assert queue.add(q1) == queue.add(q2)

    # -- list -----------------------------------------------------------

    def test_list_filters_by_ticker_and_status(self, queue):
        """list() returns only matching ticker + status questions."""
        q1 = ResearchQuestion(
            question_id="q_001", ticker="AAPL",
            question="Q1", context="c", created_at="2026-01-01T00:00:00Z",
            status="open",
        )
        q2 = ResearchQuestion(
            question_id="q_002", ticker="MSFT",
            question="Q2", context="c", created_at="2026-01-01T00:00:00Z",
            status="open",
        )
        q3 = ResearchQuestion(
            question_id="q_003", ticker="AAPL",
            question="Q3", context="c", created_at="2026-01-01T00:00:00Z",
            status="answered",
        )
        for q in (q1, q2, q3):
            queue.add(q)

        aapl_open = queue.list("AAPL", status="open")
        assert len(aapl_open) == 1
        assert aapl_open[0].question_id == "q_001"

    def test_list__ticker(self, queue):
        """list() matches ticker case-insensitively."""
        queue.add(ResearchQuestion(
            question_id="q_001", ticker="aapl",
            question="Q", context="c", created_at="2026-01-01T00:00:00Z",
            status="open",
        ))
        result = queue.list("AAPL")
        assert len(result) == 1

    def test_list_default_status_open(self, queue):
        """list() defaults to status="open"."""
        queue.add(ResearchQuestion(
            question_id="q_001", ticker="AAPL",
            question="Q", context="c", created_at="2026-01-01T00:00:00Z",
            status="stale",
        ))
        assert len(queue.list("AAPL")) == 0

    # -- answer ---------------------------------------------------------

    def test_answer_transitions_to_answered(self, queue, sample_question):
        """answer() sets status, run_id, answer, and confidence."""
        qid = queue.add(sample_question)
        queue.answer(qid, run_id="run_42", answer="Yes, sustainable.",
                     confidence="high")

        items = queue.list("AAPL", status="answered")
        assert len(items) == 1
        answered = items[0]
        assert answered.status == "answered"
        assert answered.answered_by_run_id == "run_42"
        assert answered.answer == "Yes, sustainable."
        assert answered.answer_confidence == "high"

    def test_answer_removes_from_open_list(self, queue, sample_question):
        """After answering, the question no longer appears in open list."""
        qid = queue.add(sample_question)
        assert queue.get_open_count("AAPL") == 1
        queue.answer(qid, run_id="r1", answer="A", confidence="medium")
        assert queue.get_open_count("AAPL") == 0

    # -- mark_stale -----------------------------------------------------

    def test_mark_stale_changes_status(self, queue, sample_question):
        """mark_stale() transitions to 'stale'."""
        qid = queue.add(sample_question)
        queue.mark_stale(qid)
        stale = queue.list("AAPL", status="stale")
        assert len(stale) == 1
        assert stale[0].question_id == qid

    # -- get_open_count -------------------------------------------------

    def test_get_open_count(self, queue):
        """get_open_count() returns the number of open questions for a ticker."""
        for i in range(3):
            queue.add(ResearchQuestion(
                question_id=f"q_{i:03d}", ticker="AAPL",
                question=f"Q{i}", context="c",
                created_at="2026-01-01T00:00:00Z",
                status="open",
            ))
        queue.add(ResearchQuestion(
            question_id="q_msft", ticker="MSFT",
            question="Q", context="c", created_at="2026-01-01T00:00:00Z",
            status="open",
        ))
        assert queue.get_open_count("AAPL") == 3
        assert queue.get_open_count("MSFT") == 1
        assert queue.get_open_count("NFLX") == 0

    def test_get_open_count_(self, queue):
        """get_open_count() is case-insensitive."""
        queue.add(ResearchQuestion(
            question_id="q_001", ticker="aapl",
            question="Q", context="c", created_at="2026-01-01T00:00:00Z",
            status="open",
        ))
        assert queue.get_open_count("AAPL") == 1


# ============================================================================
# E05 — ResearchTemplate & TemplateLibrary
# ============================================================================


class TestResearchTemplate:
    """Tests for the ResearchTemplate dataclass."""

    def test_create_template(self):
        """Basic template creation with all fields."""
        t = ResearchTemplate(
            template_id="my-template",
            name="My Template",
            description="A custom research template",
            steps=["fetch", "analyze"],
            required_skills=["value", "momentum"],
            prompt_template="Analyze {{ ticker }} with {{ approach }}.",
            category="custom",
        )
        assert t.template_id == "my-template"
        assert t.name == "My Template"
        assert len(t.steps) == 2
        assert len(t.required_skills) == 2


class TestTemplateLibrary:
    """Tests for the TemplateLibrary."""

    @pytest.fixture
    def lib(self):
        return TemplateLibrary()

    # -- built-in templates ---------------------------------------------

    def test_builtins_registered(self, lib):
        """All four built-in templates are auto-registered."""
        assert lib.get("earnings-deep-dive").name == "Earnings Deep Dive"
        assert lib.get("quick-screening").name == "Quick Screening"
        assert lib.get("thesis-review").name == "Thesis Review"
        assert lib.get("filing-review").name == "Filing Review"

    def test_builtin_earnings_steps(self, lib):
        """earnings-deep-dive has fetch → analyze → consensus → committee."""
        t = lib.get("earnings-deep-dive")
        assert t.steps == ["fetch", "analyze", "consensus", "committee"]

    def test_builtin_quick_screening_steps(self, lib):
        """quick-screening uses only fetch → analyze."""
        t = lib.get("quick-screening")
        assert t.steps == ["fetch", "analyze"]
        assert "value" in t.required_skills

    # -- register / get ------------------------------------------------

    def test_register_and_get(self, lib):
        """register() stores a template; get() retrieves it."""
        t = ResearchTemplate(
            template_id="custom-1",
            name="Custom",
            description="Desc",
            steps=["s1"],
            required_skills=["sk1"],
            prompt_template="Hello {{ name }}",
        )
        lib.register(t)
        assert lib.get("custom-1") is t

    def test_get_missing_raises_keyerror(self, lib):
        """get() raises KeyError for unknown template_id."""
        with pytest.raises(KeyError):
            lib.get("nonexistent")

    def test_register_overwrites(self, lib):
        """Registering a template with the same id overwrites the previous."""
        t1 = ResearchTemplate(
            template_id="dup", name="First", description="d",
            steps=[], required_skills=[], prompt_template="",
        )
        t2 = ResearchTemplate(
            template_id="dup", name="Second", description="d",
            steps=[], required_skills=[], prompt_template="",
        )
        lib.register(t1)
        lib.register(t2)
        assert lib.get("dup") is t2

    # -- list_by_category -----------------------------------------------

    def test_list_by_category(self, lib):
        """list_by_category() filters by category case-insensitively."""
        lib.register(ResearchTemplate(
            template_id="t1", name="T1", description="d",
            steps=[], required_skills=[], prompt_template="",
            category="earnings",
        ))
        lib.register(ResearchTemplate(
            template_id="t2", name="T2", description="d",
            steps=[], required_skills=[], prompt_template="",
            category="screening",
        ))
        earnings = lib.list_by_category("earnings")
        assert len(earnings) >= 1
        assert any(t.template_id == "t1" for t in earnings)

    def test_list_by_category_(self, lib):
        """list_by_category() is case-insensitive."""
        lib.register(ResearchTemplate(
            template_id="t1", name="T1", description="d",
            steps=[], required_skills=[], prompt_template="",
            category="EARNINGS",
        ))
        assert len(lib.list_by_category("earnings")) >= 1
        assert any(t.category.upper() == "EARNINGS" or t.category.upper() == "SCREENING" for t in lib.list_by_category("EARNINGS"))

    def test_list_by_category_unknown_returns_empty(self, lib):
        """list_by_category() returns empty list for unknown category."""
        assert lib.list_by_category("nonexistent") == []

    # -- render ---------------------------------------------------------

    def test_render_substitutes_variables(self, lib):
        """render() replaces {{ var }} placeholders with context values."""
        lib.register(ResearchTemplate(
            template_id="test-render",
            name="Test",
            description="d",
            steps=[],
            required_skills=[],
            prompt_template="Analyze {{ ticker }} using {{ method }}.",
        ))
        result = lib.render("test-render", {
            "ticker": "AAPL",
            "method": "DCF",
        })
        assert result == "Analyze AAPL using DCF."

    def test_render_missing_context_left_as_is(self, lib):
        """Missing context vars leave the placeholder unchanged."""
        lib.register(ResearchTemplate(
            template_id="partial",
            name="Partial",
            description="d",
            steps=[],
            required_skills=[],
            prompt_template="{{ ticker }} and {{ missing }}",
        ))
        result = lib.render("partial", {"ticker": "AAPL"})
        assert "AAPL" in result
        assert "{{ missing }}" in result

    def test_render_preserves_control_flow_tags(self, lib):
        """Jinja2 {% if %} tags are passed through unmodified."""
        lib.register(ResearchTemplate(
            template_id="ctrl",
            name="Ctrl",
            description="d",
            steps=[],
            required_skills=[],
            prompt_template="{% if flag %}do something{% endif %} {{ var }}",
        ))
        result = lib.render("ctrl", {"var": "value"})
        assert "{% if flag %}do something{% endif %}" in result
        assert "value" in result

    def test_render_missing_template_raises_keyerror(self, lib):
        """render() raises KeyError for unknown template."""
        with pytest.raises(KeyError):
            lib.render("nonexistent", {})

    def test_render_with_int_context(self, lib):
        """render() coerces non-string context values to str."""
        lib.register(ResearchTemplate(
            template_id="int-test",
            name="Int",
            description="d",
            steps=[],
            required_skills=[],
            prompt_template="Threshold: {{ threshold }}%",
        ))
        result = lib.render("int-test", {"threshold": 15})
        assert result == "Threshold: 15%"


# ============================================================================
# Integration smoke test
# ============================================================================


def test_full_workflow():
    """End-to-end: create queue, add questions, answer one, check counts."""
    queue = QuestionQueue()

    qid1 = queue.add(ResearchQuestion(
        question_id="", ticker="NFLX",
        question="Can ad-tier reach 50M subs?",
        context="Ad-supported tier expansion",
        created_at="2026-04-01T09:00:00Z",
    ))
    qid2 = queue.add(ResearchQuestion(
        question_id="", ticker="NFLX",
        question="Is content spend growth slowing?",
        context="Cash flow inflection",
        created_at="2026-04-01T09:05:00Z",
    ))

    assert queue.get_open_count("NFLX") == 2

    queue.answer(qid1, run_id="run_01", answer="On track for 40-45M",
                 confidence="medium")

    assert queue.get_open_count("NFLX") == 1
    assert queue.list("NFLX", status="answered")[0].answered_by_run_id == "run_01"

    queue.mark_stale(qid2)
    assert queue.get_open_count("NFLX") == 0
    assert len(queue.list("NFLX", status="stale")) == 1
