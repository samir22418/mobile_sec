# AEGIS Agent Phase 11 - Backend Handoff Essentials

## Purpose

This phase pulls forward only the Phase 11 items needed to hand the project to the backend/data/AI owner.

It does not turn the POC server into a production backend. It freezes the agent-side contract and documents what the server must implement next.

## Added

```text
backend-data-engineering-handoff.md
poc-server/telemetry_schema_v1.json
```

## Essential Decisions

### Idempotency

The backend must use:

```text
payload_id
```

as the primary idempotency key.

The Android agent retries the same queued scan with the same `payload_id`.

### Auth

Current POC:

```text
enrollment_token inside JSON body
```

Production recommendation:

```text
Authorization: Bearer <agent token>
```

or mTLS for enterprise deployments.

### Schema

The schema file is intentionally permissive with `additionalProperties: true` so the backend can accept additive agent changes while still validating required fields.

### AI/Data Pipeline

The backend should keep both:

- normalized relational/warehouse tables
- raw telemetry JSON

Raw JSON keeps the project reprocessable when risk rules and ML features improve.

## Remaining Production Hardening After Handoff

These are still production tasks, but they no longer block the data engineer:

- production auth implementation
- mTLS/client certificate enrollment
- real certificate pins
- backend Play Integrity decode flow
- token rotation/revocation
- privacy review for logs
- SOC dashboard and alert workflow

## Status

The backend handoff essentials are complete.

