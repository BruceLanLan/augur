# -*- coding: utf-8 -*-
"""
augur.thesis — Investment Thesis Tracking System.

Tracks investment theses over time, computes deltas between analysis runs,
and maintains an auditable decision log.  All persisted data lives under
``get_data_dir() / "thesis" /``.

Classes:
    Thesis           — immutable dataclass for a single investment thesis
    ThesisJournal    — CRUD manager for theses with JSON persistence
    ThesisDelta      — structured diff between two runs for a thesis
    compute_thesis_delta() — engine that produces a ThesisDelta
    Decision         — immutable dataclass for a trading/follow-up decision
    DecisionLog      — CRUD manager for decisions with JSON persistence
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from augur.data_dir import get_data_dir


# ---------------------------------------------------------------------------
# Data directory
# ---------------------------------------------------------------------------

THESIS_DIR = get_data_dir() / "thesis"

# Locks protecting file writes so concurrent access doesn't corrupt data
_thesis_write_lock = threading.Lock()
_decision_write_lock = threading.Lock()


def _ensure_dir() -> None:
    """Ensure the thesis data directory exists."""
    THESIS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_thesis_id(ticker: str, statement: str) -> str:
    """Generate ``th_{ticker}_{hash[:8]}`` from the thesis statement."""
    h = hashlib.sha256(statement.encode("utf-8")).hexdigest()
    return f"th_{ticker.upper()}_{h[:8]}"


def _generate_decision_id(ticker: str, action: str) -> str:
    """Generate a unique decision id."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"dec_{ticker.upper()}_{action}_{ts}"


def _atomic_write(filepath: Path, data: Any, lock: threading.Lock) -> None:
    """Write JSON atomically via temp-file + rename."""
    tmp_path = filepath.with_suffix(".json.tmp")
    with lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        tmp_path.replace(filepath)


# ---------------------------------------------------------------------------
# Thesis
# ---------------------------------------------------------------------------


@dataclass
class Thesis:
    """Immutable record of an investment thesis.

    Attributes:
        thesis_id: Unique identifier ``th_{ticker}_{hash[:8]}``.
        ticker: Instrument ticker (e.g. ``"AAPL"``).
        statement: The core thesis statement.
        catalysts: Factors expected to drive the thesis.
        risks: Factors that could undermine the thesis.
        falsification_conditions: Observable conditions that would refute
            the thesis.
        created_at: ISO-8601 creation timestamp (UTC).
        status: ``active`` | ``weakened`` | ``refuted`` | ``confirmed``.
        run_id: The :class:`RunBundle` id this thesis was created from.
    """

    thesis_id: str
    ticker: str
    statement: str
    catalysts: List[str]
    risks: List[str]
    falsification_conditions: List[str]
    created_at: str
    status: str = "active"
    run_id: str = ""


# ---------------------------------------------------------------------------
# ThesisJournal
# ---------------------------------------------------------------------------


