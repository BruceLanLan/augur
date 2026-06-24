# -*- coding: utf-8 -*-
"""
augur.workflow - Agentic multi-step analysis pipeline.

Runs configurable step chains: fetch → analyze → consensus → committee → debate → sentiment.
"""

import time
from typing import Any, Dict, List, Optional


VALID_STEPS = ("fetch", "analyze", "consensus", "committee", "debate", "sentiment")
DEFAULT_STEPS = "fetch,analyze,consensus"


def parse_steps(steps: str) -> List[str]:
    """Parse and validate a comma-separated workflow step list."""
    step_list = [s.strip().lower() for s in steps.split(",") if s.strip()]
    if not step_list:
        step_list = [s for s in DEFAULT_STEPS.split(",")]
    for s in step_list:
        if s not in VALID_STEPS:
            raise ValueError(f"Unknown step '{s}'. Valid: {', '.join(VALID_STEPS)}")
    return step_list


def _record_step_status(output: Dict[str, Any], step_list: List[str]) -> None:
    """Attach per-step status envelope (ok / skipped / error / empty)."""
    results = output.get("results", {})
    status: Dict[str, str] = {}
    for step in VALID_STEPS:
        if step not in step_list:
            status[step] = "skipped"
        elif step not in results:
            status[step] = "empty"
        elif isinstance(results[step], dict) and "error" in results[step]:
            status[step] = "error"
        else:
            status[step] = "ok"
    output["step_status"] = status


def run_workflow(
    ticker: str,
    steps: str = "fetch,analyze,consensus",
    agents: str = "",
    question: str = "",
) -> Dict[str, Any]:
    """Execute an agentic workflow and return structured results."""
    from augur.registry import AgentRegistry, DecisionCoordinator

    step_list = parse_steps(steps)
    ticker = ticker.upper()
    registry = AgentRegistry()
    coordinator = DecisionCoordinator(registry)
    output: Dict[str, Any] = {"ticker": ticker, "steps": step_list, "results": {}}
    step_timings: Dict[str, float] = {}

    ctx = None
    if any(s in step_list for s in ("fetch", "analyze", "consensus", "committee", "debate")):
        t0 = time.perf_counter()
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
            if "fetch" in step_list:
                output["results"]["fetch"] = {
                    "price": ctx.price,
                    "pe": ctx.pe,
                    "sector": ctx.sector,
                    "industry": ctx.industry,
                }
        except Exception as e:
            if "fetch" in step_list:
                output["results"]["fetch"] = {"error": str(e)}
            output.setdefault("warnings", []).append(f"fetch_failed: {e}")
        step_timings["fetch"] = round(time.perf_counter() - t0, 3)

    selected_agents = None
    persona_filter: Optional[List[str]] = None
    if agents.strip():
        selected_ids = [a.strip() for a in agents.split(",") if a.strip()]
        all_agents = {a.agent_id: a for a in registry.get_all()}
        selected_agents = {aid: all_agents[aid] for aid in selected_ids if aid in all_agents}
        skipped = [aid for aid in selected_ids if aid not in all_agents]
        if skipped:
            output["agents_skipped"] = skipped
        if not selected_agents:
            output.setdefault("warnings", []).append(
                "all_requested_agents_invalid: falling back to workspace/default agent set"
            )
    else:
        from augur.workspace import get_enabled_personas

        persona_filter = get_enabled_personas() or None
        if persona_filter:
            output["agents_filter"] = persona_filter

    debate_personas: Optional[List[str]] = None
    if selected_agents:
        debate_personas = list(selected_agents.keys())
    elif persona_filter:
        debate_personas = persona_filter

    responses = None
    needs_responses = any(s in step_list for s in ("analyze", "consensus", "committee", "debate"))
    if needs_responses and ctx is None:
        output.setdefault("warnings", []).append(
            "context_unavailable: market data fetch failed; analyze/consensus/committee/debate skipped"
        )
    elif needs_responses:
        t0 = time.perf_counter()
        try:
            if selected_agents:
                responses = {aid: agent.analyze(ctx) for aid, agent in selected_agents.items()}
            else:
                responses = coordinator.analyze_with_all(ctx, enabled_personas=persona_filter)
            if "analyze" in step_list:
                output["results"]["analyze"] = {
                    aid: {
                        "agent_name": r.agent_name,
                        "signal": r.signal.value,
                        "score": r.score,
                        "confidence": r.confidence,
                    }
                    for aid, r in responses.items()
                }
        except Exception as e:
            if "analyze" in step_list:
                output["results"]["analyze"] = {"error": str(e)}
            output.setdefault("warnings", []).append(f"analyze_failed: {e}")
        step_timings["analyze"] = round(time.perf_counter() - t0, 3)

    consensus_result = None
    if any(s in step_list for s in ("consensus", "committee")) and responses:
        t0 = time.perf_counter()
        try:
            consensus_result = coordinator.get_consensus(responses, ticker=ticker, context=ctx)
            meta = consensus_result.metadata or {}
            if meta.get("low_participation"):
                output.setdefault("warnings", []).append(
                    "low_participation: fewer than 3 agents responded; confidence capped"
                )
        except Exception as e:
            if "consensus" in step_list:
                output["results"]["consensus"] = {"error": str(e)}
            output.setdefault("warnings", []).append(f"consensus_failed: {e}")
        step_timings["consensus"] = round(time.perf_counter() - t0, 3)

    if "consensus" in step_list and consensus_result is not None:
        meta = consensus_result.metadata or {}
        output["results"]["consensus"] = {
            "signal": consensus_result.signal.value,
            "score": consensus_result.score,
            "confidence": consensus_result.confidence,
            "reasoning": consensus_result.reasoning,
            "kelly_pct": meta.get("position_sizing", {}).get("position_pct"),
            "low_participation": bool(meta.get("low_participation")),
            "regime": meta.get("regime_features", {}).get("regime"),
        }

    if "committee" in step_list and responses:
        t0 = time.perf_counter()
        try:
            consensus = consensus_result or coordinator.get_consensus(
                responses, ticker=ticker, context=ctx
            )
            bullish = sum(1 for r in responses.values() if r.signal.value == "bullish")
            bearish = sum(1 for r in responses.values() if r.signal.value == "bearish")
            neutral = len(responses) - bullish - bearish
            output["results"]["committee"] = {
                "question": question or f"Should we invest in {ticker}?",
                "verdict": consensus.signal.value,
                "score": consensus.score,
                "vote": {"bullish": bullish, "neutral": neutral, "bearish": bearish},
                "opinions": [
                    {"agent": r.agent_name, "signal": r.signal.value, "score": r.score}
                    for r in sorted(responses.values(), key=lambda x: -x.score)
                ],
            }
        except Exception as e:
            output["results"]["committee"] = {"error": str(e)}
            output.setdefault("warnings", []).append(f"committee_failed: {e}")
        step_timings["committee"] = round(time.perf_counter() - t0, 3)

    if "debate" in step_list:
        t0 = time.perf_counter()
        try:
            if responses:
                debate_results = coordinator.run_debate(
                    ctx, rounds=2, initial_results=responses
                )
            else:
                debate_results = coordinator.run_debate(
                    ctx, rounds=2, enabled_personas=debate_personas
                )
            debate_consensus = coordinator.get_consensus(
                debate_results, ticker=ticker, context=ctx
            )
            output["results"]["debate"] = {
                "signal": debate_consensus.signal.value,
                "score": debate_consensus.score,
                "rounds": 2,
            }
        except Exception as e:
            output["results"]["debate"] = {"error": str(e)}
        step_timings["debate"] = round(time.perf_counter() - t0, 3)

    if "sentiment" in step_list:
        t0 = time.perf_counter()
        try:
            from augur.sentiment import SentimentAnalyzer
            sent = SentimentAnalyzer().get_sentiment(ticker)
            output["results"]["sentiment"] = {
                "score": sent.overall_score,
                "volume": sent.volume,
                "trending": sent.trending,
            }
        except Exception as e:
            output["results"]["sentiment"] = {"error": str(e)}
        step_timings["sentiment"] = round(time.perf_counter() - t0, 3)

    if step_timings:
        output["step_timings_ms"] = {k: round(v * 1000, 1) for k, v in step_timings.items()}

    _record_step_status(output, step_list)
    output["summary"] = format_workflow_summary(output)
    return output


