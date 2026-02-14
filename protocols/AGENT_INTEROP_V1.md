# Agent Interop Protocol V1

Protocol Version: `1.0.0`
Contract ID: `guild-agent-interop-v1`

This repo adopts the AAS inter-repo protocol baseline for synchronous operations.

## Version

- Protocol version: `1.0.0`
- Repo: `guild`

## Core request fields

- `protocol_version`
- `operation_id`
- `request_id`
- `source_repo`
- `target_repo`
- `initiator`
- `intent`
- `constraints`
- `expected_outputs`
- `timeout_sec`
- `created_at_utc`

## Core response fields

- `protocol_version`
- `operation_id`
- `request_id`
- `ack`
- `status`
- `message`
- `artifacts`
- `updated_at_utc`

## Status enum

- `acknowledged`
- `in_progress`
- `blocked`
- `completed`
- `failed`
- `cancelled`

## Compatibility

- Major version changes are breaking.
- Minor changes must be additive.
- Unknown fields should be ignored, not rejected.

## Artifact location convention

- Response `artifacts` entries should use safe relative paths with repo prefix (for example `guild/docs/repo-alignment/PEER_BASELINE_REPORT.md`).
- `docs/repo-alignment/ARTIFACT_STORAGE_CONVENTIONS.md`