class ThesisJournal:
    """Persistent registry of investment theses.

    All theses are stored in ``THESIS_DIR / "theses.json"`` as a flat list
    of Thesis dicts.  Methods that mutate the list persist immediately.

    Usage::

        journal = ThesisJournal()
        tid = journal.create(Thesis(...))
        t = journal.get(tid)
        active = journal.list_by_ticker("AAPL")
        journal.update_status(tid, "refuted", "Earnings missed by 20%")
    """

    def __init__(self) -> None:
        _ensure_dir()
        self._path = THESIS_DIR / "theses.json"
        self._theses: Dict[str, Thesis] = {}
        self.load()

    # -- CRUD ---------------------------------------------------------------

    def create(self, thesis: Thesis) -> str:
        """Persist a new thesis and return its ``thesis_id``."""
        self._theses[thesis.thesis_id] = thesis
        self.save()
        return thesis.thesis_id

    def get(self, thesis_id: str) -> Optional[Thesis]:
        """Return the thesis with *thesis_id*, or ``None``."""
        return self._theses.get(thesis_id)

    def list_all(self) -> List[Thesis]:
        """Return every thesis in insertion order."""
        return list(self._theses.values())

    def list_by_ticker(self, ticker: str) -> List[Thesis]:
        """Return every thesis whose ticker matches (case-insensitive)."""
        t = ticker.upper()
        return [th for th in self._theses.values() if th.ticker.upper() == t]

    def update_status(self, thesis_id: str, status: str, reason: str = "") -> Thesis:
        """Update the status field of an existing thesis.

        Args:
            thesis_id: The thesis to update.
            status: New status (``active`` | ``weakened`` | ``refuted`` | ``confirmed``).
            reason: Human-readable reason for the change (stored in the
                thesis dict as ``status_reason`` for later inspection).

        Returns:
            The updated Thesis.

        Raises:
            KeyError: If *thesis_id* is not found.
        """
        th = self._theses[thesis_id]
        # Thesis is a frozen dataclass — replace with updated copy
        updated = Thesis(
            thesis_id=th.thesis_id,
            ticker=th.ticker,
            statement=th.statement,
            catalysts=list(th.catalysts),
            risks=list(th.risks),
            falsification_conditions=list(th.falsification_conditions),
            created_at=th.created_at,
            status=status,
            run_id=th.run_id,
        )
        # Attach reason as a transient attribute for introspection
        updated.__dict__["status_reason"] = reason  # type: ignore[attr-defined]
        self._theses[thesis_id] = updated
        self.save()
        return updated

    # -- Persistence --------------------------------------------------------

    def save(self) -> None:
        """Write all theses to disk as JSON."""
        data = []
        for th in self._theses.values():
            d = asdict(th)
            # Carry over status_reason if present
            reason = th.__dict__.get("status_reason")
            if reason:
                d["status_reason"] = reason
            data.append(d)
        _atomic_write(self._path, data, _thesis_write_lock)

    def load(self) -> None:
        """Load all theses from disk."""
        if not self._path.exists():
            self._theses = {}
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._theses = {}
            return

        self._theses = {}
        for item in raw:
            th = Thesis(
                thesis_id=item["thesis_id"],
                ticker=item["ticker"],
                statement=item["statement"],
                catalysts=item.get("catalysts", []),
                risks=item.get("risks", []),
                falsification_conditions=item.get("falsification_conditions", []),
                created_at=item.get("created_at", ""),
                status=item.get("status", "active"),
                run_id=item.get("run_id", ""),
            )
            reason = item.get("status_reason")
            if reason:
                th.__dict__["status_reason"] = reason
            self._theses[th.thesis_id] = th


# ---------------------------------------------------------------------------
# ThesisDelta
# ---------------------------------------------------------------------------


@dataclass
class ThesisDelta:
    """Structured diff between two analysis runs for a single thesis.

    Attributes:
        thesis_id: The thesis being evaluated.
        previous_run_id: The earlier RunBundle id.
        new_run_id: The later RunBundle id.
        fact_changes: Fact-level changes detected between runs.
            Each entry is a dict like ``{"field": "...", "before": ..., "after": ...}``.
        valuation_changes: Valuation-level changes.
        language_changes: Language / rhetoric changes in the run outputs.
        falsification_triggered: Which falsification conditions were met
            by the new run.
        overall_assessment: ``intact`` | ``weakened`` | ``strengthened`` | ``refuted``.
    """

    thesis_id: str
    previous_run_id: str
    new_run_id: str
    fact_changes: List[Dict[str, Any]] = field(default_factory=list)
    valuation_changes: List[Dict[str, Any]] = field(default_factory=list)
    language_changes: List[Dict[str, Any]] = field(default_factory=list)
    falsification_triggered: List[str] = field(default_factory=list)
    overall_assessment: str = "intact"




def format_thesis_delta_report(
    thesis: Thesis,
    delta: ThesisDelta,
) -> str:
    """Generate a human-readable auto report from a ThesisDelta.

    Produces a Markdown report with sections for fact changes, valuation
    changes, language changes, and triggered falsification conditions.
    """
    lines: List[str] = []
    lines.append(f"# Thesis Review: {thesis.ticker}")
    lines.append("")
    lines.append(f"**Statement**: {thesis.statement}")
    lines.append("")
    lines.append(f"**Assessment**: `{delta.overall_assessment}`")
    lines.append("")

    if delta.fact_changes:
        lines.append("## Fact Changes")
        lines.append("")
        for change in delta.fact_changes:
            field = change.get("field", "?")
            before = change.get("before", "—")
            after = change.get("after", "—")
            lines.append(f"- **{field}**: {before} → {after}")
        lines.append("")

    if delta.valuation_changes:
        lines.append("## Valuation Changes")
        lines.append("")
        for change in delta.valuation_changes:
            field = change.get("field", "?")
            before = change.get("before", "—")
            after = change.get("after", "—")
            lines.append(f"- **{field}**: {before} → {after}")
        lines.append("")

    if delta.language_changes:
        lines.append("## Language Changes")
        lines.append("")
        for change in delta.language_changes:
            field = change.get("field", "?")
            before = change.get("before", "—")
            after = change.get("after", "—")
            lines.append(f"- **{field}**: {before} → {after}")
        lines.append("")

    if delta.falsification_triggered:
        lines.append("## ⚠️ Falsification Triggered")
        lines.append("")
        for cond in delta.falsification_triggered:
            lines.append(f"- {cond}")
        lines.append("")
    else:
        lines.append("## Falsification")
        lines.append("")
        lines.append("No falsification conditions triggered.")
        lines.append("")

    lines.append(f"*Compared {delta.previous_run_id} → {delta.new_run_id}*")
    return "\n".join(lines)
