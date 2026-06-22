# Peer Review #4 — Dashboard & API

**Scope:** `dashboard/app.py` workspace/home/workflow routes, templates, API consistency, `dashboard/static/js/i18n.js` workspace keys, workflow CLI UX (`augur workflow`), cross-module boundaries with `augur.api` and `augur.workspace`.

**Version reviewed:** 10.15.0

---

## Executive summary

The dashboard delivers a rich Bloomberg-style UI with thoughtful error handling (HTML vs JSON by `Accept`), but the API surface grew organically inside a ~4k-line monolith. Workspace APIs are the best-designed REST cluster in the file; workflow exists only on the slim `augur.api` app, not the dashboard server agents typically hit. WebSockets cover analysis/committee/prices but not workspace or workflow progress. i18n for workspace profiles is incomplete in `i18n.js` despite v10.15 profile UI.

**Implemented in this review (no commit):** `GET /api/workspace/profiles/{profile_name}` — fetch full settings for a named profile without switching active.

---

## REST design

### What works

| Pattern | Example | Notes |
|---------|---------|-------|
| Resource nesting | `/api/workspace/profiles/{name}` | Profiles, presets, export/import grouped logically |
| Consistent success envelope | `{"status": "ok", ...}` | Most workspace/home endpoints follow this |
| Structured errors | `api_error_response()` via exception handlers | Machine-readable `code` + `suggestion` for API clients |
| Idempotent reads | `GET /api/workspace`, `GET /api/home/widgets` | Safe for `base.html` bootstrapping |

Workspace module (`augur.workspace`) owns validation (`VALID_PAGES`, `VALID_PRESETS`, profile slug regex) and persistence; routes stay thin. That separation is the model other dashboard features should follow.

### Gaps and inconsistencies

1. **Dual FastAPI apps.** `dashboard.app` (~80+ routes) and `augur.api` (~6 routes) duplicate auth middleware, CORS config, and overlapping endpoints (`/api/personas`, `/api/analyze/{ticker}`). **`POST /api/workflow` exists only in `augur.api`**, not the dashboard. MCP/CLI users get workflow; dashboard HTTP clients do not unless they know to run the separate API server.

2. **Action-style paths elsewhere.** Workspace uses nouns; older routes use verbs: `/api/watchlist/add`, `/api/cron/run-now`, `/api/cache/clear`. Mixed style makes OpenAPI discovery harder.

3. **Incomplete profile CRUD over HTTP.**
   - Before this review: list/create/delete/switch existed; no GET-by-name for full config.
   - Still missing: `PUT /api/workspace/profiles/{name}` to edit a non-active profile without switching (`save_profile()` exists in module but is not exposed).

4. **Redundant list endpoints.** `GET /api/workspace` returns `profiles` summary; `GET /api/workspace/profiles` returns the same list plus `active_profile`. Clients must know which to call.

5. **Response shape drift.** `GET /api/models` returns `{"models": [...]}` without `"status": "ok"`. Persona endpoints mix dict shapes. Workspace is consistent; legacy endpoints are not.

6. **No cache semantics on reads.** Every page load in `base.html` calls `GET /api/workspace` with no `ETag`, `Last-Modified`, or short TTL. Settings and landing redirect could use conditional GET.

7. **CORS env var split.** Dashboard uses `AUGUR_CORS_ORIGINS`; `augur.api` uses `AUGUR_CORS_ALLOW_ORIGINS` with stricter defaults. Deploy docs must mention both.

### Workspace API map (post-fix)

```
GET    /api/workspace                      → active workspace + profile summaries
PUT    /api/workspace                      → save active profile
GET    /api/workspace/presets              → layout presets
GET    /api/workspace/profiles             → profile list
GET    /api/workspace/profiles/{name}      → full profile config (NEW)
POST   /api/workspace/profiles             → create
DELETE /api/workspace/profiles/{name}      → delete
PUT    /api/workspace/active               → switch active
GET    /api/workspace/export               → backup bundle
POST   /api/workspace/import               → restore bundle
GET    /api/home/widgets                   → pinned tickers + collapsed panels
PUT    /api/home/widgets                   → persist home layout
```

---

## Monolithic `app.py` risks

`dashboard/app.py` is **~3,970 lines** and contains:

- Route handlers for analysis, market data, auth, cron, notifications, backtest, history, committee, compare, debate, optimizer, custom personas, workspace, home widgets, health, sitemap, and three WebSocket handlers.
- Inline persistence for home widgets (`_home_widgets_path`, YAML load/save, ticker normalization) — duplicated pattern vs `augur.workspace`.
- Global caches (`_HOME_WIDGETS_CACHE`, rate-limit dicts, registry singletons).
- Template context helpers, SEO, and startup CLI.

**Risks:**

| Risk | Impact |
|------|--------|
| Merge conflicts | Any feature touching dashboard blocks everyone |
| Test isolation | Importing `dashboard.app` loads entire surface area |
| Cognitive load | New contributors cannot find workspace vs market vs auth boundaries |
| Drift | `augur.api` and `dashboard.app` auth/CORS/error handling diverge over time |
| Dead code paths | Scanner page/routes may remain while scanner imports are being removed (v10.15 guard tests) |

**Recommended direction:** FastAPI `APIRouter` modules (`routes/workspace.py`, `routes/market.py`, `routes/ws.py`) plus move home-widget persistence to `augur.home` or extend `augur.workspace`. Keep `app.py` as wiring only (~200 lines).

---

## WebSocket gaps

Current endpoints:

| Path | Purpose | Auth |
|------|---------|--------|
| `/ws/analyze/{ticker}` | Stream per-agent results + consensus | `_ws_api_token_ok` |
| `/ws/committee` | Stream committee opinions + verdict | same |
| `/ws/prices` | Price stream (connection pool) | same |

