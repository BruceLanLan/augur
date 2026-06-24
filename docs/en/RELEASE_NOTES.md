# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

## What this update fixes

Live testing surfaced three reports: "the homepage dashboard won't respond to clicks at all," "data isn't showing up in a lot of places," and "the investment committee and deep report have problems too." v10.16.4 fixed a Kelly-position display bug in the committee (numbers like "1990.0%"). v10.16.5 root-caused and fixed 11 homepage endpoints freezing the event loop. This release (v10.16.6) traces the same root cause into the investment committee's and deep report's own code path — **but live testing found this only significantly reduces the freeze, it does not fully eliminate it**. See "Known limitation" below.

Root cause, identical to v10.16.5: `analyze_ticker` (full-persona ticker analysis), `report_ticker` (the Deep Report endpoint), `api_committee`, `api_compare`, `api_debate`, and 3 others — 8 endpoints total — were declared `async def` but had zero `await` anywhere in their bodies. Internally they made blocking, synchronous yfinance network calls and ran all 18 personas' analysis synchronously. The dashboard server runs as a single process with a single event loop, so generating one committee verdict or deep report froze that loop for its entire duration — every other request the server was handling at the same time, including other users' clicks on other pages, froze along with it.

Two streaming endpoints (`/ws/analyze`, `/ws/committee`) have to stay `async def` because the WebSocket protocol requires it, so they couldn't get the same one-line fix — instead, their blocking network calls were offloaded to a thread pool.

## What's fixed

- The 8 affected endpoints (single-ticker analysis, deep report, committee, compare, debate, persona comparison, single-persona opinion, batch watchlist analysis) are now declared as plain synchronous functions, dispatched by FastAPI to its background thread pool instead of running on the event loop.
- `/ws/analyze` and `/ws/committee` now run their blocking yfinance calls through `run_in_threadpool` instead of directly on the event loop, while staying `async def` to satisfy the WebSocket protocol.
- Fixed a related latent bug along the way: `analyze_ticker`'s fire-and-forget notification dispatch relied on `asyncio.get_event_loop()`, which only works reliably from the main thread while a loop is running. Once the handler moved into a worker thread pool, that call would have silently failed (swallowed by a nearby `except Exception`), breaking rule notifications without any visible error. Replaced with a plain background thread — same fire-and-forget behavior, no dependency on an event loop being present.
- Expanded the regression-guard test from 11 to 19 endpoints, asserting they must stay sync `def` so this class of bug can't silently come back.

## Known limitation (not fully fixed by this release)

After converting the handlers, we didn't stop at "is it structurally `async def` or not" — we re-ran a real concurrency test. While `/api/committee` was running (all 18 personas), a concurrently-issued, normally-instant request still took over 3 seconds to return, sometimes longer than the committee request's own duration. Five concurrent fast requests with no committee running at all stayed under 21ms, confirming the threadpool dispatch itself isn't the bottleneck.

The real cause here is different from v10.16.5's: the 18 personas' `analyze()` calls are CPU-bound, not I/O-bound. Moving CPU-bound work into a worker thread doesn't make it run in true parallel in CPython — only one thread can hold the GIL and execute bytecode at a time, and one thread doing sustained CPU work can severely starve other threads' requests (the well-known GIL "convoy effect"). A full fix would mean either optimizing `analyze()`'s own CPU time, or moving it somewhere that actually parallelizes (a process pool, or multiple server worker processes) — both bigger changes, deferred pending user direction, since the latter requires solving cross-process sharing of in-memory singletons, caches, and rate-limit counters.

Net effect of this release: committee/deep-report generation no longer makes the *entire* dashboard server completely unresponsive for the whole duration (the original bug is gone), but other users/pages will still see multi-second delays during that window.

## Test status

Full suite: **2095 tests passing** (excluding 5 tests that require network access; 2100 including them), 0 failures.

## How this was found

After fixing the 11 homepage endpoints in v10.16.5, we did a full sweep for the same pattern: every `async def` handler in `dashboard/app.py` that calls `fetch_market_context` or runs persona analysis directly. That turned up 8 more endpoints and 2 WebSocket handlers with the identical problem — and they happened to be exactly the committee and deep-report code the user had named in their original report.

See [CHANGELOG.md](../../CHANGELOG.md) for the full technical change log.
