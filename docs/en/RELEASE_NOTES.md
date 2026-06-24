# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

## What this update fixes

Until now, Augur worked like a "Q&A" investment tool: open the Dashboard, type a ticker, get a consensus report from 18 investor personas. Useful, but with two real gaps:

1. **Everyone watches the market differently, but Augur only had one layout.** A day trader wants a different home page than someone doing deep research; some users only trust 4 value-school masters, others want all 18 in the consensus. None of this could be saved or switched before.
2. **Once you connect an AI agent, the agent only "analyzes" — it doesn't know "you."** You could ask Claude/Hermes to call Augur's analysis tools, but the agent had no idea what you'd configured on your Dashboard — it couldn't read your layout preferences or adjust them for you. The agent and your terminal were two disconnected worlds.

This update addresses both, with the same direction we've been building toward: **turn Augur into a Bloomberg-style terminal that users can deeply customize, and let AI agents actually operate that terminal — not just chat alongside it.**

## What's new

### 1. Terminal Workspace — customize your terminal like Bloomberg

- **Layout presets**: analyst (default) / trader / committee / minimal — switch default landing page, hidden nav items, and the live price ticker tape with one click.
- **Multiple named profiles**: save several configs (e.g. "day trading" / "weekend deep research") and switch between them without overwriting the others.
- **See only the masters you trust**: enable a subset of the 18 personas for consensus calculation (e.g. only the 4 value-school masters) — weights are automatically re-normalized rather than split evenly, which matters: "pick 4 masters" and "pick all 18 but only look at 4 opinions" are mathematically different things if you don't renormalize.
- **Committee preset bound to your profile**: switching profiles switches your default committee lineup too.
- Saved locally to `~/.augur/workspace.yaml`, with export/import — bring your setup to a new machine.

Where to find it: Dashboard → Settings.

### 2. AI agents can now read and modify your terminal

This is the most significant piece of this update. If you connect to Augur through Claude Desktop, Hermes Studio, or any MCP-compatible client, the agent can now:

- **Read** your current terminal layout, which masters are enabled, and which committee preset you're using;
- **Modify it on your behalf** — tell the agent "switch me to trader mode and only show value-school opinions" and it can apply that change directly, no need to click through the Dashboard yourself;
- **List, create, switch, and delete** your saved profiles.

In other words, the agent used to be a chat assistant bolted onto the outside of Augur. Now it can sense and operate your actual working environment — which is the real distinction between "agentic" and plain "chat."

### 3. One command runs the whole analysis pipeline (`augur_workflow`)

Previously, running "fetch live data → full-roster analysis → consensus → committee" meant four separate calls. Now one command or one agent call chains it:

```bash
augur workflow NVDA --steps fetch,analyze,consensus,committee
```

It can also be scoped to just the masters you've enabled (automatically linked to your Terminal Workspace's enabled-master setting).

### 4. A stronger consensus engine under the hood

Behind the score, we added a more detailed calculation stack: an industry weighting matrix, market-regime detection and routing, probability calibration, rolling IC (information coefficient) evaluation, macro factors, and risk management. One thing worth calling out specifically:

- There's an internal "median blending" mechanism that pulls the final score partway toward the median of all masters' opinions, to avoid letting one extreme view dominate. The blend ratio used to be hard-coded at 50% and wasn't very transparent. It's now a tunable setting (`consensus.meta_model_weight`) — still 50% by default, but you can set it anywhere from 0 (no blending) to 1 (pure median).

## What this update fixes (bugs)

A code review surfaced a few issues that didn't affect day-to-day use but made results slightly less accurate or robust:

- In some cases, the "analysis timed out" message never actually fired (it was silently caught by an outer error handler instead — functionality was unaffected, only the error message was misleading).
- A background cache module had a concurrency risk; it's now properly locked.
- A few setup docs still referenced an old tool count (9 or 10); they're now updated to the current 13, with the missing tools documented.

## Test status

Full suite: **2065 tests passing**, 0 failures.

## What's next

This update wraps up most of the high-priority items from the last code review: the Committee page now reads your workspace config and auto-applies the matching committee preset, and all 18 masters' `manifest.json` / Hermes configs are back in sync with the current version number and the full 13-tool list. What's left is more architectural polish (per-step status reporting, caching headers on the config endpoint) that won't change day-to-day usage.

See [CHANGELOG.md](../../CHANGELOG.md) for the full technical change log.
