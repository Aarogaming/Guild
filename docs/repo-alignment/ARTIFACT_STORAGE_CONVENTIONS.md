# Artifact Storage Conventions

## Purpose

Define a consistent path convention for inter-repo operation outputs so agents can
exchange artifacts without ambiguous locations.

## Path format

Response `artifacts` entries in `protocols/AGENT_INTEROP_V1.md` should use safe
relative paths with a repo prefix:

- `<RepoName>/<relative/path/to/file>`
- Example: `guild/docs/repo-alignment/PEER_BASELINE_REPORT.md`

## Safety rules

- No absolute paths (`/`, `\`, or drive-letter roots).
- No traversal segments (`..`).
- No empty path segments.
- Include the repo prefix directory as the first segment.

## Recommended operation bundle layout

For operation `op_YYYYMMDD_xxx`:

- `artifacts/interop/<source_repo>/outbox/<operation_id>/request.json`
- `artifacts/interop/<target_repo>/inbox/<operation_id>/request.json`
- `artifacts/interop/<target_repo>/outbox/<operation_id>/response.json`
- `artifacts/interop/<source_repo>/inbox/<operation_id>/response.json`
