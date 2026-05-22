# AEGIS Final Backend Architecture

This is the simplified final backend architecture for AEGIS.

The design keeps the backend practical: one ingestion API, one processing
pipeline, one operational database, one risk/AI engine, and one dashboard/API
surface. AI is included, but it is not allowed to make the system complicated or
untrustworthy.

## 1. Final Shape

```text
Android Agent
  -> Backend Ingestion API
  -> Raw Payload Store
  -> Processing Queue
  -> Telemetry Worker
  -> Risk + AI Engine
  -> Risk Assessment Store
  -> Dashboard / Alerts / API
```

The backend has five core parts:

1. **Ingestion API**
2. **Telemetry Worker**
3. **Storage Layer**
4. **Risk + AI Engine**
5. **Dashboard/API Layer**

## 2. Key Rule

```text
The LLM explains and correlates evidence. It does not replace validation,
storage, deterministic rules, or backend trust decisions.
```

This keeps the architecture mature but simple.

## 3. Component Responsibilities

### Ingestion API

Receives telemetry from the Android agent.

Responsibilities:

- accept `POST /api/v1/telemetry`
- authenticate the device or enrollment token
- validate JSON schema
- enforce idempotency by `payload_id`
- store the raw payload
- enqueue work for async processing
- return `202 Accepted`

This service should be fast and boring. It should not run AI models directly.

### Telemetry Worker

Processes accepted telemetry in the background.

Responsibilities:

- read accepted payloads from the queue
- normalize device posture
- normalize app inventory
- update latest app state
- redact important logs
- extract risk features
- call the Risk + AI Engine
- store final assessment

### Storage Layer

Keeps both raw and normalized data.

Use:

- PostgreSQL for operational data
- object storage or filesystem for raw JSON
- Redis/RabbitMQ/Kafka/SQS-style queue for async jobs

For a first build, PostgreSQL + local object storage + Redis queue is enough.

### Risk + AI Engine

Produces the final device risk assessment.

Order of execution:

1. deterministic rules
2. simple feature scoring
3. small specialist models if available
4. LLM analyst only for suspicious or high-risk cases
5. reviewer LLM only for critical or ambiguous cases
6. final evidence fusion

Simple rule:

```text
Run cheap, deterministic checks first. Use LLMs only when they add value.
```

### Dashboard/API Layer

Exposes results to humans and other systems.

Responsibilities:

- latest device risk
- device timeline
- evidence-backed findings
- recommended actions
- alerts
- analyst feedback labels

## 4. Final Data Flow

```text
1. Agent uploads telemetry.
2. API validates and stores the raw payload.
3. API checks duplicate `payload_id`.
4. API enqueues the payload.
5. Worker normalizes posture, apps, and logs.
6. Worker builds a redacted evidence bundle.
7. Risk engine runs rules.
8. AI runs only when needed.
9. Evidence fusion creates the final score.
10. Dashboard shows score, reasons, and actions.
```

## 5. Minimal Tables

Keep the first production schema small.

```text
devices
enrollments
telemetry_payloads
device_reports
app_inventory_current
important_logs
risk_assessments
ai_model_runs
analyst_feedback
```

### `telemetry_payloads`

Owns idempotency.

Important fields:

```text
payload_id UNIQUE
device_id
scan_id
received_at
raw_payload_uri
processing_status
```

### `device_reports`

Stores normalized posture.

Important fields:

```text
payload_id
device_id
is_rooted
root_signal_count
integrity_verdict
security_patch_age_days
bootloader_state
```

### `app_inventory_current`

Stores latest known app state per device.

Important fields:

```text
device_id
package_name
version_code
apk_sha256
cert_sha256
install_source
requested_permissions_json
last_seen_payload_id
```

### `important_logs`

Stores redacted important logs.

Important fields:

```text
payload_id
device_id
tag
level
matched_rule
message_redacted
message_hash
```

### `risk_assessments`

Stores the final result.

Important fields:

```text
payload_id
device_id
risk_score
risk_label
confidence
reasons_json
recommended_action
needs_human_review
created_at
```

### `ai_model_runs`

Tracks model usage for auditability.

Important fields:

```text
payload_id
model_role
model_name
prompt_version
input_bundle_hash
output_json
status
latency_ms
cost_estimate
```

## 6. AI Design, Kept Simple

Use three AI levels:

### Level 1 - Rules

Always run.

Examples:

- rooted device
- failed integrity
- old patch level
- unlocked bootloader
- sideloaded app with sensitive permissions
- suspicious logs

### Level 2 - Specialist Models

Run when available.

Examples:

- log category classifier
- suspicious permission classifier
- app reputation classifier

### Level 3 - LLMs

Run only for suspicious, high-risk, or ambiguous cases.

Use:

- one primary LLM analyst
- one reviewer LLM only for critical cases

The LLM receives:

```text
redacted evidence bundle
features
rule results
threat intelligence hits
recent device history
```

The LLM must return:

```text
structured JSON
evidence references
confidence
recommended action
```

## 7. Recommended APIs

Required:

```text
GET  /health
POST /api/v1/telemetry
GET  /api/v1/devices/{device_id}/latest-risk
GET  /api/v1/devices/{device_id}/timeline
GET  /api/v1/payloads/{payload_id}
```

Later:

```text
GET  /api/v1/alerts
POST /api/v1/findings/{finding_id}/feedback
POST /api/v1/enrollments
POST /api/v1/enrollments/{id}/revoke
```

## 8. Simple Deployment

Start with:

```text
FastAPI backend
PostgreSQL
Redis queue
worker process
local/object raw payload storage
one LLM provider
```

Scale later to:

```text
multiple API instances
multiple workers
managed object storage
managed queue
private/local model option
warehouse export
```

## 9. Build Order

### Phase 1 - Ingestion

- production `POST /api/v1/telemetry`
- schema validation
- idempotency
- raw payload storage
- queue publish

### Phase 2 - Normalization

- device report table
- app inventory state
- redacted important logs
- processing worker

### Phase 3 - Risk Rules

- deterministic scoring
- risk assessment table
- latest-risk endpoint

### Phase 4 - Simple AI

- evidence bundle builder
- redaction checks
- primary LLM analyst
- model run audit table

### Phase 5 - Mature AI

- reviewer LLM
- specialist classifiers
- analyst feedback
- evaluation metrics

## 10. Final Architecture Summary

The final backend is:

```text
API for intake
queue for reliability
worker for processing
PostgreSQL for operational state
raw store for replay
rules for stable risk scoring
LLMs for evidence explanation on selected cases
dashboard/API for action
```

This gives us a backend that is simple enough to build, but mature enough for
security work.

