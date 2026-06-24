# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

## What this update fixes

While actually using the app, the user found that the Investment Committee page's "suggested position size" was showing nonsense numbers like **1990.0%** instead of the correct 19.9%.

Root cause: the position-size percentage is already a percentage value by the time it leaves the consensus layer (`src/augur/registry.py`'s half-Kelly sizing — e.g. `19.9` literally means 19.9%), but the Dashboard's `/api/committee` and `/ws/committee` endpoints multiplied it by 100 again, turning 19.9% into 1990%. The CLI, MCP tool, and Deep Report all go through a different code path and didn't have this bug — it was specific to the committee page.

## What's fixed

- `/api/committee` (REST) and `/ws/committee` (WebSocket) no longer double-multiply the `kelly_pct` field — it now matches what the Deep Report shows.
- Added two regression tests covering both endpoints, asserting the position percentage never exceeds the 20% half-Kelly cap, so a future re-introduction of this kind of scaling bug gets caught immediately.

## Test status

Full suite: **2072 tests passing** (excluding 5 tests that require network access; 2077 including them), 0 failures.

## What's still open

The same testing session also surfaced two other reports: homepage Dashboard widgets being completely unclickable, and missing data across several pages. We checked the backend report / committee / workspace / home-widgets endpoints directly via curl and a WebSocket client — the data itself is correct — but this environment has no browser automation tool, so we couldn't reproduce click-level interaction the way the user did, and static JS/CSS review didn't turn up a definitive root cause. We need browser console output or screenshots from the user to keep investigating.

See [CHANGELOG.md](../../CHANGELOG.md) for the full technical change log.