**Gaps:**

1. **No workspace sync.** Changing profile in Settings does not push to other tabs; each tab re-fetches on navigation. A lightweight `/ws/workspace` or Server-Sent Events channel would fix multi-tab drift.

2. **No workflow progress.** `run_workflow` can run fetch → analyze → consensus → committee sequentially (seconds to minutes). CLI prints a summary at the end; API returns only when complete. Long-running steps need streaming parity with `/ws/analyze`.

3. **Auth bypass surface.** HTTP middleware does not run on WebSocket handshake; auth is manually duplicated in each handler. A missed check on a new WS route would expose analysis without token.

4. **No reconnection contract.** Clients lack documented heartbeat, resubscribe, or error codes beyond `1008 Unauthorized`.

5. **Prices socket is receive-only.** Handler accepts connection and sends initial snapshot but does not document client subscription messages for ticker subsets.

6. **HTML clients vs WS.** Stock analysis page may still poll HTTP while committee uses WS — inconsistent real-time story.

---

## Workflow CLI UX

`augur workflow TICKER` (v10.15) is a solid first-class command:

- `--steps` with validated list and helpful `Valid steps:` on error
- `--json` strips human `summary` for piping
- `--agents` / `--question` passed through to committee step

**Friction points:**

1. **Split entry points.** Same pipeline via CLI, MCP (`augur_workflow`), and `POST /api/workflow` on `augur.api` only — not dashboard. Documentation must clarify which server to run.

2. **Default steps aligned** (`fetch,analyze,consensus`) across CLI and API — good — but help text lists committee/debate/sentiment without indicating cost/latency.

3. **No `--dry-run` or `--list-steps`.** Users cannot preview step order without reading source.

4. **Text output is summary-only.** Non-JSON mode prints `format_workflow_summary()`; intermediate step JSON is discarded. Debugging a failed committee step requires `--json` or re-run with fewer steps.

5. **No dashboard UI.** Workflow is agent/CLI-first; settings workspace has no “run pipeline” panel.

---

## i18n.js workspace keys

Two parallel i18n systems coexist:

- **`dashboard/static/js/i18n.js`** — embedded zh/en/ja/ko maps; drives `data-i18n` and `_t()` at runtime.
- **`dashboard/i18n/en.json`, `zh.json`** — partial JSON with `workspace.*` snake_case keys; not wired to the same key IDs as HTML.

**Coverage gap (v10.15 profiles):** `settings.html` references profile-management keys used only via `_t(..., 'fallback')`:

- `settings-workspace-profile-label`, `-create`, `-delete`, `-switched`, `-name-required`, `-created`, `-cannot-delete`, `-delete-confirm`, `-deleted`

These are **absent from `i18n.js`** and from `test_i18n_workspace_v10_15.WORKSPACE_KEYS`. Non-English users see English fallbacks for profile CRUD toasts and confirm dialogs.

**Naming drift:** JSON uses `workspace.preset_analyst`; JS/HTML uses `workspace-preset-analyst`. Tests enforce JS keys but not JSON↔HTML parity for profiles.

**Recommendation:** Add profile keys to all four `i18n.js` locales; extend `WORKSPACE_KEYS` in tests; either map JSON `workspace.profile_*` to the same IDs or document JSON as legacy/unused.

---

## Three dashboard improvements

1. **Router split + shared API package.** Extract workspace/home routes into `dashboard/routes/workspace.py`; mount on app. Move home-widget YAML logic next to `augur.workspace`. Reduces `app.py` by ~300 lines and matches the clean workspace module boundary.

2. **Conditional GET for workspace.** Add `ETag` derived from workspace file mtime + active profile hash on `GET /api/workspace`. `base.html` sends `If-None-Match` — cuts redundant fetches on every navigation.

3. **Complete workspace i18n + single source.** Add nine profile keys to `i18n.js` (zh/en/ja/ko); update `en.json`/`zh.json` with matching semantic keys; extend `test_i18n_workspace_v10_15.py` so profile UI cannot ship with English-only fallbacks again.

---

## Two cross-module critiques

### 1. Dashboard vs `augur.api` duplication

Two FastAPI applications expose overlapping analysis endpoints with different CORS env vars, auth exempt paths, and feature sets (workflow only on API). Agents integrating via HTTP must choose the correct process (`python -m dashboard.app` vs `uvicorn augur.api:app`). **Consolidate to one ASGI app with optional static/template mounting**, or clearly delegate: dashboard imports and mounts `augur.api` routers for `/api/personas`, `/api/analyze`, `/api/workflow`.

### 2. Home widgets persistence bypasses `augur.workspace`

Terminal workspace settings live in `~/.augur/workspace.yaml` with profiles, export/import, and tests. Home dashboard widgets live inline in `app.py` writing `~/.augur/home_widgets.yaml` with duplicate YAML helpers. **User backup via `/api/config/export` may not include home widgets** unless explicitly merged. Extract to `augur.home_widgets` (or nest under workspace profiles as `home_layout`) so export/import and MCP tooling see one preferences model.

---

## API improvement implemented (this review)

**`GET /api/workspace/profiles/{profile_name}`**

Returns full `workspace` dict for a named profile without calling `PUT /api/workspace/active`. Uses existing `get_profile()` from `augur.workspace`. Response:

```json
{
  "status": "ok",
  "profile": "day-trading",
  "active": false,
  "workspace": { "layout_preset": "analyst", "...": "..." }
}
```

404 when slug is invalid or profile missing. Test added in `tests/test_workspace_profiles_v10_15.py`.

---

## Test plan

```bash
python3 -m pytest tests/test_workspace_profiles_v10_15.py tests/test_i18n_workspace_v10_15.py tests/test_workflow_cli_v10_15.py -v --tb=short
```
