# AEGIS Backend + AI Next Steps Roadmap

This roadmap starts from the local backend MVP that is already implemented and running. The goal is to move from a working local service into an integrated security product without making the architecture too complex too early.

## Current Baseline

The backend MVP now has:

- FastAPI service under `backend/`.
- SQLite local database.
- Filesystem raw payload storage.
- Android telemetry schema validation.
- Enrollment token authentication from the telemetry body.
- Idempotent telemetry ingestion by `payload_id`.
- Normalization for device posture, current app inventory, and important logs.
- Redacted log persistence with message hashing.
- Deterministic risk scoring.
- AI/LLM stub with audited `ai_model_runs`.
- Analyst feedback endpoint.
- Docker Compose path for API, worker, Postgres, and Redis.
- Passing test suite.

## Recommended Next Phases

### Phase 1 - Connect The Android Agent

Point the Android agent upload client at the new backend instead of the proof-of-concept server.

Deliverables:

- Configure the Android agent backend URL.
- Send real scan telemetry to `POST /api/v1/telemetry`.
- Confirm valid payloads return `202`.
- Confirm duplicate payloads are accepted without duplicate rows.
- Verify raw JSON appears in `backend-data/raw-payloads/`.
- Verify latest risk appears for the uploaded device.

Exit criteria:

- One real device can complete scan, upload, backend processing, and latest-risk lookup.

### Phase 2 - Add A Minimal Analyst Dashboard

Build a small local dashboard over the existing API. Keep it simple and operational.

Deliverables:

- Device list with latest risk label and score.
- Device detail page with timeline.
- Payload detail page with normalized summary.
- Important logs section with redacted messages.
- Analyst feedback form.

Exit criteria:

- An analyst can open the dashboard, find a risky device, inspect the evidence, and submit feedback.

### Phase 3 - Improve Rules With Real Data

Use real test-device data to tune deterministic scoring before adding real LLM providers.

Deliverables:

- Add rule fixtures for common safe, suspicious, and critical devices.
- Tune scoring thresholds.
- Add reasons for risky app permission/source combinations.
- Add tests for Android edge cases discovered during integration.
- Add export of risk assessment examples for review.

Exit criteria:

- Risk labels are stable enough for demo scenarios and obvious false positives are reduced.

### Phase 4 - Add Real AI Provider Behind The Stub

Keep the current `LLMAnalyzer` interface and add a real provider implementation behind it.

Deliverables:

- Provider settings using environment variables.
- Timeout and retry policy.
- Structured JSON schema enforcement.
- Evidence reference validation.
- Redaction checks before model calls.
- Provider comparison using `ai_model_runs`.

Exit criteria:

- High-risk cases can create audited AI findings without changing deterministic backend decisions.

### Phase 5 - Production Hardening

Move from local MVP behavior to a deployable backend path.

Deliverables:

- Postgres as default production database.
- Redis-backed queue and dedicated worker.
- Bearer token auth, then mTLS later if needed.
- Alembic migrations.
- Request logging and error metrics.
- Play Integrity backend challenge/decode flow.
- Backup and retention policy for raw telemetry.

Exit criteria:

- API, worker, database, and queue can run from Docker Compose with production-like settings.

## Priority Order

1. Connect the Android agent to the backend.
2. Add a minimal dashboard for device risk review.
3. Tune deterministic risk rules with real telemetry.
4. Add real LLM provider support behind the existing stub.
5. Harden deployment with Postgres, Redis queue, migrations, and stronger auth.

## Key Principle

AI should help analysts understand suspicious evidence, but the backend should remain deterministic for validation, storage, normalization, and risk state. This keeps the system explainable, testable, and safer to mature.
