# AEGIS — Demo Runbook & Verification Guide

This document covers the end-to-end demo path, expected outputs at each step, and how to verify that every system component is working correctly.

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11–3.13 | `python --version` |
| Node | 18+ | `node --version` |
| Android Studio | Hedgehog+ | emulator running API 33+ AVD |
| PowerShell | 5.1+ | `$PSVersionTable` |

---

## 1. Local dev stack (one-command startup)

```powershell
# From repo root — AEGIS telemetry backend + dashboard
.\tools\start_local_mvp.ps1

# With APK Studio on :8000 (requires apk-studio/ cloned):
.\tools\start_local_mvp.ps1 -StartApkStudio
```

What it does:
1. Kills any stale listeners on ports 8080 / 5173 / 8000.
2. Creates / reuses `backend/.venv` with Python 3.11–3.13.
3. Installs `backend/requirements.txt` into the venv.
4. Runs Alembic migrations (`alembic upgrade head`).
5. Starts uvicorn on `0.0.0.0:8080` (visible in the terminal).
6. Polls `GET http://127.0.0.1:8080/health` until HTTP 200.
7. Installs frontend deps (`npm ci`) and starts Vite on `127.0.0.1:5173`.
8. *(With `-StartApkStudio`)* Starts APK Studio uvicorn on `127.0.0.1:8000`.

**Expected terminal output:**
```
[AEGIS] uvicorn started on 0.0.0.0:8080
[AEGIS] Backend healthy ✓
[AEGIS] Dashboard at http://127.0.0.1:5173
```

---

## 2. Android emulator → backend

1. Start the emulator from Android Studio (API 33 AVD).
2. Open the AEGIS sample app (`aegis-agent/app`).
3. Tap **Enroll** — app POSTs `POST http://10.0.2.2:8080/api/v1/enroll` with the enrollment token.
4. Tap **Scan** — `DeviceScanner.scan()` runs all checks (~3–5 seconds).
5. Tap **Upload** — WorkManager sends `POST http://10.0.2.2:8080/api/v1/telemetry`.

**Expected result:** `HTTP 202 Accepted` — scan appears in the dashboard within seconds.

---

## 3. Dashboard happy path

Open `http://localhost:5173`.

| Screen | What to verify |
|---|---|
| **Devices** | Device `sample-device-001` (or emulator ID) listed with scan count |
| **Risk brief** | Risk label (Low / Medium / High / Critical) + score + reasons |
| **Timeline** | One entry per upload; timestamps match scan |
| **Logs analysis** | Filtered log signals; redacted if PII present |
| **AI decisions** | `used_ai_final: true` when score ≥ 40; findings with evidence refs |
| **Feedback** | Analyst can submit CONFIRM / DISMISS on a risk decision |
| **APK Analyzer tab** | Shows APK Studio status (green when running on :8000); "Open APK Analyzer" button links to APK Studio dashboard |

---

## 4. Health check

```bash
curl http://localhost:8080/health
```

**Expected (dev, inline mode, no Redis/Kafka):**
```json
{
  "status": "ok",
  "service": "aegis-backend",
  "checks": {
    "db":    {"status": "ok"},
    "redis": {"status": "not_configured"},
    "kafka": {"status": "not_configured"}
  }
}
```

**Expected (production docker-compose):**
```json
{
  "status": "ok",
  "service": "aegis-backend",
  "checks": {
    "db":    {"status": "ok"},
    "redis": {"status": "ok"},
    "kafka": {"status": "ok", "connected": true}
  }
}
```

HTTP 200 = healthy. HTTP 503 = degraded (one or more checks failed).

---

## 5. Risk scenario verification

### 5a. Rooted device (high risk)

Send a payload with `is_rooted: true`:

