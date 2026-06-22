# Peer Review #7 — Docs & i18n

**Reviewer domain:** workflow docs accuracy, workspace docs in `hermes-setup-guide.md`, CHANGELOG completeness, ja/ko workspace i18n, README, `skills/`, `hermes-agents/`, `V9_ROADMAP.md`  
**Cross-review targets:** `agent-integration-guide.md`, `dashboard/static/js/i18n.js`, `dashboard/i18n/{en,zh}.json`, `CHANGELOG.md`  
**Date:** 2026-06-22 · **Scope:** v10.15.0 release documentation and four-language Settings UX

---

## Executive Summary

v10.15 shipped substantial terminal workspace and workflow surfaces, but **user-facing docs lag the implementation**: README version history still stops at v9.0.6, CHANGELOG omits multi-profile workspace and workspace i18n, and `hermes-setup-guide.md` documents only the original single-profile REST examples. **i18n is mostly aligned** for the 16 base workspace keys in zh/en/ja/ko, but **named-profile UI strings were never added** to any language bundle — Japanese and Korean users see English fallbacks for profile create/switch/delete. Workflow documentation is **technically correct on port 8900** but **under-explained** relative to the Dashboard-centric examples elsewhere.

---

## Workflow Docs Accuracy

### Strengths

| Area | Observation |
|------|-------------|
| **Step list** | `agent-integration-guide.md` Method 8 and `skills/README.md` § `augur_workflow` match `run_workflow()` valid steps: `fetch`, `analyze`, `consensus`, `committee`, `debate`, `sentiment`. |
| **CLI examples** | Default chain, full committee chain, `--agents`, `-q`, `--json` examples align with `cli.py workflow_cmd`. |
| **MCP surface** | Hermes setup guides and `skills/README.md` correctly list `augur_workflow` among 10 MCP tools. |
| **Cross-ref** | `docs/reviews/peer-review-02-workflow.md` already audited composability and persona-filter gaps. |

### Gaps

| Gap | Location | Impact |
|-----|----------|--------|
| **REST port context missing** | `agent-integration-guide.md` (zh + en) Method 8 | Examples use `http://localhost:8900/api/workflow` while the rest of the guide uses `:8000` (Dashboard). Readers assume Dashboard exposes workflow; it does not — workflow lives on `augur api` (`src/augur/api.py`, default port 8900). |
| **No `augur api` prerequisite** | Method 8 REST section | Missing one-liner: `augur api --port 8900` (requires `augur-agents[api]`). |
| **Hermes natural-language examples** | `hermes-setup-guide.md` | Correctly mentions `augur_workflow`, but no copy-paste workflow chain example comparable to Method 8 CLI block. |
| **Dashboard vs API split undocumented** | README, hermes-setup, skills | Workspace REST is documented on `:8000`; workflow REST on `:8900` — two servers, never explicitly contrasted in a single table. |

**Verdict:** Workflow docs are **accurate for happy-path copy-paste** once the reader knows which server to start. They fail the **discoverability** bar for integrators who only run `augur serve`.

---

## Workspace Docs in `hermes-setup-guide.md`

### Strengths

- Preset table (`analyst` / `trader` / `committee` / `minimal`) matches `LAYOUT_PRESETS` in `workspace.py` (default pages, hidden nav slugs, ticker tape, committee preset metadata).
- Settings UI path and curl examples for `GET/PUT /api/workspace` and `/api/workspace/presets` are correct for Dashboard port 8000.
- Persistence path `~/.augur/workspace.yaml` is accurate.

### Gaps vs implementation (v10.15 multi-profile)

| Feature in code | Documented in hermes-setup? |
|-----------------|------------------------------|
| Named profiles (`/api/workspace/profiles`, `/active`, create/delete) | **No** |
| `enabled_personas` roster filter | Mentioned in `skills/README.md` only; not in hermes-setup |
| `committee_preset` field on presets | Stored but not applied in UI (see peer-review-01); hermes-setup table mentions it implicitly via preset names only |
| Export/import (`/api/workspace/export`, `/import`) | **No** |
| Profile switch clears landing redirect | **No** (Settings UX detail) |