def format_workflow_summary(data: Dict[str, Any]) -> str:
    """Format workflow output as human-readable text."""
    lines = [f"═══ Augur Workflow: {data['ticker']} ═══", f"Steps: {', '.join(data['steps'])}", ""]
    results = data.get("results", {})

    if "fetch" in results and "error" not in results["fetch"]:
        f = results["fetch"]
        lines += [
            "── Fetch ──",
            f"  Price: ${f.get('price', 0):.2f}  PE: {f.get('pe', 0):.1f}",
            f"  Sector: {f.get('sector', 'N/A')}",
            "",
        ]

    if "analyze" in results and "error" not in results["analyze"]:
        agents = results["analyze"]
        lines += [f"── Analyze ({len(agents)} agents) ──", ""]
        for aid, a in sorted(agents.items(), key=lambda x: -x[1]["score"])[:5]:
            lines.append(
                f"  {a['agent_name']:<22s} {a['signal'].upper():<8s} {a['score']:.1f}/10"
            )
        if len(agents) > 5:
            lines.append(f"  … and {len(agents) - 5} more")
        lines.append("")

    if "consensus" in results and "error" not in results["consensus"]:
        c = results["consensus"]
        lines += [
            "── Consensus ──",
            f"  Signal: {c['signal'].upper()}  Score: {c['score']:.1f}/10  Conf: {c['confidence']:.0%}",
            "",
        ]

    if "committee" in results and "error" not in results["committee"]:
        cm = results["committee"]
        v = cm["vote"]
        lines += [
            "── Committee ──",
            f"  Verdict: {cm['verdict'].upper()}  Vote: {v['bullish']}B / {v['neutral']}N / {v['bearish']}Be",
            "",
        ]

    if "sentiment" in results and "error" not in results["sentiment"]:
        s = results["sentiment"]
        lines += [f"── Sentiment ──  Score: {s['score']:+.2f}", ""]

    failed_steps = [
        step for step, val in results.items()
        if isinstance(val, dict) and "error" in val
    ]
    if failed_steps:
        lines += ["── Step Errors ──"]
        for step in failed_steps:
            lines.append(f"  ✗ {step}: {results[step]['error']}")
        lines.append("")

    warnings = data.get("warnings", [])
    if warnings:
        lines += ["── Warnings ──"]
        for w in warnings:
            lines.append(f"  ! {w}")
        lines.append("")

    return "\n".join(lines)
