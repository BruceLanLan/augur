# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

## What this update fixes

Until now, `augur_workflow` — whether you ran it from the CLI or an agent called it over MCP — always defaulted to the same fixed three steps, `fetch → analyze → consensus`, completely independent of whatever terminal layout preset you'd picked in `/settings`. In other words, "customization" (your chosen layout) and "agentic" (an agent running the analysis pipeline for you) were disconnected: switching to the "trader" layout only changed what the Dashboard showed — it didn't change what an agent actually did when it ran a workflow on your behalf.

## What's new

### `augur_workflow`'s default steps now follow your terminal layout preset

No longer hardcoded to `fetch,analyze,consensus`. The CLI's `--steps` option, the MCP tool `augur_workflow`'s `steps` parameter, and the Dashboard's `/api/workflow` request field all now resolve to a preset-specific default when left empty:

- **Analyst**: `fetch,analyze,consensus` — same as before, full due-diligence flow.
- **Trader / Minimal**: `fetch,consensus` — skips the per-master score breakdown for a faster signal.
- **Committee**: `fetch,analyze,consensus,committee` — includes the committee vote directly.

If you pass `--steps` explicitly (or specify `steps` in an MCP call), that still takes priority — this only kicks in when you don't specify anything.

This means the layout you choose in `/settings` no longer just changes what the Dashboard displays — it now also changes what an agent (Claude Desktop / Hermes / OpenClaw, etc.) does by default when it runs a workflow for you. Your customization choices now actually shape agentic behavior.

## Test status

Full suite: **2075 tests passing** (including 5 tests that require network access), 0 failures.

## What's next

The only item left in the P1 backlog is P1-9 (splitting up the dashboard's router file — a purely internal code-organization change), still on hold. One P2 item is flagged as a foundational risk rather than a feature gap: **the regime detector (P2-3) currently has no smoothing/hysteresis and no historical backtest** — we re-verified this while working on this release, and it's still a genuinely open risk; don't treat consensus output as a risk-management input until it's addressed. The remaining P2 items (lazy persona loading, real-time workflow progress streaming, etc.) will be scheduled as needed.

See [CHANGELOG.md](../../CHANGELOG.md) for the full technical change log.
