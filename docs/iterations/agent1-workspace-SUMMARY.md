# Agent1 Workspace QA — 10-Round Summary

**Branch:** `feature/v9-dev`  
**Scope:** `src/augur/workspace.py`, dashboard workspace API, `settings.html`, `base.html`, scoped pytest suites  
**Final result:** **252/252 tests passed**

## Net improvements

| Area | Change |
|------|--------|
| API | Added `PUT /api/workspace/profiles/{name}` for editing non-active profiles via `save_profile()` |
| API | Hardened profile slug validation on GET/PUT using `normalize_profile_name` |
| UI | `deleteWorkspaceProfile()` blocks active profile (not only `default`) |
| UI | `saveWorkspaceConfig` uses `_workspaceState.layout_preset`; clears landing-route session flag on save |
| UI | `applyWorkspacePreset` tracks `committee_preset` in client state |
| i18n | Extended `WORKSPACE_KEYS` / JSON parity for profile + persona keys (zh/en) |
| Tests | +9 tests: PUT profile API, invalid slugs, non-active edit, HTML guards, module errors |

## Round log

| Round | Tests | P0/P1 fixes |
|-------|-------|-------------|
| 1 | 73 pass | Baseline gap analysis |
| 2 | 248 pass | PUT profile endpoint |
| 3 | 248 pass | Slug normalization |
| 4 | 248 pass | Delete active profile UI guard |
| 5 | 252 pass | i18n test + JSON keys |
| 6 | 252 pass | Preset save + committee_preset |
| 7 | 252 pass | Session flag on save + peer-review test |
| 8 | 252 pass | Module + HTML regression tests |
| 9 | 252 pass | base.html encodeURIComponent test |
| 10 | 252 pass | Final green verification |

## Deferred (P3)

- ETag / conditional GET on `GET /api/workspace`
- Home widgets in unified workspace export
- Cross-tab workspace WebSocket sync
