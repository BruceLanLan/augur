# -*- coding: utf-8 -*-
"""SEC EDGAR 13F institutional-holdings factor — Phase C, stage 2 (spec's
"阶段3") of the EDGAR data deepening.

Signal: ``institutional_flow_signal`` — a 0-10 score (5.0 = neutral)
tracking quarter-over-quarter share-count change across a curated list of
"smart money" institutions, for a curated list of tickers. Reuses
``EdgarClient`` from ``edgar_fundamentals.py``.

Why curated lists, not "any ticker held by any 13F filer"
------------------------------------------------------------
Per the spec, full-market aggregation (every 13F filer, every position) is
explicitly out of scope — thousands of filings per quarter. Tracking a
curated institution list was already the spec's plan. What real-data
investigation added: **13F holdings are identified by CUSIP, not ticker
symbol**, and SEC provides no free official CUSIP<->ticker mapping API the
way it provides ``company_tickers.json`` for CIKs (CUSIP numbers are
licensed data from CUSIP Global Services). This means "any ticker" support
is not achievable from free EDGAR data alone without a real CUSIP data
source.

The tickers in ``_TICKER_TO_CUSIP`` below are a curated large-cap set with
CUSIPs harvested directly from real, public 13F filings during
implementation (Berkshire Hathaway's and Renaissance Technologies' most
recent 13F-HR holdings tables) — CUSIP numbers for large public companies
are not secret (they appear on stock certificates, in every prospectus,
and in every 13F filing that mentions the company), so referencing a known
company's own CUSIP is not a licensing concern; bulk-redistributing a full
CUSIP master database would be. A ticker not in this table returns the
neutral default, not an error. Extending coverage means adding a verified
(ticker, CUSIP) pair here, sourced the same way.

Other real-data findings incorporated
---------------------------------------
- A single 13F filer routinely reports the *same* CUSIP across multiple
  ``infoTable`` entries within one filing — Berkshire's subsidiaries each
  report their own discretionary sleeve of a shared position (confirmed:
  Berkshire's 2026-03-31 13F has 3 separate entries for CUSIP 02005N100 /
  Ally Financial, distinguished only by their ``otherManager`` codes).
  Getting an institution's *total* position requires summing every
  ``infoTable`` entry matching the target CUSIP within one filing, not
  taking the first match.
- The raw holdings-table filename is not predictable across filings or
  filers (``form13fInfoTable.xml`` in one year, a filer-generated numeric
  name like ``53405.xml`` in another) -- discovered dynamically via
  ``EdgarClient.get_filing_index`` rather than guessed.
- The ``value`` field's unit convention changed at some point between 2017
  (thousands of dollars -- confirmed empirically: Berkshire's 2017 AAPL
  holding implies ~$143.65/share at "value in thousands", plausible for
  that period, vs. $0.14/share at face value, implausible) and 2026 (whole
  dollars -- confirmed similarly against a 2026 Ally Financial holding).
  This module doesn't use ``value`` at all (the signal is share-count
  based, sidestepping the ambiguity), but it's a real landmine documented
  here for whoever eventually wants dollar-value 13F data.

Point-in-time discipline: uses each 13F-HR's real ``filingDate`` from the
submissions index as "available from" (the legal disclosure deadline is 45
days after quarter-end, but a backtest evaluating a historical day must
only see what had actually posted to EDGAR by then, same principle as
Form 4 -- not a guessed 45-day lag).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

from augur.consensus.edgar_fundamentals import _get_client

logger = logging.getLogger(__name__)

_INFO_TABLE_NS = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}

# name -> CIK. Each verified via SEC's own company search (confirmed to
# file real 13F-HR, not 13F-NT, during implementation). Extensible: add a
# verified (name, CIK) pair, not a code change beyond this dict.
_TRACKED_INSTITUTIONS: Dict[str, int] = {
    "Berkshire Hathaway": 1067983,
    "Renaissance Technologies": 1037389,
    "Bridgewater Associates": 1350694,
    "Scion Asset Management": 1649339,
    "Pershing Square Capital Management": 1336528,
}

# ticker -> CUSIP, harvested from real 13F filings during implementation
# (see module docstring). Not exhaustive -- a curated large-cap set.
_TICKER_TO_CUSIP: Dict[str, str] = {
    "AAPL": "037833100",
    "MSFT": "594918104",
    "GOOGL": "02079K305",
    "JPM": "46625H100",
    "META": "30303M102",
    "NVDA": "67066G104",
    "TSLA": "88160R101",
    "WMT": "931142103",
    "AXP": "025816109",
    "BAC": "060505104",
    "COF": "14040H105",
    "CVX": "166764100",
    "KO": "191216100",
    "KHC": "500754106",
    "KR": "501044101",
    "MCO": "615369105",
    "NVR": "62944T105",
    "NUE": "670346105",
    "OXY": "674599105",
    "SIRI": "829933100",
    "VRSN": "92343E102",
    "DAL": "247361702",
}


def _find_holdings_table_filename(client, cik: int, accession_number: str) -> Optional[str]:
    """Return the holdings-table filename in a 13F-HR filing's directory
    (excludes the small cover-page primary_doc.xml and index/header/.txt
    boilerplate)."""
    names = client.get_filing_index(cik, accession_number)
    if not names:
        return None
    for name in names:
        lower = name.lower()
        if lower == "primary_doc.xml":
            continue
        if lower.endswith((".htm", ".html", ".txt")):
            continue
        if lower.endswith(".xml"):
            return name
    return None


def _shares_for_cusip(xml_text: str, cusip: str) -> Optional[float]:
    """Sum shares across every infoTable entry matching ``cusip`` in one
    filing's holdings table (handles multi-manager-sleeve duplication --
    see module docstring). Returns None if the CUSIP doesn't appear at
    all (institution doesn't hold this position), 0.0 is a valid "holds
    zero shares of this exact CUSIP variant" result distinct from "not
    found"."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    total = 0.0
    found = False
    for info in root.findall("ns:infoTable", _INFO_TABLE_NS):
        cusip_el = info.find("ns:cusip", _INFO_TABLE_NS)
        if cusip_el is None or not cusip_el.text or cusip_el.text.strip() != cusip:
            continue
        shares_el = info.find("ns:shrsOrPrnAmt/ns:sshPrnamt", _INFO_TABLE_NS)
        if shares_el is None or not shares_el.text:
            continue
        try:
            total += float(shares_el.text)
            found = True
        except ValueError:
            continue

    return total if found else None


def _as_of_available_13f_filings(client, cik: int, as_of_date: str) -> List[Dict[str, str]]:
    """Return every 13F-HR filing for ``cik`` whose filingDate is
    <= as_of_date, sorted most-recent-filed-first."""
    submissions = client.get_submissions(cik)
    if not submissions:
        return []
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accns = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])

    filings = [
        {"accession_number": accn, "filing_date": fdate, "report_date": rdate}
        for form, accn, fdate, rdate in zip(forms, accns, filing_dates, report_dates)
        if form == "13F-HR" and fdate <= as_of_date
    ]
    filings.sort(key=lambda f: f["filing_date"], reverse=True)
    return filings


