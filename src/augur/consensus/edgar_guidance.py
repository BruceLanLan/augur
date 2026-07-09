# -*- coding: utf-8 -*-
"""
augur.consensus.edgar_guidance - EDGAR Phase 4: LLM-extracted management guidance (default OFF)

Pulls the MD&A (Management's Discussion and Analysis) section from a
company's most recent 10-K/10-Q and asks an LLM to extract: management
outlook sentiment, any explicit forward-looking guidance numbers, and a
brief note on risk-factor language. See
docs/superpowers/specs/2026-07-03-edgar-fundamentals-design.md §4 for the
approved design.

Unlike stages 1-3 (edgar_fundamentals.py, edgar_insider.py,
edgar_institutional.py), this stage is NOT wired into the automatic
analyze()/consensus pipeline and is NOT a persona-consumable
``metadata.factors`` entry. It is an on-demand, opt-in tool only (spec:
"阶段 4 不做实时监控/推送，只在用户主动分析时按需抽取") -- reachable via
``fetch_management_guidance()`` directly or ``augur guidance TICKER``.

Cost/latency control
---------------------
Default OFF. Set ``AUGUR_EDGAR_GUIDANCE_EXTRACTION=1`` (or "true"/"yes")
to opt in -- matches the truthy-string convention already used by
``AUGUR_SKIP_MACRO_FETCH`` (macro_features.py). When not opted in, this
module makes zero network calls (not even an EDGAR fetch) and returns
immediately.

Each filing's extraction result is cached permanently to
``~/.augur/edgar_cache/guidance_<accession>.json`` (no TTL -- a filed
10-K/10-Q never changes), keyed by accession number, so the LLM is never
called twice for the same filing.

Dependency isolation: reuses ``augur.llm_client``'s existing
OpenAI-compatible client construction (same OPENAI_API_KEY/
OPENAI_BASE_URL env vars already used by persona chat) rather than adding
a second LLM config surface. Missing ``llm`` extras or missing API key is
a graceful "unavailable" return, never an exception, matching every other
EDGAR module's "never raises" convention.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CACHE_DIR = Path.home() / ".augur" / "edgar_cache"

_DEFAULT_GUIDANCE_MODEL = "gpt-4o-mini"  # cheaper than chat's gpt-4o default; extraction, not conversation
_MAX_MDNA_CHARS = 40_000  # bound LLM cost/latency; real MD&A sections observed at ~15-25KB

# (form, start_item_pattern, end_item_pattern) -- checked in order, first
# form-type match wins. 10-K's MD&A is Part II Item 7 (ending at Item 7A,
# or Item 8 if a filer omits the market-risk item); 10-Q's MD&A is Part I
# Item 2 (ending at Item 3). Confirmed against real AAPL 10-K/10-Q filings.
_SECTION_BOUNDARIES = {
    "10-K": (r"Item\s+7\.", [r"Item\s+7A\.", r"Item\s+8\."]),
    "10-Q": (r"Item\s+2\.", [r"Item\s+3\."]),
}


def _is_enabled() -> bool:
    return os.environ.get("AUGUR_EDGAR_GUIDANCE_EXTRACTION", "").strip().lower() in ("1", "true", "yes")


def _guidance_cache_path(accession_number: str) -> Path:
    accn_key = accession_number.replace("-", "")
    return _CACHE_DIR / f"guidance_{accn_key}.json"


def _load_cached_guidance(accession_number: str) -> Optional[Dict[str, Any]]:
    path = _guidance_cache_path(accession_number)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("guidance cache unreadable for accession %s", accession_number, exc_info=True)
        return None


def _save_cached_guidance(accession_number: str, result: Dict[str, Any]) -> None:
    path = _guidance_cache_path(accession_number)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("failed to persist guidance cache for accession %s", accession_number, exc_info=True)


def _html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    raw = soup.get_text(separator="\n")
    lines = [line.strip() for line in raw.split("\n") if line.strip()]
    return "\n".join(lines)


def _extract_mdna_section(text: str, form: str) -> Optional[str]:
    """Locate the real MD&A section body, distinguishing it from short
    table-of-contents / cross-reference mentions of the same "Item N."
    label elsewhere in the document.

    Real-data finding (AAPL 10-K/10-Q, both confirmed): a filing mentions
    its own MD&A item number several times -- a TOC entry, cross-references
    in other sections, and the actual section heading -- but only the real
    section heading is followed by thousands of characters of prose before
    the next item's heading. TOC/cross-reference mentions sit within a few
    hundred characters of neighboring text. So: among every (start-label,
    next end-label) pair, the one with the largest gap is the real section.
    """
    boundaries = _SECTION_BOUNDARIES.get(form)
    if boundaries is None:
        return None
    start_pattern, end_patterns = boundaries

    start_matches = list(re.finditer(start_pattern, text, re.IGNORECASE))
    end_matches = sorted(
        (m.start() for pat in end_patterns for m in re.finditer(pat, text, re.IGNORECASE))
    )
    if not start_matches or not end_matches:
        return None

    best_gap = -1
    best_span = None
    for sm in start_matches:
        start = sm.start()
        # nearest end match strictly after this start
        end = next((e for e in end_matches if e > start), None)
        if end is None:
            continue
        gap = end - start
        if gap > best_gap:
            best_gap = gap
            best_span = (start, end)

    if best_span is None:
        return None

    section = text[best_span[0]:best_span[1]].strip()
    if len(section) > _MAX_MDNA_CHARS:
        section = section[:_MAX_MDNA_CHARS]
    return section or None


def _most_recent_filing(client, cik: int, as_of_date: Optional[str]) -> Optional[Dict[str, str]]:
    """Return {"form", "accessionNumber", "primaryDocument", "filingDate"}
    for the most recent 10-K or 10-Q filed on or before as_of_date (or the
    most recent overall if as_of_date is None), preferring whichever form
    was filed most recently."""
    submissions = client.get_submissions(cik)
    if not submissions:
        return None
    try:
        recent = submissions["filings"]["recent"]
        forms = recent["form"]
        accns = recent["accessionNumber"]
        docs = recent["primaryDocument"]
        dates = recent["filingDate"]
    except (KeyError, TypeError):
        return None

    for i, form in enumerate(forms):
        if form not in _SECTION_BOUNDARIES:
            continue
        filing_date = dates[i]
        if as_of_date and filing_date > as_of_date:
            continue
        return {
            "form": form,
            "accessionNumber": accns[i],
            "primaryDocument": docs[i],
            "filingDate": filing_date,
        }
    return None


_EXTRACTION_PROMPT = """You are a financial analyst extracting structured signal from a 10-K/10-Q Management's Discussion and Analysis (MD&A) section. Read the text below and respond with ONLY a JSON object (no markdown fences, no commentary) with exactly these keys:

