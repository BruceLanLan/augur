"""Thesis Journal + Questions + Decisions REST API (E01/E03/E04 UI wiring)."""
from __future__ import annotations
from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Module-level singletons so POST/GET share state (in-memory stores)
_thesis_journal = None
_question_queue = None
_decision_log = None


def _journal():
    global _thesis_journal
    if _thesis_journal is None:
        from augur.thesis import ThesisJournal
        _thesis_journal = ThesisJournal()
    return _thesis_journal


def _questions():
    global _question_queue
    if _question_queue is None:
        from augur.questions import QuestionQueue
        _question_queue = QuestionQueue()
    return _question_queue


def _decisions():
    global _decision_log
    if _decision_log is None:
        from augur.thesis import DecisionLog
        _decision_log = DecisionLog()
    return _decision_log


class ThesisCreate(BaseModel):
    ticker: str
    statement: str
    catalysts: List[str] = []
    risks: List[str] = []
    falsification_conditions: List[str] = []


class QuestionAdd(BaseModel):
    ticker: str = ""
    question: str
    context: str = ""


class DecisionRecord(BaseModel):
    ticker: str = ""
    action: str
    reasoning: str = ""


@router.get("/api/thesis/list")
async def thesis_list(ticker: str = "") -> Dict[str, Any]:
    """List theses, optionally filtered by ticker."""
    journal = _journal()
    theses = journal.list_by_ticker(ticker) if ticker else journal.list_all()
    items = []
    for t in theses:
        items.append({
            "thesis_id": t.thesis_id, "ticker": t.ticker, "statement": t.statement,
            "catalysts": t.catalysts, "risks": t.risks,
            "falsification_conditions": t.falsification_conditions,
            "created_at": t.created_at, "status": t.status, "run_id": t.run_id,
        })
    return {"theses": items}


@router.post("/api/thesis/create")
async def thesis_create(body: ThesisCreate) -> Dict[str, Any]:
    """Create a new thesis."""
    from augur.thesis import Thesis
    journal = _journal()
    thesis = Thesis(
        thesis_id="", ticker=body.ticker.upper(), statement=body.statement,
        catalysts=body.catalysts, risks=body.risks,
        falsification_conditions=body.falsification_conditions,
        created_at="", status="active", run_id="",
    )
    tid = journal.create(thesis)
    return {"thesis_id": tid, "status": "created"}


@router.get("/api/questions/list")
async def questions_list(ticker: str = "", status: str = "open") -> Dict[str, Any]:
    """List research questions."""
    q = _questions()
    questions = q.list(ticker, status)
    return {"questions": [
        {"question_id": x.question_id, "ticker": x.ticker, "question": x.question,
         "context": x.context, "created_at": x.created_at, "status": x.status,
         "answer": x.answer, "answer_confidence": x.answer_confidence}
        for x in questions
    ]}


@router.post("/api/questions/add")
async def questions_add(body: QuestionAdd) -> Dict[str, Any]:
    """Add a research question."""
    from augur.questions import ResearchQuestion
    q = _questions()
    rq = ResearchQuestion(
        question_id="", ticker=body.ticker.upper(), question=body.question,
        context=body.context, created_at="", status="open",
    )
    qid = q.add(rq)
    return {"question_id": qid, "status": "added"}


@router.get("/api/decisions/list")
async def decisions_list(ticker: str = "") -> Dict[str, Any]:
    """List decisions."""
    log = _decisions()
    decisions = log.list_by_ticker(ticker) if ticker else []
    return {"decisions": [
        {"decision_id": d.decision_id, "ticker": d.ticker, "action": d.action,
         "reasoning": d.reasoning, "created_at": d.created_at, "outcome": d.outcome}
        for d in decisions
    ]}


@router.post("/api/decisions/record")
async def decisions_record(body: DecisionRecord) -> Dict[str, Any]:
    """Record a decision."""
    from augur.thesis import Decision
    log = _decisions()
    decision = Decision(
        decision_id="", ticker=body.ticker.upper(), action=body.action,
        reasoning=body.reasoning, evidence_run_ids=[], thesis_ids=[],
        created_at="", outcome=None,
    )
    did = log.record(decision)
    return {"decision_id": did, "status": "recorded"}
