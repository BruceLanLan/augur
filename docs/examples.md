# Augur Examples

Practical usage examples for the Research Memory System (thesis, evidence, earnings, valuation, skills).

## 1. Full Research Loop

```python
from augur.workflow import run_workflow
from augur.thesis import Thesis, ThesisJournal

# 1. Run the analysis pipeline
result = run_workflow("AAPL", steps="fetch,analyze,consensus")
run_id = result.get("run_id")
print(f"Run: {run_id}")

# 2. Create a thesis tied to the run
journal = ThesisJournal()
thesis_id = journal.create(Thesis(
    thesis_id="",   # blank: create() assigns one
    created_at="",  # blank: create() stamps the current UTC time
    ticker="AAPL",
    statement="Services revenue will surpass hardware within 2 years",
    catalysts=["Services growth 15%+", "Installed base expansion"],
    risks=["Regulatory pressure", "China demand weakness"],
    falsification_conditions=["Services growth drops below 10%"],
    run_id=run_id or "",
))
```

## 2. Evidence-First Analysis

```python
from augur.schemas import EvidenceItem, Claim
from datetime import datetime

# Create evidence with three-time semantics
evidence = EvidenceItem(
    source="sec_edgar",
    content_hash="abc123def456",
    instrument="AAPL",
    metric="revenue",
    value=383.5e9,
    effective_at=datetime(2025, 9, 28),
    available_at=datetime(2025, 10, 31),
    retrieved_at=datetime(2025, 11, 1),
)

# Create a claim backed by classified evidence
claim = Claim(
    text="Apple revenue grew 6% YoY",
    persona_id="buffett",
    supports=[evidence.evidence_id],
    classification="fact",
    confidence=0.95,
    confidence_source="explicit_rule",
)
```

## 3. Earnings Event Workflow

```python
from augur.earnings import EarningsEventService

service = EarningsEventService()
events = service.detect_events(["AAPL", "MSFT"], lookahead_days=30)
for event in events:
    print(f"{event.ticker}: earnings on {event.event_date} ({event.confidence})")

readiness = service.check_dossier_readiness(events)
for status in readiness:
    if not status.ready:
        print(f"{status.ticker} missing: {status.missing_items}")
```

## 4. Valuation Lab

```python
from augur.valuation import compute_wacc, compute_dcf, WACCInputs, DCFInputs

wacc = compute_wacc(WACCInputs(
    risk_free_rate=0.045, equity_risk_premium=0.055,  # rates are decimals
    beta=1.2, cost_of_debt=0.035, tax_rate=0.21,
))
print(f"WACC: {wacc:.2%}")

result = compute_dcf(DCFInputs(
    free_cash_flow=100e9, growth_rate_stage1=0.08,
    stage1_years=5, growth_rate_terminal=0.025,
    wacc=wacc, shares_outstanding=15.5e9, net_debt=50e9,
))
print(f"Fair Value: ${result.fair_value_per_share:.2f}")
```

## 5. Disagreement Map

```python
from augur.disagreement import DisagreementMapBuilder

builder = DisagreementMapBuilder("AAPL", "run_001")
persona_outputs = {
    "buffett": {"signal": "bullish", "score": 8.0},
    "dalio": {"signal": "bearish", "score": 3.5},
    "lynch": {"signal": "bullish", "score": 7.5},
}
result = builder.build(persona_outputs)
print(f"Consensus: {result.consensus_strength}")
for conflict in result.conflict_points:
    print(f"- {conflict.claim} (impact: {conflict.impact})")
```

## 6. Evidence-seeking Debate

```python
from augur.experimental.debate_engine import EvidenceSeekingDebate  # experimental module

debate = EvidenceSeekingDebate("AAPL", "run_001")
result = debate.run(persona_outputs)
print(f"Supported: {result.claims_supported}")
print(f"Contradicted: {result.claims_contradicted}")
print(f"New evidence: {result.new_evidence_found}")
```

## 7. Post-Earnings Scorecard

```python
from augur.scorecard import ScorecardBuilder

builder = ScorecardBuilder()
pre_run = {"consensus_signal": "bullish", "score": 7.5}
post_run = {"actual_eps": 2.40, "actual_revenue_growth": 6.2}
scorecard = builder.build(
    pre_run, post_run,
    questions=["Will revenue grow >5%?", "Will EPS beat 2.30?"],
)
print(f"Accuracy: {scorecard.accuracy:.0%}")
```

## 8. Export

```python
from augur.export import ReportExporter

exporter = ReportExporter()
markdown = exporter.to_markdown(run_bundle)
print(markdown[:200])
```

## 9. Skill Loading & Permissions

```python
from augur.skills.loader import load_skill
from augur.skills.permissions import SkillPermissionEnforcer
from pathlib import Path

spec = load_skill(Path("src/augur/skills/earnings_prep.yaml"))
enforcer = SkillPermissionEnforcer(spec)
enforcer.check_network("sec.gov")     # OK
enforcer.check_network("evil.com")    # SkillPermissionError
```

## 10. CLI Examples

```bash
# Complete research loop
augur workflow AAPL --steps fetch,analyze,consensus,committee

# Export report
augur export AAPL --format md

# Run a built-in skill (pre-earnings dossier with evidence-derived disagreement)
augur skill run earnings-prep AAPL

# Valuation
augur valuation AAPL

# Filing delta
augur filing-delta AAPL --new q3.json --prev q2.json   # two JSON evidence snapshots

# Insider activity
augur insider AAPL

# Earnings research cycle (offline: reads saved watchlist, calendar, runs, theses)
augur earnings --backfill            # fill the calendar from SEC 8-K Item 2.02 filings
augur cycle --days 14
augur thesis-delta AAPL              # active theses vs the two latest saved runs
augur scorecard AAPL                 # post-earnings scorecard on the research questions

# Grouped commands (old flat names still work but print a deprecation note)
augur watchlist add AAPL
augur cron run
augur eval ic
augur records verify-pack pack.zip
```
