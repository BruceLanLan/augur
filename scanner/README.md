# scanner/ — Legacy compatibility shim (deprecated)

> **Deprecated as of v10.15.** Use [`src/augur/`](../src/augur/) instead.

The `scanner/` package is retained only for backward compatibility with older scripts
and imports. It re-exports symbols from `augur.*` and does not contain active logic.

## Migration

| Legacy import | Use instead |
|---------------|-------------|
| `scanner.personas.base` | `augur.personas.base` |
| `scanner.personas.registry` | `augur.registry` |
| `scanner.personas.*` | `augur.personas.*` |
| `scanner.persona_loader` | `augur.persona_loader` |

Dashboard, MCP, CLI, and tests should import from `augur` only.

## Optional legacy modules

One optional feature still references `scanner/` until migrated:

| Legacy import | Use instead | Status |
|---------------|-------------|--------|
| `scanner.ten_x_screener` | *(pending)* `augur.consensus.ten_x` | Loaded lazily; silent skip if absent |
| ~~`scanner.agent_hyperparams`~~ | `augur.agent_hyperparams` | **Migrated v10.15** |

## Removal timeline

Planned removal in a future major release after v10.x once downstream consumers migrate.