{{
  "outlook_sentiment": "positive" | "negative" | "neutral",
  "outlook_summary": "1-2 sentence summary of management's forward-looking tone",
  "guidance_numbers": ["specific forward-looking numeric guidance statements found verbatim or closely paraphrased; empty list if none given"],
  "risk_notes": "brief note on notable risk-factor language in this text, or empty string if none"
}}

Ticker: {ticker}

MD&A text:
{mdna_text}
"""


def _call_llm_extraction(mdna_text: str, ticker: str) -> Optional[Dict[str, Any]]:
    from augur.llm_client import _get_client, is_llm_available

    if not is_llm_available():
        return None
    client = _get_client()
    if client is None:
        return None

    model = os.environ.get("AUGUR_GUIDANCE_MODEL", "").strip() or _DEFAULT_GUIDANCE_MODEL
    prompt = _EXTRACTION_PROMPT.format(ticker=ticker.upper(), mdna_text=mdna_text)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
    except Exception as e:
        logger.warning("guidance LLM extraction failed for %s: %s", ticker, e)
        return None

    sentiment = data.get("outlook_sentiment")
    if sentiment not in ("positive", "negative", "neutral"):
        sentiment = "neutral"
    guidance_numbers = data.get("guidance_numbers")
    if not isinstance(guidance_numbers, list):
        guidance_numbers = []

    return {
        "outlook_sentiment": sentiment,
        "outlook_summary": str(data.get("outlook_summary") or ""),
        "guidance_numbers": [str(g) for g in guidance_numbers],
        "risk_notes": str(data.get("risk_notes") or ""),
    }


def fetch_management_guidance(ticker: str, as_of_date: Optional[str] = None) -> Dict[str, Any]:
    """Main entry point. Returns a dict; never raises.

    Disabled (default) or LLM unavailable: ``{"available": False, "reason": str}``.
    Success: ``{"available": True, "form": ..., "filing_date": ..., "accession_number": ...,
    "outlook_sentiment": ..., "outlook_summary": ..., "guidance_numbers": [...], "risk_notes": ...,
    "cache_hit": bool}``.
    """
    if not _is_enabled():
        return {
            "available": False,
            "reason": "disabled — set AUGUR_EDGAR_GUIDANCE_EXTRACTION=1 to opt in "
                       "(this stage makes paid LLM API calls)",
        }

    from augur.llm_client import is_llm_available
    if not is_llm_available():
        return {
            "available": False,
            "reason": "LLM backend unavailable — set OPENAI_API_KEY and "
                       "install the 'llm' extra: pip install 'augur-agents[llm]'",
        }

    from augur.optional_deps import is_available as _is_pkg_available
    if not _is_pkg_available("bs4"):
        return {
            "available": False,
            "reason": "beautifulsoup4 not installed — install the 'llm' extra: "
                       "pip install 'augur-agents[llm]'",
        }

    try:
        from augur.consensus.edgar_fundamentals import _get_client as _get_edgar_client
        client = _get_edgar_client()

        cik = client.get_cik(ticker)
        if cik is None:
            return {"available": False, "reason": f"no EDGAR CIK found for {ticker} (non-US ticker?)"}

        filing = _most_recent_filing(client, cik, as_of_date)
        if filing is None:
            return {"available": False, "reason": f"no 10-K/10-Q found for {ticker} as of {as_of_date or 'now'}"}

        accession_number = filing["accessionNumber"]
        cached = _load_cached_guidance(accession_number)
        if cached is not None:
            result = dict(cached)
            result["cache_hit"] = True
            return result

        html = client.get_filing_document(cik, accession_number, filing["primaryDocument"])
        if html is None:
            return {"available": False, "reason": f"failed to fetch filing document for {ticker}"}

        text = _html_to_text(html)
        mdna = _extract_mdna_section(text, filing["form"])
        if mdna is None:
            return {"available": False, "reason": f"could not locate MD&A section in {filing['form']} for {ticker}"}

        extracted = _call_llm_extraction(mdna, ticker)
        if extracted is None:
            return {"available": False, "reason": "LLM extraction failed"}

        result = {
            "available": True,
            "form": filing["form"],
            "filing_date": filing["filingDate"],
            "accession_number": accession_number,
            "cache_hit": False,
            **extracted,
        }
        _save_cached_guidance(accession_number, result)
        return result
    except Exception as e:
        logger.warning("fetch_management_guidance failed for %s: %s", ticker, e, exc_info=True)
        return {"available": False, "reason": f"unexpected error: {e}"}
