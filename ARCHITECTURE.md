# Architecture

## Module role

`guild` is an AAS submodule with independent source control and local runtime configuration.

## Contract surface

- Module identity/config: `aas-module.json`
- Hive communication policy: `aas-hive.json`
- Inter-repo protocol baseline: `protocols/AGENT_INTEROP_V1.md`

## Design intent

- Keep repo-local docs discoverable through `INDEX.md`.
- Keep protocol docs versioned and backward compatible.
- Keep cross-repo operations explicit and traceable.
