# -*- coding: utf-8 -*-
"""
augur.workflow - Agentic multi-step analysis pipeline.

Runs configurable step chains: fetch → analyze → consensus → committee → debate → sentiment.
"""

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

    ctx = None
    if any(s in step_list for s in ("fetch", "analyze", "consensus", "committee", "debate")):
        from augur.data import fetch_market_context
        ctx = fetch_market_context(ticker)
        if "fetch" in step_list:
            output["results"]["fetch"] = {
                "price": ctx.price,
                "pe": ctx.pe,
                "sector": ctx.sector,
                "industry": ctx.industry,
            }

    selected_agents = None
    if agents.strip():
        selected_ids = [a.strip() for a in agents.split(",") if a.strip()]
        all_agents = {a.agent_id: a for a in registry.get_all()}
        selected_agents = {aid: all_agents[aid] for aid in selected_ids if aid in all_agents}

    responses = None
    if any(s in step_list for s in ("analyze", "consensus", "committee", "debate")):
        if selected_agents:
            responses = {aid: agent.analyze(ctx) for aid, agent in selected_agents.items()}
        else:
            responses = coordinator.analyze_with_all(ctx)
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

    if "consensus" in step_list and responses:
        consensus = coordinator.get_consensus(responses, ticker=ticker, context=ctx)
        output["results"]["consensus"] = {
            "signal": consensus.signal.value,
            "score": consensus.score,
            "confidence": consensus.confidence,
            "reasoning": consensus.reasoning,
            "kelly_pct": (consensus.metadata or {}).get("position_sizing", {}).get("position_pct"),
        }

    if "committee" in step_list and responses:
        consensus = coordinator.get_consensus(responses, ticker=ticker, context=ctx)
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

    if "debate" in step_list:
        debate_results = coordinator.run_debate(ctx, rounds=2)
        debate_consensus = coordinator.get_consensus(debate_results, ticker=ticker, context=ctx)
        output["results"]["debate"] = {
            "signal": debate_consensus.signal.value,
            "score": debate_consensus.score,
            "rounds": 2,
        }

    if "sentiment" in step_list:
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

    output["summary"] = format_workflow_summary(output)
    return output


def format_workflow_summary(data: Dict[str, Any]) -> str:
    """Format workflow output as human-readable text."""
    lines = [f"═══ Augur Workflow: {data['ticker']} ═══", f"Steps: {', '.join(data['steps'])}", ""]
    results = data.get("results", {})

    if "fetch" in results:
        f = results["fetch"]
        lines += [
            "── Fetch ──",
            f"  Price: ${f.get('price', 0):.2f}  PE: {f.get('pe', 0):.1f}",
            f"  Sector: {f.get('sector', 'N/A')}",
            "",
        ]

    if "analyze" in results:
        agents = results["analyze"]
        lines += [f"── Analyze ({len(agents)} agents) ──", ""]
        for aid, a in sorted(agents.items(), key=lambda x: -x[1]["score"])[:5]:
            lines.append(
                f"  {a['agent_name']:<22s} {a['signal'].upper():<8s} {a['score']:.1f}/10"
            )
        if len(agents) > 5:
            lines.append(f"  … and {len(agents) - 5} more")
        lines.append("")

    if "consensus" in results:
        c = results["consensus"]
        lines += [
            "── Consensus ──",
            f"  Signal: {c['signal'].upper()}  Score: {c['score']:.1f}/10  Conf: {c['confidence']:.0%}",
            "",
        ]

    if "committee" in results:
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

    return "\n".join(lines)
