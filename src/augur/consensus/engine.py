# -*- coding: utf-8 -*-
"""ConsensusEngine — standalone consensus computation extracted from DecisionCoordinator."""

import logging
import math
import time
from typing import Dict, Optional

from augur.personas.base import AgentResponse, MarketContext, SignalType

logger = logging.getLogger(__name__)


class ConsensusEngine:
    """Stateless consensus aggregator.

    Extracted from DecisionCoordinator.get_consensus so it can be tested
    independently and reused outside the registry.
    """

    def compute(
        self,
        results: Dict[str, AgentResponse],
        ticker: str = "",
        date_str: str = None,
        context: Optional[MarketContext] = None,
        analysis_ms: float = 0.0,
    ) -> AgentResponse:
        """Compute consensus signal with industry weighting."""
        t0_consensus = time.perf_counter()
        if not results:
            return AgentResponse(
                agent_id="consensus",
                agent_name="Consensus",
                signal=SignalType.NEUTRAL,
                confidence=0,
                score=0,
                reasoning="No results",
            )

        # --- Industry-aware weights ---
        from augur.consensus import (
            build_consensus_weights,
            load_global_consensus_weights,
            restrict_weights_to_agents,
        )
        from augur.consensus.paths import load_feedback_json
        from augur.consensus.probability_calibrator import calibrate_confidence
        from augur.consensus.meta_model import MetaModel
        from augur.consensus.risk_manager import RiskManager
        from augur.consensus.rolling_ic import load_rolling_ic_weights

        weight_ctx = build_consensus_weights(ticker, date_str, context)
        weights = weight_ctx.weights
        valid_agent_ids = [
            aid for aid, resp in results.items() if resp.signal != SignalType.ERROR
        ]
        if weights and valid_agent_ids:
            weights = restrict_weights_to_agents(weights, valid_agent_ids)
        regime = weight_ctx.regime
        regime_features = weight_ctx.regime_features

        # --- Correlation diversity penalty ---
        corr_matrix = {}
        try:
            corr_data = load_feedback_json("agent_correlation.json")
            corr_matrix = corr_data.get("correlation_matrix", {})
        except Exception as exc:
            logger.warning("Failed to load agent correlation matrix: %s", exc)

        # --- Signal counting and scoring ---
        signal_counts = {SignalType.BULLISH: 0.0, SignalType.NEUTRAL: 0.0, SignalType.BEARISH: 0.0}
        total_score = 0.0
        total_weight = 0.0
        total_confidence = 0.0
        all_findings = []
        all_risks = []
        adjusted_weights = {}

        # Global optimized weights as default base
        global_weights = load_global_consensus_weights()

        # Rolling IC dynamic weight override
        rolling_ic_weights = load_rolling_ic_weights() or {}

        # v8: Learned weights from LearningEngine (60% base + 40% learned)
        learned_weights = {}
        try:
            # Lazy import to avoid circular: registry imports ConsensusEngine; we import back lazily
            from augur.registry import _get_learning_engine
            le = _get_learning_engine()
            if le.has_learned_weights:
                learned_weights = le.get_weights()
        except Exception:
            pass

        # Normalize rolling IC weights before blending
        if rolling_ic_weights:
            total_ric = sum(rolling_ic_weights.values())
            if total_ric > 0:
                rolling_ic_weights = {k: v / total_ric for k, v in rolling_ic_weights.items()}

        valid_count = sum(
            1 for r in results.values() if r.signal != SignalType.ERROR
        )
        default_weight = 1.0 / valid_count if valid_count else 1.0

        for agent_id, response in results.items():
            if response.signal == SignalType.ERROR:
                continue
            if weights and agent_id in weights:
                w = weights[agent_id]
            else:
                w = global_weights.get(agent_id, default_weight)

            if rolling_ic_weights and agent_id in rolling_ic_weights:
                w = 0.5 * w + 0.5 * rolling_ic_weights[agent_id]

            # v8: Blend learned weights when available
            if learned_weights and agent_id in learned_weights:
                w = 0.6 * w + 0.4 * learned_weights[agent_id]

            w *= self._normalize_coverage_confidence(response.coverage_confidence)

            # Sector-aware weight boosting
            if context and hasattr(context, "sector") and context.sector:
                sector_lower = (context.sector or "").lower()
                industry_lower = (context.industry or "").lower() if hasattr(context, "industry") else ""
                is_tech = sector_lower in ("technology", "information technology") or any(
                    kw in industry_lower
                    for kw in ["artificial intelligence", "machine learning", "semiconductor", "software"]
                )
                is_financial = "financial" in sector_lower
                is_healthcare = "health" in sector_lower or "medical" in sector_lower

                if is_tech and agent_id in ("cathie_wood", "aschenbrenner", "thiel"):
                    w *= 1.3
                elif is_financial and agent_id in ("buffett", "graham", "marks"):
                    w *= 1.2
                elif is_healthcare and agent_id == "fisher":
                    w *= 1.2

            # Diversity penalty
            penalty = 1.0
            if corr_matrix:
                for processed_agent in adjusted_weights.keys():
                    corr = corr_matrix.get(agent_id, {}).get(processed_agent, 0)
                    if corr > 0.7:
                        penalty *= max(0.3, 1.0 - (corr - 0.7))

            adjusted_w = w * penalty
            adjusted_weights[agent_id] = adjusted_w

            if response.signal in signal_counts:
                signal_counts[response.signal] += adjusted_w
            total_score += response.score * adjusted_w
            total_confidence += response.confidence * adjusted_w
            total_weight += adjusted_w
            all_findings.extend(response.key_findings)
            all_risks.extend(response.risks)

        # Normalize
        if total_weight > 0:
            total_score /= total_weight
            total_confidence /= total_weight
        else:
            total_score = 0.0
            total_confidence = 0.0
            consensus_signal = SignalType.NEUTRAL

        # v8: Apply sentiment factor (±0.5 max, clamped to [0,10])
        if ticker:
            try:
                from augur.registry import _get_sentiment_analyzer
                sentiment_factor = _get_sentiment_analyzer().get_sentiment_factor(ticker)
                total_score = max(0.0, min(10.0, total_score + sentiment_factor))
            except Exception:
                pass

        # Weighted majority vote — directional ties resolve to NEUTRAL
        if sum(signal_counts.values()) <= 0:
            consensus_signal = SignalType.NEUTRAL
        else:
            max_weight = max(signal_counts.values())
            tied = [sig for sig, w in signal_counts.items() if w == max_weight]
            if len(tied) == 1:
                consensus_signal = tied[0]
            elif SignalType.NEUTRAL in tied:
                consensus_signal = SignalType.NEUTRAL
            elif SignalType.BULLISH in tied and SignalType.BEARISH in tied:
                consensus_signal = SignalType.NEUTRAL
            else:
                consensus_signal = tied[0]

        # Regime note
        regime_note = ""
        if regime:
            regime_labels = {
                "BULL_LOW_VOL": "Bull Low Vol",
                "BULL_HIGH_VOL": "Bull High Vol",
                "BEAR_LOW_VOL": "Bear Low Vol",
                "BEAR_HIGH_VOL": "Bear High Vol",
                "SIDEWAYS": "Sideways",
            }
            regime_label = regime_labels.get(regime, regime)
            industry_note = ""
            if weight_ctx.industry != "general":
                industry_note = f" | Industry: {weight_ctx.industry_label}"
            regime_note = f" | Regime: {regime_label}{industry_note}"

        # --- Probability calibration ---
        calibrated_confidence = min(0.95, total_confidence)
        calibrated_confidence = calibrate_confidence(total_score, calibrated_confidence, "consensus")

        # --- Meta-model blending ---
        # NOTE: MetaModel.load() always returns an active instance in this stub
        # implementation (never None outside of tests that explicitly patch it),
        # and predict() is just the cross-agent median — it has never been
        # validated to improve anything. Default weight is 0 so this stub is
        # inert out of the box; the blend/config path stays intact so a real
        # meta model can be dropped in later, and a user can still opt in via
        # consensus.meta_model_weight if they want the median blend today.
        mm = MetaModel.load()
        if mm is not None:
            from augur.config import get_config
            meta_weight = get_config().get("consensus", {}).get("meta_model_weight", 0.0)
            try:
                meta_weight = max(0.0, min(1.0, float(meta_weight)))
            except (TypeError, ValueError):
                meta_weight = 0.0
            if meta_weight > 0:
                agent_scores_dict = {aid: resp.score for aid, resp in results.items()}
                mm_score = mm.predict(agent_scores_dict)
                total_score = (1 - meta_weight) * total_score + meta_weight * mm_score

        result = AgentResponse(
            agent_id="consensus",
            agent_name="Multi-Agent Consensus",
            signal=consensus_signal,
            confidence=calibrated_confidence,
            score=total_score,
            reasoning=f"Consensus from {len(results)} agents{regime_note}",
            key_findings=all_findings[:5],
            risks=all_risks[:3],
        )

        # --- Risk Manager veto ---
        ctx_for_risk = context
        try:
            if ctx_for_risk is None:
                for r in results.values():
                    meta_ctx = r.metadata.get("context")
                    if meta_ctx and hasattr(meta_ctx, "ticker"):
                        ctx_for_risk = meta_ctx
                        break
            if ctx_for_risk is None:
                beta = 1.0
                for r in results.values():
                    if r.beta and r.beta != 1.0:
                        beta = r.beta
                    break
                ctx_for_risk = MarketContext(ticker=ticker or "UNKNOWN", beta_1y=beta)
            vix = regime_features.get("vix") if regime_features else None
            rm = RiskManager()
            verdict = rm.evaluate(ctx_for_risk, result, results, regime=regime, vix=vix)
            result = rm.apply_veto(result, verdict)
        except Exception as exc:
            logger.warning("Risk manager evaluation failed: %s", exc)

        # --- Kelly position sizing (simplified half-Kelly) ---
        try:
            sig = result.signal.value
            score = result.score
            conf = result.confidence
            # Half-Kelly: f = 0.5 * (p - (1-p)/b) clamped to 0-20%
            if sig == "bullish" and score >= 5:
                # edge = (score - 5) / 5  maps [5,10] → [0,1]
                edge = max(0, (score - 5) / 5)
                full_kelly = edge * conf
                pct = min(20.0, round(full_kelly * 0.5 * 100, 1))
                # Minimum 1% token position for bullish signal with sufficient confidence
                if pct < 1.0 and conf >= 0.5:
                    pct = 1.0
            elif sig == "bearish":
                pct = 0.0
            else:
                pct = max(0.0, round((conf - 0.5) * 3.0, 1))

            position = {
                "position_pct": pct,
                "signal": sig,
                "score": round(score, 2),
                "confidence": round(conf, 3),
                "rationale": f"half-Kelly: {pct:.1f}% (score={score:.1f}, conf={conf:.0%})",
            }
            result.metadata["position_sizing"] = position
            result.metadata["position_pct"] = pct
        except Exception:
            pass

        if regime_features:
            result.metadata["regime_features"] = regime_features

        if adjusted_weights:
            result.metadata["weighting"] = {
                "industry": weight_ctx.industry,
                "industry_label": weight_ctx.industry_label,
                "regime": regime,
                "participating_agents": len(adjusted_weights),
                "agent_weights": {
                    aid: round(w, 4) for aid, w in sorted(adjusted_weights.items())
                },
            }

        # 10x multi-factor overlay
        try:
            from scanner.ten_x_screener import attach_ten_x_to_consensus
            attach_ten_x_to_consensus(result, context, results)
        except Exception:
            pass

        # When all agents return neutral, the consensus is neutral with score reflecting
        # the weighted average (~5.0). This is expected behavior - it indicates the
        # committee genuinely has no strong conviction in either direction.

        # --- Low participation check ---
        # If fewer than 3 agents returned valid (non-ERROR) responses, flag
        # low confidence since the consensus is based on insufficient diversity.
        valid_results = {k: v for k, v in results.items() if v.signal != SignalType.ERROR}
        if len(valid_results) < 3:
            result.metadata["low_participation"] = True
            result.confidence = max(0.2, result.confidence)
            calibrated_confidence = result.confidence
        if valid_results and sum(
            1 for r in valid_results.values() if r.signal == SignalType.BULLISH
        ) == len(valid_results):
            result.risks.append("All agents bullish - historically this consensus often means overvaluation")
            if ctx_for_risk and hasattr(ctx_for_risk, "pe") and ctx_for_risk.pe > 30:
                result.risks.append(f"PE={ctx_for_risk.pe:.1f}, valuation elevated - consider stop-loss")

        # --- Divergence score (raw non-weighted head-counts) ---
        # Measures bull/bear disagreement independent of agent weights.
        # score=0.0 means all active agents agree; score=1.0 means 50/50 split.
        _bull_raw = sum(1 for r in valid_results.values() if r.signal == SignalType.BULLISH)
        _bear_raw = sum(1 for r in valid_results.values() if r.signal == SignalType.BEARISH)
        _neu_raw = sum(1 for r in valid_results.values() if r.signal == SignalType.NEUTRAL)
        _active_raw = _bull_raw + _bear_raw
        _div_score = round(2.0 * min(_bull_raw, _bear_raw) / _active_raw, 3) if _active_raw > 0 else 0.0
        result.metadata["divergence"] = {
            "score": _div_score,
            "bullish_count": _bull_raw,
            "bearish_count": _bear_raw,
            "neutral_count": _neu_raw,
            "total_valid": len(valid_results),
            # Requires at least 2 agents on each side to avoid 1v1 false alarms
            "is_divergent": min(_bull_raw, _bear_raw) >= 2 and _div_score >= 0.4,
        }

        # Clamp final score to valid range [0, 10]
        if not math.isfinite(result.score):
            result.score = 0.0
        else:
            result.score = max(0.0, min(10.0, result.score))
        if not math.isfinite(result.confidence):
            result.confidence = 0.2
        else:
            result.confidence = max(0.0, min(1.0, result.confidence))

        # --- Timing metadata ---
        consensus_ms = (time.perf_counter() - t0_consensus) * 1000
        logger.debug("get_consensus completed in %.1fms", consensus_ms)
        result.metadata["timing_ms"] = {
            "analysis_ms": analysis_ms,
            "consensus_ms": consensus_ms,
        }

        # v8 Phase A: auto-record predictions + check past outcomes
        # R6 groundwork (2026-07-09): fetch_market_context() never raises --
        # it tags a context data_source="none" when every provider fails
        # (_build_context_from_providers) or data_source="error" when the
        # ticker itself fails input validation before any provider is even
        # tried (confirmed both happen in practice: "none" from real
        # yfinance rate-limiting during watchlist testing, "error" from a
        # too-long/malformed ticker string). Predictions made against either
        # kind of empty context aren't real signal-conditioned judgments and
        # would quietly pollute R6's future calibration sample, so they're
        # skipped here rather than recorded. Still returned normally to the
        # caller -- only the *learning* record is suppressed, not the
        # analysis itself.
        context_is_empty = getattr(context, "data_source", None) in ("none", "error")
        if ticker:
            try:
                from augur.registry import _get_learning_engine, _check_and_record_outcomes
                le = _get_learning_engine()
                # Check if old predictions (>30d) for this ticker need outcomes
                # recorded -- unrelated to *today's* context quality, so this
                # always runs regardless of context_is_empty.
                _check_and_record_outcomes(le, ticker)
                # Record each agent's current prediction for future accuracy
                # tracking -- skipped when today's context is empty.
                if not context_is_empty:
                    for agent_id, resp in results.items():
                        if resp.signal != SignalType.ERROR:
                            le.record_prediction(
                                ticker, agent_id,
                                resp.signal.value, resp.score, resp.confidence,
                            )
            except Exception:
                pass

        return result

    @staticmethod
    def _normalize_coverage_confidence(coverage: float) -> float:
        """Clamp model applicability weight to a finite [0, 1] range."""
        if isinstance(coverage, bool) or not isinstance(coverage, (int, float)):
            return 1.0
        if not math.isfinite(coverage):
            return 1.0
        return max(0.0, min(1.0, float(coverage)))