```python
import httpx, json

payload = {
    "payload_id": "demo-rooted",
    "scan_id": 99,
    "device_id": "demo-device",
    "created_at_epoch_ms": 1700000000000,
    "device_report": {
        "device_id": "demo-device",
        "timestamp_epoch_ms": 1700000000000,
        "root_detection": {"su_binary_found": True, "test_keys_found": True,
                           "superuser_apk_found": True, "is_rooted": True},
        "integrity_verdict": "FAILS",
        "security_patch_date": "2020-01-01",
        "bootloader_state": "red",
    },
    "app_snapshot": {"device_id": "demo-device", "timestamp_epoch_ms": 1700000000000,
                     "total_app_count": 0, "is_delta": False, "apps": []},
    "important_logs": [],
}

r = httpx.post("http://localhost:8080/api/v1/telemetry",
               json=payload,
               headers={"Authorization": "Bearer sample-token"})
print(r.status_code, r.json())
```

**Expected:** `202 {"status": "accepted"}`. Risk score ≥ 70 (High/Critical). AI analysis triggered.

### 5b. Verify via API

```bash
# Risk assessment
curl -H "Authorization: Bearer sample-token" \
     http://localhost:8080/api/v1/risk/latest/demo-device

# AI decision
curl -H "Authorization: Bearer sample-token" \
     http://localhost:8080/api/v1/ai/decisions/demo-rooted
```

---

## 6. APK Analyzer verification

Requires `apk-studio/` cloned and the stack started with `-StartApkStudio`.

1. Open `http://localhost:5173` → click **APK Analyzer** in the sidebar.
   - Status indicator should show **Running** (green).
2. Click **Open APK Analyzer** — opens APK Studio dashboard at `http://localhost:8000`.
3. Upload a sample APK (e.g. the debug build from `aegis-agent/app/build/outputs/apk/debug/`).
4. Expected pipeline: static analysis → risk score → MITRE ATT&CK tags → AI-fused report.
5. Download the HTML/PDF report from the APK Studio dashboard.

**Health check:**
```bash
curl http://localhost:8000/health
```

---

## 7. Rate limiting verification

```bash
# Send 121 requests in quick succession (default limit: 120/60s)
for i in $(seq 1 121); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer sample-token" \
    -H "Content-Type: application/json" \
    -d '{"payload_id":"rl-test-'$i'"}' \
    http://localhost:8080/api/v1/telemetry
done
# First 120: 202. Request 121: 429.
```

---

## 8. Production docker-compose bring-up

```bash
cd backend
cp .env.production.example .env
# Edit .env: set POSTGRES_PASSWORD, AEGIS_ACCEPTED_ENROLLMENT_TOKENS, etc.

# Generate TLS cert (dev / self-signed)
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/aegis.key \
  -out certs/aegis.crt -sha256 -days 365 -nodes -subj "/CN=localhost"

docker compose up --build -d
docker compose ps       # all services healthy
docker compose logs api # check JSON structured logs
```

**Expected:** all 8 services `healthy` within ~60s. Dashboard reachable at `https://localhost`.

---

## 9. CI verification

All tests run on every push/PR:

```bash
cd backend
pip install -r requirements.txt
ruff check app/ tests/          # lint
mypy app/ --ignore-missing-imports --no-strict-optional  # type check
pytest tests/ -x -q             # 115+ tests, all green
```

Frontend:
```bash
cd frontend
npm ci
npm run build   # tsc + vite build, no type errors
```

---

## 10. Known limitations & edge cases

| Limitation | Notes |
|---|---|
| Play Integrity removed from Android agent | `integrity_verdict` is still accepted by the backend (optional field); backend `PlayIntegrityService` still works when credentials are set (direct API calls, not agent-collected) |
| APK Studio not bundled | Clone the APK Studio repo into `apk-studio/` and use `-StartApkStudio`; the placeholder directory just marks the integration point |
| AI analysis skipped below threshold | `risk_score < 40` → no AI run; deterministic score is used |
| Kafka only in docker-compose | Dev mode (`process_inline=true`) uses SQLite + inline processing |
| `READ_LOGS` on emulator | Only `SECURITY` priority logs visible without root; log signals may be sparse on AVD |
| Redis falls back to in-memory | If Redis is unavailable, rate limiting is per-process (not shared across replicas) |
