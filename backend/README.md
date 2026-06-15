# AEGIS Backend MVP

Local FastAPI backend for AEGIS telemetry ingestion, normalization, risk scoring,
and audited AI stub analysis.

## Guide Artifacts

The comprehensive backend guide is available at:

```text
../docs/backend-mvp-comprehensive-guide.pdf
../docs/generated/backend-mvp-guide/
```

## Run Locally

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Defaults:

```text
DB: ../backend-data/aegis.db
Raw payloads: ../backend-data/raw-payloads/
Accepted enrollment token: sample-token
```

Run one pending worker batch:

```powershell
python -m app.worker --once
```

Run a polling worker:

```powershell
python -m app.worker
```

## Docker Compose

The Compose profile runs the API, a polling worker, Postgres, and Redis:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\backend
docker compose up --build
```

Compose sets `AEGIS_PROCESS_INLINE=false`, so the API accepts telemetry and the
worker processes pending payloads in the background.

## Endpoints

```text
GET  /health
POST /api/v1/telemetry
GET  /api/v1/devices/{device_id}/latest-risk
GET  /api/v1/devices/{device_id}/timeline
GET  /api/v1/payloads/{payload_id}
POST /api/v1/findings/{finding_id}/feedback
```

The local MVP processes telemetry inline after ingestion. The database status
fields are still queue-ready so Redis/Celery/RQ can replace inline processing in
a later production phase.
