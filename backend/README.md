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
$env:AEGIS_ACCEPTED_ENROLLMENT_TOKENS='sample-token'
$env:AEGIS_ANALYST_TOKENS='sample-token'
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Defaults:

```text
DB: ../backend-data/aegis.db
Raw payloads: ../backend-data/raw-payloads/
Accepted enrollment token: configured by AEGIS_ACCEPTED_ENROLLMENT_TOKENS
Accepted analyst token: configured by AEGIS_ANALYST_TOKENS
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

The Compose profile runs the API, a polling worker, Postgres, and the
dashboard:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\backend
docker compose up --build
```

Compose sets `AEGIS_PROCESS_INLINE=false`, so the API accepts telemetry and the
worker processes pending payloads in the background. Kafka/Nginx are intentionally
not on the default path; they can be added later when the local flow is stable.

## Endpoints

```text
GET  /health
POST /api/v1/telemetry
POST /api/v1/enrollment-tokens
GET  /api/v1/enrollment-tokens
POST /api/v1/enrollment-tokens/{token_id}/revoke
GET  /api/v1/devices/{device_id}/latest-risk
GET  /api/v1/devices/{device_id}/timeline
GET  /api/v1/payloads/{payload_id}
POST /api/v1/findings/{finding_id}/feedback
```

The local MVP processes telemetry inline after ingestion. The database status
fields are still queue-ready so Redis/Celery/RQ can replace inline processing in
a later production phase.

## Create A Device Enrollment Token

### Browser Admin Page

Open the local admin page:

```text
http://127.0.0.1:8080/
```

For local development, enter `sample-token` as the analyst token, save it, then
create a device token with a label and device ID. Copy the returned token into
the Android app's Connect Device screen. The raw token is shown only once; after
that the page lists only token metadata and revoke actions.

### API

Use an analyst token to create a one-time visible enrollment token. The backend
stores only the token hash.

```powershell
$headers = @{ Authorization = 'Bearer sample-token' }
$body = @{ label = 'Lab phone 01'; device_id = 'android-lab-001' } | ConvertTo-Json
Invoke-RestMethod `
  -Uri 'http://127.0.0.1:8080/api/v1/enrollment-tokens' `
  -Method Post `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body $body
```

Give the returned `token` to the Android user. They paste it into the app's
Connect Device screen with the backend URL and device ID.
