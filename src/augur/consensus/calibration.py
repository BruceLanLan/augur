# -*- coding: utf-8 -*-
"""Calibration status annotation for consensus probability outputs.

Each probability output from the consensus engine is annotated with a
CalibrationStatus that reflects how much empirical validation backs it.
Products MUST use this status to gate claims like "calibrated" or
"validated" — presenting unvalidated outputs as calibrated is a
compliance risk.

Status lifecycle:
    RAW -> INSUFFICIENT_DATA (not enough resolved outcomes)
    RAW -> EXPERIMENTAL (enough data but hasn't passed OOS gate)
    EXPERIMENTAL -> VALIDATED_CALIBRATED (passed OOS gate)
"""

from enum import Enum


class CalibrationStatus(Enum):
    """Calibration state for a consensus probability output.

    RAW
        Default state. No calibration assessment has been performed.
        Products should label these outputs as "raw" or "uncalibrated".

    INSUFFICIENT_DATA
        Fewer than MIN_SAMPLES resolved outcomes are available.
        Products MUST NOT display "calibrated" — there isn't enough
        evidence to support that claim.

    EXPERIMENTAL
        Enough resolved outcomes exist (>= MIN_SAMPLES), but the
        calibration signal has not passed the OOS gate.
        Products may label these as "experimental" but NOT
        "validated" or "calibrated".

    VALIDATED_CALIBRATED
        Enough resolved outcomes AND the calibration signal passed
        the pre-registered OOS gate.
        Products may label these as "validated" and "calibrated".
    """

    RAW = "raw"
    EXPERIMENTAL = "experimental"
    VALIDATED_CALIBRATED = "validated-calibrated"
    INSUFFICIENT_DATA = "insufficient-data"


# Minimum number of resolved outcomes required to move beyond
# INSUFFICIENT_DATA. Below this threshold, any "calibration" claim
# is statistically meaningless — a single-digit number of resolved
# outcomes cannot distinguish signal from noise in calibration
# metrics (ECE, reliability curves, etc.).
MIN_SAMPLES = 30


def determine_status(
    n_resolved: int,
    oos_passed: bool = False,
    assessment_done: bool = False,
) -> CalibrationStatus:
    """Determine CalibrationStatus from evidence counts and gate results.

    Args:
        n_resolved: Number of resolved outcomes available.
        oos_passed: Whether the OOS gate pre-registered thresholds
            were met.
        assessment_done: Whether any calibration assessment has been
            performed at all. If False (default), the output stays at
            RAW regardless of other evidence.

    Returns:
        The appropriate CalibrationStatus.
    """
    if not assessment_done:
        return CalibrationStatus.RAW
    if n_resolved < MIN_SAMPLES:
        return CalibrationStatus.INSUFFICIENT_DATA
    if oos_passed:
        return CalibrationStatus.VALIDATED_CALIBRATED
    return CalibrationStatus.EXPERIMENTAL
