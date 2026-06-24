# Augur Release Notes

> Plain-language feature notes for users (for the technical diff, see [CHANGELOG.md](../../CHANGELOG.md)).

## What this update fixes

The "data isn't showing up in a lot of places" report from live testing was already partly addressed by v10.16.5/v10.16.6 (homepage + committee/deep-report). This release (v10.16.7) continues the same live-testing sweep across the rest of the dashboard (history, optimizer, portfolio, watchlist, scanner, signals, settings, chat) and found two concrete data-correctness bugs.

## What's fixed

- **The History page's (`/history`) 52-week calendar heatmap never rendered**: the page requested `/api/history?page=1&per_page=365`, but the endpoint's paginated mode caps `per_page` at 100 and returns HTTP 400 above that — the frontend's empty `.catch()` swallowed the error silently, so the calendar card simply never appeared, with no visible error. Fixed by switching to the endpoint's unpaginated `limit` mode (`/api/history?limit=365`, capped at 500), which already exists and is exactly what the calendar needs (a flat list of recent records, no pagination metadata).
- **The portfolio optimizer (`/optimizer`, `/api/optimize`) computed both its displayed Sharpe ratio and its actual optimal weights with mismatched units**: the optimizer works internally with *daily* returns, but received the risk-free rate as an *annual* rate (e.g. 0.02 for 2%) and subtracted it directly from daily returns before dividing by daily volatility. Since a typical daily mean return (~0.1%-0.3%) is tiny next to an annual rate like 2%, this made the "excess return" strongly negative for nearly every asset — skewing not just the displayed Sharpe ratio (observed -1.44 where the correct value is roughly +2.0) but the analytical max-Sharpe weight solution itself, meaning the "optimal" portfolio it recommended wasn't actually optimal. Fixed by converting the risk-free rate to a daily rate (dividing by 252 trading days) before combining it with daily returns/volatility anywhere in the optimizer. A related follow-up was caught right after: the page already displays return/volatility as annualized figures, but was showing the Sharpe ratio on a daily basis next to them — three numbers on inconsistent time bases, which still looks wrong even after the unit fix above. Now the displayed Sharpe ratio is annualized too (×√252), so all three numbers are on the same basis.

## Test status

Full suite: **2100 tests passing**, 0 failures.

## How this was found

Continuing the same live-testing approach as v10.16.5/v10.16.6, but this time not looking for the `async def`/event-loop class of bug — instead, walking every remaining dashboard page not yet covered, mapping each page's `fetch()` calls to its backend endpoint, and exercising each one against the running dev server with real tickers, checking for error responses, mismatched response shapes, or numerically implausible results. Most endpoints checked out fine; these two were genuine defects.

The GIL concurrency limitation documented in v10.16.6 (committee/deep-report slowdowns under load) was left untouched this release, per the user's earlier decision to park it.

See [CHANGELOG.md](../../CHANGELOG.md) for the full technical change log.