**Verdict:** Hermes-setup workspace section describes **v10.14 single-profile MVP**, not **v10.15 multi-profile desk manager**. Integrators copying curl blocks cannot manage named profiles without reading `dashboard/app.py` or peer-review-01.

---

## CHANGELOG Completeness (v10.15.0)

### Present and accurate

- Terminal Workspace presets, Dashboard API routes, Settings UI section.
- `augur_workflow` MCP + `workflow.py` pipeline.
- Consensus module migration off `scanner.*`.
- Version badge sync, test count (1668).

### Missing or incomplete

| Omission | Notes |
|----------|-------|
| **Multi-profile workspace** | `create_profile`, `set_active_profile`, profile CRUD API — shipped in `workspace.py` + Settings UI; not in CHANGELOG Added. |
| **Workspace i18n (16 keys × 4 langs)** | Base preset/nav strings added in v10.15; CHANGELOG silent. |
| **Profile UI i18n gap** | Nine profile-management keys used in `settings.html` were never registered in `i18n.js` (fixed in this review). |
| **README sync convention** | Project rule #4 says sync README + CHANGELOG; README collapsible version log still shows **v9.0.6 as current** despite v10.15 badge. |
| **scanner/ legacy note** | V9_ROADMAP mentions it; CHANGELOG 10.15 does not (minor). |

**Verdict:** CHANGELOG captures the **headline features** but under-reports **profile system** and **i18n work**, and README version narrative is **several major releases stale**.

---

## i18n: ja/ko Workspace Keys

### Base workspace keys (16) — ✅ Covered

`test_i18n_workspace_v10_15.py` verifies these keys in zh/en/ja/ko inside `i18n.js`:

- Section title/desc, preset label, default page/ticker, ticker tape, sidebar collapsed, hidden nav, save/saved/preset-applied, four preset names.

Japanese and Korean translations are present and match Settings `data-i18n` attributes. `dashboard/i18n/en.json` and `zh.json` duplicate the same 16 keys under a `workspace` object (legacy/parallel bundle; runtime UI uses `i18n.js`).

### Profile management keys (9) — ❌ Missing (all languages)

`settings.html` references keys **not defined in any `i18n.js` block**:

| Key | UI usage |
|-----|----------|
| `settings-workspace-profile-label` | Profile selector section label |
| `settings-workspace-profile-delete` | Delete button |
| `settings-workspace-profile-create` | New profile button |
| `settings-workspace-profile-switched` | Toast on switch |
| `settings-workspace-profile-name-required` | Validation toast |
| `settings-workspace-profile-created` | Success toast |
| `settings-workspace-profile-cannot-delete` | Guard toast |
| `settings-workspace-profile-delete-confirm` | Confirm dialog |
| `settings-workspace-profile-deleted` | Success toast |

JS fallbacks hardcode English (`_t('settings-workspace-profile-switched', 'Profile switched')`), so **ja/ko users see English toasts and confirm strings** — a regression against v10.0's four-language promise.

`test_i18n_workspace_v10_15.py` does not cover these keys; `test_settings_html_references_covered` only checks the 16-key list.

**Fix applied in this review:** Add all nine keys to zh/en/ja/ko in `dashboard/static/js/i18n.js`.

---

## README (`README.md` / `README_EN.md`)

| Item | Status |
|------|--------|
| Version badge | ✅ v10.15.0 |
| Collapsible version history | ❌ Stops at v9.0.6 "current" |
| Terminal Workspace feature | ❌ Not mentioned in feature lists or version log |
| `augur_workflow` / agentic pipeline | ❌ Not in README body (only in docs/skills) |
| Hermes / MCP tool count | ❌ Still says "9 MCP tools" in v9.0.x collapse (now 10) |
| Workspace Settings pointer | ❌ No link to Settings → Terminal Workspace |

