# AEGIS Backend MVP Comprehensive Guide

This guide explains the backend implementation that was added for the AEGIS mobile security project. The goal is a simple local MVP that can receive Android telemetry, preserve raw evidence, normalize useful records, score risk deterministically, and prepare a safe path for AI-assisted analysis.

Generated artifacts:

- PDF: `docs/backend-mvp-comprehensive-guide.pdf`
- PNG pages: `docs/generated/backend-mvp-guide/`

## What Was Built

The backend is a Python FastAPI service under `backend/`.

It includes:

- FastAPI app with health, telemetry ingestion, risk lookup, timeline, payload lookup, and feedback endpoints.
- SQLAlchemy models with SQLite as the local default and Postgres-compatible structure for later production.
- Raw JSON payload storage under `backend-data/raw-payloads/`.
- Telemetry schema v1 copied from the Android POC server and enforced at ingestion.
- Idempotency by `payload_id`.
- Normalization worker logic for device posture, current app inventory, and important logs.
- Log redaction and message hashing before log persistence.
- Deterministic risk scoring.
- AI model run audit table and an `LLMAnalyzer` stub.
- Analyst feedback capture for future model/rule evaluation.
- Pytest coverage for ingestion, worker behavior, risk scoring, AI stub behavior, and API lookups.

## Local Runtime

Default local configuration:

```text
DB: backend-data/aegis.db
Raw payloads: backend-data/raw-payloads/
Accepted enrollment token: sample-token
Queue mode: inline processing by default
```

Run the API:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Health check:

```text
GET http://127.0.0.1:8080/health
```

Run tests:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\backend
python -m pytest
```

## Public API

```text
GET  /health
POST /api/v1/telemetry
GET  /api/v1/devices/{device_id}/latest-risk
GET  /api/v1/devices/{device_id}/timeline
GET  /api/v1/payloads/{payload_id}
POST /api/v1/findings/{finding_id}/feedback
```

`POST /api/v1/telemetry` validates payloads against schema v1, authenticates the body `enrollment_token`, stores the raw JSON, enforces idempotency with `payload_id`, and returns `202 Accepted` for both new and duplicate accepted payloads.

## Processing Flow

1. Android agent sends telemetry.
2. API validates the enrollment token.
3. API validates telemetry schema v1.
4. Raw JSON is written to filesystem storage.
5. `telemetry_payloads` tracks accepted payload status.
6. Worker normalizes device posture, app inventory, and important logs.
7. Rule scoring creates a `risk_assessments` record.
8. High-risk cases build a redacted evidence bundle for the LLM stub.
9. AI attempts are recorded in `ai_model_runs`.
10. Analysts can record feedback for future evaluation.

## AI Design

AI is intentionally constrained in the MVP.

The deterministic backend remains authoritative for:

- Payload validation.
- Authentication decisions.
- Raw storage.
- Processing status.
- Risk score creation.
- Device/app/log state persistence.

The AI layer can assist by:

- Reading redacted evidence bundles.
- Producing structured JSON findings.
- Referencing evidence IDs.
- Supporting future analyst workflows.

The AI layer cannot:

- Override backend validation.
- Change normalized storage state.
- Replace deterministic risk rules.
- Persist findings without audit records.

## Current Verification

The project was verified locally with:

- `GET /health` returning `ok=true`.
- A high-risk sample telemetry payload accepted and processed.
- Latest risk lookup returning `risk_score=100`, `risk_label=Critical`, and `needs_human_review=true`.
- Payload lookup returning `processing_status=PROCESSED`.
- Backend test suite passing with `17 passed`.

## Production Readiness Path

The MVP is ready for the next hardening steps:

- Connect real Android uploads to the new backend.
- Add a dashboard or analyst UI over the existing API.
- Tune deterministic rules using real test data.
- Use analyst feedback to evaluate false positives and true positives.
- Move local SQLite to Postgres.
- Replace inline processing with Redis/RQ, Celery, or another queue.
- Move auth from body token to bearer headers, then mTLS later if needed.
- Add Play Integrity backend decode once the Android agent sends raw integrity tokens.
- Add real LLM provider wiring behind the existing `LLMAnalyzer` interface.