def compute_thesis_delta(
    thesis: Thesis,
    prev_run: dict,
    new_run: dict,
) -> ThesisDelta:
    """Compute the delta between two RunBundle payloads for a thesis.

    The function compares top-level keys shared between *prev_run* and
    *new_run*, classifying differences into *fact*, *valuation*, or
    *language* buckets.  It also checks the thesis's
    ``falsification_conditions`` against the new run's content.

    Args:
        thesis: The thesis under evaluation.
        prev_run: Dict representation of the previous RunBundle.
        new_run: Dict representation of the new RunBundle.

    Returns:
        A :class:`ThesisDelta` summarising the changes.
    """
    fact_changes: List[Dict[str, Any]] = []
    valuation_changes: List[Dict[str, Any]] = []
    language_changes: List[Dict[str, Any]] = []

    # --- classify key-level diffs -----------------------------------------
    all_keys = set(prev_run.keys()) | set(new_run.keys())
    for key in sorted(all_keys):
        before = prev_run.get(key)
        after = new_run.get(key)
        if before == after:
            continue
        change = {"field": key, "before": before, "after": after}
        # Heuristic buckets
        if any(w in key.lower() for w in ("price", "valuation", "pe", "ev", "market_cap", "revenue", "earnings", "eps")):
            valuation_changes.append(change)
        elif any(w in key.lower() for w in ("sentiment", "language", "tone", "narrative", "rhetoric")):
            language_changes.append(change)
        else:
            fact_changes.append(change)

    # --- deep scan ONLY nested dict values (top level already covered) ----
    for key in sorted(all_keys):
        before = prev_run.get(key)
        after = new_run.get(key)
        if isinstance(before, dict) and isinstance(after, dict) and before != after:
            _deep_scan(before, after, fact_changes, valuation_changes, language_changes, prefix=key)

    # --- falsification check -----------------------------------------------
    new_run_text = json.dumps(new_run, default=str).lower()
    falsification_triggered: List[str] = []
    for cond in thesis.falsification_conditions:
        # A condition is "triggered" if every word of the condition appears
        # somewhere in the new run text (case-insensitive substring match
        # per token).
        tokens = [t.strip().lower() for t in cond.split() if len(t.strip()) > 1]
        if tokens and all(t in new_run_text for t in tokens):
            falsification_triggered.append(cond)

    # --- overall assessment ------------------------------------------------
    if falsification_triggered:
        overall = "refuted"
    elif valuation_changes and not fact_changes and not language_changes:
        # Pure valuation move without factual shift — signal depends on
        # direction
        overall = "intact"
    elif len(fact_changes) + len(valuation_changes) == 0:
        overall = "intact"
    elif len(language_changes) > len(fact_changes) + len(valuation_changes):
        overall = "intact"  # mostly rhetorical; thesis holds
    else:
        # Count changes to decide direction
        positive_signals = sum(
            1 for c in valuation_changes
            if isinstance(c.get("after"), (int, float))
            and isinstance(c.get("before"), (int, float))
            and c["after"] > c["before"]
        )
        negative_signals = sum(
            1 for c in valuation_changes
            if isinstance(c.get("after"), (int, float))
            and isinstance(c.get("before"), (int, float))
            and c["after"] < c["before"]
        )
        if positive_signals > negative_signals:
            overall = "strengthened"
        elif negative_signals > positive_signals:
            overall = "weakened"
        else:
            overall = "intact"

    return ThesisDelta(
        thesis_id=thesis.thesis_id,
        previous_run_id=prev_run.get("run_id", ""),
        new_run_id=new_run.get("run_id", ""),
        fact_changes=fact_changes,
        valuation_changes=valuation_changes,
        language_changes=language_changes,
        falsification_triggered=falsification_triggered,
        overall_assessment=overall,
    )


