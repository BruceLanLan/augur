# -*- coding: utf-8 -*-
"""
Capability implementations used by the skill runner.

Every capability a built-in skill's workflow ``uses`` is implemented here by
an existing Augur function — there are no stubs. Each handler has the
signature ``handler(inputs, upstream) -> dict``:

* ``inputs``: the skill-level inputs (always includes ``ticker``).
* ``upstream``: step id -> output dict of the steps it ``needs``.

Outputs are JSON-serialisable except keys starting with ``_``, which carry
in-memory objects between steps and are stripped before persistence.
Evidence produced by a step goes under ``evidence_items`` (EvidenceItem v1
dicts) so the RunBundle, exports and the disagreement map can cite it.
"""

from __future__ import annotations

import dataclasses
import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upstream_value(upstream: Dict[str, Dict[str, Any]], key: str) -> Any:
    for output in upstream.values():
        if key in output:
            return output[key]
    return None


def _sec_evidence(ticker: str, metric: str, value: float, fiscal_year_end: str,
                  accession: str, filed: str, cik: Optional[int]) -> Dict[str, Any]:
    from augur.schemas.evidence import generate_evidence_id

    locator = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K"
               if cik else "https://www.sec.gov/edgar/search/")
    content = f"sec_edgar:{ticker}:{metric}:{fiscal_year_end}:{accession}:{value}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return {
        "evidence_id": generate_evidence_id("sec_edgar", content_hash),
        "source": "sec_edgar",
        "source_locator": f"{locator} (accession {accession})",
        "content_hash": content_hash,
        "instrument": ticker,
        "metric": metric,
        "value": value,
        "unit": "USD" if metric not in ("eps_diluted", "shares_outstanding") else None,
        "currency": "USD",
        "effective_at": f"{fiscal_year_end}T00:00:00+00:00",
        "available_at": f"{filed}T00:00:00+00:00",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",
        "coverage": 1.0,
        "missing": False,
        "degraded": False,
        "metadata": {"form": "10-K", "accession": accession, "fiscal_year_end": fiscal_year_end},
    }


def _annual_with_evidence(ticker: str, years: int) -> Dict[str, Any]:
    from augur.consensus.edgar_fundamentals import _get_client, fetch_annual_financials

    ticker = ticker.upper()
    periods = fetch_annual_financials(ticker, years=years)
    if not periods:
        raise LookupError(f"no annual SEC financials for {ticker} (non-US listing or no XBRL 10-K data)")
    cik = _get_client().get_cik(ticker)
    evidence: List[Dict[str, Any]] = []
    for period in periods:
        for metric, value in period["metrics"].items():
            evidence.append(_sec_evidence(ticker, metric, value, period["fiscal_year_end"],
                                          period["accession"], period["filed"], cik))
    return {"periods": periods, "evidence_items": evidence}


# ---------------------------------------------------------------------------
# earnings-prep
# ---------------------------------------------------------------------------

