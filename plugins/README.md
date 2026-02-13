# Guild Plugins

Guild-local plugins live in this directory.

Rules:
1. Keep plugin manifests schema-valid (`manifest.json` or `aas-plugin.json`).
2. Use `guild.`-prefixed capability names for module-owned commands.
3. Prefer backward-compatible capability evolution (new names > breaking changes).
4. Keep plugin runtime dependencies local to this module when possible.