def _deep_scan(
    prev: Any,
    new: Any,
    fact_changes: List[Dict[str, Any]],
    valuation_changes: List[Dict[str, Any]],
    language_changes: List[Dict[str, Any]],
    prefix: str = "",
) -> None:
    """Recursively walk two dicts and classify leaf-level differences."""
    if not isinstance(prev, dict) or not isinstance(new, dict):
        return
    for key in sorted(set(prev.keys()) | set(new.keys())):
        path = f"{prefix}.{key}" if prefix else key
        before = prev.get(key)
        after = new.get(key)
        if before == after:
            if isinstance(before, dict) and isinstance(after, dict):
                _deep_scan(before, after, fact_changes, valuation_changes, language_changes, path)
            continue
        if isinstance(before, dict) and isinstance(after, dict):
            _deep_scan(before, after, fact_changes, valuation_changes, language_changes, path)
        else:
            change = {"field": path, "before": before, "after": after}
            if any(w in path.lower() for w in ("price", "valuation", "pe", "ev", "market_cap", "revenue", "earnings", "eps")):
                valuation_changes.append(change)
            elif any(w in path.lower() for w in ("sentiment", "language", "tone", "narrative", "rhetoric")):
                language_changes.append(change)
            else:
                fact_changes.append(change)


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


@dataclass
class Decision:
    """Immutable record of a trading or follow-up decision.

    Attributes:
        decision_id: Unique id ``dec_{ticker}_{action}_{timestamp}``.
        ticker: Instrument ticker.
        action: ``buy`` | ``sell`` | ``hold`` | ``wait``.
        reasoning: Human-readable rationale.
        evidence_run_ids: RunBundle ids that informed this decision.
        thesis_ids: Thesis ids that informed this decision.
        created_at: ISO-8601 creation timestamp (UTC).
        outcome: Optional post-hoc evaluation: ``"correct"``,
            ``"incorrect"`` or ``"neutral"``; ``None`` while pending.
        pnl_pct: Optional realised return attributed to the decision, in
            percent.
        resolved_at: ISO-8601 timestamp when the outcome was recorded.
    """

    decision_id: str
    ticker: str
    action: str
    reasoning: str
    evidence_run_ids: List[str]
    thesis_ids: List[str]
    created_at: str
    outcome: Optional[str] = None
    pnl_pct: Optional[float] = None
    resolved_at: Optional[str] = None


# ---------------------------------------------------------------------------
# DecisionLog
# ---------------------------------------------------------------------------


class DecisionLog:
    """Persistent audit trail of trading / follow-up decisions.

    All decisions are stored in ``THESIS_DIR / "decisions.json"``.

    Usage::

        log = DecisionLog()
        did = log.record(Decision(...))
        d = log.get(did)
        recent = log.list_by_ticker("AAPL")
    """

    def __init__(self) -> None:
        _ensure_dir()
        self._path = THESIS_DIR / "decisions.json"
        self._decisions: Dict[str, Decision] = {}
        self.load()

    # -- CRUD ---------------------------------------------------------------

    def record(self, decision: Decision) -> str:
        """Persist a new decision and return its ``decision_id``.

        A blank ``decision_id`` / ``created_at`` is filled in. The dashboard
        API passes blanks, and storing them verbatim made every decision
        recorded there overwrite the previous one under the key ``""``.
        """
        now = datetime.now(timezone.utc)
        if not decision.created_at:
            decision.created_at = now.isoformat()
        if not decision.decision_id:
            base = f"dec_{decision.ticker.upper()}_{decision.action}_{now.strftime('%Y%m%dT%H%M%S%f')}"
            decision_id, n = base, 1
            while decision_id in self._decisions:
                n += 1
                decision_id = f"{base}_{n}"
            decision.decision_id = decision_id
        self._decisions[decision.decision_id] = decision
        self.save()
        return decision.decision_id

    def get(self, decision_id: str) -> Optional[Decision]:
        """Return the decision with *decision_id*, or ``None``."""
        return self._decisions.get(decision_id)

    def list_by_ticker(self, ticker: str) -> List[Decision]:
        """Return every decision whose ticker matches (case-insensitive)."""
        t = ticker.upper()
        return [d for d in self._decisions.values() if d.ticker.upper() == t]

    def list_all(self) -> List[Decision]:
        """Return every decision, oldest first."""
        return sorted(self._decisions.values(), key=lambda d: d.created_at)

    def resolve(
        self, decision_id: str, outcome: str, pnl_pct: Optional[float] = None
    ) -> Optional[Decision]:
        """Record the outcome of a decision; returns it, or ``None`` if unknown."""
        if outcome not in ("correct", "incorrect", "neutral"):
            raise ValueError("outcome must be 'correct', 'incorrect' or 'neutral'")
        decision = self._decisions.get(decision_id)
        if decision is None:
            return None
        decision.outcome = outcome
        decision.pnl_pct = pnl_pct
        decision.resolved_at = datetime.now(timezone.utc).isoformat()
        self.save()
        return decision

    # -- Persistence --------------------------------------------------------

    def save(self) -> None:
        """Write all decisions to disk as JSON."""
        data = [asdict(d) for d in self._decisions.values()]
        _atomic_write(self._path, data, _decision_write_lock)

    def load(self) -> None:
        """Load all decisions from disk."""
        if not self._path.exists():
            self._decisions = {}
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._decisions = {}
            return

        self._decisions = {}
        for item in raw:
            d = Decision(
                decision_id=item["decision_id"],
                ticker=item["ticker"],
                action=item["action"],
                reasoning=item.get("reasoning", ""),
                evidence_run_ids=item.get("evidence_run_ids", []),
                thesis_ids=item.get("thesis_ids", []),
                created_at=item.get("created_at", ""),
                outcome=item.get("outcome"),
                pnl_pct=item.get("pnl_pct"),
                resolved_at=item.get("resolved_at"),
            )
            self._decisions[d.decision_id] = d

