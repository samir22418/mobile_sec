# AEGIS Backend And Data Engineering Handoff

## Scope

The Android agent-side POC is ready for backend, AI model, and data-processing work.

The current server in this repo is only a receiver POC. The data engineer should replace it with production ingestion, storage, validation, feature extraction, and scoring.

Architecture companion:

```text
backend-server-architecture.md
ai-llm-threat-analysis-architecture.md
```

## Endpoint Contract

Current agent upload target:

```text
POST /api/v1/telemetry
Content-Type: application/json
Accept: application/json
X-Aegis-Payload-Id: <payload_id>
X-Aegis-Device-Id: <device_id>
```

Expected success response:

```text
HTTP 202 Accepted
```

Retry behavior:

- any non-2xx response is treated as failed
- failed scans stay queued locally
- the same `payload_id` is retried
- backend ingestion must be idempotent by `payload_id`

Schema:

```text
poc-server/telemetry_schema_v1.json
```

## Payload Top Level

Required fields:

```text
payload_id
scan_id
device_id
created_at_epoch_ms
enrollment_token
device_report
app_snapshot
important_logs
```

Idempotency key:

```text
payload_id
```

Recommended unique indexes:

```text
payload_id UNIQUE
(device_id, scan_id) UNIQUE
```

## Data Domains

### Device Posture

`device_report` contains:

- root detection booleans
- Play Integrity state
- security patch date
- bootloader state
- token hash for trace correlation

Important backend work:

- decode and verify Play Integrity tokens in production flow
- replace client placeholder verdicts with backend-trusted verdicts
- score stale patch date, root signals, bootloader state, and integrity failure

### App Inventory

`app_snapshot` contains:

- `total_app_count`
- `is_delta`
- app package metadata
- APK hash
- signing cert hash
- requested permissions
- install source
- system-app flag
- install/update timestamps

Important backend work:

- maintain latest device app state
- expand deltas into a current full device inventory
- join package/cert/hash values with threat intelligence
- score sideloaded apps, risky permissions, suspicious cert reuse, and unexpected app churn

### Important Logs

`important_logs` contains a bounded best-effort batch:

- log tag
- level
- message
- matched rule
- timestamp

Important backend work:

- sanitize/redact sensitive message content
- classify log messages with rules or ML/NLP
- correlate log bursts with scan posture and app changes
- handle empty arrays as normal

## Suggested Storage

Minimum relational tables:

```text
telemetry_payloads
device_reports
app_snapshots
app_inventory_events
important_logs
device_latest_state
risk_scores
```

Recommended raw storage:

```text
raw_telemetry_json
```

Keep the full raw payload for reprocessing as models improve.

## Suggested Processing Pipeline

1. Ingest HTTP payload.
2. Validate JSON schema.
3. Check idempotency by `payload_id`.
4. Store raw payload.
5. Normalize device report.
6. Normalize app snapshot.
7. Apply app delta to latest device state.
8. Normalize important logs.
9. Extract features.
10. Run risk scoring/model inference.
11. Store score and reasons.
12. Emit alert/event if score crosses threshold.

## Initial Feature Ideas For AI Models

Device features:

- rooted boolean
- root signal count
- integrity verdict category
- security patch age in days
- bootloader state category

App features:

- total app count
- changed app count
- sideloaded app count
- unknown-source ratio
- dangerous permission count
- new package count since previous scan
- APK hash/cert hash threat-intel hits
- cert reused across unrelated packages

Log features:

- important log count
- ERROR/ASSERT count
- threat-regex count
- security tag count
- failed-login count
- permission-denied count
- certificate/SSL error count

Temporal features:

- scans per device per day
- app churn rate
- risk score trend
- repeated upload failures
- repeated integrity errors

## Security Work To Finish In Backend

The POC currently includes `enrollment_token` in JSON. For production, move authentication out of the body.

Recommended production options:

- `Authorization: Bearer <agent token>` for first production pass
- mTLS/client certificate enrollment for enterprise deployment
- backend token rotation and revocation
- idempotency by `payload_id`
- request size limits
- JSON schema validation
- PII redaction for log messages
- signed server responses if commands are ever added later

Certificate pinning:

- Android network module supports future pinning
- real SHA-256 pins must be added only after production host/cert chain is known

## Play Integrity Backend Work

The agent currently stores an integrity token hash, not the raw token.

Production backend should define:

- nonce/challenge creation
- raw token submission policy
- Google decodeIntegrityToken call
- final verdict mapping
- replay protection
- trace correlation using token hash

## Current Agent Status

Implemented and verified:

- encrypted config persistence
- stable telemetry payload IDs
- durable upload queue
- HTTP upload client
- WorkManager retry handling
- POC server
- emulator success/failure/recovery test
- sample scan detail/debug UI
- important log capture and payload inclusion

The data engineer can now build server ingestion and data/model pipelines against `telemetry_schema_v1.json`.
