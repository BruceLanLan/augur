# -*- coding: utf-8 -*-
"""
Post-earnings Scorecard (B03) + Management Language Diff (B06).

B03 — Post-earnings Scorecard
  Compare pre-event predictions against actual post-event outcomes and
  produce a structured scorecard with verdicts and accuracy metrics.

B06 — Management Language Diff
  Analyse textual changes in management language between consecutive
  SEC filings (MD&A, Risk Factors, Outlook sections) to detect
  sentiment shifts and flag material narrative changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ============================================================================
# B03 — Post-earnings Scorecard
# ============================================================================

@dataclass
class ScorecardItem:
    """A single question-outcome pair on the post-earnings scorecard."""

    question: str              # pre-event question
    pre_event_answer: str      # what Augur predicted
    actual_outcome: str        # what actually happened
    verdict: str               # "confirmed" | "refuted" | "partially_correct" | "unknown"
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class PostEarningsScorecard:
    """Complete scorecard comparing pre-event predictions to actual outcomes."""

    ticker: str
    event_id: str
    pre_event_run_id: str
    post_event_run_id: str
    items: List[ScorecardItem] = field(default_factory=list)
    accuracy: float = 0.0
    summary: str = ""


class ScorecardBuilder:
    """Build a PostEarningsScorecard by comparing pre- and post-event run data.

    Matches pre-event questions against post-event actual outcomes by
    looking up matching keys or performing fuzzy matching on question text
    when run bundles use different naming conventions.
    """

    _VERDICT_CONFIRMED = "confirmed"
    _VERDICT_REFUTED = "refuted"
    _VERDICT_PARTIAL = "partially_correct"
    _VERDICT_UNKNOWN = "unknown"

    def build(
        self,
        pre_run: dict,
        post_run: dict,
        questions: List[str],
    ) -> PostEarningsScorecard:
        """Produce a post-earnings scorecard from two run bundles.

        Args:
            pre_run:  Pre-event run bundle dict (the prediction).
            post_run: Post-event run bundle dict (the actual outcome).
            questions: List of question strings to score.

        Returns:
            A complete ``PostEarningsScorecard``.
        """
        ticker = self._extract_ticker(pre_run, post_run)
        event_id = self._extract_event_id(pre_run)
        pre_run_id = pre_run.get("run_id", pre_run.get("id", ""))
        post_run_id = post_run.get("run_id", post_run.get("id", ""))

        pre_answers = self._extract_answers(pre_run, questions)
        post_answers = self._extract_answers(post_run, questions)

        items: List[ScorecardItem] = []
        for question in questions:
            pre_answer = pre_answers.get(question, "")
            actual = post_answers.get(question, "")
            evidence_refs = self._collect_evidence_refs(post_run, question)
            verdict = self._determine_verdict(question, pre_answer, actual)
            items.append(ScorecardItem(
                question=question,
                pre_event_answer=pre_answer,
                actual_outcome=actual,
                verdict=verdict,
                evidence_refs=evidence_refs,
            ))

        confirmed = sum(1 for it in items if it.verdict == self._VERDICT_CONFIRMED)
        total = len(items)
        accuracy = round(confirmed / total, 4) if total > 0 else 0.0

        summary = self._build_summary(items, accuracy)

        return PostEarningsScorecard(
            ticker=ticker,
            event_id=event_id,
            pre_event_run_id=pre_run_id,
            post_event_run_id=post_run_id,
            items=items,
            accuracy=accuracy,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_ticker(pre_run: dict, post_run: dict) -> str:
        """Resolve ticker from either run bundle."""
        for source in (pre_run, post_run):
            ticker = source.get("ticker", source.get("instrument", ""))
            if ticker:
                return str(ticker).upper()
        return "UNKNOWN"

    @staticmethod
    def _extract_event_id(pre_run: dict) -> str:
        """Resolve the earnings event id from pre-run metadata."""
        meta = pre_run.get("manifest", pre_run.get("metadata", {}))
        if isinstance(meta, dict):
            return meta.get("event_id", pre_run.get("event_id", ""))
        return pre_run.get("event_id", "")

    def _extract_answers(
        self,
        run: dict,
        questions: List[str],
    ) -> Dict[str, str]:
        """Pull answers from a run bundle, matching by question key.

        Looks in ``step_results``, ``claims``, and ``answers`` top-level
        keys.  Falls back to fuzzy matching when exact key lookup fails.
        """
        answers: Dict[str, str] = {}

        # Collect candidate answer pools
        candidates = self._collect_answer_pool(run)

        for question in questions:
            # Exact match on key
            if question in candidates:
                answers[question] = candidates[question]
                continue

            # Fuzzy: normalized partial match
            matched = self._fuzzy_match(question, candidates)
            if matched is not None:
                answers[question] = matched

        return answers

    @staticmethod
    def _collect_answer_pool(run: dict) -> Dict[str, str]:
        """Collect all possible answer key→value pairs from a run bundle."""
        pool: Dict[str, str] = {}

        # Direct answers map
        direct = run.get("answers", {})
        if isinstance(direct, dict):
            for k, v in direct.items():
                pool[str(k)] = str(v)

        # Step results
        for step in run.get("step_results", []):
            if not isinstance(step, dict):
                continue
            name = step.get("step_name", step.get("name", ""))
            content = step.get("content", step.get("result", ""))
            if name and content:
                pool[name] = str(content)

        # Claims
        for claim in run.get("claims", []):
            if not isinstance(claim, dict):
                continue
            q = claim.get("question", claim.get("claim", ""))
            a = claim.get("answer", claim.get("prediction", ""))
            if q and a:
                pool[str(q)] = str(a)

        return pool

    def _fuzzy_match(
        self,
        question: str,
        candidates: Dict[str, str],
    ) -> Optional[str]:
        """Return the answer whose key best matches *question* by token overlap.

        Returns ``None`` when no key shares at least 2 significant tokens.
        """
        q_tokens = self._tokenize(question)
        if len(q_tokens) < 2:
            return None

        best_key: Optional[str] = None
        best_score = 0

        for key, value in candidates.items():
            k_tokens = self._tokenize(key)
            overlap = len(q_tokens & k_tokens)
            if overlap > best_score:
                best_score = overlap
                best_key = key

        if best_key and best_score >= 2:
            return candidates[best_key]
        return None

    @staticmethod
    def _tokenize(text: str) -> set:
        """Tokenize text into a set of lowercased alphanumeric tokens."""
        return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))

    @staticmethod
    def _collect_evidence_refs(run: dict, question: str) -> List[str]:
        """Collect evidence references related to *question* from the run."""
        refs: List[str] = []
        for ev in run.get("evidence", run.get("evidence_items", [])):
            if not isinstance(ev, dict):
                continue
            ev_id = ev.get("evidence_id", ev.get("id", ""))
            if ev_id:
                refs.append(ev_id)
        return refs

    # ------------------------------------------------------------------
    # Verdict logic
    # ------------------------------------------------------------------

    def _determine_verdict(
        self,
        question: str,
        pre_answer: str,
        actual: str,
    ) -> str:
        """Determine verdict by comparing pre-event answer to actual outcome.

        Returns one of ``"confirmed"``, ``"refuted"``,
        ``"partially_correct"``, or ``"unknown"``.
        """
        if not pre_answer or not actual:
            return self._VERDICT_UNKNOWN

        pre_norm = pre_answer.strip().lower()
        actual_norm = actual.strip().lower()

        # Exact match
        if pre_norm == actual_norm:
            return self._VERDICT_CONFIRMED

        # Numeric comparison when both sides are parseable numbers
        pre_num = self._parse_number(pre_answer)
        actual_num = self._parse_number(actual)
        if pre_num is not None and actual_num is not None:
            return self._compare_numeric(pre_num, actual_num)

        # Directional comparison
        pre_dir = self._extract_direction(pre_norm)
        actual_dir = self._extract_direction(actual_norm)
        if pre_dir is not None and actual_dir is not None:
            return (
                self._VERDICT_CONFIRMED
                if pre_dir == actual_dir
                else self._VERDICT_REFUTED
            )

        # Partial: significant token overlap
        pre_tokens = self._tokenize(pre_answer)
        actual_tokens = self._tokenize(actual)
        overlap = len(pre_tokens & actual_tokens)
        if overlap >= max(len(pre_tokens), len(actual_tokens)) * 0.5:
            return self._VERDICT_PARTIAL

        return self._VERDICT_REFUTED

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        """Parse a number from text, handling common formatting."""
        cleaned = text.strip().replace(",", "").replace("%", "").replace("$", "")
        cleaned = re.sub(r"\s*billion", "e9", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*million", "e6", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*thousand", "e3", cleaned, flags=re.IGNORECASE)
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _compare_numeric(pre: float, actual: float) -> str:
        """Compare two numeric values with a 5% tolerance band."""
        if pre == 0 and actual == 0:
            return "confirmed"
        if pre == 0 or actual == 0:
            return "confirmed" if abs(pre - actual) < 1e-9 else "refuted"
        deviation = abs((actual - pre) / abs(pre))
        if deviation <= 0.05:
            return "confirmed"
        if deviation <= 0.20:
            return "partially_correct"
        return "refuted"

    @staticmethod
    def _extract_direction(text: str) -> Optional[str]:
        """Extract directional signal from text.

        Returns ``"up"``, ``"down"``, ``"flat"``, or ``None``.
        """
        up_words = {"up", "increase", "rose", "grew", "growth", "beat",
                     "outperform", "raised", "higher", "strong", "positive",
                     "above", "exceed", "bullish", "outperformed"}
        down_words = {"down", "decrease", "fell", "decline", "declined",
                      "miss", "underperform", "lowered", "lower", "weak",
                      "negative", "below", "bearish", "underperformed"}
        flat_words = {"flat", "unchanged", "inline", "in-line", "stable",
                      "met", "neutral"}

        tokens = set(re.findall(r"[a-zA-Z]+", text))
        if tokens & up_words and not tokens & down_words:
            return "up"
        if tokens & down_words and not tokens & up_words:
            return "down"
        if tokens & flat_words:
            return "flat"
        return None

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary(items: List[ScorecardItem], accuracy: float) -> str:
        confirmed = sum(1 for it in items if it.verdict == "confirmed")
        refuted = sum(1 for it in items if it.verdict == "refuted")
        partial = sum(1 for it in items if it.verdict == "partially_correct")
        unknown = sum(1 for it in items if it.verdict == "unknown")

        parts = [f"Accuracy: {accuracy:.1%} ({confirmed}/{len(items)} confirmed)"]
        if refuted:
            parts.append(f"{refuted} refuted")
        if partial:
            parts.append(f"{partial} partially correct")
        if unknown:
            parts.append(f"{unknown} unknown")
        return "; ".join(parts)


# ============================================================================
# B06 — Management Language Diff
# ============================================================================

@dataclass
class LanguageChange:
    """A detected change in management language between two filing snapshots."""

    section: str              # "MD&A", "Risk Factors", "Outlook"
    phrase_before: str
    phrase_after: str
    sentiment_shift: str      # "more_bullish" | "more_bearish" | "more_cautious" | "neutral"
    material: bool = False


@dataclass
class LanguageDiffReport:
    """Structured report of language changes between consecutive filings."""

    ticker: str
    changes: List[LanguageChange] = field(default_factory=list)
    overall_sentiment_shift: str = "neutral"


class LanguageDiffAnalyzer:
    """Analyse management language changes between two SEC filing texts.

    Compares section-level text (MD&A, Risk Factors, Outlook) to detect
    added, removed, or reworded phrases and evaluates sentiment shifts
    using curated bullish / bearish / cautious word lists.
    """

    # Sections we specifically care about for language diff
    _KEY_SECTIONS = ["MD&A", "Risk Factors", "Outlook"]

    # ------------------------------------------------------------------
    # Sentiment lexicons
    # ------------------------------------------------------------------

    _BULLISH_WORDS: set = {
        "accelerat", "achieved", "best", "boost", "confident", "demand",
        "expand", "expansion", "grew", "growth", "improve", "improved",
        "improvement", "increase", "increased", "innovation", "leader",
        "leadership", "opportunit", "optimistic", "outperform",
        "record", "robust", "strong", "strength", "success", "superior",
        "upside", "upward",
    }

    _BEARISH_WORDS: set = {
        "adverse", "challeng", "competitive", "cyclical", "decline",
        "declined", "decrease", "decreased", "difficult", "disruption",
        "downturn", "headwind", "impairment", "loss", "lower",
        "negativ", "pressure", "recession", "slowdown", "soft",
        "uncertaint", "volatil", "weak", "weaken", "worse",
    }

    _CAUTIOUS_WORDS: set = {
        "although", "believe", "could", "expect", "however", "likely",
        "may", "might", "potential", "potentially", "subject to",
        "uncertain", "unknown", "volatile",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        prev_filing_text: dict,
        new_filing_text: dict,
    ) -> LanguageDiffReport:
        """Compare two filing text dicts and produce a language diff report.

        Args:
            prev_filing_text: Dict mapping section name → text (previous filing).
            new_filing_text:  Dict mapping section name → text (new filing).

        Returns:
            A ``LanguageDiffReport`` with all detected changes and an
            overall sentiment shift assessment.
        """
        ticker = new_filing_text.get("ticker", prev_filing_text.get("ticker", ""))
        if isinstance(ticker, str) and ticker:
            ticker = ticker.upper()

        changes: List[LanguageChange] = []

        for section in self._KEY_SECTIONS:
            prev_text = self._section_text(prev_filing_text, section)
            new_text = self._section_text(new_filing_text, section)

            if not prev_text and not new_text:
                continue

            section_changes = self._diff_section(section, prev_text, new_text)
            changes.extend(section_changes)

        overall = self._compute_overall_sentiment(changes)

        return LanguageDiffReport(
            ticker=ticker or "UNKNOWN",
            changes=changes,
            overall_sentiment_shift=overall,
        )

    # Escalation word pairs: tentative → definitive
    _ESCALATION_PAIRS = [
        ("may", "will"),
        ("could", "will"),
        ("might", "will"),
        ("expects", "committed"),
        ("believes", "confirms"),
        ("considers", "plans to"),
        ("evaluating", "implementing"),
        ("possible", "certain"),
    ]

    def detect_escalation(self, prev_text: str, new_text: str) -> List[Dict[str, str]]:
        """Detect wording escalations from tentative to definitive language.

        Args:
            prev_text: Previous filing section text.
            new_text: New filing section text.

        Returns:
            List of escalation dicts: {before_phrase, after_phrase, kind}.
        """
        escalations: List[Dict[str, str]] = []
        if not prev_text or not new_text:
            return escalations

        prev_lower = prev_text.lower()
        new_lower = new_text.lower()

        for tentative, definitive in self._ESCALATION_PAIRS:
            # Find tentative phrases in prev and definitive in new
            if tentative in prev_lower and definitive in new_lower:
                # Extract surrounding context (simplified)
                idx_p = prev_lower.find(tentative)
                idx_n = new_lower.find(definitive)
                ctx_p = prev_text[max(0, idx_p - 30):idx_p + len(tentative) + 30]
                ctx_n = new_text[max(0, idx_n - 30):idx_n + len(definitive) + 30]
                escalations.append({
                    "before_phrase": ctx_p.strip(),
                    "after_phrase": ctx_n.strip(),
                    "kind": f"{tentative} → {definitive}",
                })

        return escalations

    def detect_sentiment_words(self, text: str) -> Dict[str, int]:
        """Count bullish, bearish, and cautious word stems in *text*.

        Returns a dict with keys ``"bullish"``, ``"bearish"``, ``"cautious"``
        and integer counts.
        """
        if not text:
            return {"bullish": 0, "bearish": 0, "cautious": 0}

        lower = text.lower()
        words = set(re.findall(r"[a-z]+", lower))

        bullish = sum(1 for bw in self._BULLISH_WORDS if any(w.startswith(bw) for w in words))
        bearish = sum(1 for bw in self._BEARISH_WORDS if any(w.startswith(bw) for w in words))
        cautious = sum(1 for cw in self._CAUTIOUS_WORDS if cw in lower or any(w.startswith(cw) for w in words))

        return {"bullish": bullish, "bearish": bearish, "cautious": cautious}

    # ------------------------------------------------------------------
    # Section diff
    # ------------------------------------------------------------------

    def _diff_section(
        self,
        section: str,
        prev_text: str,
        new_text: str,
    ) -> List[LanguageChange]:
        """Produce LanguageChange entries for one section."""
        changes: List[LanguageChange] = []

        # Phrase-level diff: find sentences that were added or removed
        prev_sentences = self._split_sentences(prev_text)
        new_sentences = self._split_sentences(new_text)

        prev_set = {s.strip() for s in prev_sentences if s.strip()}
        new_set = {s.strip() for s in new_sentences if s.strip()}

        added = new_set - prev_set
        removed = prev_set - new_set

        # Match added/removed pairs by similarity as potential replacements
        matched_pairs = self._match_replacements(removed, added)

        for before, after in matched_pairs:
            before_sent = self._classify_sentiment(before)
            after_sent = self._classify_sentiment(after)
            shift = self._sentiment_shift(before_sent, after_sent)
            material = self._is_material_change(before, after, section)
            changes.append(LanguageChange(
                section=section,
                phrase_before=before,
                phrase_after=after,
                sentiment_shift=shift,
                material=material,
            ))

            # Remove matched items from the free pools
            removed.discard(before)
            added.discard(after)

        # Unmatched removals → language removed (shift to neutral)
        for r in removed:
            before_sent = self._classify_sentiment(r)
            material = self._is_material_removal(r, section)
            changes.append(LanguageChange(
                section=section,
                phrase_before=r,
                phrase_after="[removed]",
                sentiment_shift=self._sentiment_shift(before_sent, "neutral"),
                material=material,
            ))

        # Unmatched additions → new language added
        for a in added:
            after_sent = self._classify_sentiment(a)
            material = self._is_material_addition(a, section)
            changes.append(LanguageChange(
                section=section,
                phrase_before="[not present]",
                phrase_after=a,
                sentiment_shift=self._sentiment_shift("neutral", after_sent),
                material=material,
            ))

        return changes

    # ------------------------------------------------------------------
    # Sentence helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences on ``.`` ``!`` ``?`` boundaries."""
        if not text:
            return []
        # Simple sentence split; production would use a proper sentence tokenizer
        raw = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in raw if s.strip() and len(s.strip()) > 5]

    @staticmethod
    def _match_replacements(
        removed: set,
        added: set,
    ) -> List[Tuple[str, str]]:
        """Pair up removed/added sentences that are likely replacements."""
        pairs: List[Tuple[str, str]] = []
        used_removed: set = set()
        used_added: set = set()

        for r in sorted(removed):
            best_match: Optional[str] = None
            best_score = 0
            for a in sorted(added):
                if a in used_added:
                    continue
                score = LanguageDiffAnalyzer._similarity(r, a)
                if score > best_score and score > 0.4:
                    best_score = score
                    best_match = a
            if best_match is not None:
                pairs.append((r, best_match))
                used_removed.add(r)
                used_added.add(best_match)

        return pairs

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Token-overlap similarity between two strings (Jaccard-like)."""
        a_tokens = set(re.findall(r"[a-zA-Z0-9]+", a.lower()))
        b_tokens = set(re.findall(r"[a-zA-Z0-9]+", b.lower()))
        if not a_tokens or not b_tokens:
            return 0.0
        intersection = len(a_tokens & b_tokens)
        union = len(a_tokens | b_tokens)
        return intersection / union

    # ------------------------------------------------------------------
    # Sentiment classification
    # ------------------------------------------------------------------

    def _classify_sentiment(self, text: str) -> str:
        """Classify text sentiment as ``"bullish"``, ``"bearish"``, ``"cautious"``, or ``"neutral"``."""
        counts = self.detect_sentiment_words(text)
        b = counts["bullish"]
        h = counts["bearish"]
        c = counts["cautious"]

        if b > h and b > c:
            return "bullish"
        if h > b and h > c:
            return "bearish"
        if c > b and c > h:
            return "cautious"
        if b == h == c == 0:
            return "neutral"
        # Tie-breaking: bullish > bearish > cautious > neutral
        if b == h and b > c:
            return "bullish"
        return "neutral"

    @staticmethod
    def _sentiment_shift(before: str, after: str) -> str:
        """Compute shift label from before→after sentiment classification."""
        if before == after:
            return "neutral"

        bullish_order = {"bullish": 3, "cautious": 2, "neutral": 1, "bearish": 0}
        b = bullish_order.get(before, 1)
        a = bullish_order.get(after, 1)

        if a > b:
            return "more_bullish"
        if a < b:
            return "more_bearish"
        return "neutral"

    # ------------------------------------------------------------------
    # Materiality
    # ------------------------------------------------------------------

    @staticmethod
    def _is_material_change(before: str, after: str, section: str) -> bool:
        """Determine whether a replacement is material."""
        sim = LanguageDiffAnalyzer._similarity(before, after)
        # Low-similarity replacements in key sections are material
        if LanguageDiffAnalyzer._is_material_section(section) and sim < 0.7:
            return True
        # Large text change
        len_diff = abs(len(after) - len(before))
        if len_diff > 100:
            return True
        return False

    @staticmethod
    def _is_material_removal(text: str, section: str) -> bool:
        """Determine whether a removal is material."""
        if not LanguageDiffAnalyzer._is_material_section(section):
            return False
        return len(text.split()) > 15

    @staticmethod
    def _is_material_addition(text: str, section: str) -> bool:
        """Determine whether an addition is material."""
        if not LanguageDiffAnalyzer._is_material_section(section):
            return False
        return len(text.split()) > 15

    @staticmethod
    def _is_material_section(section: str) -> bool:
        """Check if a section name indicates material content."""
        material_keywords = ["risk", "md&a", "outlook", "guidance", "legal"]
        section_lower = section.lower()
        return any(kw in section_lower for kw in material_keywords)

    # ------------------------------------------------------------------
    # Overall sentiment
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_overall_sentiment(changes: List[LanguageChange]) -> str:
        """Aggregate per-change sentiment shifts into an overall label."""
        if not changes:
            return "neutral"

        tally: Dict[str, int] = {
            "more_bullish": 0,
            "more_bearish": 0,
            "more_cautious": 0,
            "neutral": 0,
        }
        for ch in changes:
            shift = ch.sentiment_shift
            if shift in tally:
                tally[shift] += 1

        # Count "more_cautious" as mildly bearish for net calculation
        net = (tally["more_bullish"]
               - tally["more_bearish"]
               - tally["more_cautious"] * 0.5)

        if net >= 2:
            return "more_bullish"
        if net <= -2:
            return "more_bearish"
        if net < 0:
            return "more_cautious"
        return "neutral"

    # ------------------------------------------------------------------
    # Section text extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _section_text(filing: dict, section: str) -> str:
        """Extract section text from a filing dict with flexible key matching."""
        # Direct key match
        if section in filing:
            return str(filing[section])

        # Look inside a "sections" sub-dict
        sections = filing.get("sections", {})
        if isinstance(sections, dict):
            if section in sections:
                return str(sections[section])
            # Case-insensitive fallback
            for k, v in sections.items():
                if k.lower() == section.lower():
                    return str(v)

        # Top-level case-insensitive fallback
        for k, v in filing.items():
            if k.lower() == section.lower():
                return str(v)

        return ""
