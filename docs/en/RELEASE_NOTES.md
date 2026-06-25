# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

## What this update fixes

This release (v10.16.8) addresses the one item `docs/AGENT_PEER_REVIEW_SYNTHESIS.md` flags as the system's only remaining "foundational architectural risk": market regime detection (bull/bear/sideways crossed with high/low volatility). The hard rule attached to it was "do not treat consensus outputs as risk inputs until P2-3 regime validation lands."

That risk actually has two halves: (1) regime classification could flip-flop from a single noisy day, and (2) the hand-picked `_REGIME_ADJUSTMENTS` multipliers themselves have never been validated to actually help. **This release resolves only half (1).** Half (2) is left for a later P2-4 (unified out-of-sample calibration pipeline) — it is not touched here, and this release should not be read as a claim that it is.

## What's fixed

- **Regime detection had no smoothing — a single noisy day could flip it**: the previous implementation classified the regime from a single live snapshot of VIX/SPY each time it ran. VIX oscillating around the 25 threshold, or a one-day spike, could flip the regime back and forth between adjacent buckets — and that regime gets blended 35% into the persona weights feeding investment consensus, so frequent flips meant frequent, mostly-meaningless perturbation of those weights. This release adds a "confirmation window": a new regime now has to persist for 3 consecutive trading days before it's accepted, and the VIX high/low-volatility threshold switched from one hard cutoff to an asymmetric band (enter at 25, exit at 23) to reduce boundary jitter.
- **The `date_str` parameter was decorative — there was no real historical/point-in-time capability**: the function signature accepted a date, but the code never actually used it internally, always fetching "now" data regardless. This release makes it actually work — passing a historical date now fetches real VIX/SPY history up to (and not including) that date for classification. Along the way, a related bug was found and fixed: VIX and SPY historical data come back timezone-localized differently (Chicago vs. New York), so the same trading day had mismatched timestamps between the two series, causing them to silently fail to align. This didn't affect anything visible day-to-day, but it would have made historical backtesting return nothing.

## How this was validated

A manual backtest script (`scripts/regime_backtest_v2.py`, not part of the automated test suite since it needs live network access) pulls about 9 years of VIX/SPY history (2015-present) and runs the old single-snapshot classifier and the new confirmation-window classifier side by side over every trading day:

- **Flip count**: 389 (old) vs. 101 (new).
- **Whipsaw count** (A flips to B and back to A within 3 days): 146 (old) vs. just 10 (new).
- **Responsiveness**: checked against the 2020 COVID crash and the 2022 bear market — the new method entered "high-vol-bear" only 2-4 days later than the old one, so it didn't become sluggish. The 2018 Q4 window looked odd at first glance (old fired in October, new not until December), but on inspection the October trigger was the old method getting fooled by a single noisy day where both thresholds happened to cross briefly without persisting — exactly the kind of false alarm the confirmation window is designed to filter. The new method's December entry lines up with the real, sustained selloff. That's the confirmation window working as intended, not a lag.

## Test status

Full suite: **2108 tests passing** (2100 existing + 8 new), 0 failures.

## What this release does NOT do

Whether the specific numbers in `_REGIME_ADJUSTMENTS` (e.g. boosting Howard Marks's weight to 1.32 in a high-vol bear market) actually improve investment outcomes was not touched or validated here — that requires a larger out-of-sample replay framework and is left for a future P2-4 effort.

See [CHANGELOG.md](../../CHANGELOG.md) for the full technical change log.