def _institution_share_change(client, cik: int, cusip: str, as_of_date: str) -> Optional[float]:
    """Return the quarter-over-quarter share-count % change for one
    institution's holding of ``cusip``, as of ``as_of_date``. None if
    fewer than 2 as-of-available 13F-HR filings exist (can't compute a
    change), or if the CUSIP never appears in either filing."""
    filings = _as_of_available_13f_filings(client, cik, as_of_date)
    if len(filings) < 2:
        return None

    current_filing, prior_filing = filings[0], filings[1]

    def _shares_in(filing) -> Optional[float]:
        filename = _find_holdings_table_filename(client, cik, filing["accession_number"])
        if not filename:
            return None
        xml_text = client.get_filing_document(cik, filing["accession_number"], filename)
        if not xml_text:
            return None
        return _shares_for_cusip(xml_text, cusip)

    current_shares = _shares_in(current_filing)
    prior_shares = _shares_in(prior_filing)

    if current_shares is None and prior_shares is None:
        return None  # never held this position in either quarter
    current_shares = current_shares or 0.0
    prior_shares = prior_shares or 0.0

    if prior_shares == 0.0:
        return 1.0 if current_shares > 0 else 0.0  # new position -> +100%
    if current_shares == 0.0:
        return -1.0  # full exit -> -100%
    return (current_shares - prior_shares) / prior_shares


def fetch_institutional_flow_signal(ticker: str, as_of_date: str) -> Dict[str, Any]:
    """Return ``{"institutional_flow_signal": float}`` (0-10, 5.0=neutral)
    for ``ticker`` as of ``as_of_date``. Like
    ``fetch_insider_buying_signal``, always returns a usable factor value
    (neutral 5.0 default) rather than an "insufficient" flag -- this is a
    persona-consumable factor score, not a fundamentals field.

    Never raises. Returns neutral 5.0 when: ``ticker`` isn't in the
    curated CUSIP table, no tracked institution has 2+ as-of-available
    13F-HR filings, or none of them ever held the position.
    """
    try:
        cusip = _TICKER_TO_CUSIP.get(ticker.strip().upper())
        if not cusip:
            return {"institutional_flow_signal": 5.0}

        try:
            datetime.strptime(as_of_date, "%Y-%m-%d")
        except (TypeError, ValueError):
            return {"institutional_flow_signal": 5.0}

        client = _get_client()
        changes: List[float] = []
        for cik in _TRACKED_INSTITUTIONS.values():
            try:
                change = _institution_share_change(client, cik, cusip, as_of_date)
            except Exception:
                logger.debug("edgar_institutional: failed for CIK %s / %s", cik, ticker, exc_info=True)
                change = None
            if change is not None:
                changes.append(change)

        if not changes:
            return {"institutional_flow_signal": 5.0}

        avg_change = sum(changes) / len(changes)
        # Map [-1, +1] (a full exit to a brand-new full position, averaged
        # across institutions) linearly to [0, 10], clamped -- unlike the
        # Form 4 signal's tanh squash, a %-change ratio here is already
        # naturally bounded per institution (clamped at +/-100%), so a
        # linear map is sufficient and keeps the mapping easy to reason
        # about (avg_change=0 -> 5.0, avg_change=+1 -> 10.0).
        signal = max(0.0, min(10.0, 5.0 + 5.0 * avg_change))
        return {"institutional_flow_signal": round(signal, 3)}
    except Exception:
        logger.debug("edgar_institutional: unexpected failure for %s as of %s", ticker, as_of_date, exc_info=True)
        return {"institutional_flow_signal": 5.0}
