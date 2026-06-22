# -*- coding: utf-8 -*-
"""Simple confidence calibration for consensus scores."""


def calibrate_confidence(score: float, confidence: float, agent_id: str = "consensus") -> float:
    """Map raw confidence toward calibrated range using score extremity."""
    score = max(0.0, min(10.0, score))
    confidence = max(0.0, min(1.0, confidence))
    # Extreme scores (far from 5) deserve slightly higher confidence
    extremity = abs(score - 5.0) / 5.0
    calibrated = confidence * (0.85 + 0.15 * extremity)
    return min(0.95, max(0.05, calibrated))
