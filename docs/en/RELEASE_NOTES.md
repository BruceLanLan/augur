# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

## What this update fixes

The last update (v10.16.1) let agents read and write your terminal workspace. This one focuses on two lower-level issues that still show up in day-to-day use:

1. **A single failed step in `augur_workflow` used to take down the whole pipeline.** Run `fetch → analyze → consensus → committee` and if the consensus step throws (say, due to missing data), the entire pipeline aborted — even the fetch/analyze results computed earlier were thrown away.
2. **Agents polling your workspace config got a full payload every time, even when nothing changed.** If your agent checks your terminal config periodically, every check was a full JSON round-trip regardless of whether you'd touched anything.

## What's new

### 1. `augur_workflow` no longer aborts on a single step's failure

If analyze / consensus / committee throws, the error is now captured in that step's own result (as `{"error": "..."}`) and the rest of the pipeline keeps running instead of stopping cold. The final summary report has a new "Step Errors" section, so you can see exactly which step failed and why without digging through logs.

### 2. Workspace reads support conditional requests (ETag), cutting wasted traffic

`mcp_augur_workspace_get` now returns an ETag. If your agent passes that ETag back on the next call and the config genuinely hasn't changed, the server just returns "not modified" instead of re-sending the full config. Useful for agents that poll frequently.

## Doc correction

The last release notes incorrectly listed the user feedback path (`~/.augur/feedback/`, overridable via `USER_FEEDBACK_DIR`) as "not yet implemented." It actually shipped earlier, in v10.15.0's third consensus-engine round, with test coverage already in place. This update corrects that documentation — no new code changed as a result.

## Test status

Full suite: **2072 tests passing**, 0 failures.

## What's next

The only item left in the P1 backlog is P1-9 (splitting up the dashboard's router file — a purely internal code-organization change with no user-facing effect). It's intentionally on hold until after some real-world use and feedback on the product as it stands today.

See [CHANGELOG.md](../../CHANGELOG.md) for the full technical change log.
