# Backend + Android Next Implementation Stages

Date: 2026-05-28

## What Was Reviewed

Inputs reviewed:

- `C:\Users\ASUS\Downloads\walkthrough.md`
- `C:\Users\ASUS\Downloads\walkthrough2.md`
- `C:\Users\ASUS\Downloads\walkthrough3.md`
- Current repository files under `backend/` and `aegis-agent/`

## Decisions From The Review

## Current Status Update

The local MVP now has Android-to-backend upload, device enrollment token
creation, backend normalization/risk/AI stub processing, Streamlit dashboard,
and worker-scoped plus SDK-lifecycle log collection.

Recently fixed:

- Duplicate telemetry payloads stay idempotent with `202` even when rate limiting
  is enabled.
- AI evidence bundles prefer the exact raw payload app snapshot instead of only
  the current device inventory.
- Dashboard risk trend renders as a single average-risk series.
- `AegisSdk.init()` starts the log collector and `shutdown()` stops it; worker
  snapshots no longer stop an already-running log collector.
- Backend exposes `GET /api/v1/logs/analysis`, and the dashboard has a dedicated
  Logs Analyzer screen for severity mix, rule signals, repeated clusters, device
  pressure, log pulse, top tags, and recent redacted log stream.

### Useful Changes Kept

- Bearer token authentication for telemetry and analyst APIs.
- Removal of `enrollment_token` from the telemetry JSON body.
- Modular FastAPI route files.
- Alembic skeleton for future migrations.
- Dashboard concept for analyst review.
- AI model run audit table and LLM stub boundary.
- Docker Compose path for API, worker, dashboard, and Postgres.

### Risky Changes Removed Or Neutralized

- Kafka is no longer part of the default runtime path.
- Nginx is no longer required for local development.
- Docker Compose was simplified from many services to the services needed now.
- The backend no longer attempts to connect to Kafka on startup, which removed slow local test startup.
- Debug cleartext traffic is allowed only in the Android sample app debug manifest so emulator uploads to `10.0.2.2` work; release remains HTTPS-only.
- Dashboard code was rewritten to match the actual backend API response shape.

### Errors Fixed

- Android build error from stale `enrollmentToken` constructor usage in `UploadTelemetryUseCase`.
- Android tests that still expected `TelemetryPayload.enrollmentToken`.
- Backend/dashboard API mismatch for timeline and payload detail fields.
- Dashboard feedback labels that did not match backend validation.
- Dashboard dependency gap for `requests` in its Dockerfile.
- Stale app inventory bug where full snapshots did not replace old current app state.

## Validation Completed

Backend:

```text
python -m pytest
18 passed
```

Android:

```text
.\gradlew.bat :aegis-agent:testDebugUnitTest :app:assembleDebug --console=plain
BUILD SUCCESSFUL
```

Docker Compose:

```text
docker compose config --quiet
compose-ok
```

Dashboard:

```text
python -m compileall dashboard
Compiled dashboard/app.py and dashboard/client.py
```

Emulator end-to-end:

- Started `Medium_Phone_API_36.1`.
- Installed `app-debug.apk`.
- Launched `com.aegis.agent.sample/.ui.MainActivity`.
- Observed scan flow in the emulator.
- Verified Android posted telemetry to `http://10.0.2.2:8080/api/v1/telemetry`.
- Verified backend returned `202 Accepted`.
- Verified backend processed payloads to `PROCESSED`.
- Verified latest risk for `sample-device-001` returned `High`.
- Verified AI stub produced an audited model run for high-risk evidence.

Evidence image:

- `docs/generated/emulator-aegis-launch.png`
- `docs/generated/emulator-aegis-complete.png`

## Implementation Stages

### Stage 1 - Stabilize Local Integration

Goal: make Android to backend to dashboard reliable on one developer machine.

Tasks:

- Done: use `POST /api/v1/enrollment-tokens` to create device enrollment tokens without editing code.
- Done: give the Android user the backend URL, device ID, and returned enrollment token.
- Done: scripted backend smoke test posts a sample payload and checks latest risk.
- Done: emulator flow has verified app upload, backend processing, and latest risk.
- Next: add a clean local database reset script for repeatable demos.
- Next: add a one-command emulator smoke script that installs the APK, launches the app, captures logs, and checks backend payload arrival.
- Next: make scan/upload/log status easier to inspect from the sample UI.

Exit criteria:

- One command can reset, run backend, install app, trigger scan, and verify backend ingestion.

### Stage 2 - Dashboard MVP

Goal: make analyst review useful without adding heavy infrastructure.

Tasks:

- Done: run Streamlit locally at `http://127.0.0.1:8501`.
- Done: show device list, latest risk, timeline, payload details, apps, logs, AI runs, feedback, fleet KPIs, risk distribution, priority devices, and trend.
- Done: add creative Logs Analyzer screen backed by `/api/v1/logs/analysis`.
- Next: add a dashboard smoke test against a live local server.
- Next: add stronger empty/error states for missing API token, failed payloads, and no AI runs.

Exit criteria:

- Analyst can inspect an uploaded emulator payload and submit feedback.

### Stage 3 - Data Correctness

Goal: make normalized data reliable enough for scoring and AI evidence.

Tasks:

- Strengthen full snapshot versus delta app inventory semantics.
- Add tests for app removals and package updates.
- Add tests for duplicate upload races and repeated WorkManager attempts.
- Store raw payload schema version and Android agent version.
- Add payload replay tooling for debugging failed normalization.

Exit criteria:

- Replaying raw payloads produces deterministic normalized state and risk outputs.

### Stage 4 - Risk And AI Quality

Goal: improve detection quality while keeping deterministic rules authoritative.

Tasks:

- Tune score weights using real emulator and real device payloads.
- Add evidence IDs to rule reasons.
- Add structured AI finding records separate from raw `ai_model_runs`.
- Add real LLM provider behind `LLMAnalyzer` with strict JSON validation.
- Compare AI findings against analyst feedback.

Exit criteria:

- High-risk cases have explainable rule reasons, evidence references, and audited AI assistance.

### Stage 5 - Production Path

Goal: harden after the local product loop is stable.

Tasks:

- Move production default to Postgres with Alembic migrations.
- Keep DB-backed worker first; add Redis queue only if throughput requires it.
- Move auth from shared bearer token to per-device enrollment credentials.
- Add Play Integrity backend token decode and verification.
- Add retention, backups, request logging, and operational metrics.
- Reconsider Nginx/Kafka only when there is a clear deployment or throughput reason.

Exit criteria:

- API, worker, dashboard, and Postgres can run with production-like settings and documented recovery steps.
