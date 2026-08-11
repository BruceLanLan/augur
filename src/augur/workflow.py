# -*- coding: utf-8 -*-
"""
augur.workflow - Agentic multi-step analysis pipeline.

Runs configurable step chains: fetch → analyze → consensus → committee → debate → sentiment.

E1.2: Every phase is wrapped with RunTracker StepResult tracking.  When
``track=True`` (the default) a RunBundle is generated and persisted on
completion, and a checkpoint is saved after every phase.
"""

import dataclasses
import time
from typing import Any, Dict, List, Optional

VALID_STEPS = ("fetch", "analyze", "consensus", "committee", "debate", "sentiment")
DEFAULT_STEPS = "fetch,analyze,consensus"


def parse_steps(steps: str) -> List[str]:
    """Parse and validate a comma-separated workflow step list.

    An empty/falsy ``steps`` falls back to the active workspace layout
    preset's default steps (see ``workspace.get_default_workflow_steps``),
    then to ``DEFAULT_STEPS`` if no workspace is available.
    """
    if not steps or not steps.strip():
        try:
            from augur.workspace import get_default_workflow_steps

            steps = get_default_workflow_steps()
        except Exception:
            steps = DEFAULT_STEPS
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
    steps: str = "",
    agents: str = "",
    question: str = "",
    resume_from: str = "",
    track: bool = True,
) -> Dict[str, Any]:
    """Execute an agentic workflow and return structured results.

    Args:
        ticker: Stock ticker symbol.
        steps: Comma-separated step list
            (fetch,analyze,consensus,committee,debate,sentiment).
        agents: Comma-separated agent IDs to restrict analysis.
        question: Optional question for committee/debate.
        resume_from: Path to a checkpoint JSON file to resume from.
        track: When True (default), wrap execution with RunTracker for
            StepResult tracking, checkpointing, and RunBundle generation.

    Returns:
        Dict with ``ticker``, ``steps``, ``results``, ``summary``, plus
        ``run_id`` and ``run_bundle_path`` when tracking is enabled.
    """
    from augur.registry import AgentRegistry, DecisionCoordinator

    # ------------------------------------------------------------------
    # Parse steps early (needed for tracker setup)
    # ------------------------------------------------------------------
    step_list = parse_steps(steps)
    ticker = ticker.upper()

    # ------------------------------------------------------------------
    # RunTracker setup (E1.2)
    # ------------------------------------------------------------------
    tracker: Any = None

    if track:
        from augur.run_tracker import RunTracker, _compute_input_snapshot_hash
        from augur.schemas.step_result import StepStatus

        input_hash = _compute_input_snapshot_hash(
            ticker, steps, agents, question
        )

        if resume_from:
            tracker = RunTracker.resume_from_checkpoint(
                resume_from,
                ticker=ticker,
                steps=steps,
                agents=agents,
                question=question,
            )
            # start_run on a resumed tracker re-uses the stored run_id
            # but creates a fresh manifest; we override with stored hash.
            tracker.start_run(input_snapshot_hash=input_hash)
        else:
            tracker = RunTracker(ticker=ticker)
            tracker.start_run(input_snapshot_hash=input_hash)

    output: Dict[str, Any] = {
        "ticker": ticker,
        "steps": step_list,
        "results": {},
        "degradation": [],
    }
    if tracker is not None:
        output["run_id"] = tracker.run_id

    step_timings: Dict[str, float] = {}

    registry = AgentRegistry()
    coordinator = DecisionCoordinator(registry)

    # ------------------------------------------------------------------
    # PHASE 1: fetch
    # ------------------------------------------------------------------
    ctx: Any = None
    _should_fetch = any(
        s in step_list for s in ("fetch", "analyze", "consensus", "committee", "debate")
    )
    if _should_fetch:
        # Checkpoint resume: restore ctx from checkpoint_state if fetch
        # was already completed.
        if tracker is not None and tracker.is_step_completed("fetch"):
            ctx_dict = tracker.get_checkpoint_state("ctx", None)
            if ctx_dict is not None:
                from augur.personas.base import MarketContext
                ctx = MarketContext(**ctx_dict)
        else:
            sid = tracker.start_step("fetch") if tracker else None
            t0 = time.perf_counter()
            try:
                from augur.data import fetch_market_context

                ctx = fetch_market_context(ticker)
                fetch_result = {
                    "price": ctx.price,
                    "pe": ctx.pe,
                    "sector": ctx.sector,
                    "industry": ctx.industry,
                }
                if "fetch" in step_list:
                    output["results"]["fetch"] = fetch_result
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.SUCCESS, result=fetch_result
                    )
                    # Persist intermediate state for downstream resume
                    tracker.set_checkpoint_state(
                        "ctx", dataclasses.asdict(ctx)
                    )
            except Exception as e:
                if "fetch" in step_list:
                    output["results"]["fetch"] = {"error": str(e)}
                output.setdefault("warnings", []).append(f"fetch_failed: {e}")
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.FAILURE, diagnostics=str(e)
                    )
            finally:
                elapsed = round(time.perf_counter() - t0, 3)
                step_timings["fetch"] = elapsed
            if tracker:
                tracker.save_checkpoint()

    # ------------------------------------------------------------------
    # Agent selection
    # ------------------------------------------------------------------
    selected_agents: Any = None
    persona_filter: Optional[List[str]] = None
    if agents.strip():
        selected_ids = [a.strip() for a in agents.split(",") if a.strip()]
        all_agents = {a.agent_id: a for a in registry.get_all()}
        selected_agents = {
            aid: all_agents[aid] for aid in selected_ids if aid in all_agents
        }
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

    # ------------------------------------------------------------------
    # PHASE 2: analyze
    # ------------------------------------------------------------------
    responses: Any = None
    needs_responses = any(
        s in step_list for s in ("analyze", "consensus", "committee", "debate")
    )
    if needs_responses and ctx is None:
        output.setdefault("warnings", []).append(
            "context_unavailable: market data fetch failed; "
            "analyze/consensus/committee/debate skipped"
        )
    elif needs_responses:
        if tracker is not None and tracker.is_step_completed("analyze"):
            # Restore responses from checkpoint_state
            responses_raw = tracker.get_checkpoint_state("responses", None)
            if responses_raw is not None:
                # responses_raw is {aid: {agent_name, signal, score, ...}}
                # We reconstruct lightweight AgentResponse-like objects
                # enough for downstream steps.
                from augur.personas.base import AgentResponse, SignalType

                responses = {}
                for aid, rdict in responses_raw.items():
                    responses[aid] = AgentResponse(
                        agent_id=aid,
                        agent_name=rdict.get("agent_name", ""),
                        signal=SignalType(rdict.get("signal", "neutral")),
                        confidence=rdict.get("confidence", 0.0),
                        score=rdict.get("score", 0.0),
                        reasoning=rdict.get("reasoning", ""),
                    )
        else:
            sid = tracker.start_step("analyze") if tracker else None
            t0 = time.perf_counter()
            try:
                if selected_agents:
                    responses = {
                        aid: agent.analyze(ctx)
                        for aid, agent in selected_agents.items()
                    }
                else:
                    responses = coordinator.analyze_with_all(
                        ctx, enabled_personas=persona_filter
                    )
                if "analyze" in step_list:
                    analyze_result = {
                        aid: {
                            "agent_name": r.agent_name,
                            "signal": r.signal.value,
                            "score": r.score,
                            "confidence": r.confidence,
                        }
                        for aid, r in responses.items()
                    }
                    output["results"]["analyze"] = analyze_result
                if tracker and sid:
                    tracker.finish_step(
                        sid,
                        StepStatus.SUCCESS,
                        result=output["results"].get("analyze", {}),
                    )
                    # Persist serializable responses for resume
                    tracker.set_checkpoint_state(
                        "responses",
                        {
                            aid: r.to_dict()
                            for aid, r in (responses or {}).items()
                        },
                    )
            except Exception as e:
                if "analyze" in step_list:
                    output["results"]["analyze"] = {"error": str(e)}
                output.setdefault("warnings", []).append(f"analyze_failed: {e}")
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.FAILURE, diagnostics=str(e)
                    )
            finally:
                elapsed = round(time.perf_counter() - t0, 3)
                step_timings["analyze"] = elapsed
            if tracker:
                tracker.save_checkpoint()

    # ------------------------------------------------------------------
    # PHASE 3: consensus
    # ------------------------------------------------------------------
    consensus_result: Any = None
    if any(s in step_list for s in ("consensus", "committee")) and responses:
        if tracker is not None and tracker.is_step_completed("consensus"):
            # Restore consensus_result from checkpoint_state
            cons_raw = tracker.get_checkpoint_state("consensus_result", None)
            if cons_raw is not None:
                from augur.personas.base import SignalType
                # Reconstruct a lightweight consensus-like namespace
                _ConsensusProxy = type(
                    "ConsensusProxy", (),
                    {
                        "signal": SignalType(cons_raw.get("signal", "neutral")),
                        "score": cons_raw.get("score", 0.0),
                        "confidence": cons_raw.get("confidence", 0.0),
                        "reasoning": cons_raw.get("reasoning", ""),
                        "metadata": cons_raw.get("metadata", {}),
                    },
                )
                consensus_result = _ConsensusProxy()
        else:
            sid = tracker.start_step("consensus") if tracker else None
            t0 = time.perf_counter()
            try:
                consensus_result = coordinator.get_consensus(
                    responses, ticker=ticker, context=ctx
                )
                meta = consensus_result.metadata or {}
                if meta.get("low_participation"):
                    output.setdefault("warnings", []).append(
                        "low_participation: fewer than 3 agents responded; "
                        "confidence capped"
                    )
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.SUCCESS,
                        result={
                            "signal": consensus_result.signal.value,
                            "score": consensus_result.score,
                            "confidence": consensus_result.confidence,
                        },
                    )
                    # Persist consensus metadata for resume
                    tracker.set_checkpoint_state("consensus_result", {
                        "signal": consensus_result.signal.value,
                        "score": consensus_result.score,
                        "confidence": getattr(consensus_result, "confidence", 0.0),
                        "reasoning": getattr(consensus_result, "reasoning", ""),
                        "metadata": meta,
                    })
            except Exception as e:
                if "consensus" in step_list:
                    output["results"]["consensus"] = {"error": str(e)}
                output.setdefault("warnings", []).append(
                    f"consensus_failed: {e}"
                )
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.FAILURE, diagnostics=str(e)
                    )
            finally:
                elapsed = round(time.perf_counter() - t0, 3)
                step_timings["consensus"] = elapsed
            if tracker:
                tracker.save_checkpoint()

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

    # ------------------------------------------------------------------
    # PHASE 4: committee
    # ------------------------------------------------------------------
    if "committee" in step_list and responses:
        if tracker is not None and tracker.is_step_completed("committee"):
            pass  # already completed — nothing to re-execute
        else:
            sid = tracker.start_step("committee") if tracker else None
            t0 = time.perf_counter()
            try:
                consensus = consensus_result or coordinator.get_consensus(
                    responses, ticker=ticker, context=ctx
                )
                bullish = sum(
                    1 for r in responses.values()
                    if r.signal.value == "bullish"
                )
                bearish = sum(
                    1 for r in responses.values()
                    if r.signal.value == "bearish"
                )
                neutral = len(responses) - bullish - bearish
                committee_result = {
                    "question": question or f"Should we invest in {ticker}?",
                    "verdict": consensus.signal.value,
                    "score": consensus.score,
                    "vote": {
                        "bullish": bullish,
                        "neutral": neutral,
                        "bearish": bearish,
                    },
                    "opinions": [
                        {
                            "agent": r.agent_name,
                            "signal": r.signal.value,
                            "score": r.score,
                        }
                        for r in sorted(
                            responses.values(), key=lambda x: -x.score
                        )
                    ],
                }
                output["results"]["committee"] = committee_result
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.SUCCESS, result=committee_result
                    )
            except Exception as e:
                output["results"]["committee"] = {"error": str(e)}
                output.setdefault("warnings", []).append(
                    f"committee_failed: {e}"
                )
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.FAILURE, diagnostics=str(e)
                    )
            finally:
                elapsed = round(time.perf_counter() - t0, 3)
                step_timings["committee"] = elapsed
            if tracker:
                tracker.save_checkpoint()

    # ------------------------------------------------------------------
    # PHASE 5: debate
    # ------------------------------------------------------------------
    if "debate" in step_list:
        if tracker is not None and tracker.is_step_completed("debate"):
            pass
        else:
            sid = tracker.start_step("debate") if tracker else None
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
                debate_result = {
                    "signal": debate_consensus.signal.value,
                    "score": debate_consensus.score,
                    "rounds": 2,
                }
                output["results"]["debate"] = debate_result
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.SUCCESS, result=debate_result
                    )
            except Exception as e:
                output["results"]["debate"] = {"error": str(e)}
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.FAILURE, diagnostics=str(e)
                    )
            finally:
                elapsed = round(time.perf_counter() - t0, 3)
                step_timings["debate"] = elapsed
            if tracker:
                tracker.save_checkpoint()

    # ------------------------------------------------------------------
    # PHASE 6: sentiment
    # ------------------------------------------------------------------
    if "sentiment" in step_list:
        if tracker is not None and tracker.is_step_completed("sentiment"):
            pass
        else:
            sid = tracker.start_step("sentiment") if tracker else None
            t0 = time.perf_counter()
            try:
                from augur.sentiment import SentimentAnalyzer

                sent = SentimentAnalyzer().get_sentiment(ticker)
                sentiment_result = {
                    "score": sent.overall_score,
                    "volume": sent.volume,
                    "trending": sent.trending,
                }
                output["results"]["sentiment"] = sentiment_result
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.SUCCESS, result=sentiment_result
                    )
            except Exception as e:
                output["results"]["sentiment"] = {"error": str(e)}
                if tracker and sid:
                    tracker.finish_step(
                        sid, StepStatus.FAILURE, diagnostics=str(e)
                    )
            finally:
                elapsed = round(time.perf_counter() - t0, 3)
                step_timings["sentiment"] = elapsed
            if tracker:
                tracker.save_checkpoint()

    # ------------------------------------------------------------------
    # Finalise
    # ------------------------------------------------------------------
    if step_timings:
        output["step_timings_ms"] = {
            k: round(v * 1000, 1) for k, v in step_timings.items()
        }

    _record_step_status(output, step_list)
    output["summary"] = format_workflow_summary(output)

    if tracker is not None:
        bundle = tracker.finish_run()
        output["run_bundle_path"] = str(
            getattr(tracker, "_data_dir", None) or ""
        )
        # Provide a stable, re-computable path hint
        from augur.data_dir import get_data_dir
        output["run_bundle_path"] = str(
            get_data_dir() / "runs" / f"{bundle.run_id}.json"
        )

    return output


def format_workflow_summary(data: Dict[str, Any]) -> str:
    """Format workflow output as human-readable text."""
    lines = [
        f"═══ Augur Workflow: {data['ticker']} ═══",
        f"Steps: {', '.join(data['steps'])}",
        "",
    ]
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
            f"  Signal: {c['signal'].upper()}  Score: {c['score']:.1f}/10  "
            f"Conf: {c['confidence']:.0%}",
            "",
        ]

    if "committee" in results and "error" not in results["committee"]:
        cm = results["committee"]
        v = cm["vote"]
        lines += [
            "── Committee ──",
            f"  Verdict: {cm['verdict'].upper()}  "
            f"Vote: {v['bullish']}B / {v['neutral']}N / {v['bearish']}Be",
            "",
        ]

    if "sentiment" in results and "error" not in results["sentiment"]:
        s = results["sentiment"]
        lines += [f"── Sentiment ──  Score: {s['score']:+.2f}", ""]

    failed_steps = [
        step
        for step, val in results.items()
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