def scan_all_falsifications(self, data_dir: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Scan all active theses against the latest RunBundle for each ticker.

    For each active thesis, load the most recent RunBundle from the runs
    directory and run check_falsification against its contents. Returns
    a list of result dicts.
    """
    import json
    from pathlib import Path
    from augur.data_dir import get_data_dir

    runs_dir = Path(get_data_dir()) / "runs"
    results: List[Dict[str, Any]] = []

    for th in list(self._theses.values()):
        if th.status not in ("active", "weakened"):
            continue
        # Find latest run for this ticker
        latest = None
        for f in sorted(runs_dir.glob(f"run_{th.ticker.upper()}_*.json"), reverse=True):
            try:
                latest = json.loads(f.read_text(encoding="utf-8"))
                break
            except Exception:
                continue
        if latest is None:
            continue
        result = self.check_falsification(th.thesis_id, latest)
        result["ticker"] = th.ticker
        results.append(result)
    return results

    # -- Auto-falsification check -----------------------------------------

    def check_falsification(self, thesis_id: str, new_data: dict) -> dict:
        """Check if any falsification conditions are triggered by new data.

        Scans each falsification condition against keys in *new_data* using
        simple keyword matching. Returns a dict with triggered conditions
        and a recommendation.
        """
        th = self._theses.get(thesis_id)
        if not th:
            return {"error": "thesis not found", "thesis_id": thesis_id}

        triggered: List[str] = []
        data_text = " ".join(f"{k}={v}" for k, v in new_data.items()).lower()

        for condition in th.falsification_conditions:
            # Simple keyword matching: if all words in condition appear in data
            cond_words = condition.lower().split()
            if all(w in data_text for w in cond_words):
                triggered.append(condition)

        recommendation = "intact"
        if len(triggered) >= len(th.falsification_conditions) * 0.5:
            recommendation = "refuted"
            self.update_status(thesis_id, "refuted",
                               f"Falsification triggered: {', '.join(triggered)}")
        elif len(triggered) > 0:
            recommendation = "weakened"
            self.update_status(thesis_id, "weakened",
                               f"Falsification partially triggered: {', '.join(triggered)}")

        return {
            "thesis_id": thesis_id,
            "triggered": triggered,
            "recommendation": recommendation,
            "n_conditions": len(th.falsification_conditions),
        }

    def update_outcome(self, decision_id: str, outcome: str) -> Optional[Decision]:
        """Record the outcome of a past decision for post-hoc review."""
        d = self._decisions.get(decision_id)
        if d is None:
            return None
        updated = Decision(
            decision_id=d.decision_id, ticker=d.ticker, action=d.action,
            reasoning=d.reasoning, evidence_run_ids=list(d.evidence_run_ids),
            thesis_ids=list(d.thesis_ids), created_at=d.created_at, outcome=outcome,
        )
        self._decisions[decision_id] = updated
        self.save()
        return updated

    def get_outcomes(self, ticker: str = "") -> List[dict]:
        """Return all decisions with outcomes for review."""
        decisions = self.list_by_ticker(ticker) if ticker else list(self._decisions.values())
        return [
            {"decision_id": d.decision_id, "ticker": d.ticker, "action": d.action,
             "outcome": d.outcome, "created_at": d.created_at,
             "reasoning": d.reasoning[:80]}
            for d in decisions if d.outcome
        ]
