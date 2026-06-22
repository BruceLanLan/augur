# Agent1 Workspace QA — Round 1

**Result:** 73/73 scoped tests passed (8.99s)

## Gaps

1. **Missing `PUT /api/workspace/profiles/{name}`** — `save_profile()` exists in module but HTTP API only saves active profile via `PUT /api/workspace`. Severity: **P1**. Fix: expose endpoint.
2. **Profile GET uses raw `strip().lower()` instead of `normalize_profile_name`** — invalid slugs like `Bad Name!` may produce inconsistent 404 messages. Severity: **P2**. Fix: normalize before lookup.
3. **`deleteWorkspaceProfile()` blocks only `default`, not active profile** — server rejects active delete but UI allows attempt. Severity: **P1**. Fix: compare against `_workspaceActiveProfile`.
4. **Profile i18n keys absent from `WORKSPACE_KEYS` test list** — keys exist in `i18n.js` but regression test won't catch removal. Severity: **P2**. Fix: extend test + JSON parity.
5. **`saveWorkspaceConfig` preset detection via `borderColor` style** — fragile DOM heuristic; `_workspaceState.layout_preset` is authoritative. Severity: **P2**. Fix: simplify save payload.