def collect_earnings_evidence(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Live market context + evidence, and the next calendar event if one is recorded."""
    from augur.data import fetch_market_context
    from augur.earnings import EarningsEventService

    ticker = inputs["ticker"].upper()
    ctx = fetch_market_context(ticker)
    events = EarningsEventService().detect_events([ticker], lookahead_days=120)
    event = dataclasses.asdict(events[0]) if events else None
    evidence = [e for e in (getattr(ctx, "evidence_items", None) or [])
                if isinstance(e, dict) and e.get("evidence_id")]
    return {
        "_ctx": ctx,
        "data_source": getattr(ctx, "data_source", "unknown"),
        "event": event or {"note": "no entry in the local earnings calendar "
                                   "(get_data_dir()/earnings_calendar.json)"},
        "field_availability": dict(getattr(ctx, "field_availability", None) or {}),
        "evidence_items": evidence,
    }


def analyze_personas(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """All personas on the collected context, plus the weighted consensus."""
    from augur.registry import AgentRegistry, DecisionCoordinator

    ctx = _upstream_value(upstream, "_ctx")
    if ctx is None:
        raise ValueError("personas.analyze needs a market context from an earlier step")
    coordinator = DecisionCoordinator(AgentRegistry())
    responses = coordinator.analyze_with_all(ctx)
    consensus = coordinator.get_consensus(responses, ticker=inputs["ticker"].upper(), context=ctx)
    return {
        "personas": {
            aid: {
                "agent_name": r.agent_name, "signal": r.signal.value, "score": r.score,
                "confidence": r.confidence, "factors": dict((r.metadata or {}).get("factors") or {}),
                "key_findings": list(r.key_findings[:3]), "risks": list(r.risks[:3]),
            }
            for aid, r in responses.items()
        },
        "consensus": {
            "signal": consensus.signal.value, "score": round(consensus.score, 2),
            "confidence": round(consensus.confidence, 3),
            "kelly_pct": (consensus.metadata or {}).get("position_sizing", {}).get("position_pct"),
        },
    }


def compare_with_previous_run(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Consensus and per-persona signal changes versus the newest saved run for the ticker."""
    from augur.run_tracker import extract_persona_results, latest_run_id, load_run_bundle_dict

    ticker = inputs["ticker"].upper()
    current = _upstream_value(upstream, "personas") or {}
    current_consensus = _upstream_value(upstream, "consensus") or {}
    previous_id = latest_run_id(ticker, require_persona_analysis=True)
    if not previous_id:
        return {"previous_run_id": None, "diffs": [], "note": f"no earlier run for {ticker} to compare with"}

    bundle = load_run_bundle_dict(previous_id)
    prev_personas, prev_consensus = extract_persona_results(bundle)

    diffs: List[Dict[str, Any]] = []
    if prev_consensus and current_consensus:
        before, after = prev_consensus.get("score"), current_consensus.get("score")
        if isinstance(before, (int, float)) and isinstance(after, (int, float)) and abs(after - before) >= 0.005:
            diffs.append({"field": "consensus.score", "before": round(before, 2), "after": round(after, 2),
                          "delta": round(after - before, 2)})
        if prev_consensus.get("signal") != current_consensus.get("signal"):
            diffs.append({"field": "consensus.signal", "before": prev_consensus.get("signal"),
                          "after": current_consensus.get("signal")})
    for aid, now in sorted(current.items()):
        was = prev_personas.get(aid)
        if was and was.get("signal") != now.get("signal"):
            diffs.append({"field": f"persona.{aid}.signal", "before": was.get("signal"), "after": now.get("signal")})
    return {"previous_run_id": previous_id, "previous_created_at": bundle.get("created_at"), "diffs": diffs}


def build_earnings_dossier(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Dossier: event, consensus, evidence-derived disagreement and changes since the last run."""
    from augur.disagreement import DisagreementMapBuilder

    ticker = inputs["ticker"].upper()
    personas = _upstream_value(upstream, "personas") or {}
    evidence = _upstream_value(upstream, "evidence_items") or []
    consensus = _upstream_value(upstream, "consensus") or {}
    diffs = _upstream_value(upstream, "diffs") or []
    event = _upstream_value(upstream, "event") or {}
    dm = DisagreementMapBuilder(ticker, "").build(personas, evidence)

    lines = [f"# Pre-earnings dossier: {ticker}", "", f"As of {inputs.get('as_of')} · event {inputs.get('event_id')}"]
    if event.get("event_date"):
        lines.append(f"Next earnings: {event['event_date']} ({event.get('confidence', 'unknown')}, {event.get('fiscal_period', '')})")
    else:
        lines.append(f"Next earnings: {event.get('note', 'unknown')}")
    if consensus:
        lines += ["", "## Consensus", f"{consensus.get('signal', '').upper()} {consensus.get('score')}/10, "
                  f"confidence {consensus.get('confidence')}"]
    lines += ["", "## Where the personas disagree", dm.summary]
    for cp in dm.conflict_points:
        lines.append(f"- **{cp.claim}** — high: {', '.join(cp.bullish_personas)}; low: {', '.join(cp.bearish_personas)}; "
                     f"evidence: {', '.join(cp.evidence_supporting)}; would resolve: {cp.information_that_would_resolve}")
    for gap in dm.evidence_gaps:
        lines.append(f"- evidence gap: {gap}")
    previous_run = _upstream_value(upstream, "previous_run_id")
    lines += ["", "## Changes since the previous run"]
    if not previous_run:
        lines.append("- no earlier run for this ticker")
    elif not diffs:
        lines.append(f"- no consensus or signal changes versus {previous_run}")
    else:
        lines.append(f"- versus {previous_run}:")
        lines += [f"  - {d['field']}: {d.get('before')} → {d.get('after')}" for d in diffs]
    return {
        "dossier": {"ticker": ticker, "event": event, "consensus": consensus,
                    "disagreement": dataclasses.asdict(dm), "changes": diffs},
        "summary_markdown": "\n".join(lines),
    }


# ---------------------------------------------------------------------------
# filing-delta / debt-covenant-review
# ---------------------------------------------------------------------------

def read_annual_financials(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """The two most recent 10-K fiscal years from SEC XBRL company facts."""
    return _annual_with_evidence(inputs["ticker"], years=2)


def compare_annual_filings(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """FilingDeltaBuilder over the two most recent annual periods."""
    from augur.filing_delta import FilingDeltaBuilder

    periods = _upstream_value(upstream, "periods") or []
    if len(periods) < 2:
        raise LookupError("need two annual 10-K periods to compare")
    new, prev = periods[0], periods[1]
    report = FilingDeltaBuilder(inputs["ticker"], new["accession"], prev["accession"]).build(
        {"metrics": new["metrics"], "filing_date": new["filed"], "filing_type": "10-K"},
        {"metrics": prev["metrics"], "filing_date": prev["filed"], "filing_type": "10-K"},
    )
    return {"delta_report": report.to_dict(), "summary_markdown": report.to_markdown()}


# Reference thresholds only: the company's actual covenants live in its credit
# agreements, which are not machine-readable here.
REFERENCE_COVENANTS = {"debt_ebitda_max": 3.5, "interest_coverage_min": 2.5}


def review_covenants(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """CovenantReviewer on the latest annual figures against reference (or supplied) thresholds."""
    from augur.covenant import CovenantReviewer

    periods = _upstream_value(upstream, "periods") or []
    if not periods:
        raise LookupError("no annual financials to review")
    m = periods[0]["metrics"]
    financials = {"ticker": inputs["ticker"].upper()}
    for key in ("total_debt", "ebitda", "interest_expense"):
        if key in m:
            financials[key] = m[key]
    if "operating_income" in m:
        financials["ebit"] = m["operating_income"]
    terms = {k: float(inputs.get(k, v)) for k, v in REFERENCE_COVENANTS.items()}
    report = CovenantReviewer.review(financials, terms)
    unavailable = [k for k in ("total_debt", "ebitda", "interest_expense") if k not in financials]

    lines = [f"# Covenant review: {inputs['ticker'].upper()} (FY ending {periods[0]['fiscal_year_end']})", "",
             f"Thresholds: Debt/EBITDA ≤ {terms['debt_ebitda_max']}x, interest coverage ≥ {terms['interest_coverage_min']}x "
             "— reference values, not the company's contractual covenants.",
             f"Overall: {report.overall} ({report.passed}/{report.total_checks} checks pass)"]
    for check in report.checks:
        lines.append(f"- {check.description}: {check.current_value:.2f} vs {check.threshold} "
                     f"({'ok' if check.in_compliance else 'BREACH'}, headroom {check.margin_of_safety_pct:.0f}%)")
    if unavailable:
        lines.append(f"- not reported in XBRL, so not checked: {', '.join(unavailable)}")
    return {"covenant_report": {**dataclasses.asdict(report), "thresholds": terms, "unavailable_inputs": unavailable,
                                "thresholds_are_reference": not any(k in inputs for k in REFERENCE_COVENANTS)},
            "summary_markdown": "\n".join(lines)}


# ---------------------------------------------------------------------------
# insider-cluster-review
# ---------------------------------------------------------------------------

def read_form4(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Open-market Form 4 transactions for the trailing 90 days."""
    from augur.cli_commands.insider_cmd import _fetch_insider_trades
    from augur.schemas.evidence import generate_evidence_id

    ticker = inputs["ticker"].upper()
    trades = _fetch_insider_trades(ticker)
    now = datetime.now(timezone.utc).isoformat()
    evidence = []
    for t in trades:
        content_hash = hashlib.sha256(
            f"form4:{ticker}:{t.person}:{t.transaction_date}:{t.type}:{t.shares}:{t.price}".encode()
        ).hexdigest()
        evidence.append({
            "evidence_id": generate_evidence_id("sec_form4", content_hash), "source": "sec_form4",
            "source_locator": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={t.person}&type=4",
            "content_hash": content_hash, "instrument": ticker, "metric": f"insider_{t.type}",
            "value": t.value, "unit": "USD", "currency": "USD",
            "effective_at": f"{t.transaction_date}T00:00:00+00:00" if t.transaction_date else None,
            "available_at": None, "retrieved_at": now, "schema_version": "1.0",
            "coverage": 1.0, "missing": False, "degraded": False,
            "metadata": {"reporting_owner_cik": t.person, "shares": t.shares, "price": t.price},
        })
    return {"trades": [dataclasses.asdict(t) for t in trades], "evidence_items": evidence}


def detect_insider_cluster(inputs: Dict[str, Any], upstream: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    from augur.ownership import InsiderAnalyzer, InsiderTrade

    trades = [InsiderTrade(**t) for t in (_upstream_value(upstream, "trades") or [])]
    cluster = InsiderAnalyzer().detect_clusters(trades, window_days=90)
    lines = [f"# Insider cluster review: {inputs['ticker'].upper()} (trailing 90 days, open-market Form 4)", "",
             f"Assessment: {cluster.assessment}"
             + (" (trades found, but no cluster: fewer than two distinct insiders traded in the same direction)"
                if cluster.assessment == "no_activity" and trades else ""),
             f"Buys: {cluster.total_buys} · sells: {cluster.total_sells} · "
             f"net ${cluster.net_value:,.0f}", f"Participants (CIK): {', '.join(cluster.participants) or 'none'}"]
    return {"cluster_report": dataclasses.asdict(cluster), "summary_markdown": "\n".join(lines)}


# ---------------------------------------------------------------------------
# Capability table
# ---------------------------------------------------------------------------

_TICKER_INPUT = {"type": "object", "properties": {"ticker": {"type": "string", "minLength": 1}}, "required": ["ticker"]}

#: name -> spec. ``network_domains`` / ``resources`` are what the handler
#: touches; the runner checks them against the skill's permissions before
#: any step executes.
CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "earnings.collect_evidence": {
        "description": "Live market context and evidence items (yfinance, SEC EDGAR) plus the next calendar event.",
        # Default provider chain: yfinance, then stooq as fallback; SEC EDGAR overlay.
        "handler": collect_earnings_evidence, "network_domains": ["finance.yahoo.com", "stooq.com", "sec.gov"],
        "resources": ["evidence.read"], "timeout_ms": 120_000,
    },
    "personas.analyze": {
        "description": "Run every persona on the collected context and compute the weighted consensus.",
        # Consensus pulls VIX/SPY history for regime detection unless AUGUR_SKIP_MACRO_FETCH=1.
        "handler": analyze_personas, "network_domains": ["finance.yahoo.com"], "resources": [], "timeout_ms": 60_000,
    },
    "runs.compare": {
        "description": "Compare consensus and persona signals with the newest saved run for the ticker.",
        "handler": compare_with_previous_run, "network_domains": [], "resources": ["runs.read"], "timeout_ms": 30_000,
    },
    "report.earnings_dossier": {
        "description": "Assemble the pre-earnings dossier with the evidence-derived disagreement map.",
        "handler": build_earnings_dossier, "network_domains": [], "resources": ["evidence.read"], "timeout_ms": 30_000,
    },
    "sec.financials.annual": {
        "description": "Annual statement figures for the two most recent 10-K fiscal years (SEC XBRL company facts).",
        "handler": read_annual_financials, "network_domains": ["sec.gov"], "resources": ["evidence.read"],
        "timeout_ms": 120_000,
    },
    "filings.compare": {
        "description": "Material changes between the two most recent annual periods (FilingDeltaBuilder).",
        "handler": compare_annual_filings, "network_domains": [], "resources": ["evidence.read"], "timeout_ms": 30_000,
    },
    "covenant.review": {
        "description": "Debt/EBITDA and interest coverage against reference or supplied thresholds.",
        "handler": review_covenants, "network_domains": [], "resources": ["evidence.read"], "timeout_ms": 30_000,
    },
    "sec.form4.read": {
        "description": "Open-market Form 4 insider transactions for the trailing 90 days (SEC EDGAR).",
        "handler": read_form4, "network_domains": ["sec.gov"], "resources": ["evidence.read"], "timeout_ms": 120_000,
    },
    "ownership.cluster_detect": {
        "description": "Insider buy/sell cluster detection over the collected transactions.",
        "handler": detect_insider_cluster, "network_domains": [], "resources": ["evidence.read"], "timeout_ms": 30_000,
    },
}

for _spec in CAPABILITIES.values():
    _spec.setdefault("input_schema", _TICKER_INPUT)

Handler = Callable[[Dict[str, Any], Dict[str, Dict[str, Any]]], Dict[str, Any]]