**Verdict:** Badge is current; **narrative body is 6+ minor versions behind**. Users discover v10.15 from the shield, not from prose.

---

## `skills/README.md`

### Strengths

- Accurate `augur_workflow` examples and valid step list.
- Terminal Workspace subsection with Settings path and preset names.
- Documents `enabled_personas` in persistence list (ahead of hermes-setup).
- Manifest format and persona table are maintained.

### Gaps

- Manifest example still shows `"version": "9.0.3"` — stale vs v10.10+ skill regeneration.
- No mention of **multi-profile** workspace or profile API.
- Workflow section does not note **`agents` overrides `enabled_personas`** (peer-review-02 flagged this too).
- `required_tools` in example omits `mcp_augur_workflow` (peer-review-08 flagged manifest drift).

---

## `hermes-agents/*.yaml`

### Strengths

- 18 files, one persona each; copy-paste path documented.
- `command: augur-mcp` aligned with v10.9+ console script.
- Descriptions mention `augur_workflow MCP`.

### Gaps (consistent with peer-review-08)

- `required_tools` lists only analyze/consensus/fetch — **not** workflow, committee, debate, sentiment.
- No pre-built **committee coordinator** yaml (only persona agents).
- Version field `"10.10.0"` while product is v10.15.0 (cosmetic drift).

---

## `V9_ROADMAP.md`

### Strengths

- Updated to v10.15.0 with accurate MCP tool count (10), test baseline (1668), scanner legacy note.
- v10.14 / v10.15 rows match shipped features.
- Key conventions (#4 doc sync) still valid.

### Stale items

- Repo split header still says augur stable **v8.2.3** / augur-next **v9.0.8** — confusing for readers on the merged v10 line.
- P3 section still lists "⏭ 日语/韩语 i18n" as future v10 plan despite ✅ v10.0.0 completion above.
- "README 截图更新" still open — accurate.
- "因子级雷达" still listed as needing API work — done in v10.11.0.

**Verdict:** Roadmap is **good session handoff for v10.15 engineering** but contains **contradictory todo checkmarks** in the P3 block.

---

## Cross-Review Summary

| Surface | Docs/i18n grade | Top action |
|---------|-----------------|------------|
| Workflow (Method 8) | B | Add "start `augur api` on 8900" callout; contrast with Dashboard 8000 |
| Hermes workspace section | C+ | Document profile CRUD + `enabled_personas` |
| CHANGELOG 10.15 | B− | Add multi-profile + workspace i18n bullets |
| ja/ko workspace i18n | B+ → A− after fix | Profile keys added |
| README version log | D | Refresh collapsible history to v10.15 |
| skills/README | B | Bump manifest version example; note agents vs enabled_personas priority |
| hermes-agents | B− | Align `required_tools` with advertised workflow |
| V9_ROADMAP | B | Resolve P3 i18n/radar stale todos |

---

## Fix Implemented in This Review

**Gap:** Nine workspace **named-profile** i18n keys missing from all four language blocks in `dashboard/static/js/i18n.js`, causing ja/ko (and zh/en) profile UI to fall back to English for toasts, labels, and delete confirmation.

**Change:** Add `settings-workspace-profile-*` keys to zh, en, ja, and ko sections of `i18n.js`.

**Recommended follow-ups (not in scope):**

1. Extend `test_i18n_workspace_v10_15.py` `WORKSPACE_KEYS` with the nine profile keys.
2. Add profile API subsection to `hermes-setup-guide.md` (zh + en).
3. Refresh README collapsible version log through v10.15.0.
4. CHANGELOG Added bullet for multi-profile workspace + workspace i18n.

---

## Verdict

Documentation **describes the v10.14 workspace MVP and v10.15 workflow headline** but **under-documents multi-profile desk management** and **splits REST server responsibilities** without a unified integrator table. i18n **delivered ja/ko for core workspace controls** but **missed the profile-management strings** added in the same Settings section — a clear ship gap for four-language UX. CHANGELOG and README **need a version-narrative pass** to match the v10.15 badge and V9_ROADMAP capability list.
