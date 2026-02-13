# Guild Hub I/O Network

Protocol Version: `1.0.0`
Contract ID: `guild-hub-io-network`

## Purpose
Define Guild-owned input/output lanes on top of AAS hub communication primitives.

## Transport stack
1. `event_bus`: low-latency in-process signaling.
2. `outbox`: durable replay and ACK-aware delivery state.
3. `nats`: cross-process and cross-repo propagation.

## Guild channel policy
1. Primary inbound topic namespace: `guild.inbox.*`
2. Primary outbound topic namespace: `guild.outbox.*`
3. Status and heartbeat namespace: `guild.status.*`

## Envelope requirements
1. Use universal envelope fields (`schemaName`, `schemaVersion`, `kind`, `topic`).
2. Include `message_id`, `module_id`, and `sequence` for dedupe and replay.
3. Preserve `trace_id` and `correlation_id` across adapters and bridges.
4. Set `require_ack=true` for state-changing commands.

## Storage and replay
1. Guild hive storage root: `artifacts/hives/guild`
2. Durable outbox path: `artifacts/hives/guild/outbox`
3. ACK cursor and NATS replay cursor are persisted under the same root.

## Compatibility
1. Keep all new event types additive.
2. Never remove or rename existing event types without a deprecation window.
3. Consumers should ignore unknown payload fields.
